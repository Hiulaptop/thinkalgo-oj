from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from judge.models import ProblemAuthoringUpload, ProblemPackageImport
from judge.problem_authoring.types import AuthoringError
from judge.problem_authoring.uploads import receive_upload
from judge.utils.problem_package_import import archive_path, require_access


def adopt_finished_legacy(*, limit=100):
    from django.conf import settings
    from judge.models import Problem, ProblemAuthoringState, ProblemData
    candidates = ProblemPackageImport.objects.filter(
        state__in=('FINISHED', 'FAILED'), problem__isnull=False, problem__authoring_state__isnull=True,
    ).values_list('problem_id', flat=True).distinct()[:limit]
    adopted = 0
    for problem_id in list(candidates):
        with transaction.atomic():
            problem = Problem.objects.select_for_update().filter(pk=problem_id, deleted_at__isnull=True).first()
            if problem is None or ProblemAuthoringState.objects.filter(problem=problem).exists():
                continue
            if ProblemPackageImport.objects.filter(
                    problem=problem, state__in=('PUBLISHING', 'SUBMITTING', 'JUDGING')).exists():
                continue
            data = ProblemData.objects.filter(problem=problem).first()
            ready = bool(data and data.has_yml() and problem.cases.exists())
            if getattr(settings, 'BRIDGED_R2_PROBLEMS', False):
                ready = ready and bool(data.r2_release_version and data.r2_release_sha256)
            ProblemAuthoringState.objects.create(problem=problem, data_state='READY' if ready else 'MISSING',
                                                 active_data_revision=1 if ready else 0)
            adopted += 1
    return {'adopted': adopted}


def adopt_legacy_draft(context, package_import_id):
    with transaction.atomic():
        try:
            record = ProblemPackageImport.objects.select_for_update().get(pk=package_import_id)
        except (ProblemPackageImport.DoesNotExist, ValueError, ValidationError) as exc:
            raise AuthoringError('invalid_upload', 'Package draft is unavailable.') from exc
        from judge.problem_authoring.policy import context_user
        user = context_user(context)
        require_access(record, user)
        if record.problem_id or context.organization_id is not None:
            raise AuthoringError('invalid_upload', 'This legacy draft cannot be imported in the selected scope.')
        if record.created <= timezone.now() - timedelta(hours=24):
            raise AuthoringError('upload_expired', 'Package draft expired. Upload the ZIP again.')
        existing = ProblemAuthoringUpload.objects.filter(owner=user.profile,
                                                         manifest__legacy_import=str(record.pk)).first()
        if existing:
            return existing
        with archive_path(record).open('rb') as source:
            upload = receive_upload(context, source, 'PACKAGE')
        upload.manifest['legacy_import'] = str(record.pk)
        upload.save(update_fields=['manifest'])
        return upload
