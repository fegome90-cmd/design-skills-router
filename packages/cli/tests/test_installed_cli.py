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

    @unittest.skipUnless(os.name == 'posix', 'pseudo-terminal requires POSIX')
    def test_tty_help_respects_no_color(self):
        import errno
        import pty

        exe = Path(sys.executable).with_name('design-skills-router')
        master, slave = pty.openpty()
        env = {**os.environ, 'TERM': 'xterm-256color', 'NO_COLOR': '1', 'COLUMNS': '48'}
        env.pop('FORCE_COLOR', None)
        with subprocess.Popen([str(exe), 'status', '--help'], stdout=slave, stderr=slave, env=env) as proc:
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
        exe = Path(sys.executable).with_name('design-skills-router')
        with tempfile.TemporaryDirectory() as temp:
            ledger = Path(temp) / 'ledger.json'
            env = {**os.environ, 'NO_COLOR': '1'}
            initialized = subprocess.run(
                [str(exe), '--state', str(ledger), 'init', '--project-id', 'diseño', '--scope', 'test'],
                cwd=temp, env={**env, 'PYTHONIOENCODING': 'utf-8'}, capture_output=True,
            )
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            self.assertEqual(initialized.stderr, b'')

            ascii_pretty = subprocess.run(
                [str(exe), '--state', str(ledger), 'status', '--pretty'],
                cwd=temp, env={**env, 'PYTHONIOENCODING': 'ascii'}, capture_output=True,
            )
            self.assertEqual(ascii_pretty.returncode, 0, ascii_pretty.stderr)
            self.assertIn(b'dise\\xf1o', ascii_pretty.stdout)
            self.assertEqual(ascii_pretty.stderr, b'')

            utf8_pretty = subprocess.run(
                [str(exe), '--state', str(ledger), 'status', '--pretty'],
                cwd=temp, env={**env, 'PYTHONIOENCODING': 'utf-8'}, capture_output=True,
            )
            self.assertEqual(utf8_pretty.returncode, 0, utf8_pretty.stderr)
            self.assertIn('diseño'.encode('utf-8'), utf8_pretty.stdout)
            self.assertEqual(utf8_pretty.stderr, b'')

    def test_installed_entrypoint_runs_outside_checkout_with_redirected_stdout(self):
        exe = Path(sys.executable).parent / ('design-skills-router.exe' if os.name == 'nt' else 'design-skills-router')
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryFile() as output:
            result = subprocess.run([str(exe), 'verify-package'], cwd=temp, stdout=output, stderr=subprocess.PIPE)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, b'')
            output.seek(0)
            payload = output.read()
            self.assertNotIn(b'\x1b', payload)
            self.assertTrue(json.loads(payload)['baseline_verified'])
