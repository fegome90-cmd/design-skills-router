"""Read-only diagnostics must survive broken packages and preserve entry sets."""
import unittest, tempfile, shutil, json, hashlib, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class DoctorTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.p=Path(self.t.name)/'package'
  shutil.copytree(ROOT,self.p,ignore=shutil.ignore_patterns('.git','__pycache__'))
 def run_doctor(self,*args):
  p=ROOT/'skills/design-tree/scripts/doctor.py'
  self.assertTrue(p.exists(),'Doctor implementation missing')
  r=subprocess.run([sys.executable,'-B',str(p),'--package-root',str(self.p),'--format','json',*map(str,args)],capture_output=True,text=True,cwd='/tmp',encoding='utf-8')
  self.assertIn(r.returncode,(0,1,2));return json.loads(r.stdout)
 def snapshot(self):
  return {str(p.relative_to(self.p)):('dir' if p.is_dir() else hashlib.sha256(p.read_bytes()).hexdigest()) for p in self.p.rglob('*')}
 def test_broken_tree_reports_without_router_startup(self):
  (self.p/'skills/design-tree/references/tree-v0.4/tree.json').write_text('{',encoding='utf-8')
  r=self.run_doctor();self.assertIn('INVALID_JSON',{x['code'] for x in r['findings']})
 def test_runner_hash_drift_is_reported(self):
  with (self.p/'skills/design-tree/scripts/runner.py').open('a',encoding='utf-8') as f:f.write('\n# accidental drift\n')
  r=self.run_doctor();self.assertTrue(any(x['code']=='HASH_MISMATCH' and 'runner.py' in x['location'] for x in r['findings']))
 def test_doctor_preserves_all_input_bytes_and_paths(self):
  a=self.snapshot();self.run_doctor();self.assertEqual(a,self.snapshot())
 def test_locked_state_is_reported_not_unlocked(self):
  state=Path(self.t.name)/'ledger.json';state.write_text('{}',encoding='utf-8');lock=state.with_suffix('.json.lock');lock.write_text('other writer',encoding='utf-8')
  r=self.run_doctor('--state',state);self.assertTrue(lock.exists());self.assertIn('STATE_LOCK_PRESENT',{x['code'] for x in r['findings']})
 def test_unsafe_manifest_path_is_rejected(self):
  f=self.p/'plugin.json';j=json.loads(f.read_text(encoding='utf-8'));j['extensions']['com.openai']['interface']['logo']='../private';f.write_text(json.dumps(j),encoding='utf-8')
  r=self.run_doctor();self.assertIn('PATH_ESCAPE',{x['code'] for x in r['findings']})
 def test_symlink_is_reported_without_following(self):
  (self.p/'secret').symlink_to('/etc/passwd');r=self.run_doctor();self.assertIn('SYMLINK_FORBIDDEN',{x['code'] for x in r['findings']})
 def test_root_overlay_effective_configuration(self):
  f=self.p/'.codex-plugin/plugin.json';j=json.loads(f.read_text(encoding='utf-8'));j['interface']['defaultPrompt']='different';f.write_text(json.dumps(j),encoding='utf-8')
  r=self.run_doctor();self.assertIn('MANIFEST_DIVERGENCE',{x['code'] for x in r['findings']})
