import hashlib
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from judge.judgeapi import judge_submission
from judge.models import Problem, ProblemAuthoringState, ProblemReferenceRun, ProblemReferenceSource, \
    Profile, Submission, SubmissionSource
from judge.problem_authoring.policy import assert_can_submit, authorize_edit, context_user
from judge.problem_authoring.storage import upload_path
from judge.problem_authoring.types import AuthoringError


TERMINAL = ('D', 'CE', 'IE', 'AB')


def start_verification(context, problem_id, *, request_token, expected_grading_revision):
    user = context_user(context)
    with transaction.atomic():
        Profile.objects.select_for_update().get(pk=user.profile.pk)
        problem = Problem.objects.select_for_update().get(pk=problem_id)
        authorize_edit(context, problem)
        state = ProblemAuthoringState.objects.select_for_update().filter(problem=problem).first()
        if state is None:
            raise AuthoringError('save_first', 'Save this problem in the shared editor before verification.')
        existing = ProblemReferenceRun.objects.filter(owner=user.profile, request_token=request_token).first()
        if existing:
            if existing.problem_id != problem.pk or existing.grading_revision != expected_grading_revision:
                raise AuthoringError('token_conflict', 'This verification token belongs to a different request.')
            return existing
        if state.grading_revision != expected_grading_revision:
            raise AuthoringError('stale_revision', 'Grading data changed. Reload before verifying.')
        assert_can_submit(problem.pk)
        active_runs = ProblemReferenceRun.objects.filter(
            problem=problem, state__in=('PENDING', 'DISPATCHING', 'JUDGING'),
        )
        if active_runs.exists():
            raise AuthoringError('verification_busy', 'Reference verification is already active.')
        try:
            source = ProblemReferenceSource.objects.select_related('upload', 'language').get(problem=problem)
        except ProblemReferenceSource.DoesNotExist as exc:
            raise AuthoringError('missing_source', 'Attach a reference source and select its runtime first.') from exc
        if not problem.allowed_languages.filter(pk=source.language_id).exists():
            raise AuthoringError('invalid_runtime', 'Reference runtime is not enabled for this problem.')
        try:
            raw = upload_path(source.upload).read_bytes()
            if hashlib.sha256(raw).hexdigest() != source.upload.sha256:
                raise AuthoringError('invalid_source', 'Reference source changed. Upload it again.')
            content = raw.decode('utf-8-sig')
        except (OSError, UnicodeDecodeError) as exc:
            raise AuthoringError('invalid_source', 'Reference source is unavailable. Upload it again.') from exc
        submission = Submission.objects.create(problem=problem, user=user.profile, language=source.language)
        SubmissionSource.objects.create(submission=submission, source=content)
        return ProblemReferenceRun.objects.create(
            problem=problem, owner=user.profile, request_token=request_token,
            grading_revision=state.grading_revision, source_sha256=source.upload.sha256,
            upload=source.upload, language=source.language, submission=submission,
        )


def _lock_run(run_id):
    problem_id = ProblemReferenceRun.objects.values_list('problem_id', flat=True).get(pk=run_id)
    problem = Problem.objects.select_for_update().get(pk=problem_id)
    state = ProblemAuthoringState.objects.select_for_update().get(problem_id=problem_id)
    run = ProblemReferenceRun.objects.select_for_update().get(pk=run_id, problem_id=problem_id)
    run.problem = problem
    if run.submission_id:
        run.submission = Submission.objects.select_for_update().get(pk=run.submission_id)
    return run, state


def _fail_missing_submission(run):
    run.state = 'FAILED'
    run.safe_error = 'Verification submission is unavailable. Start a new verification.'
    run.save(update_fields=['state', 'safe_error', 'updated'])


def refresh_verification(run_id):
    with transaction.atomic():
        run, _ = _lock_run(run_id)
        if run.submission_id is None:
            _fail_missing_submission(run)
        elif run.submission.status in TERMINAL:
            run.state = 'FAILED' if run.submission.status == 'IE' else 'FINISHED'
            run.safe_error = 'Judge infrastructure failed. Retry this verification.' if run.state == 'FAILED' else ''
            run.save(update_fields=['state', 'safe_error', 'updated'])
        return run


def dispatch_verification(run_id):
    with transaction.atomic():
        run, state = _lock_run(run_id)
        if run.submission_id is None:
            _fail_missing_submission(run)
            return
        if run.state == 'FINISHED':
            return
        if run.state == 'JUDGING' and run.updated > timezone.now() - timedelta(minutes=5):
            return
        if run.submission.status in TERMINAL:
            refresh_verification(run.pk)
            return
        if run.submission.status in ('P', 'G'):
            run.state = 'JUDGING'
            run.save(update_fields=['state', 'updated'])
            return
        if state.grading_revision != run.grading_revision:
            raise AuthoringError('stale_revision', 'Verification does not match the current grading data.')
        assert_can_submit(run.problem_id, existing_submission_id=run.submission_id)
        if run.state == 'DISPATCHING':
            if run.updated > timezone.now() - timedelta(minutes=5):
                return
        run.state = 'DISPATCHING'
        run.save(update_fields=['state', 'updated'])
        submission = run.submission
    sent = judge_submission(submission)
    with transaction.atomic():
        run, _ = _lock_run(run_id)
        run.submission.refresh_from_db()
        if run.submission.status in ('D', 'CE', 'AB'):
            run.state = 'FINISHED'
        elif run.submission.status in ('P', 'G'):
            run.state = 'JUDGING'
        elif not sent and run.submission.status == 'QU':
            run.state = 'DISPATCHING'
        else:
            run.state = 'JUDGING' if sent and run.submission.status != 'IE' else 'FAILED'
        run.safe_error = '' if run.state != 'FAILED' else 'Judge dispatch failed. Retry this verification.'
        run.save(update_fields=['state', 'safe_error', 'updated'])


def retry_verification(context, run_id):
    with transaction.atomic():
        run, state = _lock_run(run_id)
        authorize_edit(context, run.problem)
        if run.submission_id is None:
            raise AuthoringError('missing_submission', 'Submission is unavailable. Start a new verification.')
        if state.grading_revision != run.grading_revision:
            raise AuthoringError('stale_revision', 'Start a new verification for the current grading data.')
        if run.state == 'FAILED':
            run.state = 'PENDING'
            run.safe_error = ''
            Submission.objects.filter(pk=run.submission_id, status='IE').update(status='QU', result=None)
            run.save(update_fields=['state', 'safe_error', 'updated'])
        return run
