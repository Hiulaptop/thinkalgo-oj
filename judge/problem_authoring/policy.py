from django.contrib.auth import get_user_model
from django.db import transaction

from judge.models import Organization, Problem, ProblemAuthoringState, ProblemDataOperation, ProblemReferenceRun
from judge.problem_authoring.revisions import manages_revision
from judge.problem_authoring.types import AuthoringError


def context_user(context):
    try:
        user = get_user_model().objects.get(pk=context.user_id, is_active=True)
    except get_user_model().DoesNotExist as exc:
        raise AuthoringError('permission_denied', 'You are not allowed to manage this problem.') from exc
    return user


def context_organization(context, user):
    if context.organization_id is None:
        return None
    try:
        organization = Organization.objects.get(pk=context.organization_id)
    except Organization.DoesNotExist as exc:
        raise AuthoringError('permission_denied', 'Organization is unavailable.') from exc
    if not (organization.is_admin(user.profile) or user.has_perm('judge.edit_all_organization')):
        raise AuthoringError('permission_denied', 'You are not allowed to manage this organization.')
    return organization


def authorize_create(context):
    user = context_user(context)
    organization = context_organization(context, user)
    permission = 'judge.create_organization_problem' if organization else 'judge.add_problem'
    if not user.has_perm(permission) or not user.has_perm('judge.edit_own_problem'):
        raise AuthoringError('permission_denied',
                             'Creating a problem requires creation and own-problem editing rights.')


def authorize_edit(context, problem):
    user = context_user(context)
    if (problem.is_deleted or problem.organization_id != context.organization_id or
            not problem.is_editable_by(user)):
        raise AuthoringError('permission_denied', 'You are not allowed to edit this problem in this scope.')


GRADING_FIELDS = {
    'code', 'time_limit', 'memory_limit', 'partial', 'allowed_languages',
    'tests', 'checker', 'grader', 'reference_source', 'reference_language', 'language_limits',
}
ACTIVE_DATA_STATES = ('PENDING', 'INSTALLING', 'PUBLISHING', 'WAITING', 'FAILED')
ACTIVE_RUN_STATES = ('PENDING', 'DISPATCHING', 'JUDGING')


def assert_can_submit(problem_id, *, existing_submission_id=None):
    state = ProblemAuthoringState.objects.filter(problem_id=problem_id).first()
    if state is None:
        return
    operation = state.current_operation
    pending = operation is not None and operation.state in ACTIVE_DATA_STATES
    if existing_submission_id is not None and state.active_data_revision > 0 and pending:
        from judge.models import Submission
        existing = Submission.objects.filter(pk=existing_submission_id, problem_id=problem_id).first()
        if existing and existing.status not in ('D', 'CE', 'IE', 'AB'):
            return
    if state.data_state != 'READY' or pending:
        raise AuthoringError('data_not_ready', 'Test data is not ready. Finish preparation before submitting.')


def assert_can_attach_to_contest(problem_id):
    assert_can_submit(problem_id)


def assert_mutation_allowed(problem_id, changed_fields):
    if not GRADING_FIELDS.intersection(changed_fields):
        return
    from judge.models import ProblemPackageImport
    if ProblemPackageImport.objects.filter(
            problem_id=problem_id, state__in=('PUBLISHING', 'SUBMITTING', 'JUDGING')).exists():
        raise AuthoringError('verification_busy', 'Legacy ZIP reference verification is active. Wait for it to finish.')
    current_ids = ProblemAuthoringState.objects.filter(problem_id=problem_id).values('current_operation_id')
    if ProblemDataOperation.objects.filter(pk__in=current_ids, state__in=ACTIVE_DATA_STATES).exists():
        raise AuthoringError('data_busy', 'Test preparation is active. Grading settings cannot change yet.')
    if ProblemReferenceRun.objects.filter(problem_id=problem_id, state__in=ACTIVE_RUN_STATES).exists():
        raise AuthoringError('verification_busy',
                             'Reference verification is active. Grading settings cannot change yet.')


@manages_revision
def publish_problem(context, problem_id, *, expected_revision, accept_unverified):
    with transaction.atomic():
        problem = Problem.objects.select_for_update().get(pk=problem_id)
        authorize_edit(context, problem)
        user = context_user(context)
        if not user.has_perm('judge.change_public_visibility'):
            raise AuthoringError('permission_denied', 'You do not have permission to publish this problem.')
        state = ProblemAuthoringState.objects.select_for_update().filter(problem=problem).first()
        if state and state.revision != expected_revision:
            raise AuthoringError('stale_revision', 'This problem changed. Reload before publishing.')
        assert_can_submit(problem_id)
        if not problem.description.strip() and not problem.pdf_url:
            raise AuthoringError('missing_statement', 'Add a statement before publishing.')
        verified = state and ProblemReferenceRun.objects.filter(
            problem=problem, grading_revision=state.grading_revision, state='FINISHED', submission__result='AC',
        ).exists()
        if not verified and not accept_unverified:
            raise AuthoringError('confirm_unverified', 'Confirm publishing without a current accepted verification.')
        problem.full_clean(exclude=['deleted_at'])
        problem.is_public = True
        problem.save(update_fields=['is_public'])
        if state:
            state.revision += 1
            state.save(update_fields=['revision'])
            return state.revision
        return 0
