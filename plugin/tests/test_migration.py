import unittest,tempfile,json,sys,copy,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/design-tree/scripts'))
import runner
class MigrationTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.p=Path(self.t.name)
  self.r=runner.Router();self.s=self.r.new_state('old','web','design','fixture');self.s['schema']='design-tree-ledger/0.1'
  for k in ('grants','phases','facts','phase_map','structure_sets','assistance_level','active_grant_id','active_phase_id','phase_map_hash','phase_map_receipt'):self.s.pop(k,None)
  self.bundle=self.p/'old';self.bundle.mkdir();old=copy.deepcopy(self.s);old['integrity']=runner.digest(old)
  (self.bundle/'ledger.json').write_text(json.dumps(old),encoding='utf-8');(self.bundle/'files.json').write_text('{}',encoding='utf-8')
 def mod(self):
  self.assertTrue((Path(runner.__file__).parent/'migration.py').exists(),'migration.py missing')
  import migration;return migration
 def test_dry_run_preserves_input_and_has_no_output(self):
  m=self.mod();before=(self.bundle/'ledger.json').read_bytes();out=self.p/'new'
  r=m.upgrade_bundle(self.r,self.bundle,out,dry_run=True)
  self.assertFalse(out.exists());self.assertEqual(before,(self.bundle/'ledger.json').read_bytes());self.assertEqual(r['default_level'],'manual')
 def test_0_2_migrates_to_0_3_without_elevating_legacy_verification(self):
  m=self.mod()
  old=copy.deepcopy(self.s)
  old['schema']='design-tree-ledger/0.2'
  old['history']=[{'event':'old_verification','verification':'OBSERVED','status':'APPROVED'}]
  old['records']={'Q00':{'status':'APPROVED','proposal':{'verification':'OBSERVED'}}}
  old['integrity']=runner.digest({k:v for k,v in old.items() if k!='integrity'})
  (self.bundle/'ledger.json').write_text(json.dumps(old),encoding='utf-8')
  orig=(self.bundle/'ledger.json').read_bytes();out=self.p/'migrated'
  report=m.upgrade_bundle(self.r,self.bundle,out)
  new=runner.load_state(out/'ledger.json')
  self.assertEqual(report['from_schema'],'design-tree-ledger/0.2')
  self.assertEqual(report['to_schema'],'design-tree-ledger/0.3')
  self.assertEqual(new['schema'],'design-tree-ledger/0.3')
  self.assertEqual(new['records'],{})
  self.assertEqual(new['assistance_level'],'manual')
  self.assertEqual(new['legacy_snapshot']['records']['Q00']['proposal']['verification'],'OBSERVED')
  self.assertNotIn('verification_results',new['records'])
  self.assertEqual(orig,(self.bundle/'ledger.json').read_bytes())
 def test_upgrading_new_schema_does_not_duplicate_state(self):
  m=self.mod();old=copy.deepcopy(self.s);old['schema']=runner.SCHEMA
  old['integrity']=runner.digest({k:v for k,v in old.items() if k!='integrity'})
  (self.bundle/'ledger.json').write_text(json.dumps(old),encoding='utf-8')
  with self.assertRaisesRegex(ValueError,'UPGRADE_ACCEPTS'):
   m.upgrade_bundle(self.r,self.bundle,self.p/'new')
 def test_migration_creates_new_manual_state(self):
  m=self.mod();out=self.p/'new';m.upgrade_bundle(self.r,self.bundle,out)
  new=runner.load_state(out/'ledger.json');self.assertEqual(new['schema'],runner.SCHEMA);self.assertEqual(new['assistance_level'],'manual')
  self.assertEqual(new['records'],{});self.assertEqual(new['grants'],{});self.assertIn('legacy_snapshot',new)
 def test_occupied_output_is_not_overwritten(self):
  m=self.mod();out=self.p/'new';out.mkdir();(out/'keep').write_text('keep',encoding='utf-8')
  with self.assertRaises(ValueError):m.upgrade_bundle(self.r,self.bundle,out)
  self.assertEqual((out/'keep').read_text(encoding='utf-8'),'keep')
 def test_corrupt_input_rejected(self):
  m=self.mod();(self.bundle/'ledger.json').write_text('{',encoding='utf-8')
  with self.assertRaises(ValueError):m.upgrade_bundle(self.r,self.bundle,self.p/'new')
  self.assertFalse((self.p/'new').exists())
 def test_unknown_schema_rejected(self):
  m=self.mod();self.s['schema']='unknown';self.s['integrity']=runner.digest(self.s);(self.bundle/'ledger.json').write_text(json.dumps(self.s),encoding='utf-8')
  with self.assertRaises(ValueError):m.upgrade_bundle(self.r,self.bundle,self.p/'new')
 def test_path_escape_rejected(self):
  m=self.mod();self.s['sources']={'x':{'path':'old/file','sha256':'0'*64}};self.s['integrity']=runner.digest(self.s);(self.bundle/'ledger.json').write_text(json.dumps(self.s),encoding='utf-8');(self.bundle/'files.json').write_text('{"old/file":"../../secret"}',encoding='utf-8')
  with self.assertRaises(ValueError):m.inspect_portable_bundle(self.bundle)
 def test_injected_copy_failure_leaves_no_partial_bundle(self):
  m=self.mod();out=self.p/'new'
  from unittest.mock import patch
  with patch.object(m,'write_json',side_effect=OSError('synthetic disk failure')):
   with self.assertRaises(OSError):m.upgrade_bundle(self.r,self.bundle,out)
  self.assertFalse(out.exists());self.assertEqual([x.name for x in self.p.iterdir()],['old'])
