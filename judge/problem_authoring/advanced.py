import hashlib
import shutil
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from judge.models import Organization, Problem, ProblemAuthoringState, ProblemData, ProblemDataOperation, \
    ProblemTestCase, Profile
from judge.problem_authoring.packages import inspect_data_archive
from judge.problem_authoring.policy import assert_mutation_allowed, authorize_edit, context_user
from judge.problem_authoring.quota import reserve_upload_bytes
from judge.problem_authoring.storage import sync_artifact_directory
from judge.problem_authoring.types import AuthoringError
from judge.utils.problem_data import ProblemDataCompiler, ProblemDataError


DATA_FILE_FIELDS = ('zipfile', 'generator', 'custom_checker', 'custom_grader', 'custom_header')
DATA_SCALAR_FIELDS = ('output_prefix', 'output_limit', 'checker', 'grader', 'unicode', 'nobigmath',
                      'checker_args', 'grader_args')
CASE_FIELDS = ('order', 'type', 'input_file', 'output_file', 'points', 'is_pretest', 'generator_args',
               'output_prefix', 'output_limit', 'checker', 'checker_args')


def begin_external_data_change(context, problem_id, *, expected_revision, data, cases, files):
    staged = []
    try:
        return _stage_external_data(context, problem_id, expected_revision=expected_revision,
                                    data=data, cases=cases, files=files, staged=staged)
    except Exception:
        for folder in staged:
            shutil.rmtree(folder, ignore_errors=True)
        raise


def _stage_external_data(context, problem_id, *, expected_revision, data, cases, files, staged):
    try:
        data.full_clean(exclude=[*DATA_FILE_FIELDS, 'feedback'], validate_unique=False, validate_constraints=False)
        for case in cases:
            case.full_clean(exclude=['dataset'])
    except ValidationError as exc:
        raise AuthoringError('invalid_data', '; '.join(exc.messages)) from exc
    total = 0
    limit = getattr(settings, 'PROBLEM_AUTHORING_UPLOAD_LIMIT', 100 * 1024**2)
    for incoming in files.values():
        if incoming is not None and incoming is not False:
            total += incoming.size
    if total > limit:
        raise AuthoringError('upload_too_large', 'Data attachments exceed the upload limit.')
    with transaction.atomic():
        if context.organization_id:
            Organization.objects.select_for_update().get(pk=context.organization_id)
        user = context_user(context)
        Profile.objects.select_for_update().get(pk=user.profile.pk)
        copied_bytes = sum(getattr(data, name).size for name in DATA_FILE_FIELDS
                           if files.get(name) is None and getattr(data, name))
        previous_bytes = (ProblemData.objects.filter(problem_id=problem_id)
                          .values_list('zipfile_size', flat=True).first() or 0)
        workspace_bytes = total + copied_bytes + len(cases) * 4096 + 1024**2 + previous_bytes
        reserve_upload_bytes(context, total + copied_bytes + workspace_bytes, problem_id)
        problem = Problem.objects.select_for_update().get(pk=problem_id)
        authorize_edit(context, problem)
        assert_mutation_allowed(problem.pk, {'tests'})
        state = ProblemAuthoringState.objects.select_for_update().filter(problem=problem).first()
        if state is None:
            state = ProblemAuthoringState.objects.create(
                problem=problem, active_data_revision=1 if data.pk else 0,
                data_state='READY' if data.pk else 'MISSING',
            )
        if state.revision != expected_revision:
            raise AuthoringError('stale_revision', 'Problem changed. Reload the data editor before saving.')
        config = {'mode': 'advanced', 'data': {name: getattr(data, name) for name in DATA_SCALAR_FIELDS},
                  'cases': [{name: getattr(case, name) for name in CASE_FIELDS} for case in cases],
                  'artifacts': {}, 'digests': {}, 'snapshot_bytes': 0, 'workspace_bytes': workspace_bytes,
                  'owner_id': user.profile.pk}
        operation = ProblemDataOperation.objects.create(problem=problem, target_revision=state.grading_revision + 1)
        folder = Path(settings.DMOJ_PROBLEM_DATA_ROOT) / '.authoring' / str(operation.pk) / 'snapshot'
        folder.mkdir(parents=True, mode=0o700)
        staged.append(folder.parent)
        for name in DATA_FILE_FIELDS:
            incoming = files.get(name)
            stored = getattr(data, name)
            if incoming is False:
                continue
            if incoming is None and not stored:
                continue
            filename = Path(incoming.name if incoming is not None else stored.name).name
            if filename in ('', '.', '..', 'init.yml', 'operation.json'):
                raise AuthoringError('invalid_data', 'Attachment file name is reserved.')
            if filename in config['artifacts'].values():
                raise AuthoringError('invalid_data', 'Data attachments must have distinct file names.')
            destination = folder / filename
            expected_size = incoming.size if incoming is not None else stored.size
            source = incoming if incoming is not None else stored.open('rb')
            try:
                source.seek(0)
                size = 0
                with destination.open('xb') as target:
                    for chunk in iter(lambda: source.read(65536), b''):
                        size += len(chunk)
                        if size > expected_size:
                            raise AuthoringError('invalid_data', 'Attachment size changed while staging.')
                        target.write(chunk)
                if size != expected_size:
                    raise AuthoringError('invalid_data', 'Attachment size changed while staging.')
            finally:
                if incoming is None:
                    source.close()
            config['artifacts'][name] = filename
            digest = hashlib.sha256()
            with destination.open('rb') as source:
                for chunk in iter(lambda: source.read(65536), b''):
                    digest.update(chunk)
            config['digests'][filename] = digest.hexdigest()
            config['snapshot_bytes'] += destination.stat().st_size
        operation.config = config
        desired, desired_cases = advanced_models(operation, folder)
        names = inspect_data_archive(folder / config['artifacts']['zipfile']) if desired.zipfile else []
        try:
            init = ProblemDataCompiler(problem, desired, desired_cases, names, persist_cases=False).make_init()
        except (ProblemDataError, ValueError, AttributeError, TypeError) as exc:
            raise AuthoringError('invalid_data', 'Invalid testcase, checker, or grader configuration.') from exc
        if not init:
            raise AuthoringError('invalid_data', 'At least one testcase is required.')
        config['cases'] = [{name: getattr(case, name) for name in CASE_FIELDS} for case in desired_cases]
        sync_artifact_directory(folder)
        operation.save(update_fields=['config'])
        state.revision += 1
        state.grading_revision += 1
        state.data_state = 'PENDING'
        state.current_operation = operation
        state.save()
        from judge.problem_authoring.service import _enqueue_data
        transaction.on_commit(lambda: _enqueue_data(operation.pk))
        return operation.pk


def advanced_models(operation, source_dir):
    config = operation.config
    data = ProblemData(problem=operation.problem, **config['data'])
    for field, name in config['artifacts'].items():
        setattr(data, field, operation.problem.code + '/' + name)
    cases = [ProblemTestCase(dataset=operation.problem, **case) for case in config['cases']]
    return data, cases
