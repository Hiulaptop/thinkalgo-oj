import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from judge.models import Problem
from judge.models.tests.util import create_user
from judge.tests.authoring_helpers import AuthoringTestMixin, make_zip


@override_settings(ROOT_URLCONF='judge.tests.authoring_urls', PROBLEM_AUTHORING_ENABLED=True)
class AuthoringViewTest(AuthoringTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def payload(self):
        return {'action': 'save_draft', 'request_token': str(uuid.uuid4()), 'revision': '0',
                'code': 'viewdraft', 'name': 'View draft', 'description': '# Statement',
                'time_limit': '1', 'memory_mb': '256', 'points': '100', 'group': self.group.pk,
                'types': [self.kind.pk], 'submission_source_visibility_mode': 'F',
                'testcase_visibility_mode': 'A', 'editorial': '# Edited editorial'}

    def test_main_page_contains_test_and_editorial_upload_sections(self):
        response = self.client.get('/problems/create')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="tests_file"')
        self.assertContains(response, 'name="editorial"')
        self.assertContains(response, 'name="reference_file"')
        self.assertContains(response, 'problem-authoring.js')

    def test_nonstaff_can_save_complete_form_with_tests(self):
        user = create_user('siteauthor', user_permissions=('add_problem', 'edit_own_problem'))
        self.client.force_login(user)
        payload = self.payload()
        payload['tests_file'] = SimpleUploadedFile('tests.zip', make_zip({'1.in': '1', '1.out': '2'}).getvalue())
        response = self.client.post('/problems/create', payload)
        self.assertEqual(response.status_code, 302)
        problem = Problem.objects.get(code='viewdraft')
        self.assertEqual(problem.memory_limit, 262144)
        self.assertEqual(problem.solution.content, '# Edited editorial')
        self.assertEqual(problem.authoring_state.data_state, 'PENDING')
        self.assertFalse(problem.is_public)
        self.assertEqual(response.url, '/problem/viewdraft/edit')

    def test_bad_zip_keeps_editorial_and_metadata(self):
        payload = self.payload()
        payload['tests_file'] = SimpleUploadedFile('bad.zip', b'bad')
        response = self.client.post('/problems/create', payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '# Edited editorial')
        self.assertContains(response, 'View draft')
        self.assertFalse(Problem.objects.exists())

    def test_invalid_form_retains_received_test_upload(self):
        payload = self.payload()
        payload['name'] = ''
        payload['tests_file'] = SimpleUploadedFile('tests.zip', make_zip({'1.in': '1', '1.out': '2'}).getvalue())
        response = self.client.post('/problems/create', payload)
        self.assertEqual(response.status_code, 200)
        from judge.models import ProblemAuthoringUpload
        upload = ProblemAuthoringUpload.objects.get(kind='TESTS')
        self.assertContains(response, str(upload.pk))
        self.assertContains(response, '# Edited editorial')
        self.assertFalse(Problem.objects.exists())

    def test_pdf_url_is_saved_with_draft(self):
        from unittest.mock import patch
        payload = self.payload()
        payload['statement_file'] = SimpleUploadedFile('statement.pdf', b'%PDF-1.4')
        with patch('judge.views.widgets.pdf_statement_uploader', return_value='https://example.invalid/statement.pdf'):
            response = self.client.post('/problems/create', payload)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Problem.objects.get(code='viewdraft').pdf_url, 'https://example.invalid/statement.pdf')

    def test_org_create_preserves_scope(self):
        from judge.models import Organization
        organization = Organization.objects.create(name='Team', slug='team', short_name='Team', about='')
        organization.admins.add(self.user.profile)
        payload = self.payload()
        payload['code'] = 'team_draft'
        payload.pop('types')
        response = self.client.post('/organization/team/problem-create', payload)
        self.assertEqual(response.status_code, 302)
        problem = Problem.objects.get(code='team_draft')
        self.assertEqual(problem.organization_id, organization.pk)
        self.assertTrue(problem.is_organization_private)

    def test_bad_replacement_zip_keeps_editorial(self):
        payload = self.payload()
        payload['action'] = 'upload_package'
        payload['package_file'] = SimpleUploadedFile('bad.zip', b'bad')
        response = self.client.post('/problems/create', payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '# Edited editorial')

    def test_package_apply_only_changes_confirmed_sections(self):
        from judge.models import ProblemAuthoringUpload
        payload = self.payload()
        payload['action'] = 'upload_package'
        payload['package_file'] = SimpleUploadedFile('package.zip', make_zip({
            'statement.md': '# Imported title', 'editorial.md': '# Imported editorial',
            'tests/1.in': '1', 'tests/1.out': '2',
        }).getvalue())
        response = self.client.post('/problems/create', payload)
        self.assertEqual(response.status_code, 200)
        upload = ProblemAuthoringUpload.objects.get(kind='PACKAGE')
        payload.pop('package_file')
        payload.update(action='apply_package', package_upload_id=str(upload.pk), replace_statement='on')
        response = self.client.post('/problems/create', payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '# Imported title')
        self.assertContains(response, '# Edited editorial')
        self.assertFalse(Problem.objects.exists())

    def test_user_without_permission_gets_403(self):
        user = create_user('viewer')
        self.client.force_login(user)
        response = self.client.get('/problems/create')
        self.assertEqual(response.status_code, 403)

    def test_admin_add_enters_common_editor(self):
        response = self.client.get('/admin/judge/problem/add/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/problems/create')

    def test_malformed_verification_token_is_not_server_error(self):
        from judge.models import ProblemAuthoringState
        problem = self.make_problem()
        problem.authors.add(self.user.profile)
        ProblemAuthoringState.objects.create(problem=problem, revision=1, data_state='READY')
        response = self.client.post('/problem/' + problem.code + '/edit', {
            'action': 'verify', 'revision': '1', 'request_token': 'bad-token',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reload')

    def test_pdf_storage_failure_keeps_form_without_creating_problem(self):
        from unittest.mock import patch
        payload = self.payload()
        payload['statement_file'] = SimpleUploadedFile('statement.pdf', b'%PDF-1.4')
        with patch('judge.views.widgets.pdf_statement_uploader', side_effect=OSError('private/storage')):
            response = self.client.post('/problems/create', payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '# Edited editorial')
        self.assertNotContains(response, 'private/storage')
        self.assertFalse(Problem.objects.exists())

    def test_private_source_download_requires_owner_and_is_not_cached(self):
        import io
        from judge.problem_authoring.types import AuthoringContext
        from judge.problem_authoring.uploads import receive_upload
        upload = receive_upload(AuthoringContext(self.user.pk), io.BytesIO(b'private source'), 'SOURCE')
        path = '/problems/authoring/uploads/' + str(upload.pk)
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), b'private source')
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        other = create_user('otherauthor', is_superuser=True)
        self.client.force_login(other)
        self.assertEqual(self.client.get(path).status_code, 404)

    def test_csrf_protects_editor_mutations(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.post('/problems/create', self.payload())
        self.assertNotEqual(response.status_code, 200)
        self.assertFalse(Problem.objects.exists())

    def test_consumed_package_without_import_permission_does_not_break_editor(self):
        user = create_user('plainauthor', user_permissions=('add_problem', 'edit_own_problem'))
        self.client.force_login(user)
        response = self.client.get('/problems/create')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'value="upload_package"')
        self.assertContains(response, 'name="tests_file"')

    def test_deleted_problem_cannot_be_edited_in_shared_editor(self):
        from django.utils import timezone
        problem = self.make_problem()
        problem.authors.add(self.user.profile)
        Problem.objects.filter(pk=problem.pk).update(deleted_at=timezone.now())
        response = self.client.get('/problem/' + problem.code + '/edit')
        self.assertEqual(response.status_code, 404)

    def test_edit_get_preserves_existing_limits_points_and_partial(self):
        problem = self.make_problem()
        problem.authors.add(self.user.profile)
        problem.time_limit = 3
        problem.points = 2
        problem.partial = False
        problem.save()
        response = self.client.get('/problem/' + problem.code + '/edit')
        form = response.context['form']
        self.assertEqual(form['time_limit'].value(), 3)
        self.assertEqual(form['points'].value(), 2)
        self.assertFalse(form['partial'].value())

    def test_pdf_upload_is_retained_when_other_form_fields_are_invalid(self):
        from judge.models import ProblemAuthoringUpload
        payload = self.payload()
        payload['name'] = ''
        payload['statement_file'] = SimpleUploadedFile('statement.pdf', b'%PDF-1.4')
        response = self.client.post('/problems/create', payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ProblemAuthoringUpload.objects.filter(kind='PDF').count(), 1)
        upload = ProblemAuthoringUpload.objects.get(kind='PDF')
        self.assertContains(response, str(upload.pk))

    def test_language_allowlist_is_available_in_shared_editor(self):
        response = self.client.get('/problems/create')
        self.assertContains(response, 'name="allowed_languages"')

    def test_editorial_schedule_and_authors_are_editable(self):
        response = self.client.get('/problems/create')
        self.assertContains(response, 'name="editorial_publish_on"')
        self.assertContains(response, 'name="editorial_authors"')

    def test_language_limit_controls_are_preserved_from_existing_editor(self):
        problem = self.make_problem()
        problem.authors.add(self.user.profile)
        response = self.client.get('/problem/' + problem.code + '/edit')
        self.assertContains(response, 'Giới hạn theo ngôn ngữ')
        self.assertIn('language_limit_formset', response.context)

    def test_retry_data_broker_outage_is_a_recoverable_form_error(self):
        from unittest.mock import patch
        from judge.models import ProblemAuthoringState, ProblemDataOperation
        problem = self.make_problem()
        problem.authors.add(self.user.profile)
        operation = ProblemDataOperation.objects.create(problem=problem, target_revision=1, state='FAILED')
        ProblemAuthoringState.objects.create(problem=problem, revision=1, grading_revision=1, data_state='FAILED',
                                             current_operation=operation)
        with patch('judge.tasks.problem_authoring.process_authoring_data.delay', side_effect=OSError('offline')):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post('/problem/' + problem.code + '/edit',
                                            {'action': 'retry_data', 'revision': '1'})
        self.assertEqual(response.status_code, 302)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'PENDING')

    def test_existing_kilobyte_memory_limit_is_not_rounded_on_edit(self):
        problem = self.make_problem()
        problem.authors.add(self.user.profile)
        problem.memory_limit = 100000
        problem.save()
        response = self.client.get('/problem/' + problem.code + '/edit')
        self.assertEqual(float(response.context['form']['memory_mb'].value()), 97.65625)

    def test_organization_runtime_source_creation_without_global_add_permission(self):
        from judge.models import Organization
        user = create_user('orgonlysite', user_permissions=('create_organization_problem', 'edit_own_problem'))
        organization = Organization.objects.create(name='Team', slug='team', short_name='Team', about='')
        organization.admins.add(user.profile)
        self.client.force_login(user)
        payload = self.payload()
        payload['code'] = 'team_source'
        payload.pop('types')
        payload['allowed_languages'] = [self.language.pk]
        payload['reference_language'] = self.language.pk
        payload['reference_file'] = SimpleUploadedFile('solution.cpp', b'int main() {}')
        response = self.client.post('/organization/team/problem-create', payload)
        self.assertEqual(response.status_code, 302)
        problem = Problem.objects.get(code='team_source')
        self.assertEqual(problem.reference_source.language_id, self.language.pk)
        self.assertEqual(problem.organization_id, organization.pk)

    def test_stale_edit_post_retains_user_text_without_overwriting_database(self):
        from judge.models import ProblemAuthoringState
        problem = self.make_problem('viewdraft')
        problem.authors.add(self.user.profile)
        ProblemAuthoringState.objects.create(problem=problem, revision=2)
        payload = self.payload()
        payload['revision'] = '1'
        payload['description'] = '# My unsaved draft'
        response = self.client.post('/problem/viewdraft/edit', payload)
        self.assertEqual(response.status_code, 409)
        self.assertContains(response, '# My unsaved draft', status_code=409)
        problem.refresh_from_db()
        self.assertEqual(problem.description, '# Statement')

    def test_verify_action_does_not_store_unsaved_file_selection(self):
        from judge.models import ProblemAuthoringState, ProblemAuthoringUpload
        problem = self.make_problem()
        problem.authors.add(self.user.profile)
        ProblemAuthoringState.objects.create(problem=problem, revision=1, data_state='READY')
        self.client.post('/problem/' + problem.code + '/edit', {
            'action': 'verify', 'revision': '1', 'request_token': str(uuid.uuid4()),
            'reference_file': SimpleUploadedFile('new.cpp', b'unsaved source'),
        })
        self.assertEqual(ProblemAuthoringUpload.objects.count(), 0)

    def test_verifying_unadopted_legacy_problem_returns_guidance_not_500(self):
        problem = self.make_problem()
        problem.authors.add(self.user.profile)
        response = self.client.post('/problem/' + problem.code + '/edit', {
            'action': 'verify', 'revision': '0', 'request_token': str(uuid.uuid4()),
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Save')

    def test_reference_runtime_without_source_reports_error_before_saving(self):
        payload = self.payload()
        payload['reference_language'] = self.language.pk
        payload['allowed_languages'] = [self.language.pk]
        response = self.client.post('/problems/create', payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'source')
        self.assertFalse(Problem.objects.exists())

    def test_uploaded_tests_expose_individual_weights_and_order(self):
        payload = self.payload()
        payload['action'] = 'upload_tests'
        payload['tests_file'] = SimpleUploadedFile(
            'tests.zip', make_zip({'1.in': '1', '1.out': '2', '2.in': '3', '2.out': '4'}).getvalue(),
        )
        response = self.client.post('/problems/create', payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="testcases-0-points"')
        self.assertContains(response, 'name="testcases-0-order"')

    def test_per_test_weights_and_order_reach_durable_operation(self):
        import io
        from judge.models import ProblemDataOperation
        from judge.problem_authoring.types import AuthoringContext
        from judge.problem_authoring.uploads import receive_upload
        upload = receive_upload(AuthoringContext(self.user.pk), io.BytesIO(
            make_zip({'1.in': '1', '1.out': '2', '2.in': '3', '2.out': '4'}).getvalue(),
        ), 'TESTS')
        payload = self.payload()
        payload.update(tests_upload_id=str(upload.pk), **{
            'testcases-TOTAL_FORMS': '2', 'testcases-INITIAL_FORMS': '2',
            'testcases-0-input_file': '1.in', 'testcases-0-output_file': '1.out',
            'testcases-0-order': '2', 'testcases-0-points': '3',
            'testcases-1-input_file': '2.in', 'testcases-1-output_file': '2.out',
            'testcases-1-order': '1', 'testcases-1-points': '7', 'testcases-1-is_pretest': 'on',
        })
        response = self.client.post('/problems/create', payload)
        self.assertEqual(response.status_code, 302)
        cases = ProblemDataOperation.objects.get().config['cases']
        self.assertEqual([(case['input_file'], case['points']) for case in cases], [('2.in', '7'), ('1.in', '3')])
        self.assertTrue(cases[0]['is_pretest'])

    def test_existing_problem_can_preview_and_apply_its_new_package(self):
        from judge.models import ProblemAuthoringUpload
        problem = self.make_problem('viewdraft')
        problem.authors.add(self.user.profile)
        payload = self.payload()
        payload.update(action='upload_package', package_file=SimpleUploadedFile(
            'package.zip', make_zip({'statement.md': '# Replacement statement'}).getvalue(),
        ))
        response = self.client.post('/problem/viewdraft/edit', payload)
        self.assertEqual(response.status_code, 200)
        upload = ProblemAuthoringUpload.objects.get(kind='PACKAGE')
        payload.pop('package_file')
        payload.update(action='apply_package', package_upload_id=str(upload.pk), replace_statement='on')
        response = self.client.post('/problem/viewdraft/edit', payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '# Replacement statement')
        self.assertNotContains(response, 'Upload is unavailable')
        problem.refresh_from_db()
        self.assertEqual(problem.description, '# Statement')

    def test_new_test_upload_replaces_old_preview_formset(self):
        payload = self.payload()
        payload.update(action='upload_tests', tests_file=SimpleUploadedFile(
            'tests.zip', make_zip({'new.in': '1', 'new.out': '2'}).getvalue(),
        ), **{
            'testcases-TOTAL_FORMS': '1', 'testcases-INITIAL_FORMS': '1',
            'testcases-0-input_file': 'old.in', 'testcases-0-output_file': 'old.out',
            'testcases-0-order': '1', 'testcases-0-points': '5',
        })
        response = self.client.post('/problems/create', payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="new.in"')
        self.assertNotContains(response, 'value="old.in"')
        self.assertContains(response, '# Edited editorial')

    def test_editor_shows_private_saved_artifact_downloads(self):
        import io
        from judge.models import ProblemReferenceSource
        from judge.problem_authoring.types import AuthoringContext
        from judge.problem_authoring.uploads import receive_upload
        problem = self.make_problem('viewdraft')
        problem.authors.add(self.user.profile)
        context = AuthoringContext(self.user.pk)
        tests = receive_upload(context, make_zip({'1.in': '1', '1.out': '2'}), 'TESTS', problem_id=problem.pk)
        source = receive_upload(context, io.BytesIO(b'private source'), 'SOURCE', problem_id=problem.pk)
        for upload in (tests, source):
            upload.consumed_by = problem
            upload.save()
        ProblemReferenceSource.objects.create(problem=problem, upload=source, language=self.language)
        response = self.client.get('/problem/viewdraft/edit')
        self.assertEqual(response.status_code, 200)
        for upload in (tests, source):
            self.assertContains(response, '/problems/authoring/uploads/' + str(upload.pk))
        self.assertNotContains(response, 'private source')

    def test_readonly_status_reports_saved_state_without_exposing_content(self):
        from judge.models import ProblemAuthoringState
        problem = self.make_problem('viewdraft')
        problem.authors.add(self.user.profile)
        state = ProblemAuthoringState.objects.create(problem=problem, revision=3, grading_revision=2,
                                                     data_state='MISSING')
        response = self.client.get('/problem/viewdraft/edit', {'status': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        payload = response.json()
        self.assertEqual(payload['revision'], 3)
        self.assertEqual(payload['data_state'], 'MISSING')
        self.assertFalse(payload['can_verify'])
        self.assertFalse(payload['can_publish'])
        self.assertNotIn('description', payload)
        state.refresh_from_db()
        self.assertEqual(state.revision, 3)
        self.assertEqual(response['Cache-Control'], 'private, no-store')

    def test_organization_subdomain_cannot_cross_scope_in_shared_editor(self):
        from django.test import RequestFactory
        from judge.models import Organization
        from judge.problem_authoring.views import OrganizationProblemAuthoringCreateView
        first = Organization.objects.create(name='First', slug='first', short_name='First', about='')
        second = Organization.objects.create(name='Second', slug='second', short_name='Second', about='')
        second.admins.add(self.user.profile)
        request = RequestFactory().get('/organization/second/problem-create')
        request.user = self.user
        request.profile = self.user.profile
        request.in_contest = False
        request.organization = first
        from judge.problem_authoring.types import AuthoringError
        view = OrganizationProblemAuthoringCreateView()
        view.setup(request, slug='second')
        with self.assertRaises(AuthoringError) as denied:
            view._context()
        self.assertEqual(denied.exception.code, 'permission_denied')

    def test_editorial_authors_can_be_cleared_from_shared_form(self):
        from django.utils import timezone
        from judge.models import Solution
        problem = self.make_problem('viewdraft')
        problem.authors.add(self.user.profile)
        solution = Solution.objects.create(problem=problem, content='# Existing editorial', publish_on=timezone.now())
        solution.authors.add(self.user.profile)
        payload = self.payload()
        payload['editorial_authors_present'] = '1'
        response = self.client.post('/problem/viewdraft/edit', payload)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(solution.authors.exists())

    def test_editorial_schedule_has_html_datetime_local_format(self):
        from datetime import datetime, timezone
        from judge.models import Solution
        problem = self.make_problem('viewdraft')
        problem.authors.add(self.user.profile)
        schedule = datetime(2026, 12, 3, 10, 30, tzinfo=timezone.utc)
        Solution.objects.create(problem=problem, content='# Editorial', publish_on=schedule)
        response = self.client.get('/problem/viewdraft/edit')
        self.assertEqual(response.status_code, 200)
        field = response.context['form']['editorial_publish_on']
        self.assertIn('T', field.as_widget())
        from django.utils.timezone import localtime
        self.assertIn(localtime(schedule).strftime('%Y-%m-%dT%H:%M'), field.as_widget())

    def test_uploaded_test_point_bulk_action_preserves_other_sections(self):
        import io
        from judge.problem_authoring.types import AuthoringContext
        from judge.problem_authoring.uploads import receive_upload
        upload = receive_upload(AuthoringContext(self.user.pk), io.BytesIO(
            make_zip({'1.in': '1', '1.out': '2'}).getvalue(),
        ), 'TESTS')
        payload = self.payload()
        payload.update(action='apply_test_points', tests_upload_id=str(upload.pk), test_points='9', **{
            'testcases-TOTAL_FORMS': '1', 'testcases-INITIAL_FORMS': '1',
            'testcases-0-input_file': '1.in', 'testcases-0-output_file': '1.out',
            'testcases-0-order': '1', 'testcases-0-points': '3',
        })
        response = self.client.post('/problems/create', payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="testcases-0-points" value="9"')
        self.assertContains(response, '# Edited editorial')
        self.assertFalse(Problem.objects.exists())

    def test_privileged_large_test_preview_is_not_truncated_by_post_field_limit(self):
        from django.conf import settings
        self.assertGreaterEqual(settings.DATA_UPLOAD_MAX_NUMBER_FIELDS or 0, 6 * 4998 + 1000)

    def test_privileged_author_can_submit_more_than_one_thousand_test_rows(self):
        from judge.models import ProblemDataOperation
        from judge.problem_authoring.types import AuthoringContext
        from judge.problem_authoring.uploads import receive_upload
        files = {str(index) + suffix: '1' for index in range(1002) for suffix in ('.in', '.out')}
        upload = receive_upload(AuthoringContext(self.user.pk), make_zip(files), 'TESTS')
        payload = self.payload()
        payload.update(tests_upload_id=str(upload.pk), **{
            'testcases-TOTAL_FORMS': '1002', 'testcases-INITIAL_FORMS': '1002',
        })
        for index, case in enumerate(upload.manifest['tests']):
            for field in ('input_file', 'output_file', 'order', 'points'):
                payload['testcases-%d-%s' % (index, field)] = str(case[field])
        response = self.client.post('/problems/create', payload)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(ProblemDataOperation.objects.get().config['cases']), 1002)

    def test_unknown_action_is_bad_request(self):
        response = self.client.post('/problems/create', {'action': 'unknown'})
        self.assertEqual(response.status_code, 400)
