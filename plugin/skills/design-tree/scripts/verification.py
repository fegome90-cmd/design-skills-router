"""Pure, policy-owned outcome checking; no file I/O, host execution or approvals."""
from __future__ import annotations
from datetime import datetime
from contracts import evaluate_condition

RESULTS={'PASS','FAIL','NOT_APPLICABLE','UNVERIFIED'}
METHOD_SCOPE={'STATIC_REVIEW':'helper','LOCAL_TEST':'helper',
              'BROWSER_OBSERVATION':'browser','DEVICE_OBSERVATION':'device',
              'HOST_OBSERVATION':'host'}

def _valid_time(value):
    if not isinstance(value,str) or not value.strip():return False
    try:
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        return parsed.tzinfo is not None and parsed.utcoffset() is not None
    except ValueError:return False

def validate_results(results:dict, requirements:list[dict], evidence_refs:set[str])->list[dict]:
    """Validate recorded check syntax and evidence references. Failures are valid findings.

    The authority to require a check belongs to requirements, never a result payload.
    The caller resolves evidence bytes; this function validates the exact ID set.
    """
    issues=[]
    def bad(code,id=None):issues.append({'code':code,'check_id':id})
    if not isinstance(requirements,list) or not isinstance(evidence_refs,set):return [{'code':'VALIDATION_INPUT_INVALID'}]
    if results is None:results={'schema':'design-tree-checks/1','checks':[]}
    if not isinstance(results,dict) or results.get('schema')!='design-tree-checks/1' or not isinstance(results.get('checks'),list):
        return [{'code':'RESULTS_SCHEMA_INVALID'}]
    expected={r['id']:r for r in requirements};found=set()
    for c in results['checks']:
        if not isinstance(c,dict):bad('CHECK_OBJECT_INVALID');continue
        cid=c.get('id')
        if not isinstance(cid,str) or not cid:bad('CHECK_ID_INVALID');continue
        if cid in found:bad('DUPLICATE_RESULT',cid);continue
        found.add(cid)
        req=expected.get(cid)
        if req is None:bad('UNKNOWN_RESULT',cid);continue
        if 'required' in c and (type(c['required']) is not bool or c['required'] is not req.get('required')):bad('REQUIRED_OVERRIDE_FORBIDDEN',cid)
        if not isinstance(c.get('result'),str) or c.get('result') not in RESULTS:bad('RESULT_INVALID',cid)
        method=c.get('method')
        if not isinstance(method,str) or method not in METHOD_SCOPE or method not in req.get('allowed_methods',[]):bad('METHOD_MISMATCH',cid)
        if c.get('scope') != req.get('scope') or (METHOD_SCOPE.get(method) if isinstance(method,str) else None)!=c.get('scope'):bad('SCOPE_MISMATCH',cid)
        env=c.get('environment')
        if not isinstance(env,dict) or not all(isinstance(env.get(k),str) and env[k].strip() for k in ('runtime','version','platform')):bad('ENVIRONMENT_INVALID',cid)
        if not _valid_time(c.get('observed_at')):bad('TIMESTAMP_INVALID',cid)
        refs=c.get('evidence_refs')
        if not isinstance(refs,list) or (c.get('result')!='UNVERIFIED' and not refs) or any(not isinstance(x,str) or not x.strip() for x in (refs or [])):
            bad('EVIDENCE_REQUIRED',cid)
        elif set(refs)-evidence_refs:bad('EVIDENCE_UNRESOLVED',cid)
        if c.get('result')=='NOT_APPLICABLE' and not (isinstance(c.get('reason'),str) and c['reason'].strip()):bad('REASON_REQUIRED',cid)
        if c.get('result') in ('FAIL','UNVERIFIED') and not (isinstance(c.get('reason'),str) and c['reason'].strip()):bad('REASON_REQUIRED',cid)
    for cid in expected.keys()-found:
        if expected[cid].get('required') is True:bad('MISSING_RESULT',cid)
    return issues

def evaluate_results(results:dict, requirements:list[dict], facts:dict)->dict:
    """Evaluate applicability and outcome independently; cannot authorize an action."""
    checks={c.get('id'):c for c in (results or {}).get('checks',[]) if isinstance(c,dict)}
    out={'blocking_ids':[],'satisfied_ids':[],'not_applicable_ids':[],
         'unverified_ids':[],'failed_ids':[],'optional_failed_ids':[],'unknown_applicability_ids':[]}
    for req in requirements:
        cid=req['id'];required=req['required'];c=checks.get(cid)
        applicable=evaluate_condition(req['when'],facts)
        result=c.get('result') if c else None
        if result=='FAIL':out['failed_ids'].append(cid)
        if result=='UNVERIFIED' or result is None:out['unverified_ids'].append(cid)
        if applicable=='UNKNOWN':
            out['unknown_applicability_ids'].append(cid)
            if required:out['blocking_ids'].append(cid)
            continue
        if applicable=='FALSE':
            # A known false predicate is not an unearned success. N/A can be
            # explicitly recorded only when policy permits and gives reason.
            if result=='NOT_APPLICABLE' and req.get('allow_not_applicable') and c.get('reason','').strip():
                out['not_applicable_ids'].append(cid)
            elif result is not None:
                if required:out['blocking_ids'].append(cid)
            else:
                out['not_applicable_ids'].append(cid)
            continue
        if result=='PASS':out['satisfied_ids'].append(cid)
        elif required:out['blocking_ids'].append(cid)
        if result=='FAIL' and not required:out['optional_failed_ids'].append(cid)
    return {k:sorted(set(v)) for k,v in out.items()}
