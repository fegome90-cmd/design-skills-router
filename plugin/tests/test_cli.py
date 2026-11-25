import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


RUNNER = Path(__file__).resolve().parents[1] / "skills/design-tree/scripts/runner.py"


class CliTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.state = Path(directory.name) / "ledger.json"

    def cli(self, *args, cwd=None):
        return subprocess.run(
            [sys.executable, "-B", RUNNER, "--state", self.state, *args],
            capture_output=True, text=True, cwd=cwd, encoding="utf-8",
        )

    def initialize(self):
        result = self.cli("init", "--project-id", "cli-test", "--scope", "inventory")
        self.assertEqual(result.returncode, 0, result.stderr)

    def assert_blocked(self, result, code):
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(json.loads(result.stderr), {"status": "BLOCKED", "error": code})

    def test_explicit_null_inventory_proposal_is_rejected(self):
        self.initialize()
        before = self.state.read_bytes()
        proposal = self.state.with_name("proposal.json")
        proposal.write_text("null",encoding="utf-8")
        self.assert_blocked(self.cli("inventory", "--file", proposal), "INVENTORY_COVERAGE_REQUIRED")
        self.assertEqual(self.state.read_bytes(), before)

    def test_status_requires_a_json_object(self):
        for value in (None, [], "", 0, False):
            with self.subTest(value=value):
                original = json.dumps(value)
                self.state.write_text(original,encoding="utf-8")
                self.assert_blocked(self.cli("status"), "STATE_OBJECT_REQUIRED")
                self.assertEqual(self.state.read_text(encoding="utf-8"), original)

    def test_inventory_lists_catalog_and_records_valid_proposal(self):
        self.initialize()
        before = self.state.read_bytes()
        listing = self.cli("inventory")
        self.assertEqual(listing.returncode, 0, listing.stderr)
        self.assertEqual(self.state.read_bytes(), before)
        evidence = self.state.with_name("scope.txt")
        evidence.write_text("Synthetic review scope.",encoding="utf-8")
        rows = [
            {"skill_id": skill["id"], "disposition": "DEFERRED",
             "reason": "Outside current scope", "evidence_refs": [str(evidence)]}
            for skill in json.loads(listing.stdout)["skills"]
        ]
        proposal = self.state.with_name("proposal.json")
        proposal.write_text(json.dumps(rows),encoding="utf-8")
        result = self.cli("inventory", "--file", proposal)
        self.assertEqual(result.returncode, 0, result.stderr)
        reply = json.loads(result.stdout)
        self.assertEqual(reply["state"], "AWAITING_HUMAN")
        ledger = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(ledger["revision"], 1)
        self.assertEqual(ledger["inventory_proposal"]["hash"], reply["inventory_hash"])
        self.assertEqual(ledger["inventory_proposal"]["rows"], rows)

    def test_inventory_help_explains_both_modes_and_file_format(self):
        result = self.cli("inventory", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        help_text = " ".join(result.stdout.lower().split())
        for term in ("catalog", "proposal", "json array", "skill_id", "evidence_refs"):
            self.assertIn(term, help_text)

    def test_relative_fact_evidence_exports_from_another_directory(self):
        self.initialize()
        origin = self.state.parent / "origin"
        origin.mkdir()
        note = origin / "note.txt"
        note.write_text("Original evidence",encoding="utf-8")
        evidence_hash = hashlib.sha256(note.read_bytes()).hexdigest()
        fact = {"state": "PRESENT", "value": "known", "scope": "project",
                "subject": "screen", "revision": 1, "applies_to": ["Q00"],
                "evidence": [{"path": "note.txt", "sha256": evidence_hash, "note": "scope"}]}
        (origin / "fact.json").write_text(json.dumps(fact),encoding="utf-8")
        registered = self.cli("fact", "scope", "--file", "fact.json", cwd=origin)
        self.assertEqual(registered.returncode, 0, registered.stderr)
        (self.state.parent / "note.txt").write_text("Different evidence",encoding="utf-8")
        bundle = self.state.parent / "bundle"
        exported = self.cli("export", "--output", bundle, cwd=self.state.parent)
        self.assertEqual(exported.returncode, 0, exported.stderr)
        self.assertEqual((bundle / "evidence" / evidence_hash).read_bytes(), note.read_bytes())

    def test_non_object_bundle_ledger_is_a_structured_error(self):
        bundle = self.state.parent / "bundle"
        bundle.mkdir()
        ledger = bundle / "ledger.json"
        for value in (None, [], "text", 0, False):
            ledger.write_text(json.dumps(value),encoding="utf-8")
            for args in (("resume",), ("upgrade-state", "--dry-run")):
                with self.subTest(value=value, command=args[0]):
                    self.assert_blocked(self.cli(*args, "--bundle", bundle), "STATE_OBJECT_REQUIRED")
                    self.assertFalse(self.state.exists())
                    self.assertEqual(json.loads(ledger.read_text(encoding="utf-8")), value)

    def test_root_help_describes_each_command(self):
        help_result = self.cli("--help")
        self.assertEqual(help_result.returncode, 0)
        commands = re.search(r"\{([\w,-]+)\}", help_result.stdout).group(1).split(",")
        for command in commands:
            with self.subTest(command=command):
                self.assertRegex(help_result.stdout, rf"(?m)^    {re.escape(command)}\s+\S")

    def test_configure_explains_required_fields_and_preserves_state(self):
        self.initialize()
        before = self.state.read_bytes()
        help_result = self.cli("configure", "--help")
        self.assertIn("phase_map", help_result.stdout)
        self.assertIn("receipt", help_result.stdout)
        payload = self.state.with_name("configure.json")
        for value in ({}, {"phase_map": {}}, {"receipt": {}}, []):
            payload.write_text(json.dumps(value),encoding="utf-8")
            result = self.cli("configure", "--file", payload)
            self.assert_blocked(result, "CONFIGURE_OBJECT_REQUIRED: expected phase_map and receipt")
            self.assertEqual(self.state.read_bytes(), before)
