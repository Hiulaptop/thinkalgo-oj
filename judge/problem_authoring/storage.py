import hashlib
import os
from pathlib import Path

from django.conf import settings

from judge.problem_authoring.types import AuthoringError


def authoring_root():
    return Path(getattr(settings, 'PROBLEM_AUTHORING_ROOT',
                        getattr(settings, 'PROBLEM_PACKAGE_ROOT', '/private-problem-imports') + '/authoring'))


def upload_path(upload):
    root = authoring_root().resolve()
    path = (root / upload.path).resolve()
    if not path.is_relative_to(root):
        raise AuthoringError('storage_error', 'Upload storage reference is invalid.')
    return path


def sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def sync_artifact_directory(path):
    for artifact in path.iterdir():
        if artifact.is_file():
            with artifact.open('rb') as source:
                os.fsync(source.fileno())
    sync_directory(path)
    sync_directory(path.parent)


def stage_upload(stream, upload_id):
    root = authoring_root()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    folder = root / str(upload_id)
    folder.mkdir(mode=0o700)
    path = folder / 'upload'
    size = 0
    digest = hashlib.sha256()
    limit = getattr(settings, 'PROBLEM_AUTHORING_UPLOAD_LIMIT', 100 * 1024**2)
    try:
        stream.seek(0)
        with path.open('xb') as target:
            os.chmod(path, 0o600)
            for chunk in iter(lambda: stream.read(65536), b''):
                size += len(chunk)
                if size > limit:
                    raise AuthoringError('upload_too_large', 'Upload exceeds size limit.')
                digest.update(chunk)
                target.write(chunk)
            target.flush()
            os.fsync(target.fileno())
        sync_directory(folder)
        sync_directory(root)
        return path.relative_to(root).as_posix(), digest.hexdigest(), size
    except Exception:
        path.unlink(missing_ok=True)
        folder.rmdir()
        raise
