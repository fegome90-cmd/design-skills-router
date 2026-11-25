"""Assemble the traceability map from the verified source release and board."""
import argparse
import ast
from collections import defaultdict
from functools import cache
import hashlib
import json
from pathlib import Path
import re
import sys

from view import render

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / 'plugin'
LIB = SRC/'skills/design-tree/scripts'
sys.path.insert(0, str(LIB))
from tree_model import expand_model, flatten


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


@cache
def content(path):
    return (SRC/path).read_text(encoding='utf-8')


@cache
def parsed(path):
    return json.loads(content(path))


def resolve(path, pointer):
    obj = parsed(path)
    for part in pointer[1:].split('/') if pointer else ():
        part = part.replace('~1','/').replace('~0','~')
        obj = obj[int(part)] if isinstance(obj,list) else obj[part]
    return obj


@cache
def py_symbols(path):
    tree=ast.parse(content(path))
    nodes={x.name:x for x in tree.body if isinstance(x,(ast.FunctionDef,ast.ClassDef))}
    for cls in tree.body:
        if isinstance(cls,ast.ClassDef):
            nodes.update({cls.name+'.'+x.name:x for x in cls.body if isinstance(x,ast.FunctionDef)})
    return nodes


def excerpt(path, line, end=None):
    return '\n'.join(content(path).splitlines()[line-1:min(end or line+7,line+13)])[:1600]


def file_id(path):
    return 'file-'+re.sub('[^a-zA-Z0-9]+','-',path).strip('-').lower()


runtime=read(HERE/'runtime.json')
context=read(HERE/'context.json')
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir', type=Path,
                    help='Read the v1.2 board and write the map in this directory')
args = parser.parse_args()
if args.output_dir is None:
    parser.error('usa tools/build.py o --output-dir: release/ guarda la v1.3 dorada, que no se reescribe')
DEST = args.output_dir
from extract_tree import extract
data = extract()
hashes=read(SRC/'PACKAGE-HASHES.json')
assert all(hashlib.sha256((SRC/p).read_bytes()).hexdigest()==h for p,h in hashes.items())
nodes={}
edges=[]
index={}
canonical={}
def add(n):
    key=(n['path'],n['symbol'])
    if key in index:
        canonical[n['id']]=index[key]
        return
    assert n['id'] not in nodes,n['id']
    path=n['path']
    if path.endswith('.py'):
        sym=py_symbols(path)[n['symbol']]
        n['line']=sym.lineno
        n['source']=excerpt(path,sym.lineno,sym.end_lineno)
    elif 'line' in n:
        n['source']=excerpt(path,n['line'])
    elif n['symbol'].startswith('/'):
        obj=resolve(path,n['symbol'])
        if 'source' not in n:n['source']=json.dumps(obj,ensure_ascii=False,indent=2)[:1200]
    index[key]=n['id']
    nodes[n['id']]=n


def link(a,b,kind,label):
    edges.append(dict(from_id=a,to=b,kind=kind,condition=label))


groups={'host':'Entrada del plugin','visor':'Visor del plugin','mantenimiento':'Mantenimiento','contratos':'Contratos y evidencia'}
for n in runtime['nodes']:
    n['group']='Código del flujo'
    add(n)
for ident,symbol,title,summary in [
 ('py-runner-pending','Router.frontier','Decisiones pendientes en la ruta activa','Devuelve los nodos activos que aún carecen de un registro vigente.'),
 ('py-runner-skills','Router.skills_for','Referencias asociadas al nodo','Une las skills declaradas en el nodo y las que aportan sus reglas si están en el inventario.'),
 ('py-runner-outcomes','Router.check_outcomes','Comprobar la evidencia de una propuesta','Reúne requisitos y referencias, valida los resultados y evalúa su efecto según los hechos del expediente.'),
]:
    add(dict(id=ident,symbol=symbol,path='skills/design-tree/scripts/runner.py',title=title,summary=summary,group='Código del flujo'))
for n in context['nodes']:
    n['group']=groups[n['group']]
    # At /root the decision itself owns the JSON pointer.
    if n['id']=='ctx-tree-data':
        canonical[n['id']]='Q00'
        continue
    if n['id']=='ctx-tree-rules':
        canonical[n['id']]='rule-scope'
        continue
    add(n)
for source in (runtime,context):
    for edge in source['edges']:
        link(edge['from'],edge['to'],'relación documentada',edge['condition'])

tree_path=next(n['file'] for n in data['nodes'])
aliases=defaultdict(list)
for item in flatten(expand_model(parsed(tree_path))['root']):
    if item['id']!=item['definition_id']:
        aliases[item['definition_id']].append(item['id'])
kinds={'decision':'Decisiones','all':'Ramas obligatorias','result':'Resultados','instance':'Instancias de plantilla'}
for n in data['nodes']:
    raw=resolve(n['file'],n['pointer'])
    assert raw['id']==n['id']
    # Print the local declaration only; child declarations have separate deep links.
    source=json.dumps({k:v for k,v in raw.items() if k!='children'},ensure_ascii=False,indent=2)
    add(dict(id=n['id'],path=n['file'],symbol=n['pointer'],source=source,title=n['title'],group=kinds[n['kind']],summary=n['summary'],aliases=aliases[n['id']]))
for r in data['rules']:
    add(dict(id='rule-'+r['id'],path=r['file'],symbol=r['pointer'],title=r['id'],group='Reglas',summary=r['criterion']))
for r in data['contracts']['relations']:
    add(dict(id='contract-'+r['id'],path=r['file'],symbol=r['pointer'],title=r['id'],group='Relaciones contractuales',summary=r['type']+' · '+r['from_skill']+' → '+r['target']['id']))
for n in data['nodes']:
    for rule in n.get('rules',[]):
        link(n['id'],'rule-'+rule,'regla','Criterio aplicable a esta declaración.')
    for contract in n.get('contracts',[]):
        link(n['id'],'contract-'+contract,'contrato','Relación suplementaria declarada para esta definición.')
for e in data['edges']+data['prerequisites']:
    label={'alternative':'Alternativa','all_branch':'Rama obligatoria','template_ref':'Expande plantilla','requires':'Prerrequisito'}[e['kind']]
    link(e['source'],e['target'],e['kind'],label+' · '+e['label'])

for a,b,label in [
 ('ctx-cli-start','py-runner-start','Entrada real para ejecutar los comandos documentados.'),
 ('ctx-cli-propose','py-runner-propose','Implementación del comando propose.'),
 ('ctx-cli-receipts','py-runner-human-receipt','Comprueba el tipo y la huella del recibo aportado.'),
 ('ctx-cli-phase','py-runner-prepare-phase','Prepara la propuesta de cierre de fase.'),
 ('ctx-cli-source','py-runner-record-source','Registra la consulta de fuente.'),
 ('ctx-cli-persist','py-ledger-export','Exporta el expediente portable.'),
 ('py-runner-show-node','Q00','Consulta de ejemplo: node Q00 crea el paquete de la decisión raíz.'),
 ('py-runner-frontier','Q00','La evaluación de alcance parte de la raíz del árbol expandido.'),
 ('ctx-viewer-data','Q00','El visor contiene una copia del modelo con la misma raíz.'),
 ('ctx-tree-inventory','py-runner-inventory','El runner examina las disposiciones del inventario.'),
 ('ctx-contracts-json','py-contracts-evaluate','El runner evalúa las relaciones aplicables a cada nodo.'),
 ('py-runner-validate-response','py-runner-outcomes','Comprueba la evidencia de los resultados.'),
 ('py-runner-status','py-runner-pending','Identifica las decisiones pendientes.'),
 ('py-runner-pending','py-runner-frontier','Consulta la ruta activa.'),
 ('py-runner-show-node','py-runner-skills','Resuelve referencias del nodo presentado.'),
 ('py-runner-outcomes','ctx-verification-validate','Valida los resultados entregados con la propuesta.'),
 ('py-runner-outcomes','ctx-verification-results','Evalúa los resultados según los hechos disponibles.'),
 ('ctx-assist-doc','py-assistance-gate','La política distingue el nivel y las decisiones reservadas.'),
 ('ctx-maint','ctx-doctor','Inspección del paquete y del estado.'),
]:link(a,b,'trazabilidad',label)
for n in data['nodes']:
    if n['id']=='Q00': continue
    if n['kind']=='instance':
        link(n['id'],'py-model-expand','implementación','El expansor sustituye esta instancia por su plantilla y aplica el prefijo.')
    else:
        link(n['id'],'py-runner-show-node','implementación','Router.packet consulta esta definición a través del ID de su ocurrencia.')
        if n['kind'] in ('all','decision'):
            label='todas las ramas' if n['kind']=='all' else 'la alternativa seleccionada'
            link(n['id'],'py-runner-frontier','implementación','Con registro vigente, Router.active recorre '+label+'.')
# Files are first-class vertices with paths and whole-file digests.
descriptions={s['file']:s['summary'] for s in data['sources']}
for path in sorted({n['path'] for n in nodes.values()}):
    fid=file_id(path)
    symbols=[n['id'] for n in nodes.values() if n['path']==path]
    nodes[fid]=dict(id=fid,title=Path(path).name,path=path,symbol='Archivo completo',group='Archivos del plugin',summary=descriptions.get(path,'Archivo del release con puntos de entrada y referencias identificados en este mapa.'),source='SHA-256 del archivo\n'+hashes[path])
    for nid in symbols:
        link(nid,fid,'ubicación','Definido en este archivo del release.')
for p,desc in [('tree.json','Carga la raíz y las plantillas.'),('rules.json','Carga el catálogo de reglas.'),('skill-inventory.json','Carga el inventario de referencias.')]:
    link('py-router-load',file_id(str(Path(tree_path).with_name(p))),'lectura',desc)
link('py-router-load',file_id('skills/design-tree/references/contracts.json'),'lectura','Carga los contratos suplementarios.')
unique={}
for e in edges:
    a=canonical.get(e['from_id'],e['from_id']);b=canonical.get(e['to'],e['to'])
    assert a in nodes and b in nodes,(a,b)
    if a!=b:unique[a,b,e['kind'],e['condition']]={'from':a,'to':b,'kind':e['kind'],'condition':e['condition']}
graph={'plugin':{'name':'design-skills-router','version':'0.3.1','release':'pluginrel_6af336537e808191831d72799b60bf4b','tree_version':'0.4'},'root':'Q00','nodes':list(nodes.values()),'edges':list(unique.values())}
(DEST/'design-router-mapa-fuentes.json').write_text(json.dumps(graph,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
board=(DEST/'design-router-pizarra-v1.2.html').read_text(encoding='utf-8')
board=board.replace('Design Skills Router · Selección mínima v1.2','Design Skills Router · Mapa del plugin v1.3')
(DEST/'design-router-pizarra-v1.3.html').write_text(render(board,graph),encoding='utf-8')
print(len(nodes),'nodes',len(unique),'edges',sum(n['group']=='Archivos del plugin' for n in nodes.values()),'files')
