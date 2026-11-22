from contextlib import redirect_stderr, redirect_stdout
from importlib.metadata import distribution
from io import StringIO
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

from typer.testing import CliRunner

from design_skills_router.cli import app


CLI = Path(sys.executable).with_name('design-skills-router.exe' if os.name == 'nt' else 'design-skills-router')


class InstalledCliTests(unittest.TestCase):
    def setUp(self):
        self.cli = CliRunner()

    def test_help_describes_each_command_without_loading_state(self):
        result = self.cli.invoke(app, ['init', '--help'], env={'NO_COLOR': '1', 'COLUMNS': '48'})
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn('Create a new ledger', result.stdout)
        self.assertIn('--project-id', result.stdout)
        self.assertEqual(result.stderr, '')
        self.assertNotIn('\x1b', result.stdout)

    def test_help_names_the_fields_required_in_json_inputs(self):
        fields = {
            'configure': ('phase_map', 'receipt'),
            'inventory': ('skill_id', 'disposition', 'reason', 'evidence_refs'),
        }
        for command, names in fields.items():
            with self.subTest(command=command):
                result = self.cli.invoke(app, [command, '--help'], env={'NO_COLOR': '1', 'COLUMNS': '100'})
                self.assertEqual(result.exit_code, 0, result.output)
                for name in names:
                    self.assertIn(name, result.stdout)

    def test_distribution_includes_the_project_license(self):
        package = distribution('design-skills-router')
        self.assertEqual(package.metadata.get('License-Expression'), 'MIT')
        self.assertIn('LICENSE', package.metadata.get_all('License-File') or [])
        license_text = package.read_text('licenses/LICENSE')
        self.assertIsNotNone(license_text)
        self.assertIn('Felipe González', license_text)
        self.assertIn('Permission is hereby granted', license_text)

    def test_validation_failures_go_to_stderr(self):
        for args in (['unknown'], ['init'], ['init', '--project-id', 'test', '--scope', 'test', '--mode', 'bad']):
            with self.subTest(args=args):
                result = self.cli.invoke(app, args)
                self.assertEqual(result.exit_code, 2, result.output)
                self.assertEqual(result.stdout, '')
                self.assertIn('Error', result.stderr)

    def test_package_probe_and_gate_have_separate_json_streams(self):
        result = self.cli.invoke(app, ['verify-package'], color=True, env={'FORCE_COLOR': '1'})
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(result.stderr, '')
        self.assertTrue(json.loads(result.stdout)['baseline_verified'])
        self.assertNotIn('\x1b', result.stdout)
        result = self.cli.invoke(app, ['status'])
        self.assertEqual(result.exit_code, 2, result.output)
        self.assertEqual(result.stdout, '')
        self.assertEqual(json.loads(result.stderr), {'status': 'BLOCKED', 'error': 'STATE_PATH_REQUIRED'})

    def test_json_can_be_captured_by_text_only_streams(self):
        with self.subTest(command='verify-package'):
            with redirect_stdout(StringIO()) as out, redirect_stderr(StringIO()) as err:
                app(args=['verify-package'], standalone_mode=False)
            self.assertTrue(json.loads(out.getvalue())['baseline_verified'])
            self.assertEqual(err.getvalue(), '')

        with self.subTest(command='status'):
            with redirect_stdout(StringIO()) as out, redirect_stderr(StringIO()) as err:
                code = app(args=['status'], standalone_mode=False)
            self.assertEqual(code, 2)
            self.assertEqual(out.getvalue(), '')
            self.assertEqual(json.loads(err.getvalue()), {'status': 'BLOCKED', 'error': 'STATE_PATH_REQUIRED'})

    def test_status_is_read_only_and_pretty_renders_literal_project(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger = Path(temp) / 'with spaces.json'
            state = ['--state', str(ledger)]
            # A value starting with '--' must be forwarded as a value, not parsed again as a flag.
            result = self.cli.invoke(app, [*state, 'init', '--project-id=[red]demo[/red]', '--scope=--help'])
            self.assertEqual(result.exit_code, 0, result.output)
            before = ledger.read_bytes()
            status = self.cli.invoke(app, [*state, 'status'])
            self.assertEqual(status.exit_code, 0, status.output)
            self.assertEqual(json.loads(status.stdout)['project_id'], '[red]demo[/red]')
            pretty = self.cli.invoke(
                app, [*state, 'status', '--pretty'], env={'NO_COLOR': '1', 'COLUMNS': '36'}
            )
            self.assertEqual(pretty.exit_code, 0, pretty.output)
            self.assertIn('[red]demo[/red]', pretty.stdout)
            self.assertNotIn('\x1b', pretty.stdout)
            self.assertLessEqual(max(map(len, pretty.stdout.splitlines())), 36)
            self.assertEqual(pretty.stderr, '')
            self.assertEqual(ledger.read_bytes(), before)

    def test_json_streams_preserve_unicode_with_redirected_cp1252_output(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger = Path(temp) / 'ledger.json'

            def run(*args):
                return subprocess.run(
                    [CLI, '--state', ledger, *args], cwd=temp, capture_output=True,
                    env={**os.environ, 'PYTHONIOENCODING': 'cp1252:strict'},
                )

            with self.subTest(command='init'):
                result = run('init', '--project-id', '東京', '--scope', 'test')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, b'')
                self.assertEqual(json.loads(result.stdout.decode('utf-8'))['project_id'], '東京')
                self.assertEqual(json.loads(ledger.read_bytes())['project_id'], '東京')

            with self.subTest(command='node'):
                result = run('node', 'Q00')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, b'')
                self.assertEqual(json.loads(result.stdout.decode('utf-8'))['node_id'], 'Q00')

            with self.subTest(command='configure'):
                missing = 'diseño-東京.json'
                result = run('configure', '--file', missing)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(result.stdout, b'')
                error = json.loads(result.stderr.decode('utf-8'))
                self.assertEqual(error['status'], 'BLOCKED')
                self.assertIn(missing, error['error'])

    @unittest.skipUnless(os.name == 'posix', 'pseudo-terminal requires POSIX')
    def test_tty_help_respects_no_color(self):
        import errno
        import pty

        master, slave = pty.openpty()
        env = {**os.environ, 'TERM': 'xterm-256color', 'NO_COLOR': '1', 'COLUMNS': '48'}
        env.pop('FORCE_COLOR', None)
        with subprocess.Popen([CLI, 'status', '--help'], stdout=slave, stderr=slave, env=env) as proc:
            os.close(slave)
            chunks = []
            try:
                while True:
                    chunk = os.read(master, 4096)
                    if not chunk:
                        break
                    chunks.append(chunk)
            except OSError as error:
                if error.errno != errno.EIO:
                    raise
            finally:
                os.close(master)
            self.assertEqual(proc.wait(timeout=5), 0)
        output = b''.join(chunks)
        self.assertIn(b'--pretty', output)
        self.assertIsNone(re.search(rb'\x1b\[(?:[0-9;]*;)?(?:3[0-9]|9[0-7])m', output))

    def test_pretty_status_escapes_values_unrepresentable_in_console_encoding(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger = Path(temp) / 'ledger.json'
            env = {**os.environ, 'NO_COLOR': '1'}
            initialized = subprocess.run(
                [CLI, '--state', str(ledger), 'init', '--project-id', 'diseño', '--scope', 'test'],
                cwd=temp, env={**env, 'PYTHONIOENCODING': 'utf-8'}, capture_output=True,
            )
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            self.assertEqual(initialized.stderr, b'')

            ascii_pretty = subprocess.run(
                [CLI, '--state', str(ledger), 'status', '--pretty'],
                cwd=temp, env={**env, 'PYTHONIOENCODING': 'ascii'}, capture_output=True,
            )
            self.assertEqual(ascii_pretty.returncode, 0, ascii_pretty.stderr)
            self.assertIn(b'dise\\xf1o', ascii_pretty.stdout)
            self.assertEqual(ascii_pretty.stderr, b'')

            utf8_pretty = subprocess.run(
                [CLI, '--state', str(ledger), 'status', '--pretty'],
                cwd=temp, env={**env, 'PYTHONIOENCODING': 'utf-8'}, capture_output=True,
            )
            self.assertEqual(utf8_pretty.returncode, 0, utf8_pretty.stderr)
            self.assertIn('diseño'.encode('utf-8'), utf8_pretty.stdout)
            self.assertEqual(utf8_pretty.stderr, b'')

    def test_installed_entrypoint_runs_outside_checkout_with_redirected_stdout(self):
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryFile() as output:
            result = subprocess.run([CLI, 'verify-package'], cwd=temp, stdout=output, stderr=subprocess.PIPE)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, b'')
            output.seek(0)
            payload = output.read()
            self.assertNotIn(b'\x1b', payload)
            self.assertTrue(json.loads(payload)['baseline_verified'])
