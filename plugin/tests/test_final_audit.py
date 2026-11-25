import unittest,sys,copy,hashlib,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));import test_runner as fixtures
class FinalAuditTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):fixtures.RunnerTests.setUpClass()
 def setUp(self):
  self.h=fixtures.RunnerTests(methodName='test_root_only_initially');self.h.setUp();self.addCleanup(self.h.doCleanups);self.r,self.s=self.h.router,self.h.state
 def test_relevant_fact_bytes_revalidated_without_condition(self):
  p=self.h.work/'context.txt';p.write_text('old context',encoding='utf-8')
  e={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'note':'context fixture'}
  self.r.set_fact(self.s,'goal',{'state':'PRESENT','value':'one','scope':'project','subject':'pilot','revision':1,'applies_to':['Q00'],'evidence':[e]})
  self.h.complete('Q00','F00');p.write_text('changed context',encoding='utf-8')
  self.assertFalse(self.r.record_current(self.s,'Q00'))
 def test_inventory_confirmation_rejects_evidence_changed(self):
  rows=[{'skill_id':x,'disposition':'NOT_APPLICABLE','reason':'Synthetic scope only','evidence_refs':[str(self.h.ev)]} for x in self.r.inventory]
  h=self.r.propose_inventory(self.s,rows);self.h.ev.write_text('changed',encoding='utf-8')
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
  p=self.h.work/'grant.json';p.write_text(json.dumps(g),encoding='utf-8')
  import subprocess
  run=subprocess.run([sys.executable,'-B',self.h.r.__file__,'--state',str(state),'grant-packet','--file',str(p)],capture_output=True,text=True,encoding='utf-8')
  self.assertEqual(run.returncode,0,run.stderr);out=json.loads(run.stdout)
  self.assertEqual(out['target_hash'],self.r.grant_hash(self.s,g));self.assertEqual(out['grant'],g)

 def register_inventory_source(self,skill,path,ref):
  data=path.read_bytes()
  blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
  self.r.register_source(self.s,skill,path,self.r.inventory[skill]['candidate_commit'],blob,ref)

 def test_inventory_rejects_ambiguous_source_alias(self):
  first,second=list(self.r.inventory)[:2]
  other=self.h.work/'other.txt';other.write_text('Independent reviewed document',encoding='utf-8')
  self.register_inventory_source(first,self.h.ev,'fetch:shared')
  self.register_inventory_source(second,other,'fetch:shared')
  rows=[{'skill_id':sid,'disposition':'DEFERRED','reason':'Review later',
         'evidence_refs':['fetch:shared']} for sid in self.r.inventory]
  with self.assertRaisesRegex(self.h.r.GateError,'EVIDENCE_REFERENCE_AMBIGUOUS'):
   self.r.propose_inventory(self.s,rows)

 def test_inventory_receipt_binds_each_reference_to_its_evidence(self):
  first,second=list(self.r.inventory)[:2]
  other=self.h.work/'other.txt';other.write_text('Independent reviewed document',encoding='utf-8')
  self.register_inventory_source(first,self.h.ev,'fetch:a')
  self.register_inventory_source(second,other,'fetch:b')
  rows=[{'skill_id':sid,'disposition':'DEFERRED','reason':'Review later',
         'evidence_refs':['fetch:a' if sid==first else 'fetch:b']} for sid in self.r.inventory]
  receipt=self.h.receipt(self.r.propose_inventory(self.s,rows),'inventory')
  self.r.confirm_inventory(self.s,receipt)
  self.register_inventory_source(first,self.h.ev,'fetch:b')
  self.register_inventory_source(second,other,'fetch:a')
  self.assertFalse(self.r.inventory_confirmed(self.s))
  with self.assertRaisesRegex(self.h.r.GateError,'INVENTORY_EVIDENCE_CHANGED'):
   self.r.confirm_inventory(self.s,receipt)
  revised=self.r.propose_inventory(self.s,rows)
  self.assertNotEqual(receipt['target_hash'],revised)
  with self.assertRaisesRegex(self.h.r.GateError,'RECEIPT_HASH_MISMATCH'):
   self.r.confirm_inventory(self.s,receipt)
  self.r.confirm_inventory(self.s,self.h.receipt(revised,'inventory'))
  self.assertTrue(self.r.inventory_confirmed(self.s))

 def test_phase_receipt_cannot_accept_rebound_inventory_evidence(self):
  self.h.complete('Q00','F00')
  phase_map={'schema':'design-tree-phases/1','project_kind':'bounded','phases':[
   {'id':'root','family':'foundations','revision':1,'node_instance_ids':['Q00'],
    'dependency_ids':[],'deliverables':['Root decision']}]}
  self.r.configure_phases(self.s,phase_map,self.h.receipt(self.h.r.digest(phase_map),'phase_map'))
  grant=self.r.grant_template(self.s,'root')
  self.r.grant_assistance(self.s,grant,self.h.receipt(self.r.grant_hash(self.s,grant),'delegation'))
  skill=next(sid for sid in self.r.inventory if sid not in self.r.skills_for('Q00'))
  self.register_inventory_source(skill,self.h.ev,'fetch:inventory')
  rows=[{'skill_id':sid,'disposition':'DEFERRED','reason':'Review later',
         'evidence_refs':['fetch:inventory']} for sid in self.r.inventory]
  self.r.propose_inventory(self.s,rows)
  packet=self.r.prepare_phase(self.s,'root',[self.h.evidence()])
  other=self.h.work/'updated.txt';other.write_text('Revised scope',encoding='utf-8')
  self.register_inventory_source(skill,other,'fetch:inventory')
  before=copy.deepcopy(self.s)
  with self.assertRaisesRegex(self.h.r.GateError,'INVENTORY_EVIDENCE_CHANGED'):
   self.r.accept_phase(self.s,'root',self.h.receipt(packet['gate_packet_hash'],'phase'))
  self.assertEqual(self.s,before)

 def test_pending_legacy_inventory_gate_can_receive_a_new_human_receipt(self):
  self.h.complete('Q00','F00')
  records=copy.deepcopy(self.s['records'])
  phase_map={'schema':'design-tree-phases/1','project_kind':'bounded','phases':[
   {'id':'root','family':'foundations','revision':1,'node_instance_ids':['Q00'],
    'dependency_ids':[],'deliverables':['Root decision']}]}
  self.r.configure_phases(self.s,phase_map,self.h.receipt(self.h.r.digest(phase_map),'phase_map'))
  grant=self.r.grant_template(self.s,'root')
  self.r.grant_assistance(self.s,grant,self.h.receipt(self.r.grant_hash(self.s,grant),'delegation'))
  rows=[{'skill_id':sid,'disposition':'DEFERRED','reason':'Review later',
         'evidence_refs':[str(self.h.ev)]} for sid in self.r.inventory]
  self.r.propose_inventory(self.s,rows)
  deliverables=[self.h.evidence()]
  self.r.prepare_phase(self.s,'root',deliverables)
  # Reconstruct exactly the packet and inventory digest written by the previous runner.
  phase=self.s['phases']['root']
  legacy_hash=self.h.r.digest({'baseline':self.r.inventory_hash,'rows':rows,
                               'context':self.r.scope_hash(self.s)})
  phase['packet']['inventory_hash']=legacy_hash
  phase['gate_packet_hash']=self.h.r.digest(phase['packet'])
  self.s['inventory_proposal']['hash']=legacy_hash
  old_receipt=self.h.receipt(phase['gate_packet_hash'],'phase')
  with self.assertRaisesRegex(self.h.r.GateError,'INVENTORY_CHANGED'):
   self.r.accept_phase(self.s,'root',old_receipt)
  changed_rows=copy.deepcopy(rows)
  changed_rows[0]['reason']='Changed after preparation'
  self.r.propose_inventory(self.s,changed_rows)
  with self.assertRaisesRegex(self.h.r.GateError,'PHASE_NOT_ACTIVE'):
   self.r.prepare_phase(self.s,'root',deliverables)
  current_hash=self.r.propose_inventory(self.s,rows)
  before=copy.deepcopy(self.s)
  with self.assertRaisesRegex(self.h.r.GateError,'PHASE_NOT_ACTIVE'):
   self.r.prepare_phase(self.s,'root',[{**deliverables[0],'note':'A different deliverable'}])
  self.assertEqual(self.s,before)
  with self.assertRaisesRegex(self.h.r.GateError,'INVENTORY_CHANGED'):
   self.r.accept_phase(self.s,'root',old_receipt)
  refreshed=self.r.prepare_phase(self.s,'root',deliverables)
  self.assertEqual(refreshed['packet']['inventory_hash'],current_hash)
  self.assertNotEqual(old_receipt['target_hash'],refreshed['gate_packet_hash'])
  self.assertEqual(phase['status'],'AWAITING_HUMAN')
  with self.assertRaisesRegex(self.h.r.GateError,'RECEIPT_HASH_MISMATCH'):
   self.r.accept_phase(self.s,'root',old_receipt)
  with self.assertRaisesRegex(self.h.r.GateError,'PHASE_NOT_ACTIVE'):
   self.r.prepare_phase(self.s,'root',deliverables)
  self.r.accept_phase(self.s,'root',self.h.receipt(refreshed['gate_packet_hash'],'phase'))
  self.assertEqual(self.s['records'],records)
  self.assertTrue(self.r.phase_current(self.s,'root'))
  self.assertTrue(self.r.inventory_confirmed(self.s))
