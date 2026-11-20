import hashlib
import json
from dataclasses import asdict
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from reversion import revisions

from judge.models import Language, LanguageLimit, Organization, Problem, ProblemAuthoringSave, ProblemAuthoringState, \
    ProblemDataOperation, ProblemReferenceSource, Profile, Solution
from judge.problem_authoring.policy import authorize_create, authorize_edit, context_user
from judge.problem_authoring.revisions import manages_revision
from judge.problem_authoring.types import AuthoringError, ConflictError, SaveResult
from judge.problem_authoring.uploads import get_upload


PROBLEM_FIELDS = {
    'code', 'name', 'description', 'group_id', 'time_limit', 'memory_limit', 'points', 'partial', 'source',
    'submission_source_visibility_mode', 'testcase_visibility_mode', 'pdf_url',
}
RELATIONS = {'types', 'tags', 'testers', 'allowed_languages'}
GRADING_FIELDS = {'code', 'time_limit', 'memory_limit', 'partial', 'allowed_languages'}
ACTIVE_OPERATIONS = {'PENDING', 'INSTALLING', 'PUBLISHING', 'WAITING', 'FAILED'}


def grading_fields_changed(before, after):
    for key, value in after.items():
        if key == 'allowed_languages':
            if set(before.get(key, [])) != set(value):
                return True
        elif key in GRADING_FIELDS and before.get(key) != value:
            return True
    return False


def _fingerprint(context, changes, problem_id, expected_revision):
    payload = {'context': asdict(context), 'changes': asdict(changes),
               'problem': problem_id, 'revision': expected_revision}
    encoded = json.dumps(payload, sort_keys=True, default=lambda value: sorted(value) if isinstance(
        value, (set, frozenset)) else str(value), separators=(',', ':'))
    return hashlib.sha256(encoded.encode()).hexdigest()


def _save_result(saved):
    return SaveResult(saved.problem_id, saved.revision, saved.operation_id)


def _validate_fields(context, user, changes, problem):
    fields = changes.problem_fields
    if set(fields) - PROBLEM_FIELDS - RELATIONS:
        raise AuthoringError('invalid_fields', 'One or more fields cannot be changed here.')
    if context.organization_id:
        organization = Organization.objects.get(pk=context.organization_id)
        prefix = ''.join(char for char in organization.slug.lower() if char.isalnum()) + '_'
        if not fields.get('code', problem.code).startswith(prefix):
            raise AuthoringError('invalid_code', 'Organization problem code must start with ' + prefix, 'code')
    if 'pdf_url' in fields and not user.has_perm('judge.upload_file_statement'):
        raise AuthoringError('permission_denied', 'You do not have permission to upload PDF statements.')
    if ('time_limit' in fields and fields['time_limit'] > settings.VNOJ_PROBLEM_TIMELIMIT_LIMIT and
            not user.has_perm('judge.high_problem_timelimit')):
        raise AuthoringError('invalid_limit', 'Time limit exceeds your permitted limit.', 'time_limit')
    if context.organization_id and 'tags' in fields:
        from judge.models import OrganizationProblemTag
        if OrganizationProblemTag.objects.filter(pk__in=fields['tags']).exclude(
                organization_id=context.organization_id).exists():
            raise AuthoringError('invalid_tags', 'Tags must belong to this organization.')
    if not context.organization_id and fields.get('tags'):
        raise AuthoringError('invalid_tags', 'Organization tags are unavailable for global problems.')
    for name in RELATIONS & fields.keys():
        model = Problem._meta.get_field(name).related_model
        identifiers = set(fields[name])
        if model.objects.filter(pk__in=identifiers).count() != len(identifiers):
            raise AuthoringError('invalid_relation', 'One or more selected ' + name + ' no longer exist.', name)


def _data_config(user, upload, changes):
    expected = upload.manifest['tests']
    cases = [asdict(case) for case in changes.cases] if changes.cases is not None else expected
    if not cases:
        raise AuthoringError('invalid_tests', 'Select at least one input/output pair.')
    if len(cases) > settings.VNOJ_TESTCASE_HARD_LIMIT and not user.has_perm('judge.create_mass_testcases'):
        raise AuthoringError('too_many_tests', 'Too many test cases for your permissions.')
    if len(cases) > 4998:
        raise AuthoringError('too_many_tests', 'Too many test cases for safe processing.')
    valid_pairs = {(case['input_file'], case['output_file']) for case in expected}
    seen = set()
    normalized = []
    for index, case in enumerate(cases, 1):
        pair = case['input_file'], case['output_file']
        points = Decimal(str(changes.data_fields.get('test_points', case['points'])))
        if (pair not in valid_pairs or pair in seen or not points.is_finite() or points < 0 or
                points != points.to_integral_value()):
            raise AuthoringError('invalid_tests', 'Invalid testcase pair or points.')
        seen.add(pair)
        normalized.append(dict(input_file=pair[0], output_file=pair[1], order=index,
                               points=str(points), is_pretest=bool(case.get('is_pretest', False))))
    if not any(Decimal(case['points']) > 0 for case in normalized):
        raise AuthoringError('invalid_tests', 'At least one testcase must have positive points.')
    from judge.models import CHECKERS
    checker = changes.data_fields.get('checker') or 'standard'
    if checker not in {key for key, _ in CHECKERS if key != 'bridged'}:
        raise AuthoringError('invalid_checker', 'Select a supported standard checker.')
    return {'cases': normalized, 'root': upload.manifest['fields']['root'],
            'checker': checker, 'grader': 'standard'}


def _validate_solution(user, problem, fields):
    if fields is None:
        return
    solution = Solution.objects.filter(problem=problem).first() if problem.pk else None
    solution = solution or Solution(problem=problem, content='', publish_on=timezone.now())
    if 'is_public' in fields and bool(fields['is_public']) != solution.is_public:
        if not user.has_perm('judge.change_public_visibility'):
            raise AuthoringError('permission_denied', 'You do not have permission to publish editorials.')
    if 'authors' in fields:
        author_ids = set(fields['authors'])
        if Profile.objects.filter(pk__in=author_ids).count() != len(author_ids):
            raise AuthoringError('invalid_authors', 'Selected editorial authors no longer exist.')
    for key in ('content', 'publish_on'):
        if key in fields:
            setattr(solution, key, fields[key])
    solution.full_clean(exclude=['problem', 'content'] if not solution.content.strip() else ['problem'])


def _enqueue_data(operation_id):
    from judge.tasks.problem_authoring import process_authoring_data
    try:
        process_authoring_data.delay(str(operation_id))
    except Exception:
        import logging
        logging.getLogger(__name__).warning('Data operation %s retained for recovery after queue failure', operation_id)


class _PdfPublicationRequired(Exception):
    pass


def save_draft(context, changes, *, problem_id, expected_revision, request_token):
    options = dict(problem_id=problem_id, expected_revision=expected_revision, request_token=request_token)
    try:
        return _save_draft(context, changes, **options)
    except _PdfPublicationRequired:
        from judge.problem_authoring.uploads import publish_staged_pdf
        publish_staged_pdf(context, changes.pdf_upload_id, problem_id=problem_id)
        return _save_draft(context, changes, **options)


@manages_revision
def _save_draft(context, changes, *, problem_id, expected_revision, request_token):
    user = context_user(context)
    fingerprint = _fingerprint(context, changes, problem_id, expected_revision)
    try:
        with transaction.atomic(), revisions.create_revision(atomic=False):
            if context.organization_id:
                organization = Organization.objects.select_for_update().get(pk=context.organization_id)
            else:
                organization = None
            Profile.objects.select_for_update().get(pk=user.profile.pk)
            previous = ProblemAuthoringSave.objects.filter(actor=user.profile, request_token=request_token).first()
            if previous:
                if previous.payload_sha256 != fingerprint:
                    raise ConflictError('token_conflict', 'This save token was already used for different changes.')
                if problem_id is None:
                    authorize_create(context)
                else:
                    authorize_edit(context, previous.problem)
                return _save_result(previous)
            creating = problem_id is None
            if creating:
                authorize_create(context)
                if organization and getattr(settings, 'VNOJ_QUOTA_ENFORCEMENT_ENABLED', False):
                    if not organization.can_create_problem():
                        raise AuthoringError('problem_quota', 'Organization problem limit has been reached.')
                problem = Problem(is_public=False, organization=organization,
                                  is_organization_private=organization is not None, date=timezone.now())
                state = None
            else:
                problem = Problem.objects.select_for_update().get(pk=problem_id)
                authorize_edit(context, problem)
                state = ProblemAuthoringState.objects.select_for_update().filter(problem=problem).first()
                if state is None:
                    from judge.models import ProblemData
                    data = ProblemData.objects.filter(problem=problem).first()
                    ready = bool(data and data.has_yml() and problem.cases.exists())
                    if getattr(settings, 'BRIDGED_R2_PROBLEMS', False):
                        ready = ready and bool(data.r2_release_version and data.r2_release_sha256)
                    state = ProblemAuthoringState.objects.create(
                        problem=problem, data_state='READY' if ready else 'MISSING',
                        active_data_revision=1 if ready else 0,
                    )
                if expected_revision != state.revision:
                    raise ConflictError('stale_revision', 'This problem changed in another tab. Reload before saving.')
            _validate_fields(context, user, changes, problem)
            before = {key: getattr(problem, key) for key in GRADING_FIELDS - RELATIONS}
            before['allowed_languages'] = (
                list(problem.allowed_languages.values_list('pk', flat=True)) if problem.pk else []
            )
            existing_reference = ProblemReferenceSource.objects.filter(problem=problem).first() if problem.pk else None
            runtime_changed = (changes.reference_language_id is not None and
                               (existing_reference is None or
                                existing_reference.language_id != changes.reference_language_id))
            grading_changed = (creating or grading_fields_changed(before, changes.problem_fields) or
                               changes.test_upload_id is not None or changes.reference_upload_id is not None or
                               runtime_changed)
            if changes.language_limits is not None:
                current_limits = list(problem.language_limits.order_by('language_id').values(
                    'language_id', 'time_limit', 'memory_limit',
                )) if problem.pk else []
                grading_changed = grading_changed or current_limits != sorted(
                    changes.language_limits, key=lambda value: value['language_id'],
                )
            if not creating and grading_changed:
                from judge.utils.problem_package_guards import assert_package_mutable
                assert_package_mutable(problem.pk)
            if state and grading_changed and state.current_operation_id:
                operation = state.current_operation
                if operation.state in ACTIVE_OPERATIONS:
                    raise AuthoringError('data_busy',
                                         'Wait for test preparation to finish or retry the failed operation.')
            if state and grading_changed and problem.reference_runs.filter(
                    state__in=('PENDING', 'DISPATCHING', 'JUDGING')).exists():
                raise AuthoringError('verification_busy',
                                     'Wait for reference verification before changing grading data.')
            upload = None
            config = None
            if changes.test_upload_id:
                from judge.models import ProblemAuthoringUpload, ProblemData
                advanced = (ProblemData.objects.filter(problem=problem).exclude(grader='standard')
                            if problem.pk else None)
                from django.db.models import Q
                custom_data = ProblemData.objects.filter(problem=problem).filter(
                    Q(checker='bridged') | ~Q(checker_args='') | ~Q(grader_args='') |
                    ~Q(generator='') & Q(generator__isnull=False) |
                    ~Q(custom_checker='') & Q(custom_checker__isnull=False),
                ).exists() if problem.pk else False
                complex_cases = problem.cases.filter(
                    ~Q(type='C') | ~Q(checker='') | ~Q(checker_args='') | ~Q(generator_args='') |
                    Q(output_prefix__isnull=False) | Q(output_limit__isnull=False),
                ).exists() if problem.pk else False
                if (advanced is not None and advanced.exists()) or custom_data or complex_cases:
                    raise AuthoringError('advanced_data',
                                         'Use the advanced data editor to replace this problem dataset.')
                kind = ProblemAuthoringUpload.objects.filter(
                    pk=changes.test_upload_id,
                ).values_list('kind', flat=True).first()
                if kind not in ('TESTS', 'PACKAGE'):
                    raise AuthoringError('invalid_upload', 'Select a testcase upload.')
                upload = get_upload(context, changes.test_upload_id, kind=kind, for_consumption=True,
                                    problem_id=problem_id)
                config = _data_config(user, upload, changes)
                from judge.problem_authoring.quota import reserve_upload_bytes
                previous_bytes = (ProblemData.objects.filter(problem=problem).values_list('zipfile_size', flat=True)
                                  .first() or 0) if problem.pk else 0
                workspace_bytes = upload.expanded_size + len(config['cases']) * 4096 + 1024**2 + previous_bytes
                reserve_upload_bytes(context, workspace_bytes, problem_id)
                config.update(workspace_bytes=workspace_bytes, owner_id=user.profile.pk)
            reference_upload = None
            language = None
            if changes.reference_upload_id:
                reference_upload = get_upload(context, changes.reference_upload_id, kind='SOURCE',
                                              for_consumption=True, problem_id=problem_id)
                language = Language.objects.filter(pk=changes.reference_language_id).first()
                allowed = changes.problem_fields.get('allowed_languages')
                if not language or (allowed is not None and language.pk not in allowed) or (
                        not creating and allowed is None and
                        not problem.allowed_languages.filter(pk=language.pk).exists()):
                    raise AuthoringError('invalid_runtime', 'Select an allowed runtime for the reference source.')
            if runtime_changed and reference_upload is None:
                if existing_reference is None:
                    raise AuthoringError('missing_source', 'Attach a reference source before choosing its runtime.')
                language = Language.objects.filter(pk=changes.reference_language_id).first()
                allowed = changes.problem_fields.get('allowed_languages')
                if not language or (allowed is not None and language.pk not in allowed) or (
                        allowed is None and not problem.allowed_languages.filter(pk=language.pk).exists()):
                    raise AuthoringError('invalid_runtime', 'Select an allowed runtime for the reference source.')
                existing_reference.language = language
                existing_reference.save(update_fields=['language'])
            for key, value in changes.problem_fields.items():
                if key in PROBLEM_FIELDS:
                    setattr(problem, key, value)
            problem.full_clean(exclude=['deleted_at'])
            _validate_solution(user, problem, changes.solution_fields)
            limits = []
            if changes.language_limits is not None:
                seen_languages = set()
                for values in changes.language_limits:
                    language_id = values['language_id']
                    if language_id in seen_languages:
                        raise AuthoringError('invalid_limits', 'Specify each language limit only once.')
                    seen_languages.add(language_id)
                    limit = LanguageLimit(problem=problem, **values)
                    limit.full_clean(exclude=['problem'], validate_unique=False, validate_constraints=False)
                    if (limit.time_limit and limit.time_limit > settings.VNOJ_PROBLEM_TIMELIMIT_LIMIT and
                            not user.has_perm('judge.high_problem_timelimit')):
                        raise AuthoringError('invalid_limits', 'Language time limit exceeds your permitted limit.')
                    limits.append(limit)
            pdf_upload = None
            if changes.pdf_upload_id:
                pdf_upload = get_upload(context, changes.pdf_upload_id, kind='PDF', for_consumption=True,
                                        problem_id=problem_id)
                url = pdf_upload.manifest.get('published_url')
                if not url:
                    raise _PdfPublicationRequired()
                problem.pdf_url = url
            problem.full_clean(exclude=['deleted_at'])
            problem.save()
            for key in RELATIONS & changes.problem_fields.keys():
                getattr(problem, key).set(changes.problem_fields[key])
            if creating:
                problem.authors.add(user.profile)
                problem.curators.add(user.profile)
                if 'allowed_languages' not in changes.problem_fields:
                    problem.allowed_languages.set(Language.objects.filter(include_in_problem=True))
                state = ProblemAuthoringState.objects.create(problem=problem)
            if changes.language_limits is not None:
                for limit in limits:
                    limit.problem = problem
                problem.language_limits.all().delete()
                LanguageLimit.objects.bulk_create(limits)
            if pdf_upload:
                pdf_upload.consumed_by = problem
                pdf_upload.save(update_fields=['consumed_by'])
            if reference_upload:
                if not problem.allowed_languages.filter(pk=language.pk).exists():
                    raise AuthoringError('invalid_runtime', 'Reference runtime must be enabled for this problem.')
                reference_upload.consumed_by = problem
                reference_upload.save(update_fields=['consumed_by'])
                ProblemReferenceSource.objects.update_or_create(problem=problem, defaults={
                    'upload': reference_upload, 'language': language,
                })
            if changes.solution_fields is not None:
                solution, _ = Solution.objects.get_or_create(problem=problem, defaults={
                    'content': '', 'is_public': False, 'publish_on': timezone.now(),
                })
                if 'is_public' in changes.solution_fields and bool(changes.solution_fields['is_public']) != (
                        solution.is_public):
                    if not user.has_perm('judge.change_public_visibility'):
                        raise AuthoringError('permission_denied', 'You do not have permission to publish editorials.')
                    solution.is_public = bool(changes.solution_fields['is_public'])
                for key in ('content', 'publish_on'):
                    if key in changes.solution_fields:
                        setattr(solution, key, changes.solution_fields[key])
                if not solution.content.strip():
                    solution.is_public = False
                solution.full_clean(exclude=['content'] if not solution.content.strip() else None)
                solution.save()
                if 'authors' in changes.solution_fields:
                    author_ids = set(changes.solution_fields['authors'])
                    if Profile.objects.filter(pk__in=author_ids).count() != len(author_ids):
                        raise AuthoringError('invalid_authors', 'Selected editorial authors no longer exist.')
                    solution.authors.set(author_ids)
                else:
                    solution.authors.add(user.profile)
            state.revision += 1
            if grading_changed:
                state.grading_revision += 1
            operation = None
            if upload:
                upload.consumed_by = problem
                upload.save(update_fields=['consumed_by'])
                operation = ProblemDataOperation.objects.create(problem=problem, upload=upload, config=config,
                                                                target_revision=state.grading_revision)
                state.current_operation = operation
                state.data_state = 'PENDING'
            state.save()
            saved = ProblemAuthoringSave.objects.create(actor=user.profile, request_token=request_token,
                                                        payload_sha256=fingerprint, problem=problem,
                                                        revision=state.revision, operation=operation)
            revisions.set_user(user)
            revisions.set_comment('Saved using the shared problem editor')
            if operation:
                transaction.on_commit(lambda: _enqueue_data(operation.pk))
            return _save_result(saved)
    except ValidationError as exc:
        raise AuthoringError('invalid_problem', '; '.join(exc.messages)) from exc
    except Problem.DoesNotExist as exc:
        raise AuthoringError('permission_denied', 'Problem is unavailable.') from exc
