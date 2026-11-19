from pathlib import Path
import json,sys,copy,hashlib
import pytest
from bs4 import BeautifulSoup
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from model import expand_model,flatten
P=Path(__file__).resolve().parents[1]
SRC=json.loads((P/'tree.json').read_text()); INV=json.loads((P/'skill-inventory.json').read_text());RULES=json.loads((P/'rules.json').read_text())
MODEL=expand_model(SRC); NODES=list(flatten(MODEL['root']));BY={n['id']:n for n in NODES}
DEFS=[n for n in flatten(SRC['root']) if n['kind']!='instance']+[n for v in SRC['templates'].values() for n in flatten(v) if n['kind']!='instance'];DB={n['id']:n for n in DEFS}
def verify(model,inventory):
 ns=list(flatten(model['root']));by={n['id']:n for n in ns}
 assert len(by)==len(ns),'duplicate-instance'
 assert model['root']['id']=='Q00','root'
 assert len(inventory['skills'])==82,'inventory-count'
 assert all(n['gate']['status']=='PENDING' for n in ns),'autoapproval'
 assert {'D01','D10'}<=set(c['node']['id'] for c in by['D00']['children']),'identity-coverage'
 for n in ns:
  assert all(r in RULES for r in n.get('rule_ids',[])),'source-rule'
  if n.get('adoption_contract'):
   descendants=list(flatten(n))
   assert all(x.get('candidate_key')==n['candidate_key'] for x in descendants),'foreign-candidate'
  if n.get('context_mode')=='audit':assert n.get('write_policy')=='NO_WRITES','audit-writes'
 return True

def test_structural_and_semantic_validator():assert verify(MODEL,INV)
def test_decisions_are_real_branches():assert all(len(n['children'])>=2 for n in NODES if n['kind']=='decision')
def test_results_have_no_children():assert all(not n['children'] for n in NODES if n['kind']=='result')
def test_no_unresolved_instances():assert all(n['kind']!='instance' for n in NODES)
def test_pending_gates_are_present_everywhere():assert all(n['gate'].get('needs') and n['human_review']=='PENDING' for n in NODES)
def test_new_and_existing_preserve_domain_coverage():
 for prefix in ['','E03__','E04__','E05__','E07__']:
  assert prefix+'ENV00' in BY
  d=BY[prefix+'D00'];assert {prefix+'D01',prefix+'D10'}<=set(c['node']['id'] for c in d['children'])
  for id in ['ART01','ART02','ART03','ART04','ART05','TY01','TY02','TY03','QA01']:
   assert prefix+id in BY

def test_independent_capabilities_are_not_xor():
 assert BY['R11']['kind']=='all';assert {'LIST01','DRAG01'}==set(c['node']['id'] for c in BY['R11']['children'])
 assert BY['M03']['kind']=='all';assert BY['CAT00']['kind']=='decision'
def test_atomic_requirement_is_explicit():assert BY['R01']['instance_scope']=='per_atomic_requirement'
def test_candidate_unknown_never_declared_verified():
 for n in NODES:
  if n.get('assessment_axis'):
   unknown=[c['node'] for c in n['children'] if c['answer']=='No verificado'];assert len(unknown)==1;assert unknown[0]['evaluation_status']=='NOT_VERIFIED'
def test_adoption_axes_complete_per_candidate():
 for n in NODES:
  if n.get('adoption_contract'):
   axes={c.get('assessment_axis') for c in flatten(n)}
   assert {'PLATFORM','LICENSE','SECURITY','ACCESS','COST'}<=axes
   assert n['adoption_contract']['identity_fields']==['component_id','requirement_id','candidate_source','candidate_version']
def test_registry_preserved_and_disposition_visible():
 assert len({s['id'] for s in INV['skills']})==82
 assert all(s.get('disposition_reason') and s['human_scope_approval']=='PENDING' for s in INV['skills'])
def test_registry_node_links_resolve():
 for s in INV['skills']:
  assert all(id in DB for id in s['proposed_decision_nodes'])
def test_criterion_map_resolves():
 for row in json.loads((P/'criterion-map.json').read_text()):
  assert row['rule'] in RULES
  assert all(id in DB for id in row['definition_nodes'])
def test_rules_are_typed_and_source_sections_explicit():
 for r in RULES.values():
  assert r['category'] and r['source_section'] and r['criterion']
  if r['skill']:
   assert len(r['source_commit'])==40 and r['source_commit'] in r['source_url']
  else:assert r['category']=='router-policy'
def test_specialized_routes_block_instead_of_forcing_web():
 for id in ['S05','S06','S10']:assert 'BLOCKED' in BY[id]['proposal_status']
def test_html_contains_the_actual_canonical_data():
 soup=BeautifulSoup((P/'index.html').read_text(),'html.parser')
 assert json.loads(soup.find(id='source-data').string)==SRC
 assert json.loads(soup.find(id='inventory-data').string)==INV
 assert json.loads(soup.find(id='rule-data').string)==RULES
 assert not soup.select('script[src]') and not soup.select('link[rel="stylesheet"]')
def test_shared_definitions_not_separate_manual_copies():
 for id in ['E03','E04','E05','E07']:
  n=DB[id]['children'][0]['node'];assert n['kind']=='instance' and n['template_ref']=='F00'
 for n in DEFS:
  if n.get('adoption_contract'):assert n['children'][0]['node']['template_ref']=='ADOPT'

@pytest.mark.parametrize('mutation', ['autoapproval','missing-skill','foreign-candidate','audit-writes','lost-review','unknown-rule'])
def test_negative_mutations_are_rejected(mutation):
 m=copy.deepcopy(MODEL);i=copy.deepcopy(INV);b={n['id']:n for n in flatten(m['root'])}
 if mutation=='autoapproval':m['root']['gate']['status']='APPROVED'
 elif mutation=='missing-skill':i['skills'].pop()
 elif mutation=='foreign-candidate':b['R05__ADOPT_LICENSE']['candidate_key']='R03'
 elif mutation=='audit-writes':b['E05__D01']['write_policy']='MAY_WRITE'
 elif mutation=='lost-review':b['D00']['children']=[x for x in b['D00']['children'] if x['node']['id']!='D10']
 elif mutation=='unknown-rule':b['ART01']['rule_ids']=['invented-rule']
 with pytest.raises(AssertionError):verify(m,i)

def test_cyclic_template_rejected():
 s=copy.deepcopy(SRC);s['templates']['ADOPT']['children']=[{'answer':'bad','node':{'id':'bad','kind':'instance','template_ref':'ADOPT','prefix':'bad'}}]
 with pytest.raises(ValueError,match='cyclic template'):expand_model(s)

def test_missing_template_rejected():
 s=copy.deepcopy(SRC);s['root']={'id':'bad','kind':'instance','template_ref':'missing','prefix':''}
 with pytest.raises(ValueError,match='missing template'):expand_model(s)
