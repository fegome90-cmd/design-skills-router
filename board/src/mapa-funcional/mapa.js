
(()=>{
 const $=id=>document.getElementById(id),d=JSON.parse($('capabilityMapData').textContent),app=document.querySelector('.app');
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const skillById=Object.fromEntries(d.skills.map(x=>[x.id,x]));
 let active='type-choice',query='',owner='all',effect='all',route='tipografia',routeOnly=true;
 const currentRoute=()=>d.routes.find(x=>x.id===route);
 function textFor(f){return (f.label+' '+f.definition+' '+f.owners.join(' ')+' '+f.nodes.join(' ')+' '+d.skills.filter(s=>s.contributions.some(c=>c.function_id===f.id)).map(s=>s.name+' '+s.repo).join(' ')).toLocaleLowerCase('es');}
 function candidateList(f){return d.skills.flatMap(s=>s.contributions.filter(c=>c.function_id===f.id).map(c=>({...c,skill:s}))).filter(c=>(effect==='all'||c.effect===effect)&&(query===''||((c.skill.name+' '+c.skill.repo+' '+f.label+' '+c.trigger+' '+f.definition).toLocaleLowerCase('es')).includes(query)));}
 function matches(f){return (owner==='all'||f.owners.includes(owner))&&(!query||textFor(f).includes(query))&&candidateList(f).length>0;}
 function functions(){return d.functions.filter(f=>(!routeOnly||currentRoute().functions.includes(f.id))&&matches(f))}
 function renderRoutes(){let el=$('capRouteButtons');el.innerHTML=d.routes.map(r=>`<button type="button" class="cap-route-btn" data-route="${esc(r.id)}" aria-pressed="${route===r.id}">${esc(r.name)}</button>`).join('');el.querySelectorAll('[data-route]').forEach(b=>b.addEventListener('click',()=>{route=b.dataset.route;routeOnly=true;let r=currentRoute();active=r.functions[0];owner='all';effect='all';query='';$('capOwner').value='all';$('capEffect').value='all';$('capSearch').value='';const hadFocus=document.activeElement===b;render();if(hadFocus)el.querySelector('[aria-pressed="true"]')?.focus({preventScroll:true});}));let r=currentRoute();$('capRouteDetails').innerHTML=`<div><strong>${esc(r.request)}</strong><p>${esc(r.tasks.join(' → '))}</p></div><div><div class="cap-flow">Panorama del escenario (no activación): G0 → ${esc(r.owners.join(' · '))}</div><p>${esc(r.stop)}</p></div>`;}
 function renderList(){const fs=functions(),elem=$('capFunctionList');$('capFound').textContent=String(fs.length);if(!fs.some(f=>f.id===active))active=fs[0]?.id||'';elem.innerHTML=fs.length?fs.map(f=>{let size=candidateList(f).length;return `<button type="button" class="cap-function" data-cap="${esc(f.id)}" role="option" tabindex="${f.id===active?0:-1}" aria-selected="${f.id===active}"><span class="cap-n">${size}</span><strong>${esc(f.label)}</strong><small>${esc(f.owners.join(' / ')||'Fuera del diseño')} · ${esc(f.nodes.join(' · '))}</small></button>`}).join(''):'<div class="cap-empty">Sin resultados para estos filtros. Prueba otra función o limpia la búsqueda.</div>';
 elem.querySelectorAll('[data-cap]').forEach(b=>b.addEventListener('click',()=>{active=b.dataset.cap;const hadFocus=document.activeElement===b;renderList();renderDetail();if(hadFocus)elem.querySelector('[aria-selected="true"]')?.focus({preventScroll:true})}));}
 function renderDetail(){const f=d.functions.find(f=>f.id===active);if(!f){$('capDetail').innerHTML='<p>Selecciona una función.</p>';return}const cand=candidateList(f);
 $('capDetail').innerHTML=`<div class="cap-focus">FUNCIÓN / ${esc(f.id)} · ${cand.length} FUENTES COMPATIBLES CON LOS FILTROS</div><h3>${esc(f.label)}</h3><p>${esc(f.definition)}</p><div class="cap-chips">${(f.owners.length?f.owners:['FUERA DEL ROUTER']).map(t=>`<span>${esc(t)}</span>`).join('')}${f.nodes.map(t=>`<span>${esc(t)}</span>`).join('')}</div><section class="cap-rectors"><div class="cap-section-name">Especialistas propios · gobiernan esta función</div>${f.owners.length ? f.owners.map(g=>{const o=d.owners[g];return o?`<div class="cap-owner-card"><strong>${esc(g)} · ${esc(o.name)}</strong><p>${esc(o.what)}</p><a href="${esc(o.source_url)}" rel="noopener noreferrer" target="_blank">Consultar skill rectora</a></div>`:''}).join('') : '<p>Fuera del dominio del router web. No se habilita G0 como ejecutor de infraestructura.</p>'}${d.mapped_baseline_support[f.id]?.length?`<p class="cap-baseline-note">También ya inventariada en el árbol: ${esc(d.mapped_baseline_support[f.id].join(' · '))}. No confundirla con una nueva incorporación.</p>`:''}</section><div class="cap-section-name cap-external-head">Capacidades externas propuestas · ${cand.length} vínculos</div>${cand.map(c=>{let s=c.skill;return `<article class="cap-entry" data-effect="${esc(c.effect)}"><div class="cap-entry-top"><h4>${esc(s.id)} · ${esc(s.name)}</h4><span class="cap-status">${esc(c.effect)} · ${esc(s.already_in_baseline?'Inventariada':'Nueva candidata')}</span></div><p><strong>Activa solo si:</strong> ${esc(c.trigger)}</p><p class="cap-guard"><strong>Límite:</strong> ${esc(s.guard)}${s.requires_explicit_invocation?' · Invocación explícita requerida.':''}</p><a href="${esc(s.source.url)}" target="_blank" rel="noopener noreferrer">Revisar SKILL.md fijada por commit</a></article>`}).join('')||'<div class="cap-empty">Sin skills para este filtro.</div>'}`;
 }
 function render(){renderRoutes();$('capShowAll').setAttribute('aria-pressed',String(!routeOnly));$('capShowAll').textContent=routeOnly?'Ver todas las funciones':'Solo la ruta actual';renderList();renderDetail()}
 function save(){const body=JSON.stringify(d,null,2),blob=new Blob([body],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='design-router-mapa-funcional-v1.0.json';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)}
 function close(){app.classList.remove('capability-active');$('capabilityPanel').setAttribute('aria-hidden','true');$('capabilityMapView').setAttribute('aria-pressed','false')}
 function open(){if(['all-active','proposal-active','comparison-active','semantic-active'].some(c=>app.classList.contains(c)))$('stageMapView').click();app.classList.add('capability-active');$('capabilityPanel').setAttribute('aria-hidden','false');['stageMapView','skillNetworkView','proposalBoardView','compareSkillsView','allComparisonsView'].forEach(id=>$(id).setAttribute('aria-pressed','false'));$('capabilityMapView').setAttribute('aria-pressed','true');render()}
 function init(){for(const g of ['G0','G1','G2','G3','G4','G5','G6','G7'])$('capOwner').insertAdjacentHTML('beforeend',`<option value="${g}">${g}</option>`);
 $('capabilityMapView').addEventListener('click',open);
 ['stageMapView','skillNetworkView','proposalBoardView','compareSkillsView','allComparisonsView'].forEach(id=>$(id).addEventListener('click',close,true));
 $('capSearch').addEventListener('input',e=>{query=e.target.value.trim().toLocaleLowerCase('es');if(query)routeOnly=false;render()});
 $('capFunctionList').addEventListener('keydown',event=>{
  const list=$('capFunctionList'),buttons=[...list.querySelectorAll('[data-cap]')];
  const index=buttons.indexOf(event.target);
  if(index<0)return;
  let next;
  switch(event.key){
   case 'ArrowDown':next=Math.min(index+1,buttons.length-1);break;
   case 'ArrowUp':next=Math.max(index-1,0);break;
   case 'Home':next=0;break;
   case 'End':next=buttons.length-1;break;
   default:return;
  }
  event.preventDefault();
  buttons[next].focus({preventScroll:true});
  buttons[next].click();
  list.querySelector('[aria-selected="true"]')?.scrollIntoView({block:'nearest',inline:'nearest'});
 });
 $('capOwner').addEventListener('change',e=>{owner=e.target.value;routeOnly=false;render()});
 $('capEffect').addEventListener('change',e=>{effect=e.target.value;routeOnly=false;render()});
 $('capShowAll').addEventListener('click',()=>{routeOnly=!routeOnly;render()});$('capReset').addEventListener('click',()=>{query='';owner='all';effect='all';routeOnly=false;$('capSearch').value='';$('capOwner').value='all';$('capEffect').value='all';render()});$('capExport').addEventListener('click',save);
 $('capFunctionCount').textContent=d.counts.functions;$('capSkillCount').textContent=d.counts.skills;$('capEdgeCount').textContent=d.counts.edges;
 render();open();$('capabilityMapView').scrollIntoView({block:'nearest',inline:'nearest'});
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
