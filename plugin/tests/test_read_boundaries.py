"""Read snapshots never survive a command or an intervening evidence mutation."""
import unittest
import test_runner as fixtures

class ReadBoundaryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):fixtures.RunnerTests.setUpClass()
 def setUp(self):
  self.h=fixtures.RunnerTests(methodName='test_root_only_initially');self.h.setUp();self.addCleanup(self.h.doCleanups)
  self.r,self.s=self.h.router,self.h.state
 def test_next_read_observes_changed_source_evidence(self):
  self.h.complete('Q00','F00');self.assertTrue(self.r.record_current(self.s,'Q00'))
  self.h.ev.write_text('changed evidence',encoding='utf-8');self.assertFalse(self.r.record_current(self.s,'Q00'))
  self.assertEqual(self.r.frontier(self.s),['Q00'])
 def test_next_read_observes_changed_scope(self):
  self.h.complete('Q00','F00');self.r.status(self.s)
  self.s['scope']='Changed product';self.assertFalse(self.r.record_current(self.s,'Q00'))
 def test_next_read_observes_missing_source_set(self):
  self.h.complete('Q00','F00');self.r.frontier(self.s)
  self.s['records']['Q00']['source_hashes']={};self.assertFalse(self.r.record_current(self.s,'Q00'))
