const STAGES=DATA.stages,CANDIDATES=DATA.candidates,NODES=[...DATA.nodes,...CANDIDATES],EDGES=DATA.edges;
const CANDIDATE_COUNT=CANDIDATES.length;
const CANDIDATE_COLORS={candidate:['#fff8ec','#bb795c','#644036'],conditional:['#fffae9','#a99050','#5f5133'],inventory:['#efedff','#6f68ad','#373568'],paused:['#f3eef0','#a796a0','#594b57'],exclude:['#f5f1ef','#a59b94','#554e4a']};
const DISP_LABEL={candidate:'PROPUESTA NUEVA',conditional:'USO CONDICIONAL',inventory:'YA EN INVENTARIO',paused:'RUTA BLOQUEADA',exclude:'NO INCORPORAR'};
const SKILL_GROUPS={candidate:'PROPUESTA',conditional:'CONDICIONAL',inventory:'YA REGISTRADA',paused:'BLOQUEADA',exclude:'DESCARTADA'};
const CANDS_BY_STAGE=Object.fromEntries(STAGES.map(s=>[s.id,CANDIDATES.filter(n=>n.stage===s.id)]));
function cardRows(id){return Math.ceil((CANDS_BY_STAGE[id]||[]).length/6);}
function stageExtra(id){let rows=cardRows(id);return STATUS.proposals&&rows?100+rows*132:0;}
function stageLength(id){return 344+stageExtra(id);}
function stageStart(id){let idx=STAGES.findIndex(s=>s.id===id);return STAGES.slice(0,idx).reduce((acc,s)=>acc+stageLength(s.id),0);}
function stageOffset(id){return STATUS.stage==='all'?stageStart(id):15;}
function worldHeight(){return (STATUS.stage==='all'?STAGES.reduce((acc,s)=>acc+stageLength(s.id),0):stageLength(STATUS.stage))+85;}

const COLORS={core:['#e9ebfa','#5767b4','#30375d'],decision:['#ffffff','#8d94a4','#263650'],source:['#faf6ed','#a37b46','#3e4355'],authority:['#f0efff','#8572be','#34365f'],gate:['#fff0eb','#b85849','#6f3f36'],external:['#fff9e9','#947037','#684d26'],blocked:['#f2eff0','#786a7c','#755f64'],evidence:['#f4f1fa','#86729d','#4a3e63']};
const STATUS={stage:'all',kinds:new Set(Object.keys(COLORS)),selected:'G0',zoom:.8,engine:'svg',search:'',proposals:true};
let toastTimer=0; const $=(s)=>document.querySelector(s);const $$=(s)=>Array.from(document.querySelectorAll(s));
function textEscape(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;')}
const nameOf = n=>n.id+' · '+n.title+' '+n.description+' '+n.owner+' '+(n.repo||'')+' '+(n.target||'')+' '+(n.when||'');
function visibleNodes(){return NODES.filter(n=>(STATUS.stage==='all'||n.stage===STATUS.stage)&&(n.kind==='candidate'?STATUS.proposals:STATUS.kinds.has(n.kind)));}
function nodeMap(){return new Map(visibleNodes().map(n=>[n.id,n]));}
function stagePos(n){let idx=STAGES.findIndex(s=>s.id===n.stage);let y=n.kind==='candidate'?n.local_y:n.y-idx*344;return{x:n.x,y:y+stageOffset(n.stage)};}
function svgEl(tag,props,body=''){return '<'+tag+' '+Object.entries(props).map(([k,v])=>k+'="'+textEscape(v)+'"').join(' ')+'>'+body+'</'+tag+'>';}
function drawStage(s){const offset=stageOffset(s.id),y=47+offset,extra=stageExtra(s.id),rows=cardRows(s.id),coreH=(s.id==='encuadre'||s.id==='aprendizaje'?235:322),h=Math.max(coreH+extra,STATUS.proposals&&rows?385+rows*132:coreH);
let more='';if(STATUS.proposals&&CANDS_BY_STAGE[s.id].length){const line=375+offset;more=`<path d="M105 ${line} H2010" class="proposal-rule"/><text class="proposal-heading" x="105" y="${line+24}">PROPUESTAS DE INSERCIÓN · ${CANDS_BY_STAGE[s.id].length} SKILLS EXTERNAS · BORRADOR, NO INSTALADAS</text>`;}
return `<g class="stage-layer" data-stage="${s.id}"><rect class="stage-bg" x="63" y="${y}" rx="18" width="2002" height="${h}"/><path class="stage-rule" d="M105 ${y+78} H2010"/><text class="stage-index" x="105" y="${y+30}">${s.index}</text><text class="stage-heading" x="148" y="${y+31}">${textEscape(s.label)}</text><text class="stage-description" x="148" y="${y+55}">${textEscape(s.subtitle)} · ${textEscape(s.code)}</text>${more}</g>`;}

function nodeLayout(n){let{x,y}=stagePos(n);let special=n.kind==='candidate';let disp=n.disposition||'candidate';let[bg,border,ink]=special?CANDIDATE_COLORS[disp]:COLORS[n.kind];
if(special){let selected=STATUS.selected===n.id?' selected':'';let name=n.title.length>31?n.title.slice(0,29)+'…':n.title;let desc=n.description.length>63?n.description.slice(0,60)+'…':n.description;
return `<g class="node candidate-node ${disp}${selected}" role="button" tabindex="0" data-node="${n.id}" aria-label="Abrir propuesta ${textEscape(n.title)}, bajo ${textEscape(n.owner)} hacia ${textEscape(n.target)}"><rect x="${x}" y="${y}" rx="9" width="${n.w}" height="${n.h}" fill="${bg}" stroke="${border}" stroke-width="2" stroke-dasharray="5 4"/><path d="M${x+n.w-24} ${y+1} l23 23 v-23 z" fill="${border}" opacity=".18"/><text class="candidate-kind" x="${x+14}" y="${y+21}" fill="${ink}">${textEscape(DISP_LABEL[disp])} · ${textEscape(n.owner)}</text><text class="candidate-title" x="${x+14}" y="${y+47}">${textEscape(name)}</text><text class="candidate-target" x="${x+14}" y="${y+68}">INSERTAR EN ${textEscape(n.target)}</text><text class="candidate-sub" x="${x+14}" y="${y+86}">${textEscape(desc)}</text></g>`;}
let label=n.kind==='core'?'SKILL RECTORA':n.kind==='external'?'APOYO EXTERNO':n.kind==='gate'?'GATE':n.kind==='blocked'?'NO MODELADA':n.kind==='source'?'FUENTE':n.kind==='authority'?'AUTORIDAD':n.kind==='evidence'?'EVIDENCIA':'DECISIÓN';
let ell=n.description.length>76?n.description.slice(0,76)+'…':n.description;
function wrap(str,max=41){let words=str.split(/\s+/),lines=[],a='';words.forEach(w=>{if((a+' '+w).trim().length>max){if(a)lines.push(a);a=w}else a=(a+' '+w).trim()});if(a)lines.push(a);return lines.slice(0,2)}
let descriptions=wrap(ell,42).map((v,i)=>`<tspan x="${x+17}" dy="${i?16:0}">${textEscape(v)}</tspan>`).join('');const selected=STATUS.selected===n.id?' selected':'';
return `<g class="node${selected}" role="button" tabindex="0" data-node="${n.id}" aria-label="Abrir ficha de ${textEscape(n.title)}"><rect x="${x}" y="${y}" rx="13" width="${n.w}" height="${n.h}" fill="${bg}" stroke="${border}"/><rect x="${x+13}" y="${y+11}" rx="2" width="5" height="12" fill="${border}"/><text class="node-kind" x="${x+28}" y="${y+21}" fill="${ink}">${label}</text><text class="node-title" x="${x+17}" y="${y+47}">${textEscape(n.title)}</text><text class="node-body" x="${x+17}" y="${y+68}">${descriptions}</text></g>`;}

function linkPath(a,b){let pa=stagePos(a),pb=stagePos(b);let ax=pa.x+a.w,ay=pa.y+a.h/2,bx=pb.x,by=pb.y+b.h/2;if(bx>ax+15){let mid=(ax+bx)/2;return `M${ax} ${ay} L${mid} ${ay} L${mid} ${by} L${bx-9} ${by}`;}let x=pa.x+a.w/2, y=pa.y+a.h, xt=pb.x+b.w/2, yt=pb.y;let mid=(y+yt)/2;return `M${x} ${y} L${x} ${mid} L${xt} ${mid} L${xt} ${yt-5}`;}
function clipSvgLabel(el,maxWidth){if(!el||el.getComputedTextLength()<=maxWidth)return;let chars=Array.from(el.textContent),lo=0,hi=chars.length;while(lo<hi){let mid=Math.ceil((lo+hi)/2);el.textContent=chars.slice(0,mid).join('')+'…';if(el.getComputedTextLength()>maxWidth)hi=mid-1;else lo=mid;}el.textContent=chars.slice(0,lo).join('')+'…';}
function redraw(){let ns=visibleNodes(),map=new Map(ns.map(n=>[n.id,n]));let stages=STAGES.filter(s=>STATUS.stage==='all'||s.id===STATUS.stage);let h=worldHeight();let svg=$('#boardSVG');svg.setAttribute('viewBox',`0 0 2150 ${h}`);svg.setAttribute('height',h);svg.style.height=h+'px';
let content=`<defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="5.8" refY="3.5" orient="auto"><path d="M0 0 L7 3.5 L0 7 Z" fill="#9da1ad"/></marker><filter id="paperShadow" x="-15%" y="-20%" width="130%" height="145%"><feDropShadow dx="0" dy="2" stdDeviation="2.3" flood-opacity=".08"/></filter><filter id="selectedShadow" x="-20%" y="-20%" width="140%" height="145%"><feDropShadow dx="0" dy="3" stdDeviation="4" flood-color="#4b54b4" flood-opacity=".13"/></filter></defs>`;
content+=stages.map(s=>drawStage(s)).join('');
content+=EDGES.filter(e=>map.has(e.from)&&map.has(e.to)).map(e=>`<path class="edge ${e.kind}" d="${linkPath(map.get(e.from),map.get(e.to))}"/>`).join('');
const candidate=NODES.find(n=>n.id===STATUS.selected&&n.kind==='candidate');if(candidate&&map.has(candidate.id)&&map.has(candidate.anchor)){
content+=`<path class="edge candidate-connection" d="${linkPath(map.get(candidate.anchor),candidate)}"/>`;}
content+=ns.map(nodeLayout).join('');content+=`<text class="board-stamp" x="105" y="${h-17}">MAPA DE INSERCIONES PROPUESTAS / BASELINE CANÓNICO v0.4 INTACTO · SKILLS EXTERNAS NO INSTALADAS</text>`;
svg.innerHTML=content;$$('[data-node]').forEach(el=>{el.addEventListener('click',()=>selectNode(el.dataset.node));el.addEventListener('keydown',ev=>{if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();selectNode(el.dataset.node)}})});
$('#nodeCount').textContent=String(ns.length).padStart(2,'0');$('#candidateCount').textContent=String(ns.filter(n=>n.kind==='candidate').length).padStart(2,'0');$('#stageCount').textContent=String(stages.length).padStart(2,'0');$('#stageFocus').textContent=STATUS.stage==='all'?'MAPA COMPLETO':'CAPA '+STAGES.find(s=>s.id===STATUS.stage).index;updateWorldSize();}

function notify(msg){let t=$('#toast');t.textContent=msg;t.hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>t.hidden=true,3600);}
function openInspector(focusHeading=false){let el=$('#inspector');el.classList.add('show');$('#mobileInspect').setAttribute('aria-expanded','true');if(innerWidth<850){el.scrollTop=0;if(focusHeading)$('#inspectTitle').focus({preventScroll:true});}}
function closeInspector(){let el=$('#inspector');el.classList.remove('show');$('#mobileInspect').setAttribute('aria-expanded','false');if(innerWidth<850)$('#mobileInspect').focus({preventScroll:true});}
function selectNode(id){let n=NODES.find(n=>n.id===id);if(!n)return;STATUS.selected=id;if(STATUS.stage!=='all'&&STATUS.stage!==n.stage)setStage(n.stage,true);STATUS.kinds.add(n.kind);$$('[data-kind-toggle]').forEach(b=>b.setAttribute('aria-pressed',String(STATUS.kinds.has(b.dataset.kindToggle))));redraw();renderInspector(n);openInspector(true);}
function renderInspector(n){let s=STAGES.find(s=>s.id===n.stage);$('#inspectCode').textContent=n.id+' / '+s.index;$('#inspectTitle').textContent=n.title;$('#inspectDesc').textContent=n.description;$('#inspectStage').textContent=s.label;$('#inspectOwner').textContent=n.kind==='candidate'?(n.owner+' · autoridad metodológica my-skills'):n.owner||'Sin responsable asignado';$('#inspectStatus').textContent=n.kind==='candidate'?DISP_LABEL[n.disposition]:n.status|| (n.kind==='core'?'SKILL RECTORA':n.kind==='external'?'REFERENCIA EXTERNA':n.kind==='gate'?'REQUIERE VALIDACIÓN HUMANA':'MAPA CONCEPTUAL');let a=$('#inspectSource');if(n.source){a.href=n.source;a.classList.remove('hidden');a.textContent='Abrir SKILL.md original ↗'}else a.classList.add('hidden');$('#inspectKind').textContent=n.kind==='candidate'?'Skill externa · posición propuesta':n.kind==='core'?'Mi skill':n.kind==='external'?'Externa':n.kind==='gate'?'Gate':n.kind==='blocked'?'Bloqueada':'Nodo del router';
let extra=$('#inspectExtra');if(n.kind==='candidate'){extra.hidden=false;extra.innerHTML=`<div class="inspect-label">NODO DE INSERCIÓN</div><div class="inspect-value mono">${textEscape(n.target)}</div><div class="inspect-label">¿Por qué aquí?</div><div class="inspect-value">${textEscape(n.purpose)}</div><div class="inspect-label">Activador / condición</div><div class="inspect-value">${textEscape(n.when)}</div><div class="inspect-label">Límite o conflicto</div><div class="inspect-value">${textEscape(n.limit)}</div><div class="inspect-label">Repositorio</div><div class="inspect-value mono">${textEscape(n.repo)}</div>`;}else{extra.hidden=true;extra.replaceChildren();}}

function setStage(id,preserveSelection=false){if(id!=='all'&&!STAGES.some(s=>s.id===id))return;STATUS.stage=id;if(!preserveSelection){let first=NODES.find(n=>(id==='all'||n.stage===id)&&STATUS.kinds.has(n.kind));if(first){STATUS.selected=first.id;renderInspector(first);}}$$('[data-stage-select]').forEach(el=>{let active=el.dataset.stageSelect===id;el.classList.toggle('active',active);el.setAttribute('aria-pressed',String(active))});$('#nativeBoard').setAttribute('aria-label',id==='all'?'Pizarra completa, seis capas':'Pizarra, '+STAGES.find(s=>s.id===id).label);redraw();if(STATUS.engine==='drawio')showDrawio();const canvas=$('#nativeBoard');canvas.scrollTop=0;canvas.scrollLeft=0;}
function updateWorldSize(){let h=worldHeight(),world=$('#boardWorld');world.style.width=(2150*STATUS.zoom)+'px';world.style.height=(h*STATUS.zoom)+'px';let svg=$('#boardSVG');svg.style.transform=`scale(${STATUS.zoom})`;svg.style.transformOrigin='top left';$('#zoomValue').textContent=Math.round(STATUS.zoom*100)+'%';}
function zoom(delta){STATUS.zoom=Math.min(1.65,Math.max(.08,Math.round((STATUS.zoom+delta)*100)/100));updateWorldSize();}
function fit(){let w=$('#canvasFrame').clientWidth-40;STATUS.zoom=Math.min(1.1,Math.max(.08,w/2150));updateWorldSize();$('#nativeBoard').scrollLeft=0;$('#nativeBoard').scrollTop=0;}
function escapeXml(s){return textEscape(s);}
function drawioXML(){let ns=[...DATA.nodes,...CANDIDATES],map=new Map(ns.map(n=>[n.id,n])),parts=['<mxGraphModel dx="1100" dy="650" grid="1" gridSize="10" guides="1" tooltips="1" connect="0" arrows="1" fold="1" page="0" pageScale="1" shadow="0"><root><mxCell id="0"/><mxCell id="1" parent="0"/>'];
function absolutePos(n){const idx=STAGES.findIndex(s=>s.id===n.stage),localY=n.kind==='candidate'?n.local_y:n.y-idx*344;return{x:n.x,y:localY+STAGES.slice(0,idx).reduce((acc,s)=>acc+344+(100+cardRows(s.id)*132),0)};}
STAGES.forEach(s=>{parts.push(`<mxCell id="layer_${s.id}" value="${escapeXml(s.label)}" parent="0"/>`);let y=47+STAGES.slice(0,STAGES.indexOf(s)).reduce((acc,x)=>acc+344+100+cardRows(x.id)*132,0),h=Math.max((s.id==='encuadre'||s.id==='aprendizaje'?235:322)+100+cardRows(s.id)*132,385+cardRows(s.id)*132);parts.push(`<mxCell id="bg_${s.id}" value="" style="rounded=1;arcSize=8;fillColor=#faf7f1;strokeColor=#ddd5cc;dashed=1;movable=0;resizable=0;" vertex="1" parent="layer_${s.id}"><mxGeometry x="63" y="${y}" width="2002" height="${h}" as="geometry"/></mxCell>`);});
ns.forEach(n=>{let{x,y}=absolutePos(n),cand=n.kind==='candidate',scheme=cand?CANDIDATE_COLORS[n.disposition]:COLORS[n.kind],[bg,stroke,ink]=scheme,style=cand?`rounded=1;arcSize=9;whiteSpace=wrap;html=1;align=left;verticalAlign=middle;spacingLeft=15;spacingRight=14;strokeWidth=2;dashed=1;dashPattern=5 4;fillColor=${bg};strokeColor=${stroke};fontColor=${ink};fontSize=12;fontFamily=Arial;`:`rounded=1;arcSize=14;whiteSpace=wrap;html=1;align=left;verticalAlign=middle;spacingLeft=15;spacingRight=14;strokeWidth=1.5;fillColor=${bg};strokeColor=${stroke};fontColor=${ink};fontSize=15;fontFamily=Arial;`;
let label=cand?`<b>${escapeXml(DISP_LABEL[n.disposition])} · ${escapeXml(n.title)}</b><br><font size="2">${escapeXml(n.owner)} → ${escapeXml(n.target)}<br>${escapeXml(n.description)}</font>`:`<b>${escapeXml(n.title)}</b><br><font size="2">${escapeXml(n.description)}</font>`;
parts.push(`<mxCell id="${n.id}" value="${escapeXml(label)}" style="${style}" vertex="1" parent="layer_${n.stage}"><mxGeometry x="${x}" y="${y}" width="${n.w}" height="${n.h}" as="geometry"/></mxCell>`);});let i=0;
EDGES.forEach(e=>{if(!map.has(e.from)||!map.has(e.to))return;let a=map.get(e.from),b=map.get(e.to),style=`edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;strokeColor=#a0a4ad;strokeWidth=1.6;endArrow=block;endFill=1;${e.kind==='flow'?'':'dashed=1;dashPattern=4 4;'}html=1;`;parts.push(`<mxCell id="edge_${i++}" style="${style}" edge="1" parent="${a.stage===b.stage?'layer_'+a.stage:'1'}" source="${e.from}" target="${e.to}"><mxGeometry relative="1" as="geometry"/></mxCell>`);});
CANDIDATES.forEach(n=>{if(!map.has(n.anchor))return;parts.push(`<mxCell id="integration_${n.id}" value="${escapeXml(n.owner+' → '+n.target)}" style="edgeStyle=orthogonalEdgeStyle;rounded=1;jettySize=auto;strokeColor=#c6a99e;strokeWidth=1;dashed=1;dashPattern=2 5;endArrow=open;endFill=0;html=1;fontSize=9;fontColor=#8f7774;" edge="1" parent="layer_${n.stage}" source="${n.anchor}" target="${n.id}"><mxGeometry relative="1" as="geometry"/></mxCell>`);});
parts.push('</root></mxGraphModel>');return parts.join('');}

function download(name,content,mime){let blob=new Blob([content],{type:mime}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1200);}
function downloadDrawio(){let xml='<?xml version="1.0" encoding="UTF-8"?><mxfile host="app.diagrams.net" modified="2026-11-17T10:50:00.000Z" agent="ResearchBoard" type="device"><diagram id="router-map" name="Router · Capas">'+drawioXML()+'</diagram></mxfile>';download('design-router-integraciones-v0.3.drawio',xml,'application/xml;charset=utf-8');notify('Archivo .drawio exportado. Puedes abrirlo en diagrams.net.');}
function showSvg(){STATUS.engine='svg';$('#drawioHost').classList.remove('show');$('#nativeBoard').classList.remove('hidden');$('#engineButton').textContent='Motor draw.io';$('#engineBadge').textContent='SVG LOCAL · EXPORTABLE';redraw();}
function showDrawio(){if(typeof window.GraphViewer==='undefined'){notify('El visor oficial de draw.io necesita conexión. La pizarra local sigue disponible y el XML se puede exportar.');showSvg();return;}STATUS.engine='drawio';let host=$('#drawioHost');$('#nativeBoard').classList.add('hidden');host.classList.add('show');host.innerHTML='<div class="drawio-watermark">Motor draw.io · mxGraph · usa las herramientas del visor para acercar, desplazar y explorar capas.</div>';
let div=document.createElement('div');div.className='mxgraph';div.dataset.mxgraph=JSON.stringify({highlight:'#4b60b7',nav:true,resize:true,toolbar:'zoom layers',xml:drawioXML()});host.appendChild(div);$('#engineButton').textContent='Volver al tablero';$('#engineBadge').textContent='DRAW.IO VIEWER';try{window.GraphViewer.processElements()}catch(e){console.warn('drawio viewer',e);showSvg();notify('El visor no pudo procesar este diagrama. Vista local conservada.')}}
let viewerPromise=null;
function fetchDrawioViewer(){if(window.GraphViewer)return Promise.resolve(true);if(viewerPromise)return viewerPromise;viewerPromise=new Promise(resolve=>{let s=document.createElement('script');s.src='https://viewer.diagrams.net/js/viewer-static.min.js';s.async=true;let done=false;let timer=setTimeout(()=>finish(false),5000);function finish(ok){if(done)return;done=true;clearTimeout(timer);if(!ok)s.remove();resolve(ok)}s.onload=()=>finish(Boolean(window.GraphViewer));s.onerror=()=>finish(false);document.head.appendChild(s)});return viewerPromise;}
async function toggleEngine(){if(STATUS.engine==='drawio'){showSvg();return;}let b=$('#engineButton');b.disabled=true;b.textContent='Conectando draw.io…';let ok=await fetchDrawioViewer();b.disabled=false;if(ok){showDrawio();}else{notify('El visor de draw.io necesita conexión; sigue disponible el diagrama local y su XML.');showSvg();}}
function handleSearch(q){STATUS.search=q.trim().toLowerCase();let res=$('#results');if(!STATUS.search){res.classList.add('hidden');return;}let found=NODES.filter(n=>nameOf(n).toLowerCase().includes(STATUS.search)).sort((a,b)=>Number(b.kind==='candidate')-Number(a.kind==='candidate') || Number(b.title.toLowerCase()===STATUS.search)-Number(a.title.toLowerCase()===STATUS.search)).slice(0,14);res.classList.remove('hidden');res.replaceChildren();res.style.cssText='position:absolute;left:0;right:0;top:40px;background:#fffdfa;z-index:20;border:1px solid #d9d2cc;border-radius:10px;padding:6px;box-shadow:0 9px 18px #0002;max-height:230px;overflow:auto;';if(!found.length){let e=document.createElement('div');e.textContent='Sin coincidencias';e.style.padding='10px';res.appendChild(e);return;}found.forEach(n=>{let b=document.createElement('button');b.type='button';b.textContent=n.kind==='candidate'?(n.title+' · '+n.owner+' / '+n.target):(n.id+' · '+n.title);b.style.cssText='display:block;padding:9px;border:0;text-align:left;width:100%;background:transparent;font-size:var(--text-xs);cursor:pointer;';b.addEventListener('click',()=>{res.classList.add('hidden');$('#searchInput').value='';if(n.kind==='candidate')STATUS.proposals=true;$('#candidateToggle').setAttribute('aria-pressed',String(STATUS.proposals));selectNode(n.id);});res.appendChild(b)});}
function init(){let container=$('#stageButtons');const allButton=(id,num,title,subtitle)=>{let b=document.createElement('button');b.type='button';b.className='stage-btn'+(id==='all'?' active':'');b.dataset.stageSelect=id;b.setAttribute('aria-pressed',String(id==='all'));b.innerHTML=`<span class="num">${num}</span><span><strong>${title}</strong><small>${subtitle}</small></span>`;b.addEventListener('click',()=>setStage(id));b.setAttribute('aria-label',id==='all'?'Mostrar mapa completo':'Mostrar capa '+num+': '+title);b.setAttribute('aria-controls','nativeBoard');container.appendChild(b)};allButton('all','∞','Mapa completo','Todas las capas');STAGES.forEach(s=>allButton(s.id,s.index,s.label,s.subtitle));
$$('[data-kind-toggle]').forEach(b=>b.addEventListener('click',()=>{let k=b.dataset.kindToggle;if(k==='external')k='external';if(STATUS.kinds.has(k))STATUS.kinds.delete(k);else STATUS.kinds.add(k);b.setAttribute('aria-pressed',String(STATUS.kinds.has(k)));if(!visibleNodes().some(n=>n.id===STATUS.selected)){let first=visibleNodes()[0];if(first){STATUS.selected=first.id;renderInspector(first)}}redraw();if(STATUS.engine==='drawio')showDrawio();}));
$('#candidateToggle').addEventListener('click',()=>{STATUS.proposals=!STATUS.proposals;$('#candidateToggle').setAttribute('aria-pressed',String(STATUS.proposals));if(!visibleNodes().some(n=>n.id===STATUS.selected)){STATUS.selected='G0';renderInspector(NODES.find(n=>n.id==='G0'));}redraw();if(STATUS.engine==='drawio')showDrawio();});
$('#zoomIn').addEventListener('click',()=>zoom(.12));$('#zoomOut').addEventListener('click',()=>zoom(-.12));$('#zoomFit').addEventListener('click',fit);$('#exportDrawio').addEventListener('click',downloadDrawio);$('#exportDrawioBottom').addEventListener('click',downloadDrawio);$('#engineButton').addEventListener('click',toggleEngine);$('#mobileInspect').addEventListener('click',()=>$('#inspector').classList.contains('show')?closeInspector():openInspector(true));$('#closeInspect').addEventListener('click',closeInspector);$('#searchInput').addEventListener('input',e=>handleSearch(e.target.value));$('#searchInput').addEventListener('keydown',e=>{if(e.key==='Escape'){$('#results').classList.add('hidden');e.target.value=''}});document.addEventListener('click',e=>{if(!e.target.closest('.search'))$('#results').classList.add('hidden')});document.addEventListener('keydown',e=>{if((e.key==='/'||e.key==='f')&&!['INPUT','TEXTAREA'].includes(document.activeElement.tagName)){e.preventDefault();$('#searchInput').focus()}if(e.key==='Escape'&&$('#inspector').classList.contains('show'))closeInspector()});
$('#drawioExternal').addEventListener('click',()=>window.open('https://app.diagrams.net/','_blank','noopener,noreferrer'));
redraw();renderInspector(NODES.find(n=>n.id===STATUS.selected));$('#nativeBoard').scrollTop=0;
}
function initSidebarPreference(){
 const button=$('#stageNavigationToggle'),app=$('.app');
 const panels=$$('[data-board-sidebar]');
 button.setAttribute('aria-controls',panels.map(panel=>panel.id).join(' '));
 const compact=window.matchMedia('(max-width: 840px)');
 const storageKey='design-router.stage-navigation-expanded';
 let userExpanded;
 try{
  const saved=window.localStorage.getItem(storageKey);
  if(saved==='true'||saved==='false')userExpanded=saved==='true';
 }catch{
  // Use the responsive default when browser storage is unavailable.
 }
 function sync(){
  const expanded=userExpanded??!compact.matches;
  const restoreFocus=!expanded&&panels.some(panel=>panel.contains(document.activeElement));
  app.classList.toggle('stage-navigation-collapsed',!expanded);
  button.setAttribute('aria-expanded',String(expanded));
  button.textContent=expanded?'Ocultar paneles':'Mostrar paneles';
  if(restoreFocus)button.focus({preventScroll:true});
 }
 button.addEventListener('click',()=>{
  userExpanded=button.getAttribute('aria-expanded')==='false';
  sync();
  try{
   window.localStorage.setItem(storageKey,String(userExpanded));
  }catch{
   // Keep the current choice in memory when it cannot be saved.
  }
 });
 compact.addEventListener('change',sync);
 sync();
}
initSidebarPreference();
function initViewSwitch(){
 const strip=$('.mode-switch');
 if(!strip)return;
 const fade=28;
 function syncEdges(){
  const max=strip.scrollWidth-strip.clientWidth;
  const edges=[];
  if(strip.scrollLeft>1)edges.push('start');
  if(strip.scrollLeft<max-1)edges.push('end');
  if(edges.length)strip.dataset.overflow=edges.join(' ');
  else delete strip.dataset.overflow;
 }
 // Scroll only the strip, so the page and board never jump when a view changes.
 function revealActive(){
  const active=strip.querySelector('button[aria-pressed="true"]');
  if(active&&strip.scrollWidth>strip.clientWidth){
   const start=active.offsetLeft-fade,end=active.offsetLeft+active.offsetWidth+fade;
   if(start<strip.scrollLeft)strip.scrollLeft=start;
   else if(end>strip.scrollLeft+strip.clientWidth)strip.scrollLeft=end-strip.clientWidth;
  }
  syncEdges();
 }
 // Each view clears its own tab when it closes; the stage map is the view left behind.
 const stageTab=$('#stageMapView'),overlays=['semantic-active','proposal-active','comparison-active','capability-active','all-active','router-nodes-active'];
 stageTab?.addEventListener('click',()=>{
  if(overlays.some(name=>$('.app').classList.contains(name)))return;
  strip.querySelectorAll('button[aria-pressed]').forEach(button=>button.setAttribute('aria-pressed',String(button===stageTab)));
 });
 // On narrow screens the Ficha is a sheet over the view; a new view starts with it closed.
 // Runs after every view's own click handlers, including ones that restore a selection.
 strip.addEventListener('click',e=>{
  // Programmatic clicks (jump to a node) open the Ficha on purpose; only a user's tab choice closes it.
  if(!e.isTrusted||!e.target.closest('button[aria-pressed]')||innerWidth>=850)return;
  setTimeout(()=>{$('#inspector').classList.remove('show');$('#mobileInspect').setAttribute('aria-expanded','false');});
 });
 strip.addEventListener('scroll',syncEdges,{passive:true});
 strip.addEventListener('wheel',event=>{
  if(Math.abs(event.deltaY)<=Math.abs(event.deltaX)||strip.scrollWidth<=strip.clientWidth)return;
  strip.scrollLeft+=event.deltaY;
  event.preventDefault();
 },{passive:false});
 new MutationObserver(revealActive).observe(strip,{subtree:true,childList:true,attributes:true,attributeFilter:['aria-pressed']});
 new ResizeObserver(revealActive).observe(strip);
 // Web fonts widen the tabs after the first layout.
 document.fonts?.ready.then(revealActive);
 revealActive();
}
initViewSwitch();
document.addEventListener('DOMContentLoaded',init);
