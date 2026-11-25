"""A release candidate must remain testable AFTER bumping its version and packaging."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]

class ReleaseRoundtripTests(unittest.TestCase):
    def test_prepared_artifact_tests_and_hashes(self):
        spec = importlib.util.spec_from_file_location('release_prep', ROOT/'scripts/release.py')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            manifest = json.loads((ROOT/'plugin.json').read_text(encoding='utf-8'))
            nums = tuple(int(n) for n in manifest['version'].split('.'))
            next_version = f'{nums[0]}.{nums[1]}.{nums[2]+1}'
            old_hashes = json.loads((ROOT/'PACKAGE-HASHES.json').read_text(encoding='utf-8'))
            retained = {name:{'sha256':h} for name,h in old_hashes.items()
                        if name.startswith('assets/') and not (ROOT/name).is_file()}
            archive = td/'candidate.zip'
            result = mod.prepare_release(ROOT, next_version, archive, retained)
            self.assertEqual(result['version'],next_version)
            with zipfile.ZipFile(archive) as z:
                self.assertIsNone(z.testzip())
                z.extractall(td/'unpacked')
                names = {n.split('/',1)[1]:n for n in z.namelist() if '/' in n}
                lock = json.loads(z.read(names['PACKAGE-HASHES.json']))
                for name,h in lock.items():
                    if name in retained:
                        self.assertEqual(h,old_hashes[name]); self.assertNotIn(name,names)
                    else:
                        self.assertEqual(hashlib.sha256(z.read(names[name])).hexdigest(),h,name)
            package = td/'unpacked'/'design-skills-router'
            self.assertEqual(json.loads((package/'plugin.json').read_text(encoding='utf-8'))['version'],next_version)
            proc = subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests',
                                   '-p','test_release.py','-q'],cwd=package,
                                  env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},
                                  text=True,capture_output=True,timeout=120, encoding='utf-8')
            self.assertEqual(proc.returncode,0,proc.stdout+'\n'+proc.stderr)
            self.assertIn('OK',proc.stderr)
