"""Bounded reader for Markdown problem packages; never extracts uploaded paths."""
import hashlib
import re
import stat
import zipfile
from pathlib import PurePosixPath


class PackageValidationError(ValueError):
    pass


def inspect_package(stream, upload_limit=100 * 1024**2, expanded_limit=1024**3):
    stream.seek(0, 2)
    if stream.tell() > upload_limit:
        raise PackageValidationError('ZIP exceeds upload limit.')
    stream.seek(0)
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(65536), b''):
        digest.update(chunk)
    stream.seek(0)
    try:
        with zipfile.ZipFile(stream) as archive:
            infos = archive.infolist()
            if len(infos) > 10000:
                raise PackageValidationError('ZIP contains too many entries.')
            names = set()
            for info in infos:
                name = info.orig_filename
                parts = name.rstrip('/').split('/')
                if ('\x00' in name or '\\' in name or ':' in name or name.startswith('/') or
                        any(part in ('', '.', '..') for part in parts) or
                        stat.S_ISLNK(info.external_attr >> 16) or info.flag_bits & 1):
                    raise PackageValidationError('Unsafe ZIP entry: %s' % name)
                normalized = str(PurePosixPath(name))
                if normalized in names:
                    raise PackageValidationError('Duplicate ZIP entry: %s' % name)
                names.add(normalized)
            files = {i.filename: i for i in infos if not i.is_dir()}
            roots = [name[:-len('statement.md')] for name in files
                     if name == 'statement.md' or (name.endswith('/statement.md') and name.count('/') == 1)]
            if len(roots) != 1:
                raise PackageValidationError('Expected one package root with statement.md.')
            root = roots[0]
            required = ('statement.md', 'editorial.md', 'solution.cpp')
            if any(root + name not in files for name in required):
                raise PackageValidationError('Required: statement.md, editorial.md, solution.cpp.')
            text = {}
            total = 0
            for name, info in files.items():
                relative = name[len(root):] if name.startswith(root) else name
                limit = 5 * 1024**2 if relative in required else 256 * 1024**2
                size = 0
                chunks = []
                with archive.open(info) as source:
                    for chunk in iter(lambda: source.read(65536), b''):
                        size += len(chunk)
                        total += len(chunk)
                        if size > limit or total > expanded_limit:
                            raise PackageValidationError('Expanded ZIP exceeds size limit.')
                        if name == root + relative and relative in required:
                            chunks.append(chunk)
                if relative in required and name == root + relative:
                    text[relative] = b''.join(chunks).decode('utf-8-sig')
                    if not text[relative].strip():
                        raise PackageValidationError('Empty required file: %s' % relative)
            inputs, outputs = set(), set()
            for name in files:
                if not name.startswith(root + 'tests/'):
                    continue
                relative = name[len(root):]
                if relative.count('/') != 1:
                    raise PackageValidationError('Tests must be directly inside tests/.')
                if relative.endswith('.in'):
                    inputs.add(relative[:-3])
                elif relative.endswith('.out'):
                    outputs.add(relative[:-4])
            if not inputs or inputs != outputs:
                raise PackageValidationError('Missing input/output pairs: %s' % ', '.join(sorted(inputs ^ outputs)))
            order = sorted(inputs, key=lambda name: tuple(
                (1, int(x)) if x.isdigit() else (0, x) for x in re.split(r'(\d+)', name)))
            statement = text['statement.md']
            title = re.search(r'^#\s+(.+)$', statement, re.M)
            time = re.search(r'Giới hạn thời gian:\*\*\s*([0-9]+(?:\.[0-9]+)?)\s*giây', statement)
            memory = re.search(r'Giới hạn bộ nhớ:\*\*\s*([0-9]+)\s*MB', statement)
            return {
                'root': root, 'name': title.group(1).strip() if title else '',
                'time_limit': float(time.group(1)) if time else None,
                'memory_mb': int(memory.group(1)) if memory else None,
                'statement': statement, 'editorial': text['editorial.md'], 'source': text['solution.cpp'],
                'tests': [(name + '.in', name + '.out') for name in order],
                'sha256': digest.hexdigest(),
            }
    except (zipfile.BadZipFile, UnicodeDecodeError, RuntimeError, NotImplementedError) as exc:
        raise PackageValidationError('Invalid ZIP or UTF-8 content: %s' % exc) from exc
