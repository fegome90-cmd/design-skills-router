"""Packaging is explicit; missing original binary assets require a declared overlay."""
import unittest,tempfile,shutil,json,hashlib,importlib.util,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ReleaseTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name)
  self.root=self.base/'source';shutil.copytree(ROOT,self.root,ignore=shutil.ignore_patterns('.git','__pycache__'))
  self.script=ROOT/'scripts/release.py'
 def mod(self):
  self.assertTrue(self.script.is_file(),'release preparer not implemented')
  spec=importlib.util.spec_from_file_location('release_prepare',self.script);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 def next_version(self):
  major,minor,patch=map(int,json.loads((self.root/"plugin.json").read_text())["version"].split("."));return f"{major}.{minor}.{patch+1}"
 def retained(self):
  lock=json.loads((self.root/'PACKAGE-HASHES.json').read_text());return {k:{'sha256':v} for k,v in lock.items() if k.startswith('assets/') and not (self.root/k).exists()}
 def snapshot(self):return {p.relative_to(self.root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob('*') if p.is_file()}
 def test_same_inputs_same_zip_and_preserved_source(self):
  m=self.mod();before=self.snapshot();a=self.base/'a.zip';b=self.base/'b.zip'
  m.prepare_release(self.root,self.next_version(),a,self.retained());m.prepare_release(self.root,self.next_version(),b,self.retained())
  self.assertEqual(a.read_bytes(),b.read_bytes());self.assertEqual(before,self.snapshot())
  with zipfile.ZipFile(a) as z:
   manifest=json.loads(z.read('design-skills-router/plugin.json'));old=json.loads((self.root/'plugin.json').read_text())
   self.assertEqual(manifest['extensions'],old['extensions']);self.assertEqual(manifest['version'],self.next_version())
   lock=json.loads(z.read('design-skills-router/PACKAGE-HASHES.json'))
   for name in self.retained():self.assertIn(name,lock);self.assertNotIn('design-skills-router/'+name,z.namelist())
 def test_missing_binary_not_silently_dropped(self):
  # Ensure the binary is deliberately missing in this fixture, even if the
  # package under test came from a complete distribution.
  icon='assets/flor-color-512.png';path=self.root/icon
  path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'fixture-only-icon')
  path.unlink()
  retained={k:v for k,v in self.retained().items() if k!=icon}
  with self.assertRaisesRegex(ValueError,'RETAINED_ASSET_REQUIRED'):
   self.mod().prepare_release(self.root,self.next_version(),self.base/'out.zip',retained)
 def test_baseline_drift_not_rehashed(self):
  (self.root/'skills/design-tree/references/tree-v0.4/tree.json').write_text('{}')
  with self.assertRaisesRegex(ValueError,'BASELINE'):self.mod().prepare_release(self.root,self.next_version(),self.base/'out.zip',self.retained())
 def test_destination_exists_rejected(self):
  out=self.base/'a.zip';out.write_bytes(b'original')
  with self.assertRaisesRegex(ValueError,'DESTINATION'):self.mod().prepare_release(self.root,self.next_version(),out,self.retained())
  self.assertEqual(out.read_bytes(),b'original')
 def test_secret_and_symlink_rejected(self):
  m=self.mod();(self.root/'.env').write_text('SECRET=test')
  with self.assertRaisesRegex(ValueError,'UNSAFE'):m.prepare_release(self.root,self.next_version(),self.base/'out.zip',self.retained())
 def test_symlink_is_rejected_independently(self):
  (self.root/'docs'/'not-a-real-document').symlink_to(self.root/'README.md')
  with self.assertRaisesRegex(ValueError,'UNSAFE_SYMLINK'):
   self.mod().prepare_release(self.root,self.next_version(),self.base/'out.zip',self.retained())
 def test_equal_version_rejected(self):
  version=json.loads((self.root/'plugin.json').read_text())['version']
  with self.assertRaisesRegex(ValueError,'VERSION_MUST_INCREASE'):
   self.mod().prepare_release(self.root,version,self.base/'out.zip',self.retained())
 def test_version_downgrade_rejected(self):
  with self.assertRaisesRegex(ValueError,'VERSION'):self.mod().prepare_release(self.root,'0.1.2',self.base/'out.zip',self.retained())
 def test_compatibility_bytes_match_observed_backend_serialization(self):
  m=self.mod();out=self.base/'normalized.zip';m.prepare_release(self.root,self.next_version(),out,self.retained())
  with zipfile.ZipFile(out) as z:
   portable=json.loads(z.read('design-skills-router/plugin.json'))
   observed=json.loads((self.root/'.codex-plugin/plugin.json').read_text())
   observed['interface']=portable['extensions']['com.openai']['interface'];observed['version']=self.next_version()
   # Exact observed backend order/escaping, not semantic equality only.
   expected=(json.dumps(observed,ensure_ascii=True,indent=2)+'\n').encode()
   self.assertEqual(z.read('design-skills-router/.codex-plugin/plugin.json'),expected)
   lock=json.loads(z.read('design-skills-router/PACKAGE-HASHES.json'))
   self.assertEqual(lock['.codex-plugin/plugin.json'],hashlib.sha256(expected).hexdigest())
