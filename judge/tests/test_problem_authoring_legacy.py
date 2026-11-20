import uuid

from django.test import TestCase, override_settings

from judge.problem_authoring.types import AuthoringContext
from judge.tests.authoring_helpers import AuthoringTestMixin, make_zip
from judge.utils.problem_package_import import create_draft


@override_settings(ROOT_URLCONF='judge.tests.authoring_urls', PROBLEM_AUTHORING_ENABLED=True)
class AuthoringLegacyTest(AuthoringTestMixin, TestCase):
    def test_old_unconfirmed_package_opens_without_creating_problem(self):
        from judge.models import Problem, ProblemAuthoringUpload
        self.client.force_login(self.user)
        record = create_draft(self.user, make_zip({
            'statement.md': '# Legacy package', 'editorial.md': '# Legacy editorial',
            'solution.cpp': 'int main() {}', 'tests/1.in': '1', 'tests/1.out': '2',
        }))
        response = self.client.get('/problems/create', {'package_id': str(record.pk)})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ProblemAuthoringUpload.objects.exists())
        self.assertContains(response, 'value="adopt_legacy"')
        response = self.client.post('/problems/create', {
            'action': 'adopt_legacy', 'legacy_package_id': str(record.pk),
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ProblemAuthoringUpload.objects.count(), 1)
        self.assertContains(response, '# Legacy package')
        self.assertContains(response, '# Legacy editorial')
        self.assertFalse(Problem.objects.exists())

    def test_legacy_check_command_is_read_only(self):
        import io
        import json
        from django.core.management import call_command
        from judge.models import ProblemPackageImport
        ProblemPackageImport.objects.create(owner=self.user.profile, state='PUBLISHING')
        output = io.StringIO()
        call_command('reconcile_problem_authoring', '--legacy-check', stdout=output)
        self.assertEqual(json.loads(output.getvalue())['PUBLISHING'], 1)
        self.assertEqual(ProblemPackageImport.objects.get().state, 'PUBLISHING')

    def test_finished_legacy_adoption_command_is_idempotent_and_never_submits(self):
        import io
        from unittest.mock import patch
        from django.core.management import call_command
        from judge.models import ProblemAuthoringState, ProblemPackageImport
        problem = self.make_problem()
        ProblemPackageImport.objects.create(owner=self.user.profile, problem=problem, state='FINISHED')
        with patch('judge.judgeapi.judge_submission', side_effect=AssertionError('must not submit')):
            call_command('reconcile_problem_authoring', '--adopt-legacy-finished', stdout=io.StringIO())
            call_command('reconcile_problem_authoring', '--adopt-legacy-finished', stdout=io.StringIO())
        state = ProblemAuthoringState.objects.get(problem=problem)
        self.assertEqual(state.data_state, 'MISSING')
        self.assertEqual(state.revision, 0)
        self.assertFalse(problem.reference_runs.exists())

    def test_invalid_legacy_id_returns_validation_error(self):
        from judge.problem_authoring.legacy import adopt_legacy_draft
        from judge.problem_authoring.types import AuthoringError
        with self.assertRaises(AuthoringError):
            adopt_legacy_draft(AuthoringContext(self.user.pk), 'not-a-uuid')

    def test_finished_legacy_submission_updates_without_editor_visit(self):
        from django.utils import timezone
        from judge.models import ProblemPackageImport, Submission
        from judge.problem_authoring.data import reconcile_authoring
        problem = self.make_problem()
        submission = Submission.objects.create(problem=problem, user=self.user.profile,
                                               language=self.language, status='D', result='AC')
        record = ProblemPackageImport.objects.create(owner=self.user.profile, problem=problem,
                                                     submission=submission, state='JUDGING')
        reconcile_authoring(now=timezone.now())
        record.refresh_from_db()
        self.assertEqual(record.state, 'FINISHED')

    def test_legacy_adoption_is_idempotent(self):
        import importlib.util
        self.assertIsNotNone(importlib.util.find_spec('judge.problem_authoring.legacy'),
                             'Legacy draft adapter is missing')
        from judge.problem_authoring.legacy import adopt_legacy_draft
        record = create_draft(self.user, make_zip({
            'statement.md': '# Legacy', 'editorial.md': '# Editorial', 'solution.cpp': 'int main() {}',
            'tests/1.in': '1', 'tests/1.out': '2',
        }))
        context = AuthoringContext(self.user.pk)
        first = adopt_legacy_draft(context, record.pk)
        second = adopt_legacy_draft(context, record.pk)
        self.assertEqual(first.pk, second.pk)
        self.assertIsInstance(first.pk, uuid.UUID)
