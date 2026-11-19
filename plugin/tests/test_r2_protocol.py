"""Human approvals here are synthetic fixtures. Not a host/LLM evaluation."""
import unittest,copy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));import test_runner as fixtures
class ProtocolTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): fixtures.RunnerTests.setUpClass()
 def setUp(self):
  self.h=fixtures.RunnerTests(methodName='test_root_only_initially');self.h.setUp();self.addCleanup(self.h.doCleanups)
  self.r,self.s=self.h.router,self.h.state
 def setup_phases(self,level='phase_auto'):
  self.assertTrue(hasattr(self.r,'default_phase_map'),'Phase protocol missing')
  m=self.r.default_phase_map();self.r.configure_phases(self.s,m,self.h.receipt(self.h.r.digest(m),'phase_map'))
  ids=list(self.r.nodes);self.r.confirm_structure_set(self.s,ids,self.h.receipt(self.r.structure_set_hash(ids),'structure_set'))
  g=self.r.grant_template(self.s,'foundations',level)
  self.r.grant_assistance(self.s,g,self.h.receipt(self.r.grant_hash(self.s,g),'delegation'))
 def delegate(self,n,choice=None):
  p=self.h.proposal(n,choice);h=self.r.propose(self.s,n,p);self.r.delegate_decision(self.s,n);return h
 def test_default_manual(self):self.assertEqual(self.s.get('assistance_level'),'manual')
 def test_delegation_requires_real_scoped_protocol(self):
  self.setup_phases();self.delegate('Q00','F00')
  self.assertEqual(self.s['records']['Q00']['status'],'DECIDED_DELEGATED')
  self.assertNotIn('receipt',self.s['records']['Q00']);self.assertEqual(self.r.frontier(self.s),['F00'])
 def test_cannot_delegate_without_mandate(self):
  self.assertTrue(hasattr(self.r,'delegate_decision'),'Phase protocol missing')
  self.h.approve_structure('Q00');self.r.propose(self.s,'Q00',self.h.proposal('Q00','F00'))
  with self.assertRaises(self.h.r.GateError):self.r.delegate_decision(self.s,'Q00')
 def test_next_phase_cannot_open_early(self):
  self.setup_phases();self.delegate('Q00','F00');self.delegate('F00')
  with self.assertRaisesRegex(self.h.r.GateError,'PHASE'):self.r.propose(self.s,'D00',self.h.proposal('D00'))
 def test_phase_gate_refuses_missing_work(self):
  self.setup_phases();self.delegate('Q00','F00')
  with self.assertRaisesRegex(self.h.r.GateError,'PHASE'):self.r.prepare_phase(self.s,'foundations',[self.h.evidence()])
 def test_level_change_preserves_sources_and_stops_delegation(self):
  self.setup_phases();self.delegate('Q00','F00');sources=copy.deepcopy(self.s['sources'])
  self.r.revoke_delegation(self.s,'User requested manual')
  self.assertEqual(self.s['sources'],sources);self.assertEqual(self.s['assistance_level'],'manual')
  self.assertFalse(self.r.record_current(self.s,'Q00'))
 def test_phase_cannot_cover_whole_project(self):
  self.assertTrue(hasattr(self.r,'configure_phases'),'Phase protocol missing')
  m={'schema':'design-tree-phases/1','project_kind':'multi_phase','phases':[{'id':'all','revision':1,'node_instance_ids':list(self.r.nodes),'dependency_ids':[],'deliverables':['all'],'family':'all'}]}
  with self.assertRaises(self.h.r.GateError):self.r.configure_phases(self.s,m,self.h.receipt(self.h.r.digest(m),'phase_map'))
 def test_structure_batch_cannot_use_assistant_receipt(self):
  self.assertTrue(hasattr(self.r,'structure_set_hash'),'Phase protocol missing')
  ids=['Q00'];r=self.h.receipt(self.r.structure_set_hash(ids),'structure_set');r['role']='assistant'
  with self.assertRaises(self.h.r.GateError):self.r.confirm_structure_set(self.s,ids,r)
 def test_context_fact_changes_selected_decision_only(self):
  self.assertTrue(hasattr(self.r,'set_fact'),'Fact protocol missing')
  self.h.new_branch();self.h.complete('P01','P02');self.h.complete('C01','C02')
  self.r.set_fact(self.s,'product.goal',{'state':'PRESENT','value':'new goal','scope':'project','subject':'pilot','revision':1,'applies_to':['P01'],'evidence':[self.h.evidence()]})
  self.assertFalse(self.r.record_current(self.s,'P01'));self.assertTrue(self.r.record_current(self.s,'C01'))
