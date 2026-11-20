import importlib.util
import io
from datetime import timedelta
from pathlib import Path

from django.test import TestCase, override_settings
from django.utils import timezone

from judge.models import Organization, ProblemAuthoringUpload
from judge.models.tests.util import create_user
from judge.problem_authoring.types import AuthoringContext, AuthoringError
from judge.tests.authoring_helpers import AuthoringTestMixin, make_zip


class AuthoringUploadTest(AuthoringTestMixin, TestCase):
    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('judge.problem_authoring.uploads'),
                             'Private authoring uploads are missing')
        from judge.problem_authoring import uploads
        return uploads

    @property
    def context(self):
        return AuthoringContext(self.user.pk)

    def test_upload_is_private_and_owned(self):
        upload = self.api().receive_upload(self.context, make_zip({'1.in': '1', '1.out': '2'}), 'TESTS')
        path = Path(self.temp.name, 'uploads', upload.path)
        self.assertTrue(path.is_file())
        self.assertEqual(upload.owner_id, self.user.profile.pk)
        self.assertEqual(upload.manifest['tests'][0]['input_file'], '1.in')
        self.assertEqual(upload.manifest['tests'][0]['points'], '1')
        other = create_user('other', is_superuser=True)
        with self.assertRaises(AuthoringError):
            self.api().get_upload(AuthoringContext(other.pk), upload.pk, kind='TESTS')

    def test_expired_unconsumed_upload_is_rejected(self):
        upload = self.api().receive_upload(self.context, io.BytesIO(b'int main() {}'), 'SOURCE')
        ProblemAuthoringUpload.objects.filter(pk=upload.pk).update(expires_at=timezone.now())
        with self.assertRaises(AuthoringError):
            self.api().get_upload(self.context, upload.pk, kind='SOURCE', for_consumption=True)

    def test_consumed_upload_survives_expiry_for_same_problem(self):
        upload = self.api().receive_upload(self.context, io.BytesIO(b'int main() {}'), 'SOURCE')
        problem = self.make_problem()
        upload.consumed_by = problem
        upload.expires_at = timezone.now() - timedelta(days=1)
        upload.save()
        found = self.api().get_upload(self.context, upload.pk, kind='SOURCE', problem_id=problem.pk)
        self.assertEqual(found.pk, upload.pk)
        with self.assertRaises(AuthoringError):
            self.api().get_upload(self.context, upload.pk, kind='SOURCE', for_consumption=True)

    def test_permission_revoked_before_consumption(self):
        user = create_user('limited', user_permissions=('add_problem', 'edit_own_problem'))
        context = AuthoringContext(user.pk)
        upload = self.api().receive_upload(context, io.BytesIO(b'x'), 'SOURCE')
        user.user_permissions.clear()
        with self.assertRaises(AuthoringError):
            self.api().get_upload(context, upload.pk, kind='SOURCE', for_consumption=True)

    @override_settings(PROBLEM_AUTHORING_OWNER_UPLOAD_LIMIT=12)
    def test_exact_quota_boundary_and_failed_upload_reservation(self):
        self.api().receive_upload(self.context, io.BytesIO(b'123456'), 'SOURCE')
        self.api().receive_upload(self.context, io.BytesIO(b'123456'), 'SOURCE')
        with self.assertRaises(AuthoringError):
            self.api().receive_upload(self.context, io.BytesIO(b'x'), 'SOURCE')
        self.assertEqual(ProblemAuthoringUpload.objects.count(), 2)
        self.assertEqual(len(list(Path(self.temp.name, 'uploads').rglob('upload'))), 2)

    def test_bad_source_and_missing_pdf_permission(self):
        with self.assertRaises(AuthoringError):
            self.api().receive_upload(self.context, io.BytesIO(b'\xff'), 'SOURCE')
        user = create_user('nopdf', user_permissions=('add_problem', 'edit_own_problem'))
        with self.assertRaises(AuthoringError):
            self.api().receive_upload(AuthoringContext(user.pk), io.BytesIO(b'%PDF-1.4'), 'PDF')
        self.assertEqual(ProblemAuthoringUpload.objects.count(), 0)

    def test_package_permission_is_separate_from_test_upload(self):
        user = create_user('testonly', user_permissions=('add_problem', 'edit_own_problem'))
        context = AuthoringContext(user.pk)
        self.api().receive_upload(context, make_zip({'1.in': '1', '1.out': '2'}), 'TESTS')
        with self.assertRaises(AuthoringError):
            self.api().receive_upload(context, make_zip({'statement.md': '# Title'}), 'PACKAGE')

    @override_settings(VNOJ_QUOTA_ENFORCEMENT_ENABLED=True, VNOJ_ORGANIZATION_DEFAULT_MAX_STORAGE=12)
    def test_organization_quota_and_scope(self):
        organization = Organization.objects.create(name='Team', slug='team', short_name='Team', about='')
        organization.admins.add(self.user.profile)
        context = AuthoringContext(self.user.pk, organization.pk)
        upload = self.api().receive_upload(context, io.BytesIO(b'123456'), 'SOURCE')
        self.api().receive_upload(context, io.BytesIO(b'123456'), 'SOURCE')
        with self.assertRaises(AuthoringError):
            self.api().receive_upload(context, io.BytesIO(b'x'), 'SOURCE')
        with self.assertRaises(AuthoringError):
            self.api().get_upload(self.context, upload.pk, kind='SOURCE')

    def test_org_only_author_does_not_need_global_creation_permission(self):
        user = create_user('orgauthor', user_permissions=('create_organization_problem', 'edit_own_problem'))
        organization = Organization.objects.create(name='Club', slug='club', short_name='Club', about='')
        organization.admins.add(user.profile)
        upload = self.api().receive_upload(AuthoringContext(user.pk, organization.pk), io.BytesIO(b'x'), 'SOURCE')
        self.assertEqual(upload.organization_id, organization.pk)
        self.assertEqual(upload.owner_id, user.profile.pk)

    def test_consumed_source_is_readable_by_authorized_collaborator(self):
        from judge.problem_authoring.uploads import receive_upload
        problem = self.make_problem()
        problem.authors.add(self.user.profile)
        upload = receive_upload(self.context, io.BytesIO(b'private source'), 'SOURCE')
        upload.consumed_by = problem
        upload.save()
        collaborator = create_user('collaborator', user_permissions=('edit_own_problem',))
        problem.curators.add(collaborator.profile)
        found = self.api().get_upload(AuthoringContext(collaborator.pk), upload.pk,
                                      kind='SOURCE', problem_id=problem.pk)
        self.assertEqual(found.pk, upload.pk)

    def test_upload_checksum_is_verified_before_consumption(self):
        from judge.problem_authoring.storage import upload_path
        upload = self.api().receive_upload(self.context, io.BytesIO(b'original'), 'SOURCE')
        upload_path(upload).write_bytes(b'modified')
        with self.assertRaises(AuthoringError):
            self.api().get_upload(self.context, upload.pk, kind='SOURCE', for_consumption=True)

    @override_settings(VNOJ_QUOTA_ENFORCEMENT_ENABLED=True, VNOJ_ORGANIZATION_DEFAULT_MAX_STORAGE=10,
                       PROBLEM_AUTHORING_REPLACEMENT_BUDGET=0)
    def test_reserved_advanced_snapshot_counts_against_later_uploads(self):
        from judge.models import ProblemDataOperation
        organization = Organization.objects.create(name='Team', slug='team', short_name='Team', about='')
        organization.admins.add(self.user.profile)
        problem = self.make_problem()
        problem.organization = organization
        problem.save()
        ProblemDataOperation.objects.create(problem=problem, target_revision=1,
                                            config={'snapshot_bytes': 10, 'owner_id': self.user.profile.pk})
        with self.assertRaises(AuthoringError):
            self.api().receive_upload(AuthoringContext(self.user.pk, organization.pk), io.BytesIO(b'x'), 'SOURCE')

    def test_permission_revoked_during_inspection_rejects_staging(self):
        from unittest.mock import patch
        from judge.problem_authoring import uploads
        user = create_user('revokedupload', user_permissions=('add_problem', 'edit_own_problem'))
        context = AuthoringContext(user.pk)
        original = uploads._manifest

        def revoke_after_inspection(stream, kind):
            result = original(stream, kind)
            user.user_permissions.clear()
            return result

        with patch('judge.problem_authoring.uploads._manifest', side_effect=revoke_after_inspection):
            with self.assertRaises(AuthoringError):
                uploads.receive_upload(context, io.BytesIO(b'private source'), 'SOURCE')
        self.assertFalse(ProblemAuthoringUpload.objects.exists())

    @override_settings(PROBLEM_AUTHORING_OWNER_UPLOAD_LIMIT=10)
    def test_ready_snapshot_still_on_disk_counts_toward_owner_quota(self):
        from judge.models import ProblemDataOperation
        problem = self.make_problem()
        ProblemDataOperation.objects.create(problem=problem, target_revision=1, state='READY',
                                            config={'snapshot_bytes': 10, 'owner_id': self.user.profile.pk})
        with self.assertRaises(AuthoringError):
            self.api().receive_upload(self.context, io.BytesIO(b'x'), 'SOURCE')

    def test_pdf_retry_after_metadata_failure_reuses_one_media_object(self):
        import tempfile
        from unittest.mock import patch
        from django.core.files.storage import FileSystemStorage
        from judge.problem_authoring.uploads import publish_staged_pdf
        upload = self.api().receive_upload(self.context, io.BytesIO(b'%PDF-1.4'), 'PDF')
        original_save = ProblemAuthoringUpload.save

        def fail_manifest_save(instance, *args, **kwargs):
            if kwargs.get('update_fields') == ['manifest']:
                raise RuntimeError('metadata write interrupted')
            return original_save(instance, *args, **kwargs)

        with tempfile.TemporaryDirectory() as media_root:
            storage = FileSystemStorage(location=media_root)
            with patch('judge.views.widgets.default_storage', storage):
                with patch.object(ProblemAuthoringUpload, 'save', fail_manifest_save):
                    with self.assertRaises(RuntimeError):
                        publish_staged_pdf(self.context, upload.pk)
                url = publish_staged_pdf(self.context, upload.pk)
            self.assertEqual(len(list(Path(media_root).rglob('*.pdf'))), 1)
            upload.refresh_from_db()
            self.assertEqual(upload.manifest['published_url'], url)

    def test_expired_unconsumed_published_pdf_is_removed_from_media_and_staging(self):
        import tempfile
        from unittest.mock import patch
        from django.core.files.storage import FileSystemStorage
        from judge.problem_authoring.data import reconcile_authoring
        from judge.problem_authoring.storage import upload_path
        from judge.problem_authoring.uploads import publish_staged_pdf
        upload = self.api().receive_upload(self.context, io.BytesIO(b'%PDF-1.4'), 'PDF')
        with tempfile.TemporaryDirectory() as media_root:
            storage = FileSystemStorage(location=media_root)
            with patch('judge.views.widgets.default_storage', storage):
                publish_staged_pdf(self.context, upload.pk)
                self.assertEqual(len(list(Path(media_root).rglob('*.pdf'))), 1)
                ProblemAuthoringUpload.objects.filter(pk=upload.pk).update(expires_at=timezone.now())
                reconcile_authoring(now=timezone.now())
            self.assertFalse(list(Path(media_root).rglob('*.pdf')))
        self.assertFalse(ProblemAuthoringUpload.objects.filter(pk=upload.pk).exists())
        self.assertFalse(upload_path(upload).parent.exists())

    def test_one_expired_pdf_storage_failure_does_not_block_other_cleanup(self):
        from unittest.mock import patch
        from judge.problem_authoring.data import reconcile_authoring
        pdf = self.api().receive_upload(self.context, io.BytesIO(b'%PDF-1.4'), 'PDF')
        source = self.api().receive_upload(self.context, io.BytesIO(b'expired'), 'SOURCE')
        ProblemAuthoringUpload.objects.update(expires_at=timezone.now())
        with patch('judge.views.widgets.default_storage.delete', side_effect=OSError('media offline')):
            result = reconcile_authoring(now=timezone.now())
        self.assertEqual(result['cleaned'], 1)
        self.assertTrue(ProblemAuthoringUpload.objects.filter(pk=pdf.pk).exists())
        self.assertFalse(ProblemAuthoringUpload.objects.filter(pk=source.pk).exists())

    @override_settings(PROBLEM_AUTHORING_OWNER_UPLOAD_LIMIT=10)
    def test_operation_workspace_reservation_counts_toward_owner_quota(self):
        from judge.models import ProblemDataOperation
        problem = self.make_problem()
        ProblemDataOperation.objects.create(problem=problem, target_revision=1,
                                            config={'workspace_bytes': 10, 'owner_id': self.user.profile.pk})
        with self.assertRaises(AuthoringError):
            self.api().receive_upload(self.context, io.BytesIO(b'x'), 'SOURCE')

    def test_staging_directory_flush_failure_does_not_commit_upload(self):
        import os
        import stat
        from unittest.mock import patch
        original = os.fsync

        def fail_directory(descriptor):
            if stat.S_ISDIR(os.fstat(descriptor).st_mode):
                raise OSError('directory flush failed')
            return original(descriptor)

        with patch('os.fsync', side_effect=fail_directory):
            with self.assertRaises(AuthoringError):
                self.api().receive_upload(self.context, io.BytesIO(b'private source'), 'SOURCE')
        self.assertFalse(ProblemAuthoringUpload.objects.exists())
        self.assertFalse(list(Path(self.temp.name, 'uploads').glob('*/upload')))

    def test_unconsumed_upload_expiry_is_24_hours(self):
        start = timezone.now()
        upload = self.api().receive_upload(self.context, io.BytesIO(b'x'), 'SOURCE')
        self.assertGreaterEqual(upload.expires_at, start + timedelta(hours=24))
        self.assertLess(upload.expires_at, timezone.now() + timedelta(hours=24, seconds=1))
