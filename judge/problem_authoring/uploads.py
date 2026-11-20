from dataclasses import asdict
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from judge.models import Organization, Problem, ProblemAuthoringUpload, Profile
from judge.problem_authoring.packages import inspect_full_package, inspect_tests
from judge.problem_authoring.policy import authorize_create, authorize_edit, context_user
from judge.problem_authoring.quota import reserve_upload_bytes
from judge.problem_authoring.storage import stage_upload, upload_path
from judge.problem_authoring.types import AuthoringError


KINDS = {'TESTS', 'PACKAGE', 'PDF', 'SOURCE'}


def _authorize(context, problem_id=None):
    if problem_id is None:
        authorize_create(context)
    else:
        try:
            problem = Problem.objects.get(pk=problem_id)
        except Problem.DoesNotExist as exc:
            raise AuthoringError('permission_denied', 'Problem is unavailable.') from exc
        authorize_edit(context, problem)


def _authorize_kind(user, kind):
    if kind not in KINDS:
        raise AuthoringError('invalid_upload', 'Unsupported upload type.')
    permission = {'PACKAGE': 'judge.import_problem_package', 'PDF': 'judge.upload_file_statement'}.get(kind)
    if permission and not user.has_perm(permission):
        raise AuthoringError('permission_denied', 'You do not have permission for this upload type.')


def _manifest(stream, kind):
    if kind in ('TESTS', 'PACKAGE'):
        result = (inspect_tests if kind == 'TESTS' else inspect_full_package)(stream)
        manifest = asdict(result)
        for case in manifest['tests']:
            case['points'] = str(case['points'])
        return manifest, result.expanded_bytes
    stream.seek(0, 2)
    size = stream.tell()
    limit = getattr(settings, 'PDF_STATEMENT_MAX_FILE_SIZE', 5 * 1024**2) if kind == 'PDF' else 5 * 1024**2
    if not size or size > limit:
        raise AuthoringError('invalid_upload', 'File is empty or exceeds size limit.')
    stream.seek(0)
    content = stream.read(limit + 1)
    if kind == 'PDF':
        if not content.startswith(b'%PDF-'):
            raise AuthoringError('invalid_upload', 'Choose a PDF document.')
    else:
        try:
            if not content.decode('utf-8-sig').strip():
                raise AuthoringError('invalid_upload', 'Source file is empty.')
        except UnicodeDecodeError as exc:
            raise AuthoringError('invalid_upload', 'Source must be UTF-8 text.') from exc
    return {}, size


def receive_upload(context, stream, kind, *, problem_id=None):
    _authorize(context, problem_id)
    user = context_user(context)
    _authorize_kind(user, kind)
    manifest, expanded = _manifest(stream, kind)
    stream.seek(0, 2)
    size = stream.tell()
    staged = None
    saved = False
    try:
        with transaction.atomic():
            if context.organization_id:
                Organization.objects.select_for_update().get(pk=context.organization_id)
            Profile.objects.select_for_update().get(pk=user.profile.pk)
            _authorize(context, problem_id)
            _authorize_kind(context_user(context), kind)
            reserve_upload_bytes(context, size, problem_id)
            upload = ProblemAuthoringUpload(owner=user.profile, organization_id=context.organization_id, kind=kind,
                                            expires_at=timezone.now() + timedelta(hours=24), manifest=manifest,
                                            expanded_size=expanded)
            path, digest, actual_size = stage_upload(stream, upload.pk)
            upload.path, upload.sha256, upload.size = path, digest, actual_size
            staged = upload_path(upload)
            if size != actual_size or (manifest and digest != manifest['sha256']):
                raise AuthoringError('invalid_upload', 'Upload changed while it was being stored.')
            upload.save()
        saved = True
        return upload
    except OSError as exc:
        raise AuthoringError('storage_error', 'Cannot store upload. Please retry or contact an administrator.') from exc
    finally:
        if staged is not None and not saved:
            staged.unlink(missing_ok=True)
            staged.parent.rmdir()


def publish_staged_pdf(context, upload_id, *, problem_id=None):
    import fcntl
    from django.core.files import File
    from judge.views.widgets import pdf_statement_uploader
    upload = get_upload(context, upload_id, kind='PDF', for_consumption=True, problem_id=problem_id)
    path = upload_path(upload)
    with (path.parent / 'pdf.lock').open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        upload = get_upload(context, upload_id, kind='PDF', for_consumption=True, problem_id=problem_id)
        if upload.manifest.get('published_url'):
            return upload.manifest['published_url']
        try:
            with path.open('rb') as source:
                url = pdf_statement_uploader(File(source, name='statement.pdf'), authoring_id=upload.pk)
        except Exception as exc:
            raise AuthoringError('storage_error', 'Unable to store the PDF. Please retry.') from exc
        with transaction.atomic():
            Profile.objects.select_for_update().get(pk=upload.owner_id)
            upload = ProblemAuthoringUpload.objects.select_for_update().get(pk=upload.pk)
            upload.manifest['published_url'] = url
            upload.save(update_fields=['manifest'])
        return url


def get_upload(context, upload_id, *, kind, for_consumption=False, problem_id=None):
    _authorize(context, problem_id)
    user = context_user(context)
    _authorize_kind(user, kind)
    try:
        uploads = ProblemAuthoringUpload.objects.filter(
            organization_id=context.organization_id, kind=kind,
        )
        if not for_consumption and problem_id is not None:
            uploads = uploads.filter(consumed_by_id=problem_id)
        else:
            uploads = uploads.filter(owner=user.profile)
        upload = uploads.get(pk=upload_id)
    except (ProblemAuthoringUpload.DoesNotExist, ValueError, ValidationError) as exc:
        raise AuthoringError('invalid_upload', 'Upload is unavailable in this scope.') from exc
    if upload.manifest.get('cleanup_pending'):
        raise AuthoringError('upload_expired', 'Upload is being removed. Please upload the file again.')
    if upload.consumed_by_id is not None:
        if upload.consumed_by_id != problem_id:
            raise AuthoringError('invalid_upload', 'Upload has already been used by a different problem.')
    elif upload.expires_at <= timezone.now():
        raise AuthoringError('upload_expired', 'Upload expired. Please upload the file again.')
    path = upload_path(upload)
    if not path.is_file():
        raise AuthoringError('storage_error', 'Uploaded file is unavailable. Please upload it again.')
    if for_consumption:
        import hashlib
        digest = hashlib.sha256()
        with path.open('rb') as source:
            for chunk in iter(lambda: source.read(65536), b''):
                digest.update(chunk)
        if digest.hexdigest() != upload.sha256:
            raise AuthoringError('invalid_upload', 'Uploaded file changed. Please upload it again.')
    return upload
