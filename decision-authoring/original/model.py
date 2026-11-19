"""Expand shared decision definitions into a true single-parent tree for rendering/testing.
This is NOT an agent runtime, an approval authority or a dependency installer.
"""
import copy

def expand_model(source):
    definitions = {}
    def index(n):
        if n['kind'] != 'instance':
            if n['id'] in definitions: raise ValueError('duplicate definition: '+n['id'])
            definitions[n['id']] = n
            for c in n.get('children', []): index(c['node'])
    index(source['root'])
    for n in source.get('templates', {}).values(): index(n)
    gate=source.get('default_gate', {'status':'PENDING'})
    def expand(n, prefix='', context=None, chain=()):
        context = context or {}
        if n['kind'] == 'instance':
            ref=n['template_ref']
            if ref in chain: raise ValueError('cyclic template: '+ref)
            if ref not in definitions: raise ValueError('missing template: '+ref)
            ctx=dict(context)
            for k in ('context_mode','write_policy'):
                if k in n:ctx[k]=n[k]
            if 'candidate_key' in n:ctx['candidate_key']=prefix+n['candidate_key']
            return expand(definitions[ref],prefix+n.get('prefix',''),ctx,chain+(ref,))
        result={k:copy.deepcopy(v) for k,v in n.items() if k!='children'}
        result['definition_id']=n.get('definition_id',n['id']);result['id']=prefix+n['id']
        result['requires']=[prefix+r for r in n.get('requires',[])]
        if 'candidate_key' in result:result['candidate_key']=prefix+result['candidate_key']
        result.update(context);result['gate']=copy.deepcopy(n.get('gate',gate));result['human_review']='PENDING'
        result['children']=[{'answer':c['answer'],'node':expand(c['node'],prefix,context,chain)} for c in n.get('children',[])]
        return result
    result=copy.deepcopy(source);result['root']=expand(source['root']);return result

def flatten(n):
    yield n
    for c in n.get('children',[]): yield from flatten(c['node'])
