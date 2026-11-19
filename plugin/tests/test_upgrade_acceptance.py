"""Outcome contract acceptance tests for the 0.3.0 candidate.
Synthetic user receipts are test fixtures, never real approval.
"""
import unittest, sys, copy, os
from pathlib import Path
BASE=Path(os.environ.get('ROUTER_ROOT',str(Path(__file__).resolve().parents[1])))
sys.path.insert(0,str(Path(__file__).resolve().parent)); sys.path.insert(0,str(BASE/'tests')); sys.path.insert(0,str(BASE/'skills/design-tree/scripts'))
import test_runner as fixtures
from contracts import evaluate_condition, evaluate_contracts
from assistance import assistance_action

class UpgradeAcceptance(unittest.TestCase):
 @classmethod
 def setUpClass(cls):fixtures.RunnerTests.setUpClass()
 def setUp(self):
  self.h=fixtures.RunnerTests(methodName='test_root_only_initially');self.h.setUp();self.addCleanup(self.h.doCleanups)
  self.r=type(self.h.router)();self.h.router=self.r;self.s=self.h.state
 def prepare(self,check,legacy='OBSERVED',required=True):
  self.r.contracts['verification_requirements']=[{'id':'probe.required','applies_to':['Q00'],'required':required,'scope':'helper','allowed_methods':['LOCAL_TEST'],'when':[],'allow_not_applicable':False,'source':{'provenance':'router_policy','reason':'Synthetic required check for regression'}}]
  m={'schema':'design-tree-phases/1','project_kind':'bounded','phases':[{'id':'probe','revision':1,'node_instance_ids':['Q00'],'dependency_ids':[],'deliverables':['synthetic artifact'],'family':self.r.phase_family('Q00')}]}
  self.r.configure_phases(self.s,m,self.h.receipt(self.h.r.digest(m),'phase_map'))
  self.r.confirm_structure_set(self.s,['Q00'],self.h.receipt(self.r.structure_set_hash(['Q00']),'structure_set'))
  g=self.r.grant_template(self.s,'probe','phase_auto');self.r.grant_assistance(self.s,g,self.h.receipt(self.r.grant_hash(self.s,g),'delegation'))
  p=self.h.proposal('Q00','F00');p['verification']=legacy
  if check is not None:p['verification_results']={'schema':'design-tree-checks/1','checks':[check]}
  self.r.propose(self.s,'Q00',p);self.r.delegate_decision(self.s,'Q00')
  return self.r.prepare_phase(self.s,'probe',[self.h.evidence()])
 def check(self,result='PASS',**kwargs):
  value={'id':'probe.required','required':True,'result':result,'method':'LOCAL_TEST','scope':'helper','environment':{'runtime':'Python','version':sys.version.split()[0],'platform':sys.platform},'observed_at':'2026-11-10T12:06:00Z','evidence_refs':[str(self.h.ev)],'reason':'Synthetic experiment'}
  value.update(kwargs);return value
 def test_U01_required_fail_cannot_prepare_phase(self):
  with self.assertRaisesRegex(self.h.r.GateError,'CHECK|VERIFICATION'):self.prepare(self.check('FAIL'))
 def test_U02_required_unverified_cannot_prepare_phase(self):
  with self.assertRaisesRegex(self.h.r.GateError,'CHECK|VERIFICATION'):self.prepare(self.check('UNVERIFIED'))
 def test_U03_local_test_cannot_certify_host(self):
  with self.assertRaisesRegex(self.h.r.GateError,'CHECK|VERIFICATION'):self.prepare(self.check(scope='host'))
 def test_U04_not_applicable_requires_reason(self):
  with self.assertRaisesRegex(self.h.r.GateError,'CHECK|VERIFICATION'):self.prepare(self.check('NOT_APPLICABLE',reason=''))
 def test_C01_legacy_unverified_already_blocks(self):
  with self.assertRaisesRegex(self.h.r.GateError,'PHASE_VERIFICATION_PENDING'):self.prepare(self.check('PASS'),legacy='NOT_VERIFIED')
 def test_C02_phase_awaits_human_and_cannot_execute(self):
  self.prepare(self.check('PASS'));self.assertEqual(self.s['phases']['probe']['status'],'AWAITING_HUMAN');self.assertFalse(self.r.status(self.s)['permission_to_execute'])
 def test_required_missing_result_rejected_during_propose(self):
  with self.assertRaisesRegex(self.h.r.GateError,'CHECK_RESULTS_INVALID:MISSING_RESULT'):
   self.prepare(None)
 def test_required_pass_can_be_accepted_and_is_current(self):
  answer=self.prepare(self.check('PASS'))
  self.assertTrue(self.r.status(self.s)['failed_required_check_nodes']==[])
  self.r.accept_phase(self.s,'probe',self.h.receipt(answer['gate_packet_hash'],'phase'))
  self.assertTrue(self.r.phase_current(self.s,'probe'))
 def test_change_of_verification_policy_invalidates_decision(self):
  self.prepare(self.check('PASS'))
  self.assertTrue(self.r.record_current(self.s,'Q00'))
  self.r.contracts['verification_requirements'][0]['allowed_methods']=['STATIC_REVIEW']
  self.assertFalse(self.r.record_current(self.s,'Q00'))
  with self.assertRaisesRegex(self.h.r.GateError,'PHASE_OBLIGATIONS_PENDING|PHASE_'):
   self.r.prepare_phase(self.s,'probe',[self.h.evidence()])
 def test_required_failure_is_visible_in_status(self):
  with self.assertRaisesRegex(self.h.r.GateError,'CHECK_REQUIRED_PENDING'):
   self.prepare(self.check('FAIL'))
  self.assertIn('Q00',self.r.status(self.s)['failed_required_check_nodes'])
 def test_optional_failure_is_not_recorded_as_success(self):
  self.prepare(self.check('FAIL',required=False),required=False)
  self.assertEqual(self.r.check_outcomes(self.s,'Q00',self.s['records']['Q00']['proposal'])['optional_failed_ids'],['probe.required'])
 def test_evidence_tampering_after_accept_invalidates_phase(self):
  answer=self.prepare(self.check('PASS'))
  self.r.accept_phase(self.s,'probe',self.h.receipt(answer['gate_packet_hash'],'phase'))
  self.h.ev.write_text('after acceptance, altered evidence')
  self.assertFalse(self.r.phase_current(self.s,'probe'))
 def test_required_check_cannot_use_unrelated_skill_source(self):
  self.prepare(self.check('PASS'))
  self.s['sources']['unrelated-skill']={'source_ref':'cross-scope-source',
    'path':str(self.h.ev),'sha256':self.h.evidence()['sha256']}
  candidate=copy.deepcopy(self.s['records']['Q00']['proposal'])
  candidate['verification_results']['checks'][0]['evidence_refs']=['cross-scope-source']
  with self.assertRaisesRegex(self.h.r.GateError,'EVIDENCE_UNRESOLVED'):
   self.r.validate_proposal(self.s,'Q00',candidate)
 def test_C03_missing_fact_is_unknown(self):
  self.assertEqual(evaluate_condition([{'fact':'missing','op':'exists'}],{}),'UNKNOWN')
 def test_C04_false_conjunction_not_unknown(self):
  self.assertEqual(evaluate_condition([{'fact':'known','op':'eq','value':True},{'fact':'missing','op':'exists'}],{'known':{'state':'PRESENT','value':False,'evidence_refs':['fixture']}}),'FALSE')
 def test_C05_boolean_does_not_equal_integer(self):
  self.assertEqual(evaluate_condition([{'fact':'known','op':'eq','value':1}],{'known':{'state':'PRESENT','value':True,'evidence_refs':['fixture']}}),'FALSE')
 def test_C06_cannot_forge_human_role(self):
  p=self.r.packet(self.s,'Q00');receipt=self.h.receipt(p['structure_hash'],'structure');receipt['role']='assistant'
  with self.assertRaisesRegex(self.h.r.GateError,'HUMAN'):self.r.confirm_structure(self.s,'Q00',receipt)
