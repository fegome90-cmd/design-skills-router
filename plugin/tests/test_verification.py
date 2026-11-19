"""TDD for separated method, outcome, applicability and policy-owned checks."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/design-tree/scripts'))
from contracts import canonical_hash, policy_hash, validate_contracts

class VerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from verification import validate_results, evaluate_results
        cls.validate_results=staticmethod(validate_results)
        cls.evaluate_results=staticmethod(evaluate_results)
    def policy(self,required=True,when=None,scope='helper',allow_na=False):
        return {'id':'test.required','required':required,'applies_to':['Q00'],'scope':scope,
            'allowed_methods':['LOCAL_TEST' if scope=='helper' else 'HOST_OBSERVATION'],
            'when':when if when is not None else [],'allow_not_applicable':allow_na,
            'source':{'provenance':'router_policy','reason':'Scoped synthetic test obligation'}}
    def check(self,result='PASS',**kw):
        c={'id':'test.required','result':result,'method':'LOCAL_TEST','scope':'helper',
           'environment':{'runtime':'Python','version':'3.13','platform':'linux'},
           'observed_at':'2026-11-10T12:00:00Z','evidence_refs':['sample-v1'],
           'reason':'Synthetic test'}
        c.update(kw);return c
    def data(self,checks):return {'schema':'design-tree-checks/1','checks':checks}
    def validate(self,checks,reqs=None,refs=None):
        return self.validate_results(self.data(checks),reqs if reqs is not None else [self.policy()],refs if refs is not None else {'sample-v1'})
    def test_pass_and_required_fail_unverified(self):
        reqs=[self.policy()]
        self.assertEqual(self.validate([self.check()]),[])
        ok=self.evaluate_results(self.data([self.check()]),reqs,{})
        self.assertEqual(ok['satisfied_ids'],['test.required']);self.assertEqual(ok['blocking_ids'],[])
        for status in ('FAIL','UNVERIFIED'):
            out=self.evaluate_results(self.data([self.check(status)]),reqs,{})
            self.assertEqual(out['blocking_ids'],['test.required'])
    def test_required_missing_and_unknown_applicability_block(self):
        self.assertIn('MISSING_RESULT',[e['code'] for e in self.validate([], [self.policy()])])
        req=[self.policy(when=[{'fact':'present','op':'exists'}])]
        out=self.evaluate_results(self.data([self.check()]),req,{})
        self.assertEqual(out['blocking_ids'],['test.required'])
    def test_legitimate_na_requires_false_fact_and_policy(self):
        req=[self.policy(when=[{'fact':'keyboard','op':'eq','value':True}],allow_na=True)]
        facts={'keyboard':{'state':'PRESENT','value':False,'evidence_refs':['sample-v1']}}
        self.assertEqual(self.validate([self.check('NOT_APPLICABLE',reason='Keyboard not in scope')],req),[])
        out=self.evaluate_results(self.data([self.check('NOT_APPLICABLE',reason='Keyboard not in scope')]),req,facts)
        self.assertEqual(out['not_applicable_ids'],['test.required']);self.assertEqual(out['blocking_ids'],[])
        self.assertEqual(self.evaluate_results(self.data([self.check('NOT_APPLICABLE')]),req,{})['blocking_ids'],['test.required'])
        self.assertEqual(self.evaluate_results(self.data([self.check('NOT_APPLICABLE')]),[self.policy(allow_na=False)],facts)['blocking_ids'],['test.required'])
        self.assertIn('REASON_REQUIRED',[e['code'] for e in self.validate([self.check('NOT_APPLICABLE',reason='')],req)])
    def test_optional_failure_tracked_not_success(self):
        req=[self.policy(required=False)]
        s=self.evaluate_results(self.data([self.check('FAIL')]),req,{})
        self.assertEqual(s['blocking_ids'],[]);self.assertEqual(s['optional_failed_ids'],['test.required']);self.assertEqual(s['satisfied_ids'],[])
    def test_missing_optional_result_does_not_become_requirement(self):
        req=[self.policy(required=False)]
        self.assertEqual(self.validate_results(self.data([]),req,set()),[])
        self.assertEqual(self.evaluate_results(self.data([]),req,{})['blocking_ids'],[])
    def test_empty_requirement_set(self):
        self.assertEqual(self.validate_results(self.data([]),[],set()),[])
        self.assertEqual(self.evaluate_results(self.data([]),[],{})['blocking_ids'],[])
    def test_duplicate_extra_missing_required_forgery(self):
        for checks,expected in [([self.check(),self.check()],'DUPLICATE_RESULT'),([self.check(id='unknown')],'UNKNOWN_RESULT'),([self.check(required=False)],'REQUIRED_OVERRIDE_FORBIDDEN'),([self.check(required=1)],'REQUIRED_OVERRIDE_FORBIDDEN')]:
            with self.subTest(code=expected):self.assertIn(expected,[x['code'] for x in self.validate(checks)])
    def test_invalid_enum_and_missing_evidence_and_timestamp(self):
        inputs=[(self.check('GREEN'),'RESULT_INVALID'),(self.check(scope='host'),'SCOPE_MISMATCH'),
                (self.check(method='HOST_OBSERVATION'),'METHOD_MISMATCH'),
                (self.check(environment={'runtime':'Python','version':'','platform':'linux'}),'ENVIRONMENT_INVALID'),
                (self.check(observed_at='today'),'TIMESTAMP_INVALID'),(self.check(evidence_refs=['unresolved']),'EVIDENCE_UNRESOLVED'),
                (self.check(result='PASS',evidence_refs=[]),'EVIDENCE_REQUIRED'),(self.check('NOT_APPLICABLE',reason=''),'REASON_REQUIRED')]
        for inp,expected in inputs:
            with self.subTest(case=expected):self.assertIn(expected,[x['code'] for x in self.validate([inp])])
    def test_malformed_nested_fields_return_issues_not_exception(self):
        malformed=[self.check(method=[]),self.check(result=[]),
                   self.check(evidence_refs=[{'bad':'type'}]),self.check(id=[])]
        for check in malformed:
            with self.subTest(check=repr(check)):
                issues=self.validate_results(self.data([check]),[self.policy()],{'sample-v1'})
                self.assertTrue(isinstance(issues,list) and issues)
    def test_contract_policy_changes_hash_not_comments(self):
        node={'id':'Q00','definition_id':'Q00','rule_ids':[]}
        contracts={'schema':'design-tree-contracts/0.2','relations':[], 'verification_requirements':[self.policy()]}
        a=policy_hash(node,{},contracts)
        contracts['verification_requirements'][0]['comment']='not normative'
        self.assertEqual(a,policy_hash(node,{},contracts))
        contracts['verification_requirements'][0]['required']=False
        self.assertNotEqual(a,policy_hash(node,{},contracts))
    def test_reject_invalid_policy(self):
        from runner import Router
        router=Router();c=copy.deepcopy(router.contracts)
        c['verification_requirements']=[self.policy(),self.policy()]
        self.assertTrue(any('verification' in str(e).lower() for e in validate_contracts(c,router.nodes,router.inventory)))
        c['verification_requirements']=[self.policy(scope='host')]
        c['verification_requirements'][0]['allowed_methods']=['LOCAL_TEST']
        self.assertTrue(validate_contracts(c,router.nodes,router.inventory))
