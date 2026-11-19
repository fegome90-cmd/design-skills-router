"""Pure assistance policy. Delegation never authenticates a human or executes tools."""
from __future__ import annotations
LEVELS={'manual','guided','phase_auto'}
PHASE_STATES={'PLANNED','ACTIVE','BLOCKED','AWAITING_HUMAN','ACCEPTED','STALE'}
ALLOWED_ACTIONS={'analyze','compare','draft','test','edit_sandbox'}

def validate_assistance(grant:dict,phase_map:dict)->list[dict]:
    issues=[]
    def err(detail):issues.append({'location':'assistance_grant','detail':detail})
    if not isinstance(grant,dict):return [{'location':'assistance_grant','detail':'Grant must be an object'}]
    if grant.get('level') not in LEVELS:err('Unsupported assistance level')
    for k in ('id','scope_id','phase_map_hash','stop_at','message_ref','quote'):
        if not isinstance(grant.get(k),str) or not grant[k].strip():err('Missing '+k)
    if type(grant.get('revision')) is not int or grant.get('revision',0)<1:err('Positive integer revision required')
    if not isinstance(grant.get('allowed_actions'),list) or not set(grant.get('allowed_actions',[]))<=ALLOWED_ACTIONS:err('Action outside helper delegation boundary')
    if not isinstance(grant.get('reserved_decisions'),list):err('Reserved decisions list required')
    ids={p.get('id') for p in phase_map.get('phases',[]) if isinstance(p,dict)} if isinstance(phase_map,dict) else set()
    if grant.get('stop_at') not in ids:err('Unknown phase stop point')
    return issues

def assistance_action(state:dict,node:dict,action:str)->dict:
    result={'allowed':False,'basis':'none','stop_reason':None,'required_gate':'node','external_tool_authorization':False}
    if action not in ('delegate','analyze','compare','draft','test','edit_sandbox'):
        result.update(stop_reason='HUMAN_OR_EXTERNAL_AUTHORIZATION_REQUIRED');return result
    level=state.get('assistance_level','manual')
    if level=='manual':result['stop_reason']='MANUAL_DECISION_REQUIRED';return result
    gid=state.get('active_grant_id');g=state.get('grants',{}).get(gid,{})
    if not gid or g.get('status')!='ACTIVE' or g.get('level')!=level:
        result['stop_reason']='ACTIVE_DELEGATION_REQUIRED';return result
    pid=state.get('active_phase_id');p=state.get('phases',{}).get(pid,{})
    if p.get('status')!='ACTIVE':result.update(stop_reason='PHASE_GATE_REQUIRED',required_gate='phase');return result
    if node.get('id') not in p.get('node_instance_ids',[]):result['stop_reason']='OUTSIDE_PHASE';return result
    if node.get('reserved') or node.get('id') in g.get('reserved_decisions',[]) or node.get('definition_id') in g.get('reserved_decisions',[]):
        result['stop_reason']='RESERVED_DECISION';return result
    if action!='delegate' and action not in g.get('allowed_actions',[]):result['stop_reason']='ACTION_NOT_DELEGATED';return result
    result.update(allowed=True,basis='active_delegation',stop_reason=None,required_gate='phase');return result
