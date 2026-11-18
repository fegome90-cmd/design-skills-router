'use strict';
// Read-only design review. No approval storage, plugin control or remote execution.
const source=JSON.parse(document.getElementById('source-data').textContent);
const rules=JSON.parse(document.getElementById('rule-data').textContent);
const inventory=JSON.parse(document.getElementById('inventory-data').textContent);
const defs={};
function index(n){if(n.kind==='instance')return;if(defs[n.id])throw Error('Definición duplicada: '+n.id);defs[n.id]=n;for(const c of n.children||[])index(c.node);}
index(source.root);Object.values(source.templates||{}).forEach(index);
function expand(n,prefix='',ctx={},chain=[]){
 if(n.kind==='instance'){
  const ref=n.template_ref;if(!defs[ref]||chain.includes(ref))throw Error('Referencia inválida: '+ref);
  const next={...ctx};for(const k of ['context_mode','write_policy'])if(n[k])next[k]=n[k];
  if(n.candidate_key)next.candidate_key=prefix+n.candidate_key;
  return expand(defs[ref],prefix+(n.prefix||''),next,[...chain,ref]);
 }
 const r={...n,id:prefix+n.id,definition_id:n.definition_id||n.id,requires:(n.requires||[]).map(x=>prefix+x),gate:{...(n.gate||source.default_gate)},...ctx};
 if(n.candidate_key&&!ctx.candidate_key)r.candidate_key=prefix+n.candidate_key;
 r.children=(n.children||[]).map(c=>({answer:c.answer,node:expand(c.node,prefix,ctx,chain)}));return r;
}
const root=expand(source.root), nodes={},parents={};
function collect(n,parent=null){if(nodes[n.id])throw Error('Instancia duplicada: '+n.id);nodes[n.id]=n;parents[n.id]=parent;for(const c of n.children)collect(c.node,n.id);}
collect(root);
const $=id=>document.getElementById(id);
const el=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
let current=root.id;
const kindNames={decision:'DECISIÓN · elegir respuesta',all:'COBERTURA · revisar todas',result:'RESULTADO PROPUESTO'};
function pathFor(id){const p=[];while(id){p.unshift(id);id=parents[id];}return p;}
function button(text,fn){const b=el('button',text);b.type='button';b.addEventListener('click',fn);return b;}
function navigate(id,push=true){
 if(!nodes[id]){$('notice').textContent='No se encontró el nodo. No se cambió la rama.';return;}
 current=id;$('notice').textContent='Rama '+id+'. '+(nodes[id].children.length?nodes[id].children.length+' respuestas o dominios visibles.':'Resultado propuesto; revisa la ficha.');
 if(push&&location.hash!=='#'+encodeURIComponent(id)){location.hash=encodeURIComponent(id);return;}
 render();
}
function textBlock(parent,label,value){if(!value)return;const p=el('p');p.append(el('strong',label+': '),document.createTextNode(value));parent.append(p);}
function inspect(id,focus=true){
 const n=nodes[id];if(!n)return;const box=$('inspect');box.hidden=false;box.replaceChildren();
 const h=el('h3',n.id+' · '+n.title);h.tabIndex=-1;box.append(h);
 textBlock(box,'Estado','PENDIENTE. Confirmar el diseño de esta pregunta no aprueba una decisión de un proyecto.');
 textBlock(box,'Criterio',n.criterion||n.reason);textBlock(box,'Registro',n.output);textBlock(box,'Evidencia exigida',n.evidence_required||'Fuentes consultadas, alternativa elegida y descartes justificados; comprobaciones aplicables y sus límites.');
 textBlock(box,'Alcance',n.context_mode||'Proyecto nuevo / contexto por confirmar');
 if(n.candidate_key)textBlock(box,'Evaluación vinculada',n.candidate_key+' · componente + requisito + fuente + versión. No se reutiliza la aprobación de otra pieza.');
 if(n.write_policy==='NO_WRITES')textBlock(box,'Permisos','Sólo lectura: esta rama de auditoría no autoriza editar.');
 if(n.terminal_status||n.proposal_status?.startsWith('BLOCKED'))textBlock(box,'Bloqueo',n.terminal_status||n.proposal_status);
 const s=el('p','Skills propuestas: ');for(const [i,sk] of (n.skills||[]).entries()){if(i)s.append(document.createTextNode(', '));const rec=inventory.skills.find(x=>x.id===sk);const a=el('a',sk.split('/').pop());if(rec){a.href=rec.source_url;a.target='_blank';a.rel='noopener noreferrer';}s.append(a);}if(n.skills?.length)box.append(s);
 const refs=el('div');refs.append(el('h4','Criterios y procedencia'));
 for(const rid of n.rule_ids||[]){const r=rules[rid];if(!r)continue;const d=el('div',undefined,'rule');d.append(el('strong',r.category+' · '+rid));textBlock(d,'Sección',r.source_section);textBlock(d,'Criterio',r.criterion);textBlock(d,'Adaptación',r.adaptation);if(r.source_url){const a=el('a','Consultar fuente fijada');a.href=r.source_url;a.target='_blank';a.rel='noopener noreferrer';d.append(a);}refs.append(d);}
 box.append(refs);
 if(n.children.length)box.append(button('Explorar respuestas de '+id,()=>navigate(id)));
 if(focus){h.focus({preventScroll:true});box.scrollIntoView({block:'nearest'});}
}
// Simple SVG projection of a tree, two branch levels. SVG is a view, never the source.
const NS='http://www.w3.org/2000/svg';
function svgEl(tag,attrs={},text){const e=document.createElementNS(NS,tag);for(const [k,v]of Object.entries(attrs))e.setAttribute(k,String(v));if(text!==undefined)e.textContent=text;return e;}
function wrap(text,width=34){const words=text.split(/\s+/),lines=[];let line='';for(let word of words){while(word.length>width){if(line){lines.push(line);line='';}lines.push(word.slice(0,width));word=word.slice(width);}if((line+' '+word).trim().length>width){lines.push(line);line=word;}else line=(line+' '+word).trim();}if(line)lines.push(line);return lines;}
function drawGraph(n){
 const svg=svgEl('svg',{role:'img','aria-label':'Árbol de '+n.id+'; los enlaces exploran ramas'}),entries=[],edges=[];
 function layout(node,depth,y,answer=''){
  const lines=wrap(node.title),h=48+lines.length*17;const visible=depth<1?node.children:[];
  let cursor=y,children=[];
  for(const c of visible){const child=layout(c.node,depth+1,cursor,c.answer);children.push(child);cursor=child.bottom+38;}
  const span=Math.max(h,cursor-y-38),top=depth===0?y:y+(span-h)/2;const item={node,depth,x:depth*370+18,y:top,h,lines,answer,bottom:y+span};entries.push(item);children.forEach(child=>edges.push([item,child]));return item;
 }
 const first=layout(n,0,48);const maxDepth=Math.max(...entries.map(e=>e.depth));const w=(maxDepth+1)*370,h=Math.max(first.bottom+30,180);svg.setAttribute('viewBox',`0 0 ${w} ${h}`);svg.style.width=w+'px';svg.style.height=h+'px';
 const defsSvg=svgEl('defs');const marker=svgEl('marker',{id:'arrow',viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:5,markerHeight:5,orient:'auto-start-reverse'});marker.append(svgEl('path',{d:'M 0 0 L 10 5 L 0 10 z',fill:'#637f87'}));defsSvg.append(marker);svg.append(defsSvg);
 for(const [a,b]of edges){const x1=a.x+280,y1=a.y+a.h/2,x2=b.x,y2=b.y+b.h/2;svg.append(svgEl('path',{d:`M${x1},${y1} C${x1+45},${y1} ${x2-45},${y2} ${x2},${y2}`,fill:'none',stroke:'#637f87','stroke-width':1.2,'marker-end':'url(#arrow)'}));}
 for(const item of entries){const {node,x,y,h,lines}=item;const a=svgEl('a',{href:'#'+encodeURIComponent(node.id),'data-node':node.id,'aria-label':(node.children.length?'Explorar respuestas de ':'Ver resultado de ')+node.id});a.append(svgEl('title',{},node.title));a.append(svgEl('rect',{x,y,width:280,height:h,rx:7,fill:node.kind==='all'?'#eaf5f1':node.kind==='decision'?'#f5f4ff':'#fff',stroke:node.kind==='all'?'#3f796c':'#686095','stroke-width':1.3}));
  if(item.answer){const label=wrap(item.answer,36).slice(0,2);label.forEach((v,i)=>a.append(svgEl('text',{x:x+8,y:y-10-(label.length-1-i)*13,'font-size':10,fill:'#455c67'},v)));}
  a.append(svgEl('text',{x:x+12,y:y+18,'font-size':11,'font-weight':700,fill:'#2b635c'},node.id.length<32?node.id:node.definition_id+' · instancia'));
  lines.forEach((v,i)=>a.append(svgEl('text',{x:x+12,y:y+39+i*17,'font-size':12,fill:'#203746'},v)));
  a.append(svgEl('text',{x:x+12,y:y+h-10,'font-size':10,fill:'#526572'},node.children.length?(node.kind==='all'?'Revisar ':'Explorar ')+node.children.length+' ramas':'Ver ficha · propuesta'));
  a.addEventListener('click',e=>{e.preventDefault();navigate(node.id);});svg.append(a);
 }
 $('canvas').replaceChildren(svg);$('canvas').dataset.root=n.id;
}
function outline(n,depth=0,answer=''){
 const li=el('li');const detail=el('details');detail.dataset.node=n.id;if(depth===0)detail.open=true;
 const sum=el('summary');sum.style.setProperty('--depth',Math.min(depth,3));sum.append(el('span',n.id,'node-id'),document.createTextNode(' '+n.title));detail.append(sum);
 const content=el('div',undefined,'node-details');if(answer)content.append(el('p',answer,'answer'));content.append(el('p',kindNames[n.kind]||n.kind,'caption'));content.append(button('Ver ficha de '+n.id,()=>inspect(n.id)));if(n.children.length)content.append(button('Explorar respuestas de '+n.id,()=>navigate(n.id)));detail.append(content);
 if(n.children.length){const ul=el('ul');for(const c of n.children)ul.append(outline(c.node,depth+1,c.answer));detail.append(ul);}li.append(detail);return li;
}
function render(){const n=nodes[current];$('view').value=[...$('view').options].some(o=>o.value===current)?current:'';const h=$('branch-title');h.textContent=n.id+' · '+n.title;h.dataset.node=current;const bc=$('breadcrumbs');bc.replaceChildren();for(const id of pathFor(current)){bc.append(button(nodes[id].definition_id||id,()=>navigate(id)));}
 drawGraph(n);$('outline').replaceChildren(outline(n));$('inspect').hidden=true;$('branch-kind').textContent=kindNames[n.kind];$('up').disabled=!parents[current];h.focus({preventScroll:true});
 if(!n.children.length)inspect(current,false);
}
function renderInventory(){const box=$('inventory');const groups={};for(const s of inventory.skills)(groups[s.disposition]??=[]).push(s);for(const [kind,items]of Object.entries(groups)){const d=el('details');d.append(el('summary',`${kind} · ${items.length}`));for(const s of items){const row=el('div',undefined,'inventory-row');row.append(el('strong',s.id));textBlock(row,'Propuesta',s.disposition_reason);textBlock(row,'Confirmación','Pendiente; no equivale a admisión ni a ejecución.');textBlock(row,'Nodos',s.proposed_decision_nodes?.join(', ')||'GOV00 · revisión de disposición');const a=el('a','Fuente fijada');a.href=s.source_url;a.target='_blank';a.rel='noopener noreferrer';row.append(a);d.append(row);}box.append(d);}}
$('view').addEventListener('change',e=>navigate(e.target.value));$('root').addEventListener('click',()=>navigate(root.id));$('up').addEventListener('click',()=>{if(parents[current])navigate(parents[current]);});
$('expand').addEventListener('click',()=>{$('outline').querySelectorAll('details').forEach(d=>d.open=true);$('notice').textContent='Rama desplegada; el resto del árbol no se ha aprobado.';});
$('collapse').addEventListener('click',()=>{$('outline').querySelectorAll('details').forEach(d=>d.open=false);$('outline').querySelector('details').open=true;});
$('zoom').addEventListener('click',()=>{$('canvas').classList.toggle('compact');$('zoom').setAttribute('aria-pressed',String($('canvas').classList.contains('compact')));});
$('search-form').addEventListener('submit',e=>{e.preventDefault();navigate($('node-search').value.trim());});
$('inspect-current').addEventListener('click',()=>inspect(current));
window.addEventListener('hashchange',()=>{let id;try{id=decodeURIComponent(location.hash.slice(1));}catch{id='';}if(nodes[id])navigate(id,false);else $('notice').textContent='El enlace no corresponde a un nodo del árbol.';});
renderInventory();let initial;try{initial=decodeURIComponent(location.hash.slice(1));}catch{initial='';}navigate(nodes[initial]?initial:root.id,false);
