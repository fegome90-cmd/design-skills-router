"""Behaviour of scripts/check-encoding.py on positive, negative and non-applicable cases."""

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / 'scripts' / 'check-encoding.py'
spec = importlib.util.spec_from_file_location('check_encoding', SCRIPT)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class CheckEncodingTests(unittest.TestCase):
    def findings(self, source):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'sample.py'
            path.write_text(textwrap.dedent(source), encoding='utf-8')
            return [(line, message.split(':')[0]) for _, line, _, message
                    in guard.check_file(path, 'sample.py')]

    def assertReports(self, source, expected):
        self.assertEqual(self.findings(source), expected)

    def test_reports_text_io_without_encoding(self):
        self.assertReports('''\
            import io, os, subprocess, tempfile, fileinput
            from pathlib import Path
            open('a')
            open('a', 'w')
            io.open('a', 'r')
            os.fdopen(3, 'w')
            Path('a').open()
            Path('a').read_text()
            Path('a').write_text('x')
            (Path('a') / 'b').read_text()
            tempfile.NamedTemporaryFile('w')
            tempfile.TemporaryFile(mode='w+')
            tempfile.SpooledTemporaryFile(10, 'w+')
            fileinput.input(['a'])
            subprocess.run(['x'], text=True)
            subprocess.check_output(['x'], universal_newlines=True)
            ''', [(3, 'open'), (4, 'open'), (5, 'io.open'), (6, 'os.fdopen'),
                  (7, 'Path.open'), (8, 'Path.read_text'), (9, 'Path.write_text'),
                  (10, 'Path.read_text'), (11, 'tempfile.NamedTemporaryFile'),
                  (12, 'tempfile.TemporaryFile'), (13, 'tempfile.SpooledTemporaryFile'),
                  (14, 'fileinput.input'), (15, 'subprocess.run'),
                  (16, 'subprocess.check_output')])

    def test_reports_explicit_encoding_none(self):
        self.assertReports('''\
            from pathlib import Path
            open('a', encoding=None)
            Path('a').read_text(None)
            Path('a').write_text('x', None)
            ''', [(2, 'open'), (3, 'Path.read_text'), (4, 'Path.write_text')])

    def test_accepts_explicit_encoding_by_keyword_and_position(self):
        self.assertReports('''\
            import subprocess, tempfile
            from pathlib import Path
            open('a', encoding='utf-8')
            open('a', 'w', -1, 'utf-8')
            Path('a').open('w', -1, 'utf-8')
            Path('a').read_text('utf-8')
            Path('a').write_text('x', 'utf-8')
            Path('a').write_text('x', encoding='utf-8', newline='')
            tempfile.NamedTemporaryFile('w', -1, 'utf-8')
            tempfile.SpooledTemporaryFile(10, 'w+', -1, 'utf-8')
            subprocess.run(['x'], text=True, encoding='utf-8')
            ''', [])

    def test_ignores_binary_modes_and_bytes_apis(self):
        self.assertReports('''\
            import io, subprocess, tempfile
            from pathlib import Path
            open('a', 'rb')
            io.open('a', 'rb', opener=None)
            Path('a').open(mode='xb')
            Path('a').read_bytes()
            Path('a').write_bytes(b'x')
            tempfile.TemporaryFile()
            tempfile.NamedTemporaryFile(delete=False)
            tempfile.SpooledTemporaryFile(10)
            subprocess.run(['x'], capture_output=True)
            subprocess.run(['x'], text=False)
            ''', [])

    def test_ignores_tempfile_helpers_that_open_no_text_stream(self):
        self.assertReports('''\
            import tempfile
            from tempfile import TemporaryDirectory, mkdtemp
            tempfile.mkstemp()
            tempfile.mkdtemp()
            tempfile.gettempdir()
            TemporaryDirectory()
            mkdtemp()
            ''', [])

    def test_treats_non_literal_mode_and_text_flag_as_text(self):
        self.assertReports('''\
            import subprocess
            mode = 'r'
            open('a', mode)
            subprocess.run(['x'], text=flag)
            ''', [(3, 'open'), (4, 'subprocess.run')])

    def test_resolves_import_aliases(self):
        self.assertReports('''\
            import subprocess as sp
            import tempfile as tf
            import os.path
            from subprocess import Popen as P
            from io import open as io_open
            sp.run(['x'], text=True)
            tf.TemporaryFile('w')
            P(['x'], text=True)
            io_open('a')
            os.fdopen(3, 'r')
            ''', [(6, 'subprocess.run'), (7, 'tempfile.TemporaryFile'),
                  (8, 'subprocess.Popen'), (9, 'io.open'), (10, 'os.fdopen')])

    def test_ignores_open_of_unrelated_modules_and_fileinput_hooks(self):
        self.assertReports('''\
            import fileinput, gzip, os, webbrowser, zipfile
            from webbrowser import open as browse
            webbrowser.open('https://example.org')
            browse('https://example.org')
            gzip.open('a.gz')
            os.open('a', os.O_RDONLY)
            zipfile.ZipFile('a.zip').open('x')
            fileinput.input(['a'], openhook=fileinput.hook_encoded('utf-8'))
            fileinput.input(['a'], mode='rb')
            ''', [(7, 'Path.open')])

    def test_reports_review_findings_outside_the_original_list(self):
        self.assertReports('''\
            import builtins, codecs, fileinput, io, subprocess
            builtins.open('a')
            codecs.open('a')
            io.TextIOWrapper(buffer)
            subprocess.run(['x'], capture_output=True, errors='replace')
            fileinput.input(['a'], openhook=None)
            ''', [(2, 'open'), (3, 'codecs.open'), (4, 'io.TextIOWrapper'),
                  (5, 'subprocess.run'), (6, 'fileinput.input')])
        self.assertReports('''\
            import codecs, io, subprocess
            codecs.open('a', 'r', 'utf-8')
            codecs.open('a', 'rb')
            io.TextIOWrapper(buffer, 'utf-8')
            subprocess.run(['x'], errors=None)
            ''', [])

    def test_resolves_an_import_written_after_its_use(self):
        self.assertReports('''\
            def write():
                return NamedTemporaryFile('w')
            from tempfile import NamedTemporaryFile
            ''', [(2, 'tempfile.NamedTemporaryFile')])

    def test_ignore_marker_requires_a_reason(self):
        self.assertReports('''\
            import zipfile
            archive = zipfile.ZipFile('a.zip')
            archive.open('x')  # check-encoding: ignore[ZipFile.open reads bytes]
            archive.open('y')  # check-encoding: ignore[]
            archive.open('z')  # check-encoding: ignore
            note = "# check-encoding: ignore[inside a string]"; open('s')
            open('a'); open('b')  # check-encoding: ignore[covers one call only]
            ''', [(4, 'Path.open'), (5, 'Path.open'), (6, 'open'), (7, 'open'), (7, 'open')])

    def test_function_level_import_does_not_hide_module_calls(self):
        self.assertReports('''\
            open('a')
            def compress():
                from gzip import open
                return open('b.gz')
            open('c')
            ''', [(1, 'open'), (5, 'open')])

    def test_summary_lists_calls_ignored_by_marker(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'marked.py'
            path.write_text("open('a')  # check-encoding: ignore[fixture]\n", encoding='utf-8')
            result = subprocess.run([sys.executable, '-B', str(SCRIPT), '--summary', str(path)],
                                    capture_output=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0)
            self.assertIn('1 calls ignored by marker', result.stderr)
            self.assertIn('ignored: ' + path.as_posix() + ':1:1: open', result.stderr)

    def test_command_line_exit_codes_and_exclusions(self):
        with tempfile.TemporaryDirectory() as temp:
            bad = Path(temp) / 'bad.py'
            bad.write_text("open('a')\n", encoding='utf-8')
            good = Path(temp) / 'good.py'
            good.write_text("open('a', encoding='utf-8')\n", encoding='utf-8')
            broken = Path(temp) / 'broken.py'
            broken.write_text('def (:\n', encoding='utf-8')
            run = lambda *a: subprocess.run([sys.executable, '-B', str(SCRIPT), *a],
                                            capture_output=True, encoding='utf-8')
            self.assertEqual(run(str(good)).returncode, 0)
            result = run(str(bad))
            self.assertEqual(result.returncode, 1)
            self.assertIn('bad.py:1:1: open: text I/O without an explicit encoding', result.stdout)
            self.assertIn('1 calls, 1 lines, 1 files', result.stderr)
            self.assertEqual(run(str(broken)).returncode, 2)
            listed = run('--list-excluded')
            self.assertEqual(listed.returncode, 0)
            self.assertEqual({line.split('\t')[0] for line in listed.stdout.splitlines()},
                             set(guard.EXCLUDED))
        for prefix, reason in guard.EXCLUDED.items():
            self.assertTrue(reason.strip(), prefix)
            self.assertTrue(guard.excluded(prefix + 'x.py'))
        self.assertFalse(guard.excluded('plugin/x.py'))


if __name__ == '__main__':
    unittest.main()
