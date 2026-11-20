import importlib.util
import io
import uuid
from unittest.mock import patch

from django.test import TestCase

from judge.models import ProblemAuthoringState, ProblemReferenceSource, Submission
from judge.problem_authoring.types import AuthoringContext, AuthoringError
from judge.problem_authoring.uploads import receive_upload
from judge.tests.authoring_helpers import AuthoringTestMixin


class AuthoringVerificationTest(AuthoringTestMixin, TestCase):
    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('judge.problem_authoring.verification'),
                             'Independent reference verification is missing')
        from judge.problem_authoring import verification
        return verification

    def reference(self, ready=True):
        problem = self.make_problem()
        problem.authors.add(self.user.profile)
        problem.allowed_languages.add(self.language)
        state = ProblemAuthoringState.objects.create(problem=problem, revision=1, grading_revision=1,
                                                     active_data_revision=1, data_state='READY' if ready else 'MISSING')
        upload = receive_upload(AuthoringContext(self.user.pk), io.BytesIO(b'int main() {}'), 'SOURCE')
        upload.consumed_by = problem
        upload.save()
        ProblemReferenceSource.objects.create(problem=problem, upload=upload, language=self.language)
        return problem, state

    def test_start_is_idempotent_and_dispatch_reuses_submission(self):
        problem, state = self.reference()
        token = uuid.uuid4()
        api = self.api()
        run = api.start_verification(AuthoringContext(self.user.pk), problem.pk,
                                     request_token=token, expected_grading_revision=1)
        duplicate = api.start_verification(AuthoringContext(self.user.pk), problem.pk,
                                           request_token=token, expected_grading_revision=1)
        self.assertEqual(run.pk, duplicate.pk)
        self.assertEqual(Submission.objects.filter(problem=problem).count(), 1)
        with patch('judge.problem_authoring.verification.judge_submission', return_value=True):
            api.dispatch_verification(run.pk)
            api.dispatch_verification(run.pk)
        run.refresh_from_db()
        self.assertEqual(run.state, 'JUDGING')
        self.assertEqual(run.submission.source.source, 'int main() {}')

    def test_deleted_submission_releases_verification_lock_without_recreating_job(self):
        from django.utils import timezone
        from judge.problem_authoring.data import reconcile_authoring
        from judge.problem_authoring.service import save_draft
        from judge.problem_authoring.types import DraftChanges
        problem, state = self.reference()
        context = AuthoringContext(self.user.pk)
        run = self.api().start_verification(context, problem.pk, request_token=uuid.uuid4(),
                                            expected_grading_revision=1)
        Submission.objects.filter(pk=run.submission_id).delete()
        reconcile_authoring(now=timezone.now())
        run.refresh_from_db()
        self.assertEqual(run.state, 'FAILED')
        self.assertIn('new verification', run.safe_error)
        self.assertFalse(Submission.objects.filter(problem=problem).exists())
        with self.assertRaises(AuthoringError) as error:
            self.api().retry_verification(context, run.pk)
        self.assertEqual(error.exception.code, 'missing_submission')
        self.assertFalse(Submission.objects.filter(problem=problem).exists())
        save_draft(context, DraftChanges(problem_fields={'time_limit': 2}), problem_id=problem.pk,
                   expected_revision=1, request_token=uuid.uuid4())
        state.refresh_from_db()
        self.assertEqual(state.grading_revision, 2)

    def test_missing_data_and_stale_revision_reject_start(self):
        problem, state = self.reference(ready=False)
        with self.assertRaises(AuthoringError):
            self.api().start_verification(AuthoringContext(self.user.pk), problem.pk,
                                          request_token=uuid.uuid4(), expected_grading_revision=1)
        state.data_state = 'READY'
        state.save()
        with self.assertRaises(AuthoringError):
            self.api().start_verification(AuthoringContext(self.user.pk), problem.pk,
                                          request_token=uuid.uuid4(), expected_grading_revision=0)
        self.assertFalse(Submission.objects.exists())

    def test_run_snapshots_reference_source_digest_and_runtime(self):
        problem, state = self.reference()
        token = uuid.uuid4()
        run = self.api().start_verification(AuthoringContext(self.user.pk), problem.pk,
                                            request_token=token, expected_grading_revision=1)
        self.assertEqual(run.source_sha256, problem.reference_source.upload.sha256)
        self.assertEqual(run.language_id, self.language.pk)

    def test_stale_finished_run_is_preserved_but_not_current_verified(self):
        from judge.problem_authoring.policy import publish_problem
        from judge.problem_authoring.service import save_draft
        from judge.problem_authoring.types import DraftChanges
        problem, state = self.reference()
        context = AuthoringContext(self.user.pk)
        run = self.api().start_verification(context, problem.pk, request_token=uuid.uuid4(),
                                            expected_grading_revision=1)
        Submission.objects.filter(pk=run.submission_id).update(status='D', result='AC')
        self.api().refresh_verification(run.pk)
        save_draft(context, DraftChanges(problem_fields={'time_limit': 2}), problem_id=problem.pk,
                   expected_revision=1, request_token=uuid.uuid4())
        with self.assertRaises(AuthoringError):
            publish_problem(context, problem.pk, expected_revision=2, accept_unverified=False)
        run.refresh_from_db()
        self.assertEqual(run.state, 'FINISHED')
        self.assertEqual(run.grading_revision, 1)

    def test_dispatch_does_not_reset_submission_already_processing(self):
        problem, state = self.reference()
        run = self.api().start_verification(AuthoringContext(self.user.pk), problem.pk,
                                            request_token=uuid.uuid4(), expected_grading_revision=1)
        Submission.objects.filter(pk=run.submission_id).update(status='P')
        with patch('judge.problem_authoring.verification.judge_submission',
                   side_effect=AssertionError('do not resend')):
            self.api().dispatch_verification(run.pk)
        run.refresh_from_db()
        self.assertEqual(run.state, 'JUDGING')

    def test_bridge_duplicate_queue_id_remains_idempotent(self):
        from judge.bridge.judge_list import JudgeList
        judges = JudgeList()
        judges.judge(123, 'test', 'CPP20', 'source', None, 1, [])
        judges.judge(123, 'test', 'CPP20', 'source', None, 1, [])
        self.assertEqual(len(judges.node_map), 1)
        self.assertIn(123, judges.node_map)

    def test_retry_infrastructure_failure_reuses_original_submission(self):
        problem, state = self.reference()
        context = AuthoringContext(self.user.pk)
        run = self.api().start_verification(context, problem.pk, request_token=uuid.uuid4(),
                                            expected_grading_revision=1)
        submission_id = run.submission_id
        Submission.objects.filter(pk=submission_id).update(status='IE', result='IE')
        self.api().refresh_verification(run.pk)
        retried = self.api().retry_verification(context, run.pk)
        self.assertEqual(retried.state, 'PENDING')
        self.assertEqual(retried.submission_id, submission_id)
        self.assertEqual(Submission.objects.filter(problem=problem).count(), 1)

    def test_modified_reference_source_is_rejected_before_submission_creation(self):
        from judge.problem_authoring.storage import upload_path
        problem, state = self.reference()
        upload_path(problem.reference_source.upload).write_bytes(b'changed')
        with self.assertRaises(AuthoringError):
            self.api().start_verification(AuthoringContext(self.user.pk), problem.pk,
                                          request_token=uuid.uuid4(), expected_grading_revision=1)
        self.assertFalse(Submission.objects.exists())

    def test_lost_dispatch_ack_keeps_submission_nonterminal_for_reconciliation(self):
        problem, state = self.reference()
        run = self.api().start_verification(AuthoringContext(self.user.pk), problem.pk,
                                            request_token=uuid.uuid4(), expected_grading_revision=1)
        with patch('judge.judgeapi.judge_request', side_effect=OSError('ack lost')):
            self.api().dispatch_verification(run.pk)
        run.refresh_from_db()
        run.submission.refresh_from_db()
        self.assertEqual(run.state, 'DISPATCHING')
        self.assertEqual(run.submission.status, 'QU')
        Submission.objects.filter(pk=run.submission_id).update(status='D', result='AC')
        self.api().refresh_verification(run.pk)
        run.refresh_from_db()
        self.assertEqual(run.state, 'FINISHED')

    def test_lost_ack_after_processing_callback_does_not_fail_active_run(self):
        problem, state = self.reference()
        run = self.api().start_verification(AuthoringContext(self.user.pk), problem.pk,
                                            request_token=uuid.uuid4(), expected_grading_revision=1)

        def processing_then_disconnect(packet):
            Submission.objects.filter(pk=run.submission_id).update(status='P')
            raise OSError('reply connection closed')

        with patch('judge.judgeapi.judge_request', side_effect=processing_then_disconnect):
            self.api().dispatch_verification(run.pk)
        run.refresh_from_db()
        self.assertEqual(run.state, 'JUDGING')
        self.assertEqual(Submission.objects.get(pk=run.submission_id).status, 'P')

    def test_bad_reply_does_not_overwrite_completed_reference_result(self):
        problem, state = self.reference()
        run = self.api().start_verification(AuthoringContext(self.user.pk), problem.pk,
                                            request_token=uuid.uuid4(), expected_grading_revision=1)

        def completed_then_bad_reply(packet):
            Submission.objects.filter(pk=run.submission_id).update(status='D', result='AC')
            return {'name': 'bad-request'}

        with patch('judge.judgeapi.judge_request', side_effect=completed_then_bad_reply):
            self.api().dispatch_verification(run.pk)
        run.refresh_from_db()
        self.assertEqual(run.state, 'FINISHED')
        self.assertEqual(Submission.objects.get(pk=run.submission_id).result, 'AC')

    def test_acknowledged_queue_lost_on_bridge_restart_can_be_reconciled(self):
        from datetime import timedelta
        from django.utils import timezone
        from judge.models import ProblemReferenceRun
        problem, state = self.reference()
        run = self.api().start_verification(AuthoringContext(self.user.pk), problem.pk,
                                            request_token=uuid.uuid4(), expected_grading_revision=1)
        with patch('judge.problem_authoring.verification.judge_submission', return_value=True):
            self.api().dispatch_verification(run.pk)
        ProblemReferenceRun.objects.filter(pk=run.pk).update(updated=timezone.now() - timedelta(minutes=6))
        with patch('judge.judgeapi.judge_request', return_value={
                'name': 'submission-received', 'submission-id': run.submission_id}):
            with patch('judge.judgeapi._post_update_submission'):
                self.api().dispatch_verification(run.pk)
        run.refresh_from_db()
        self.assertGreater(run.updated, timezone.now() - timedelta(minutes=1))
        self.assertEqual(run.state, 'JUDGING')
        self.assertEqual(Submission.objects.filter(problem=problem).count(), 1)

    def test_reference_submission_source_stays_private_when_problem_sources_are_public(self):
        from judge.models.tests.util import create_user
        from judge.models.problem import SubmissionSourceAccess
        problem, state = self.reference()
        problem.submission_source_visibility_mode = SubmissionSourceAccess.ALWAYS
        problem.save(update_fields=['submission_source_visibility_mode'])
        run = self.api().start_verification(AuthoringContext(self.user.pk), problem.pk,
                                            request_token=uuid.uuid4(), expected_grading_revision=1)
        viewer = create_user('referenceviewer')
        self.assertFalse(run.submission.can_see_detail(viewer))
        self.assertTrue(run.submission.can_see_detail(self.user))

    def test_retry_cannot_revive_run_after_source_runtime_changes(self):
        from judge.models import ProblemReferenceRun
        from judge.problem_authoring.service import save_draft
        from judge.problem_authoring.types import DraftChanges
        problem, state = self.reference()
        run = self.api().start_verification(AuthoringContext(self.user.pk), problem.pk,
                                            request_token=uuid.uuid4(), expected_grading_revision=1)
        Submission.objects.filter(pk=run.submission_id).update(status='IE', result='IE')
        self.api().refresh_verification(run.pk)
        save_draft(AuthoringContext(self.user.pk), DraftChanges(problem_fields={'time_limit': 2}),
                   problem_id=problem.pk, expected_revision=1, request_token=uuid.uuid4())
        with self.assertRaises(AuthoringError):
            self.api().retry_verification(AuthoringContext(self.user.pk), run.pk)
        self.assertEqual(ProblemReferenceRun.objects.get(pk=run.pk).state, 'FAILED')

    def test_terminal_callback_between_claim_and_send_is_not_reset(self):
        from judge.judgeapi import judge_submission
        problem, state = self.reference()
        run = self.api().start_verification(AuthoringContext(self.user.pk), problem.pk,
                                            request_token=uuid.uuid4(), expected_grading_revision=1)

        def complete_before_send(submission):
            Submission.objects.filter(pk=submission.pk).update(status='D', result='AC')
            return judge_submission(submission)

        with patch('judge.problem_authoring.verification.judge_submission', side_effect=complete_before_send):
            with patch('judge.judgeapi.judge_request', return_value={
                    'name': 'submission-received', 'submission-id': run.submission_id}):
                self.api().dispatch_verification(run.pk)
        run.refresh_from_db()
        self.assertEqual(run.state, 'FINISHED')
        self.assertEqual(Submission.objects.get(pk=run.submission_id).result, 'AC')

    def test_non_ac_finishes_without_publication(self):
        problem, state = self.reference()
        run = self.api().start_verification(AuthoringContext(self.user.pk), problem.pk,
                                            request_token=uuid.uuid4(), expected_grading_revision=1)
        Submission.objects.filter(pk=run.submission_id).update(status='D', result='WA')
        refreshed = self.api().refresh_verification(run.pk)
        self.assertEqual(refreshed.state, 'FINISHED')
        problem.refresh_from_db()
        self.assertFalse(problem.is_public)
