import importlib.util
import uuid

from django.test import TestCase, override_settings

from judge.models import Organization, Problem, ProblemAuthoringState, ProblemDataOperation
from judge.models.tests.util import create_user
from judge.problem_authoring.types import AuthoringContext, AuthoringError, DraftChanges
from judge.tests.authoring_helpers import AuthoringTestMixin, make_zip


class AuthoringServiceTest(AuthoringTestMixin, TestCase):
    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('judge.problem_authoring.service'),
                             'Shared authoring save service is missing')
        from judge.problem_authoring import service
        return service

    @property
    def context(self):
        return AuthoringContext(self.user.pk)

    def changes(self, **extra):
        fields = dict(code='savedraft', name='Draft', description='# Edited', group_id=self.group.pk,
                      types=[self.kind.pk], time_limit=1, memory_limit=262144, points=100, partial=False,
                      submission_source_visibility_mode='F', testcase_visibility_mode='A')
        fields.update(extra)
        return DraftChanges(problem_fields=fields, solution_fields={'content': '# Editorial'})

    def save(self, changes=None, **kwargs):
        options = dict(problem_id=None, expected_revision=None, request_token=uuid.uuid4())
        options.update(kwargs)
        return self.api().save_draft(self.context, changes or self.changes(), **options)

    def test_failed_metadata_validation_does_not_publish_pdf_media(self):
        import io
        from unittest.mock import patch
        from judge.problem_authoring.uploads import receive_upload
        upload = receive_upload(self.context, io.BytesIO(b'%PDF-1.4'), 'PDF')
        fields = self.changes().problem_fields
        fields['name'] = ''
        with patch('judge.views.widgets.pdf_statement_uploader', side_effect=AssertionError('must not publish')):
            with self.assertRaises(AuthoringError) as failure:
                self.save(DraftChanges(problem_fields=fields, pdf_upload_id=upload.pk))
        self.assertEqual(failure.exception.code, 'invalid_problem')
        upload.refresh_from_db()
        self.assertIsNone(upload.consumed_by_id)
        self.assertNotIn('published_url', upload.manifest)

    def test_editorial_visibility_is_explicit_and_independent_from_problem(self):
        result = self.save()
        problem = Problem.objects.get(pk=result.problem_id)
        self.save(DraftChanges(solution_fields={'content': '# Public editorial', 'is_public': True}),
                  problem_id=problem.pk, expected_revision=1)
        problem.refresh_from_db()
        self.assertTrue(problem.solution.is_public)
        self.assertFalse(problem.is_public)

    def test_editorial_visibility_requires_publication_permission(self):
        from judge.models import Solution
        from django.utils import timezone
        user = create_user('editorialauthor', user_permissions=('edit_own_problem',))
        problem = self.make_problem()
        problem.authors.add(user.profile)
        Solution.objects.create(problem=problem, content='# Draft editorial', publish_on=timezone.now())
        with self.assertRaises(AuthoringError):
            self.api().save_draft(AuthoringContext(user.pk), DraftChanges(solution_fields={
                'content': '# Editorial', 'is_public': True,
            }), problem_id=problem.pk, expected_revision=0, request_token=uuid.uuid4())
        problem.solution.refresh_from_db()
        self.assertFalse(problem.solution.is_public)

    def test_invalid_editorial_does_not_publish_pdf_media(self):
        import io
        from unittest.mock import patch
        from judge.problem_authoring.uploads import receive_upload
        upload = receive_upload(self.context, io.BytesIO(b'%PDF-1.4'), 'PDF')
        with patch('judge.views.widgets.pdf_statement_uploader', side_effect=AssertionError('must not publish')):
            with self.assertRaises(AuthoringError) as failure:
                self.save(DraftChanges(problem_fields=self.changes().problem_fields, pdf_upload_id=upload.pk,
                                       solution_fields={'content': '# Editorial', 'authors': [999999]}))
        self.assertEqual(failure.exception.code, 'invalid_authors')
        self.assertFalse(Problem.objects.exists())

    def test_simple_test_replacement_does_not_discard_per_case_output_settings(self):
        from judge.models import ProblemData, ProblemTestCase
        from judge.problem_authoring.uploads import receive_upload
        problem = self.make_problem()
        problem.authors.add(self.user.profile)
        ProblemData.objects.create(problem=problem)
        ProblemTestCase.objects.create(dataset=problem, order=1, type='C', input_file='1.in', output_file='1.out',
                                       points=1, is_pretest=False, output_limit=4096)
        upload = receive_upload(self.context, make_zip({'1.in': '1', '1.out': '2'}), 'TESTS', problem_id=problem.pk)
        with self.assertRaises(AuthoringError) as failure:
            self.save(DraftChanges(test_upload_id=upload.pk), problem_id=problem.pk, expected_revision=0)
        self.assertEqual(failure.exception.code, 'advanced_data')
        self.assertEqual(problem.cases.get().output_limit, 4096)

    def test_reference_runtime_can_switch_to_newly_enabled_language_in_same_save(self):
        import io
        from judge.models import Language, ProblemReferenceSource
        from judge.problem_authoring.uploads import receive_upload
        first = self.save()
        problem = Problem.objects.get(pk=first.problem_id)
        problem.allowed_languages.add(self.language)
        upload = receive_upload(self.context, io.BytesIO(b'print(1)'), 'SOURCE')
        upload.consumed_by = problem
        upload.save()
        ProblemReferenceSource.objects.create(problem=problem, upload=upload, language=self.language)
        runtime = Language.objects.create(key='PYAUTH', name='Python authoring', short_name='Python')
        state = ProblemAuthoringState.objects.get(problem=problem)
        self.save(DraftChanges(problem_fields={'allowed_languages': [runtime.pk]},
                               reference_language_id=runtime.pk), problem_id=problem.pk,
                  expected_revision=state.revision)
        self.assertEqual(ProblemReferenceSource.objects.get(problem=problem).language_id, runtime.pk)
        self.assertEqual(list(problem.allowed_languages.values_list('pk', flat=True)), [runtime.pk])

    @override_settings(PROBLEM_AUTHORING_OWNER_UPLOAD_LIMIT=300)
    def test_test_upload_save_reserves_generated_workspace_before_commit(self):
        from judge.problem_authoring.uploads import receive_upload
        upload = receive_upload(self.context, make_zip({'1.in': '1', '1.out': '2'}), 'TESTS')
        with self.assertRaises(AuthoringError) as failure:
            self.save(DraftChanges(problem_fields=self.changes().problem_fields, test_upload_id=upload.pk))
        self.assertEqual(failure.exception.code, 'storage_quota')
        self.assertFalse(Problem.objects.exists())
        self.assertFalse(ProblemDataOperation.objects.exists())

    def test_invalid_language_limits_do_not_publish_staged_pdf(self):
        import io
        from unittest.mock import patch
        from judge.problem_authoring.uploads import receive_upload
        upload = receive_upload(self.context, io.BytesIO(b'%PDF-1.4'), 'PDF')
        with patch('judge.views.widgets.pdf_statement_uploader', side_effect=AssertionError('must not publish')):
            with self.assertRaises(AuthoringError) as failure:
                self.save(DraftChanges(problem_fields=self.changes().problem_fields, pdf_upload_id=upload.pk,
                                       language_limits=[{'language_id': self.language.pk,
                                                         'time_limit': -1, 'memory_limit': 262144}]))
        self.assertEqual(failure.exception.code, 'invalid_problem')
        self.assertFalse(Problem.objects.exists())

    def test_create_private_draft_and_editorial(self):
        result = self.save()
        problem = Problem.objects.get(pk=result.problem_id)
        self.assertFalse(problem.is_public)
        self.assertFalse(problem.partial)
        self.assertEqual(problem.description, '# Edited')
        self.assertEqual(problem.solution.content, '# Editorial')
        self.assertFalse(problem.solution.is_public)
        self.assertEqual(problem.authoring_state.data_state, 'MISSING')
        self.assertEqual(list(problem.authors.all()), [self.user.profile])
        self.assertTrue(problem.curators.filter(pk=self.user.profile.pk).exists())
        self.assertTrue(problem.types.filter(pk=self.kind.pk).exists())
        self.assertEqual(result.revision, 1)

    def test_duplicate_token_returns_original_result_and_rejects_changed_payload(self):
        token = uuid.uuid4()
        first = self.save(request_token=token)
        second = self.save(request_token=token)
        self.assertEqual(first, second)
        self.assertEqual(Problem.objects.count(), 1)
        with self.assertRaises(AuthoringError):
            self.save(self.changes(name='Different'), request_token=token)

    def test_stale_revision_does_not_overwrite(self):
        first = self.save()
        second = self.save(DraftChanges(problem_fields={'name': 'Fresh'}),
                           problem_id=first.problem_id, expected_revision=1)
        self.assertEqual(second.revision, 2)
        with self.assertRaises(AuthoringError):
            self.save(DraftChanges(problem_fields={'name': 'Stale'}),
                      problem_id=first.problem_id, expected_revision=1)
        problem = Problem.objects.get(pk=first.problem_id)
        self.assertEqual(problem.name, 'Fresh')
        self.assertEqual(problem.solution.content, '# Editorial')
        self.assertFalse(problem.partial)

    def test_org_only_author_preserves_scope(self):
        user = create_user('organizationauthor', user_permissions=('create_organization_problem', 'edit_own_problem'))
        organization = Organization.objects.create(name='Team', slug='team', short_name='Team', about='')
        organization.admins.add(user.profile)
        result = self.api().save_draft(AuthoringContext(user.pk, organization.pk), self.changes(code='team_draft'),
                                       problem_id=None, expected_revision=None, request_token=uuid.uuid4())
        problem = Problem.objects.get(pk=result.problem_id)
        self.assertEqual(problem.organization_id, organization.pk)
        self.assertTrue(problem.is_organization_private)
        self.assertFalse(problem.is_public)

    def test_adopting_legacy_problem_does_not_mark_missing_tests_ready(self):
        problem = self.make_problem('legacyempty')
        problem.authors.add(self.user.profile)
        result = self.save(DraftChanges(problem_fields={'description': '# Updated'}),
                           problem_id=problem.pk, expected_revision=0)
        self.assertEqual(result.revision, 1)
        self.assertEqual(ProblemAuthoringState.objects.get(problem=problem).data_state, 'MISSING')

    def test_broker_failure_does_not_rollback_saved_operation(self):
        from unittest.mock import patch
        from judge.problem_authoring.uploads import receive_upload
        upload = receive_upload(self.context, make_zip({'1.in': '1', '1.out': '2'}), 'TESTS')
        with patch('judge.tasks.problem_authoring.process_authoring_data.delay', side_effect=OSError('offline')):
            with self.captureOnCommitCallbacks(execute=True):
                result = self.save(DraftChanges(problem_fields=self.changes().problem_fields, test_upload_id=upload.pk))
        self.assertEqual(ProblemDataOperation.objects.get(pk=result.operation_id).state, 'PENDING')
        self.assertTrue(Problem.objects.filter(pk=result.problem_id).exists())

    def test_unchanged_reference_runtime_does_not_invalidate_statement_edit(self):
        import io
        from judge.models import ProblemReferenceSource
        from judge.problem_authoring.uploads import receive_upload
        result = self.save()
        problem = Problem.objects.get(pk=result.problem_id)
        problem.allowed_languages.add(self.language)
        upload = receive_upload(self.context, io.BytesIO(b'x'), 'SOURCE')
        upload.consumed_by = problem
        upload.save()
        ProblemReferenceSource.objects.create(problem=problem, upload=upload, language=self.language)
        before = problem.authoring_state.grading_revision
        self.save(DraftChanges(problem_fields={'description': '# Revised'}, reference_language_id=self.language.pk),
                  problem_id=problem.pk, expected_revision=problem.authoring_state.revision)
        self.assertEqual(ProblemAuthoringState.objects.get(problem=problem).grading_revision, before)

    def test_request_token_is_bound_to_organization_scope(self):
        first = self.save(request_token=uuid.UUID('11111111-1111-4111-8111-111111111111'))
        organization = Organization.objects.create(name='Team', slug='team', short_name='Team', about='')
        organization.admins.add(self.user.profile)
        with self.assertRaises(AuthoringError):
            self.api().save_draft(AuthoringContext(self.user.pk, organization.pk), self.changes(),
                                  problem_id=None, expected_revision=None,
                                  request_token=uuid.UUID('11111111-1111-4111-8111-111111111111'))
        self.assertEqual(Problem.objects.get(pk=first.problem_id).organization_id, None)

    def test_source_is_optional_but_editorial_metadata_is_preserved(self):
        from django.utils import timezone
        first = self.save()
        problem = Problem.objects.get(pk=first.problem_id)
        solution = problem.solution
        solution.is_public = True
        scheduled = timezone.now() + timezone.timedelta(days=2)
        solution.publish_on = scheduled
        solution.save()
        self.save(DraftChanges(problem_fields={'description': '# Revised'}, solution_fields={'content': '# Updated'}),
                  problem_id=problem.pk, expected_revision=ProblemAuthoringState.objects.get(problem=problem).revision)
        solution.refresh_from_db()
        self.assertTrue(solution.is_public)
        self.assertEqual(solution.publish_on, scheduled)
        self.assertEqual(solution.content, '# Updated')
        self.assertFalse(problem.reference_runs.exists())

    def test_language_order_alone_does_not_invalidate_verification(self):
        from judge.problem_authoring.service import grading_fields_changed
        self.assertFalse(grading_fields_changed({'allowed_languages': [1, 2]}, {'allowed_languages': [2, 1]}))

    def test_pdf_reference_is_consumed_atomically_by_save(self):
        import io
        from unittest.mock import patch
        from judge.problem_authoring.uploads import receive_upload
        upload = receive_upload(self.context, io.BytesIO(b'%PDF-1.4'), 'PDF')
        changes = DraftChanges(problem_fields=self.changes().problem_fields, pdf_upload_id=upload.pk)
        token = uuid.uuid4()
        with patch('judge.views.widgets.pdf_statement_uploader', return_value='https://example.invalid/pdf'):
            first = self.save(changes, request_token=token)
            duplicate = self.save(changes, request_token=token)
        upload.refresh_from_db()
        self.assertEqual(upload.consumed_by_id, first.problem_id)
        self.assertEqual(first, duplicate)
        self.assertEqual(Problem.objects.get(pk=first.problem_id).pdf_url, 'https://example.invalid/pdf')

    def test_empty_optional_editorial_does_not_block_draft_save(self):
        result = self.save(DraftChanges(problem_fields=self.changes().problem_fields, solution_fields={'content': ''}))
        self.assertTrue(Problem.objects.filter(pk=result.problem_id).exists())
        self.assertFalse(Problem.objects.get(pk=result.problem_id).solution.content)

    def test_text_only_change_keeps_current_verification_revision(self):
        first = self.save()
        state = ProblemAuthoringState.objects.get(problem_id=first.problem_id)
        before = state.grading_revision
        changes = DraftChanges(problem_fields={'description': '# Revised'},
                               solution_fields={'content': '# Revised sol'})
        self.save(changes, problem_id=first.problem_id, expected_revision=1)
        state.refresh_from_db()
        self.assertEqual(state.revision, 2)
        self.assertEqual(state.grading_revision, before)

    def test_mass_testcase_permission_avoids_hidden_formset_limit(self):
        from judge.problem_authoring.uploads import receive_upload
        files = {}
        for index in range(1002):
            files[str(index) + '.in'] = ''
            files[str(index) + '.out'] = ''
        upload = receive_upload(self.context, make_zip(files), 'TESTS')
        result = self.save(DraftChanges(problem_fields=self.changes().problem_fields, test_upload_id=upload.pk))
        self.assertEqual(len(ProblemDataOperation.objects.get(pk=result.operation_id).config['cases']), 1002)

    def test_regular_author_cannot_exceed_testcase_hard_limit(self):
        from django.test import override_settings
        from judge.problem_authoring.uploads import receive_upload
        user = create_user('regular', user_permissions=('add_problem', 'edit_own_problem'))
        context = AuthoringContext(user.pk)
        upload = receive_upload(context, make_zip({'1.in': '', '1.out': '', '2.in': '', '2.out': ''}), 'TESTS')
        with override_settings(VNOJ_TESTCASE_HARD_LIMIT=1), self.assertRaises(AuthoringError):
            self.api().save_draft(context, DraftChanges(problem_fields=self.changes().problem_fields,
                                                        test_upload_id=upload.pk),
                                  problem_id=None, expected_revision=None, request_token=uuid.uuid4())
        self.assertFalse(Problem.objects.exists())

    def test_service_rejects_unknown_related_identifiers_without_partial_problem(self):
        with self.assertRaises(AuthoringError):
            self.save(self.changes(types=[99999999]))
        self.assertFalse(Problem.objects.exists())

    def test_language_limits_are_saved_and_kept_when_section_omitted(self):
        limits = [{'language_id': self.language.pk, 'time_limit': 2, 'memory_limit': 524288}]
        changes = DraftChanges(problem_fields=self.changes().problem_fields, language_limits=limits)
        first = self.save(changes)
        problem = Problem.objects.get(pk=first.problem_id)
        self.assertEqual(problem.language_limits.get().time_limit, 2)
        self.save(DraftChanges(problem_fields={'description': '# Updated'}),
                  problem_id=first.problem_id, expected_revision=1)
        self.assertEqual(problem.language_limits.get().memory_limit, 524288)

    def test_updating_existing_language_limit_does_not_fail_unique_validation(self):
        limits = [{'language_id': self.language.pk, 'time_limit': 2, 'memory_limit': 524288}]
        first = self.save(DraftChanges(problem_fields=self.changes().problem_fields, language_limits=limits))
        limits = [{'language_id': self.language.pk, 'time_limit': 3, 'memory_limit': 524288}]
        self.save(DraftChanges(language_limits=limits), problem_id=first.problem_id, expected_revision=1)
        self.assertEqual(Problem.objects.get(pk=first.problem_id).language_limits.get().time_limit, 3)

    def test_empty_editorial_cannot_remain_public(self):
        first = self.save()
        solution = Problem.objects.get(pk=first.problem_id).solution
        solution.is_public = True
        solution.save()
        self.save(DraftChanges(solution_fields={'content': ''}), problem_id=first.problem_id,
                  expected_revision=ProblemAuthoringState.objects.get(problem_id=first.problem_id).revision)
        solution.refresh_from_db()
        self.assertFalse(solution.is_public)

    def test_legacy_active_import_rejects_grading_mutation_even_without_model_field_change(self):
        from judge.models import ProblemPackageImport
        problem = self.make_problem()
        problem.authors.add(self.user.profile)
        ProblemPackageImport.objects.create(owner=self.user.profile, problem=problem, state='JUDGING')
        with self.assertRaises(AuthoringError):
            self.save(DraftChanges(language_limits=[{
                'language_id': self.language.pk, 'time_limit': 2, 'memory_limit': 524288,
            }]), problem_id=problem.pk, expected_revision=0)
        self.assertFalse(problem.language_limits.exists())

    def test_creation_requires_ability_to_edit_own_problem(self):
        user = create_user('addonly', user_permissions=('add_problem',))
        with self.assertRaises(AuthoringError):
            self.api().save_draft(AuthoringContext(user.pk), self.changes(), problem_id=None,
                                  expected_revision=None, request_token=uuid.uuid4())
        self.assertFalse(Problem.objects.exists())

    def test_test_upload_creates_durable_operation_and_cannot_be_reused_for_another_problem(self):
        from judge.problem_authoring.uploads import receive_upload
        upload = receive_upload(self.context, make_zip({'1.in': '1', '1.out': '2'}), 'TESTS')
        changes = self.changes()
        changes = DraftChanges(problem_fields=changes.problem_fields, test_upload_id=upload.pk)
        result = self.save(changes)
        operation = ProblemDataOperation.objects.get(pk=result.operation_id)
        self.assertEqual(operation.problem_id, result.problem_id)
        self.assertEqual(operation.state, 'PENDING')
        self.assertEqual(operation.config['cases'][0]['input_file'], '1.in')
        self.assertEqual(ProblemAuthoringState.objects.get(problem_id=result.problem_id).data_state, 'PENDING')
        upload.refresh_from_db()
        self.assertEqual(upload.consumed_by_id, result.problem_id)
        with self.assertRaises(AuthoringError):
            self.save(DraftChanges(problem_fields=self.changes(code='another').problem_fields,
                                   test_upload_id=upload.pk))
        self.assertEqual(Problem.objects.count(), 1)

    def test_explicit_checker_and_bulk_points_reach_operation(self):
        from judge.problem_authoring.uploads import receive_upload
        upload = receive_upload(self.context, make_zip({'1.in': '1', '1.out': '2'}), 'TESTS')
        result = self.save(DraftChanges(problem_fields=self.changes().problem_fields, test_upload_id=upload.pk,
                                        data_fields={'checker': 'identical', 'test_points': '3'}))
        operation = ProblemDataOperation.objects.get(pk=result.operation_id)
        self.assertEqual(operation.config['checker'], 'identical')
        self.assertEqual(operation.config['cases'][0]['points'], '3')

    def test_fractional_test_weights_are_rejected_for_integer_storage(self):
        from judge.problem_authoring.uploads import receive_upload
        upload = receive_upload(self.context, make_zip({'1.in': '1', '1.out': '2'}), 'TESTS')
        with self.assertRaises(AuthoringError):
            self.save(DraftChanges(problem_fields=self.changes().problem_fields, test_upload_id=upload.pk,
                                   data_fields={'test_points': '0.5'}))
        self.assertFalse(Problem.objects.exists())

    def test_simple_editor_cannot_replace_batched_dataset(self):
        from judge.models import ProblemData, ProblemTestCase
        from judge.problem_authoring.uploads import receive_upload
        result = self.save()
        problem = Problem.objects.get(pk=result.problem_id)
        ProblemData.objects.create(problem=problem)
        ProblemTestCase.objects.create(dataset=problem, order=1, type='S', points=1, is_pretest=False)
        upload = receive_upload(self.context, make_zip({'1.in': '1', '1.out': '2'}), 'TESTS')
        with self.assertRaises(AuthoringError):
            self.save(DraftChanges(test_upload_id=upload.pk), problem_id=problem.pk, expected_revision=1)
        self.assertEqual(problem.cases.get().type, 'S')

    def test_simple_editor_cannot_replace_advanced_dataset(self):
        from judge.models import ProblemData
        from judge.problem_authoring.uploads import receive_upload
        result = self.save()
        problem = Problem.objects.get(pk=result.problem_id)
        ProblemData.objects.create(problem=problem, grader='interactive')
        upload = receive_upload(self.context, make_zip({'1.in': '1', '1.out': '2'}), 'TESTS')
        with self.assertRaises(AuthoringError):
            self.save(DraftChanges(test_upload_id=upload.pk), problem_id=problem.pk, expected_revision=1)
        self.assertEqual(problem.data_files.grader, 'interactive')

    def test_one_nonterminal_data_operation_per_problem(self):
        from judge.problem_authoring.uploads import receive_upload
        upload = receive_upload(self.context, make_zip({'1.in': '1', '1.out': '2'}), 'TESTS')
        result = self.save(DraftChanges(problem_fields=self.changes().problem_fields, test_upload_id=upload.pk))
        with self.assertRaises(AuthoringError):
            self.save(DraftChanges(test_upload_id=upload.pk), problem_id=result.problem_id, expected_revision=1)
        self.assertEqual(ProblemDataOperation.objects.count(), 1)
        self.save(DraftChanges(problem_fields={'description': '# Safe edit'}),
                  problem_id=result.problem_id, expected_revision=1)
        self.assertEqual(Problem.objects.get(pk=result.problem_id).description, '# Safe edit')
