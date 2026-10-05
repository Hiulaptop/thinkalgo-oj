import os
from unittest import mock

from django.test import SimpleTestCase

from judge.utils.problem_releases import (
    build_release, delete_release, list_releases, purge_releases, r2_client,
    read_release_manifest, release_key, verify_sha256,
)

R2_ENV = {
    'R2_ACCESS_KEY_ID': 'key',
    'R2_SECRET_ACCESS_KEY': 'secret',
    'R2_ENDPOINT_URL': 'https://example.r2.cloudflarestorage.com',
    'R2_PROBLEMS_BUCKET': 'problems-bucket',
}


class ReleaseKeyTest(SimpleTestCase):
    def test_release_key_format(self):
        self.assertEqual(release_key('odd1out_2', 'v1'), 'releases/odd1out_2/v1')


class R2ClientTest(SimpleTestCase):
    def test_missing_settings_raise(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                r2_client()
        self.assertIn('R2_ACCESS_KEY_ID', str(ctx.exception))

    def test_client_built_with_env(self):
        with mock.patch.dict(os.environ, R2_ENV, clear=True), \
             mock.patch('judge.utils.problem_releases.boto3.client') as client_factory:
            r2_client()
        client_factory.assert_called_once_with(
            's3',
            endpoint_url='https://example.r2.cloudflarestorage.com',
            region_name='auto',
            aws_access_key_id='key',
            aws_secret_access_key='secret',
        )


class BuildReleaseTest(SimpleTestCase):
    def test_build_release_deterministic_hash(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as source_dir:
            source = Path(source_dir)
            (source / 'init.yml').write_text('archive: data.zip\n')
            (source / 'data.zip').write_bytes(b'fake test data')

            package_a, manifest_bytes_a, manifest_a = build_release(source, 'code1', 'v1')
            package_b, manifest_bytes_b, manifest_b = build_release(source, 'code1', 'v1')

        # Same input directory -> same package bytes -> same sha256, regardless of
        # when the build ran (only created_at differs between the two manifests).
        self.assertEqual(package_a, package_b)
        self.assertEqual(manifest_a['sha256'], manifest_b['sha256'])
        self.assertEqual(manifest_a['package'], 'releases/code1/v1/package.zip')

    def test_missing_source_dir_raises(self):
        with self.assertRaises(ValueError):
            build_release('/no/such/directory', 'code1', 'v1')


class VerifySha256Test(SimpleTestCase):
    def test_verify_sha256_matches(self):
        import hashlib
        import tempfile

        with tempfile.NamedTemporaryFile() as f:
            f.write(b'hello world')
            f.flush()
            expected = hashlib.sha256(b'hello world').hexdigest()
            self.assertTrue(verify_sha256(f.name, expected))
            self.assertFalse(verify_sha256(f.name, 'deadbeef'))


class ReadReleaseManifestTest(SimpleTestCase):
    def test_read_release_manifest(self):
        fake_body = mock.Mock()
        fake_body.read.return_value = b'{"code": "p1", "version": "v1", "sha256": "abc"}'
        fake_client = mock.Mock()
        fake_client.get_object.return_value = {'Body': fake_body}

        with mock.patch.dict(os.environ, R2_ENV, clear=True), \
             mock.patch('judge.utils.problem_releases.r2_client', return_value=fake_client):
            manifest = read_release_manifest('p1', 'v1')

        fake_client.get_object.assert_called_once_with(Bucket='problems-bucket', Key='releases/p1/v1/manifest.json')
        self.assertEqual(manifest['sha256'], 'abc')


class ListReleasesTest(SimpleTestCase):
    def test_list_releases_parses_common_prefixes(self):
        fake_client = mock.Mock()
        fake_paginator = mock.Mock()
        fake_paginator.paginate.return_value = [{
            'CommonPrefixes': [
                {'Prefix': 'releases/p1/v1/'},
                {'Prefix': 'releases/p1/v2/'},
            ],
        }]
        fake_client.get_paginator.return_value = fake_paginator
        fake_client.head_object.side_effect = [
            {'LastModified': 'yesterday', 'ContentLength': 100},
            {'LastModified': 'today', 'ContentLength': 200},
        ]

        with mock.patch.dict(os.environ, R2_ENV, clear=True), \
             mock.patch('judge.utils.problem_releases.r2_client', return_value=fake_client):
            releases = list_releases('p1')

        versions = [r['version'] for r in releases]
        self.assertEqual(sorted(versions), ['v1', 'v2'])
        self.assertEqual(len(releases), 2)
        fake_client.get_paginator.assert_called_once_with('list_objects_v2')

    def test_list_releases_empty(self):
        fake_client = mock.Mock()
        fake_paginator = mock.Mock()
        fake_paginator.paginate.return_value = [{}]
        fake_client.get_paginator.return_value = fake_paginator

        with mock.patch.dict(os.environ, R2_ENV, clear=True), \
             mock.patch('judge.utils.problem_releases.r2_client', return_value=fake_client):
            releases = list_releases('p1')

        self.assertEqual(releases, [])


class PurgeReleasesTest(SimpleTestCase):
    def test_purge_releases_deletes_every_object(self):
        fake_client = mock.Mock()
        fake_paginator = mock.Mock()
        fake_paginator.paginate.return_value = [
            {'Contents': [
                {'Key': 'releases/p1/v1/package.zip'},
                {'Key': 'releases/p1/v1/manifest.json'},
            ]},
            {'Contents': [
                {'Key': 'releases/p1/v2/package.zip'},
                {'Key': 'releases/p1/v2/manifest.json'},
            ]},
        ]
        fake_client.get_paginator.return_value = fake_paginator

        with mock.patch.dict(os.environ, R2_ENV, clear=True), \
             mock.patch('judge.utils.problem_releases.r2_client', return_value=fake_client):
            purge_releases('p1')

        self.assertEqual(fake_client.delete_objects.call_count, 2)
        first_call_keys = {o['Key'] for o in fake_client.delete_objects.call_args_list[0].kwargs['Delete']['Objects']}
        self.assertEqual(first_call_keys, {'releases/p1/v1/package.zip', 'releases/p1/v1/manifest.json'})

    def test_purge_releases_no_objects_skips_delete_call(self):
        fake_client = mock.Mock()
        fake_paginator = mock.Mock()
        fake_paginator.paginate.return_value = [{}]
        fake_client.get_paginator.return_value = fake_paginator

        with mock.patch.dict(os.environ, R2_ENV, clear=True), \
             mock.patch('judge.utils.problem_releases.r2_client', return_value=fake_client):
            purge_releases('p1')

        fake_client.delete_objects.assert_not_called()


class DeleteReleaseTest(SimpleTestCase):
    def test_delete_release_removes_objects_and_clears_problem_data(self):
        fake_client = mock.Mock()
        fake_data = mock.Mock(r2_release_version='v1')
        fake_queryset = mock.Mock()
        fake_queryset.first.return_value = fake_data

        with mock.patch.dict(os.environ, R2_ENV, clear=True), \
             mock.patch('judge.utils.problem_releases.r2_client', return_value=fake_client), \
             mock.patch('judge.models.ProblemData.objects') as manager:
            manager.filter.return_value = fake_queryset
            delete_release('p1', 'v1')

        fake_client.delete_objects.assert_called_once()
        deleted_keys = {o['Key'] for o in fake_client.delete_objects.call_args.kwargs['Delete']['Objects']}
        self.assertEqual(deleted_keys, {'releases/p1/v1/package.zip', 'releases/p1/v1/manifest.json'})
        self.assertEqual(fake_data.r2_release_version, '')
        self.assertEqual(fake_data.r2_release_sha256, '')
        self.assertEqual(fake_data.r2_release_key, '')
        self.assertIsNone(fake_data.r2_released_at)
        fake_data.save.assert_called_once()

    def test_delete_release_leaves_other_versions_alone(self):
        fake_client = mock.Mock()
        fake_queryset = mock.Mock()
        fake_queryset.first.return_value = None  # not the currently-recorded release

        with mock.patch.dict(os.environ, R2_ENV, clear=True), \
             mock.patch('judge.utils.problem_releases.r2_client', return_value=fake_client), \
             mock.patch('judge.models.ProblemData.objects') as manager:
            manager.filter.return_value = fake_queryset
            delete_release('p1', 'v0')

        fake_client.delete_objects.assert_called_once()
