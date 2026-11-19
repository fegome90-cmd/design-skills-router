"""End-to-end synthetic fixture. Does not measure an LLM conversation."""
import unittest,sys,copy,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));import test_runner as fixtures

class EndToEndScenarios(unittest.TestCase):
 @classmethod
 def setUpClass(cls):fixtures.RunnerTests.setUpClass()
 def setUp(self):
  self.h=fixtures.RunnerTests(methodName='test_root_only_initially');self.h.setUp();self.addCleanup(self.h.doCleanups);self.r=type(self.h.router)();self.h.router=self.r;self.s=self.h.state
 def route(self,n):
  # Reviewed fixture: existing brand/type/color/layout, web, native/local resources.
  # Literal choices are independent of the runtime's frontier/complete evaluator.
  choices={
   'Q00':'F00','P01':'P02','C01':'C02','S03':'S04','ENV02':'ENV02_1','S01':'S02',
   'D01':'D02','D02':'D03','ART01':'ART01_1','ART02':'ART02_1','ART03':'ART03_1',
   'ART04':'ART04_1','ART05':'ART05_1','T01':'T02','T02':'T03','TY01':'TY01_1',
   'TY02':'TY02_1','TY03':'TY03_1','K01':'K02','K02':'K03','L01':'L02','L02':'L03',
   'LAY01':'LAY01_1','V01':'V02','M01':'M02','RC01':'RC01_1','R01':'R02','R02':'R03',
   'R03__ADOPT_BIND':'R03__ADOPT_BIND_1','R03__ADOPT_PLATFORM':'R03__ADOPT_PLATFORM_1',
   'R03__ADOPT_LICENSE':'R03__ADOPT_LICENSE_1','R03__ADOPT_SECURITY':'R03__ADOPT_SECURITY_1',
   'R03__ADOPT_ACCESS':'R03__ADOPT_ACCESS_1','R03__ADOPT_COST':'R03__ADOPT_COST_1','A10':'A11',
   'A11__ADOPT_BIND':'A11__ADOPT_BIND_1','A11__ADOPT_PLATFORM':'A11__ADOPT_PLATFORM_1',
   'A11__ADOPT_LICENSE':'A11__ADOPT_LICENSE_1','A11__ADOPT_SECURITY':'A11__ADOPT_SECURITY_1',
   'A11__ADOPT_ACCESS':'A11__ADOPT_ACCESS_1','A11__ADOPT_COST':'A11__ADOPT_COST_1',
   'WR01':'WR01_1','AC01':'AC01_1','QA01':'QA01_1','GOV00':'GOV00_1'}
  result={n['id']:None}
  if n['kind']=='all':
   for c in n['children']:result.update(self.route(c['node']))
  elif n['kind']=='decision':
   selected=choices[n['id']];result[n['id']]=selected
   child=next(c['node'] for c in n['children'] if c['node']['id']==selected)
   result.update(self.route(child))
  return result
 def proposal(self,n,choice):
  p=self.h.proposal(n,choice);packet=self.r.packet(self.s,n)
  p['relation_reviews']=[{'relation_id':x,'status':'SATISFIED','reason':'Synthetic fixture domain review','evidence_refs':[str(self.h.ev)]} for x in packet['relationships']['obligations']]
  for review in p['relation_reviews']:
   rel=next(r for r in self.r.contracts['relations'] if r['id']==review['relation_id'])
   if rel['target']['kind']=='resource':review.update(resource_id=rel['target']['id'],resource_path=str(self.h.ev))
  if packet['candidate_key']:
   p['candidate']={'candidate_key':packet['candidate_key'],'component_id':'fixture-component','requirement_id':'fixture-requirement','candidate_source':'https://example.test/fixture','candidate_version':'fixture-1'}
  return p
 def setup_map(self,route):
  m=self.r.default_phase_map();self.r.configure_phases(self.s,m,self.h.receipt(self.h.r.digest(m),'phase_map'))
  # Confirm one exact structural set for the fixture, not per-node conversations.
  ids=list(route);self.r.confirm_structure_set(self.s,ids,self.h.receipt(self.r.structure_set_hash(ids),'structure_set'))
  used=set(s for n in route for s in self.r.skills_for(n))
  rows=[{'skill_id':sid,'disposition':'APPLICABLE' if sid in used else 'NOT_APPLICABLE','reason':'Synthetic route coverage, not a real product judgement','evidence_refs':[str(self.h.ev)]} for sid in self.r.inventory]
  self.r.propose_inventory(self.s,rows)
 def run_all(self):
  # A synthetic pin is isolated from production contracts; not a source-retrieval test.
  for resource in self.r.contracts['resources']:
   resource['sha256']=self.h.evidence()['sha256'];resource.pop('git_blob',None)
  route=self.route(self.r.expanded['root']);self.setup_map(route)
  gates=[]
  for pid in self.s['phases']:
   g=self.r.grant_template(self.s,pid,'phase_auto');self.r.grant_assistance(self.s,g,self.h.receipt(self.r.grant_hash(self.s,g),'delegation'))
   pending={n for n in route if self.r.phase_for(self.s,n)==pid}
   while pending:
    progressed=False
    for n in self.r.frontier(self.s):
     if n not in pending:continue
     try:self.r.check_open(self.s,n)
     except self.h.r.GateError:continue
     self.r.propose(self.s,n,self.proposal(n,route[n]));self.r.delegate_decision(self.s,n);pending.remove(n);progressed=True;break
    self.assertTrue(progressed,'No progress: '+repr(pending))
   pack=self.r.prepare_phase(self.s,pid,[self.h.evidence()]);gates.append(pack['gate_packet_hash'])
   self.assertEqual(self.s['phases'][pid]['status'],'AWAITING_HUMAN')
   self.r.accept_phase(self.s,pid,self.h.receipt(pack['gate_packet_hash'],'phase'))
  return route,gates
 def test_AS17_complete_web_then_evidence_removal_blocks(self):
  route,gates=self.run_all();status=self.r.status(self.s)
  self.assertEqual(len(route),93);self.assertEqual(sum(x is not None for x in route.values()),45)
  self.assertTrue(status['ready_for_human_handoff'],status)
  self.assertEqual(len(gates),4);self.assertEqual(len(self.s['records']),len(route));self.assertFalse(status['permission_to_execute'])
  self.assertTrue(all('receipt' not in r and r['authority']['decided_by']=='agent_delegated' for r in self.s['records'].values()))
  self.h.ev.write_text('evidence changed');self.assertFalse(self.r.status(self.s)['ready_for_human_handoff'])
 def test_AS18_policy_budget_not_claimed_host_measurement(self):
  from assistance import assistance_action
  nodes=[{'id':'n'+str(i)} for i in range(12)]
  state={'assistance_level':'phase_auto','active_phase_id':'p','active_grant_id':'g','grants':{'g':{'id':'g','level':'phase_auto','status':'ACTIVE','reserved_decisions':[],'allowed_actions':['analyze']}},'phases':{'p':{'status':'ACTIVE','node_instance_ids':[n['id'] for n in nodes]}}}
  auto=sum(not assistance_action(state,n,'delegate')['allowed'] for n in nodes)
  state['assistance_level']='manual';manual=sum(not assistance_action(state,n,'delegate')['allowed'] for n in nodes)
  self.assertEqual((manual,auto),(12,0)) # Plus one phase exit gate, not measured agent questions.
 def test_phase_acceptance_is_atomic_and_hash_bound(self):
  route=self.route(self.r.expanded['root']);self.setup_map(route)
  p=self.s['phases']['foundations'];p['status']='AWAITING_HUMAN';p['gate_packet_hash']='0'*64;p['packet']={}
  before=copy.deepcopy(self.s)
  with self.assertRaises(self.h.r.GateError):self.r.accept_phase(self.s,'foundations',self.h.receipt('1'*64,'phase'))
  self.assertEqual(self.s,before)

 def test_bounded_phase_map_preserves_prior_human_approvals(self):
  self.h.complete('Q00','F00')
  self.h.complete('F00',None)
  m={'schema':'design-tree-phases/1','project_kind':'bounded','phases':[
   {'id':'p-subset','revision':1,'family':'foundations','node_instance_ids':['P01','P02'],
    'dependency_ids':[],'deliverables':['Alcance acotado']}]}
  self.r.configure_phases(self.s,m,self.h.receipt(self.h.r.digest(m),'phase_map'))
  g=self.r.grant_template(self.s,'p-subset','guided')
  self.r.grant_assistance(self.s,g,self.h.receipt(self.r.grant_hash(self.s,g),'delegation'))
  st=self.r.status(self.s)
  self.assertIn('P01',st['frontier'])
  self.assertNotIn('Q00',st['frontier'])
  self.assertEqual(st['approved_current_count'],2)
  self.r.check_open(self.s,'P01')

 def test_delegate_rejects_proposal_bound_to_revoked_grant_after_renewal(self):
  m=self.r.default_phase_map()
  self.r.configure_phases(self.s,m,self.h.receipt(self.h.r.digest(m),'phase_map'))
  g1=self.r.grant_template(self.s,'foundations','phase_auto')
  self.r.grant_assistance(self.s,g1,self.h.receipt(self.r.grant_hash(self.s,g1),'delegation'))
  self.h.approve_structure('Q00')
  self.r.propose(self.s,'Q00',self.proposal('Q00','F00'))
  g2=self.r.grant_template(self.s,'foundations','phase_auto')
  self.r.grant_assistance(self.s,g2,self.h.receipt(self.r.grant_hash(self.s,g2),'delegation'))
  with self.assertRaisesRegex(self.h.r.GateError,'DELEGATION_REVOKED'):
   self.r.delegate_decision(self.s,'Q00')
  self.assertEqual(self.s['records']['Q00']['status'],'AWAITING_HUMAN')

 def test_bounded_ledger_recovers_after_invalidating_prior_approval(self):
  self.h.complete('Q00','F00')
  self.h.complete('F00',None)
  m={'schema':'design-tree-phases/1','project_kind':'bounded','phases':[
   {'id':'p-subset','revision':1,'family':'foundations','node_instance_ids':['P01','P02'],
    'dependency_ids':[],'deliverables':['Alcance acotado']}]}
  self.r.configure_phases(self.s,m,self.h.receipt(self.h.r.digest(m),'phase_map'))
  g=self.r.grant_template(self.s,'p-subset','guided')
  self.r.grant_assistance(self.s,g,self.h.receipt(self.r.grant_hash(self.s,g),'delegation'))
  self.h.complete('P01','P02')
  self.h.complete('P02',None)
  packet_hash=self.r.prepare_phase(self.s,'p-subset',[self.h.evidence()])['gate_packet_hash']
  self.r.accept_phase(self.s,'p-subset',self.h.receipt(packet_hash,'phase'))
  # Invalidating prior approval Q00 must allow manual recovery of Q00 -> F00 -> renewed p-subset.
  self.r.invalidate(self.s,'Q00','Revisar raiz')
  st=self.r.status(self.s)
  self.assertEqual(st['frontier'],['Q00'])
  self.assertEqual(self.s['phases']['p-subset']['status'],'STALE')
  # Delegation outside bounded phase stays forbidden even when recovering prerequisites.
  self.assertFalse(self.r.packet(self.s,'Q00')['assistance']['allowed'])
  self.h.complete('Q00','F00')
  self.h.complete('F00',None)
  # Non-prerequisite nodes outside the bounded map remain blocked.
  outside=next(nid for nid in self.r.active(self.s) if nid not in ('P01','P02') and not self.r.record_current(self.s,nid))
  with self.assertRaisesRegex(self.h.r.GateError,'PHASE_BOUNDARY:None'):
   self.r.check_open(self.s,outside)
  g2=self.r.grant_template(self.s,'p-subset','guided')
  self.r.grant_assistance(self.s,g2,self.h.receipt(self.r.grant_hash(self.s,g2),'delegation'))
  self.h.complete('P01','P02')
  self.h.complete('P02',None)
  packet_hash2=self.r.prepare_phase(self.s,'p-subset',[self.h.evidence()])['gate_packet_hash']
  self.r.accept_phase(self.s,'p-subset',self.h.receipt(packet_hash2,'phase'))
  self.assertTrue(self.r.phase_current(self.s,'p-subset'))

 def test_bounded_typography_phase_completes_selected_prerequisite_via_cli(self):
  for node, selected in [('Q00','F00'), ('F00',None), ('D00',None), ('D10',None),
                         ('T00',None), ('S01','S02'), ('S02',None), ('P01','P02')]:
   self.h.complete(node, selected)
  phase_map={'schema':'design-tree-phases/1','project_kind':'bounded','phases':[
   {'id':'type','revision':1,'family':'visual','node_instance_ids':['T01'],
    'dependency_ids':[],'deliverables':['Typography decision']}]}
  self.r.configure_phases(self.s,phase_map,self.h.receipt(self.h.r.digest(phase_map),'phase_map'))
  grant=self.r.grant_template(self.s,'type','manual')
  self.r.grant_assistance(self.s,grant,self.h.receipt(self.r.grant_hash(self.s,grant),'delegation'))
  proposals={node:self.h.proposal(node,choice) for node,choice in [('P02',None),('T01','T02')]}
  self.assertFalse(self.r.packet(self.s,'P02')['assistance']['allowed'])
  with self.assertRaisesRegex(self.h.r.GateError,'PHASE_BOUNDARY'):
   self.r.check_open(self.s,'C01')
  with self.assertRaisesRegex(self.h.r.GateError,'PREREQUISITE_PENDING:P01'):
   self.r.check_open(self.s,'T01')
  ledger=self.h.work/'state.json'
  payload=self.h.work/'payload.json'
  self.h.r.save_state(ledger,self.s,None)
  def cli(command,node,data):
   payload.write_text(json.dumps(data))
   return self.h.r.main(['--state',str(ledger),command,node,'--file',str(payload)])
  for node,proposal in proposals.items():
   cli('structure',node,self.h.receipt(self.r.structure_hash(node),'structure'))
   decision=cli('propose',node,proposal)
   cli('confirm',node,self.h.receipt(decision['proposal_hash'],'project'))
  packet=cli('phase-prepare','type',[self.h.evidence()])
  cli('phase-accept','type',self.h.receipt(packet['gate_packet_hash'],'phase'))
  self.assertTrue(self.r.phase_current(self.h.r.load_state(ledger),'type'))
