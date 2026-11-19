"""Behavioral tests for the local ledger; not LLM compliance tests."""
import copy, hashlib, importlib.util, json, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/'skills/design-tree/scripts'
class RunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import sys
        sys.path.insert(0,str(SCRIPTS))
        spec=importlib.util.spec_from_file_location('runner',SCRIPTS/'runner.py')
        if not spec or not spec.loader or not (SCRIPTS/'runner.py').exists():
            raise AssertionError('MISSING_IMPLEMENTATION: runner.py does not exist yet')
        cls.r=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.r)
        cls.router=cls.r.Router()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.work=Path(self.tmp.name)
        self.state=self.router.new_state('pilot','web','design','One screen; no production writes')
        self.ev=self.work/'brief.txt';self.ev.write_text('Synthetic test brief only',encoding='utf-8')
    def evidence(self):return {'path':str(self.ev),'sha256':hashlib.sha256(self.ev.read_bytes()).hexdigest(),'note':'synthetic fixture'}
    def receipt(self,target,kind):
        return {'role':'user','message_ref':'synthetic/user/1','quote':'Apruebo esta propuesta exacta para la prueba.','kind':kind,'target_hash':target}
    def sources(self,node):
        out=[]
        for item in self.router.packet(self.state,node)['skills']:
            sk=item['id'];path=self.work/(hashlib.sha256(sk.encode()).hexdigest()+'.md')
            data=('---\nname: '+item['name']+'\ndescription: Synthetic fixture\n---\nFixture only.\n').encode();path.write_bytes(data)
            git=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
            self.router.register_source(self.state,sk,str(path),item['commit'],git,'synthetic/fetch/1')
            out.append({'skill_id':sk,'status':'APPLIED','rationale':'Applied to this fixture','evidence_refs':['synthetic/fetch/1']})
        return out
    def approve_structure(self,node):
        p=self.router.packet(self.state,node)
        self.router.confirm_structure(self.state,node,self.receipt(p['structure_hash'],'structure'))
    def proposal(self,node,selection=None):
        packet=self.router.packet(self.state,node)
        return {'summary':'Synthetic proposal for test','selected':selection,
                'alternatives':[{'node_id':o['node_id'],'disposition':('REQUIRED' if packet['kind']=='all' else 'SELECTED' if o['node_id']==selection else 'REJECTED'),'reason':'Explicit test reason'} for o in packet['alternatives']],
                'skill_reviews':self.sources(node),'criterion_reviews':[{'rule_id':c['id'],'disposition':'APPLIED','reason':'Synthetic criterion decision','evidence_refs':[str(self.ev)]} for c in packet['criteria']],'evidence':[self.evidence()],
                'candidate':None,'verification':'OBSERVED','permission':'read_only'}
    def complete(self,node,selection=None):
        self.approve_structure(node);p=self.proposal(node,selection)
        h=self.router.propose(self.state,node,p)
        self.router.confirm_decision(self.state,node,self.receipt(h,'project'))
        return h
    def new_branch(self):self.complete('Q00','F00');self.complete('F00')
    def test_root_only_initially(self):
        self.assertEqual(self.router.frontier(self.state),['Q00'])
    def test_packet_contains_real_tree_and_skill(self):
        p=self.router.packet(self.state,'Q00')
        self.assertEqual(len(p['alternatives']),3)
        self.assertEqual(p['skills'][0]['id'],'fegome90-cmd/my-skills/design-process-orchestrator')
    def test_tree_baseline_bytes_preserved(self):
        self.assertEqual(self.router.tree['version'],'0.4');self.assertTrue(self.router.verify_baseline())
    def test_unknown_node_rejected(self):
        with self.assertRaises(self.r.GateError):self.router.packet(self.state,'made-up')
    def test_descendant_is_locked_before_approval(self):
        with self.assertRaises(self.r.GateError):self.router.propose(self.state,'P01',{})
    def test_proposal_without_structure_is_blocked(self):
        p=self.proposal('Q00','F00')
        with self.assertRaisesRegex(self.r.GateError,'STRUCTURE'):self.router.propose(self.state,'Q00',p)
    def test_decision_does_not_auto_approve(self):
        self.approve_structure('Q00');h=self.router.propose(self.state,'Q00',self.proposal('Q00','F00'))
        self.assertEqual(self.router.frontier(self.state),['Q00'])
        self.assertEqual(self.state['records']['Q00']['status'],'AWAITING_HUMAN')
    def test_assistant_receipt_rejected(self):
        p=self.router.packet(self.state,'Q00');r=self.receipt(p['structure_hash'],'structure');r['role']='assistant'
        with self.assertRaisesRegex(self.r.GateError,'HUMAN'):self.router.confirm_structure(self.state,'Q00',r)
    def test_mismatched_receipt_hash_rejected(self):
        self.approve_structure('Q00');h=self.router.propose(self.state,'Q00',self.proposal('Q00','F00'))
        with self.assertRaisesRegex(self.r.GateError,'HASH'):self.router.confirm_decision(self.state,'Q00',self.receipt('0'*64,'project'))
    def test_scope_confusion_rejected(self):
        self.approve_structure('Q00');h=self.router.propose(self.state,'Q00',self.proposal('Q00','F00'))
        with self.assertRaisesRegex(self.r.GateError,'SCOPE'):self.router.confirm_decision(self.state,'Q00',self.receipt(h,'structure'))
    def test_confirmed_choice_opens_only_selected_branch(self):
        self.complete('Q00','F00');self.assertEqual(self.router.frontier(self.state),['F00'])
    def test_all_children_stay_open(self):
        self.new_branch();f=self.router.frontier(self.state)
        for n in ['P01','C01','ENV00','S01','D00']:self.assertIn(n,f)
    def test_all_branch_cannot_be_rejected(self):
        self.complete('Q00','F00');self.approve_structure('F00');p=self.proposal('F00');p['alternatives'][0]['disposition']='REJECTED'
        with self.assertRaisesRegex(self.r.GateError,'ALTERNATIVES'):self.router.propose(self.state,'F00',p)
    def test_unexamined_alternative_blocks(self):
        self.approve_structure('Q00');p=self.proposal('Q00','F00');p['alternatives'].pop()
        with self.assertRaisesRegex(self.r.GateError,'ALTERNATIVES'):self.router.propose(self.state,'Q00',p)
    def test_missing_skill_review_blocks(self):
        self.approve_structure('Q00');p=self.proposal('Q00','F00');p['skill_reviews']=[]
        with self.assertRaisesRegex(self.r.GateError,'SKILL'):self.router.propose(self.state,'Q00',p)
    def test_source_receipt_does_not_prove_comprehension(self):
        self.sources('Q00');x=next(iter(self.state['sources'].values()))
        self.assertEqual(x['coverage'],'BYTES_RECEIVED_NOT_COMPREHENSION')
    def test_missing_source_blocks(self):
        self.approve_structure('Q00');p=self.proposal('Q00','F00');self.state['sources'].clear()
        with self.assertRaisesRegex(self.r.GateError,'SOURCE'):self.router.propose(self.state,'Q00',p)
    def test_changed_source_file_blocks(self):
        self.approve_structure('Q00');p=self.proposal('Q00','F00');next(iter(self.state['sources'].values()))['path']=str(self.ev)
        with self.assertRaisesRegex(self.r.GateError,'SOURCE'):self.router.propose(self.state,'Q00',p)
    def test_wrong_commit_rejected(self):
        sk='fegome90-cmd/my-skills/design-process-orchestrator'
        with self.assertRaisesRegex(self.r.GateError,'COMMIT'):self.router.register_source(self.state,sk,str(self.ev),'main','0'*40,'ref')
    def test_bad_git_blob_rejected(self):
        sk=self.router.packet(self.state,'Q00')['skills'][0]
        with self.assertRaisesRegex(self.r.GateError,'BLOB'):self.router.register_source(self.state,sk['id'],str(self.ev),sk['commit'],'0'*40,'ref')
    def test_evidence_changes_before_confirmation_block(self):
        self.approve_structure('Q00');h=self.router.propose(self.state,'Q00',self.proposal('Q00','F00'));self.ev.write_text('changed')
        with self.assertRaisesRegex(self.r.GateError,'EVIDENCE'):self.router.confirm_decision(self.state,'Q00',self.receipt(h,'project'))
    def test_invalidate_root_revokes_downstream(self):
        self.new_branch();self.router.invalidate(self.state,'Q00','Changed scope')
        self.assertEqual(self.router.frontier(self.state),['Q00'])
        self.assertEqual(self.state['records']['F00']['status'],'STALE')
    def test_siblings_not_invalidated_unnecessarily(self):
        self.new_branch();self.complete('P01','P02');self.complete('C01','C02');self.router.invalidate(self.state,'P01','Changed product')
        self.assertEqual(self.state['records']['C01']['status'],'APPROVED')
    def test_unknown_route_blocks_instead_of_web_fallback(self):
        self.new_branch();self.complete('ENV00');self.complete('S03','S05')
        with self.assertRaisesRegex(self.r.GateError,'BLOCKED_ROUTE'):self.approve_structure('S05')
    def test_incomplete_evidence_leaf_cannot_be_approved(self):
        self.new_branch();self.complete('P01','P03')
        with self.assertRaisesRegex(self.r.GateError,'BLOCKED_ROUTE'):self.approve_structure('P03')
    def test_inventory_preserves_all_entries(self):
        self.assertEqual(len(self.router.inventory),82)
        self.assertEqual(len(self.router.status(self.state)['inventory_pending']),82)
    def test_inventory_no_silent_defaults(self):
        with self.assertRaisesRegex(self.r.GateError,'INVENTORY'):self.router.propose_inventory(self.state,[])
    def test_inventory_proposal_needs_human(self):
        rows=[{'skill_id':i,'disposition':'DEFERRED','reason':'Requires human review in this pilot','evidence_refs':[str(self.ev)]} for i in self.router.inventory]
        h=self.router.propose_inventory(self.state,rows)
        self.assertFalse(self.router.status(self.state)['inventory_confirmed'])
        self.router.confirm_inventory(self.state,self.receipt(h,'inventory'))
        self.assertTrue(self.router.status(self.state)['inventory_confirmed'])
    def test_audit_permission_is_read_only(self):
        self.state['mode']='audit';self.approve_structure('Q00');p=self.proposal('Q00','F00');p['permission']='write'
        with self.assertRaisesRegex(self.r.GateError,'AUDIT'):self.router.propose(self.state,'Q00',p)
    def test_declared_hard_enforcement_is_false(self):
        s=self.router.status(self.state)
        self.assertFalse(s['external_tool_enforcement']);self.assertFalse(s['authenticated_human_identity'])
    def test_initial_not_ready_to_implement(self):
        self.assertFalse(self.router.status(self.state)['ready_for_human_handoff'])
    def test_state_roundtrip_and_integrity(self):
        f=self.work/'state.json';self.r.save_state(f,self.state,expected_revision=None)
        saved=self.r.load_state(f);self.assertEqual(saved['project_id'],'pilot')
        text=json.loads(f.read_text());text['project_id']='tampered';f.write_text(json.dumps(text))
        with self.assertRaisesRegex(self.r.GateError,'INTEGRITY'):self.r.load_state(f)
    def test_state_stale_writer_rejected(self):
        f=self.work/'state.json';self.r.save_state(f,self.state,expected_revision=None);s=self.r.load_state(f)
        self.r.save_state(f,s,expected_revision=s['revision'])
        with self.assertRaisesRegex(self.r.GateError,'REVISION'):self.r.save_state(f,s,expected_revision=0)
    def test_baseline_drift_rejected(self):
        self.state['tree_hash']='0'*64
        with self.assertRaisesRegex(self.r.GateError,'BASELINE'):self.router.frontier(self.state)

    def test_missing_criterion_decisions_blocks(self):
        self.approve_structure('Q00');p=self.proposal('Q00','F00');p.pop('criterion_reviews',None)
        with self.assertRaisesRegex(self.r.GateError,'CRITERION'):self.router.propose(self.state,'Q00',p)
    def test_candidate_identity_is_required(self):
        p=self.proposal('R05')
        with self.assertRaisesRegex(self.r.GateError,'CANDIDATE'):self.router.validate_proposal(self.state,'R05',p)
    def test_candidate_cannot_cross_component_context(self):
        p=self.proposal('R05');p['candidate']={'candidate_key':'R05','component_id':'toast-a','requirement_id':'notify','candidate_source':'fixture:sonner','candidate_version':'test'}
        self.router.validate_proposal(self.state,'R05',p)
        self.state['candidates']['R05']=dict(p['candidate']);p['candidate']['component_id']='toast-b'
        with self.assertRaisesRegex(self.r.GateError,'CANDIDATE_CONTEXT'):self.router.validate_proposal(self.state,'R05',p)
    def test_node_not_applicable_is_not_a_silent_branch_skip(self):
        self.complete('Q00','F00');self.approve_structure('F00');p=self.proposal('F00');p['selected']='P01'
        with self.assertRaisesRegex(self.r.GateError,'ALL_OR_RESULT'):self.router.propose(self.state,'F00',p)
    def test_source_invocation_needs_separate_authority(self):
        self.approve_structure('Q00');p=self.proposal('Q00','F00');p['skill_reviews'][0]['use']='INVOKE'
        with self.assertRaisesRegex(self.r.GateError,'INVOCATION'):self.router.propose(self.state,'Q00',p)


    def test_dangling_skill_evidence_reference_rejected(self):
        self.approve_structure('Q00');p=self.proposal('Q00','F00')
        p['skill_reviews'][0]['evidence_refs']=['invented:receipt']
        with self.assertRaisesRegex(self.r.GateError,'EVIDENCE_REFERENCE'):
            self.router.propose(self.state,'Q00',p)
    def test_dangling_criterion_evidence_reference_rejected(self):
        self.approve_structure('Q00');p=self.proposal('Q00','F00')
        p['criterion_reviews'][0]['evidence_refs']=['invented:receipt']
        with self.assertRaisesRegex(self.r.GateError,'EVIDENCE_REFERENCE'):
            self.router.propose(self.state,'Q00',p)
    def test_string_instead_of_reference_list_rejected(self):
        self.approve_structure('Q00');p=self.proposal('Q00','F00')
        p['criterion_reviews'][0]['evidence_refs']='synthetic/fetch/1'
        with self.assertRaisesRegex(self.r.GateError,'EVIDENCE_REFERENCE'):
            self.router.propose(self.state,'Q00',p)
    def test_inventory_applicable_requires_observed_review(self):
        rows=[{'skill_id':i,'disposition':'APPLICABLE','reason':'Synthetic scope; review is still pending','evidence_refs':[str(self.ev)]} for i in self.router.inventory]
        h=self.router.propose_inventory(self.state,rows)
        self.router.confirm_inventory(self.state,self.receipt(h,'inventory'))
        s=self.router.status(self.state)
        self.assertEqual(set(s.get('unreviewed_applicable_skills',[])),set(self.router.inventory))
    def test_excluded_inventory_cannot_mask_active_applied_skill(self):
        self.complete('Q00','F00')
        rows=[{'skill_id':i,'disposition':'NOT_APPLICABLE','reason':'Synthetic exclusion proposal','evidence_refs':[str(self.ev)]} for i in self.router.inventory]
        h=self.router.propose_inventory(self.state,rows)
        self.router.confirm_inventory(self.state,self.receipt(h,'inventory'))
        s=self.router.status(self.state)
        self.assertIn('fegome90-cmd/my-skills/design-process-orchestrator',s.get('inventory_conflicts',[]))

if __name__=='__main__':unittest.main()
