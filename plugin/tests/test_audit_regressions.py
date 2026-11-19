"""Regression targets from audit; deliberately synthetic receipts, never user approvals."""
import unittest, sys, hashlib, copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import test_runner as fixtures

class AuditRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.RunnerTests.setUpClass()
    def setUp(self):
        self.h=fixtures.RunnerTests(methodName='test_root_only_initially'); self.h.setUp()
        self.addCleanup(self.h.doCleanups)
        self.r,self.s=self.h.router,self.h.state
    def test_scope_change_revokes_approval(self):
        self.h.complete('Q00','F00'); self.s['scope']='Different objective'
        self.assertFalse(self.r.record_current(self.s,'Q00'))
    def test_removed_criteria_even_rehashed_not_current(self):
        self.h.complete('Q00','F00');rec=self.s['records']['Q00'];rec['proposal']['criterion_reviews']=[]
        # An integrity wrapper is not semantic validation.
        rec['proposal_hash']=self.h.r.digest({'structure':self.r.structure_hash('Q00'),'proposal':rec['proposal'],'project':self.s['project_id']})
        rec['receipt']['target_hash']=rec['proposal_hash']
        self.assertFalse(self.r.record_current(self.s,'Q00'))
    def test_removed_source_receipts_not_current(self):
        self.h.complete('Q00','F00'); self.s['sources']={};self.s['records']['Q00']['source_hashes']={}
        self.assertFalse(self.r.record_current(self.s,'Q00'))
    def test_inventory_fake_refs_rejected(self):
        rows=[{'skill_id':sid,'disposition':'NOT_APPLICABLE','reason':'fixture','evidence_refs':['invented:scope']} for sid in self.r.inventory]
        with self.assertRaises(self.h.r.GateError): self.r.propose_inventory(self.s,rows)
    def test_unknown_invocation_is_not_false(self):
        self.h.sources('Q00')
        self.assertIsNone(next(iter(self.s['sources'].values()))['explicit_invocation_required'])
