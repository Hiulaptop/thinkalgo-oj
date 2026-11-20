from django.test import TestCase

from judge.models import ProblemAuthoringState, Submission
from judge.tests.authoring_helpers import AuthoringTestMixin


class AuthoringPolygonGuardTest(AuthoringTestMixin, TestCase):
    def importer(self, problem):
        from judge.utils.codeforces_polygon import PolygonImporter
        importer = object.__new__(PolygonImporter)
        importer.meta = {'code': problem.code}
        importer.interactive = False
        importer.config = {}
        return importer

    def test_polygon_mutation_waits_for_existing_submissions_before_any_write(self):
        from judge.utils.codeforces_polygon import ImportPolygonError
        problem = self.make_problem()
        Submission.objects.create(problem=problem, user=self.user.profile, language=self.language, status='QU')
        with self.assertRaises(ImportPolygonError):
            self.importer(problem).update_or_create_problem()
        problem.refresh_from_db()
        self.assertEqual(problem.description, '# Statement')

    def test_gated_polygon_update_stages_files_and_invalidates_revision(self):
        from pathlib import Path
        from judge.models import ProblemData, ProblemDataOperation
        from judge.tests.authoring_helpers import make_zip
        problem = self.make_problem()
        problem.authors.add(self.user.profile)
        ProblemAuthoringState.objects.create(problem=problem, revision=1, grading_revision=1,
                                             active_data_revision=1, data_state='READY')
        folder = Path(self.temp.name, 'data', problem.code)
        folder.mkdir(parents=True)
        old_bytes = make_zip({'old.in': '1', 'old.out': '2'}).getvalue()
        folder.joinpath('tests.zip').write_bytes(old_bytes)
        ProblemData.objects.create(problem=problem, zipfile=problem.code + '/tests.zip')
        incoming = Path(self.temp.name, 'replacement.zip')
        incoming.write_bytes(make_zip({'1.in': '3', '1.out': '4'}).getvalue())
        importer = self.importer(problem)
        importer.meta.update(name='Updated Polygon', time_limit=2, memory_limit=262144,
                             description='# Updated', partial=True, authors=[self.user.profile], curators=[],
                             translations=[], tutorial='# Editorial', zipfile=str(incoming), grader='standard',
                             checker='identical', grader_args={}, batches={}, normal_cases=[1], cases_data={
                                 1: {'input_file': '1.in', 'output_file': '1.out', 'points': 1},
                             })
        importer.update_or_create_problem()
        self.assertEqual(folder.joinpath('tests.zip').read_bytes(), old_bytes)
        state = ProblemAuthoringState.objects.get(problem=problem)
        self.assertEqual(state.data_state, 'PENDING')
        self.assertEqual(state.revision, 2)
        self.assertEqual(state.grading_revision, 2)
        operation = ProblemDataOperation.objects.get(problem=problem)
        self.assertEqual(operation.config['data']['checker'], 'identical')
        self.assertEqual(operation.config['cases'][0]['input_file'], '1.in')
        from judge.problem_authoring.data import process_data_operation
        process_data_operation(operation.pk)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'READY')
        self.assertEqual(problem.cases.get().input_file, '1.in')
        self.assertNotEqual(folder.joinpath('replacement.zip').read_bytes(), old_bytes)

    def test_polygon_mutation_checks_pending_authoring_operation(self):
        from judge.models import ProblemDataOperation
        from judge.utils.codeforces_polygon import ImportPolygonError
        problem = self.make_problem()
        operation = ProblemDataOperation.objects.create(problem=problem, target_revision=1)
        ProblemAuthoringState.objects.create(problem=problem, current_operation=operation)
        with self.assertRaises(ImportPolygonError):
            self.importer(problem).update_or_create_problem()
