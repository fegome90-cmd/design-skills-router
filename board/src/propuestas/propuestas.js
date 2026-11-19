(function(){
'use strict';
const data = JSON.parse(document.getElementById('changeBoardData').textContent);
const xml = JSON.parse(document.getElementById('changeDrawioData').textContent);
const app = document.querySelector('.app');
const byId = new Map(data.proposals.map(p=>[p.id,p]));
const stageLabel = Object.fromEntries(data.stages.map(s=>[s.id,s]));
const state={layer:'all',priority:'all',phase:'all',query:'',selected:null};
const $=s=>document.querySelector(s);
function escape(s){return String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}
function download(name,body,type){const url=URL.createObjectURL(new Blob([body],{type}));let a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1500);}
function visible(p){const q=state.query.trim().toLowerCase();return (state.layer==='all'||p.layer===state.layer)&&(state.priority==='all'||p.priority===state.priority)&&(state.phase==='all'||p.phase===state.phase)&&(!q||[p.id,p.title,p.summary,p.before,p.after,p.change,p.owner,...p.nodes,...p.skills,...p.audit,...p.files].join(' ').toLowerCase().includes(q));}
function render(){let shown=data.proposals.filter(visible);$('#changeNoResults').hidden=!!shown.length;
 $('#changeSummary').innerHTML=[['15','cambios propuestos'],['07','familias de hallazgos'],['04','paquetes de corrección'],['00','cambios publicados']].map(([n,t])=>`<div class="change-metric"><strong>${n}</strong><span>${t}</span></div>`).join('');
 $('#changeSchedule').innerHTML=data.phases.map(f=>`<div class="change-milestone"><div class="cm-id">${escape(f.id)} · PAQUETE PENDIENTE</div><h3>${escape(f.label)}</h3><p>${escape(f.description)}</p><small>${escape(f.check)}</small></div>`).join('');
 $('#changeLanes').innerHTML=data.stages.map(s=>{const cards=shown.filter(p=>p.layer===s.id);if(!cards.length)return '';return `<section class="change-lane" data-change-stage="${escape(s.id)}" aria-label="Etapa ${escape(s.index)} · ${escape(s.title)}"><div class="change-lane-head"><div class="change-lane-num">${escape(s.index)}</div><div><h3>${escape(s.title)}</h3><p>${escape(s.description)}</p></div><span class="change-lane-counter">${cards.length} propuesta${cards.length===1?'':'s'}</span></div><div class="change-card-grid">${cards.map(p=>`<button type="button" class="change-card" data-change="${escape(p.id)}" data-priority="${escape(p.priority)}" data-selected="${p.id===state.selected}" aria-label="Abrir propuesta ${escape(p.id)}: ${escape(p.title)}"><div class="change-card-top"><span class="change-id">${escape(p.id)}</span><span class="change-pri">${escape(p.priority)}</span><span class="change-phase">${escape(p.phase)}</span><span class="change-status">${escape(p.status)}</span><span class="change-owner">${escape(p.owner)}</span></div><h4>${escape(p.title)}</h4><p class="change-summarytext">${escape(p.summary)}</p><div class="change-diff"><div><b>AHORA</b><p>${escape(p.before)}</p></div><span class="diff-arrow" aria-hidden="true">›</span><div><b>PROPUESTA</b><p>${escape(p.after)}</p></div></div><div class="change-bottom"><span class="change-node">${escape(p.nodes[0])}</span><span>${escape(p.audit.join(' · '))}</span><span class="change-action">Ver ficha y pruebas ›</span></div></button>`).join('')}</div></section>`;}).join('');
 document.querySelectorAll('[data-change]').forEach(b=>b.addEventListener('click',()=>select(b.dataset.change)));
}
function show(){
 // Reset the existing semantic graph before changing the view, preserving its event handlers.
 if(app.classList.contains('semantic-active')) $('#stageMapView').click();
 app.classList.add('proposal-active');$('#stageMapView').setAttribute('aria-pressed','false');$('#skillNetworkView').setAttribute('aria-pressed','false');$('#proposalBoardView').setAttribute('aria-pressed','true');$('#proposalPanel').setAttribute('aria-hidden','false');
 $('#changeScroll').scrollTop=0;render();
}
function close(){if(!app.classList.contains('proposal-active'))return;app.classList.remove('proposal-active');$('#proposalPanel').setAttribute('aria-hidden','true');$('#proposalBoardView').setAttribute('aria-pressed','false');if(!app.classList.contains('semantic-active'))$('#stageMapView').setAttribute('aria-pressed','true');}
function select(id){const p=byId.get(id);if(!p)return;state.selected=id;render();
 $('#inspectCode').textContent=p.id+' / '+p.phase+' · CAMBIO PROPUESTO';$('#inspectTitle').textContent=p.title;$('#inspectDesc').textContent=p.summary;
 $('#inspectKind').textContent='Plan de corrección';$('#inspectStatus').textContent=p.priority+' · SIN APROBAR';$('#inspectOwner').textContent=p.owner+' / my-skills';$('#inspectStage').textContent=stageLabel[p.layer].index+' · '+stageLabel[p.layer].title;
 const l=$('#inspectSource');l.classList.add('hidden');l.removeAttribute('href');
 let rows=[['Situación actual',p.before],['Resultado propuesto',p.after],['Intervención concreta',p.change],['Gate',p.gate]];
 let body=rows.map(([a,b],idx)=>`<div class="change-inspector-label">${escape(a)}</div><div class="change-inspector-block ${idx===1?'after':''}">${escape(b)}</div>`).join('');
 body+=`<div class="change-inspector-label">Nodos y skills afectados</div><div class="change-inspector-block"><b>${escape(p.nodes.join(' · '))}</b><p style="margin:4px 0 0">Skills: ${escape(p.skills.join(', '))}</p></div>`;
 body+=`<div class="change-inspector-label">Archivos candidatos (sin editar)</div><ul class="change-inspector-list">${p.files.map(s=>`<li>${escape(s)}</li>`).join('')}</ul>`;
 body+=`<div class="change-inspector-label">Pruebas de aceptación propuestas</div><ul class="change-inspector-list">${p.checks.map(s=>`<li>${escape(s)}</li>`).join('')}</ul>`;
 body+=`<div class="change-inspector-label">Dependencias · hallazgos</div><div class="change-inspector-block">${escape((p.depends.length?p.depends.join(' → '):'Sin dependencia interna previa')+' · '+p.audit.join(', '))}</div>`;
 body+=`<button type="button" class="change-inspector-jump" id="changeJump">Ver nodo ${escape(p.anchor)} en Capas ↗</button>`;
 $('#inspectExtra').innerHTML=body;$('#inspectExtra').hidden=false;$('#changeJump').addEventListener('click',()=>jump(p.anchor));
 if(window.innerWidth<=850){$('#inspector').classList.add('show');$('#mobileInspect').setAttribute('aria-expanded','true');}
}
function jump(id){close();$('#stageMapView').click();if(typeof window.selectNode==='function'){window.selectNode(id);}else{$('#searchInput').value=id;$('#searchInput').dispatchEvent(new Event('input',{bubbles:true}));}}
function init(){
 data.stages.forEach(s=>{let o=document.createElement('option');o.value=s.id;o.textContent=s.index+' · '+s.title;$('#changeLayer').appendChild(o);});
 $('#proposalBoardView').addEventListener('click',show);
 $('#stageMapView').addEventListener('click',close,true);$('#skillNetworkView').addEventListener('click',close,true);
 $('#stageButtons').addEventListener('click',close,true);
 $('#changeLayer').addEventListener('change',e=>{state.layer=e.target.value;render()});
 $('#changePriority').addEventListener('change',e=>{state.priority=e.target.value;render()});
 $('#changePhase').addEventListener('change',e=>{state.phase=e.target.value;render()});
 $('#changeQuery').addEventListener('input',e=>{state.query=e.target.value;render()});
 $('#changeClear').addEventListener('click',()=>{state.layer=state.priority=state.phase='all';state.query='';$('#changeLayer').value='all';$('#changePriority').value='all';$('#changePhase').value='all';$('#changeQuery').value='';render()});
 $('#changeExportJson').addEventListener('click',()=>download('design-router-cambios-propuestos-v0.6.json',JSON.stringify(data,null,2),'application/json'));
 $('#changeExportDrawio').addEventListener('click',()=>download('design-router-cambios-propuestos-v0.6.drawio',xml,'application/xml'));
 $('#exportDrawio').addEventListener('click',e=>{if(app.classList.contains('proposal-active')){e.stopImmediatePropagation();e.preventDefault();download('design-router-cambios-propuestos-v0.6.drawio',xml,'application/xml');}},true);
 if(window.innerWidth<=570)$('#changeRoadmap').open=false;const requestedView=new URLSearchParams(location.search).get('vista');if(location.hash==='#capas'||requestedView==='capas'||requestedView==='relaciones')render();else show();
 window.__routerChangeBoard={data,visible:()=>data.proposals.filter(visible),show,select,jump,exportDrawio:()=>xml};
}
document.addEventListener('DOMContentLoaded',init);
})();