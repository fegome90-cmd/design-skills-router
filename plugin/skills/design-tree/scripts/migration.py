"""Explicit portable export, inspection and conservative schema migration.

No network. New bundles publish by rename only after validation, never in place.
"""
from __future__ import annotations
import sys
sys.dont_write_bytecode=True
import copy,hashlib,json,os,shutil,tempfile
from pathlib import Path
from contracts import canonical_hash
SUPPORTED={'design-tree-ledger/0.1','design-tree-ledger/0.2','design-tree-ledger/0.3'}

def need(condition,message):
    if not condition:raise ValueError(message)

def read_json(p):
    need(p.is_file() and not p.is_symlink() and p.stat().st_size<=16*1024*1024,'BUNDLE_FILE_INVALID')
    return json.loads(p.read_text(encoding='utf-8'))

def write_json(p,data):
    with p.open('x',encoding='utf-8') as f:
        json.dump(data,f,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())

def evidence_files(state):
    files={}
    def walk(value):
        if isinstance(value,dict):
            if isinstance(value.get('path'),str) and isinstance(value.get('sha256'),str):
                path,h=value['path'],value['sha256']
                need(path not in files or files[path]==h,'EVIDENCE_PATH_HAS_MULTIPLE_VERSIONS')
                files[path]=h
            for k,v in value.items():
                if k!='artifact_paths':walk(v)
        elif isinstance(value,list):
            for v in value:walk(v)
    walk(state);return files

def safe_file(root,relative):
    need(isinstance(relative,str) and not Path(relative).is_absolute() and '..' not in Path(relative).parts,'RESUME_EVIDENCE_PATH_INVALID')
    p=root/relative;cur=root
    for part in Path(relative).parts:
        cur=cur/part;need(not cur.is_symlink(),'BUNDLE_SYMLINK_FORBIDDEN')
    need(p.resolve().is_relative_to(root.resolve()),'RESUME_EVIDENCE_PATH_ESCAPE')
    need(p.is_file() and p.stat().st_size<=16*1024*1024,'RESUME_EVIDENCE_FILE_INVALID');return p

def inspect_portable_bundle(bundle):
    b=Path(bundle).resolve();s=read_json(b/'ledger.json')
    need(isinstance(s,dict),'STATE_OBJECT_REQUIRED')
    integrity=s.pop('integrity',None)
    need(integrity==canonical_hash(s),'STATE_INTEGRITY_MISMATCH')
    need(s.get('schema') in SUPPORTED,'UNSUPPORTED_LEDGER_SCHEMA')
    need(all(isinstance(s.get(k),dict) for k in ('records','structures','sources','candidates')) and isinstance(s.get('history'),list),'PARTIAL_STATE_REJECTED')
    mapping=read_json(b/'files.json');expected=evidence_files(s)
    need(isinstance(mapping,dict) and set(mapping)==set(expected),'RESUME_EVIDENCE_MAP_MISMATCH')
    paths={}
    for original,relative in mapping.items():
        f=safe_file(b,relative);need(hashlib.sha256(f.read_bytes()).hexdigest()==expected[original],'RESUME_EVIDENCE_DRIFT');paths[original]=str(f)
    return {'schema':s['schema'],'state':s,'files':expected,'paths':paths}

def export_bundle(state,output):
    out=Path(output);need(not out.exists(),'EXPORT_DESTINATION_EXISTS')
    expected=evidence_files(state);paths=state.get('artifact_paths',{})
    # Resolve and check every source before creating even the staging directory.
    data={}
    for original,h in expected.items():
        p=Path(paths.get(original,original));need(p.is_file() and not p.is_symlink() and p.stat().st_size<=16*1024*1024,'EXPORT_EVIDENCE_MISSING')
        value=p.read_bytes();need(hashlib.sha256(value).hexdigest()==h,'EXPORT_EVIDENCE_DRIFT');data[h]=value
    out.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.'+out.name+'-',dir=out.parent))
    try:
        (stage/'evidence').mkdir()
        for h,value in sorted(data.items()):(stage/'evidence'/h).write_bytes(value)
        copied=copy.deepcopy(state);copied.pop('integrity',None);copied['integrity']=canonical_hash(copied)
        write_json(stage/'ledger.json',copied)
        write_json(stage/'files.json',{p:'evidence/'+h for p,h in sorted(expected.items())})
        inspect_portable_bundle(stage)
        need(not out.exists(),'EXPORT_DESTINATION_EXISTS')
        stage.rename(out)
    finally:
        if stage.exists():shutil.rmtree(stage)
    return {'export_dir':str(out),'portable_evidence':len(expected),'resume_requires_path_rebinding':True}

def upgrade_bundle(router,bundle,output=None,dry_run=False):
    info=inspect_portable_bundle(bundle);old=info['state']
    need(info['schema'] in ('design-tree-ledger/0.1','design-tree-ledger/0.2'),'UPGRADE_ACCEPTS_0_1_OR_0_2_ONLY')
    need(old.get('tree_hash')==router.tree_hash and old.get('inventory_hash')==router.inventory_hash,'BASELINE_MISMATCH')
    report={'from_schema':info['schema'],'to_schema':'design-tree-ledger/0.3','default_level':'manual','new_approvals':0,
            'historic_approvals':sum(r.get('status')=='APPROVED' for r in old['records'].values()),'reopen':'ALL_DECISIONS_NEW_CONTRACT','original_unchanged':True,'legacy_verification_promoted':False}
    if dry_run:return report
    need(output is not None,'OUTPUT_REQUIRED');need(not Path(output).exists(),'EXPORT_DESTINATION_EXISTS')
    new=router.new_state(old['project_id'],old['medium'],old['mode'],old['scope'])
    new['sources']=copy.deepcopy(old['sources'])
    for source in new['sources'].values():source['explicit_invocation_required']=None;source['invocation_policy_verified']=False
    new['legacy_snapshot']=copy.deepcopy(old);new['artifact_paths']=info['paths']
    new['history'].append({'event':'explicit_schema_upgrade','report':report})
    export_bundle(new,output)
    return {**report,'output':str(output)}
