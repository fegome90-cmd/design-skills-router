(()=>{
 'use strict';
 const el=id=>document.getElementById(id),data=JSON.parse(el('capabilityMapData').textContent),policy=JSON.parse(el('minRouteData').textContent),owners=data.owners;
 const escapeHtml=value=>String(value??'').replace(/[&<>"']/g,k=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[k]));
 const state={scope:'function',permit:'read',domain:'',reviews:{}};
 let lastContext='';
 const routeId=()=>el('capRouteButtons').querySelector('[aria-pressed="true"]')?.dataset.route || 'tipografia';
 const profile=()=>{if(state.scope==='function'&&selectedFunction()==='type-choice')return policy.profiles['solo-fuente'];if(state.scope==='function'&&selectedFunction()==='type-micro')return policy.profiles['solo-micro'];return policy.profiles[routeId()]||policy.profiles.tipografia;};
 const selectedFunction=()=>el('capFunctionList').querySelector('[data-cap][aria-selected="true"]')?.dataset.cap||data.routes.find(r=>r.id===routeId())?.functions[0]||'type-choice';
 const functionsSelected=()=>state.scope==='function'?[selectedFunction()]:data.routes.find(r=>r.id===routeId())?.functions||[];
 const functionById=Object.fromEntries(data.functions.map(f=>[f.id,f]));
 const skillById=Object.fromEntries(data.skills.map(s=>[s.id,s]));
 const context=()=>routeId()+'|'+state.scope+'|'+functionsSelected().join(',');
 const unique=x=>[...new Set(x)];
 function resolveOwner(id){
  if(policy.special_blocked.includes(id))return null;
  if(state.domain && (functionById[id]?.owners||[]).includes(state.domain))return state.domain;
  if(state.domain && id==='accessibility')return state.domain;
  const direct=policy.owner_by_function[id];if(direct)return direct;
  return policy.default_context_owner[routeId()]?.[id]||null;
 }
 function ownersSelected(){
  if(routeId()==='auditoria'&&!state.domain)return [];
  return unique(functionsSelected().map(resolveOwner).filter(Boolean));
 }
 const preserveReview=()=>state.reviews[context()]||(state.reviews[context()]={});
 function checkReview(owner,needed){const o=preserveReview()[owner]||{};return {status:o.status||(needed?'applies':'pending'),reason:o.reason||''}}
 function renderDomain(){
  const fids=functionsSelected();const ambiguous=fids.filter(id=>!resolveOwner(id)&&!policy.special_blocked.includes(id));const multi=fids.some(id=>(functionById[id]?.owners||[]).length>1&&!policy.owner_by_function[id]);
  const needsChoice=routeId()==='auditoria'||ambiguous.length>0||multi;
  el('minDomainArea').hidden=!needsChoice;
  if(needsChoice){
   const f=fids.map(id=>functionById[id]);
   let options=unique(f.flatMap(x=>x?.owners||[]).filter(x=>/^G[1-7]$/.test(x)));
   if(routeId()==='auditoria'||fids.includes('accessibility'))options=policy.reviewable_domains;
   if(state.domain && !options.includes(state.domain))state.domain='';
   el('minDomain').innerHTML='<option value="">Pendiente de delimitar</option>'+options.map(g=>`<option value="${g}" ${g===state.domain?'selected':''}>${g} · ${escapeHtml(owners[g]?.name||'Especialista')}</option>`).join('');
  }
 }
 function renderMain(){
  const fs=functionsSelected(),primary=ownersSelected(),p=profile();
  renderDomain();
  const titles=fs.map(id=>functionById[id]?.label||id);
  el('minFlow').innerHTML=`<span>${escapeHtml(p.mode)}</span><i>→</i><span>${escapeHtml(titles.join(' + '))}</span><i>→</i><span>${primary.length?escapeHtml(primary.join(' · ')):'Delimitar dominio'}</span><i>→</i><span>apoyos bajo condición</span>`;
  el('minPrimary').innerHTML=primary.length?primary.map(g=>`<div class="min-owner-row"><div class="min-owner-name">${escapeHtml(g)} · ${escapeHtml(owners[g]?.name||'Especialista')}</div><div class="min-owner-note">Revisión propuesta del nodo; no consta consulta real ni ejecución.</div><a target="_blank" rel="noopener noreferrer" href="${escapeHtml(owners[g]?.source_url||'#')}">SKILL.md fijada</a></div>`).join(''):`<p class="min-unknown">Falta delimitar dominio o función. No se activa automáticamente ningún especialista.</p>`;
  if(fs.some(id=>policy.special_blocked.includes(id)))el('minPrimary').innerHTML='<p class="min-unknown">Ruta excluida o no modelada. No es una autorización de ejecución.</p>';
  el('minPrereqs').innerHTML='<ul>'+p.prereqs.map(x=>`<li>${escapeHtml(x)}</li>`).join('')+'</ul><p class="min-note">'+escapeHtml(p.hint)+'</p>';
  const matches=data.skills.flatMap(s=>s.contributions.filter(c=>fs.includes(c.function_id)).map(c=>({...c,skill:s})));
  const read=matches.filter(c=>!policy.writes.includes(c.effect)&&c.effect!=='externo'&&c.effect!=='excluir');const write=matches.filter(c=>policy.writes.includes(c.effect));
  const all=[...read,...write];
  const rows=all.slice(0,10).map(c=>{
   const writes=policy.writes.includes(c.effect);const explicit=c.skill.requires_explicit_invocation;const readAudit=(routeId()==='auditoria');
   const label=writes?(readAudit?'ESCRITURA · PROHIBIDA':state.permit==='read'?'ESCRITURA · Sin permiso':'ESCRITURA · Gate externo'):'CONSULTA · Opcional';
   return `<div class="min-support-item ${writes?'is-write':''}"><div><strong>${escapeHtml(c.skill.name.charAt(0).toUpperCase()+c.skill.name.slice(1))}</strong><small>${escapeHtml(c.trigger)}${explicit?' · Requiere invocación explícita':''}</small></div><span>${escapeHtml(label)}</span></div>`;
  }).join('');
  el('minSupport').innerHTML='<div class="min-support-list">'+(rows||'<p class="min-note">No se identificaron apoyos para esta función.</p>')+'</div>'+(all.length>10?`<p class="min-support-warning">${all.length-10} contribuciones adicionales en las fichas del mapa inferior.</p>`:'')+`<p class="min-support-warning">${read.length} consultas propuestas · ${write.length} intervenciones que podrían requerir edición. ${state.permit==='sandbox'?'Edición simulada: no concede permisos ni activa herramientas.':'La edición sigue sin permiso en esta simulación.'}</p>`;
  renderCoverage(primary);
 }
 function renderCoverage(primary){
  let applies=0,pending=0,na=0,invalid=0;
  el('minCoverage').innerHTML=policy.reviewable_domains.map(g=>{
   const rec=checkReview(g,primary.includes(g));const expected=primary.includes(g);
   const conflict=expected&&rec.status==='not_applicable';const empty=rec.status==='not_applicable'&&!rec.reason.trim();
   const status=conflict?'Contradicción: función requerida':empty?'Falta justificar':rec.status==='applies'?'Aplica · por revisar':rec.status==='not_applicable'?'No aplica (propuesto)':'Pendiente de revisar';
   if(conflict||empty)invalid++;else if(rec.status==='applies')applies++;else if(rec.status==='not_applicable')na++;else pending++;
   const input=rec.status==='not_applicable'?`<input type="text" aria-label="Justificación ${g}" data-review-reason="${g}" value="${escapeHtml(rec.reason)}" placeholder="Razón concreta de no aplicabilidad…"/>`:'';
   return `<div class="min-review-row" data-review-owner="${g}" data-primary="${expected}" data-conflict="${conflict}"><div class="min-review-top"><strong>${g} · ${escapeHtml(owners[g]?.name||'')}</strong><select data-review-status="${g}" aria-label="Aplicabilidad de ${g}"><option value="pending" ${rec.status==='pending'?'selected':''}>Pendiente</option><option value="applies" ${rec.status==='applies'?'selected':''}>Aplica</option><option value="not_applicable" ${rec.status==='not_applicable'?'selected':''}>No aplica</option></select></div><p>${expected?'Pertenece a la ruta mínima propuesta; aún hay que revisar la fuente.':'No activado para esta función; aplicabilidad aún no evaluada.'}</p>${input}<div class="min-review-status ${empty||conflict?'is-invalid':''}">${escapeHtml(status)}</div></div>`;
  }).join('');
  el('minCoverageSummary').innerHTML=`<span class="min-cover-summary">${applies} en alcance · ${pending} pendientes · ${na} N/A justificados · ${invalid} conflictos / razones faltantes · 0 verificaciones de ejecución</span>`;
 }
 function exportSelection(){
  const fs=functionsSelected(),primary=ownersSelected();const assessments={};policy.reviewable_domains.forEach(g=>{const x=checkReview(g,primary.includes(g));assessments[g]={applicability:x.status,reason:x.reason,reviewed:false,verified:false,approved:false};});
  const doc={schema:'design-router-minimal-selection-export/1.1',source:'research-board, not a runtime authorization',selected_route:routeId(),selected_scope:state.scope,selected_functions:fs,proposed_owners:primary,mode:profile().mode,simulated_permission:state.permit,source_pins:primary.map(g=>({id:g,commit:owners[g]?.commit,git_blob:owners[g]?.git_blob})),prerequisites:profile().prereqs,applicability:assessments,human_gate:'NOT_APPROVED',skills_executed:[],notes:policy.notes};
  const blob=new Blob([JSON.stringify(doc,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='design-router-seleccion-minima-v1.1-expediente.json';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
 }
 function refresh(){const key=context();if(key!==lastContext){state.domain='';lastContext=key;}renderMain()}
 function init(){
  el('minScope').addEventListener('change',e=>{state.scope=e.target.value;refresh()});
  el('minPermit').addEventListener('change',e=>{state.permit=e.target.value;renderMain()});
  el('minDomain').addEventListener('change',e=>{state.domain=e.target.value;renderMain()});
  el('minReviewToggle').addEventListener('click',()=>{const hidden=el('minCoverage').hidden;el('minCoverage').hidden=!hidden;el('minReviewToggle').setAttribute('aria-expanded',String(hidden));el('minReviewToggle').textContent=hidden?'Ocultar revisión':'Revisar dominios'});
  el('minCoverage').addEventListener('change',e=>{
   const g=e.target.dataset.reviewStatus||e.target.dataset.reviewReason;if(!g)return;
   const x=preserveReview()[g]||{};
   if(e.target.dataset.reviewStatus){x.status=e.target.value;if(x.status!=='not_applicable')x.reason='';}
   if(e.target.dataset.reviewReason)x.reason=e.target.value;
   preserveReview()[g]=x;renderCoverage(ownersSelected());
  });
  el('minExport').addEventListener('click',exportSelection);
  el('capRouteButtons').addEventListener('click',e=>{if(e.target.closest('[data-route]'))refresh()});
  el('capFunctionList').addEventListener('click',e=>{if(e.target.closest('[data-cap]'))refresh()});
  for(const id of ['capShowAll','capReset','capOwner','capEffect','capSearch'])el(id).addEventListener(id==='capSearch'?'input':'click',()=>queueMicrotask(refresh));
  refresh();
  window.__minimalRouterPreview={getState:()=>({route:routeId(),scope:state.scope,functions:functionsSelected(),owners:ownersSelected(),reviews:JSON.parse(JSON.stringify(state.reviews))})};
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
