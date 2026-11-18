
(()=>{
'use strict';
const graph=JSON.parse(document.querySelector('#semanticDataset').textContent);
const idOf=graph.core_ids;
const skillById=new Map(graph.nodes.map(n=>[n.id,n]));
const edges=graph.edges;
const functionsBySkill=new Map((graph.skillFunctions||[]).map(f=>[f.skillId,f]));
const functionsByNode=new Map((graph.nodeFunctions||[]).map(f=>[f.id,f]));
const originalStageSelection=()=>typeof STATUS!=='undefined'?STATUS.selected:null;
const el=s=>document.querySelector(s);
const esc=s=>String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
const eXml=esc;
const ownerNames={G0:'Coordinación',G1:'Arte y dirección',G2:'Selección tipográfica',G3:'Escalas y microtipo',G4:'Color',G5:'Layout',G6:'Tokens y componentes',G7:'Movimiento y handoff'};
const relations={coordina:'Coordina',alimenta:'Alimenta',prerrequisito_condicional:'Prerrequisito condicional',apoya:'Apoya',consulta:'Consulta',verifica:'Verifica',delega_a:'Delega a',complementa:'Complementa',alternativa:'Alternativa',verificada_por:'Es verificada por',referencia_de_gobernanza:'Referencia de gobernanza',ruta_pendiente:'Ruta pendiente',catalogada_fuera_alcance:'Exclusión propuesta',riesgo_compatibilidad:'Riesgo de compatibilidad',requiere_aprobacion:'Requiere aprobación'};
const edgeColors={coordina:'#4956a0',alimenta:'#7666a3',prerrequisito_condicional:'#5d69af',apoya:'#a48573',consulta:'#7d61a2',verifica:'#b15e61',delega_a:'#a66a9d',complementa:'#7b708f',alternativa:'#9e7950',verificada_por:'#c07a70',ruta_pendiente:'#a4979e',catalogada_fuera_alcance:'#aaa0a0',referencia_de_gobernanza:'#6b7391',riesgo_compatibilidad:'#b45766',requiere_aprobacion:'#b4584e'};
const state={active:false,scope:'all',selected:idOf.G1,showPaused:false,showExcluded:false,onlyDocumented:false,rel:'all',zoom:0.82,oldSelected:'G0',visibleKeys:[],selectedEdge:null,lockSelection:false};
function abbrev(s,max=30){let p=String(s);return p.length<=max?p:p.slice(0,max-1)+'…'}
function wrapLines(s,max=33,limit=2){let arr=[],row='';for(const w of String(s||'').split(/\s+/)){if((row+' '+w).trim().length>max&&row){arr.push(row);row=w}else row=(row+' '+w).trim();}if(row)arr.push(row);return arr.slice(0,limit)}
function coreCode(n){return n.ownerCode||n.owners[0]||'G0'}
function previewLabel(n){return n.kind==='core'?(n.ownerCode+' · '+n.label):n.label}
function visible(n){if(n.status==='proposed-exclusion'&&!state.showExcluded)return false;if(n.status==='paused'&&!state.showPaused)return false;return true}
function allowed(e){if(state.onlyDocumented&&e.evidence!=='DOCUMENTED')return false;if(state.rel!=='all'&&state.rel!==e.relation)return false;return true}
function graphNeighbors(key){return edges.filter(e=>e.from===key||e.to===key).filter(allowed)}
function renderCard(n,x,y,w=320,h=89,desc='',count=null){let kind=n.kind==='core'?'core':n.kind;
 let role=n.ownerCode?'RECTORA / MY-SKILLS':n.status==='proposed-exclusion'?'EXCLUSIÓN PROPUESTA':n.status==='paused'?'RUTA BLOQUEADA':n.kind==='new_candidate'?'PROPUESTA NUEVA':'YA INVENTARIADA';
 let lines=wrapLines(desc||n.shortPurpose||n.inventoryEvidence||'',44,1);
 return `<g role="button" tabindex="0" data-skill-key="${esc(n.id)}" aria-label="Consultar relaciones de ${esc(n.label)}" class="skill-card ${esc(kind)} ${esc(n.status)} ${state.selected===n.id?'selected':''}"><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="12"/><text class="skill-owner" x="${x+16}" y="${y+18}">${esc(role)}</text><text class="skill-name" x="${x+16}" y="${y+42}">${esc(abbrev(n.label,w>340?38:31))}</text>${lines.length?`<text class="skill-desc" x="${x+16}" y="${y+65}">${esc(abbrev(lines[0],40))}</text>`:''}${count!=null?`<text class="skill-counter" x="${x+w-28}" y="${y+42}" text-anchor="middle">${count}</text>`:''}</g>`;
}
function pathBetween(a,b){let ax=a.x+a.w/2,ay=a.y+a.h/2,bx=b.x+b.w/2,by=b.y+b.h/2;
 if(Math.abs(ay-by)>Math.abs(ax-bx)) {ay=a.y+(by>ay?a.h:0);by=b.y+(ay>by?b.h:0);let m=(ay+by)/2;return `M${ax} ${ay} C${ax} ${m} ${bx} ${m} ${bx} ${by}`;}
 ax=a.x+(bx>ax?a.w:0);bx=b.x+(ax>bx?b.w:0);let m=(ax+bx)/2;return `M${ax} ${ay} C${m} ${ay} ${m} ${by} ${bx} ${by}`;
}
function drawEdge(e,pos,cross=false){let a=pos.get(e.from),b=pos.get(e.to);if(!a||!b||!allowed(e))return '';
 let p=pathBetween(a,b),active=state.selected===e.from||state.selected===e.to||state.selectedEdge===e.id;
 if(cross&&!active)return ''; // evita una telaraña ilegible en el plano general
 let c=edgeColors[e.relation]||'#7e7a87';
 return `<g><path d="${p}" stroke="${c}" class="skill-graph-edge ${e.evidence==='DOCUMENTED'?'documented':'proposed'} ${active?'active':''} ${cross?'cross':''}"/><path d="${p}" data-rel-edge="${esc(e.id)}" class="skill-edge-hit" role="button" tabindex="0" aria-label="Relación ${esc(relations[e.relation]||e.relation)} entre ${esc(skillById.get(e.from).label)} y ${esc(skillById.get(e.to).label)}"/></g>`;
}
function coreOverview(){
 const pos=new Map(),elements=[];let y0=72;
 pos.set(idOf.G0,{x:579,y:y0,w:344,h:101});
 elements.push(renderCard(skillById.get(idOf.G0),579,y0,344,101,'Define alcance y coordina especialistas'));
 for(let i=1;i<=7;i++){
   const g='G'+i,n=skillById.get(idOf[g]),col=(i-1)%4,row=Math.floor((i-1)/4),x=65+col*354,y=300+row*207;
   pos.set(n.id,{x,y,w:320,h:103});
   const count=edges.filter(e=>e.to===n.id&&e.from!==idOf.G0&&visible(skillById.get(e.from))&&allowed(e)).length;
   elements.push(renderCard(n,x,y,320,103,'Pulsa para explorar '+ownerNames[g],count));
 }
 const links=edges.filter(e=>e.evidence==='DOCUMENTED'&&e.relation==='coordina').map(e=>drawEdge(e,pos)).join('');
 let secondary=edges.filter(e=>['alimenta','prerrequisito_condicional'].includes(e.relation)).map(e=>drawEdge(e,pos,state.rel==='all')).join('');
 const note=`<text x="76" y="239" class="skill-group-title">G0 COORDINA · G1–G7 DECIDEN EN SU DOMINIO</text><path d="M70 251H1434" class="skill-group-rule"/><text x="76" y="760" class="skill-group-title">Selecciona una rectora para ver las skills conectadas; las relaciones cruzadas se destacan al seleccionar una ficha.</text>`;
 return {svg:links+secondary+elements.join('')+note,width:1500,height:815,positions:pos,keys:[...pos.keys()],shown:(links+secondary).match(/data-rel-edge=/g)?.length||0};
}
function focusGraph(owner){
 let core=skillById.get(idOf[owner]),pos=new Map(),cards=[],drawn=[];
 pos.set(core.id,{x:584,y:83,w:332,h:110});cards.push(renderCard(core,584,83,332,110,ownerNames[owner]));
 if(owner!=='G0'){
   const g=skillById.get(idOf.G0);pos.set(g.id,{x:68,y:91,w:280,h:88});cards.push(renderCard(g,68,91,280,88,'Coordina sin sustituir'));}
 const linked=edges.filter(e=>allowed(e)&&(e.from===core.id||e.to===core.id));
 const visibleItems=[...new Set(linked.map(e=>e.from===core.id?e.to:e.from))]
     .map(id=>skillById.get(id)).filter(n=>n&&n.id!==idOf.G0&&n.id!==core.id&&visible(n));
 // 3 categorías semánticas, no etapas secuenciales ni niveles de autoridad nuevos.
 const columns=[[],[],[]];
 for(const n of visibleItems){
    let ers=linked.filter(e=>e.from===n.id||e.to===n.id),rels=ers.map(e=>e.relation);
    let c=rels.some(k=>['verifica','delega_a','verificada_por'].includes(k))?2:
          rels.some(k=>['consulta','referencia_de_gobernanza'].includes(k))?1:0;
    columns[c].push(n);
 }
 for(const c of columns) c.sort((a,b)=>a.kind===b.kind?a.label.localeCompare(b.label):
   (a.kind==='core'?-1:b.kind==='core'?1:0));
 const labels=['CAPACIDAD Y COMPONENTES','CONSULTA Y GOBERNANZA','VERIFICACIÓN Y REVISIÓN'];
 let maxHeight=0;
 columns.forEach((list,c)=>{
   let x=51+c*494;
   cards.push(`<text class="skill-group-title" x="${x}" y="278">${labels[c]} · ${list.length}</text><path d="M${x} 294H${x+420}" class="skill-group-rule"/>`);
   list.forEach((n,i)=>{let y=315+i*111;
     pos.set(n.id,{x,y,w:420,h:89});cards.push(renderCard(n,x,y,420,89));maxHeight=Math.max(maxHeight,y+111);
   });
 });
 const mainLinks=linked.map(e=>drawEdge(e,pos)).join('');
 const cross=edges.filter(e=>!linked.includes(e)&&pos.has(e.from)&&pos.has(e.to)&&allowed(e)).map(e=>drawEdge(e,pos,true)).join('');
 let more=state.onlyDocumented?'Relaciones documentadas exclusivamente':'Relaciones propuestas y documentadas diferenciadas';
 const foot=`<text class="skill-group-title" x="54" y="${Math.max(470,maxHeight+28)}">${esc(more.toUpperCase())} · HAZ CLIC EN UNA SKILL PARA VER LOS ENLACES CRUZADOS</text>`;
 return {svg:mainLinks+cross+cards.join('')+foot,width:1500,height:Math.max(585,maxHeight+75),positions:pos,keys:[...pos.keys()],shown:linked.filter(e=>pos.has(e.from)&&pos.has(e.to)).length};
}
function nodeHint(e,n){const peer=skillById.get(e.from===n.id?e.to:e.from);return `${relations[e.relation]||e.relation}: ${peer?.label||'?'}`}
function inspectSkill(n){if(!n)return;const pick=el('#graphFunctionNode');if(pick)pick.value='';
 state.selected=n.id;state.selectedEdge=null;
 el('#inspectCode').textContent=(n.ownerCode||n.owners.join('·'))+' / GRAFO DE SKILLS';
 el('#inspectTitle').textContent=n.label;
 el('#inspectDesc').textContent=n.shortPurpose||n.inventoryEvidence||'Referencia del inventario del Design Skills Router.';
 el('#inspectStage').textContent=n.ownerCode?'Skill rectora '+n.ownerCode:'Relación propuesta con '+n.owners.join(', ');
 el('#inspectOwner').textContent=n.repo+' · '+(n.versionRef||'versión no fijada');
 el('#inspectKind').textContent=n.ownerCode?'my-skills · rectora':(n.kind==='new_candidate'?'candidata externa':n.kind==='own_specialist'?'skill propia complementaria':'inventariada');
 el('#inspectStatus').textContent=n.ownerCode?'RECTORA':'NO ADMITIDA POR ESTA VISTA';
 const src=el('#inspectSource');if(n.source&&/^https:\/\//.test(n.source)){src.href=n.source;src.classList.remove('hidden')}else src.classList.add('hidden');
 const outgoing=graphNeighbors(n.id).filter(e=>visible(skillById.get(e.from))&&visible(skillById.get(e.to)));
 const countDocs=outgoing.filter(e=>e.evidence==='DOCUMENTED').length;
 const f=functionsBySkill.get(n.id);
 const listItems=(values)=>Array.isArray(values)?values.map(x=>esc(x)).join(' · '):esc(values||'Sin especificación');
 const funcBlock=f?`<div class="functional-contract"><div class="inspect-label">Ficha funcional · FBS / IDEF0 (propuesta)</div><div class="inspect-value"><b>Función</b> ${esc(f.function)}</div><div class="inspect-value"><b>Entrada</b> ${listItems(f.input)}</div><div class="inspect-value"><b>Control</b> ${listItems(f.control)}</div><div class="inspect-value"><b>Salida</b> ${listItems(f.output)}</div><div class="inspect-value"><b>Mecanismo</b> ${listItems(f.mechanism)}</div><div class="inspect-value"><b>Evidencia</b> ${listItems(f.evidenceRequirement)}</div><div class="inspect-value"><b>Elegibilidad</b> ${esc(f.eligibility.status)} · sin permiso de ejecución</div></div>`:'';
 const restriction=n.routeConstraints&&n.routeConstraints.length?`<div class="inspect-label">Rutas bloqueadas ≠ capacidades bloqueadas</div><div class="inspect-value">${esc(n.routeConstraints.map(x=>x.id+': '+x.scope).join(' · '))}</div>`:'';
 const sources=`<div class="inspect-label">Fuente y trazabilidad</div><div class="inspect-value">${esc(n.versionRef)}${n.gitBlob?' · blob '+esc(n.gitBlob.slice(0,12)):''} · ${esc(n.license||'Licencia: revisar fuente original')}</div><div class="inspect-value">Dependencias: ${esc(n.dependencyVerification||'Por comprobar')}</div>`;

 let content=`<div class="inspect-label">Capacidad y procedencia</div><div class="inspect-value">${esc(n.shortPurpose||n.inventoryEvidence||'Catálogo de referencia.')}</div>`+
 `<div class="inspect-label">Activación o condición</div><div class="inspect-value">${esc(n.activation||'Solo cuando el encargo habilite este dominio y exista evidencia.')}</div>`+
 `<div class="inspect-label">Límite</div><div class="inspect-value">${esc(n.note||'Consultar la skill original y verificar el contrato de invocación.')}</div>`+
 `<div class="inspect-label">Relaciones directas (${outgoing.length})</div><div class="relation-counts"><span>Documentadas ${countDocs}</span><span>Propuestas ${outgoing.length-countDocs}</span></div>`+
 `<div class="relation-list">${outgoing.slice(0,28).map(e=>{
 const other=skillById.get(e.from===n.id?e.to:e.from);
 return `<button class="relation-btn" type="button" data-skill-related="${esc(other.id)}" data-related-edge="${esc(e.id)}"><b>${esc(relations[e.relation]||e.relation)}</b><span class="relation-badge ${e.evidence==='DOCUMENTED'?'documented':''}">${e.evidence==='DOCUMENTED'?'FUENTE DOCUMENTADA':'HIPÓTESIS'}</span><span>${esc(other.label)} · ${esc(abbrev(e.why||e.when||'',83))}</span></button>`}).join('')}</div>`;
 content=funcBlock+restriction+sources+content;
 if(outgoing.length>28)content+=`<p class="srchint">Mostrando 28 relaciones. Usa la búsqueda por skill o el filtro de dominio para explorar el resto.</p>`;
 content+=`<p class="srchint">Una relación propuesta no instala una skill, no crea una dependencia obligatoria y no autoriza ejecución.</p>`;
 el('#inspectExtra').hidden=false;el('#inspectExtra').innerHTML=content;
 el('#inspectExtra').querySelectorAll('[data-skill-related]').forEach(b=>b.addEventListener('click',()=>selectSkill(b.dataset.skillRelated,b.dataset.relatedEdge)));
 if(window.innerWidth<850&&!state.suppressMobileInspector){const panel=el('#inspector');panel.classList.add('show');el('#mobileInspect').setAttribute('aria-expanded','true');}
}
function inspectEdge(e){const pick=el('#graphFunctionNode');if(pick)pick.value='';const a=skillById.get(e.from),b=skillById.get(e.to);state.selectedEdge=e.id;
 el('#inspectCode').textContent='RELACIÓN / '+e.id;
 el('#inspectTitle').textContent=relations[e.relation]||e.relation;
 el('#inspectDesc').textContent=a.label+' → '+b.label;
 el('#inspectStage').textContent=e.when||'Condición: depende del encargo';
 el('#inspectOwner').textContent=e.evidence==='DOCUMENTED'?'Relación documentada en la fuente citada':'Relación propuesta para evaluación';
 el('#inspectKind').textContent='Arista semántica';el('#inspectStatus').textContent=e.evidence==='DOCUMENTED'?'DOCUMENTADA':'PROPUESTA';
 const src=el('#inspectSource');if(e.source&&/^https:\/\//.test(e.source)){src.href=e.source;src.classList.remove('hidden')}else src.classList.add('hidden');
 el('#inspectExtra').hidden=false;
 el('#inspectExtra').innerHTML=`<div class="inspect-label">Justificación</div><div class="inspect-value">${esc(e.why||'No registrada')}</div><div class="inspect-label">Condición</div><div class="inspect-value">${esc(e.when||'La aplicabilidad requiere revisión humana')}</div><div class="relation-list"><button class="relation-btn" data-skill-related="${esc(a.id)}">Ver origen: ${esc(a.label)}</button><button class="relation-btn" data-skill-related="${esc(b.id)}">Ver destino: ${esc(b.label)}</button></div>`;
 const refs=(e.sourceRefs||[]).map(s=>`<div class="inspect-value">${esc(s.role)}: <a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">SKILL.md / fuente fijada</a></div>`).join('');
 el('#inspectExtra').insertAdjacentHTML('beforeend',`<div class="inspect-label">Procedencia y límite de esta arista</div><div class="inspect-value">${e.originalDirectSourceMissing?'Solo fuentes de los extremos; sin prueba directa de la relación.':'Referencia directa documentada como fuente o hipótesis.'} · ${esc(e.eligibility?.status||'No verificado')}</div>${refs}`);
 el('#inspectExtra').querySelectorAll('[data-skill-related]').forEach(b=>b.addEventListener('click',()=>selectSkill(b.dataset.skillRelated)));
 if(window.innerWidth<850){el('#inspector').classList.add('show');} 
}
function inspectBoardFunction(key){
 const f=functionsByNode.get(key);if(!f)return;
 el('#inspectCode').textContent='NODO / '+f.id+' · PROPUESTA';
 el('#inspectTitle').textContent=f.title;
 el('#inspectDesc').textContent=f.function;
 el('#inspectStage').textContent='Capa '+f.stage+' · método '+f.modelMethod;
 el('#inspectOwner').textContent=f.owner+' · ficha experimental no ratificada';
 el('#inspectKind').textContent=f.kind;el('#inspectStatus').textContent='INVESTIGACIÓN';
 el('#inspectSource').classList.add('hidden');
 const row=(name,v)=>`<div class="inspect-label">${name}</div><div class="inspect-value">${esc((Array.isArray(v)?v:[v]).join(' · '))}</div>`;
 el('#inspectExtra').hidden=false;el('#inspectExtra').innerHTML=row('Función',f.function)+row('Entradas',f.inputs)+row('Controles',f.controls)+row('Mecanismos',f.mechanisms)+row('Salidas',f.outputs)+row('Evidencia requerida',f.evidenceRequirements)+row('Estado','Propuesta FBS/IDEF0; pendiente de aprobación');
 if(window.innerWidth<850)el('#inspector').classList.add('show');
}
function selectSkill(key,edgeId=null){let n=skillById.get(key);if(!n)return;
 if(n.ownerCode)state.scope=n.ownerCode;
 else if(!n.owners.includes(state.scope))state.scope=n.owners[0]||'G0';
 el('#graphOwner').value=state.scope;
 inspectSkill(n);state.selectedEdge=edgeId;redrawGraph();
}
// Para relaciones entre dos skills no rectoras, usar una lente bipartita.
// No inferimos dependencias por similitud de palabras: se muestran solo aristas registradas.
const CROSS_TYPES=new Set(['delega_a','complementa','alternativa','verificada_por','riesgo_compatibilidad','requiere_aprobacion']);
function crossRelationLayout(){
 const matches=edges.filter(e=>allowed(e)&&visible(skillById.get(e.from))&&visible(skillById.get(e.to))).filter(e=>state.scope==='all'||
   (skillById.get(e.from).owners||[]).includes(state.scope)||(skillById.get(e.to).owners||[]).includes(state.scope)||e.from===state.selected||e.to===state.selected);
 const sources=[...new Set(matches.map(e=>e.from))],targets=[...new Set(matches.map(e=>e.to))];
 const pos=new Map(),cards=[];
 cards.push(`<text class="skill-group-title" x="100" y="82">ORIGEN · ${sources.length} SKILLS</text><path d="M100 100H655" class="skill-group-rule"/>`);
 cards.push(`<text class="skill-group-title" x="840" y="82">DESTINO · ${targets.length} SKILLS</text><path d="M840 100H1400" class="skill-group-rule"/>`);
 sources.forEach((id,i)=>{const n=skillById.get(id),x=100,y=144+i*112;pos.set(id,{x,y,w:425,h:89});cards.push(renderCard(n,x,y,425,89));});
 targets.forEach((id,i)=>{const n=skillById.get(id);if(pos.has(id))return;const x=857,y=144+i*112;pos.set(id,{x,y,w:425,h:89});cards.push(renderCard(n,x,y,425,89));});
 const links=matches.map(e=>drawEdge(e,pos)).join('');
 const empty=matches.length?'':`<rect x="425" y="160" width="660" height="110" rx="11" class="skill-frame"/><text x="455" y="199" class="skill-name">No hay relaciones de este tipo para el dominio seleccionado.</text><text x="455" y="224" class="skill-desc">Prueba «Vista G0–G7» o cambia el filtro. No significa que la skill no tenga función.</text>`;
 return {svg:links+cards.join('')+empty,width:1500,height:Math.max(485,144+Math.max(sources.length,targets.length)*112+70),positions:pos,keys:[...pos.keys()],shown:matches.length};
}
function graphLayout(){if(CROSS_TYPES.has(state.rel)||(state.scope==='all'&&!['all','coordina','alimenta','prerrequisito_condicional'].includes(state.rel)))return crossRelationLayout();return state.scope==='all'?coreOverview():focusGraph(state.scope)}
function redrawGraph(){if(!state.active)return;
 let d=graphLayout(),svg=el('#semanticSvg');svg.setAttribute('viewBox',`0 0 ${d.width} ${d.height}`);svg.setAttribute('height',d.height);svg.setAttribute('width',d.width);svg.style.height=d.height+'px';
 svg.innerHTML=`<title>Relaciones semánticas entre skills del router</title><desc>Diagrama SVG local; exportación en formato nativo mxGraph/draw.io. G0 coordina; G1 a G7 gobiernan. Las relaciones propuestas no autorizan ejecución.</desc>${d.svg}`;
 state.visibleKeys=d.keys;
 svg.querySelectorAll('[data-skill-key]').forEach(g=>{g.addEventListener('click',()=>selectSkill(g.dataset.skillKey));g.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectSkill(g.dataset.skillKey)}})});
 svg.querySelectorAll('[data-rel-edge]').forEach(g=>{const open=()=>{let e=edges.find(x=>x.id===g.dataset.relEdge);if(e){inspectEdge(e);redrawGraph();}};g.addEventListener('click',open);g.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();open()}})});
 el('#semanticStat').textContent=`${d.keys.length} skills visibles · ${d.shown} enlaces dibujados · ${graph.counts.relations} relaciones inventariadas`;
 const small=el('#semanticCompactStat');if(small)small.textContent=`${d.keys.length} skills · ${d.shown} enlaces`; 
 scaleGraph();
}
function scaleGraph(){const h=el('#semanticSvg').getAttribute('height')|0,w=1500;const world=el('#semanticWorld');world.style.width=w*state.zoom+'px';world.style.height=h*state.zoom+'px';const svg=el('#semanticSvg');svg.style.transform=`scale(${state.zoom})`;el('#graphZoomPct').textContent=Math.round(state.zoom*100)+'%';}
function centerGraph(){const scroll=el('#semanticScroll');if(CROSS_TYPES.has(state.rel)){scroll.scrollLeft=0;return}const x=750*state.zoom;scroll.scrollLeft=Math.max(0,x-scroll.clientWidth/2)}
function graphFit(){let viewport=el('#semanticScroll').clientWidth;state.zoom=Math.max(.16,Math.min(.95,(viewport-24)/1500));scaleGraph();}
function showSemantic(){if(state.active)return;state.active=true;state.oldSelected=originalStageSelection()||'G0';if(window.innerWidth<850){el('#inspector').classList.remove('show');el('#mobileInspect').setAttribute('aria-expanded','false');}if(window.innerWidth<570)state.zoom=.74;el('.app').classList.add('semantic-active');el('#skillNetworkView').setAttribute('aria-pressed','true');el('#stageMapView').setAttribute('aria-pressed','false');el('#semanticPanel').removeAttribute('aria-hidden');
 el('#graphOwner').value=state.scope;state.suppressMobileInspector=true;inspectSkill(skillById.get(state.selected));state.suppressMobileInspector=false;redrawGraph();scaleGraph();centerGraph();}
function showStages(){if(!state.active)return;state.active=false;if(window.innerWidth<850){el('#inspector').classList.remove('show');el('#mobileInspect').setAttribute('aria-expanded','false');}el('.app').classList.remove('semantic-active');el('#skillNetworkView').setAttribute('aria-pressed','false');el('#stageMapView').setAttribute('aria-pressed','true');el('#semanticPanel').setAttribute('aria-hidden','true');
 if(typeof selectNode==='function') selectNode(state.oldSelected);
}
function triggerDownload(name,content,mime){const blob=new Blob([content],{type:mime});let url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1700)}
function buildGraphDrawio(){
 let types=['core','existing','new','paused','relations'];let layers=types.map(t=>`<mxCell id="layer_${t}" parent="0" value="${({core:'G0–G7 / Rectoras',existing:'Referencias de v0.4',new:'Candidatas nuevas',paused:'Pendientes y fuera de alcance',relations:'Relaciones tipadas'}[t])}"/>`).join('');
 let ns=[...graph.nodes];let positions=new Map();let buckets=Object.fromEntries(Object.keys(idOf).map(k=>[k,[]]));
 for(let n of ns){let g=n.ownerCode||n.owners[0]||'G0';if(!n.ownerCode)buckets[g].push(n)}
 let cells='';let idx=0;
 Object.entries(idOf).forEach(([g,key],column)=>{
   const x=80+column*353,y=65,core=skillById.get(key);positions.set(key,{x,y,w:302,h:76});
   cells+=`<mxCell id="n${idx++}" value="${eXml(g+' · '+core.label)}" style="rounded=1;arcSize=12;whiteSpace=wrap;fillColor=#e6e9fa;strokeColor=#5767b4;fontColor=#30375d;fontSize=15;fontStyle=1;" vertex="1" parent="layer_core"><mxGeometry x="${x}" y="${y}" width="302" height="76" as="geometry"/></mxCell>`;
   for(let i=0;i<buckets[g].length;i++){
      let n=buckets[g][i],v={x,y:190+i*81,w:302,h:62};positions.set(n.id,v);
      const out=n.status==='paused'||n.status==='proposed-exclusion';let color=out?'#e8e4e6':n.kind==='new_candidate'?'#fff0e5':'#fffaf3',border=out?'#aa929c':n.kind==='new_candidate'?'#bd775a':'#aca0aa';
      const layer=out?'paused':n.kind==='new_candidate'?'new':'existing';
      cells+=`<mxCell id="n${idx++}" value="${eXml(n.label)}" style="rounded=1;arcSize=6;whiteSpace=wrap;fillColor=${color};strokeColor=${border};fontColor=#30334a;fontSize=12;${n.kind==='new_candidate'?'dashed=1;':''}" vertex="1" parent="layer_${layer}"><mxGeometry x="${x}" y="${v.y}" width="${v.w}" height="${v.h}" as="geometry"/></mxCell>`;
   }
 });
 // We need graph cell id for each source/target. Above construction preserves iteration order: build map separately.
 let idMap=new Map(),counter=0;Object.entries(idOf).forEach(([g,key])=>{idMap.set(key,'n'+counter++);for(const n of buckets[g])idMap.set(n.id,'n'+counter++);});
 const links=edges.map((e,i)=>{let source=idMap.get(e.from),target=idMap.get(e.to);if(!source||!target)return'';
  const c=edgeColors[e.relation]||'#9094a7';return `<mxCell id="rel_${i+1}" value="${eXml(relations[e.relation]||e.relation)}" evidence="${esc(e.evidence)}" hypothesis="${e.eligibleForAutomaticRouting?'0':'1'}" style="edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;strokeColor=${c};strokeWidth=${e.evidence==='DOCUMENTED'?'1.9':'1.1'};fontColor=#5e5970;fontSize=10;endArrow=open;${e.evidence!=='DOCUMENTED'?'dashed=1;dashPattern=5 3;':''}" edge="1" parent="layer_relations" source="${source}" target="${target}"><mxGeometry relative="1" as="geometry"/></mxCell>`;}).join('');
 let xml=`<?xml version="1.0" encoding="UTF-8"?><mxfile host="app.diagrams.net" agent="ResearchSkillGraph" version="24.0" type="device"><diagram id="skills-v05" name="Relaciones entre skills"><mxGraphModel dx="1900" dy="1100" grid="1" gridSize="10" guides="1" tooltips="1" connect="0" arrows="1" fold="1" page="0" pageScale="1" shadow="0"><root><mxCell id="0"/><mxCell id="1" parent="0"/>${layers}${cells}${links}</root></mxGraphModel></diagram></mxfile>`;
 return xml;
}
function downloadGraphDrawio(){triggerDownload('design-router-relaciones-skills-v0.5.drawio',buildGraphDrawio(),'application/xml;charset=utf-8')}
function downloadGraphJson(){triggerDownload('router_skill_relations_v05.json',JSON.stringify(graph,null,2),'application/json;charset=utf-8')}
function searchSkills(q){let box=el('#graphSearchBox');q=q.trim().toLowerCase();if(!q){box.classList.remove('show');box.replaceChildren();return;}
 let hits=graph.nodes.filter(n=>[n.label,n.repo,n.provider,n.id].join(' ').toLowerCase().includes(q)).slice(0,11);
 box.replaceChildren();hits.forEach(n=>{let b=document.createElement('button');b.type='button';b.textContent=n.label+' · '+n.repo.split('/')[0];b.addEventListener('click',()=>{box.classList.remove('show');el('#graphSkillSearch').value='';selectSkill(n.id)});box.append(b)});
 if(!hits.length){let d=document.createElement('span');d.textContent='Sin coincidencias';d.style.padding='9px';box.append(d)}box.classList.add('show');
}
function init(){
 const optDrawer=el('.semantic-options');let prevMobile=window.innerWidth<=850;optDrawer.open=!prevMobile;
 window.addEventListener('resize',()=>{let mobile=window.innerWidth<=850;if(mobile!==prevMobile){optDrawer.open=!mobile;prevMobile=mobile;}});
 el('#skillNetworkView').addEventListener('click',showSemantic);el('#stageMapView').addEventListener('click',showStages);
 el('#stageButtons').addEventListener('click',()=>{if(state.active)showStages()},true);
 const select=el('#graphOwner');select.innerHTML='<option value="all">Vista G0–G7</option>'+Object.keys(idOf).map(k=>`<option value="${k}">${k} · ${esc(ownerNames[k])}</option>`).join('');
 select.addEventListener('change',()=>{state.scope=select.value;state.selected=idOf[state.scope]||idOf.G0;state.selectedEdge=null;state.suppressMobileInspector=true;inspectSkill(skillById.get(state.selected));state.suppressMobileInspector=false;redrawGraph();el('#semanticScroll').scrollTop=0;centerGraph()});
 const selectFunction=el('#graphFunctionNode');
 if(selectFunction){selectFunction.innerHTML='<option value="">Elegir nodo de la pizarra…</option>'+Array.from(functionsByNode.values()).map(f=>`<option value="${esc(f.id)}">${esc(f.id+' · '+f.title)}</option>`).join('');
 selectFunction.addEventListener('change',()=>{if(selectFunction.value)inspectBoardFunction(selectFunction.value)});}
 const relation=el('#graphRelation');relation.innerHTML='<option value="all">Todas las relaciones</option>'+Object.entries(relations).map(([k,v])=>`<option value="${esc(k)}">${esc(v)}</option>`).join('');
 relation.addEventListener('change',()=>{
 state.rel=relation.value;
 if(CROSS_TYPES.has(state.rel)){
   const entry=edges.find(e=>allowed(e)&&visible(skillById.get(e.from))&&visible(skillById.get(e.to))&&
    (state.scope==='all'||skillById.get(e.from).owners.includes(state.scope)||skillById.get(e.to).owners.includes(state.scope)));
   if(entry){state.selected=entry.from;state.suppressMobileInspector=true;inspectSkill(skillById.get(entry.from));state.suppressMobileInspector=false;}
 }
 redrawGraph();centerGraph();
});
 el('#graphShowPaused').addEventListener('change',e=>{state.showPaused=e.target.checked;redrawGraph()});
 el('#graphShowExcluded').addEventListener('change',e=>{state.showExcluded=e.target.checked;redrawGraph()});
 el('#graphOnlyDocumented').addEventListener('change',e=>{state.onlyDocumented=e.target.checked;redrawGraph()});
 el('#graphSkillSearch').addEventListener('input',e=>searchSkills(e.target.value));
 el('#graphExportDrawio').addEventListener('click',downloadGraphDrawio);
 el('#graphExportJson').addEventListener('click',downloadGraphJson);
 el('#graphZoomIn').addEventListener('click',()=>{state.zoom=Math.min(1.6,+(state.zoom+0.12).toFixed(2));scaleGraph()});
 el('#graphZoomOut').addEventListener('click',()=>{state.zoom=Math.max(.16,+(state.zoom-.12).toFixed(2));scaleGraph()});
 el('#graphZoomFit').addEventListener('click',graphFit);
 // Main toolbar export should also export the view currently being shown, never the invisible stage diagram.
 el('#exportDrawio').addEventListener('click',e=>{if(state.active){e.preventDefault();e.stopImmediatePropagation();downloadGraphDrawio()}},true);
 window.addEventListener('resize',()=>{if(!state.active)return;if(window.innerWidth<570){if(state.zoom<.56)state.zoom=.74;scaleGraph();centerGraph();}else if(state.zoom<.9)graphFit()});
 document.addEventListener('keydown',e=>{if(state.active&&e.key==='Escape'){el('#graphSearchBox').classList.remove('show')}});
 window.__routerSkillGraphDiagnostics={get data(){return graph},get state(){return {...state}},buildGraphDrawio,redrawGraph,selectSkill,inspectBoardFunction,graphLayout};
}
document.addEventListener('DOMContentLoaded',init);
})();

