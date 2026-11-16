import io
import unittest
import zipfile

from judge.utils.problem_package import PackageValidationError, inspect_package


def make_package(extra=None, root='package/'):
    files = {
        'statement.md': '# Các số phân biệt\n**Giới hạn thời gian:** 1 giây\n**Giới hạn bộ nhớ:** 512 MB',
        'editorial.md': '# Lời giải',
        'solution.cpp': 'int main() {}',
        'tests/2.in': '1\n', 'tests/2.out': '1\n',
        'tests/10.in': '2\n', 'tests/10.out': '2\n',
    }
    files.update(extra or {})
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        for name, content in files.items():
            if content is not None:
                archive.writestr(root + name, content)
    stream.seek(0)
    return stream


class PackageParserTest(unittest.TestCase):
    def test_metadata_and_natural_order(self):
        result = inspect_package(make_package())
        self.assertEqual(result['name'], 'Các số phân biệt')
        self.assertEqual(result['memory_mb'], 512)
        self.assertEqual(result['time_limit'], 1)
        self.assertEqual(result['tests'], [('tests/2.in', 'tests/2.out'), ('tests/10.in', 'tests/10.out')])

    def test_root_package(self):
        self.assertEqual(inspect_package(make_package(root=''))['root'], '')

    def test_missing_output(self):
        with self.assertRaises(PackageValidationError):
            inspect_package(make_package({'tests/2.out': None}))

    def test_unsafe_path(self):
        with self.assertRaises(PackageValidationError):
            inspect_package(make_package({'../outside': 'bad'}))

    def test_invalid_utf8(self):
        with self.assertRaises(PackageValidationError):
            inspect_package(make_package({'statement.md': b'\xff'}))

    def test_limit(self):
        with self.assertRaises(PackageValidationError):
            inspect_package(make_package(), upload_limit=10)
