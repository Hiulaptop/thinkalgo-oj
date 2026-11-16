import tempfile
from unittest.mock import patch

from django.test import TestCase, override_settings

from judge.models import Language, Problem, ProblemGroup, ProblemType
from judge.models.tests.util import create_user
from judge.tests.test_problem_package_parser import make_package
from judge.utils.problem_package_import import create_draft, confirm_import


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

    def test_upload_page(self):
        self.client.force_login(self.user)
        response = self.client.get('/problems/import-zip/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'statement.md')

    def test_preview_page(self):
        record = create_draft(self.user, make_package())
        self.client.force_login(self.user)
        response = self.client.get('/problems/import-zip/%s/' % record.pk)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Các số phân biệt')

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
