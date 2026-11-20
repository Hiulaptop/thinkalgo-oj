import importlib.util
import uuid
from pathlib import Path

import yaml
from django.test import TestCase, override_settings
from django.utils import timezone

from judge.models import Problem, ProblemAuthoringState, ProblemData, Submission
from judge.problem_authoring.service import save_draft
from judge.problem_authoring.types import AuthoringContext, DraftChanges
from judge.problem_authoring.uploads import receive_upload
from judge.tests.authoring_helpers import AuthoringTestMixin, make_zip


class AuthoringDataTest(AuthoringTestMixin, TestCase):
    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('judge.problem_authoring.data'),
                             'Recoverable data operations are missing')
        from judge.problem_authoring import data
        return data

    def operation(self):
        context = AuthoringContext(self.user.pk)
        upload = receive_upload(context, make_zip({'1.in': '1', '1.out': '2'}), 'TESTS')
        result = save_draft(context, DraftChanges(problem_fields={
            'code': 'optest', 'name': 'Operation', 'description': '# Title', 'group_id': self.group.pk,
            'time_limit': 1, 'memory_limit': 262144, 'points': 100,
        }, test_upload_id=upload.pk), problem_id=None, expected_revision=None, request_token=uuid.uuid4())
        from judge.models import ProblemDataOperation
        return ProblemDataOperation.objects.get(pk=result.operation_id)

    def test_non_r2_install_and_duplicate_retry(self):
        operation = self.operation()
        self.api().process_data_operation(operation.pk)
        self.api().process_data_operation(operation.pk)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'READY')
        state = ProblemAuthoringState.objects.get(problem=operation.problem)
        self.assertEqual(state.data_state, 'READY')
        self.assertEqual(state.active_data_revision, operation.target_revision)
        self.assertEqual(operation.problem.cases.count(), 1)
        init = yaml.safe_load(Path(self.temp.name, 'data', 'optest', 'init.yml').read_text())
        self.assertEqual(init['archive'], 'tests.zip')
        self.assertEqual(init['test_cases'][0]['in'], '1.in')
        self.assertEqual(init['test_cases'][0]['points'], 1)
        self.assertTrue(ProblemData.objects.get(problem=operation.problem).has_yml())

    def test_queued_submission_blocks_activation_but_can_be_retried(self):
        operation = self.operation()
        state = ProblemAuthoringState.objects.get(problem=operation.problem)
        state.data_state = 'READY'
        state.active_data_revision = 1
        state.current_operation = None
        state.save()
        submission = Submission.objects.create(problem=operation.problem, user=self.user.profile,
                                               language=self.language, status='QU')
        state.current_operation = operation
        state.save()
        self.api().process_data_operation(operation.pk)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'WAITING')
        self.assertFalse(Path(self.temp.name, 'data', 'optest').exists())
        Submission.objects.filter(pk=submission.pk).update(status='D')
        self.api().process_data_operation(operation.pk)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'READY')

    @override_settings(BRIDGED_R2_PROBLEMS=True)
    def test_publish_failure_keeps_recoverable_pending_data(self):
        from unittest.mock import patch
        operation = self.operation()
        with patch('judge.problem_authoring.data.upload_release', side_effect=OSError('private/path')):
            self.api().process_data_operation(operation.pk)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'FAILED')
        self.assertNotIn('private/path', operation.safe_error)
        self.assertFalse(Path(self.temp.name, 'data', 'optest').exists())
        with patch('judge.problem_authoring.data.upload_release', return_value={
                'version': 'authoring-' + operation.pk.hex, 'sha256': 'a' * 64, 'package': 'key'}):
            self.api().process_data_operation(operation.pk)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'READY')
        self.assertEqual(ProblemData.objects.get(problem=operation.problem).r2_release_sha256, 'a' * 64)

    def test_reconciler_installs_unqueued_operation(self):
        operation = self.operation()
        self.api().reconcile_authoring(now=timezone.now())
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'READY')

    def test_recovery_after_install_before_database_commit(self):
        from unittest.mock import patch
        operation = self.operation()
        self.api().prepare_data_operation(operation.pk)
        with patch('judge.problem_authoring.data.ProblemTestCase.objects.bulk_create',
                   side_effect=RuntimeError('crash')):
            self.api().process_data_operation(operation.pk)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'FAILED')
        self.assertTrue(Path(self.temp.name, 'data', 'optest', 'operation.json').exists())
        self.api().process_data_operation(operation.pk)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'READY')
        self.assertEqual(operation.problem.cases.count(), 1)

    def test_reconciler_dispatches_and_refreshes_verification_without_editor_get(self):
        import io
        from unittest.mock import patch
        from judge.models import ProblemReferenceSource
        from judge.problem_authoring.verification import start_verification
        operation = self.operation()
        self.api().process_data_operation(operation.pk)
        problem = operation.problem
        problem.authors.add(self.user.profile)
        problem.allowed_languages.add(self.language)
        context = AuthoringContext(self.user.pk)
        upload = receive_upload(context, io.BytesIO(b'int main() {}'), 'SOURCE')
        upload.consumed_by = problem
        upload.save()
        ProblemReferenceSource.objects.create(problem=problem, upload=upload, language=self.language)
        run = start_verification(context, problem.pk, request_token=uuid.uuid4(),
                                 expected_grading_revision=problem.authoring_state.grading_revision)
        with patch('judge.problem_authoring.verification.judge_submission', return_value=True):
            self.api().reconcile_authoring(now=timezone.now())
        run.refresh_from_db()
        self.assertEqual(run.state, 'JUDGING')
        Submission.objects.filter(pk=run.submission_id).update(status='D', result='AC')
        self.api().reconcile_authoring(now=timezone.now())
        run.refresh_from_db()
        self.assertEqual(run.state, 'FINISHED')

    def test_expired_upload_cleanup_preserves_committed_operation(self):
        import io
        from datetime import timedelta
        from judge.models import ProblemAuthoringUpload
        from judge.problem_authoring.storage import upload_path
        operation = self.operation()
        unused = receive_upload(AuthoringContext(self.user.pk), io.BytesIO(b'unused'), 'SOURCE')
        path = upload_path(unused)
        ProblemAuthoringUpload.objects.update(expires_at=timezone.now() - timedelta(days=1))
        self.api().reconcile_authoring(now=timezone.now())
        self.assertFalse(ProblemAuthoringUpload.objects.filter(pk=unused.pk).exists())
        self.assertFalse(path.exists())
        self.assertTrue(ProblemAuthoringUpload.objects.filter(pk=operation.upload_id).exists())

    def test_tampered_prepared_dataset_is_not_activated(self):
        operation = self.operation()
        self.api().prepare_data_operation(operation.pk)
        prepared = Path(self.temp.name, 'data', '.authoring', str(operation.pk), 'prepared')
        (prepared / 'tests.zip').write_bytes(b'tampered')
        self.api().process_data_operation(operation.pk)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'FAILED')
        self.assertFalse(Path(self.temp.name, 'data', 'optest').exists())

    def test_retry_after_install_does_not_rebuild_or_change_release_bytes(self):
        from unittest.mock import patch
        operation = self.operation()
        with patch('judge.problem_authoring.data.ProblemTestCase.objects.bulk_create',
                   side_effect=RuntimeError('crash')):
            self.api().process_data_operation(operation.pk)
        with patch('judge.problem_authoring.data.prepare_data_operation', side_effect=RuntimeError('must not rebuild')):
            self.api().process_data_operation(operation.pk)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'READY')

    def test_advanced_data_snapshot_keeps_checker_and_batch_configuration(self):
        from judge.problem_authoring import data
        self.assertTrue(hasattr(data, 'begin_external_data_change'), 'Advanced staging adapter is missing')
        from judge.models import ProblemTestCase
        problem = self.make_problem('advanced')
        problem.authors.add(self.user.profile)
        folder = Path(self.temp.name, 'data', problem.code)
        folder.mkdir(parents=True)
        folder.joinpath('tests.zip').write_bytes(make_zip({'1.in': '1', '1.out': '2'}).getvalue())
        dataset = ProblemData.objects.create(problem=problem, zipfile=problem.code + '/tests.zip', checker='identical')
        cases = [ProblemTestCase(dataset=problem, type='C', order=1, points=2, is_pretest=False,
                                 input_file='1.in', output_file='1.out')]
        operation_id = data.begin_external_data_change(AuthoringContext(self.user.pk), problem.pk,
                                                       expected_revision=0, data=dataset, cases=cases, files={})
        data.process_data_operation(operation_id)
        dataset.refresh_from_db()
        self.assertEqual(dataset.checker, 'identical')
        self.assertEqual(problem.cases.get().points, 2)
        self.assertEqual(problem.authoring_state.data_state, 'READY')

    @override_settings(PROBLEM_AUTHORING_UPLOAD_LIMIT=4)
    def test_advanced_snapshot_obeys_upload_size_limit(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from judge.problem_authoring import data
        from judge.problem_authoring.types import AuthoringError
        problem = self.make_problem('oversized')
        problem.authors.add(self.user.profile)
        dataset = ProblemData(problem=problem)
        files = {'zipfile': SimpleUploadedFile('tests.zip', b'12345')}
        with self.assertRaises(AuthoringError):
            data.begin_external_data_change(AuthoringContext(self.user.pk), problem.pk,
                                            expected_revision=0, data=dataset, cases=[], files=files)
        from judge.models import ProblemDataOperation
        self.assertFalse(ProblemDataOperation.objects.filter(problem=problem).exists())

    def test_stale_operation_is_rejected_before_preparing_files(self):
        from unittest.mock import patch
        operation = self.operation()
        ProblemAuthoringState.objects.filter(problem=operation.problem).update(grading_revision=9)
        with patch('judge.problem_authoring.data.prepare_data_operation',
                   side_effect=AssertionError('must not prepare')):
            self.api().process_data_operation(operation.pk)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'FAILED')
        self.assertIn('newer', operation.safe_error.lower())

    def test_worker_refuses_modified_source_archive(self):
        from judge.problem_authoring.storage import upload_path
        operation = self.operation()
        upload_path(operation.upload).write_bytes(make_zip({'1.in': 'altered', '1.out': 'wrong'}).getvalue())
        self.api().process_data_operation(operation.pk)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'FAILED')
        self.assertFalse(Path(self.temp.name, 'data', 'optest').exists())

    def test_activation_rejects_expired_worker_lease(self):
        from datetime import timedelta
        from judge.models import ProblemDataOperation
        from judge.problem_authoring.types import AuthoringError
        operation = self.operation()
        self.api().prepare_data_operation(operation.pk)
        token = uuid.uuid4()
        ProblemDataOperation.objects.filter(pk=operation.pk).update(
            lease_token=token, lease_until=timezone.now() - timedelta(seconds=1), state='INSTALLING',
        )
        with self.assertRaises(AuthoringError):
            self.api().activate_operation(operation.pk, lease_token=token)
        self.assertFalse(Path(self.temp.name, 'data', 'optest').exists())

    def test_worker_does_not_activate_deleted_problem(self):
        operation = self.operation()
        operation.problem.mark_as_deleted()
        self.api().process_data_operation(operation.pk)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'FAILED')
        self.assertFalse(Path(self.temp.name, 'data', 'optest').exists())

    def test_expired_lease_cannot_be_stolen_while_filesystem_worker_is_live(self):
        import fcntl
        from datetime import timedelta
        from judge.models import ProblemDataOperation
        operation = self.operation()
        folder = Path(self.temp.name, 'data', '.authoring', str(operation.pk))
        folder.mkdir(parents=True)
        token = uuid.uuid4()
        ProblemDataOperation.objects.filter(pk=operation.pk).update(
            lease_token=token, lease_until=timezone.now() - timedelta(seconds=1), state='INSTALLING',
        )
        with (folder / 'worker.lock').open('a+b') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.api().process_data_operation(operation.pk)
        operation.refresh_from_db()
        self.assertEqual(operation.lease_token, token)
        self.assertEqual(operation.state, 'INSTALLING')
        self.api().process_data_operation(operation.pk)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'READY')

    def test_worker_refreshes_owned_lease_before_activation(self):
        from datetime import timedelta
        from unittest.mock import patch
        from judge.models import ProblemDataOperation
        operation = self.operation()
        original = self.api().prepare_data_operation

        def slow_prepare(operation_id):
            original(operation_id)
            ProblemDataOperation.objects.filter(pk=operation_id).update(
                lease_until=timezone.now() - timedelta(seconds=1),
            )

        with patch('judge.problem_authoring.data.prepare_data_operation', side_effect=slow_prepare):
            self.api().process_data_operation(operation.pk)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'READY')

    def test_replacement_keeps_old_data_until_activation_and_preserves_backup(self):
        import zipfile
        from judge.models import ProblemDataOperation
        first = self.operation()
        self.api().process_data_operation(first.pk)
        context = AuthoringContext(self.user.pk)
        replacement = receive_upload(context, make_zip({'2.in': '3', '2.out': '4'}), 'TESTS',
                                     problem_id=first.problem_id)
        result = save_draft(context, DraftChanges(test_upload_id=replacement.pk), problem_id=first.problem_id,
                            expected_revision=1, request_token=uuid.uuid4())
        destination = Path(self.temp.name, 'data', 'optest')
        with zipfile.ZipFile(destination / 'tests.zip') as archive:
            self.assertEqual(archive.namelist(), ['1.in', '1.out'])
        self.api().process_data_operation(result.operation_id)
        operation = ProblemDataOperation.objects.get(pk=result.operation_id)
        self.assertEqual(operation.state, 'READY')
        with zipfile.ZipFile(destination / 'tests.zip') as archive:
            self.assertEqual(archive.namelist(), ['2.in', '2.out'])
        self.assertTrue(Path(self.temp.name, 'data', '.authoring', str(operation.pk), 'backup', 'tests.zip').exists())

    def test_reconciler_recovers_other_jobs_when_one_operation_disappears(self):
        from unittest.mock import patch
        from judge.models import ProblemDataOperation
        operation = self.operation()
        with patch('judge.problem_authoring.data.process_data_operation',
                   side_effect=ProblemDataOperation.DoesNotExist):
            result = self.api().reconcile_authoring(now=timezone.now())
        self.assertIn('processed', result)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'PENDING')

    def test_reconciler_does_not_delete_source_attached_to_reference_run(self):
        import io
        from datetime import timedelta
        from judge.models import ProblemAuthoringUpload, ProblemReferenceRun
        from judge.problem_authoring.storage import upload_path
        operation = self.operation()
        self.api().process_data_operation(operation.pk)
        upload = receive_upload(AuthoringContext(self.user.pk), io.BytesIO(b'source'), 'SOURCE')
        ProblemAuthoringUpload.objects.filter(pk=upload.pk).update(expires_at=timezone.now() - timedelta(days=1))
        ProblemReferenceRun.objects.create(
            problem=operation.problem, owner=self.user.profile, request_token=uuid.uuid4(),
            grading_revision=1, source_sha256=upload.sha256, upload=upload, language=self.language, state='FINISHED',
        )
        self.api().reconcile_authoring(now=timezone.now())
        self.assertTrue(upload_path(upload).exists())
        self.assertTrue(ProblemAuthoringUpload.objects.filter(pk=upload.pk).exists())

    def test_cleanup_missing_expired_upload_file_does_not_abort_reconciliation(self):
        import io
        from datetime import timedelta
        from judge.models import ProblemAuthoringUpload
        from judge.problem_authoring.storage import upload_path
        upload = receive_upload(AuthoringContext(self.user.pk), io.BytesIO(b'x'), 'SOURCE')
        path = upload_path(upload)
        path.unlink()
        path.parent.rmdir()
        ProblemAuthoringUpload.objects.filter(pk=upload.pk).update(expires_at=timezone.now() - timedelta(days=1))
        result = self.api().reconcile_authoring(now=timezone.now())
        self.assertEqual(result['cleaned'], 1)
        self.assertFalse(ProblemAuthoringUpload.objects.filter(pk=upload.pk).exists())

    def test_non_r2_activation_clears_old_release_pointer(self):
        operation = self.operation()
        ProblemData.objects.create(problem=operation.problem, r2_release_version='old',
                                   r2_release_sha256='a' * 64, r2_release_key='old/key')
        self.api().process_data_operation(operation.pk)
        data = ProblemData.objects.get(problem=operation.problem)
        self.assertEqual(data.r2_release_version, '')
        self.assertEqual(data.r2_release_sha256, '')

    def test_preparation_flush_failure_does_not_activate_data(self):
        from unittest.mock import patch
        operation = self.operation()
        with patch('os.fsync', side_effect=OSError('disk flush failed')):
            self.api().process_data_operation(operation.pk)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'FAILED')
        self.assertFalse(Path(self.temp.name, 'data', 'optest').exists())
        self.assertEqual(operation.problem.cases.count(), 0)
        self.api().process_data_operation(operation.pk)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'READY')

    def test_install_flush_failure_recovers_installed_bytes_without_rebuilding(self):
        import os
        from unittest.mock import patch
        operation = self.operation()
        destination = Path(self.temp.name, 'data', 'optest')
        original_fsync = os.fsync

        def fail_after_install(descriptor):
            if (destination / 'operation.json').is_file():
                raise OSError('directory flush failed')
            return original_fsync(descriptor)

        with patch('os.fsync', side_effect=fail_after_install):
            self.api().process_data_operation(operation.pk)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'FAILED')
        self.assertTrue((destination / 'operation.json').exists())
        self.assertEqual(operation.problem.cases.count(), 0)
        with patch('judge.problem_authoring.data.prepare_data_operation', side_effect=AssertionError('rebuilt')):
            self.api().process_data_operation(operation.pk)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'READY')
        self.assertEqual(operation.problem.cases.count(), 1)

    def test_retry_checks_revision_and_problem_scope_in_shared_service(self):
        from judge.models import ProblemDataOperation
        from judge.problem_authoring.types import AuthoringError
        operation = self.operation()
        ProblemDataOperation.objects.filter(pk=operation.pk).update(state='FAILED')
        ProblemAuthoringState.objects.filter(problem=operation.problem).update(data_state='FAILED')
        api = self.api()
        self.assertTrue(hasattr(api, 'retry_data_operation'), 'Shared retry service is missing')
        context = AuthoringContext(self.user.pk)
        with self.assertRaises(AuthoringError):
            api.retry_data_operation(context, operation.problem_id, expected_revision=0)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'FAILED')
        with self.captureOnCommitCallbacks(execute=True):
            api.retry_data_operation(context, operation.problem_id, expected_revision=1)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'PENDING')
        self.assertEqual(operation.problem.authoring_state.data_state, 'PENDING')

    def test_legacy_release_publisher_cannot_replace_authoring_owned_pointer(self):
        from unittest.mock import patch
        from judge.problem_authoring.types import AuthoringError
        from judge.utils.problem_releases import publish_problem_to_r2
        operation = self.operation()
        self.api().process_data_operation(operation.pk)
        with patch('judge.utils.problem_releases.build_release', side_effect=AssertionError('must not publish')):
            with self.assertRaises(AuthoringError):
                publish_problem_to_r2(operation.problem.code)
        data = ProblemData.objects.get(problem=operation.problem)
        self.assertEqual(data.r2_release_version, '')

    def test_legacy_publish_started_before_adoption_cannot_commit_late_pointer(self):
        import os
        from unittest.mock import Mock, patch
        from judge.problem_authoring.types import AuthoringError
        from judge.utils.problem_releases import publish_problem_to_r2
        problem = self.make_problem()
        ProblemData.objects.create(problem=problem)

        def adopt_during_upload(**kwargs):
            ProblemAuthoringState.objects.get_or_create(problem=problem, defaults={
                'revision': 1, 'grading_revision': 1, 'active_data_revision': 1, 'data_state': 'READY',
            })

        client = Mock()
        client.put_object.side_effect = adopt_during_upload
        with patch.dict(os.environ, {'R2_PROBLEMS_BUCKET': 'test'}):
            with patch('judge.utils.problem_releases.r2_client', return_value=client):
                with patch('judge.utils.problem_releases.build_release', return_value=(
                        b'old', b'{}', {'sha256': 'a' * 64})):
                    with self.assertRaises(AuthoringError):
                        publish_problem_to_r2(problem.code, 'old')
        self.assertEqual(ProblemData.objects.get(problem=problem).r2_release_version, '')

    def test_untracked_prepared_file_is_not_published_or_activated(self):
        from unittest.mock import patch
        operation = self.operation()
        self.api().prepare_data_operation(operation.pk)
        prepared = Path(self.temp.name, 'data', '.authoring', str(operation.pk), 'prepared')
        prepared.joinpath('unexpected-source.cpp').write_text('private source')
        with override_settings(BRIDGED_R2_PROBLEMS=True):
            with patch('judge.problem_authoring.data.upload_release', return_value={
                    'version': 'v1', 'sha256': 'a' * 64, 'package': 'key'}):
                self.api().process_data_operation(operation.pk)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'FAILED')
        self.assertFalse(Path(self.temp.name, 'data', 'optest').exists())

    def test_replacement_flush_failure_after_backup_recovers_without_old_data_loss(self):
        import os
        from unittest.mock import patch
        from judge.models import ProblemDataOperation
        first = self.operation()
        self.api().process_data_operation(first.pk)
        context = AuthoringContext(self.user.pk)
        upload = receive_upload(context, make_zip({'2.in': '3', '2.out': '4'}), 'TESTS',
                                problem_id=first.problem_id)
        result = save_draft(context, DraftChanges(test_upload_id=upload.pk), problem_id=first.problem_id,
                            expected_revision=1, request_token=uuid.uuid4())
        folder = Path(self.temp.name, 'data', '.authoring', str(result.operation_id))
        destination = Path(self.temp.name, 'data', 'optest')
        original_fsync = os.fsync

        def fail_after_backup(descriptor):
            if (folder / 'backup').exists() and not destination.exists():
                raise OSError('backup parent flush failed')
            return original_fsync(descriptor)

        with patch('os.fsync', side_effect=fail_after_backup):
            self.api().process_data_operation(result.operation_id)
        self.assertTrue((folder / 'backup' / 'tests.zip').exists())
        self.assertEqual(ProblemDataOperation.objects.get(pk=result.operation_id).state, 'FAILED')
        self.api().process_data_operation(result.operation_id)
        self.assertEqual(ProblemDataOperation.objects.get(pk=result.operation_id).state, 'READY')
        self.assertEqual(first.problem.cases.get().input_file, '2.in')
        self.assertTrue((folder / 'backup' / 'tests.zip').exists())

    def test_successful_operation_cleans_retained_copies_only_after_retention(self):
        from datetime import timedelta
        from judge.models import ProblemDataOperation
        operation = self.operation()
        self.api().process_data_operation(operation.pk)
        folder = Path(self.temp.name, 'data', '.authoring', str(operation.pk))
        snapshot = folder / 'snapshot'
        snapshot.mkdir()
        snapshot.joinpath('tests.zip').write_bytes(b'old retained bytes')
        operation.refresh_from_db()
        operation.config['snapshot_bytes'] = 18
        operation.save(update_fields=['config'])
        self.api().reconcile_authoring(now=timezone.now())
        self.assertTrue(snapshot.exists())
        ProblemDataOperation.objects.filter(pk=operation.pk).update(updated=timezone.now() - timedelta(days=2))
        self.api().reconcile_authoring(now=timezone.now())
        operation.refresh_from_db()
        self.assertFalse(snapshot.exists())
        self.assertEqual(operation.config['snapshot_bytes'], 0)
        self.assertTrue(Path(self.temp.name, 'data', 'optest', 'tests.zip').exists())
        self.assertEqual(operation.state, 'READY')

    def test_missing_completed_folder_releases_obsolete_workspace_reservation(self):
        import shutil
        from datetime import timedelta
        from judge.models import ProblemDataOperation
        operation = self.operation()
        self.api().process_data_operation(operation.pk)
        folder = Path(self.temp.name, 'data', '.authoring', str(operation.pk))
        shutil.rmtree(folder)
        ProblemDataOperation.objects.filter(pk=operation.pk).update(updated=timezone.now() - timedelta(days=2))
        result = self.api().reconcile_authoring(now=timezone.now())
        operation.refresh_from_db()
        self.assertEqual(result['artifacts_cleaned'], 1)
        self.assertEqual(operation.config['workspace_bytes'], 0)
        self.assertEqual(operation.phase, 'CLEANED')
        self.assertTrue(Path(self.temp.name, 'data', 'optest', 'tests.zip').exists())

    def test_retained_artifact_failure_does_not_block_unrelated_completed_cleanup(self):
        from datetime import timedelta
        from unittest.mock import patch
        from judge.models import ProblemDataOperation
        first = self.operation()
        self.api().process_data_operation(first.pk)
        upload = receive_upload(AuthoringContext(self.user.pk), make_zip({'2.in': '3', '2.out': '4'}), 'TESTS',
                                problem_id=first.problem_id)
        result = save_draft(AuthoringContext(self.user.pk), DraftChanges(test_upload_id=upload.pk),
                            problem_id=first.problem_id, expected_revision=1, request_token=uuid.uuid4())
        self.api().process_data_operation(result.operation_id)
        ProblemDataOperation.objects.update(updated=timezone.now() - timedelta(days=2))
        folder = Path(self.temp.name, 'data', '.authoring')
        for operation_id in (first.pk, result.operation_id):
            (folder / str(operation_id) / 'snapshot').mkdir(exist_ok=True)
        import shutil
        original = shutil.rmtree

        def remove(path, *args, **kwargs):
            if str(first.pk) in str(path):
                raise OSError('one retained folder unavailable')
            return original(path, *args, **kwargs)

        with patch('judge.problem_authoring.data.shutil.rmtree', side_effect=remove):
            cleanup = self.api().reconcile_authoring(now=timezone.now())
        self.assertEqual(cleanup['artifacts_cleaned'], 1)
        first.refresh_from_db()
        second = ProblemDataOperation.objects.get(pk=result.operation_id)
        self.assertGreater(first.config['workspace_bytes'], 0)
        self.assertEqual(second.config['workspace_bytes'], 0)
        self.assertTrue(Path(self.temp.name, 'data', 'optest', 'tests.zip').exists())
        self.assertEqual(self.api().reconcile_authoring(now=timezone.now())['artifacts_cleaned'], 1)

    def test_retry_release_manifest_with_wrong_identity_is_rejected(self):
        import io
        import json
        import os
        from unittest.mock import Mock, patch
        from judge.problem_authoring.types import AuthoringError
        operation = self.operation()
        self.api().prepare_data_operation(operation.pk)
        prepared = Path(self.temp.name, 'data', '.authoring', str(operation.pk), 'prepared')
        _, _, manifest = self.api().build_release(prepared, 'optest', 'authoring-' + operation.pk.hex)
        manifest['package'] = 'other/problem/package.zip'
        client = Mock()
        client.get_object.return_value = {'Body': io.BytesIO(json.dumps(manifest).encode())}
        with patch.dict(os.environ, {'R2_PROBLEMS_BUCKET': 'test'}):
            with patch('judge.problem_authoring.data.r2_client', return_value=client):
                with self.assertRaises(AuthoringError):
                    self.api().upload_release(prepared, 'optest', 'authoring-' + operation.pk.hex)

    def test_release_manifest_cannot_reuse_missing_or_corrupt_remote_package(self):
        import io
        import json
        import os
        from unittest.mock import Mock, patch
        from botocore.exceptions import ClientError
        from judge.problem_authoring.types import AuthoringError
        operation = self.operation()
        self.api().prepare_data_operation(operation.pk)
        prepared = Path(self.temp.name, 'data', '.authoring', str(operation.pk), 'prepared')
        version = 'authoring-' + operation.pk.hex
        _, _, manifest = self.api().build_release(prepared, 'optest', version)
        for package in (None, b'corrupt remote package'):
            with self.subTest(package=package):
                def get_object(**kwargs):
                    if kwargs['Key'].endswith('manifest.json'):
                        return {'Body': io.BytesIO(json.dumps(manifest).encode())}
                    if package is None:
                        raise ClientError({'Error': {'Code': 'NoSuchKey'}}, 'GetObject')
                    return {'Body': io.BytesIO(package)}

                client = Mock()
                client.get_object.side_effect = get_object
                with patch.dict(os.environ, {'R2_PROBLEMS_BUCKET': 'test'}):
                    with patch('judge.problem_authoring.data.r2_client', return_value=client):
                        with self.assertRaises(AuthoringError) as error:
                            self.api().upload_release(prepared, 'optest', version)
                self.assertEqual(error.exception.code, 'release_conflict')
        self.assertFalse(ProblemData.objects.filter(problem=operation.problem).exists())

    def test_release_reuse_accepts_checksum_verified_remote_package(self):
        import io
        import json
        import os
        from unittest.mock import Mock, patch
        operation = self.operation()
        self.api().prepare_data_operation(operation.pk)
        prepared = Path(self.temp.name, 'data', '.authoring', str(operation.pk), 'prepared')
        version = 'authoring-' + operation.pk.hex
        package, _, manifest = self.api().build_release(prepared, 'optest', version)

        def get_object(**kwargs):
            content = json.dumps(manifest).encode() if kwargs['Key'].endswith('manifest.json') else package
            return {'Body': io.BytesIO(content)}

        client = Mock()
        client.get_object.side_effect = get_object
        with patch.dict(os.environ, {'R2_PROBLEMS_BUCKET': 'test'}):
            with patch('judge.problem_authoring.data.r2_client', return_value=client):
                result = self.api().upload_release(prepared, 'optest', version)
        self.assertEqual(result['sha256'], manifest['sha256'])
        self.assertEqual(result['package'], 'releases/optest/' + version + '/package.zip')

    def test_generated_artifacts_cannot_exceed_reserved_workspace(self):
        from judge.models import ProblemDataOperation
        operation = self.operation()
        operation.config['workspace_bytes'] = 1
        ProblemDataOperation.objects.filter(pk=operation.pk).update(config=operation.config)
        self.api().process_data_operation(operation.pk)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'FAILED')
        self.assertFalse(Path(self.temp.name, 'data', 'optest').exists())
        self.api().process_data_operation(operation.pk)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'FAILED')
        self.assertFalse(Path(self.temp.name, 'data', 'optest').exists())

    def test_reserved_workspace_covers_backup_and_prepared_dataset_together(self):
        from judge.models import ProblemDataOperation
        first = self.operation()
        self.api().process_data_operation(first.pk)
        upload = receive_upload(AuthoringContext(self.user.pk), make_zip({'2.in': '3', '2.out': '4'}), 'TESTS',
                                problem_id=first.problem_id)
        result = save_draft(AuthoringContext(self.user.pk), DraftChanges(test_upload_id=upload.pk),
                            problem_id=first.problem_id, expected_revision=1, request_token=uuid.uuid4())
        operation = ProblemDataOperation.objects.get(pk=result.operation_id)
        self.api().prepare_data_operation(operation.pk)
        prepared = Path(self.temp.name, 'data', '.authoring', str(operation.pk), 'prepared')
        operation.config['workspace_bytes'] = sum(path.stat().st_size for path in prepared.iterdir())
        operation.save(update_fields=['config'])
        self.api().process_data_operation(operation.pk)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'FAILED')
        self.assertEqual(first.problem.cases.get().input_file, '1.in')

    def test_unknown_target_directory_is_never_overwritten(self):
        operation = self.operation()
        destination = Path(self.temp.name, 'data', 'optest')
        destination.mkdir(parents=True)
        (destination / 'keep').write_text('unowned')
        self.api().process_data_operation(operation.pk)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'FAILED')
        self.assertEqual((destination / 'keep').read_text(), 'unowned')
        self.assertFalse(Problem.objects.get(pk=operation.problem_id).cases.exists())
