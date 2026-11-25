"""Maintenance entry and executable examples from a clean copy; not independent-agent discovery."""
import unittest,subprocess,sys,tempfile,json,hashlib,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class MaintenanceTests(unittest.TestCase):
 def test_entry_routes_maintenance_before_design(self):
  text=(ROOT/'skills/design-tree/SKILL.md').read_text(encoding='utf-8')
  self.assertIn('Mantenimiento del plugin',text)
  self.assertLess(text.index('Mantenimiento del plugin'),text.index('Proyecto de diseño'))
  self.assertIn('MAINTENANCE.md',text);self.assertIn('no iniciar q00',text.lower())
 def test_manual_has_real_commands_and_baseline_owner(self):
  p=ROOT/'skills/design-tree/references/MAINTENANCE.md';self.assertTrue(p.is_file(),'Maintenance manual missing')
  s=p.read_text(encoding='utf-8')
  for x in ('doctor.py','contracts.json','release.py prepare','upgrade-state','grant-packet','baseline-lock.json','rollback','expected_release_id'):self.assertIn(x,s)
  self.assertIn('nueva versión del baseline',s)
 def test_scripts_help_are_real_and_side_effect_free(self):
  for rel in ('skills/design-tree/scripts/doctor.py','skills/design-tree/scripts/runner.py','scripts/release.py'):
   p=ROOT/rel;self.assertTrue(p.is_file(),rel)
   proc=subprocess.run([sys.executable,'-B',str(p),'--help'],capture_output=True,text=True,cwd='/tmp',encoding='utf-8')
   self.assertEqual(proc.returncode,0,proc.stderr);self.assertIn('usage:',proc.stdout)
 def test_relation_editorial_edit_and_pin_diagnostic(self):
  p=ROOT/'skills/design-tree/references/MAINTENANCE.md';self.assertTrue(p.is_file(),'Maintenance manual missing')
  sys.path.insert(0,str(ROOT/'skills/design-tree/scripts'));from runner import Router;from contracts import validate_contracts
  r=Router();import copy
  c=copy.deepcopy(r.contracts);c['relations'][0]['comment']='Synthetic editorial change'
  self.assertEqual(validate_contracts(c,r.nodes,r.inventory),[])
  sid=next(iter(c['source_reviews']));c['source_reviews'][sid]['commit']='0'*40
  self.assertTrue(any('pin' in x['detail'].lower() for x in validate_contracts(c,r.nodes,r.inventory)))

class LearningCandidateTests(unittest.TestCase):
 def test_template_has_reproducible_owner_and_separate_authority(self):
  p=ROOT/'skills/design-tree/references/LEARNING-CANDIDATE.md'
  self.assertTrue(p.is_file(),'Learning candidate template is missing')
  text=p.read_text(encoding='utf-8')
  for field in ('PROPOSED','source_release','owning_file','reproduction','before_evidence','after_evidence','minimal_diff','licence','scope','review_gate'):
   self.assertIn(field,text)
  self.assertIn('fuera del plugin',text.lower())
  self.assertIn('no aplica',text.lower())
 def test_maintenance_requires_review_before_any_learning_update(self):
  text=(ROOT/'skills/design-tree/references/MAINTENANCE.md').read_text(encoding='utf-8')
  self.assertIn('LEARNING-CANDIDATE.md',text)
  self.assertIn('aprobación',text.lower())
  self.assertIn('no auto',text.lower())
