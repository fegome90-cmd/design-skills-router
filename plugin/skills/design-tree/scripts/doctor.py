"""Read-only local diagnostic. Run with Python 3.10+; never repairs inputs."""
from __future__ import annotations
import sys
sys.dont_write_bytecode=True
import argparse,json
from pathlib import Path
from diagnostics import inspect_package,inspect_session,inspect_bundle

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package-root',type=Path,default=Path(__file__).resolve().parents[3]);p.add_argument('--format',choices=['text','json'],default='text')
    g=p.add_mutually_exclusive_group();g.add_argument('--state',type=Path);g.add_argument('--bundle',type=Path)
    a=p.parse_args(argv)
    try:
        r=inspect_session(a.package_root,a.state) if a.state else inspect_bundle(a.package_root,a.bundle) if a.bundle else inspect_package(a.package_root)
        if a.format=='json':print(json.dumps(r,ensure_ascii=False,indent=2))
        else:
            print('Design Skills Router · doctor ·',r.get('version','unknown'))
            for k,v in r['scopes'].items():print(k+': '+v)
            for f in r['findings']:print(f"{f['severity']} {f['code']} {f['location']}: {f['detail']}\n  → {f['next_action']}")
            if 'session' in r:print(json.dumps(r['session'],ensure_ascii=False,indent=2))
            print('Sin autorreparación. Integridad no demuestra autenticidad ni calidad de diseño.')
        return r['exit_code']
    except Exception as e:
        print(json.dumps({'schema':'design-tree-doctor/1','exit_code':3,'error':'INTERNAL_DIAGNOSTIC_ERROR','detail':str(e)},ensure_ascii=False));return 3
if __name__=='__main__':sys.exit(main())
