import unittest,importlib,sys
from pathlib import Path
S=Path(__file__).resolve().parents[1]/'skills/design-tree/scripts';sys.path.insert(0,str(S))
class AssistanceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  if not (S/'assistance.py').exists():raise AssertionError('assistance.py missing')
  cls.a=importlib.import_module('assistance')
 def state(self,level='phase_auto'):
  return {'assistance_level':level,'active_phase_id':'p','active_grant_id':'g','grants':{'g':{'id':'g','level':level,'reserved_decisions':[],'allowed_actions':['analyze'],'status':'ACTIVE'}},'phases':{'p':{'status':'ACTIVE','node_instance_ids':['N'],'dependency_ids':[]}}}
 def test_manual_waits(self):self.assertFalse(self.a.assistance_action(self.state('manual'),{'id':'N'},'delegate')['allowed'])
 def test_without_mandate_waits(self):
  s=self.state();s['active_grant_id']=None;self.assertFalse(self.a.assistance_action(s,{'id':'N'},'delegate')['allowed'])
 def test_auto_inside_phase(self):self.assertTrue(self.a.assistance_action(self.state(),{'id':'N'},'delegate')['allowed'])
 def test_guided_reserved_waits(self):
  s=self.state('guided');s['grants']['g']['reserved_decisions']=['N'];self.assertFalse(self.a.assistance_action(s,{'id':'N'},'delegate')['allowed'])
 def test_other_phase_blocked(self):self.assertFalse(self.a.assistance_action(self.state(),{'id':'NEXT'},'delegate')['allowed'])
 def test_gate_waits(self):
  s=self.state();s['phases']['p']['status']='AWAITING_HUMAN';self.assertFalse(self.a.assistance_action(s,{'id':'N'},'delegate')['allowed'])
 def test_approval_not_delegable(self):self.assertFalse(self.a.assistance_action(self.state(),{'id':'N'},'accept_phase')['allowed'])
 def test_exception_not_delegable(self):self.assertFalse(self.a.assistance_action(self.state(),{'id':'N','reserved':True},'delegate')['allowed'])
 def test_external_execution_never_authorized(self):self.assertFalse(self.a.assistance_action(self.state(),{'id':'N'},'publish')['allowed'])
 def test_invalid_level_rejected(self):
  self.assertTrue(self.a.validate_assistance({'level':'full_auto'},{}))
