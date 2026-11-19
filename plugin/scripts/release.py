"""Prepare deterministic distribution copies. Never uploads, edits sources or rehashes a drifting baseline."""
from __future__ import annotations
import sys
sys.dont_write_bytecode=True
import argparse,hashlib,json,re,tempfile,zipfile,os
from pathlib import Path

def need(ok,message):
    if not ok:raise ValueError(message)
def sha(data):return hashlib.sha256(data).hexdigest()
def encoded(data):return (json.dumps(data,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode()
def version_tuple(text):
    need(isinstance(text,str) and re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)',text),'VERSION_REQUIRES_STABLE_SEMVER')
    return tuple(map(int,text.split('.')))

def prepare_release(package_root:Path,version:str,output:Path,retained_assets:dict|None=None)->dict:
    root=Path(package_root).resolve();out=Path(output).absolute();retained=retained_assets or {}
    need(not out.exists() and not out.is_symlink(),'DESTINATION_EXISTS')
    need(not out.resolve().is_relative_to(root),'DESTINATION_INSIDE_PACKAGE')
    manifest=json.loads((root/'plugin.json').read_text());overlay=json.loads((root/'.codex-plugin/plugin.json').read_text())
    need(version_tuple(version)>version_tuple(manifest['version']),'VERSION_MUST_INCREASE')
    need(manifest['name']==overlay['name'],'MANIFEST_IDENTITY_MISMATCH')
    inter=manifest['extensions']['com.openai']['interface']
    need(inter==overlay['interface'],'MANIFEST_PRESENTATION_MISMATCH')
    base=root/'skills/design-tree/references/tree-v0.4';lock=json.loads((base.parent/'baseline-lock.json').read_text())
    for relative,h in lock.items():
        p=base/relative
        need(p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(base.resolve()) and sha(p.read_bytes())==h,'BASELINE_DRIFT:'+relative)
    oldhash=json.loads((root/'PACKAGE-HASHES.json').read_text())
    for name,record in retained.items():
        need(isinstance(name,str) and name.startswith('assets/') and '..' not in Path(name).parts and isinstance(record,dict),'RETAINED_ASSET_INVALID')
        need(record.get('sha256')==oldhash.get(name) and re.fullmatch('[a-f0-9]{64}',record.get('sha256','')),'RETAINED_ASSET_HASH_MISMATCH')
        need(not (root/name).exists(),'RETAINED_ASSET_ALREADY_LOCAL')
    files={}
    allowed_roots={'skills','scripts','tests','docs','evidence','assets','.codex-plugin'}
    allowed_files={'plugin.json','README.md','NOTICE.md','AGENTS.md','CHANGELOG.md','PACKAGE-HASHES.json'}
    for p in sorted(root.rglob('*')):
        relative=p.relative_to(root);parts=relative.parts
        if any(x in ('.git','__pycache__','.pytest_cache','.superpowers') for x in parts):continue
        need(not p.is_symlink(),'UNSAFE_SYMLINK:'+str(relative))
        if not p.is_file():continue
        rel=relative.as_posix()
        need((len(parts)>1 and parts[0] in allowed_roots) or rel in allowed_files,'UNSAFE_PACKAGE_FILE:'+rel)
        need(not (p.name.startswith('.env') or p.suffix in ('.sqlite','.db','.xlsx') or p.name in ('ledger.json','files.json','credentials.json')),'UNSAFE_PRIVATE_OR_CATALOG_FILE:'+rel)
        need(p.stat().st_size<=16*1024*1024,'PACKAGE_FILE_TOO_LARGE:'+rel)
        files[rel]=p.read_bytes()
    for key in ('logo','logoDark','composerIcon','composerIconDark'):
        rel=inter.get(key)
        if not rel:continue
        need(isinstance(rel,str) and not Path(rel).is_absolute() and '..' not in Path(rel).parts,'UNSAFE_ASSET_PATH')
        rel=Path(rel).as_posix()
        need(rel in files or rel in retained,'RETAINED_ASSET_REQUIRED:'+rel)
    manifest['version']=version;overlay['version']=version
    files['plugin.json']=encoded(manifest)
    # Plugin Creator regenerates this compatibility projection. Preserve the
    # observed field order and ASCII escaping so its delivered bytes match the
    # package lock. Read-back is still mandatory if server behavior changes.
    overlay['interface']=json.loads(files['plugin.json'])['extensions']['com.openai']['interface']
    files['.codex-plugin/plugin.json']=(json.dumps(overlay,ensure_ascii=True,indent=2)+'\n').encode()
    files.pop('PACKAGE-HASHES.json',None)
    hashes={name:sha(data) for name,data in sorted(files.items())};hashes.update({name:r['sha256'] for name,r in retained.items()})
    files['PACKAGE-HASHES.json']=encoded(hashes)
    # Every byte in the overlay is hashed. Omitted binaries are explicit backend-retained inputs.
    out.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.'+out.name,dir=out.parent);os.close(fd)
    try:
        with zipfile.ZipFile(tmp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for name,data in sorted(files.items()):
                info=zipfile.ZipInfo(manifest['name']+'/'+name,date_time=(2020,1,1,0,0,0));info.create_system=3;info.external_attr=0o100644<<16;info.compress_type=zipfile.ZIP_DEFLATED
                z.writestr(info,data)
        with zipfile.ZipFile(tmp) as z:need(z.testzip() is None,'ZIP_CRC_FAILURE')
        need(not out.exists(),'DESTINATION_EXISTS');Path(tmp).rename(out)
    finally:
        if Path(tmp).exists():Path(tmp).unlink()
    return {'version':version,'archive':str(out),'sha256':sha(out.read_bytes()),'delivered_files':len(files),
            'mode':'GUARDED_OVERLAY' if retained else 'FULL_PACKAGE','retained_assets':retained,
            'local_binary_validation':'NOT_CHECKED' if retained else 'INCLUDED',
            'publication':'NOT_RUN','source_modified':False}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('prepare');q.add_argument('--version',required=True);q.add_argument('--output',type=Path,required=True);q.add_argument('--package-root',type=Path,default=Path(__file__).resolve().parents[1]);q.add_argument('--retained-assets',type=Path)
    a=p.parse_args(argv);retained=json.loads(a.retained_assets.read_text()) if a.retained_assets else None
    return prepare_release(a.package_root,a.version,a.output,retained)
if __name__=='__main__':
    try:print(json.dumps(main(),ensure_ascii=False,indent=2))
    except (OSError,ValueError,KeyError,TypeError) as e:print(json.dumps({'status':'BLOCKED','error':str(e)}),file=sys.stderr);sys.exit(2)
