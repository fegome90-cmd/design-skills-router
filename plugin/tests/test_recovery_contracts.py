"""Regression cases found in final self-review; approvals are synthetic."""
import unittest,sys,copy,hashlib,json,subprocess,tempfile,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));import test_runner as fixtures
ROOT=Path(__file__).resolve().parents[1]
class RecoveryContractTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):fixtures.RunnerTests.setUpClass()
 def setUp(self):
  self.h=fixtures.RunnerTests(methodName='test_root_only_initially');self.h.setUp();self.addCleanup(self.h.doCleanups)
  self.r=type(self.h.router)();self.h.router=self.r;self.s=self.h.state
 def test_audit_selection_prevents_sibling_write(self):
  self.h.new_branch();self.h.complete('ENV00');self.h.complete('ENV02','ENV02_2')
  self.h.approve_structure('P01');p=self.h.proposal('P01','P02');p['permission']='write'
  with self.assertRaisesRegex(self.h.r.GateError,'AUDIT'):self.r.propose(self.s,'P01',p)
 def test_resource_requires_specific_evidence_file(self):
  sid=self.r.skills_for('Q00')[0]
  resource=self.h.work/'reference.md';resource.write_text('Required reference content',encoding='utf-8')
  self.r.contracts['resources']=[{'id':'ref1','sha256':hashlib.sha256(resource.read_bytes()).hexdigest()}]
  self.r.contracts['relations'].append({'id':'resource1','from_skill':sid,'target':{'kind':'resource','id':'ref1'},'type':'uses_resource','required':True,'scope':'reference','applies_to':['Q00'],'when':[],'source':{'url':'https://example.test/source','commit':'a'*40,'section':'fixture'},'provenance':'router_policy','evidence_status':'SOURCE_REVIEWED'})
  p=self.h.proposal('Q00','F00');p['relation_reviews']=[{'relation_id':'resource1','status':'SATISFIED','reason':'fixture','evidence_refs':[str(self.h.ev)]}]
  with self.assertRaisesRegex(self.h.r.GateError,'RESOURCE'):self.r.validate_proposal(self.s,'Q00',p)
  e={'path':str(resource),'sha256':hashlib.sha256(resource.read_bytes()).hexdigest(),'note':'specific resource'}
  p['evidence'].append(e);p['relation_reviews'][0].update(resource_id='ref1',resource_path=str(resource),evidence_refs=[str(resource)])
  self.assertTrue(self.r.validate_proposal(self.s,'Q00',p))
 def test_unknown_optional_relation_cannot_be_selected(self):
  p=self.h.proposal('Q00','F00');p['selected_relations']=['made-up']
  with self.assertRaisesRegex(self.h.r.GateError,'RELATION'):self.r.validate_proposal(self.s,'Q00',p)
 def test_reopen_preserves_old_gate_and_retires_authority(self):
  m=self.r.default_phase_map();self.r.configure_phases(self.s,m,self.h.receipt(self.h.r.digest(m),'phase_map'))
  g=self.r.grant_template(self.s,'foundations','phase_auto');self.r.grant_assistance(self.s,g,self.h.receipt(self.r.grant_hash(self.s,g),'delegation'))
  # This recovery fixture is a stored gate, not a claim it passed a real evaluation.
  p=self.s['phases']['foundations'];p.update(status='AWAITING_HUMAN',gate_packet_hash='a'*64,packet={'synthetic':'old'})
  rec=self.h.receipt(self.h.r.digest({'phase_id':'foundations','gate_packet_hash':'a'*64,'reason':'revise'}),'reopen')
  self.r.reopen_phase(self.s,'foundations','revise',rec)
  self.assertTrue(any(x.get('event')=='phase_reopened' and x.get('previous',{}).get('packet')=={'synthetic':'old'} for x in self.s['history']))
  self.assertIsNone(self.s['active_grant_id']);self.assertNotIn('packet',self.s['phases']['foundations'])
 def test_contract_malformed_target_is_diagnostic(self):
  from contracts import validate_contracts
  c=copy.deepcopy(self.r.contracts);c['relations'][0]['target']=None
  self.assertTrue(validate_contracts(c,self.r.nodes,self.r.inventory))
 def test_doctor_non_object_manifest_is_diagnostic(self):
  p=self.h.work/'copy';shutil.copytree(ROOT,p,ignore=shutil.ignore_patterns('.git','__pycache__'))
  (p/'plugin.json').write_text('[]',encoding='utf-8')
  run=subprocess.run([sys.executable,'-B',str(ROOT/'skills/design-tree/scripts/doctor.py'),'--package-root',str(p),'--format','json'],capture_output=True,text=True,encoding='utf-8')
  self.assertEqual(run.returncode,2,run.stderr);r=json.loads(run.stdout)
  self.assertTrue(any(x['code']=='INVALID_JSON_TYPE' for x in r['findings']))
 def test_reopen_cli_reports_actual_stale_state(self):
  m=self.r.default_phase_map();self.r.configure_phases(self.s,m,self.h.receipt(self.h.r.digest(m),'phase_map'))
  phase=self.s['phases']['foundations'];phase.update(status='AWAITING_HUMAN',gate_packet_hash='a'*64,packet={'synthetic':'old'})
  state=self.h.work/'ledger.json';self.h.r.save_state(state,self.s,None)
  receipt=self.h.receipt(self.h.r.digest({'phase_id':'foundations','gate_packet_hash':'a'*64,'reason':'revise'}),'reopen')
  rp=self.h.work/'receipt.json';rp.write_text(json.dumps(receipt),encoding='utf-8')
  proc=subprocess.run([sys.executable,'-B',str(Path(self.h.r.__file__)),'--state',str(state),'phase-reopen','foundations','--reason','revise','--file',str(rp)],capture_output=True,text=True,encoding='utf-8')
  self.assertEqual(proc.returncode,0,proc.stderr);data=json.loads(proc.stdout);saved=self.h.r.load_state(state)
  self.assertEqual(data['status'],saved['phases']['foundations']['status']);self.assertEqual(data['status'],'STALE')
