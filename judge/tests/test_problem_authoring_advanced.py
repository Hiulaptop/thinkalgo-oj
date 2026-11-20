import uuid
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from judge.models import ProblemDataOperation
from judge.tests.authoring_helpers import AuthoringTestMixin, make_zip


@override_settings(PROBLEM_AUTHORING_ENABLED=True)
class AuthoringAdvancedViewTest(AuthoringTestMixin, TestCase):
    def test_snapshot_rejects_reserved_attachment_names(self):
        from judge.models import ProblemData, ProblemTestCase
        from judge.problem_authoring.advanced import begin_external_data_change
        from judge.problem_authoring.types import AuthoringContext, AuthoringError
        problem = self.make_problem()
        problem.authors.add(self.user.profile)
        for name in ('init.yml', 'operation.json'):
            with self.subTest(name=name), self.assertRaises(AuthoringError):
                begin_external_data_change(
                    AuthoringContext(self.user.pk), problem.pk, expected_revision=0,
                    data=ProblemData(problem=problem), cases=[ProblemTestCase(
                        dataset=problem, type='C', order=1, input_file='1.in', output_file='1.out',
                        points=1, is_pretest=False,
                    )], files={'zipfile': SimpleUploadedFile(name, b'bad')},
                )
        self.assertFalse(ProblemDataOperation.objects.exists())

    def test_rejected_snapshot_does_not_leave_staging_directory(self):
        from judge.models import ProblemData
        from judge.problem_authoring.advanced import begin_external_data_change
        from judge.problem_authoring.types import AuthoringContext, AuthoringError
        problem = self.make_problem()
        problem.authors.add(self.user.profile)
        files = {'zipfile': SimpleUploadedFile('init.yml', b'bad')}
        with self.assertRaises(AuthoringError):
            begin_external_data_change(AuthoringContext(self.user.pk), problem.pk, expected_revision=0,
                                       data=ProblemData(problem=problem), cases=[], files=files)
        folder = Path(self.temp.name, 'data', '.authoring')
        self.assertFalse(folder.exists() and any(folder.iterdir()))

    def test_advanced_snapshot_rejects_changed_artifact_before_install(self):
        from judge.models import ProblemData, ProblemTestCase
        from judge.problem_authoring.advanced import begin_external_data_change
        from judge.problem_authoring.data import process_data_operation
        from judge.problem_authoring.types import AuthoringContext
        problem = self.make_problem()
        problem.authors.add(self.user.profile)
        operation_id = begin_external_data_change(
            AuthoringContext(self.user.pk), problem.pk, expected_revision=0,
            data=ProblemData(problem=problem), cases=[ProblemTestCase(
                dataset=problem, type='C', order=1, input_file='1.in', output_file='1.out', points=1, is_pretest=False,
            )], files={'zipfile': SimpleUploadedFile('tests.zip', make_zip({'1.in': '1', '1.out': '2'}).getvalue())},
        )
        path = Path(self.temp.name, 'data', '.authoring', str(operation_id), 'snapshot', 'tests.zip')
        path.write_bytes(make_zip({'1.in': 'changed', '1.out': 'bad'}).getvalue())
        process_data_operation(operation_id)
        self.assertEqual(ProblemDataOperation.objects.get(pk=operation_id).state, 'FAILED')
        self.assertFalse(Path(self.temp.name, 'data', problem.code).exists())

    @override_settings(VNOJ_QUOTA_ENFORCEMENT_ENABLED=True, VNOJ_ORGANIZATION_DEFAULT_MAX_STORAGE=1,
                       PROBLEM_AUTHORING_REPLACEMENT_BUDGET=0)
    def test_advanced_snapshot_cannot_bypass_organization_storage_quota(self):
        from judge.models import Organization, ProblemData
        from judge.problem_authoring.advanced import begin_external_data_change
        from judge.problem_authoring.types import AuthoringContext, AuthoringError
        organization = Organization.objects.create(name='Team', slug='team', short_name='Team', about='')
        problem = self.make_problem()
        problem.organization = organization
        problem.save()
        problem.authors.add(self.user.profile)
        files = {'zipfile': SimpleUploadedFile('tests.zip', make_zip({'1.in': '1', '1.out': '2'}).getvalue())}
        with self.assertRaises(AuthoringError):
            begin_external_data_change(AuthoringContext(self.user.pk, organization.pk), problem.pk,
                                       expected_revision=0, data=ProblemData(problem=problem), cases=[], files=files)
        self.assertFalse(ProblemDataOperation.objects.exists())

    def test_advanced_snapshot_rejects_invalid_case_fields_before_commit(self):
        from judge.models import ProblemData, ProblemTestCase
        from judge.problem_authoring.advanced import begin_external_data_change
        from judge.problem_authoring.types import AuthoringContext, AuthoringError
        problem = self.make_problem()
        problem.authors.add(self.user.profile)
        with self.assertRaises(AuthoringError):
            begin_external_data_change(
                AuthoringContext(self.user.pk), problem.pk, expected_revision=0,
                data=ProblemData(problem=problem), cases=[ProblemTestCase(
                    dataset=problem, type='INVALID', order=1, input_file='1.in', output_file='1.out',
                    points=1, is_pretest=False,
                )], files={},
            )
        self.assertFalse(ProblemDataOperation.objects.exists())

    def test_invalid_archive_or_case_configuration_does_not_commit_operation(self):
        from judge.models import ProblemData, ProblemTestCase
        from judge.problem_authoring.advanced import begin_external_data_change
        from judge.problem_authoring.types import AuthoringContext, AuthoringError
        problem = self.make_problem()
        problem.authors.add(self.user.profile)
        for contents in ({'../1.in': '1', '1.out': '2'}, {'other.in': '1', 'other.out': '2'}):
            with self.subTest(contents=contents), self.assertRaises(AuthoringError):
                begin_external_data_change(
                    AuthoringContext(self.user.pk), problem.pk, expected_revision=0,
                    data=ProblemData(problem=problem), cases=[ProblemTestCase(
                        dataset=problem, type='C', order=1, input_file='1.in', output_file='1.out',
                        points=1, is_pretest=False,
                    )], files={'zipfile': SimpleUploadedFile('tests.zip', make_zip(contents).getvalue())},
                )
        self.assertFalse(ProblemDataOperation.objects.exists())
        self.assertFalse(hasattr(problem, 'authoring_state'))

    @override_settings(PROBLEM_AUTHORING_EXPANDED_LIMIT=3)
    def test_advanced_archive_respects_expanded_size_limit_before_commit(self):
        from judge.models import ProblemData, ProblemTestCase
        from judge.problem_authoring.advanced import begin_external_data_change
        from judge.problem_authoring.types import AuthoringContext, AuthoringError
        problem = self.make_problem()
        problem.authors.add(self.user.profile)
        with self.assertRaises(AuthoringError):
            begin_external_data_change(
                AuthoringContext(self.user.pk), problem.pk, expected_revision=0,
                data=ProblemData(problem=problem), cases=[ProblemTestCase(
                    dataset=problem, type='C', order=1, input_file='1.in', output_file='1.out',
                    points=1, is_pretest=False,
                )], files={'zipfile': SimpleUploadedFile(
                    'tests.zip', make_zip({'1.in': '1234', '1.out': '2'}).getvalue(),
                )},
            )
        self.assertFalse(ProblemDataOperation.objects.exists())

    @override_settings(PROBLEM_AUTHORING_OWNER_UPLOAD_LIMIT=1)
    def test_copied_existing_attachments_reserve_snapshot_quota(self):
        from judge.models import ProblemData, ProblemTestCase
        from judge.problem_authoring.advanced import begin_external_data_change
        from judge.problem_authoring.types import AuthoringContext, AuthoringError
        problem = self.make_problem()
        problem.authors.add(self.user.profile)
        folder = Path(self.temp.name, 'data', problem.code)
        folder.mkdir(parents=True)
        folder.joinpath('tests.zip').write_bytes(make_zip({'1.in': '1', '1.out': '2'}).getvalue())
        dataset = ProblemData.objects.create(problem=problem, zipfile=problem.code + '/tests.zip')
        with self.assertRaises(AuthoringError):
            begin_external_data_change(
                AuthoringContext(self.user.pk), problem.pk, expected_revision=0, data=dataset,
                cases=[ProblemTestCase(dataset=problem, type='C', order=1, input_file='1.in', output_file='1.out',
                                       points=1, is_pretest=False)], files={},
            )
        self.assertFalse(ProblemDataOperation.objects.exists())
        self.assertTrue(folder.joinpath('tests.zip').is_file())

    def test_advanced_snapshot_limits_actual_stream_not_declared_size(self):
        from judge.models import ProblemData, ProblemTestCase
        from judge.problem_authoring.advanced import begin_external_data_change
        from judge.problem_authoring.types import AuthoringContext, AuthoringError
        problem = self.make_problem()
        problem.authors.add(self.user.profile)
        incoming = SimpleUploadedFile('tests.zip', make_zip({'1.in': '1', '1.out': '2'}).getvalue())
        incoming.size = 1
        with self.assertRaises(AuthoringError):
            begin_external_data_change(
                AuthoringContext(self.user.pk), problem.pk, expected_revision=0, data=ProblemData(problem=problem),
                cases=[ProblemTestCase(dataset=problem, type='C', order=1, input_file='1.in', output_file='1.out',
                                       points=1, is_pretest=False)], files={'zipfile': incoming},
            )
        self.assertFalse(ProblemDataOperation.objects.exists())

    def test_data_page_stages_replacement_instead_of_mutating_active_files(self):
        self.client.force_login(self.user)
        problem = self.make_problem()
        problem.authors.add(self.user.profile)
        response = self.client.post('/problem/' + problem.code + '/test_data', {
            'authoring_revision': '0',
            'problem-data-zipfile': SimpleUploadedFile('tests.zip', make_zip({'1.in': '1', '1.out': '2'}).getvalue()),
            'problem-data-grader': 'standard', 'problem-data-checker': 'identical',
            'problem-data-io_method': 'standard', 'problem-data-checker_type': 'default',
            'cases-TOTAL_FORMS': '1', 'cases-INITIAL_FORMS': '0',
            'cases-MIN_NUM_FORMS': '0', 'cases-MAX_NUM_FORMS': '1',
            'cases-0-order': '1', 'cases-0-type': 'C', 'cases-0-input_file': '1.in',
            'cases-0-output_file': '1.out', 'cases-0-points': '2',
        })
        if response.status_code != 302:
            self.fail(str(response.context['data_form'].errors) + str(response.context['cases_formset'].errors))
        operation = ProblemDataOperation.objects.get(problem=problem)
        self.assertIsInstance(operation.pk, uuid.UUID)
        self.assertEqual(operation.config['data']['checker'], 'identical')
        self.assertFalse(Path(self.temp.name, 'data', problem.code, 'tests.zip').exists())
