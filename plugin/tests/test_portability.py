import hashlib,json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/design-tree/scripts'))
import runner

class PortabilityTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.base=Path(self.t.name)
  self.r=runner.Router();self.s=self.r.new_state('portable','web','design','Synthetic portability test')
  self.state=self.base/'original'/'state.json';self.state.parent.mkdir()
  self.e=self.state.parent/'evidence.txt';self.e.write_text('fixture')
  self.sid='fegome90-cmd/my-skills/design-process-orchestrator'
  data=self.e.read_bytes();blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
  self.r.register_source(self.s,self.sid,str(self.e),self.r.inventory[self.sid]['candidate_commit'],blob,'fixture:source')
  h=self.r.structure_hash('Q00');receipt=lambda h,k:{'role':'user','kind':k,'target_hash':h,'quote':'Explicit synthetic approval','message_ref':'fixture:user'}
  self.r.confirm_structure(self.s,'Q00',receipt(h,'structure'))
  packet=self.r.packet(self.s,'Q00')
  p={'summary':'Start fresh test','selected':'F00','alternatives':[{'node_id':a['node_id'],'disposition':'SELECTED' if a['node_id']=='F00' else 'REJECTED','reason':'fixture'} for a in packet['alternatives']],
     'skill_reviews':[{'skill_id':self.sid,'status':'APPLIED','rationale':'fixture','evidence_refs':['fixture:source']}],
     'evidence':[{'path':str(self.e),'sha256':runner.file_hash(self.e),'note':'fixture'}],
     'criterion_reviews':[{'rule_id':c['id'],'disposition':'APPLIED','reason':'fixture','evidence_refs':[str(self.e)]} for c in packet['criteria']],
     'permission':'read_only','verification':'OBSERVED','candidate':None}
  ph=self.r.propose(self.s,'Q00',p);self.r.confirm_decision(self.s,'Q00',receipt(ph,'project'))
  runner.save_state(self.state,self.s,None)
 def cli(self,*args):
  return subprocess.run([sys.executable,str(Path(runner.__file__)),*map(str,args)],capture_output=True,text=True)
 def test_export_is_loadable_integrity_protected_state(self):
  out=self.base/'export';res=self.cli('--state',self.state,'export','--output',out)
  self.assertEqual(res.returncode,0,res.stderr)
  s=runner.load_state(out/'ledger.json');self.assertEqual(s['project_id'],'portable')
 def test_move_bundle_resume_preserves_confirmations(self):
  out=self.base/'export';self.assertEqual(self.cli('--state',self.state,'export','--output',out).returncode,0)
  moved=self.base/'moved';shutil.move(out,moved);shutil.rmtree(self.state.parent)
  new=self.base/'new'/'state.json'
  res=self.cli('--state',new,'resume','--bundle',moved)
  self.assertEqual(res.returncode,0,res.stderr)
  s=runner.load_state(new);self.assertEqual(self.r.frontier(s),['F00'])
 def test_tampered_export_evidence_rejected_on_resume(self):
  out=self.base/'export';self.cli('--state',self.state,'export','--output',out)
  next((out/'evidence').iterdir()).write_text('tampered')
  res=self.cli('--state',self.base/'new.json','resume','--bundle',out)
  self.assertNotEqual(res.returncode,0);self.assertIn('EVIDENCE',res.stderr)
 def test_resume_refuses_overwrite(self):
  out=self.base/'export';self.cli('--state',self.state,'export','--output',out)
  res=self.cli('--state',self.state,'resume','--bundle',out)
  self.assertNotEqual(res.returncode,0)
 def test_export_has_no_external_network_behavior(self):
  source=Path(runner.__file__).read_text()
  self.assertNotIn('import requests',source);self.assertNotIn('urlopen(',source)
