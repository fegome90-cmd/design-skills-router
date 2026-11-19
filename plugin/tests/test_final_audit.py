import unittest,sys,copy,hashlib,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));import test_runner as fixtures
class FinalAuditTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):fixtures.RunnerTests.setUpClass()
 def setUp(self):
  self.h=fixtures.RunnerTests(methodName='test_root_only_initially');self.h.setUp();self.addCleanup(self.h.doCleanups);self.r,self.s=self.h.router,self.h.state
 def test_relevant_fact_bytes_revalidated_without_condition(self):
  p=self.h.work/'context.txt';p.write_text('old context')
  e={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'note':'context fixture'}
  self.r.set_fact(self.s,'goal',{'state':'PRESENT','value':'one','scope':'project','subject':'pilot','revision':1,'applies_to':['Q00'],'evidence':[e]})
  self.h.complete('Q00','F00');p.write_text('changed context')
  self.assertFalse(self.r.record_current(self.s,'Q00'))
 def test_inventory_confirmation_rejects_evidence_changed(self):
  rows=[{'skill_id':x,'disposition':'NOT_APPLICABLE','reason':'Synthetic scope only','evidence_refs':[str(self.h.ev)]} for x in self.r.inventory]
  h=self.r.propose_inventory(self.s,rows);self.h.ev.write_text('changed')
  with self.assertRaisesRegex(self.h.r.GateError,'EVIDENCE'):self.r.confirm_inventory(self.s,self.h.receipt(h,'inventory'))
 def test_invalid_fact_binding_rejected(self):
  with self.assertRaisesRegex(self.h.r.GateError,'FACT_BINDING'):
   self.r.set_fact(self.s,'goal',{'state':'UNKNOWN','scope':'project','subject':'pilot','revision':1,'applies_to':['made-up']})
 def test_non_object_alternative_is_protocol_error_not_crash(self):
  self.h.approve_structure('Q00');p=self.h.proposal('Q00','F00');p['alternatives'][0]='bad'
  with self.assertRaises(self.h.r.GateError):self.r.propose(self.s,'Q00',p)
 def test_grant_packet_cli_hashes_edited_input(self):
  m=self.r.default_phase_map();self.r.configure_phases(self.s,m,self.h.receipt(self.h.r.digest(m),'phase_map'))
  state=self.h.work/'state.json';self.h.r.save_state(state,self.s,None)
  g=self.r.grant_template(self.s,'foundations','guided');g.update(message_ref='synthetic:1',quote='Synthetic delegation only')
  p=self.h.work/'grant.json';p.write_text(json.dumps(g))
  import subprocess
  run=subprocess.run([sys.executable,'-B',self.h.r.__file__,'--state',str(state),'grant-packet','--file',str(p)],capture_output=True,text=True)
  self.assertEqual(run.returncode,0,run.stderr);out=json.loads(run.stdout)
  self.assertEqual(out['target_hash'],self.r.grant_hash(self.s,g));self.assertEqual(out['grant'],g)
