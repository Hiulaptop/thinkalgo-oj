import tempfile
from unittest.mock import patch

from django.test import TestCase, override_settings

from judge.models import Language, Problem, ProblemGroup, ProblemType
from judge.models.tests.util import create_user
from judge.tests.test_problem_package_parser import make_package
from judge.utils.problem_package_import import confirm_import, create_draft


class PackageImportTest(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings_override = override_settings(PROBLEM_PACKAGE_ROOT=self.temp.name + '/private',
                                                   DMOJ_PROBLEM_DATA_ROOT=self.temp.name + '/tests')
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        from judge.models import problem_data_storage
        storage_patch = patch.object(problem_data_storage, '_location', self.temp.name + '/tests')
        storage_patch.start()
        for key in ('location', 'base_location'):
            problem_data_storage.__dict__.pop(key, None)
        self.addCleanup(storage_patch.stop)
        self.user = create_user('importer', is_superuser=True, is_staff=True)
        self.group = ProblemGroup.objects.create(name='Package')
        self.kind = ProblemType.objects.create(name='Package')
        self.language = Language.objects.create(key='CPP20', name='C++20', short_name='C++20')
        self.metadata = dict(code='packagetest', name='Package test', time_limit=1, memory_limit=524288,
                             points=100, group=self.group.pk, types=[self.kind.pk], language=self.language.pk)

    @patch('judge.tasks.problem_package.run_import.delay')
    def test_create_hidden_problem_and_tests(self, enqueue):
        record = create_draft(self.user, make_package())
        confirm_import(record.pk, self.user, self.metadata)
        confirm_import(record.pk, self.user, self.metadata)
        record.refresh_from_db()
        self.assertEqual(Problem.objects.filter(code='packagetest').count(), 1)
        self.assertFalse(record.problem.is_public)

    @patch('judge.tasks.problem_package.dispatch_reference.delay')
    @patch('judge.tasks.problem_package.publish_problem_to_r2')
    @patch('judge.tasks.problem_package.run_import.delay')
    def test_publish_retry_keeps_one_private_submission(self, enqueue, publish, dispatch):
        from judge.tasks.problem_package import run_import
        publish.return_value = {'version': 'test-release', 'sha256': 'a' * 64}
        record = create_draft(self.user, make_package())
        confirm_import(record.pk, self.user, self.metadata)
        with override_settings(BRIDGED_R2_PROBLEMS=True):
            run_import(str(record.pk))
            run_import(str(record.pk))
        record.refresh_from_db()
        self.assertEqual(record.problem.submission_set.count(), 1)
        self.assertEqual(record.submission.source.source, 'int main() {}')
        student = create_user('student')
        self.assertFalse(record.submission.can_see_detail(student))
        self.assertTrue(record.submission.can_see_detail(self.user))
        self.assertFalse(record.problem.solution.is_public)
        self.assertEqual(record.problem.cases.count(), 2)
        self.assertEqual(record.problem.memory_limit, 524288)
        self.assertTrue(record.problem.data_files.has_yml())

    def test_legacy_editor_get_does_not_finalize_reference_run(self):
        from judge.models import ProblemPackageImport, Submission
        problem = Problem.objects.create(code='readonlylegacy', name='Legacy', group=self.group,
                                         time_limit=1, memory_limit=262144, points=100)
        submission = Submission.objects.create(problem=problem, user=self.user.profile,
                                               language=self.language, status='D', result='AC')
        record = ProblemPackageImport.objects.create(owner=self.user.profile, problem=problem,
                                                     submission=submission, state='JUDGING')
        self.client.force_login(self.user)
        with override_settings(PROBLEM_AUTHORING_ENABLED=False):
            response = self.client.get('/problem/readonlylegacy/edit')
        self.assertEqual(response.status_code, 200)
        record.refresh_from_db()
        self.assertEqual(record.state, 'JUDGING')

    def test_upload_page(self):
        self.client.force_login(self.user)
        response = self.client.get('/problems/import-zip/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'statement.md')

    def test_load_zip_uses_existing_create_form_without_creating_problem(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from judge.forms import ProblemEditForm
        self.client.force_login(self.user)
        before = Problem.objects.count()
        response = self.client.post('/problems/create', {
            'action': 'load_package',
            'package': SimpleUploadedFile('package.zip', make_package().getvalue()),
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Problem.objects.count(), before)
        self.assertIsInstance(response.context['form'], ProblemEditForm)
        self.assertEqual(response.context['form']['name'].value(), 'Các số phân biệt')
        self.assertEqual(response.context['form']['memory_limit'].value(), 524288)
        self.assertEqual(response.context['solution_formset'].forms[0]['content'].value(), '# Lời giải')

    def test_missing_zip_returns_form_error(self):
        self.client.force_login(self.user)
        response = self.client.post('/problems/create', {'action': 'load_package'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Choose a ZIP file.')

    def test_preview_page(self):
        record = create_draft(self.user, make_package())
        self.client.force_login(self.user)
        response = self.client.get('/problems/import-zip/%s/' % record.pk, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Các số phân biệt')

    @patch('judge.tasks.problem_package.run_import.delay')
    def test_create_from_editor_preserves_user_changes(self, enqueue):
        record = create_draft(self.user, make_package())
        self.client.force_login(self.user)
        preview = self.client.get('/problems/create', {'package_id': str(record.pk)})
        prefix = preview.context['solution_formset'].prefix
        payload = {
            'package_id': str(record.pk), 'code': 'editedpackage', 'name': 'Edited title',
            'description': 'Edited statement', 'time_limit': '1', 'memory_limit': '524288',
            'points': '1', 'partial': 'on', 'group': self.group.pk, 'types': [self.kind.pk],
            'submission_source_visibility_mode': 'F', 'testcase_visibility_mode': 'A',
            'reference_language': self.language.pk,
            prefix + '-TOTAL_FORMS': '1', prefix + '-INITIAL_FORMS': '0',
            prefix + '-MIN_NUM_FORMS': '0', prefix + '-MAX_NUM_FORMS': '1',
            prefix + '-0-content': 'Edited editorial', prefix + '-0-publish_on': '2026-11-17',
        }
        response = self.client.post('/problems/create', payload)
        if response.status_code == 200:
            self.fail(str(response.context['form'].errors) + str(response.context['solution_formset'].errors))
        self.assertEqual(response.status_code, 302)
        record.refresh_from_db()
        self.assertEqual(record.problem.description, 'Edited statement')
        self.assertEqual(record.problem.solution.content, 'Edited editorial')
        self.assertEqual(record.problem.cases.count(), 2)
        response = self.client.get(response.url)
        self.assertEqual(response.status_code, 200)

    @patch('judge.tasks.problem_package.run_import.delay')
    def test_publish_failure_preserves_problem(self, enqueue):
        from judge.tasks.problem_package import run_import
        record = create_draft(self.user, make_package())
        confirm_import(record.pk, self.user, self.metadata)
        with override_settings(BRIDGED_R2_PROBLEMS=False):
            run_import(str(record.pk))
        record.refresh_from_db()
        self.assertEqual(record.state, 'FAILED')
        self.assertIsNone(record.submission_id)
        self.assertFalse(record.problem.is_public)
