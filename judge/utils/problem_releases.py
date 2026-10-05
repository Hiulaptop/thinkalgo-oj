import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.utils import timezone as django_timezone


def release_key(code, version):
    return f'releases/{code}/{version}'


def _require_r2_settings():
    required = ('R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY', 'R2_ENDPOINT_URL', 'R2_PROBLEMS_BUCKET')
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f'Missing R2 settings: {", ".join(missing)}')


def r2_client():
    """Build a boto3 S3-compatible client for the R2 problems bucket.

    Raises RuntimeError if the required environment variables are not set.
    """
    _require_r2_settings()
    return boto3.client(
        's3',
        endpoint_url=os.environ['R2_ENDPOINT_URL'],
        region_name='auto',
        aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'].strip(),
        aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'].strip(),
    )


def _problems_bucket():
    return os.environ['R2_PROBLEMS_BUCKET']


def next_release_version(code):
    from judge.models import ProblemData

    data = ProblemData.objects.filter(problem__code=code).first()
    if data and data.r2_release_version.startswith('v'):
        try:
            current = int(data.r2_release_version[1:])
            return f'v{current + 1}'
        except ValueError:
            pass
    return 'v1'


def build_release(source_dir, code, version):
    """Build a deterministic zip and manifest for a local problem directory."""
    source_dir = Path(source_dir).resolve()
    if not source_dir.is_dir():
        raise ValueError(f'Problem directory does not exist: {source_dir}')

    with tempfile.TemporaryDirectory() as temp_dir:
        package_path = Path(temp_dir) / 'package.zip'
        with zipfile.ZipFile(package_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(source_dir.rglob('*')):
                if path.is_file():
                    archive.write(path, path.relative_to(source_dir).as_posix())

        digest = hashlib.sha256(package_path.read_bytes()).hexdigest()
        manifest = {
            'code': code,
            'version': version,
            'sha256': digest,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'package': f'{release_key(code, version)}/package.zip',
        }
        return package_path.read_bytes(), json.dumps(manifest, sort_keys=True).encode(), manifest


def publish_problem_to_r2(code, version=None):
    """Upload local problem data to R2 and record release metadata on ProblemData.

    This is the "write" half of the R2 release mechanism: it always creates a
    brand-new, immutable, sha256-verified version (never overwrites an
    existing one in place), and points ProblemData at it. Call this any time
    local test data (including test case points) changes and the change
    needs to reach judges that grade from R2.
    """
    from judge.models import Problem, ProblemData

    version = version or next_release_version(code)
    source_dir = os.path.join(settings.DMOJ_PROBLEM_DATA_ROOT, code)
    package, manifest_bytes, manifest = build_release(source_dir, code, version)
    client = r2_client()
    prefix = release_key(code, version)
    bucket = _problems_bucket()
    package_key = f'{prefix}/package.zip'
    client.put_object(Bucket=bucket, Key=package_key, Body=package, ContentType='application/zip')
    client.put_object(Bucket=bucket, Key=f'{prefix}/manifest.json', Body=manifest_bytes,
                      ContentType='application/json')

    problem = Problem.objects.filter(code=code).first()
    if problem is not None:
        data, _ = ProblemData.objects.get_or_create(problem=problem)
        data.r2_release_version = version
        data.r2_release_sha256 = manifest['sha256']
        data.r2_release_key = package_key
        data.r2_released_at = django_timezone.now()
        data.save(update_fields=[
            'r2_release_version', 'r2_release_sha256', 'r2_release_key', 'r2_released_at',
        ])
    return manifest


def read_release_manifest(code, version):
    """Read (the "read" half) a release's manifest.json back from R2."""
    client = r2_client()
    bucket = _problems_bucket()
    key = f'{release_key(code, version)}/manifest.json'
    response = client.get_object(Bucket=bucket, Key=key)
    return json.loads(response['Body'].read())


def list_releases(code):
    """List every published release version for a problem, newest first.

    Returns a list of dicts: {'version', 'package_key', 'last_modified', 'size'}.
    """
    client = r2_client()
    bucket = _problems_bucket()
    prefix = f'releases/{code}/'
    paginator = client.get_paginator('list_objects_v2')
    releases = {}
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter='/'):
        for entry in page.get('CommonPrefixes', []):
            # entry['Prefix'] looks like 'releases/{code}/{version}/'
            version = entry['Prefix'][len(prefix):].rstrip('/')
            if version:
                releases[version] = {'version': version, 'package_key': f'releases/{code}/{version}/package.zip'}
    # Fill in size/last_modified for the package object of each version found above.
    for info in releases.values():
        try:
            head = client.head_object(Bucket=bucket, Key=info['package_key'])
            info['last_modified'] = head['LastModified']
            info['size'] = head['ContentLength']
        except ClientError:
            info['last_modified'] = None
            info['size'] = None
    return sorted(releases.values(), key=lambda r: r['version'], reverse=True)


def delete_release(code, version):
    """Delete (the "delete" half) one specific release's objects from R2.

    If this is the release currently recorded on ProblemData, clears those
    fields so the problem is no longer considered published until a new
    release is published.
    """
    from judge.models import ProblemData

    client = r2_client()
    bucket = _problems_bucket()
    prefix = release_key(code, version)
    keys = [f'{prefix}/package.zip', f'{prefix}/manifest.json']
    client.delete_objects(Bucket=bucket, Delete={'Objects': [{'Key': key} for key in keys]})

    data = ProblemData.objects.filter(problem__code=code, r2_release_version=version).first()
    if data is not None:
        data.r2_release_version = ''
        data.r2_release_sha256 = ''
        data.r2_release_key = ''
        data.r2_released_at = None
        data.save(update_fields=[
            'r2_release_version', 'r2_release_sha256', 'r2_release_key', 'r2_released_at',
        ])


def purge_releases(code):
    """Delete every published release for a problem (used when a problem is deleted)."""
    client = r2_client()
    bucket = _problems_bucket()
    prefix = f'releases/{code}/'
    paginator = client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        objects = [{'Key': obj['Key']} for obj in page.get('Contents', [])]
        if objects:
            client.delete_objects(Bucket=bucket, Delete={'Objects': objects})


def verify_sha256(path, expected):
    digest = hashlib.sha256()
    with open(path, 'rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest() == expected


def activate_release(package_path, target_dir, code):
    """Extract a verified package and atomically replace the active problem."""
    target_dir = Path(target_dir)
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(tempfile.mkdtemp(prefix=f'.{code}.', dir=target_dir.parent))
    try:
        with zipfile.ZipFile(package_path) as archive:
            staging_root = staging_dir.resolve()
            for member in archive.infolist():
                destination = (staging_root / member.filename).resolve()
                if os.path.commonpath((staging_root, destination)) != str(staging_root):
                    raise ValueError(f'Unsafe path in release package: {member.filename}')
            archive.extractall(staging_dir)
        active_dir = target_dir.parent / f'.{code}.active'
        previous_dir = target_dir.parent / f'.{code}.previous'
        if active_dir.exists():
            shutil.rmtree(active_dir)
        staging_dir.rename(active_dir)
        if target_dir.exists():
            if previous_dir.exists():
                shutil.rmtree(previous_dir)
            target_dir.rename(previous_dir)
        active_dir.rename(target_dir)
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
