(function(){'use strict';document.addEventListener('DOMContentLoaded',function(){
  const el=document.getElementById('individualSkillReviewData');const data=JSON.parse(el.textContent);
  const download=document.getElementById('skill-review-download');const jump=document.getElementById('skill-review-jump');
  download.addEventListener('click',()=>{const u=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=u;a.download='design-router-skill-X05-ui-radar-review-v0.7.json';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),1800);});
  jump.addEventListener('click',()=>{document.getElementById('stageMapView').click();const q=document.getElementById('searchInput');q.value='ART01';q.dispatchEvent(new Event('input',{bubbles:true}));});
  window.__skillReviewX05={status:data.status, subject:data.subject.name,tests:data.test_cases.length};
});})();