import hashlib
import re
import stat
import zipfile
from pathlib import PurePosixPath

from django.conf import settings

from judge.problem_authoring.types import AuthoringError, CaseSpec, PackageManifest


def _error(message):
    return AuthoringError('invalid_package', message)


def _limit(name, default):
    return getattr(settings, 'PROBLEM_AUTHORING_' + name, default)


def _natural_key(name):
    return tuple((1, int(part)) if part.isdigit() else (0, part) for part in re.split(r'(\d+)', name))


def _pair_cases(names):
    inputs = {name[:-3] for name in names if name.endswith('.in')}
    outputs = {name[:-4] for name in names if name.endswith('.out')}
    if not inputs or inputs != outputs:
        missing = ', '.join(sorted(inputs ^ outputs))
        raise _error('Missing input/output pairs: ' + (missing or '(no tests)'))
    return [CaseSpec(name + '.in', name + '.out', index)
            for index, name in enumerate(sorted(inputs, key=_natural_key), 1)]


def _root(files, full):
    if full:
        candidates = [name[:-len('statement.md')] for name in files
                      if name == 'statement.md' or (name.endswith('/statement.md') and name.count('/') == 1)]
        if len(candidates) != 1:
            raise _error('Expected one package root with statement.md.')
        return candidates[0]
    parents = {str(PurePosixPath(name).parent) for name in files}
    if len(parents) != 1:
        raise _error('Tests must share one unambiguous directory.')
    parent = parents.pop()
    if parent == '.':
        return ''
    parts = parent.split('/')
    if len(parts) > 2 or (len(parts) == 2 and parts[-1] != 'tests'):
        raise _error('Expected tests at root, tests/, wrapper/, or wrapper/tests/.')
    return parent + '/'


def _archive_files(archive):
    infos = archive.infolist()
    if len(infos) > _limit('ENTRY_LIMIT', 10000):
        raise _error('ZIP contains too many entries.')
    seen = set()
    files = {}
    for info in infos:
        name = info.orig_filename
        parts = name.rstrip('/').split('/')
        if ('\x00' in name or '\\' in name or ':' in name or name.startswith('/') or
                any(part in ('', '.', '..') for part in parts) or
                stat.S_ISLNK(info.external_attr >> 16) or info.flag_bits & 1):
            raise _error('Unsafe ZIP entry: ' + name)
        normalized = str(PurePosixPath(name))
        if normalized in seen:
            raise _error('Duplicate ZIP entry: ' + name)
        seen.add(normalized)
        if not info.is_dir():
            files[name] = info
    if not files:
        raise _error('ZIP contains no files.')
    return files


def inspect_data_archive(path):
    expanded = 0
    try:
        with zipfile.ZipFile(path) as archive:
            files = _archive_files(archive)
            for info in files.values():
                size = 0
                with archive.open(info) as source:
                    for chunk in iter(lambda: source.read(65536), b''):
                        size += len(chunk)
                        expanded += len(chunk)
                        if (size > _limit('TEST_FILE_LIMIT', 256 * 1024**2) or
                                expanded > _limit('EXPANDED_LIMIT', 1024**3)):
                            raise _error('Expanded ZIP exceeds size limit.')
            return list(files)
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError) as exc:
        raise _error('Invalid data ZIP.') from exc


def _inspect(stream, *, full):
    stream.seek(0, 2)
    compressed = stream.tell()
    if compressed > _limit('UPLOAD_LIMIT', 100 * 1024**2):
        raise _error('ZIP exceeds upload limit.')
    stream.seek(0)
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(65536), b''):
        digest.update(chunk)
    stream.seek(0)
    try:
        with zipfile.ZipFile(stream) as archive:
            files = _archive_files(archive)
            root = _root(files, full)
            text_names = {'statement.md', 'editorial.md', 'solution.cpp'} if full else set()
            tests = []
            texts = {}
            expanded = 0
            for name, info in files.items():
                if not name.startswith(root):
                    raise _error('File outside package root: ' + name)
                relative = name[len(root):]
                is_text = relative in text_names
                is_test = (relative.startswith('tests/') and relative.count('/') == 1) if full else '/' not in relative
                is_test = is_test and relative.endswith(('.in', '.out'))
                if not is_text and not is_test:
                    raise _error('Unsupported file: ' + relative)
                if is_test and len(relative) > 100:
                    raise _error('Testcase file name exceeds 100 characters: ' + relative)
                file_limit = _limit('TEXT_LIMIT', 5 * 1024**2) if is_text else _limit('TEST_FILE_LIMIT', 256 * 1024**2)
                if info.file_size > file_limit:
                    raise _error('File exceeds size limit: ' + relative)
                size = 0
                chunks = []
                with archive.open(info) as source:
                    for chunk in iter(lambda: source.read(65536), b''):
                        size += len(chunk)
                        expanded += len(chunk)
                        if size > file_limit or expanded > _limit('EXPANDED_LIMIT', 1024**3):
                            raise _error('Expanded ZIP exceeds size limit.')
                        if is_text:
                            chunks.append(chunk)
                if is_text:
                    texts[relative] = b''.join(chunks).decode('utf-8-sig')
                else:
                    tests.append(relative)
            fields = {'root': root}
            source_name = None
            if full:
                statement = texts['statement.md']
                if not statement.strip():
                    raise _error('Empty required file: statement.md')
                fields['description'] = statement
                title = re.search(r'^#\s+(.+)$', statement, re.M)
                time = re.search(r'Giới hạn thời gian:\*\*\s*([0-9]+(?:\.[0-9]+)?)\s*giây', statement)
                memory = re.search(r'Giới hạn bộ nhớ:\*\*\s*([0-9]+)\s*MB', statement)
                if title:
                    fields['name'] = title.group(1).strip()
                if time:
                    fields['time_limit'] = float(time.group(1))
                if memory:
                    fields['memory_limit'] = int(memory.group(1)) * 1024
                if 'editorial.md' in texts:
                    fields['editorial'] = texts['editorial.md']
                if 'solution.cpp' in texts:
                    if not texts['solution.cpp'].strip():
                        raise _error('Empty source file: solution.cpp')
                    source_name = root + 'solution.cpp'
            cases = _pair_cases(tests) if tests or not full else []
            return PackageManifest('PACKAGE' if full else 'TESTS', fields, cases, source_name, [],
                                   digest.hexdigest(), compressed, expanded)
    except (zipfile.BadZipFile, UnicodeDecodeError, RuntimeError, NotImplementedError, EOFError) as exc:
        raise _error('Invalid ZIP or UTF-8 content.') from exc


def inspect_tests(stream):
    return _inspect(stream, full=False)


def inspect_full_package(stream):
    return _inspect(stream, full=True)
