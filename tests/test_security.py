import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCANNER = ROOT / "scripts" / "check-secrets.sh"
FAKE_VALUE = "router" + "-TEST" + "-q8f3TB62"
MAC_HOME = "/".join(("", "Users", "router-fixture", "Developer", "sample"))
MAC_TEMP = "/".join(("", "var", "folders", "zz", "router_fixture_2026", "T"))


class SecurityChecks(unittest.TestCase):
    def setUp(self):
        workspace = TemporaryDirectory(prefix="router-security-test-")
        self.addCleanup(workspace.cleanup)
        self.repo = Path(workspace.name)
        self.env = {
            name: value for name, value in os.environ.items() if not name.startswith("GIT_")
        }
        self.env["GIT_CONFIG_GLOBAL"] = os.devnull
        self.env["GIT_CONFIG_SYSTEM"] = os.devnull
        self.git("init", "--quiet")
        self.git("config", "user.name", "Router Test")
        self.git("config", "user.email", "router@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("commit", "--allow-empty", "--quiet", "-m", "test baseline")
        self.git("config", "core.hooksPath", ".githooks")

        for relative_path in (
            ".githooks/pre-commit", ".gitleaks.toml", ".gitignore",
            "scripts/check-secrets.sh", "scripts/check-sensitive-paths.py",
        ):
            source = ROOT / relative_path
            destination = self.repo / relative_path
            if source.is_file():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)

    def run_command(self, *command, check=True):
        return subprocess.run(
            command, cwd=self.repo, env=self.env, capture_output=True, text=True, check=check
        )

    def git(self, *arguments, check=True):
        return self.run_command("git", *arguments, check=check)

    def write(self, relative_path, content=""):
        file = self.repo / relative_path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content, encoding="utf-8")

    def scan(self, mode):
        return self.run_command(str(SCANNER), mode, check=False)

    def commit_fixture(self):
        self.git("-c", f"core.hooksPath={os.devnull}", "commit", "--quiet", "-m", "synthetic fixture")

    def assert_content_blocked(self, result, *sensitive_values):
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "Security check blocked potential credentials or local paths.\n")
        for value in sensitive_values:
            self.assertNotIn(value, result.stdout + result.stderr)

    def test_hook_blocks_a_staged_key_even_after_the_worktree_is_cleaned(self):
        self.write("sample.txt", f"DEMO_API_KEY={FAKE_VALUE}\n")
        self.git("add", "sample.txt")
        self.write("sample.txt", "Working tree copy is clean.\n")
        original_head = self.git("rev-parse", "HEAD").stdout

        result = self.git("commit", "--quiet", "-m", "should be blocked", check=False)

        self.assert_content_blocked(result, FAKE_VALUE)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout, original_head)

    def test_hook_accepts_blank_templates_and_dynamic_references_and_ignores_unstaged_content(self):
        templates = [".env.example", "documentation/.env.sample", "documentation/.env.template"]
        for path in templates:
            self.write(path, "DEMO_API_KEY=\n")
        self.write("safe.js", "const apiKey = process.env.ROUTER_API_KEY;\n")
        self.write("safe.py", 'api_key = os.environ.get("ROUTER_API_KEY")\n')
        self.write("portable.md", "Use `~/Developer/sample` or `$HOME/Developer/sample`.\n")
        self.git("add", *templates, "safe.js", "safe.py", "portable.md")
        self.write(".env.example", f"DEMO_API_KEY={FAKE_VALUE}\n")
        self.write("unstaged.txt", MAC_HOME)

        self.git("commit", "--quiet", "-m", "safe fixture")

        self.assertEqual(self.git("show", "HEAD:.env.example").stdout, "DEMO_API_KEY=\n")
        self.assertEqual(self.scan("history").returncode, 0)

    def test_hook_checks_desktop_changes_after_security_and_blocks_on_failure(self):
        runner = self.repo / "bin/pre-commit"
        self.write(
            "bin/pre-commit",
            '#!/bin/sh\nprintf "Desktop checks: %s\\n" "$*"\nexit 7\n',
        )
        runner.chmod(0o755)
        self.env["PATH"] = str(runner.parent) + os.pathsep + self.env["PATH"]

        self.write("readme.md", "Unrelated documentation.\n")
        self.git("add", "readme.md")
        commit = self.git("commit", "--quiet", "-m", "docs fixture")
        self.assertNotIn("Desktop checks:", commit.stdout + commit.stderr)

        desktop = "board/desktop-demo/sample.js"
        self.write(desktop, f"DEMO_API_KEY={FAKE_VALUE}\n")
        self.git("add", desktop)
        original_head = self.git("rev-parse", "HEAD").stdout
        rejected = self.git("commit", "--quiet", "-m", "blocked secret", check=False)
        self.assert_content_blocked(rejected, FAKE_VALUE)

        self.write(desktop, "const demo = true;\n")
        self.git("add", desktop)
        rejected = self.git("commit", "--quiet", "-m", "blocked desktop checks", check=False)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertEqual(
            (rejected.stdout + rejected.stderr).splitlines(),
            [
                "Security check passed (staged).",
                "Desktop checks: run --config board/desktop-demo/.pre-commit-config.yaml",
            ],
        )
        self.assertEqual(self.git("rev-parse", "HEAD").stdout, original_head)

    def test_staged_filenames_are_rejected_even_when_empty_and_forced(self):
        blocked_names = [
            ".env", "sample paths/.env.local", "account/credentials.json",
            "keys/id_ed25519", "keys/certificate.p12", "account/.aws/config",
        ]
        for name in blocked_names:
            self.write(name)
        self.git("add", "--force", "--", *blocked_names)

        result = self.scan("staged")

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "Security check found 6 disallowed Git filename(s).\n")
        self.assertEqual(result.stdout, "")

    def test_staged_content_rules_cover_templates_macos_paths_and_private_key_blocks(self):
        fake_key_body = "synthetic" * 10
        fake_key = "\n".join(("-----" + "BEGIN PRIVATE KEY-----", fake_key_body, "-----" + "END PRIVATE KEY-----"))
        cases = (
            (".env.example", f"DEMO_API_KEY={FAKE_VALUE}\n", FAKE_VALUE),
            ("notes.md", f"This fixture used `{MAC_HOME}`.\n", MAC_HOME),
            ("notes.md", f"This fixture used `{MAC_TEMP}`.\n", MAC_TEMP),
            ("notes.md", f"This fixture used `/private{MAC_TEMP}`.\n", MAC_TEMP),
            ("notes.md", fake_key + "\n", fake_key_body),
        )
        for number, (path, content, sensitive_value) in enumerate(cases, start=1):
            with self.subTest(path=path, case=number):
                self.write(path, content)
                self.git("add", path)
                self.assert_content_blocked(self.scan("staged"), sensitive_value)
                self.git("reset", "--quiet", "HEAD", "--", path)

    def test_history_rejects_a_key_removed_after_an_intermediate_commit(self):
        self.write("settings.txt", f"DEMO_API_KEY={FAKE_VALUE}\n")
        self.git("add", "settings.txt")
        self.commit_fixture()
        self.git("rm", "--quiet", "settings.txt")
        self.commit_fixture()
        self.write(".gitleaks.toml", '[allowlist]\npaths = [".*"]\n')

        self.assert_content_blocked(self.scan("history"), FAKE_VALUE)

    def test_history_rejects_a_key_introduced_in_a_merge_commit(self):
        initial_branch = self.git("branch", "--show-current").stdout.strip()
        self.git("checkout", "--quiet", "-b", "fixture-topic")
        self.write("safe.txt", "Changes from the second parent.\n")
        self.git("add", "safe.txt")
        self.commit_fixture()
        self.git("checkout", "--quiet", initial_branch)
        self.git("merge", "--quiet", "--no-ff", "--no-commit", "fixture-topic")
        self.write("settings.txt", f"DEMO_API_KEY={FAKE_VALUE}\n")
        self.git("add", "settings.txt")
        self.commit_fixture()
        self.git("rm", "--quiet", "settings.txt")
        self.commit_fixture()

        self.assert_content_blocked(self.scan("history"), FAKE_VALUE)

    def test_history_rejects_a_deleted_empty_environment_file(self):
        self.write("archive/.env.local")
        self.git("add", "--force", "archive/.env.local")
        self.commit_fixture()
        self.git("rm", "--quiet", "archive/.env.local")
        self.commit_fixture()

        result = self.scan("history")

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "Security check found 1 disallowed Git filename(s).\n")
        self.assertEqual(result.stdout, "")

    def test_history_rejects_an_untracked_ignore_file_in_the_scan_target(self):
        self.write(".gitleaksignore")

        result = self.scan("history")

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "The scan target contains a disallowed Gitleaks ignore file.\n")

    def test_scan_fails_closed_when_gitleaks_is_missing(self):
        tools = self.repo / "fixture-bin"
        tools.mkdir()
        for command in ("git", "python3"):
            (tools / command).symlink_to(shutil.which(command))
        self.env["PATH"] = str(tools)

        result = self.scan("staged")

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "Security check requires gitleaks.\n")


if __name__ == "__main__":
    unittest.main()
