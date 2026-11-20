import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from django.db import close_old_connections, connection
from django.test import TransactionTestCase, override_settings

from judge.models import Problem, ProblemAuthoringSave
from judge.problem_authoring.service import save_draft
from judge.problem_authoring.types import AuthoringContext, AuthoringError, DraftChanges
from judge.tests.authoring_helpers import AuthoringTestMixin


class AuthoringConcurrencyTest(AuthoringTestMixin, TransactionTestCase):
    def setUp(self):
        super().setUp()
        if connection.vendor != 'mysql':
            self.skipTest('MariaDB/MySQL required for row-lock concurrency evidence')

    def concurrent_save(self, context, changes, token):
        barrier = threading.Barrier(2)

        def save():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return save_draft(context, changes, problem_id=None, expected_revision=None, request_token=token)
            finally:
                close_old_connections()

        with patch('judge.problem_authoring.service._enqueue_data'):
            with ThreadPoolExecutor(max_workers=2) as pool:
                return list(pool.map(lambda _: save(), range(2)))

    def test_duplicate_create_token_produces_one_problem_under_concurrency(self):
        context = AuthoringContext(self.user.pk)
        changes = DraftChanges(problem_fields={
            'code': 'concurrent', 'name': 'Concurrent', 'group_id': self.group.pk,
            'description': '# Title', 'time_limit': 1, 'memory_limit': 262144, 'points': 100,
        })
        results = self.concurrent_save(context, changes, uuid.uuid4())
        self.assertEqual(results[0], results[1])
        self.assertEqual(Problem.objects.filter(code='concurrent').count(), 1)
        self.assertEqual(ProblemAuthoringSave.objects.count(), 1)

    def test_two_stale_editors_cannot_overwrite_each_other(self):
        from judge.models import ProblemAuthoringState
        problem = self.make_problem()
        problem.authors.add(self.user.profile)
        ProblemAuthoringState.objects.create(problem=problem, revision=1)
        context = AuthoringContext(self.user.pk)
        barrier = threading.Barrier(2)

        def edit(index):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    save_draft(context, DraftChanges(problem_fields={'name': 'Editor ' + str(index)}),
                               problem_id=problem.pk, expected_revision=1, request_token=uuid.uuid4())
                    return 'saved'
                except AuthoringError as exc:
                    return exc.code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(edit, range(2)))
        self.assertCountEqual(results, ['saved', 'stale_revision'])
        self.assertEqual(ProblemAuthoringState.objects.get(problem=problem).revision, 2)

    def test_submit_race_cannot_enter_pending_replacement(self):
        from judge.models import ProblemAuthoringState, Submission
        from judge.problem_authoring.uploads import receive_upload
        from judge.tests.authoring_helpers import make_zip
        from django.core.exceptions import ValidationError
        problem = self.make_problem()
        problem.authors.add(self.user.profile)
        ProblemAuthoringState.objects.create(problem=problem, revision=1, grading_revision=1,
                                             active_data_revision=1, data_state='READY')
        context = AuthoringContext(self.user.pk)
        upload = receive_upload(context, make_zip({'1.in': '1', '1.out': '2'}), 'TESTS', problem_id=problem.pk)
        barrier = threading.Barrier(2)

        def replace():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                with patch('judge.problem_authoring.service._enqueue_data'):
                    return save_draft(context, DraftChanges(test_upload_id=upload.pk), problem_id=problem.pk,
                                      expected_revision=1, request_token=uuid.uuid4())
            finally:
                close_old_connections()

        def submit():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    return Submission.objects.create(problem_id=problem.pk, user_id=self.user.profile.pk,
                                                     language_id=self.language.pk).pk
                except ValidationError:
                    return None
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            replacement = pool.submit(replace)
            submitted = pool.submit(submit)
            replacement.result(timeout=20)
            submission_id = submitted.result(timeout=20)
        state = ProblemAuthoringState.objects.get(problem=problem)
        self.assertEqual(state.data_state, 'PENDING')
        if submission_id is not None:
            self.assertEqual(Submission.objects.get(pk=submission_id).status, 'QU')
            self.assertEqual(Submission.objects.filter(problem=problem).count(), 1)
        else:
            self.assertFalse(Submission.objects.filter(problem=problem).exists())

    def test_reference_bridge_callback_can_commit_before_dispatch_reply(self):
        import io
        from judge.models import ProblemAuthoringState, ProblemReferenceSource, Submission
        from judge.problem_authoring.uploads import receive_upload
        from judge.problem_authoring.verification import dispatch_verification, start_verification
        problem = self.make_problem()
        problem.authors.add(self.user.profile)
        problem.allowed_languages.add(self.language)
        ProblemAuthoringState.objects.create(problem=problem, revision=1, grading_revision=1,
                                             active_data_revision=1, data_state='READY')
        context = AuthoringContext(self.user.pk)
        upload = receive_upload(context, io.BytesIO(b'int main() {}'), 'SOURCE')
        upload.consumed_by = problem
        upload.save()
        ProblemReferenceSource.objects.create(problem=problem, upload=upload, language=self.language)
        run = start_verification(context, problem.pk, request_token=uuid.uuid4(), expected_grading_revision=1)

        def callback():
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute('SET SESSION innodb_lock_wait_timeout = 1')
                Submission.objects.filter(pk=run.submission_id).update(status='D', result='AC')
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=1) as pool:
            def bridge_reply(packet):
                pool.submit(callback).result(timeout=5)
                return {'name': 'submission-received', 'submission-id': run.submission_id}

            with patch('judge.judgeapi.judge_request', side_effect=bridge_reply):
                dispatch_verification(run.pk)
        run.refresh_from_db()
        self.assertEqual(run.state, 'FINISHED')
        self.assertEqual(Submission.objects.get(pk=run.submission_id).result, 'AC')

    def test_expired_worker_lease_cannot_bypass_live_filesystem_owner(self):
        from datetime import timedelta
        from django.utils import timezone
        from judge.models import ProblemDataOperation
        from judge.problem_authoring import data
        from judge.problem_authoring.uploads import receive_upload
        from judge.tests.authoring_helpers import make_zip
        context = AuthoringContext(self.user.pk)
        upload = receive_upload(context, make_zip({'1.in': '1', '1.out': '2'}), 'TESTS')
        changes = DraftChanges(problem_fields={
            'code': 'oneworker', 'name': 'One worker', 'group_id': self.group.pk,
            'description': '# Title', 'time_limit': 1, 'memory_limit': 262144, 'points': 100,
        }, test_upload_id=upload.pk)
        with patch('judge.problem_authoring.service._enqueue_data'):
            result = save_draft(context, changes, problem_id=None, expected_revision=None, request_token=uuid.uuid4())
        prepared = threading.Event()
        release = threading.Event()
        original = data.prepare_data_operation

        def pause(operation_id):
            original(operation_id)
            prepared.set()
            if not release.wait(timeout=10):
                raise AssertionError('Worker was not released')

        def process():
            close_old_connections()
            try:
                data.process_data_operation(result.operation_id)
            finally:
                close_old_connections()

        with patch('judge.problem_authoring.data.prepare_data_operation', side_effect=pause):
            with ThreadPoolExecutor(max_workers=2) as pool:
                owner = pool.submit(process)
                try:
                    self.assertTrue(prepared.wait(timeout=10))
                    ProblemDataOperation.objects.filter(pk=result.operation_id).update(
                        lease_until=timezone.now() - timedelta(seconds=1))
                    pool.submit(process).result(timeout=10)
                    operation = ProblemDataOperation.objects.get(pk=result.operation_id)
                    self.assertEqual(operation.attempts, 1)
                    self.assertEqual(operation.state, 'INSTALLING')
                finally:
                    release.set()
                owner.result(timeout=10)
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'READY')
        self.assertEqual(operation.attempts, 1)
        self.assertEqual(Problem.objects.get(pk=result.problem_id).cases.count(), 1)

    def test_cleanup_waiting_for_save_cannot_delete_consumed_upload(self):
        from django.utils import timezone
        from judge.models import ProblemAuthoringUpload
        from judge.problem_authoring import service
        from judge.problem_authoring import data
        from judge.problem_authoring.data import reconcile_authoring
        from judge.problem_authoring.uploads import receive_upload
        from judge.tests.authoring_helpers import make_zip
        context = AuthoringContext(self.user.pk)
        upload = receive_upload(context, make_zip({'1.in': '1', '1.out': '2'}), 'TESTS')
        cleanup_started = threading.Event()
        original_cleanup = data._clean_expired_upload

        def begin_cleanup(*args, **kwargs):
            cleanup_started.set()
            return original_cleanup(*args, **kwargs)

        checked = threading.Event()
        release = threading.Event()
        original = service.get_upload

        def pause(*args, **kwargs):
            retained = original(*args, **kwargs)
            checked.set()
            if not release.wait(timeout=10):
                raise AssertionError('Save was not released')
            return retained

        def save():
            close_old_connections()
            try:
                changes = DraftChanges(problem_fields={
                    'code': 'consume', 'name': 'Consume', 'group_id': self.group.pk,
                    'description': '# Title', 'time_limit': 1, 'memory_limit': 262144, 'points': 100,
                }, test_upload_id=upload.pk)
                return save_draft(context, changes, problem_id=None, expected_revision=None,
                                  request_token=uuid.uuid4())
            finally:
                close_old_connections()

        def cleanup():
            close_old_connections()
            try:
                with patch('judge.problem_authoring.data._clean_expired_upload', side_effect=begin_cleanup):
                    return reconcile_authoring(now=timezone.now())
            finally:
                close_old_connections()

        with patch('judge.problem_authoring.service.get_upload', side_effect=pause):
            with patch('judge.problem_authoring.service._enqueue_data'):
                with ThreadPoolExecutor(max_workers=2) as pool:
                    saving = pool.submit(save)
                    try:
                        self.assertTrue(checked.wait(timeout=10))
                        ProblemAuthoringUpload.objects.filter(pk=upload.pk).update(expires_at=timezone.now())
                        cleaning = pool.submit(cleanup)
                        self.assertTrue(cleanup_started.wait(timeout=10))
                    finally:
                        release.set()
                    result = saving.result(timeout=10)
                    cleanup_result = cleaning.result(timeout=10)
        upload.refresh_from_db()
        self.assertEqual(upload.consumed_by_id, result.problem_id)
        self.assertEqual(cleanup_result['cleaned'], 0)
        from judge.problem_authoring.storage import upload_path
        self.assertTrue(upload_path(upload).is_file())

    def test_pdf_publication_does_not_hold_database_transaction(self):
        import io
        from judge.models import ProblemAuthoringUpload
        from judge.problem_authoring.uploads import receive_upload
        context = AuthoringContext(self.user.pk)
        upload = receive_upload(context, io.BytesIO(b'%PDF-1.4'), 'PDF')
        changes = DraftChanges(problem_fields={
            'code': 'pdfdraft', 'name': 'PDF draft', 'group_id': self.group.pk,
            'description': '# Statement', 'time_limit': 1, 'memory_limit': 262144, 'points': 100,
        }, pdf_upload_id=upload.pk)

        def publish(statement, **kwargs):
            self.assertFalse(connection.in_atomic_block, 'PDF network write held database transaction')
            self.assertFalse(Problem.objects.filter(code='pdfdraft').exists())
            return 'https://example.invalid/statement.pdf'

        with patch('judge.views.widgets.pdf_statement_uploader', side_effect=publish):
            result = save_draft(context, changes, problem_id=None, expected_revision=None, request_token=uuid.uuid4())
        self.assertEqual(Problem.objects.get(pk=result.problem_id).pdf_url, 'https://example.invalid/statement.pdf')
        self.assertEqual(ProblemAuthoringUpload.objects.get(pk=upload.pk).consumed_by_id, result.problem_id)

    def test_pdf_cleanup_does_not_hold_database_transaction(self):
        import io
        from django.utils import timezone
        from judge.models import ProblemAuthoringUpload
        from judge.problem_authoring.data import reconcile_authoring
        from judge.problem_authoring.uploads import receive_upload
        upload = receive_upload(AuthoringContext(self.user.pk), io.BytesIO(b'%PDF-1.4'), 'PDF')
        ProblemAuthoringUpload.objects.filter(pk=upload.pk).update(expires_at=timezone.now())

        def delete_media(path):
            self.assertFalse(connection.in_atomic_block, 'Media cleanup held database transaction')

        with patch('judge.views.widgets.default_storage.delete', side_effect=delete_media):
            result = reconcile_authoring(now=timezone.now())
        self.assertEqual(result['cleaned'], 1)
        self.assertFalse(ProblemAuthoringUpload.objects.filter(pk=upload.pk).exists())

    def test_language_mutation_serializes_with_reference_start(self):
        import io
        from judge.models import ProblemAuthoringState, ProblemReferenceSource
        from judge.problem_authoring import policy
        from judge.problem_authoring.uploads import receive_upload
        from judge.problem_authoring.verification import start_verification
        problem = self.make_problem()
        problem.authors.add(self.user.profile)
        problem.allowed_languages.add(self.language)
        ProblemAuthoringState.objects.create(problem=problem, revision=1, grading_revision=1,
                                             active_data_revision=1, data_state='READY')
        context = AuthoringContext(self.user.pk)
        upload = receive_upload(context, io.BytesIO(b'int main() {}'), 'SOURCE')
        upload.consumed_by = problem
        upload.save()
        ProblemReferenceSource.objects.create(problem=problem, upload=upload, language=self.language)
        checked = threading.Event()
        proceed = threading.Event()
        original = policy.assert_mutation_allowed

        def pause_after_check(problem_id, fields):
            original(problem_id, fields)
            checked.set()
            if not proceed.wait(timeout=5):
                raise AssertionError('Reference start did not release mutation')

        def remove():
            close_old_connections()
            try:
                problem.allowed_languages.remove(self.language)
            finally:
                close_old_connections()

        with patch('judge.problem_authoring.policy.assert_mutation_allowed', side_effect=pause_after_check):
            with ThreadPoolExecutor(max_workers=2) as pool:
                mutation = pool.submit(remove)
                self.assertTrue(checked.wait(timeout=5))
                from django.db import DatabaseError, transaction
                try:
                    with self.assertRaises(DatabaseError), transaction.atomic():
                        Problem.objects.select_for_update(nowait=True).get(pk=problem.pk)
                finally:
                    proceed.set()
                mutation.result(timeout=10)
        with self.assertRaises(AuthoringError):
            start_verification(context, problem.pk, request_token=uuid.uuid4(), expected_grading_revision=1)

    def test_language_limit_queryset_delete_holds_admission_mutex(self):
        from django.db import DatabaseError, transaction
        from judge.models import LanguageLimit, ProblemAuthoringState
        from judge.problem_authoring import policy
        problem = self.make_problem()
        ProblemAuthoringState.objects.create(problem=problem, revision=1, grading_revision=1,
                                             active_data_revision=1, data_state='READY')
        limit = LanguageLimit.objects.create(problem=problem, language=self.language,
                                             time_limit=2, memory_limit=524288)
        checked = threading.Event()
        release = threading.Event()
        original = policy.assert_mutation_allowed

        def pause(problem_id, fields):
            original(problem_id, fields)
            checked.set()
            if not release.wait(timeout=10):
                raise AssertionError('Deletion was not released')

        def delete():
            close_old_connections()
            try:
                LanguageLimit.objects.filter(pk=limit.pk).delete()
            finally:
                close_old_connections()

        with patch('judge.problem_authoring.policy.assert_mutation_allowed', side_effect=pause):
            with ThreadPoolExecutor(max_workers=1) as pool:
                deletion = pool.submit(delete)
                try:
                    self.assertTrue(checked.wait(timeout=10))
                    with self.assertRaises(DatabaseError), transaction.atomic():
                        Problem.objects.select_for_update(nowait=True).get(pk=problem.pk)
                finally:
                    release.set()
                deletion.result(timeout=10)
        self.assertFalse(LanguageLimit.objects.filter(pk=limit.pk).exists())

    @override_settings(VNOJ_QUOTA_ENFORCEMENT_ENABLED=True, VNOJ_ORGANIZATION_DEFAULT_MAX_PROBLEMS=1)
    def test_quota_race_allows_one_problem(self):
        from judge.models import Organization
        organization = Organization.objects.create(name='Team', slug='team', short_name='Team', about='')
        organization.admins.add(self.user.profile)
        context = AuthoringContext(self.user.pk, organization.pk)
        barrier = threading.Barrier(2)

        def save(index):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                changes = DraftChanges(problem_fields={
                    'code': 'team_' + str(index), 'name': 'Concurrent', 'group_id': self.group.pk,
                    'time_limit': 1, 'memory_limit': 262144, 'points': 100,
                })
                try:
                    save_draft(context, changes, problem_id=None, expected_revision=None, request_token=uuid.uuid4())
                    return 'saved'
                except AuthoringError as exc:
                    return exc.code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(save, range(2)))
        self.assertCountEqual(results, ['saved', 'problem_quota'])
        self.assertEqual(Problem.objects.filter(organization=organization).count(), 1)
