"""Small typed relationship evaluator. No I/O, eval, installers or source execution."""
from __future__ import annotations
import hashlib,json,re
TYPES={'delegates_to','requires_skill','routes_to','optional_companion','uses_resource'}
SCOPES={'reference','product','preparation','verification','host'}

def canonical_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()

def evaluate_condition(predicates: list, facts: dict) -> str:
    if not isinstance(predicates,list) or not isinstance(facts,dict):raise ValueError('CONDITION_INVALID')
    results=[]
    for p in predicates:
        if not isinstance(p,dict) or p.get('op') not in ('eq','in','exists') or not isinstance(p.get('fact'),str):raise ValueError('CONDITION_OPERATOR_INVALID')
        if p['op']=='in' and not isinstance(p.get('value'),list):raise ValueError('CONDITION_IN_REQUIRES_LIST')
        f=facts.get(p['fact'])
        if not isinstance(f,dict) or f.get('state')=='UNKNOWN' or not f.get('evidence_refs'):
            results.append('UNKNOWN');continue
        if f.get('state')=='ABSENT':results.append('FALSE');continue
        if f.get('state')!='PRESENT' or 'value' not in f:results.append('UNKNOWN');continue
        value=f['value']
        if p['op']=='exists':yes=True
        elif p['op']=='eq':yes=type(value) is type(p.get('value')) and value==p.get('value')
        else:yes=any(type(value) is type(v) and value==v for v in p['value'])
        results.append('TRUE' if yes else 'FALSE')
    # Strong Kleene conjunction. FALSE settles conjunction but never invents evidence.
    return 'FALSE' if 'FALSE' in results else 'UNKNOWN' if 'UNKNOWN' in results else 'TRUE'

def applies(relation,node):
    return node.get('id') in relation.get('applies_to',[]) or node.get('definition_id',node.get('id')) in relation.get('applies_to',[])

def validate_contracts(data:dict,nodes:dict,inventory:dict)->list[dict]:
    issues=[]
    def err(loc,msg):issues.append({'location':loc,'detail':msg})
    if not isinstance(data,dict) or data.get('schema')!='design-tree-contracts/0.2':return [{'location':'contracts','detail':'Unsupported contract schema'}]
    if not isinstance(data.get('relations'),list):return [{'location':'relations','detail':'Expected relation list'}]
    ids=set();graph={};validnodes=set(nodes)|{n.get('definition_id',n.get('id')) for n in nodes.values()}
    resources={x.get('id') for x in data.get('resources',[]) if isinstance(x,dict)}
    for r in data['relations']:
        if not isinstance(r,dict):err('relations','Invalid relation object');continue
        rid=r.get('id');loc=str(rid)
        if not isinstance(rid,str) or not rid or rid in ids:err(loc,'Duplicate or missing relation ID')
        ids.add(rid)
        if r.get('from_skill') not in inventory:err(loc,'Unknown source skill')
        target=r.get('target',{})
        if not isinstance(target,dict):err(loc,'Target must be an object');continue
        kind=target.get('kind');tid=target.get('id')
        if kind not in ('skill','resource') or tid not in (inventory if kind=='skill' else resources):err(loc,'Unknown typed relation target')
        if r.get('type') not in TYPES:err(loc,'Unknown relation type')
        if r.get('type')=='uses_resource' and kind!='resource':err(loc,'Resource is not a skill')
        if r.get('type')=='optional_companion' and r.get('required') is not False:err(loc,'Optional companion cannot be mandatory')
        if not isinstance(r.get('required'),bool):err(loc,'Required must be boolean')
        if r.get('scope') not in SCOPES:err(loc,'Invalid operation scope')
        if not isinstance(r.get('applies_to'),list) or not r['applies_to'] or set(r['applies_to'])-validnodes:err(loc,'Unknown node binding')
        src=r.get('source',{})
        if not isinstance(src,dict):err(loc,'Source must be an object');continue
        if not all(isinstance(src.get(k),str) and src[k] for k in ('url','commit','section')) or re.fullmatch(r'[a-f0-9]{40}',src.get('commit','')) is None:err(loc,'Pinned source and section required')
        if r.get('provenance') not in ('author','host','router_policy'):err(loc,'Provenance required')
        if r.get('evidence_status') not in ('SOURCE_REVIEWED','INDEXED_ONLY'):err(loc,'Evidence status required')
        try:evaluate_condition(r.get('when'),{})
        except (ValueError,TypeError) as e:err(loc,str(e))
        if r.get('required') and r.get('type') in ('delegates_to','requires_skill') and kind=='skill':graph.setdefault(r.get('from_skill'),set()).add(tid)
    visiting=set();done=set()
    def visit(x):
        if x in visiting:raise ValueError('Mandatory relationship cycle')
        if x in done:return
        visiting.add(x)
        for y in graph.get(x,[]):visit(y)
        visiting.remove(x);done.add(x)
    try:
        for x in graph:visit(x)
    except (ValueError,RecursionError) as e:err('relations',str(e))
    # Verification policy belongs to reviewed supplementary contracts, never
    # to the agent's reported result. Keep the immutable tree untouched.
    from verification import METHOD_SCOPE
    requirements=data.get('verification_requirements',[])
    if not isinstance(requirements,list):
        err('verification_requirements','Expected verification requirement list')
        requirements=[]
    check_ids=set()
    for req in requirements:
        if not isinstance(req,dict):err('verification_requirements','Invalid requirement object');continue
        cid=req.get('id');loc='verification_requirements:'+str(cid)
        if not isinstance(cid,str) or not cid or cid in check_ids:err(loc,'Duplicate or missing verification requirement ID')
        check_ids.add(cid)
        if req.get('required') is not True and req.get('required') is not False:err(loc,'Required must be boolean')
        if not isinstance(req.get('applies_to'),list) or not req['applies_to'] or set(req['applies_to'])-validnodes:err(loc,'Unknown verification node binding')
        if req.get('scope') not in ('helper','browser','device','host'):err(loc,'Invalid verification scope')
        methods=req.get('allowed_methods')
        if not isinstance(methods,list) or not methods or any(x not in METHOD_SCOPE or METHOD_SCOPE[x]!=req.get('scope') for x in methods):err(loc,'Incompatible verification method and scope')
        if req.get('allow_not_applicable') is not True and req.get('allow_not_applicable') is not False:err(loc,'N/A permission must be boolean')
        try:evaluate_condition(req.get('when'),{})
        except (ValueError,TypeError) as ex:err(loc,'Invalid verification condition: '+str(ex))
        source=req.get('source')
        if not isinstance(source,dict) or source.get('provenance') not in ('router_policy','author','host') or not isinstance(source.get('reason'),str) or not source['reason'].strip():err(loc,'Verification source and justification required')
    # An inventory pin has one owner. Supplementary contracts cannot override it.
    if not isinstance(data.get('source_reviews',{}),dict):err('source_reviews','Expected mapping');return issues
    for sid,review in data.get('source_reviews',{}).items():
        if sid not in inventory:err(sid,'Review for unknown skill');continue
        if not isinstance(review,dict):err(sid,'Source review must be an object');continue
        if review.get('commit')!=inventory[sid].get('candidate_commit'):err(sid,'Source pin override forbidden')
    return issues

def evaluate_contracts(node:dict,context:dict,contracts:dict)->dict:
    out={'relations':[],'obligations':[],'pending':[],'fact_ids':[]}
    selected=set(context.get('selected_relations',[]));operation=context.get('operation','reference')
    for r in sorted(contracts.get('relations',[]),key=lambda x:x['id']):
        if not applies(r,node):continue
        rid=r['id'];out['fact_ids']+= [p['fact'] for p in r['when']]
        if r['scope'] not in ('reference',operation):status='OUT_OF_OPERATION'
        elif r['type']=='optional_companion' and rid not in selected:status='OPTIONAL_NOT_SELECTED'
        else:status=evaluate_condition(r['when'],context.get('facts',{}))
        if status=='TRUE' and r['evidence_status']!='SOURCE_REVIEWED':status='UNKNOWN'
        obligation=(r.get('required') or rid in selected) and status=='TRUE'
        if obligation:out['obligations'].append(rid)
        if status=='UNKNOWN' and (r.get('required') or rid in selected):out['pending'].append(rid)
        out['relations'].append({'id':rid,'condition':status,'obligatory':bool(obligation),'target':r['target'],'source':r['source']})
    out['fact_ids']=sorted(set(out['fact_ids']));return out

def policy_hash(node:dict,rules:dict,contracts:dict)->str:
    # Only normative content enters the binding; review timestamps/comments do not.
    relations=[{k:v for k,v in r.items() if k not in ('comment','reviewed_at')} for r in contracts.get('relations',[]) if applies(r,node)]
    fields=('id','definition_id','kind','skills','rule_ids','requires','criterion','write_policy','candidate_key','terminal_status','proposal_status','adoption_contract')
    rule_content={rid:{k:v for k,v in rules[rid].items() if k not in ('comment','reviewed_at')} for rid in node.get('rule_ids',[])}
    resource_ids={r['target']['id'] for r in relations if r['target']['kind']=='resource'}
    resources=[{k:v for k,v in r.items() if k not in ('comment','reviewed_at')} for r in contracts.get('resources',[]) if r['id'] in resource_ids]
    checks=[{k:v for k,v in r.items() if k not in ('comment','reviewed_at')}
            for r in contracts.get('verification_requirements',[]) if applies(r,node)]
    return canonical_hash({'node':{k:node[k] for k in fields if k in node},'rules':rule_content,
                           'relations':relations,'resources':resources,'verification_requirements':checks,
                           'schema':contracts.get('schema')})
