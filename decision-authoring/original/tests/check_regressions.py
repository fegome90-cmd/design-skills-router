"""Semantic regressions for the concrete v0.3 findings, run before and after repair."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from model import expand_model
p=Path(sys.argv[1]);t=expand_model(json.loads((p/'tree.json').read_text())); inv=json.loads((p/'skill-inventory.json').read_text())
def flat(n):
 return [n]+[x for c in n.get('children',[]) for x in flat(c['node'])]
nodes=flat(t['root']); by={n['id']:n for n in nodes};out=[]
def check(name,value):out.append({'name':name,'pass':bool(value)})
check('single_root_unique_ids', len(by)==len(nodes))
check('identity_and_required_review_are_siblings', 'D00' in by and {'D01','D10'}<=set(c['node']['id'] for c in by['D00']['children']))
check('existing_scopes_have_review_expansion',all(by[x].get('children') for x in ['E03','E04','E05','E07']))
check('art_direction_decomposed',all(x in by for x in ['ART01','ART02','ART03','ART04','ART05']))
check('microtypography_decomposed',all(x in by for x in ['TY01','TY02','TY03']))
check('deliverable_always_reviewed','ENV00' in by and any(c['node']['id']=='ENV00' for c in by['F00']['children']))
check('capabilities_not_exclusive',by['R11']['kind']=='all' and by['M03']['kind']=='all')
check('cross_discipline_reviewer_present',any('jakubkrehel/skills/better-interface' in n.get('skills',[]) for n in nodes))
check('each_named_candidate_has_assessment',all(by[x].get('candidate_key') and by[x].get('children') for x in ['R03','R04','R05','R08','R09','R12','R13']))
check('all_82_have_disposition',len(inv['skills'])==82 and all(s.get('disposition') and s.get('disposition_reason') for s in inv['skills']))
check('every_decision_has_rule_source',all(n.get('evidence_refs') for n in nodes if n['kind']=='decision'))
check('human_gates_are_not_self_approved',all(n.get('gate',{}).get('status')=='PENDING' for n in nodes))
report={'target':str(p),'passed':sum(x['pass'] for x in out),'failed':sum(not x['pass'] for x in out),'checks':out};print(json.dumps(report,ensure_ascii=False,indent=2));sys.exit(bool(report['failed']))
