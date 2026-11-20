from django.conf import settings
from django.db.models import Sum

from judge.models import ProblemAuthoringUpload, ProblemData, ProblemDataOperation
from judge.problem_authoring.types import AuthoringError


def reserve_upload_bytes(context, compressed_bytes, problem_id=None):
    from judge.problem_authoring.policy import context_user
    user = context_user(context)
    owner_usage = ProblemAuthoringUpload.objects.filter(owner=user.profile).aggregate(total=Sum('size'))['total'] or 0
    snapshots = list(ProblemDataOperation.objects.all().values_list(
        'config', 'problem__organization_id',
    ))
    owner_usage += sum(int(config.get('snapshot_bytes', 0)) + int(config.get('workspace_bytes', 0))
                       for config, _ in snapshots if config.get('owner_id') == user.profile.pk)
    owner_limit = getattr(settings, 'PROBLEM_AUTHORING_OWNER_UPLOAD_LIMIT', 200 * 1024**2)
    if owner_usage + compressed_bytes > owner_limit:
        raise AuthoringError('storage_quota', 'Your retained uploads exceed the upload storage limit.')
    if context.organization_id is None or not getattr(settings, 'VNOJ_QUOTA_ENFORCEMENT_ENABLED', False):
        return
    from judge.models import Organization
    organization = Organization.objects.get(pk=context.organization_id)
    active = ProblemData.objects.filter(
        problem__organization=organization, problem__deleted_at__isnull=True,
    ).aggregate(total=Sum('zipfile_size'))['total'] or 0
    retained = ProblemAuthoringUpload.objects.filter(
        organization=organization,
    ).aggregate(total=Sum('size'))['total'] or 0
    retained += sum(int(config.get('snapshot_bytes', 0)) + int(config.get('workspace_bytes', 0))
                    for config, organization_id in snapshots if organization_id == context.organization_id)
    budget = getattr(settings, 'PROBLEM_AUTHORING_REPLACEMENT_BUDGET', 100 * 1024**2) if problem_id else 0
    if active + retained + compressed_bytes > organization.max_storage + budget:
        raise AuthoringError('storage_quota', 'Organization storage limit would be exceeded.')
