import uuid

from django.test import TestCase

from judge.models import ProblemAuthoringState
from judge.problem_authoring import policy
from judge.problem_authoring.service import save_draft
from judge.problem_authoring.types import AuthoringContext, AuthoringError, DraftChanges
from judge.tests.authoring_helpers import AuthoringTestMixin


class AuthoringPolicyTest(AuthoringTestMixin, TestCase):
    def ready_problem(self):
        problem = self.make_problem()
        problem.authors.add(self.user.profile)
        state = ProblemAuthoringState.objects.create(problem=problem, revision=1, grading_revision=1,
                                                     active_data_revision=1, data_state='READY')
        return problem, state

    def test_missing_data_cannot_be_submitted_or_attached_to_contest(self):
        problem, state = self.ready_problem()
        state.data_state = 'MISSING'
        state.save()
        self.assertTrue(hasattr(policy, 'assert_can_submit'), 'Readiness policy is missing')
        for guard in (policy.assert_can_submit, policy.assert_can_attach_to_contest):
            with self.assertRaises(AuthoringError):
                guard(problem.pk)

    def test_direct_submission_creation_cannot_bypass_readiness(self):
        from django.core.exceptions import ValidationError
        from judge.models import Submission
        problem, state = self.ready_problem()
        state.data_state = 'MISSING'
        state.save()
        with self.assertRaises(ValidationError):
            Submission.objects.create(problem=problem, user=self.user.profile, language=self.language)

    def test_rejudge_of_terminal_submission_is_blocked_during_data_preparation(self):
        from unittest.mock import patch
        from judge.judgeapi import judge_submission
        from judge.models import ProblemDataOperation, Submission
        problem, state = self.ready_problem()
        submission = Submission.objects.create(problem=problem, user=self.user.profile,
                                               language=self.language, status='D')
        operation = ProblemDataOperation.objects.create(problem=problem, target_revision=2)
        state.current_operation = operation
        state.save()
        with patch('judge.judgeapi.judge_request', return_value={
                'name': 'submission-received', 'submission-id': submission.pk}):
            self.assertFalse(judge_submission(submission, rejudge=True))
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'D')

    def test_organization_author_can_edit_without_being_organization_admin(self):
        from judge.models import Organization
        from judge.models.tests.util import create_user
        from judge.problem_authoring.types import AuthoringContext
        user = create_user('orgcollaborator', user_permissions=('edit_own_problem',))
        organization = Organization.objects.create(name='Team', slug='team', short_name='Team', about='')
        problem = self.make_problem()
        problem.organization = organization
        problem.is_organization_private = True
        problem.save()
        problem.authors.add(user.profile)
        policy.authorize_edit(AuthoringContext(user.pk, organization.pk), problem)

    def test_older_failed_operation_does_not_lock_current_ready_problem(self):
        from judge.models import ProblemDataOperation
        problem, state = self.ready_problem()
        ProblemDataOperation.objects.create(problem=problem, target_revision=0, state='FAILED')
        policy.assert_mutation_allowed(problem.pk, {'time_limit'})

    def test_language_relation_change_cannot_bypass_active_verification(self):
        import io
        from django.core.exceptions import ValidationError
        from judge.models import ProblemReferenceRun
        from judge.problem_authoring.uploads import receive_upload
        problem, state = self.ready_problem()
        upload = receive_upload(AuthoringContext(self.user.pk), io.BytesIO(b'x'), 'SOURCE')
        ProblemReferenceRun.objects.create(problem=problem, owner=self.user.profile, request_token=uuid.uuid4(),
                                           grading_revision=1, source_sha256=upload.sha256, upload=upload,
                                           language=self.language)
        with self.assertRaises(ValidationError):
            problem.allowed_languages.add(self.language)

    def test_admin_scalar_edit_invalidates_old_verification_revision(self):
        from django.contrib.admin.sites import AdminSite
        from django.test import RequestFactory
        from unittest.mock import Mock
        from judge.admin.problem import ProblemAdmin
        from judge.models import Problem
        problem, state = self.ready_problem()
        problem.time_limit = 2
        request = RequestFactory().post('/admin/')
        request.user = self.user
        form = Mock(changed_data=['time_limit'])
        ProblemAdmin(Problem, AdminSite()).save_model(request, problem, form, True)
        state.refresh_from_db()
        self.assertEqual(state.grading_revision, 2)
        self.assertEqual(state.revision, 2)

    def test_direct_scalar_changes_invalidate_revision_without_admin(self):
        problem, state = self.ready_problem()
        problem.time_limit = 2
        problem.save(update_fields=['time_limit'])
        state.refresh_from_db()
        self.assertEqual((state.revision, state.grading_revision), (2, 2))
        problem.description = '# Direct edit'
        problem.save(update_fields=['description'])
        state.refresh_from_db()
        self.assertEqual((state.revision, state.grading_revision), (3, 2))

    def test_direct_language_relation_changes_invalidate_current_verification(self):
        problem, state = self.ready_problem()
        problem.allowed_languages.add(self.language)
        state.refresh_from_db()
        self.assertEqual((state.revision, state.grading_revision), (2, 2))
        problem.allowed_languages.add(self.language)
        state.refresh_from_db()
        self.assertEqual((state.revision, state.grading_revision), (2, 2))
        problem.allowed_languages.remove(self.language)
        state.refresh_from_db()
        self.assertEqual((state.revision, state.grading_revision), (3, 3))

    def test_direct_language_limit_changes_invalidate_current_verification(self):
        from judge.models import LanguageLimit
        problem, state = self.ready_problem()
        limit = LanguageLimit.objects.create(problem=problem, language=self.language, time_limit=2, memory_limit=524288)
        state.refresh_from_db()
        self.assertEqual((state.revision, state.grading_revision), (2, 2))
        limit.delete()
        state.refresh_from_db()
        self.assertEqual((state.revision, state.grading_revision), (3, 3))

    def test_unchanged_foreign_key_save_does_not_increment_revision(self):
        problem, state = self.ready_problem()
        problem.save(update_fields=['group'])
        state.refresh_from_db()
        self.assertEqual((state.revision, state.grading_revision), (1, 1))

    def test_language_limit_queryset_delete_invalidates_revision(self):
        from judge.models import LanguageLimit
        problem, state = self.ready_problem()
        LanguageLimit.objects.create(problem=problem, language=self.language, time_limit=2, memory_limit=524288)
        state.refresh_from_db()
        before = state.grading_revision
        problem.language_limits.all().delete()
        state.refresh_from_db()
        self.assertEqual(state.grading_revision, before + 1)

    def test_language_limit_queryset_delete_cannot_bypass_verification_lock(self):
        import io
        from django.core.exceptions import ValidationError
        from judge.models import LanguageLimit, ProblemReferenceRun
        from judge.problem_authoring.uploads import receive_upload
        problem, state = self.ready_problem()
        LanguageLimit.objects.create(problem=problem, language=self.language, time_limit=2, memory_limit=524288)
        upload = receive_upload(AuthoringContext(self.user.pk), io.BytesIO(b'x'), 'SOURCE')
        ProblemReferenceRun.objects.create(problem=problem, owner=self.user.profile, request_token=uuid.uuid4(),
                                           grading_revision=2, source_sha256=upload.sha256, upload=upload,
                                           language=self.language)
        from django.db import transaction
        with self.assertRaises(ValidationError), transaction.atomic():
            problem.language_limits.all().delete()
        self.assertTrue(problem.language_limits.exists())

    def test_scalar_mutation_rolls_back_if_revision_write_fails(self):
        from unittest.mock import patch
        problem, state = self.ready_problem()
        problem.time_limit = 2
        with patch('judge.problem_authoring.revisions.invalidate_revision', side_effect=RuntimeError('revision write')):
            with self.assertRaises(RuntimeError):
                problem.save(update_fields=['time_limit'])
        problem.refresh_from_db()
        self.assertEqual(problem.time_limit, 1)
        state.refresh_from_db()
        self.assertEqual(state.grading_revision, 1)

    def test_language_limit_mutation_rolls_back_if_revision_write_fails(self):
        from unittest.mock import patch
        from judge.models import LanguageLimit
        problem, state = self.ready_problem()
        with patch('judge.problem_authoring.revisions.invalidate_revision', side_effect=RuntimeError('revision write')):
            with self.assertRaises(RuntimeError):
                LanguageLimit.objects.create(problem=problem, language=self.language, time_limit=2, memory_limit=524288)
        self.assertFalse(problem.language_limits.exists())

    def test_direct_editorial_update_invalidates_editor_revision_only(self):
        from django.utils import timezone
        from judge.models import Solution
        problem, state = self.ready_problem()
        solution = Solution.objects.create(problem=problem, content='# Original', publish_on=timezone.now())
        state.refresh_from_db()
        before = state.revision
        solution.content = '# Updated outside shared editor'
        solution.save(update_fields=['content'])
        state.refresh_from_db()
        self.assertEqual(state.revision, before + 1)
        self.assertEqual(state.grading_revision, 1)

    def test_editorial_authors_relation_invalidates_editor_revision(self):
        from django.utils import timezone
        from judge.models import Solution
        problem, state = self.ready_problem()
        solution = Solution.objects.create(problem=problem, content='# Editorial', publish_on=timezone.now())
        state.refresh_from_db()
        before = state.revision
        solution.authors.add(self.user.profile)
        state.refresh_from_db()
        self.assertEqual(state.revision, before + 1)
        self.assertEqual(state.grading_revision, 1)

    def test_editorial_queryset_deletion_invalidates_stale_editor(self):
        from django.utils import timezone
        from judge.models import Solution
        problem, state = self.ready_problem()
        solution = Solution.objects.create(problem=problem, content='# Editorial', publish_on=timezone.now())
        state.refresh_from_db()
        before = state.revision
        Solution.objects.filter(pk=solution.pk).delete()
        state.refresh_from_db()
        self.assertEqual(state.revision, before + 1)
        self.assertEqual(state.grading_revision, 1)
        self.assertFalse(Solution.objects.filter(problem=problem).exists())

    def test_empty_editorial_authors_clear_does_not_conflict_with_open_editor(self):
        from django.utils import timezone
        from judge.models import Solution
        problem, state = self.ready_problem()
        solution = Solution.objects.create(problem=problem, content='# Editorial', publish_on=timezone.now())
        state.refresh_from_db()
        before = state.revision
        solution.authors.clear()
        state.refresh_from_db()
        self.assertEqual(state.revision, before)

    def test_removing_absent_editorial_author_does_not_conflict_with_open_editor(self):
        from django.utils import timezone
        from judge.models import Solution
        problem, state = self.ready_problem()
        solution = Solution.objects.create(problem=problem, content='# Editorial', publish_on=timezone.now())
        state.refresh_from_db()
        before = state.revision
        solution.authors.remove(self.user.profile)
        state.refresh_from_db()
        self.assertEqual(state.revision, before)

    def test_reverse_editorial_author_clear_invalidates_only_affected_problem(self):
        from django.utils import timezone
        from judge.models import Solution
        problem, state = self.ready_problem()
        solution = Solution.objects.create(problem=problem, content='# Editorial', publish_on=timezone.now())
        solution.authors.add(self.user.profile)
        state.refresh_from_db()
        before = state.revision
        self.user.profile.solution_set.clear()
        state.refresh_from_db()
        self.assertEqual(state.revision, before + 1)
        self.assertFalse(solution.authors.exists())
        self.user.profile.solution_set.clear()
        state.refresh_from_db()
        self.assertEqual(state.revision, before + 1)

    def test_language_limit_model_cannot_bypass_active_verification(self):
        import io
        from django.core.exceptions import ValidationError
        from judge.models import LanguageLimit, ProblemReferenceRun
        from judge.problem_authoring.uploads import receive_upload
        problem, state = self.ready_problem()
        upload = receive_upload(AuthoringContext(self.user.pk), io.BytesIO(b'x'), 'SOURCE')
        ProblemReferenceRun.objects.create(problem=problem, owner=self.user.profile, request_token=uuid.uuid4(),
                                           grading_revision=1, source_sha256=upload.sha256, upload=upload,
                                           language=self.language)
        with self.assertRaises(ValidationError):
            LanguageLimit.objects.create(problem=problem, language=self.language, time_limit=2, memory_limit=524288)

    def test_bridge_readiness_rejects_unprepared_reference(self):
        from unittest.mock import Mock
        from judge.bridge.django_handler import DjangoHandler
        from judge.models import Submission
        problem, state = self.ready_problem()
        submission = Submission.objects.create(problem=problem, user=self.user.profile, language=self.language)
        state.data_state = 'MISSING'
        state.active_data_revision = 0
        state.save()
        handler = object.__new__(DjangoHandler)
        handler.judges = Mock()
        handler.judges.check_priority.return_value = True
        response = handler.on_submission({'submission-id': submission.pk, 'problem-id': problem.code,
                                          'language': self.language.key, 'source': 'x', 'judge-id': None,
                                          'priority': 1, 'banned-judges': []})
        self.assertEqual(response, {'name': 'bad-request'})

    def test_judge_data_load_rechecks_readiness_for_queued_submission(self):
        from judge.bridge.judge_handler import JudgeHandler
        from judge.models import Submission
        problem, state = self.ready_problem()
        submission = Submission.objects.create(problem=problem, user=self.user.profile, language=self.language)
        state.data_state = 'MISSING'
        state.save()
        handler = object.__new__(JudgeHandler)
        handler._working = submission.pk
        from unittest.mock import patch
        with patch('judge.bridge.judge_handler._ensure_connection'):
            self.assertIsNone(handler.get_related_submission_data(submission.pk))

    def test_shared_field_guard_preserves_legacy_active_verification(self):
        from judge.models import ProblemPackageImport
        problem = self.make_problem()
        ProblemPackageImport.objects.create(owner=self.user.profile, problem=problem, state='JUDGING')
        with self.assertRaises(AuthoringError):
            policy.assert_mutation_allowed(problem.pk, {'tests'})
        policy.assert_mutation_allowed(problem.pk, {'description'})

    def test_legacy_hidden_problem_remains_usable(self):
        problem = self.make_problem()
        self.assertTrue(hasattr(policy, 'assert_can_submit'), 'Readiness policy is missing')
        policy.assert_can_submit(problem.pk)
        policy.assert_can_attach_to_contest(problem.pk)

    def test_publication_requires_confirmation_when_unverified(self):
        problem, state = self.ready_problem()
        self.assertTrue(hasattr(policy, 'publish_problem'), 'Publication policy is missing')
        context = AuthoringContext(self.user.pk)
        with self.assertRaises(AuthoringError):
            policy.publish_problem(context, problem.pk, expected_revision=1, accept_unverified=False)
        policy.publish_problem(context, problem.pk, expected_revision=1, accept_unverified=True)
        problem.refresh_from_db()
        self.assertTrue(problem.is_public)
        self.assertEqual(problem.authoring_state.revision, 2)

    def test_direct_visibility_change_rejects_unready_draft(self):
        from django.core.exceptions import ValidationError
        problem, state = self.ready_problem()
        state.data_state = 'MISSING'
        state.save()
        problem.is_public = True
        with self.assertRaises(ValidationError):
            problem.save(update_fields=['is_public'])

    def test_admin_bulk_publish_does_not_bypass_readiness(self):
        from django.contrib.admin.sites import AdminSite
        from django.test import RequestFactory
        from unittest.mock import patch
        from judge.admin.problem import ProblemAdmin
        from judge.models import Problem
        problem, state = self.ready_problem()
        state.data_state = 'MISSING'
        state.save()
        request = RequestFactory().post('/admin/')
        request.user = self.user
        model_admin = ProblemAdmin(Problem, AdminSite())
        with patch.object(model_admin, 'message_user'), patch.object(model_admin, '_rescore'):
            model_admin.make_public_and_update_publish_date(request, Problem.objects.filter(pk=problem.pk))
        problem.refresh_from_db()
        self.assertFalse(problem.is_public)

    def test_pending_data_blocks_grading_edits_but_not_statement(self):
        from judge.models import ProblemDataOperation
        problem, state = self.ready_problem()
        operation = ProblemDataOperation.objects.create(problem=problem, target_revision=2)
        state.current_operation = operation
        state.save()
        self.assertTrue(hasattr(policy, 'assert_mutation_allowed'), 'Field mutation policy is missing')
        policy.assert_mutation_allowed(problem.pk, {'description'})
        with self.assertRaises(AuthoringError):
            policy.assert_mutation_allowed(problem.pk, {'time_limit'})
        save_draft(AuthoringContext(self.user.pk), DraftChanges(problem_fields={'description': '# New'}),
                   problem_id=problem.pk, expected_revision=1, request_token=uuid.uuid4())

    def test_model_update_fields_cannot_bypass_active_verification_lock(self):
        from judge.models import ProblemReferenceRun
        from judge.problem_authoring.uploads import receive_upload
        import io

        problem, state = self.ready_problem()
        upload = receive_upload(AuthoringContext(self.user.pk), io.BytesIO(b'x'), 'SOURCE')
        ProblemReferenceRun.objects.create(problem=problem, owner=self.user.profile, request_token=uuid.uuid4(),
                                           grading_revision=1, source_sha256=upload.sha256, upload=upload,
                                           language=self.language)
        problem.time_limit = 2
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            problem.save(update_fields=['time_limit'])
        problem.refresh_from_db()
        problem.description = '# Safe change'
        problem.save(update_fields=['description'])
        problem.refresh_from_db()
        self.assertEqual(problem.description, '# Safe change')
