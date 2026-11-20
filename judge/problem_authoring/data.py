import hashlib
import json
import logging
import os
import shutil
import uuid
import zipfile
from datetime import timedelta
from pathlib import Path

import yaml
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from judge.models import Problem, ProblemAuthoringState, ProblemData, ProblemDataOperation, ProblemTestCase, Submission
from judge.problem_authoring.advanced import begin_external_data_change  # noqa: F401
from judge.problem_authoring.storage import sync_artifact_directory, sync_directory, upload_path
from judge.problem_authoring.types import AuthoringError, ConflictError
from judge.utils.problem_data import ProblemDataCompiler
from judge.utils.problem_releases import build_release, r2_client


logger = logging.getLogger(__name__)
TERMINAL_SUBMISSIONS = ('D', 'CE', 'IE', 'AB')


def upload_release(source_dir, code, version):
    package, manifest_bytes, manifest = build_release(source_dir, code, version)
    client = r2_client()
    bucket = os.environ['R2_PROBLEMS_BUCKET']
    key = manifest['package']
    from botocore.exceptions import ClientError
    try:
        response = client.get_object(Bucket=bucket, Key=key.rsplit('/', 1)[0] + '/manifest.json')
        existing = json.loads(response['Body'].read())
    except ClientError as exc:
        if exc.response.get('Error', {}).get('Code') not in ('NoSuchKey', '404', 'NotFound'):
            raise
    else:
        if any(existing.get(field) != manifest[field] for field in ('sha256', 'code', 'version', 'package')):
            raise AuthoringError('release_conflict', 'Release contents differ from the prepared operation.')
        try:
            body = client.get_object(Bucket=bucket, Key=key)['Body']
        except ClientError as exc:
            if exc.response.get('Error', {}).get('Code') in ('NoSuchKey', '404', 'NotFound'):
                raise AuthoringError('release_conflict', 'Existing release package is unavailable.') from exc
            raise
        digest = hashlib.sha256()
        size = 0
        try:
            for chunk in iter(lambda: body.read(65536), b''):
                size += len(chunk)
                if size > len(package):
                    raise AuthoringError('release_conflict', 'Existing release package exceeds expected size.')
                digest.update(chunk)
        finally:
            body.close()
        if size != len(package) or digest.hexdigest() != manifest['sha256']:
            raise AuthoringError('release_conflict', 'Existing release package checksum does not match.')
        return existing
    client.put_object(Bucket=bucket, Key=key, Body=package, ContentType='application/zip')
    client.put_object(Bucket=bucket, Key=key.rsplit('/', 1)[0] + '/manifest.json', Body=manifest_bytes,
                      ContentType='application/json')
    return manifest


def _operation_paths(operation):
    root = Path(settings.DMOJ_PROBLEM_DATA_ROOT)
    folder = root / '.authoring' / str(operation.pk)
    return folder, folder / 'prepared', root / operation.problem.code, folder / 'backup'


def _cases(operation):
    if operation.config.get('mode') == 'advanced':
        return [ProblemTestCase(dataset=operation.problem, **case) for case in operation.config['cases']]
    return [ProblemTestCase(dataset=operation.problem, type='C', order=case['order'],
                            input_file=case['input_file'], output_file=case['output_file'],
                            points=int(case['points']), is_pretest=case.get('is_pretest', False))
            for case in operation.config['cases']]


def _artifact_digest(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(65536), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_prepared(path, operation):
    marker_path = path / 'operation.json'
    if not marker_path.is_file():
        raise AuthoringError('storage_conflict', 'Prepared data marker is missing.')
    marker = json.loads(marker_path.read_text())
    if marker.get('operation') != str(operation.pk):
        raise AuthoringError('storage_conflict', 'Prepared data belongs to a different operation.')
    names = marker.get('files', ['tests.zip', 'init.yml'])
    if (not isinstance(names, list) or any(not isinstance(name, str) for name in names) or
            len(names) != len(set(names)) or
            {entry.name for entry in path.iterdir()} != set(names) | {'operation.json'}):
        raise AuthoringError('storage_conflict', 'Prepared data inventory does not match.')
    for name in names:
        if (Path(name).name != name or (path / name).is_symlink() or not (path / name).is_file() or
                marker.get(name) != _artifact_digest(path / name)):
            raise AuthoringError('storage_conflict', 'Prepared data checksum does not match.')
    _validate_workspace(path, operation)


def _validate_workspace(path, operation):
    if 'workspace_bytes' in operation.config:
        prepared_bytes = sum(entry.stat().st_size for entry in path.iterdir() if entry.is_file())
        if prepared_bytes > operation.config['workspace_bytes']:
            raise AuthoringError('storage_quota', 'Prepared artifacts exceed the reserved workspace.')


def prepare_data_operation(operation_id):
    operation = ProblemDataOperation.objects.select_related('problem', 'upload').get(pk=operation_id)
    folder, prepared, _, _ = _operation_paths(operation)
    if (prepared / 'operation.json').is_file():
        _validate_prepared(prepared, operation)
        sync_artifact_directory(prepared)
        return
    if prepared.exists():
        shutil.rmtree(prepared)
    prepared.mkdir(parents=True, mode=0o700)
    if operation.config.get('mode') == 'advanced':
        from judge.problem_authoring.advanced import advanced_models
        for name in operation.config['artifacts'].values():
            source = folder / 'snapshot' / name
            if _artifact_digest(source) != operation.config['digests'].get(name):
                raise AuthoringError('invalid_data', 'Data attachment changed before test preparation.')
            shutil.copyfile(source, prepared / name)
        data, cases = advanced_models(operation, prepared)
        files = []
        if data.zipfile:
            with zipfile.ZipFile(prepared / Path(data.zipfile.name).name) as archive:
                files = archive.namelist()
    else:
        source_path = upload_path(operation.upload)
        if _artifact_digest(source_path) != operation.upload.sha256:
            raise AuthoringError('invalid_upload', 'Uploaded archive changed before test preparation.')
        files = [case[key] for case in operation.config['cases'] for key in ('input_file', 'output_file')]
        with zipfile.ZipFile(source_path) as source:
            with zipfile.ZipFile(prepared / 'tests.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
                for name in files:
                    with source.open(operation.config['root'] + name) as incoming, archive.open(name, 'w') as outgoing:
                        shutil.copyfileobj(incoming, outgoing, 65536)
        data = ProblemData(problem=operation.problem, zipfile=operation.problem.code + '/tests.zip',
                           checker=operation.config.get('checker', 'standard'), grader='standard')
        cases = _cases(operation)
    init = ProblemDataCompiler(operation.problem, data, cases, files, persist_cases=False).make_init()
    if not init:
        raise AuthoringError('invalid_tests', 'Empty test configuration.')
    (prepared / 'init.yml').write_text(yaml.safe_dump(init), encoding='utf-8')
    names = sorted(path.name for path in prepared.iterdir() if path.is_file())
    marker = {'operation': str(operation.pk), 'files': names}
    marker.update({name: _artifact_digest(prepared / name) for name in names})
    (prepared / 'operation.json').write_text(json.dumps(marker, sort_keys=True), encoding='utf-8')
    sync_artifact_directory(prepared)
    _validate_workspace(prepared, operation)


def _lock_operation(operation_id):
    problem_id = ProblemDataOperation.objects.values_list('problem_id', flat=True).get(pk=operation_id)
    problem = Problem.objects.select_for_update().get(pk=problem_id)
    state = ProblemAuthoringState.objects.select_for_update().get(problem_id=problem_id)
    operation = ProblemDataOperation.objects.select_for_update().get(pk=operation_id, problem_id=problem_id)
    operation.problem = problem
    return operation, state


def activate_operation(operation_id, manifest=None, *, lease_token=None):
    with transaction.atomic():
        operation, state = _lock_operation(operation_id)
        if operation.state == 'READY':
            return
        if lease_token is not None and (operation.lease_token != lease_token or
                                        operation.lease_until is None or operation.lease_until <= timezone.now()):
            raise AuthoringError('lease_lost', 'Another worker owns this operation or its lease expired.')
        if (operation.problem.is_deleted or state.current_operation_id != operation.pk or
                state.grading_revision != operation.target_revision):
            raise AuthoringError('operation_stale', 'A newer data revision or deletion superseded this operation.')
        if Submission.objects.filter(problem=operation.problem).exclude(status__in=TERMINAL_SUBMISSIONS).exists():
            operation.state = 'WAITING'
            operation.lease_until = None
            operation.save(update_fields=['state', 'lease_until', 'updated'])
            return
        folder, prepared, destination, backup = _operation_paths(operation)
        marker = destination / 'operation.json'
        installed = marker.is_file() and json.loads(marker.read_text()).get('operation') == str(operation.pk)
        _validate_prepared(destination if installed else prepared, operation)
        if 'workspace_bytes' in operation.config:
            source = destination if installed else prepared
            previous = backup if backup.exists() else destination if not installed else None
            total = sum(entry.stat().st_size for entry in source.rglob('*') if entry.is_file())
            if previous and previous.exists():
                total += sum(entry.stat().st_size for entry in previous.rglob('*') if entry.is_file())
            if total > operation.config['workspace_bytes']:
                raise AuthoringError('storage_quota', 'Dataset and backup exceed the reserved workspace.')
        if not installed:
            if destination.exists():
                if state.active_data_revision == 0:
                    raise AuthoringError('storage_conflict', 'An unowned data directory already exists.')
                if backup.exists():
                    raise AuthoringError('storage_conflict', 'Data installation needs reconciliation.')
                os.rename(destination, backup)
                sync_directory(destination.parent)
                sync_directory(folder)
            operation.phase = 'INSTALLING'
            operation.save(update_fields=['phase', 'updated'])
            os.rename(prepared, destination)
        sync_artifact_directory(destination)
        sync_directory(folder)
        ProblemTestCase.objects.filter(dataset=operation.problem).delete()
        ProblemTestCase.objects.bulk_create(_cases(operation))
        data, _ = ProblemData.objects.get_or_create(problem=operation.problem)
        if operation.config.get('mode') == 'advanced':
            from judge.problem_authoring.advanced import DATA_FILE_FIELDS, DATA_SCALAR_FIELDS, advanced_models
            desired, _ = advanced_models(operation, destination)
            for name in DATA_FILE_FIELDS + DATA_SCALAR_FIELDS:
                setattr(data, name, getattr(desired, name))
        else:
            data.zipfile = operation.problem.code + '/tests.zip'
            data.checker = operation.config.get('checker', 'standard')
            data.grader = 'standard'
        data.feedback = ''
        if manifest:
            data.r2_release_version = manifest['version']
            data.r2_release_sha256 = manifest['sha256']
            data.r2_release_key = manifest['package']
            data.r2_released_at = timezone.now()
        else:
            data.r2_release_version = ''
            data.r2_release_sha256 = ''
            data.r2_release_key = ''
            data.r2_released_at = None
        data.save()
        state.active_data_revision = operation.target_revision
        state.data_state = 'READY'
        state.save(update_fields=['active_data_revision', 'data_state'])
        operation.state = 'READY'
        operation.phase = 'COMMITTED'
        operation.safe_error = ''
        operation.lease_until = None
        operation.save()


def retry_data_operation(context, problem_id, *, expected_revision):
    from judge.problem_authoring.policy import authorize_edit
    from judge.tasks.problem_authoring import process_authoring_data

    def enqueue():
        try:
            process_authoring_data.delay(str(operation_id))
        except Exception:
            logger.warning('Data retry %s retained for reconciliation after queue failure', operation_id)

    with transaction.atomic():
        problem = Problem.objects.select_for_update().get(pk=problem_id)
        authorize_edit(context, problem)
        state = ProblemAuthoringState.objects.select_for_update().filter(problem=problem).first()
        if state is None or state.revision != expected_revision:
            raise ConflictError('stale_revision', 'This problem changed. Reload before retrying.')
        if not state.current_operation_id:
            raise AuthoringError('missing_operation', 'There is no test preparation operation to retry.')
        operation = ProblemDataOperation.objects.select_for_update().get(pk=state.current_operation_id)
        if operation.target_revision != state.grading_revision:
            raise ConflictError('stale_revision', 'This operation belongs to older grading data.')
        operation_id = operation.pk
        if operation.state == 'FAILED':
            operation.state = 'PENDING'
            operation.safe_error = ''
            operation.save(update_fields=['state', 'safe_error', 'updated'])
            state.data_state = 'PENDING'
            state.save(update_fields=['data_state'])
            transaction.on_commit(enqueue)
        return operation


def process_data_operation(operation_id):
    import fcntl
    operation = ProblemDataOperation.objects.select_related('problem').get(pk=operation_id)
    folder, _, _, _ = _operation_paths(operation)
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (folder / 'worker.lock').open('a+b') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        try:
            _process_owned_data_operation(operation_id)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _process_owned_data_operation(operation_id):
    token = uuid.uuid4()
    with transaction.atomic():
        operation, state = _lock_operation(operation_id)
        if operation.state == 'READY':
            return
        if (operation.problem.is_deleted or state.current_operation_id != operation.pk or
                state.grading_revision != operation.target_revision):
            operation.state = 'FAILED'
            operation.safe_error = 'A newer data revision superseded this operation.'
            operation.lease_until = None
            operation.save()
            return
        if operation.lease_until and operation.lease_until > timezone.now():
            return
        if Submission.objects.filter(problem=operation.problem).exclude(status__in=TERMINAL_SUBMISSIONS).exists():
            operation.state = 'WAITING'
            operation.save(update_fields=['state', 'updated'])
            return
        operation.lease_token = token
        operation.lease_until = timezone.now() + timedelta(minutes=5)
        operation.attempts += 1
        operation.state = 'INSTALLING'
        operation.save()
    try:
        _, prepared, destination, _ = _operation_paths(operation)
        marker = destination / 'operation.json'
        installed = marker.is_file() and json.loads(marker.read_text()).get('operation') == str(operation.pk)
        if installed:
            _validate_prepared(destination, operation)
            source = destination
        else:
            prepare_data_operation(operation_id)
            source = prepared
        operation.refresh_from_db()
        renewed = ProblemDataOperation.objects.filter(pk=operation_id, lease_token=token).update(
            lease_until=timezone.now() + timedelta(minutes=5),
        )
        if not renewed:
            raise AuthoringError('lease_lost', 'Another worker owns this operation.')
        manifest = None
        if getattr(settings, 'BRIDGED_R2_PROBLEMS', False):
            manifest = upload_release(source, operation.problem.code, 'authoring-' + operation.pk.hex)
        ProblemDataOperation.objects.filter(pk=operation_id, lease_token=token).update(
            lease_until=timezone.now() + timedelta(minutes=5),
        )
        activate_operation(operation_id, manifest, lease_token=token)
    except Exception:
        logger.exception('Authoring data operation failed: %s', operation_id)
        with transaction.atomic():
            current, state = _lock_operation(operation_id)
            if current.lease_token == token and current.state != 'READY':
                current.state = 'FAILED'
                current.safe_error = 'Unable to prepare or synchronize tests. Retry this operation.'
                current.lease_until = None
                current.save()
                ProblemAuthoringState.objects.filter(current_operation=current).update(data_state='FAILED')


def clean_completed_artifacts(*, now, limit=100):
    import fcntl
    from judge.models import Organization, Profile
    retention = timedelta(seconds=getattr(settings, 'PROBLEM_AUTHORING_ARTIFACT_RETENTION', 86400))
    candidates = ProblemDataOperation.objects.filter(state='READY', updated__lte=now - retention).exclude(
        phase='CLEANED',
    ).values_list('pk', flat=True)[:limit]
    cleaned = 0
    for operation_id in list(candidates):
        try:
            operation = ProblemDataOperation.objects.select_related('problem', 'upload').filter(pk=operation_id).first()
            if operation is None:
                continue
            folder, _, _, _ = _operation_paths(operation)
            folder.mkdir(parents=True, exist_ok=True, mode=0o700)
            with (folder / 'worker.lock').open('a+b') as lock:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    continue
                with transaction.atomic():
                    if operation.problem.organization_id:
                        Organization.objects.select_for_update().get(pk=operation.problem.organization_id)
                    owner_id = operation.config.get('owner_id') or (
                        operation.upload.owner_id if operation.upload else None)
                    if owner_id:
                        Profile.objects.select_for_update().get(pk=owner_id)
                    Problem.objects.select_for_update().get(pk=operation.problem_id)
                    operation = ProblemDataOperation.objects.select_for_update().get(pk=operation_id)
                    if (operation.state != 'READY' or operation.updated > now - retention or
                            operation.phase == 'CLEANED'):
                        continue
                    for name in ('snapshot', 'backup', 'prepared'):
                        path = folder / name
                        if path.is_symlink():
                            raise AuthoringError('storage_conflict', 'Retained artifact path is invalid.')
                        if path.exists():
                            shutil.rmtree(path)
                    sync_directory(folder)
                    sync_directory(folder.parent)
                    operation.config['snapshot_bytes'] = 0
                    operation.config['workspace_bytes'] = 0
                    operation.phase = 'CLEANED'
                    operation.save(update_fields=['config', 'phase', 'updated'])
                    cleaned += 1
        except Exception:
            logger.exception('Completed authoring artifact cleanup failed: %s', operation_id)
    return cleaned


def _clean_expired_upload(expired, upload_id):
    import fcntl
    from contextlib import ExitStack
    from judge.models import Profile
    candidate = expired.filter(pk=upload_id).first()
    if candidate is None:
        return False
    path = upload_path(candidate)
    with ExitStack() as locks:
        if candidate.kind == 'PDF' and path.parent.is_dir():
            lock = locks.enter_context((path.parent / 'pdf.lock').open('a+b'))
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return False
        with transaction.atomic():
            Profile.objects.select_for_update().get(pk=candidate.owner_id)
            upload = expired.select_for_update().filter(pk=upload_id).first()
            if upload is None:
                return False
            upload.manifest['cleanup_pending'] = True
            upload.save(update_fields=['manifest'])
        if upload.kind == 'PDF':
            from judge.views.widgets import default_storage
            default_storage.delete(os.path.join(settings.PDF_STATEMENT_UPLOAD_MEDIA_DIR,
                                                'authoring-' + upload.pk.hex + '.pdf'))
        path.unlink(missing_ok=True)
        (path.parent / 'pdf.lock').unlink(missing_ok=True)
        if path.parent.is_dir() and not any(path.parent.iterdir()):
            path.parent.rmdir()
        with transaction.atomic():
            Profile.objects.select_for_update().get(pk=candidate.owner_id)
            upload = expired.select_for_update().filter(pk=upload_id, manifest__cleanup_pending=True).first()
            if upload is None:
                return False
            upload.delete()
        return True


def reconcile_authoring(*, now, limit=100):
    from judge.models import ProblemPackageImport
    ProblemPackageImport.objects.filter(state='JUDGING', submission__status__in=TERMINAL_SUBMISSIONS).update(
        state='FINISHED',
    )
    candidates = ProblemDataOperation.objects.filter(
        state__in=('PENDING', 'INSTALLING', 'PUBLISHING', 'WAITING'),
    ).filter(Q(lease_until__isnull=True) | Q(lease_until__lte=now)).order_by('created')
    processed = 0
    for operation_id in list(candidates.values_list('pk', flat=True)[:limit]):
        try:
            process_data_operation(operation_id)
            processed += 1
        except ProblemDataOperation.DoesNotExist:
            continue
        except Exception:
            logger.exception('Data operation recovery failed: %s', operation_id)
    from judge.models import ProblemReferenceRun
    from judge.problem_authoring.verification import dispatch_verification, refresh_verification
    runs = ProblemReferenceRun.objects.filter(state__in=('PENDING', 'DISPATCHING', 'JUDGING')).order_by('created')
    refreshed = 0
    for run_id in list(runs.values_list('pk', flat=True)[:limit]):
        try:
            run = refresh_verification(run_id)
            if run.state in ('PENDING', 'DISPATCHING', 'JUDGING'):
                dispatch_verification(run_id)
            refreshed += 1
        except Exception:
            logger.exception('Reference verification recovery failed: %s', run_id)
    from judge.models import ProblemAuthoringUpload
    cleaned = 0
    expired = ProblemAuthoringUpload.objects.filter(
        expires_at__lte=now, consumed_by__isnull=True,
        problemdataoperation__isnull=True, problemreferencesource__isnull=True, problemreferencerun__isnull=True,
    ).order_by('created')
    for upload_id in list(expired.values_list('pk', flat=True)[:limit]):
        try:
            cleaned += int(_clean_expired_upload(expired, upload_id))
        except Exception:
            logger.exception('Expired authoring upload cleanup failed: %s', upload_id)
    artifacts = clean_completed_artifacts(now=now, limit=limit)
    return {'processed': processed, 'verifications': refreshed, 'cleaned': cleaned, 'artifacts_cleaned': artifacts}
