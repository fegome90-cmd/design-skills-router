(function(){'use strict';
const data=JSON.parse(document.getElementById('cmpData').textContent);
const app=document.querySelector('.app');
const $=s=>document.querySelector(s);
const byId=s=>document.getElementById(s);
const escape=s=>String(s??'').replace(/[&<>"']/g,k=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[k]));
const legends={different:'Δ DIFERENCIA',complement:'↔ COMPLEMENTO',tension:'! TENSIÓN',shared:'= COINCIDENCIA'};
let subject='impeccable',filter='all';
function cardSource(key,cls){const d=data.sources[key];return `<div class="cmp-source-head ${cls}"><span class="source-tag">${cls==='external'?'B / REFERENCIA EXTERNA':'A / SKILL COMPARADA'}</span><h3>${escape(d.name)}</h3><p>${escape(d.role)} · ${escape(d.org)}</p><a href="${escape(d.uri)}" target="_blank" rel="noopener noreferrer">Ver SKILL.md en commit ${escape(d.commit.slice(0,8))} ↗</a><div class="cmp-source-tag" style="font:500 var(--text-2xs) var(--mono);color:#636273;margin-top:7px">Git blob ${escape(d.git_blob.slice(0,12))}…</div></div>`}
function render(){let cfg=data.comparisons[subject],items=cfg.rows.filter(x=>filter==='all'||x.kind===filter);
byId('cmpHeaders').innerHTML=cardSource(subject,'owned')+'<div class="cmp-center-label">VS</div>'+cardSource('radar','external');
byId('cmpRows').innerHTML=items.length?items.map(r=>`<article class="cmp-row" data-kind="${escape(r.kind)}" id="cmp-${escape(subject)}-${r.id}">
 <div class="cmp-row-heading"><span class="cmp-index">${escape(r.id)}</span><span class="cmp-aspect">${escape(r.title)}</span><span class="cmp-kind">${legends[r.kind]}</span></div>
 <div class="cmp-cells"><div class="cmp-cell"><span class="cmp-col-flag">${escape(r.left_label)}</span><p>${escape(r.left)}</p></div><span aria-hidden="true" class="cmp-axis">${r.kind==='shared'?'=':r.kind==='tension'?'!':r.kind==='complement'?'↔':'≠'}</span><div class="cmp-cell external"><span class="cmp-col-flag">${escape(r.right_label)}</span><p>${escape(r.right)}</p></div></div><details><summary>Razón de la diferencia · prueba de aceptación</summary><div class="cmp-details"><p><b>INTERPRETACIÓN</b>${escape(r.why)}</p><p><b>TEST NEGATIVO / POSITIVO</b>${escape(r.test)}</p></div></details></article>`).join(''):'<p class="cmp-empty">No hay filas para este filtro.</p>';
byId('cmpBottom').innerHTML=`<strong>${escape(cfg.verdict)}</strong><p>${escape(cfg.counts_as_skill)}</p><div class="cmp-note">Nodos: ${escape(cfg.nodes.join(' · '))} · Comparación documental no ejecutable · Baseline v0.4 intacto</div>`;
byId('cmpCount').textContent=items.length+' / '+cfg.rows.length+' aspectos';
document.querySelectorAll('[data-cmpfilter]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.cmpfilter===filter)));
}
function download(name,contents,type){let u=URL.createObjectURL(new Blob([contents],{type}));let a=document.createElement('a');a.href=u;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),1500)}
function markdown(){let c=data.comparisons[subject],a=data.sources[subject],b=data.sources.radar,lines=[`# Diferencias semánticas · ${a.name} vs ${b.name}`,'','*Comparación documental, no diff de líneas ni aprobación.*','','Fuentes:',`- ${a.uri}`,`- ${b.uri}`,'',`**Dictamen:** ${c.verdict}`,''];for(let r of c.rows){lines.push(`## ${r.id} · ${r.title} (${legends[r.kind]})`,'',`**${a.name} (${r.left_label}):** ${r.left}`,'',`**${b.name} (${r.right_label}):** ${r.right}`,'',`**Diferencia:** ${r.why}`,'',`**Prueba:** ${r.test}`,'')}return lines.join('\n')}
function close(){app.classList.remove('comparison-active');byId('comparisonPanel').setAttribute('aria-hidden','true');byId('compareSkillsView').setAttribute('aria-pressed','false')}
function open(){if(app.classList.contains('semantic-active')||app.classList.contains('proposal-active')) byId('stageMapView').click();app.classList.add('comparison-active');byId('comparisonPanel').setAttribute('aria-hidden','false');['stageMapView','skillNetworkView','proposalBoardView'].forEach(id=>byId(id).setAttribute('aria-pressed','false'));byId('compareSkillsView').setAttribute('aria-pressed','true');byId('cmpScroll').scrollTop=0;render()}
function init(){byId('compareSkillsView').addEventListener('click',open);for(let id of ['stageMapView','skillNetworkView','proposalBoardView'])byId(id).addEventListener('click',close,true);
byId('cmpSubject').addEventListener('change',e=>{subject=e.target.value;filter='all';render();byId('cmpScroll').scrollTop=0});
document.querySelectorAll('[data-cmpfilter]').forEach(b=>b.addEventListener('click',()=>{filter=b.dataset.cmpfilter;render()}));
byId('cmpExport').addEventListener('click',()=>download(`design-router-diff-${subject}-ui-radar-v0.8.json`,JSON.stringify({subject,reference:'radar',method:data.comparison_method,comparison:data.comparisons[subject],sources:{subject:data.sources[subject],radar:data.sources.radar}},null,2),'application/json'));
byId('cmpReport').addEventListener('click',()=>download(`design-router-diff-${subject}-ui-radar-v0.8.md`,markdown(),'text/markdown'));
window.__routerSemanticDiff={get subject(){return subject},get filter(){return filter},get displayed(){return byId('cmpRows').querySelectorAll('.cmp-row').length},get data(){return data},render,open,close};
open();}
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init);else init();
})();