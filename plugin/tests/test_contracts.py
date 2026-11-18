import unittest,sys,importlib,json,copy
from pathlib import Path
S=Path(__file__).resolve().parents[1]/'skills/design-tree/scripts';sys.path.insert(0,str(S))
class ContractsTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  if not (S/'contracts.py').exists():raise AssertionError('contracts.py is missing')
  cls.c=importlib.import_module('contracts')
 def test_missing_and_known_absent_differ(self):
  self.assertEqual(self.c.evaluate_condition([{'fact':'x','op':'exists'}],{}),'UNKNOWN')
  self.assertEqual(self.c.evaluate_condition([{'fact':'x','op':'exists'}],{'x':{'state':'ABSENT','evidence_refs':['fixture']}}),'FALSE')
 def test_false_and_unknown_is_false(self):
  facts={'x':{'state':'PRESENT','value':False,'evidence_refs':['fixture']}}
  self.assertEqual(self.c.evaluate_condition([{'fact':'x','op':'eq','value':True},{'fact':'missing','op':'exists'}],facts),'FALSE')
 def test_true_and_unknown_is_unknown(self):
  self.assertEqual(self.c.evaluate_condition([{'fact':'x','op':'exists'}],{'x':{'state':'PRESENT','value':1,'evidence_refs':[]}}),'UNKNOWN')
 def test_typed_equality(self):
  self.assertEqual(self.c.evaluate_condition([{'fact':'x','op':'eq','value':1}],{'x':{'state':'PRESENT','value':True,'evidence_refs':['e']}}),'FALSE')
 def test_unsupported_operator_rejected(self):
  with self.assertRaises(ValueError):self.c.evaluate_condition([{'fact':'x','op':'eval','value':'code'}],{})
 def contract(self,typ='optional_companion'):
  return {'schema':'design-tree-contracts/0.2','relations':[{'id':'r','from_skill':'a','target':{'kind':'skill','id':'b'},'type':typ,'required':typ!='optional_companion','applies_to':['N'],'when':[{'fact':'x','op':'exists'}],'scope':'reference','source':{'url':'https://example.test/pinned','commit':'0'*40,'section':'test'},'provenance':'router_policy','evidence_status':'SOURCE_REVIEWED'}]}
 def test_unselected_optional_does_not_block_on_unknown(self):
  r=self.c.evaluate_contracts({'id':'N','definition_id':'N'},{'facts':{},'selected_relations':[]},self.contract())
  self.assertEqual(r['pending'],[]);self.assertEqual(r['obligations'],[])
 def test_required_unknown_is_pending(self):
  r=self.c.evaluate_contracts({'id':'N','definition_id':'N'},{'facts':{}},self.contract('requires_skill'))
  self.assertEqual(r['pending'],['r'])
 def test_reference_does_not_require_runtime(self):
  d=self.contract('requires_skill');d['relations'][0]['scope']='verification'
  r=self.c.evaluate_contracts({'id':'N','definition_id':'N'},{'facts':{},'operation':'reference'},d)
  self.assertEqual(r['pending'],[])
 def test_mandatory_cycle_is_reported(self):
  d=self.contract('requires_skill');a=d['relations'][0];b=copy.deepcopy(a);b.update(id='s',from_skill='b',target={'kind':'skill','id':'a'});d['relations'].append(b)
  f=self.c.validate_contracts(d,{'N':{'id':'N','definition_id':'N'}},{'a':{},'b':{}})
  self.assertTrue(any('cycle' in x['detail'].lower() for x in f))
 def test_malformed_source_review_returns_issue_not_exception(self):
  from runner import Router
  r=Router();d=copy.deepcopy(r.contracts)
  sid=next(iter(d['source_reviews']));d['source_reviews'][sid]=None
  issues=self.c.validate_contracts(d,r.nodes,r.inventory)
  self.assertTrue(any('review' in str(i).lower() for i in issues))
 def test_invalid_hex_commit_rejected_in_relation(self):
  c=self.contract('requires_skill');c['relations'][0]['source']['commit']='Z'*40
  issues=self.c.validate_contracts(c,{'N':{'id':'N','definition_id':'N'}},{'a':{},'b':{}})
  self.assertTrue(any('pinned' in i['detail'].lower() for i in issues))
 def test_rule_changes_modify_policy_hash_not_comments(self):
  node={'id':'N','definition_id':'N','rule_ids':['r']};rules={'r':{'criterion':'a'}};con={'schema':'design-tree-contracts/0.2','relations':[]}
  h=self.c.policy_hash(node,rules,con);con['comment']='non normative';self.assertEqual(h,self.c.policy_hash(node,rules,con))
  rules['r']['criterion']='b';self.assertNotEqual(h,self.c.policy_hash(node,rules,con))
