import importlib.util
import io
import stat
import zipfile
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from judge.tests.authoring_helpers import make_zip


class AuthoringPackageTest(SimpleTestCase):
    def parser(self):
        self.assertIsNotNone(importlib.util.find_spec('judge.problem_authoring.packages'),
                             'Bounded authoring package parser is missing')
        from judge.problem_authoring import packages
        return packages

    def test_natural_order(self):
        parsed = self.parser().inspect_tests(make_zip({
            '10.in': '10', '10.out': '10', '2.in': '2', '2.out': '2', '1.in': '1', '1.out': '1',
        }))
        self.assertEqual([case.input_file for case in parsed.tests], ['1.in', '2.in', '10.in'])
        self.assertEqual([case.order for case in parsed.tests], [1, 2, 3])
        self.assertEqual(parsed.kind, 'TESTS')

    def test_test_roots(self):
        for root in ('', 'tests/', 'wrapper/', 'wrapper/tests/'):
            with self.subTest(root=root):
                parsed = self.parser().inspect_tests(make_zip({root + '1.in': '1', root + '1.out': '1'}))
                self.assertEqual(len(parsed.tests), 1)
                self.assertEqual(parsed.tests[0].input_file, '1.in')
                self.assertEqual(parsed.fields['root'], root)

    def test_mixed_roots_are_rejected(self):
        from judge.problem_authoring.types import AuthoringError
        with self.assertRaises(AuthoringError):
            self.parser().inspect_tests(make_zip({'1.in': '', 'tests/1.out': ''}))

    def test_missing_pair_names_error(self):
        from judge.problem_authoring.types import AuthoringError
        with self.assertRaisesRegex(AuthoringError, '2'):
            self.parser().inspect_tests(make_zip({'1.in': '', '1.out': '', '2.in': ''}))

    def test_full_package_allows_statement_only(self):
        parsed = self.parser().inspect_full_package(make_zip({'statement.md': '# Draft'}))
        self.assertEqual(parsed.fields['description'], '# Draft')
        self.assertEqual(parsed.fields['name'], 'Draft')
        self.assertNotIn('editorial', parsed.fields)
        self.assertEqual(parsed.tests, [])
        self.assertIsNone(parsed.source_name)

    def test_old_complete_package_still_parses(self):
        parsed = self.parser().inspect_full_package(make_zip({
            'pkg/statement.md': '# Title\n**Giới hạn thời gian:** 1.5 giây\n**Giới hạn bộ nhớ:** 256 MB',
            'pkg/editorial.md': '# Solution', 'pkg/solution.cpp': 'int main() {}',
            'pkg/tests/1.in': '1', 'pkg/tests/1.out': '2',
        }))
        self.assertEqual(parsed.fields['memory_limit'], 262144)
        self.assertEqual(parsed.fields['time_limit'], 1.5)
        self.assertEqual(parsed.fields['root'], 'pkg/')
        self.assertEqual(parsed.source_name, 'pkg/solution.cpp')
        self.assertEqual(parsed.tests[0].input_file, 'tests/1.in')

    def test_unknown_files_are_not_ignored(self):
        from judge.problem_authoring.types import AuthoringError
        for full, files in ((False, {'1.in': '', '1.out': '', 'init.yml': 'bad'}),
                            (True, {'statement.md': '# Title', 'image.png': 'unhandled'})):
            with self.subTest(full=full), self.assertRaises(AuthoringError):
                parser = self.parser()
                (parser.inspect_full_package if full else parser.inspect_tests)(make_zip(files))

    def test_md_limits_are_suggestions(self):
        parsed = self.parser().inspect_full_package(make_zip({'statement.md': '# Title\nNo limits here.'}))
        self.assertNotIn('time_limit', parsed.fields)
        self.assertNotIn('memory_limit', parsed.fields)

    def test_unsafe_archive_entries_are_rejected(self):
        from judge.problem_authoring.types import AuthoringError
        parser = self.parser()
        for name in ('../1.in', '/1.in', 'C:/1.in', 'tests\\1.in', 'tests/./1.in'):
            with self.subTest(name=name), self.assertRaises(AuthoringError):
                parser.inspect_tests(make_zip({name: '', '1.out': ''}))
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            info = zipfile.ZipInfo('1.in')
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, '../private')
            archive.writestr('1.out', '')
        with self.assertRaises(AuthoringError):
            parser.inspect_tests(stream)

    def test_bad_zip_and_invalid_utf8_are_validation_errors(self):
        from judge.problem_authoring.types import AuthoringError
        parser = self.parser()
        for stream in (io.BytesIO(b'not a zip'), make_zip({'statement.md': b'\xff'}),
                       make_zip({'statement.md': '   '})):
            with self.assertRaises(AuthoringError):
                parser.inspect_full_package(stream)

    def test_duplicate_entries_are_rejected(self):
        from judge.problem_authoring.types import AuthoringError
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            archive.writestr('1.in', 'one')
            with self.assertWarns(UserWarning):
                archive.writestr('1.in', 'two')
            archive.writestr('1.out', 'one')
        with self.assertRaises(AuthoringError):
            self.parser().inspect_tests(stream)

    def test_streamed_and_compressed_limits_are_enforced(self):
        from judge.problem_authoring.types import AuthoringError
        parser = self.parser()
        cases = ({'PROBLEM_AUTHORING_UPLOAD_LIMIT': 10},
                 {'PROBLEM_AUTHORING_EXPANDED_LIMIT': 8},
                 {'PROBLEM_AUTHORING_TEST_FILE_LIMIT': 4},
                 {'PROBLEM_AUTHORING_ENTRY_LIMIT': 1})
        for settings in cases:
            with self.subTest(settings=settings), override_settings(**settings), self.assertRaises(AuthoringError):
                parser.inspect_tests(make_zip({'1.in': '12345', '1.out': '12345'}))
        with override_settings(PROBLEM_AUTHORING_TEXT_LIMIT=4), self.assertRaises(AuthoringError):
            parser.inspect_full_package(make_zip({'statement.md': '# Title'}))

    def test_mass_testcases_not_formset_limited(self):
        files = {}
        for index in range(1002):
            files[str(index) + '.in'] = ''
            files[str(index) + '.out'] = ''
        self.assertEqual(len(self.parser().inspect_tests(make_zip(files)).tests), 1002)

    def test_case_names_fit_persistent_testcase_fields(self):
        from judge.problem_authoring.types import AuthoringError
        name = 'a' * 100
        with self.assertRaises(AuthoringError):
            self.parser().inspect_tests(make_zip({name + '.in': '', name + '.out': ''}))

    def test_encrypted_flag_is_rejected(self):
        from judge.problem_authoring.types import AuthoringError
        parser = self.parser()
        original = zipfile.ZipFile.infolist

        def encrypted(archive):
            entries = original(archive)
            entries[0].flag_bits |= 1
            return entries

        with patch.object(zipfile.ZipFile, 'infolist', encrypted), self.assertRaises(AuthoringError):
            parser.inspect_tests(make_zip({'1.in': '', '1.out': ''}))
