/* Rulers and measurements on demand: @scena/guides draws the rulers and guides; this file only wires them. */
(function(){
 const PX_PER_CM=96/2.54, RULER=20;
 const toggle=document.getElementById('measureToggle');
 if(!toggle||typeof window.Guides!=='function')return;
 let layer=null, box=null, tip=null, rulers=[];
 const css=name=>getComputedStyle(document.documentElement).getPropertyValue(name).trim();
 // direction:'start' draws labels with a top baseline 17px in; textOffset pulls them back inside the 20px bar.
 const common=type=>({direction:'start',textOffset:type==='horizontal'?[0,-7]:[-7,0],backgroundColor:'#fffdfa',lineColor:'#b9b3aa',textColor:'#575c72',font:`9px ${css('--mono')||'monospace'}`,useResizeObserver:true});
 // Pixel rulers own the guides; cm rulers only read. Each ruler starts at 0, and guidesOffset adds back the ruler bar
 // so a guide reads its viewport coordinate.
 const pxRuler=(el,type)=>new Guides(el,{...common(type),type,unit:50,segment:5,guidesOffset:-RULER,displayDragPos:true,displayGuidePos:true,
  guideStyle:{background:'#4057bd'},dragGuideStyle:{background:'#4057bd'},guidePosStyle:{color:'#4057bd'},
  dragPosFormat:v=>`${Math.round(v)} px`,guidePosFormat:v=>`${Math.round(v)} px`});
 const cmRuler=(el,type)=>new Guides(el,{...common(type),type,zoom:PX_PER_CM,unit:1,segment:10,showGuides:false,textFormat:v=>`${v}`});
 const mm=px=>(px/PX_PER_CM*10).toLocaleString('es-CL',{maximumFractionDigits:1});
 function build(){
  layer=document.createElement('div');layer.className='measure-layer';layer.id='measureLayer';layer.hidden=true;
  layer.setAttribute('aria-hidden','true');
  layer.innerHTML='<div class="measure-ruler" data-edge="top"></div><div class="measure-ruler" data-edge="left"></div><div class="measure-ruler" data-edge="bottom"></div><div class="measure-ruler" data-edge="right"></div>'+
   '<div class="measure-corner" data-corner="tl">px</div><div class="measure-corner" data-corner="tr">px</div><div class="measure-corner" data-corner="bl">cm</div><div class="measure-corner" data-corner="br">cm</div>'+
   '<div class="measure-box" hidden></div><div class="measure-tip" hidden></div>';
  document.body.append(layer);
  const q=s=>layer.querySelector(s);
  box=q('.measure-box');tip=q('.measure-tip');
  rulers=[pxRuler(q('[data-edge="top"]'),'horizontal'),pxRuler(q('[data-edge="left"]'),'vertical'),
   cmRuler(q('[data-edge="bottom"]'),'horizontal'),cmRuler(q('[data-edge="right"]'),'vertical')];
 }
 function measure(e){
  const t=e.target;
  if(!(t instanceof Element)||layer.contains(t)||t===document.documentElement||t===document.body){box.hidden=tip.hidden=true;return;}
  const r=t.getBoundingClientRect();
  if(!r.width&&!r.height){box.hidden=tip.hidden=true;return;}
  Object.assign(box.style,{left:r.left+'px',top:r.top+'px',width:r.width+'px',height:r.height+'px'});box.hidden=false;
  const name=t.id?'#'+t.id:(t.classList[0]?'.'+t.classList[0]:t.tagName.toLowerCase());
  tip.innerHTML='';tip.append(`${Math.round(r.width)} × ${Math.round(r.height)} px`);
  const sub=document.createElement('span');sub.textContent=` · ${mm(r.width)} × ${mm(r.height)} mm · ${name}`;tip.append(sub);
  tip.hidden=false;
  const w=tip.offsetWidth,h=tip.offsetHeight;
  let x=e.clientX+14,y=e.clientY+16;
  if(x+w>innerWidth-RULER-4)x=e.clientX-w-10;
  if(y+h>innerHeight-RULER-4)y=e.clientY-h-12;
  tip.style.left=Math.max(RULER+4,x)+'px';tip.style.top=Math.max(RULER+4,y)+'px';
 }
 const hideMeasure=()=>{if(box){box.hidden=tip.hidden=true;}};
 function setActive(on){
  if(on&&!layer)build();
  if(!layer)return;
  layer.hidden=!on;toggle.setAttribute('aria-pressed',String(on));
  if(on){rulers.forEach(g=>g.resize());document.addEventListener('pointermove',measure,{passive:true});document.addEventListener('pointerleave',hideMeasure);}
  else{document.removeEventListener('pointermove',measure);document.removeEventListener('pointerleave',hideMeasure);hideMeasure();}
 }
 toggle.addEventListener('click',()=>setActive(toggle.getAttribute('aria-pressed')!=='true'));
 // R toggles the layer unless the user is typing.
 document.addEventListener('keydown',e=>{
  if(e.key.toLowerCase()!=='r'||e.altKey||e.ctrlKey||e.metaKey||e.repeat)return;
  const t=e.target;if(t instanceof Element&&t.closest('input,textarea,select,[contenteditable]:not([contenteditable="false"])'))return;
  e.preventDefault();setActive(toggle.getAttribute('aria-pressed')!=='true');
 });
})();
