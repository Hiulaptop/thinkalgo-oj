import uuid

from django.apps import apps
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from judge.models import Problem, ProblemPackageImport, Solution
from judge.tests.authoring_helpers import AuthoringTestMixin


class AuthoringModelTest(AuthoringTestMixin, TestCase):
    def model(self, name):
        self.assertTrue(apps.is_installed('judge'))
        model = apps.all_models['judge'].get(name.lower())
        self.assertIsNotNone(model, 'Authoring persistence model is missing: ' + name)
        return model

    def test_legacy_problem_has_no_authoring_gate(self):
        state = self.model('ProblemAuthoringState')
        problem = self.make_problem()
        Solution.objects.create(problem=problem, content='Editorial', is_public=False, publish_on=timezone.now())
        record = ProblemPackageImport.objects.create(owner=self.user.profile, problem=problem)
        self.assertFalse(state.objects.filter(problem=problem).exists())
        problem.refresh_from_db()
        self.assertFalse(problem.is_public)
        self.assertEqual(problem.solution.content, 'Editorial')
        self.assertEqual(record.problem_id, problem.pk)

    def test_request_token_is_unique_per_actor(self):
        save = self.model('ProblemAuthoringSave')
        problem = self.make_problem()
        token = uuid.uuid4()
        save.objects.create(actor=self.user.profile, request_token=token, payload_sha256='a' * 64,
                            problem=problem, revision=1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            save.objects.create(actor=self.user.profile, request_token=token, payload_sha256='a' * 64,
                                problem=problem, revision=1)
        self.assertEqual(save.objects.count(), 1)

    def test_state_owns_single_current_operation(self):
        state_model = self.model('ProblemAuthoringState')
        operation_model = self.model('ProblemDataOperation')
        problem = self.make_problem()
        state = state_model.objects.create(problem=problem)
        operation = operation_model.objects.create(problem=problem, target_revision=1, config={})
        state.current_operation = operation
        state.save(update_fields=['current_operation'])
        state.refresh_from_db()
        self.assertEqual(state.current_operation_id, operation.pk)
        self.assertEqual(state.data_state, 'MISSING')
        self.assertEqual(operation.state, 'PENDING')

    def test_deleting_problem_with_operation_is_protected(self):
        from django.db.models.deletion import ProtectedError
        operation_model = self.model('ProblemDataOperation')
        problem = self.make_problem()
        operation_model.objects.create(problem=problem, target_revision=1, config={})
        with self.assertRaises(ProtectedError):
            problem.delete()

    def test_garbage_collection_removes_finished_authoring_records(self):
        from judge.utils.problems import fast_delete_problem
        operation_model = self.model('ProblemDataOperation')
        problem = self.make_problem()
        operation_model.objects.create(problem=problem, target_revision=1, config={}, state='READY')
        fast_delete_problem(problem)
        self.assertFalse(Problem.objects.filter(pk=problem.pk).exists())
        self.assertFalse(operation_model.objects.exists())

    def test_garbage_collector_refuses_live_worker_even_if_lease_expired(self):
        import fcntl
        from pathlib import Path
        from django.core.exceptions import ValidationError
        from judge.utils.problems import fast_delete_problem
        operation_model = self.model('ProblemDataOperation')
        problem = self.make_problem()
        operation = operation_model.objects.create(problem=problem, target_revision=1, config={}, state='INSTALLING')
        folder = Path(self.temp.name, 'data', '.authoring', str(operation.pk))
        folder.mkdir(parents=True)
        with folder.joinpath('worker.lock').open('a+b') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(ValidationError):
                fast_delete_problem(problem)
        self.assertTrue(Problem.objects.filter(pk=problem.pk).exists())

    def test_garbage_collection_cleans_operation_folders_after_commit(self):
        from pathlib import Path
        from judge.utils.problems import fast_delete_problem
        operation_model = self.model('ProblemDataOperation')
        problem = self.make_problem()
        operation = operation_model.objects.create(problem=problem, target_revision=1, state='READY')
        folder = Path(self.temp.name, 'data', '.authoring', str(operation.pk))
        folder.mkdir(parents=True)
        folder.joinpath('retained').write_bytes(b'old data')
        with self.captureOnCommitCallbacks(execute=True):
            fast_delete_problem(problem)
            self.assertTrue(folder.exists())
        self.assertFalse(folder.exists())

    def test_garbage_collection_rollback_preserves_operation_folders(self):
        from pathlib import Path
        from judge.utils.problems import fast_delete_problem
        operation_model = self.model('ProblemDataOperation')
        problem = self.make_problem()
        operation = operation_model.objects.create(problem=problem, target_revision=1, state='READY')
        folder = Path(self.temp.name, 'data', '.authoring', str(operation.pk))
        folder.mkdir(parents=True)
        folder.joinpath('retained').write_bytes(b'old data')
        with self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(RuntimeError), transaction.atomic():
                fast_delete_problem(problem)
                raise RuntimeError('outer rollback')
        self.assertTrue(folder.joinpath('retained').exists())
        self.assertTrue(operation_model.objects.filter(pk=operation.pk).exists())

    def test_garbage_collection_refuses_pending_reference_submission(self):
        import io
        from django.core.exceptions import ValidationError
        from judge.models import ProblemAuthoringState, ProblemReferenceSource
        from judge.problem_authoring.types import AuthoringContext
        from judge.problem_authoring.uploads import receive_upload
        from judge.problem_authoring.verification import start_verification
        from judge.utils.problems import fast_delete_problem
        problem = self.make_problem()
        problem.authors.add(self.user.profile)
        problem.allowed_languages.add(self.language)
        ProblemAuthoringState.objects.create(problem=problem, revision=1, grading_revision=1,
                                             active_data_revision=1, data_state='READY')
        upload = receive_upload(AuthoringContext(self.user.pk), io.BytesIO(b'int main() {}'), 'SOURCE')
        upload.consumed_by = problem
        upload.save()
        ProblemReferenceSource.objects.create(problem=problem, upload=upload, language=self.language)
        start_verification(AuthoringContext(self.user.pk), problem.pk, request_token=uuid.uuid4(),
                           expected_grading_revision=1)
        with self.assertRaises(ValidationError):
            fast_delete_problem(problem)
        self.assertTrue(Problem.objects.filter(pk=problem.pk).exists())

    def test_deleting_referenced_upload_is_rejected(self):
        from django.db.models.deletion import ProtectedError
        from django.utils import timezone

        upload_model = self.model('ProblemAuthoringUpload')
        source_model = self.model('ProblemReferenceSource')
        problem = self.make_problem()
        upload = upload_model.objects.create(
            owner=self.user.profile, kind='SOURCE', path='private/source', sha256='a' * 64,
            size=12, expires_at=timezone.now(), consumed_by=problem,
        )
        source_model.objects.create(problem=problem, upload=upload, language=self.language)
        with self.assertRaises(ProtectedError):
            upload.delete()
        self.assertTrue(Problem.objects.filter(pk=problem.pk).exists())


class AuthoringMigrationTest(AuthoringTestMixin, TransactionTestCase):
    def test_migration_roundtrip_preserves_legacy_content(self):
        from judge.models import ProblemTestCase

        problem = self.make_problem('migrationlegacy')
        problem.is_public = True
        problem.save()
        Solution.objects.create(problem=problem, content='Keep editorial', publish_on=timezone.now())
        ProblemTestCase.objects.create(dataset=problem, order=1, input_file='1.in', output_file='1.out',
                                       points=1, is_pretest=False)
        record = ProblemPackageImport.objects.create(owner=self.user.profile, problem=problem)
        try:
            executor = MigrationExecutor(connection)
            executor.migrate([('judge', '0234_problem_package_import')])
            executor = MigrationExecutor(connection)
            executor.migrate([('judge', '0235_problem_authoring')])
            problem.refresh_from_db()
            self.assertTrue(problem.is_public)
            self.assertEqual(problem.solution.content, 'Keep editorial')
            self.assertEqual(problem.cases.get().input_file, '1.in')
            self.assertTrue(ProblemPackageImport.objects.filter(pk=record.pk, problem=problem).exists())
            self.assertFalse(apps.get_model('judge', 'ProblemAuthoringState').objects.exists())
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
