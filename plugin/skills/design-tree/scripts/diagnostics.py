"""Read-only diagnostics. Hash integrity is not authenticity or human identity."""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True
import hashlib, json
from pathlib import Path

MAX_BYTES = 16 * 1024 * 1024
MANUAL = 'skills/design-tree/references/MAINTENANCE.md'

def finding(code, severity, scope, location, detail, next_action):
    return dict(code=code,severity=severity,scope=scope,location=str(location),detail=detail,
                next_action=next_action,manual_ref=MANUAL+'#diagnostico')

def read_json(path, findings, scope='package'):
    try:
        if path.is_symlink(): raise ValueError('symbolic link')
        if path.stat().st_size > MAX_BYTES: raise ValueError('file exceeds 16 MiB')
        value=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(value,dict):
            findings.append(finding('INVALID_JSON_TYPE','BLOCK',scope,path,'Expected JSON object','Restaurar el tipo de documento; no convertirlo por inferencia.'))
            return None
        return value
    except (OSError,ValueError,UnicodeError) as e:
        findings.append(finding('INVALID_JSON','BLOCK',scope,path,str(e),'Recuperar la fuente correcta; no regenerar huellas para esconder el error.'))
        return None

def contained(root, relative):
    if not isinstance(relative,str) or not relative or Path(relative).is_absolute(): return None
    p=root/relative
    try:
        if not p.resolve().is_relative_to(root.resolve()):return None
        # Inspect every existing component, not just the final one.
        part=root
        for name in Path(relative).parts:
            if name == '..': return None
            part=part/name
            if part.is_symlink(): return None
        return p
    except OSError:return None

def new_report():
    return {'schema':'design-tree-doctor/1','scopes':{'package':'NOT_CHECKED','model_coverage':'NOT_CHECKED','session':'NOT_CHECKED','host_validation':'NOT_CHECKED'},
            'findings':[],'limits':['Local consistency only; human receipts are not authenticated.','No remote source freshness, visual QA or host/LLM behavior checked.']}

def finish(report):
    f=report['findings'];report['exit_code']=2 if any(x['severity']=='BLOCK' for x in f) else 1 if any(x['severity']=='WARN' for x in f) else 0
    return report

def inspect_package(package_root: Path) -> dict:
    root=Path(package_root).resolve();r=new_report();f=r['findings']
    r['package_root']=str(root)
    m=read_json(root/'plugin.json',f);overlay=read_json(root/'.codex-plugin/plugin.json',f)
    lock=read_json(root/'PACKAGE-HASHES.json',f)
    for p in root.rglob('*'):
        if '.git' in p.relative_to(root).parts:continue
        if p.is_symlink():f.append(finding('SYMLINK_FORBIDDEN','BLOCK','package',p,'Unexpected symbolic link','Eliminar el enlace de la copia de distribución, no su destino.'))
    if isinstance(m,dict):
        r['version']=m.get('version');r['name']=m.get('name')
        extensions=m.get('extensions',{});ext=extensions.get('com.openai',{}) if isinstance(extensions,dict) else None
        inter=ext.get('interface',{}) if isinstance(ext,dict) else None
        if not isinstance(inter,dict):
            f.append(finding('MANIFEST_SCHEMA','BLOCK','package','plugin.json','OpenAI metadata must be objects','Restaurar el tipo del manifiesto.'))
            ext={};inter={}
        if m.get('$schema')!='https://agent-plugins.org/schemas/1.0.0/plugin.schema.json':
            f.append(finding('MANIFEST_SCHEMA','BLOCK','package','plugin.json','Unrecognized portable schema','Restaurar el manifiesto canónico.'))
        if isinstance(overlay,dict):
            fields=['name','version','description','author','keywords']
            if any(m.get(k)!=overlay.get(k) for k in fields) or inter!=overlay.get('interface',{}):
                f.append(finding('MANIFEST_DIVERGENCE','BLOCK','package','.codex-plugin/plugin.json','Root is authoritative; compatibility metadata differs','Sincronizar los campos equivalentes en la copia de release.'))
        for k,v in {**{k:inter[k] for k in ('logo','logoDark','composerIcon','composerIconDark') if k in inter},'onboardingSkill':ext.get('onboardingSkill')}.items():
            if v is None:continue
            p=contained(root,v)
            if p is None:f.append(finding('PATH_ESCAPE','BLOCK','package',k,'Path escapes package or traverses a symlink','Usar una ruta relativa contenida.'))
            elif not p.is_file():f.append(finding('FILE_MISSING','BLOCK','package',v,'Referenced file missing','Recuperar el archivo del release actual; no sustituir un icono.'))
    if isinstance(lock,dict):
        for rel,h in lock.items():
            p=contained(root,rel)
            if p is None:f.append(finding('PATH_ESCAPE','BLOCK','package',rel,'Unsafe hash entry','Corregir el manifiesto desde una fuente revisada.'));continue
            if not p.is_file():
                f.append(finding('FILE_MISSING','BLOCK','package',rel,'Hash entry file is absent','Recuperar archivo.'));continue
            if p.stat().st_size>MAX_BYTES:
                f.append(finding('FILE_TOO_LARGE','BLOCK','package',rel,'File too large to inspect safely','Revisar el tamaño fuera del doctor.'));continue
            if hashlib.sha256(p.read_bytes()).hexdigest()!=h:
                f.append(finding('HASH_MISMATCH','BLOCK','package',rel,'Bytes differ from package lock','Auditar el cambio; preparar nuevo release sólo tras verificarlo.'))
        for p in root.rglob('*'):
            rel=p.relative_to(root).as_posix()
            if p.is_file() and not p.is_symlink() and not any(x in p.parts for x in ('.git','__pycache__')) and rel!='PACKAGE-HASHES.json' and rel not in lock:
                f.append(finding('UNTRACKED_PACKAGE_FILE','BLOCK','package',rel,'File absent from package hash manifest','Incluir intencionalmente en release o excluir de distribución.'))
    base=root/'skills/design-tree/references/tree-v0.4';bl=read_json(base.parent/'baseline-lock.json',f)
    if isinstance(bl,dict):
        for rel,h in bl.items():
            p=contained(base,rel)
            if p is None or not p.is_file() or p.stat().st_size>MAX_BYTES or hashlib.sha256(p.read_bytes()).hexdigest()!=h:
                f.append(finding('BASELINE_DRIFT','BLOCK','package',rel,'Immutable v0.4 differs or is absent','Restaurar baseline, no rehash.'))
    tree=read_json(base/'tree.json',f);rules=read_json(base/'rules.json',f);inventory=read_json(base/'skill-inventory.json',f)
    if isinstance(tree,dict) and isinstance(rules,dict) and isinstance(inventory,dict):
        try:
            from tree_model import expand_model,flatten
            ns=list(flatten(expand_model(tree)['root']));ids=[n['id'] for n in ns];skills=[s['id'] for s in inventory['skills']]
            if len(ids)!=len(set(ids)) or len(skills)!=len(set(skills)):raise ValueError('Duplicate node or skill IDs')
            for n in ns:
                if n['kind']=='decision' and len(n.get('children',[]))<2:raise ValueError('Decision with fewer than two answers: '+n['id'])
                for key,expected in [('skills',set(skills)),('rule_ids',set(rules)),('requires',set(ids))]:
                    if set(n.get(key,[]))-expected:raise ValueError('Dangling '+key+' at '+n['id'])
            cp=root/'skills/design-tree/references/contracts.json'
            if cp.is_file():
                from contracts import validate_contracts
                c=read_json(cp,f)
                if c is not None:
                    for issue in validate_contracts(c,{n['id']:n for n in ns},{s['id']:s for s in inventory['skills']}):
                        f.append(finding('CONTRACT_INVALID','BLOCK','model_coverage',issue.get('location','contracts'),issue['detail'],'Corregir contrato suplementario, conservando baseline.'))
            r['model']={'inventory_count':len(skills),'expanded_nodes':len(ns),'semantic_completeness':'PARTIAL','skill_execution':'NOT_CHECKED'}
            if cp.is_file() and isinstance(c,dict):
                reviews=list(c.get('source_reviews',{}).values())
                r['model']['source_review_counts']={status:sum(x.get('status')==status for x in reviews) for status in sorted({x.get('status','UNKNOWN') for x in reviews})}
                r['model']['relationship_count']=len(c.get('relations',[]))
                r['model']['verification_requirement_count']=len(c.get('verification_requirements',[]))
            r['scopes']['model_coverage']='STRUCTURAL_CHECKS_ONLY'
        except (ValueError,KeyError,TypeError,AttributeError,RecursionError,ImportError) as e:
            f.append(finding('MODEL_INVALID','BLOCK','model_coverage',base,str(e),'Revisar IDs y referencias; restaurar baseline si fue alterado.'))
    r['scopes']['package']='BLOCKED' if any(x['scope']=='package' and x['severity']=='BLOCK' for x in f) else 'CHECKED'
    return finish(r)

def inspect_session(package_root: Path, state_path: Path) -> dict:
    r=inspect_package(package_root);f=r['findings'];p=Path(state_path)
    if p.with_suffix(p.suffix+'.lock').exists():
        f.append(finding('STATE_LOCK_PRESENT','WARN','session',p,'Another writer or stale lock may exist','Comprobar al propietario; no eliminar el lock automáticamente.'))
    if r['scopes']['package']=='BLOCKED':
        r['scopes']['session']='NOT_CHECKED';return finish(r)
    try:
        from runner import Router,load_state
        router=Router(package_root);s=load_state(p);router.check_state(s)
        invalid=[nid for nid,rec in s['records'].items() if rec.get('status') in ('APPROVED','RATIFIED_IN_PHASE','DECIDED_DELEGATED') and not router.record_current(s,nid)]
        for nid in invalid:f.append(finding('STATE_RECORD_STALE','BLOCK','session',nid,'Decision no longer meets its full contract','Revisar evidencia/contexto y volver a presentar lo afectado.'))
        r['session']=router.status(s);r['scopes']['session']='CHECKED'
    except (ValueError,OSError,KeyError,TypeError,AttributeError,ImportError) as e:
        f.append(finding('STATE_INVALID','BLOCK','session',p,str(e),'Usar una copia íntegra o la migración explícita; no recalcular el hash.'));r['scopes']['session']='BLOCKED'
    return finish(r)

def inspect_bundle(package_root: Path, bundle_path: Path) -> dict:
    r=inspect_package(package_root);f=r['findings'];b=Path(bundle_path)
    if r['scopes']['package']=='BLOCKED':return finish(r)
    try:
        from migration import inspect_portable_bundle
        data=inspect_portable_bundle(b)
        r['bundle']={'schema':data['schema'],'evidence_count':len(data['files'])};r['scopes']['session']='BUNDLE_INTEGRITY_CHECKED'
    except (ValueError,OSError,KeyError,TypeError,AttributeError,ImportError) as e:
        f.append(finding('BUNDLE_INVALID','BLOCK','session',b,str(e),'Recuperar bundle completo; usar upgrade-state sólo para formato antiguo válido.'));r['scopes']['session']='BLOCKED'
    return finish(r)
