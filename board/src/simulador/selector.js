(()=>{
 'use strict';
 const {resolveSelection}=(()=>{
  const module={exports:{}};
__MIN_ROUTE_SELECTION_CORE__
  return module.exports;
 })();
 const el=id=>document.getElementById(id),data=JSON.parse(el('capabilityMapData').textContent),policy=JSON.parse(el('minRouteData').textContent),owners=data.owners;
 const escapeHtml=value=>String(value??'').replace(/[&<>"']/g,k=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[k]));
 const state={scope:'function',permit:'read',domain:'',reviews:{}};
 let lastContext='';
 const domainsByContext=new Map();
 const routesById=new Map(data.routes.map(route=>[route.id,route]));
 const functionById=Object.fromEntries(data.functions.map(f=>[f.id,f]));
 const dependencies={catalog:data,policy};
 const emptyReviews={};

 function selectionInput(){
  const route=el('capRouteButtons').querySelector('[aria-pressed="true"]')?.dataset.route||'tipografia';
  const functionId=el('capFunctionList').querySelector('[data-cap][aria-selected="true"]')?.dataset.cap||'';
  return {route,scope:state.scope,functionId};
 }
 function selectionKey({route,scope,functionId}){
  const functions=scope==='function'?functionId:(routesById.get(route)?.functions||[]).join(',');
  return `${route}|${scope}|${functions}`;
 }
 const reviewKey=(key,domain)=>domain?`${key}|${domain}`:key;
 function activeReviews(){
  const key=reviewKey(selectionKey(selectionInput()),state.domain);
  return state.reviews[key]||(state.reviews[key]={});
 }
 function resolveCurrent(input,key=selectionKey(input)){
  const query={...input,domain:state.domain,permit:state.permit};
  const reviewsFor=domain=>state.reviews[reviewKey(key,domain)]||emptyReviews;
  const reviews=reviewsFor(query.domain);
  const selection=resolveSelection({...query,reviews},dependencies);
  const normalizedReviews=reviewsFor(selection.domain);
  return normalizedReviews===reviews?selection:
   resolveSelection({...query,domain:selection.domain,reviews:normalizedReviews},dependencies);
 }
 function renderDomain({domain,domainOptions,showDomain}){
  el('minDomainArea').hidden=!showDomain;
  if(!showDomain){
   el('minDomain').value='';
   return;
  }
  el('minDomain').innerHTML='<option value="">Pendiente de delimitar</option>'+domainOptions.map(g=>`<option value="${g}" ${g===domain?'selected':''}>${g} · ${escapeHtml(owners[g]?.name||'Especialista')}</option>`).join('');
 }
 function renderPermission({audit,permit}){
  const select=el('minPermit');
  select.querySelector('option[value="sandbox"]').disabled=audit;
  select.value=permit;
  const note=el('minPermitNote');
  const message=audit?'Auditoría en solo lectura. La simulación de sandbox queda deshabilitada.':'';
  if(note.textContent!==message)note.textContent=message;
  note.hidden=!audit;
  if(audit)select.setAttribute('aria-describedby',note.id);
  else select.removeAttribute('aria-describedby');
 }
 function renderMain(input=selectionInput(),key=selectionKey(input)){
  const selection=resolveCurrent(input,key);
  const {selectedFunctions:fs,owners:primary,profile:p,domain,permit,audit,support:{read,write},validation}=selection;
  state.domain=domain;
  state.permit=permit;
  renderPermission(selection);
  renderDomain(selection);
  const auditRoute=input.route==='auditoria';
  const titles=fs.map(id=>functionById[id]?.label||id);
  const missingFunction=input.scope==='function'&&!input.functionId;
  if(!titles.length){
   if(missingFunction)titles.push('Sin función seleccionada');
   else if(auditRoute)titles.push(domain?'Sin función aplicable':'Evaluación pendiente');
  }
  const illustrative=['Lightweight','Subgraph'].includes(p.mode);
  const mode=illustrative?`${p.mode} · Orientativo`:p.mode;
  el('minModeNote').hidden=!illustrative;
  el('minFlow').innerHTML=`<span>${escapeHtml(mode)}</span><i>→</i><span>${escapeHtml(titles.join(' + '))}</span><i>→</i><span>${primary.length?escapeHtml(primary.join(' · ')):(missingFunction?'Seleccionar función':auditRoute&&domain?'Revisar función y dominio':'Delimitar dominio')}</span><i>→</i><span>apoyos bajo condición</span>`;
  el('minPrimary').innerHTML=primary.length?primary.map(g=>`<div class="min-owner-row"><div class="min-owner-name">${escapeHtml(g)} · ${escapeHtml(owners[g]?.name||'Especialista')}</div><div class="min-owner-note">Revisión propuesta del nodo; no consta consulta real ni ejecución.</div><a target="_blank" rel="noopener noreferrer" href="${escapeHtml(owners[g]?.source_url||'#')}">SKILL.md fijada</a></div>`).join(''):`<p class="min-unknown">Falta delimitar dominio o función. No se activa automáticamente ningún especialista.</p>`;
  if(validation.errors.some(error=>error.code==='AUDIT_FUNCTION_OUTSIDE_DOMAIN'))el('minPrimary').innerHTML='<p class="min-unknown">La función seleccionada queda fuera del dominio de auditoría. Elige una función compatible o ajusta el dominio.</p>';
  if(validation.errors.some(error=>error.code==='FUNCTION_NOT_PROPOSABLE'))el('minPrimary').innerHTML='<p class="min-unknown">Ruta excluida o no modelada. No es una autorización de ejecución.</p>';
  el('minPrereqs').innerHTML='<ul>'+p.prereqs.map(x=>`<li>${escapeHtml(x)}</li>`).join('')+'</ul><p class="min-note">'+escapeHtml(p.hint)+'</p>';
  const support=el('minSupport');
  const openGroups=new Set([...support.querySelectorAll('details[open]')].map(group=>group.dataset.effectGroup));
  const focusedGroup=support.contains(document.activeElement)?document.activeElement.closest('details')?.dataset.effectGroup:null;
  const writingLabel=audit?'Escritura prohibida en auditoría':permit==='read'?'Escritura sin permiso':'Edición simulada · requiere autorización externa';
  const groups=[
   {id:'write', title:'Intervenciones de escritura', items:write},
   {id:'read', title:'Consultas opcionales', items:read}
  ];
  const groupMarkup=groups.map(({id,title,items})=>{
   if(!items.length)return `<p class="min-support-count">0 ${escapeHtml(title.toLowerCase())}</p>`;
   const writes=id==='write';
   const rows=items.map(({skill,trigger,function_id})=>`
    <li class="min-support-item ${writes?'is-write':''}">
     <strong>${escapeHtml(skill.name)}</strong>
     <small>${escapeHtml(functionById[function_id]?.label||function_id)}</small>
     <small>${escapeHtml(trigger)}${skill.requires_explicit_invocation?' · Requiere invocación explícita':''}</small>
    </li>`).join('');
   return `<details data-effect-group="${id}" ${openGroups.has(id)?'open':''}>
    <summary>${items.length} ${escapeHtml(title.toLowerCase())}</summary>
     <ul class="min-support-list">${rows}</ul>
   </details>`;
  });
  support.innerHTML=groupMarkup.join('');
  if(write.length)support.insertAdjacentHTML('beforeend',`<p class="min-support-warning">${escapeHtml(writingLabel)}.</p>`);
  if(focusedGroup)support.querySelector(`[data-effect-group="${focusedGroup}"] > summary`)?.focus({preventScroll:true});
  renderCoverage(selection);
 }
 function renderCoverage({owners:primary,assessments,counts,completeness,validation}){
  const coverage=el('minCoverage');
  if(!coverage.firstElementChild){
   coverage.innerHTML=Object.keys(assessments).map(g=>`
    <div class="min-review-row" data-review-owner="${g}">
     <div class="min-review-top"><strong>${g} · ${escapeHtml(owners[g]?.name||'')}</strong>
      <select data-review-status="${g}" aria-label="Aplicabilidad de ${g}" aria-describedby="minReviewStatus-${g}">
       <option value="pending">Pendiente</option><option value="applies">Aplica</option><option value="not_applicable">No aplica</option>
      </select>
     </div>
     <p></p>
     <input type="text" aria-label="Justificación ${g}" aria-describedby="minReviewStatus-${g}" data-review-reason="${g}" placeholder="Razón concreta de no aplicabilidad…" hidden>
     <div id="minReviewStatus-${g}" class="min-review-status"></div>
    </div>`).join('');
  }
  for(const row of coverage.querySelectorAll('[data-review-owner]')){
   const g=row.dataset.reviewOwner;
   const {applicability,reason}=assessments[g];
   const expected=primary.includes(g);
   const errors=validation.errors.filter(error=>error.domain===g);
   const select=row.querySelector('select'),input=row.querySelector('input'),note=row.querySelector('p');
   const status=row.querySelector('.min-review-status');
   row.dataset.primary=String(expected);
   row.dataset.conflict=String(errors.some(error=>error.code==='REQUIRED_DOMAIN_NOT_APPLICABLE'));
   if(select.value!==applicability)select.value=applicability;
   if(input.value!==reason)input.value=reason;
   input.hidden=applicability!=='not_applicable';
   input.style.display=input.hidden?'none':'';
   input.setAttribute('aria-invalid',String(errors.some(error=>error.code==='MISSING_JUSTIFICATION')));
   select.setAttribute('aria-invalid',row.dataset.conflict);
   const noteText=expected?'Pertenece a la ruta mínima propuesta. La fuente sigue por revisar.':'Queda fuera de la ruta mínima propuesta.';
   if(note.textContent!==noteText)note.textContent=noteText;
   const statusText=errors.length?errors.map(error=>error.message).join(' '):
    applicability==='applies'?'Aplica · por revisar':applicability==='not_applicable'?'No aplica (propuesto)':'Pendiente de revisar';
   if(status.textContent!==statusText)status.textContent=statusText;
   status.classList.toggle('is-invalid',errors.length>0);
  }
  const summary=el('minCoverageSummary');
  summary.classList.add('min-cover-summary');
  if(!summary.hasAttribute('aria-live'))summary.setAttribute('aria-live','polite');
  if(!summary.hasAttribute('aria-atomic'))summary.setAttribute('aria-atomic','true');
  const domainMessage=validation.errors.filter(error=>!error.domain).map(error=>error.message).join(' ');
  const summaryText=[
   `${counts.applies} en alcance · ${counts.pending} pendientes · ${counts.notApplicable} N/A justificados`,
   completeness.complete?'Cobertura completa':'Cobertura incompleta',
   validation.valid?'Sin errores de validación':`${validation.errors.length} errores de validación`,
   domainMessage,'Ejecución sin autorización'
  ].filter(Boolean).join(' · ');
  if(summary.textContent!==summaryText)summary.textContent=summaryText;
 }
 function exportSelection(){
  const input=selectionInput();
  const {selectedFunctions,requestedFunctions,domain,owners:primary,profile,permit,assessments,completeness,validation}=resolveCurrent(input);
  const {mode,prereqs}=profile;
  const draft=!validation.valid||!completeness.complete;
  const doc={
   schema:'design-router-minimal-selection-export/1.2',
   source:'research-board, not a runtime authorization',
   status:draft?'DRAFT':'PROPOSAL',
   selected_route:input.route,selected_scope:input.scope,selected_functions:selectedFunctions,requested_functions:requestedFunctions,
   selected_domain:domain||null,
   policy_version:policy.policy_version||policy.schema,
   policy_hash:'__MIN_ROUTE_POLICY_SHA256__',
   proposed_owners:primary,mode,mode_status:/lightweight|subgraph/i.test(mode)?'ORIENTATION_ONLY':'SIMULATED',
   simulated_permission:permit,
   source_pins:primary.map(g=>({id:g,commit:owners[g]?.commit,git_blob:owners[g]?.git_blob})),
   prerequisites:prereqs,applicability:assessments,completeness,validation,
   human_gate:'NOT_APPROVED',skills_executed:[],notes:policy.notes
  };
  const blob=new Blob([JSON.stringify(doc,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),link=document.createElement('a');
  link.href=url;
  link.download=`design-router-seleccion-minima-v1.2-expediente${draft?'-borrador':''}.json`;
  document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
 }
 function refresh(){
  const input=selectionInput(),key=selectionKey(input);
  if(key!==lastContext){
   state.domain=domainsByContext.get(key)||'';
   lastContext=key;
  }
  renderMain(input,key);
 }
 function init(){
  el('minScope').addEventListener('change',e=>{state.scope=e.target.value;refresh()});
  el('minPermit').addEventListener('change',e=>{state.permit=e.target.value;renderMain()});
  el('minDomain').addEventListener('change',e=>{
   state.domain=e.target.value;
   domainsByContext.set(selectionKey(selectionInput()),state.domain);
   renderMain();
  });
  el('minReviewToggle').addEventListener('click',()=>{const hidden=el('minCoverage').hidden;el('minCoverage').hidden=!hidden;el('minReviewToggle').setAttribute('aria-expanded',String(hidden));el('minReviewToggle').textContent=hidden?'Ocultar revisión':'Revisar dominios'});
  el('minCoverage').addEventListener('change',e=>{
   const owner=e.target.dataset.reviewStatus;if(!owner)return;
   const reviews=activeReviews(),record=reviews[owner]||{};
   const status=e.target.value;
   reviews[owner]={status,reason:status==='not_applicable'?record.reason||'':''};
   renderCoverage(resolveCurrent(selectionInput()));
  });
  el('minCoverage').addEventListener('input',e=>{
   const owner=e.target.dataset.reviewReason;if(!owner)return;
   const reviews=activeReviews();
   reviews[owner]={...reviews[owner],reason:e.target.value};
   renderCoverage(resolveCurrent(selectionInput()));
  });
  el('minExport').addEventListener('click',exportSelection);
  el('capRouteButtons').addEventListener('click',e=>{if(e.target.closest('[data-route]'))refresh()});
  el('capFunctionList').addEventListener('click',e=>{if(e.target.closest('[data-cap]'))refresh()});
  for(const [id,event] of Object.entries({capShowAll:'click',capReset:'click',capOwner:'change',capEffect:'change',capSearch:'input'})){
   el(id).addEventListener(event,()=>queueMicrotask(refresh));
  }
  refresh();
  window.__minimalRouterPreview={getState:()=>{
   const input=selectionInput();
   const {selectedFunctions,owners}=resolveCurrent(input);
   return {route:input.route,scope:input.scope,functions:selectedFunctions,owners,reviews:JSON.parse(JSON.stringify(state.reviews))};
  },getSelection:()=>resolveCurrent(selectionInput())};
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();