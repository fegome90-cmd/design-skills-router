var Ut=globalThis,It=Ut.trustedTypes,Ue=It?It.createPolicy("lit-html",{createHTML:t=>t}):void 0,ae="$lit$",J=`lit$${Math.random().toFixed(9).slice(2)}$`,le="?"+J,vr=`<${le}>`,ut=document,Tt=()=>ut.createComment(""),kt=t=>t===null||typeof t!="object"&&typeof t!="function",ce=Array.isArray,si=t=>ce(t)||typeof t?.[Symbol.iterator]=="function",se=`[ 	
\f\r]`,Rt=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,Ie=/-->/g,Fe=/>/g,ht=RegExp(`>|${se}(?:([^\\s"'>=/]+)(${se}*=${se}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),Ve=/'/g,je=/"/g,ni=/^(?:script|style|textarea|title)$/i,he=t=>(e,...i)=>({_$litType$:t,strings:e,values:i}),M=he(1),ai=he(2),li=he(3),ot=Symbol.for("lit-noChange"),C=Symbol.for("lit-nothing"),We=new WeakMap,pt=ut.createTreeWalker(ut,129);function ci(t,e){if(!ce(t)||!t.hasOwnProperty("raw"))throw Error("invalid template strings array");return Ue!==void 0?Ue.createHTML(e):e}var hi=(t,e)=>{let i=t.length-1,r=[],o,s=e===2?"<svg>":e===3?"<math>":"",n=Rt;for(let a=0;a<i;a++){let l=t[a],c,p,h=-1,f=0;for(;f<l.length&&(n.lastIndex=f,p=n.exec(l),p!==null);)f=n.lastIndex,n===Rt?p[1]==="!--"?n=Ie:p[1]!==void 0?n=Fe:p[2]!==void 0?(ni.test(p[2])&&(o=RegExp("</"+p[2],"g")),n=ht):p[3]!==void 0&&(n=ht):n===ht?p[0]===">"?(n=o??Rt,h=-1):p[1]===void 0?h=-2:(h=n.lastIndex-p[2].length,c=p[1],n=p[3]===void 0?ht:p[3]==='"'?je:Ve):n===je||n===Ve?n=ht:n===Ie||n===Fe?n=Rt:(n=ht,o=void 0);let u=n===ht&&t[a+1].startsWith("/>")?" ":"";s+=n===Rt?l+vr:h>=0?(r.push(c),l.slice(0,h)+ae+l.slice(h)+J+u):l+J+(h===-2?a:u)}return[ci(t,s+(t[i]||"<?>")+(e===2?"</svg>":e===3?"</math>":"")),r]},ne=class pi{constructor({strings:e,_$litType$:i},r){let o;this.parts=[];let s=0,n=0,a=e.length-1,l=this.parts,[c,p]=hi(e,i);if(this.el=pi.createElement(c,r),pt.currentNode=this.el.content,i===2||i===3){let h=this.el.content.firstChild;h.replaceWith(...h.childNodes)}for(;(o=pt.nextNode())!==null&&l.length<a;){if(o.nodeType===1){if(o.hasAttributes())for(let h of o.getAttributeNames())if(h.endsWith(ae)){let f=p[n++],u=o.getAttribute(h).split(J),g=/([.?@])?(.*)/.exec(f);l.push({type:1,index:s,name:g[2],strings:u,ctor:g[1]==="."?fi:g[1]==="?"?mi:g[1]==="@"?gi:Mt}),o.removeAttribute(h)}else h.startsWith(J)&&(l.push({type:6,index:s}),o.removeAttribute(h));if(ni.test(o.tagName)){let h=o.textContent.split(J),f=h.length-1;if(f>0){o.textContent=It?It.emptyScript:"";for(let u=0;u<f;u++)o.append(h[u],Tt()),pt.nextNode(),l.push({type:2,index:++s});o.append(h[f],Tt())}}}else if(o.nodeType===8)if(o.data===le)l.push({type:2,index:s});else{let h=-1;for(;(h=o.data.indexOf(J,h+1))!==-1;)l.push({type:7,index:s}),h+=J.length-1}s++}}static createElement(e,i){let r=ut.createElement("template");return r.innerHTML=e,r}};function dt(t,e,i=t,r){var o,s,n;if(e===ot)return e;let a=r!==void 0?(o=i._$Co)==null?void 0:o[r]:i._$Cl,l=kt(e)?void 0:e._$litDirective$;return a?.constructor!==l&&((s=a?._$AO)==null||s.call(a,!1),l===void 0?a=void 0:(a=new l(t),a._$AT(t,i,r)),r!==void 0?((n=i._$Co)!=null?n:i._$Co=[])[r]=a:i._$Cl=a),a!==void 0&&(e=dt(t,a._$AS(t,e.values),a,r)),e}var ui=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){var e;let{el:{content:i},parts:r}=this._$AD,o=((e=t?.creationScope)!=null?e:ut).importNode(i,!0);pt.currentNode=o;let s=pt.nextNode(),n=0,a=0,l=r[0];for(;l!==void 0;){if(n===l.index){let c;l.type===2?c=new Ft(s,s.nextSibling,this,t):l.type===1?c=new l.ctor(s,l.name,l.strings,this,t):l.type===6&&(c=new vi(s,this,t)),this._$AV.push(c),l=r[++a]}n!==l?.index&&(s=pt.nextNode(),n++)}return pt.currentNode=ut,o}p(t){let e=0;for(let i of this._$AV)i!==void 0&&(i.strings!==void 0?(i._$AI(t,i,e),e+=i.strings.length-2):i._$AI(t[e])),e++}},Ft=class di{get _$AU(){var e,i;return(i=(e=this._$AM)==null?void 0:e._$AU)!=null?i:this._$Cv}constructor(e,i,r,o){var s;this.type=2,this._$AH=C,this._$AN=void 0,this._$AA=e,this._$AB=i,this._$AM=r,this.options=o,this._$Cv=(s=o?.isConnected)!=null?s:!0}get parentNode(){let e=this._$AA.parentNode,i=this._$AM;return i!==void 0&&e?.nodeType===11&&(e=i.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,i=this){e=dt(this,e,i),kt(e)?e===C||e==null||e===""?(this._$AH!==C&&this._$AR(),this._$AH=C):e!==this._$AH&&e!==ot&&this._(e):e._$litType$!==void 0?this.$(e):e.nodeType!==void 0?this.T(e):si(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==C&&kt(this._$AH)?this._$AA.nextSibling.data=e:this.T(ut.createTextNode(e)),this._$AH=e}$(e){var i;let{values:r,_$litType$:o}=e,s=typeof o=="number"?this._$AC(e):(o.el===void 0&&(o.el=ne.createElement(ci(o.h,o.h[0]),this.options)),o);if(((i=this._$AH)==null?void 0:i._$AD)===s)this._$AH.p(r);else{let n=new ui(s,this),a=n.u(this.options);n.p(r),this.T(a),this._$AH=n}}_$AC(e){let i=We.get(e.strings);return i===void 0&&We.set(e.strings,i=new ne(e)),i}k(e){ce(this._$AH)||(this._$AH=[],this._$AR());let i=this._$AH,r,o=0;for(let s of e)o===i.length?i.push(r=new di(this.O(Tt()),this.O(Tt()),this,this.options)):r=i[o],r._$AI(s),o++;o<i.length&&(this._$AR(r&&r._$AB.nextSibling,o),i.length=o)}_$AR(e=this._$AA.nextSibling,i){var r;for((r=this._$AP)==null?void 0:r.call(this,!1,!0,i);e&&e!==this._$AB;){let o=e.nextSibling;e.remove(),e=o}}setConnected(e){var i;this._$AM===void 0&&(this._$Cv=e,(i=this._$AP)==null||i.call(this,e))}},Mt=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,i,r,o){this.type=1,this._$AH=C,this._$AN=void 0,this.element=t,this.name=e,this._$AM=r,this.options=o,i.length>2||i[0]!==""||i[1]!==""?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=C}_$AI(t,e=this,i,r){let o=this.strings,s=!1;if(o===void 0)t=dt(this,t,e,0),s=!kt(t)||t!==this._$AH&&t!==ot,s&&(this._$AH=t);else{let n=t,a,l;for(t=o[0],a=0;a<o.length-1;a++)l=dt(this,n[i+a],e,a),l===ot&&(l=this._$AH[a]),s||(s=!kt(l)||l!==this._$AH[a]),l===C?t=C:t!==C&&(t+=(l??"")+o[a+1]),this._$AH[a]=l}s&&!r&&this.j(t)}j(t){t===C?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},fi=class extends Mt{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===C?void 0:t}},mi=class extends Mt{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==C)}},gi=class extends Mt{constructor(t,e,i,r,o){super(t,e,i,r,o),this.type=5}_$AI(t,e=this){var i;if((t=(i=dt(this,t,e,0))!=null?i:C)===ot)return;let r=this._$AH,o=t===C&&r!==C||t.capture!==r.capture||t.once!==r.once||t.passive!==r.passive,s=t!==C&&(r===C||o);o&&this.element.removeEventListener(this.name,this,r),s&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){var e,i;typeof this._$AH=="function"?this._$AH.call((i=(e=this.options)==null?void 0:e.host)!=null?i:this.element,t):this._$AH.handleEvent(t)}},vi=class{constructor(t,e,i){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(t){dt(this,t)}},yi={M:ae,P:J,A:le,C:1,L:hi,R:ui,D:si,V:dt,I:Ft,H:Mt,N:mi,U:gi,B:fi,F:vi},qe=Ut.litHtmlPolyfillSupport,Ye;qe?.(ne,Ft),((Ye=Ut.litHtmlVersions)!=null?Ye:Ut.litHtmlVersions=[]).push("3.2.1");var yr=(t,e,i)=>{var r,o;let s=(r=i?.renderBefore)!=null?r:e,n=s._$litPart$;if(n===void 0){let a=(o=i?.renderBefore)!=null?o:null;s._$litPart$=n=new Ft(e.insertBefore(Tt(),a),a,void 0,i??{})}return n._$AI(t),n},Ht=globalThis,pe=Ht.ShadowRoot&&(Ht.ShadyCSS===void 0||Ht.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,ue=Symbol(),Ke=new WeakMap,bi=class{constructor(t,e,i){if(this._$cssResult$=!0,i!==ue)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(pe&&t===void 0){let i=e!==void 0&&e.length===1;i&&(t=Ke.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),i&&Ke.set(e,t))}return t}toString(){return this.cssText}},br=t=>new bi(typeof t=="string"?t:t+"",void 0,ue),B=(t,...e)=>{let i=t.length===1?t[0]:e.reduce((r,o,s)=>r+(n=>{if(n._$cssResult$===!0)return n.cssText;if(typeof n=="number")return n;throw Error("Value passed to 'css' function must be a 'css' function result: "+n+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(o)+t[s+1],t[0]);return new bi(i,t,ue)},wr=(t,e)=>{if(pe)t.adoptedStyleSheets=e.map(i=>i instanceof CSSStyleSheet?i:i.styleSheet);else for(let i of e){let r=document.createElement("style"),o=Ht.litNonce;o!==void 0&&r.setAttribute("nonce",o),r.textContent=i.cssText,t.appendChild(r)}},Xe=pe?t=>t:t=>t instanceof CSSStyleSheet?(e=>{let i="";for(let r of e.cssRules)i+=r.cssText;return br(i)})(t):t,{is:_r,defineProperty:xr,getOwnPropertyDescriptor:$r,getOwnPropertyNames:Ar,getOwnPropertySymbols:Er,getPrototypeOf:Cr}=Object,xt=globalThis,Ze=xt.trustedTypes,Sr=Ze?Ze.emptyScript:"",Ge=xt.reactiveElementPolyfillSupport,Lt=(t,e)=>t,zt={toAttribute(t,e){switch(e){case Boolean:t=t?Sr:null;break;case Object:case Array:t=t==null?t:JSON.stringify(t)}return t},fromAttribute(t,e){let i=t;switch(e){case Boolean:i=t!==null;break;case Number:i=t===null?null:Number(t);break;case Object:case Array:try{i=JSON.parse(t)}catch{i=null}}return i}},Vt=(t,e)=>!_r(t,e),Je={attribute:!0,type:String,converter:zt,reflect:!1,hasChanged:Vt},Qe,ti;(Qe=Symbol.metadata)!=null||(Symbol.metadata=Symbol("metadata")),(ti=xt.litPropertyMetadata)!=null||(xt.litPropertyMetadata=new WeakMap);var wt=class extends HTMLElement{static addInitializer(t){var e;this._$Ei(),((e=this.l)!=null?e:this.l=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=Je){if(e.state&&(e.attribute=!1),this._$Ei(),this.elementProperties.set(t,e),!e.noAccessor){let i=Symbol(),r=this.getPropertyDescriptor(t,i,e);r!==void 0&&xr(this.prototype,t,r)}}static getPropertyDescriptor(t,e,i){var r;let{get:o,set:s}=(r=$r(this.prototype,t))!=null?r:{get(){return this[e]},set(n){this[e]=n}};return{get(){return o?.call(this)},set(n){let a=o?.call(this);s.call(this,n),this.requestUpdate(t,a,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){var e;return(e=this.elementProperties.get(t))!=null?e:Je}static _$Ei(){if(this.hasOwnProperty(Lt("elementProperties")))return;let t=Cr(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(Lt("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(Lt("properties"))){let e=this.properties,i=[...Ar(e),...Er(e)];for(let r of i)this.createProperty(r,e[r])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[i,r]of e)this.elementProperties.set(i,r)}this._$Eh=new Map;for(let[e,i]of this.elementProperties){let r=this._$Eu(e,i);r!==void 0&&this._$Eh.set(r,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let i=new Set(t.flat(1/0).reverse());for(let r of i)e.unshift(Xe(r))}else t!==void 0&&e.push(Xe(t));return e}static _$Eu(t,e){let i=e.attribute;return i===!1?void 0:typeof i=="string"?i:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){var t;this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),(t=this.constructor.l)==null||t.forEach(e=>e(this))}addController(t){var e,i;((e=this._$EO)!=null?e:this._$EO=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&((i=t.hostConnected)==null||i.call(t))}removeController(t){var e;(e=this._$EO)==null||e.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let i of e.keys())this.hasOwnProperty(i)&&(t.set(i,this[i]),delete this[i]);t.size>0&&(this._$Ep=t)}createRenderRoot(){var t;let e=(t=this.shadowRoot)!=null?t:this.attachShadow(this.constructor.shadowRootOptions);return wr(e,this.constructor.elementStyles),e}connectedCallback(){var t,e;(t=this.renderRoot)!=null||(this.renderRoot=this.createRenderRoot()),this.enableUpdating(!0),(e=this._$EO)==null||e.forEach(i=>{var r;return(r=i.hostConnected)==null?void 0:r.call(i)})}enableUpdating(t){}disconnectedCallback(){var t;(t=this._$EO)==null||t.forEach(e=>{var i;return(i=e.hostDisconnected)==null?void 0:i.call(e)})}attributeChangedCallback(t,e,i){this._$AK(t,i)}_$EC(t,e){var i;let r=this.constructor.elementProperties.get(t),o=this.constructor._$Eu(t,r);if(o!==void 0&&r.reflect===!0){let s=(((i=r.converter)==null?void 0:i.toAttribute)!==void 0?r.converter:zt).toAttribute(e,r.type);this._$Em=t,s==null?this.removeAttribute(o):this.setAttribute(o,s),this._$Em=null}}_$AK(t,e){var i;let r=this.constructor,o=r._$Eh.get(t);if(o!==void 0&&this._$Em!==o){let s=r.getPropertyOptions(o),n=typeof s.converter=="function"?{fromAttribute:s.converter}:((i=s.converter)==null?void 0:i.fromAttribute)!==void 0?s.converter:zt;this._$Em=o,this[o]=n.fromAttribute(e,s.type),this._$Em=null}}requestUpdate(t,e,i){var r;if(t!==void 0){if(i??(i=this.constructor.getPropertyOptions(t)),!((r=i.hasChanged)!=null?r:Vt)(this[t],e))return;this.P(t,e,i)}this.isUpdatePending===!1&&(this._$ES=this._$ET())}P(t,e,i){var r;this._$AL.has(t)||this._$AL.set(t,e),i.reflect===!0&&this._$Em!==t&&((r=this._$Ej)!=null?r:this._$Ej=new Set).add(t)}async _$ET(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){var t,e;if(!this.isUpdatePending)return;if(!this.hasUpdated){if((t=this.renderRoot)!=null||(this.renderRoot=this.createRenderRoot()),this._$Ep){for(let[s,n]of this._$Ep)this[s]=n;this._$Ep=void 0}let o=this.constructor.elementProperties;if(o.size>0)for(let[s,n]of o)n.wrapped!==!0||this._$AL.has(s)||this[s]===void 0||this.P(s,this[s],n)}let i=!1,r=this._$AL;try{i=this.shouldUpdate(r),i?(this.willUpdate(r),(e=this._$EO)==null||e.forEach(o=>{var s;return(s=o.hostUpdate)==null?void 0:s.call(o)}),this.update(r)):this._$EU()}catch(o){throw i=!1,this._$EU(),o}i&&this._$AE(r)}willUpdate(t){}_$AE(t){var e;(e=this._$EO)==null||e.forEach(i=>{var r;return(r=i.hostUpdated)==null?void 0:r.call(i)}),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EU(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Ej&&(this._$Ej=this._$Ej.forEach(e=>this._$EC(e,this[e]))),this._$EU()}updated(t){}firstUpdated(t){}},ei;wt.elementStyles=[],wt.shadowRootOptions={mode:"open"},wt[Lt("elementProperties")]=new Map,wt[Lt("finalized")]=new Map,Ge?.({ReactiveElement:wt}),((ei=xt.reactiveElementVersions)!=null?ei:xt.reactiveElementVersions=[]).push("2.0.4");var _t=class extends wt{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){var t,e;let i=super.createRenderRoot();return(e=(t=this.renderOptions).renderBefore)!=null||(t.renderBefore=i.firstChild),i}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=yr(e,this.renderRoot,this.renderOptions)}connectedCallback(){var t;super.connectedCallback(),(t=this._$Do)==null||t.setConnected(!0)}disconnectedCallback(){var t;super.disconnectedCallback(),(t=this._$Do)==null||t.setConnected(!1)}render(){return ot}},ii;_t._$litElement$=!0,_t.finalized=!0,(ii=globalThis.litElementHydrateSupport)==null||ii.call(globalThis,{LitElement:_t});var ri=globalThis.litElementPolyfillSupport;ri?.({LitElement:_t});var oi;((oi=globalThis.litElementVersions)!=null?oi:globalThis.litElementVersions=[]).push("4.1.1");/*! Bundled license information:

lit-html/lit-html.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/css-tag.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/reactive-element.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-element/lit-element.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/is-server.js:
  (**
   * @license
   * Copyright 2022 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*/var wi=B`
  :host {
    --max-width: 20rem;
    --hide-delay: 0ms;
    --show-delay: 150ms;

    display: contents;
  }

  .tooltip {
    --arrow-size: var(--sl-tooltip-arrow-size);
    --arrow-color: var(--sl-tooltip-background-color);
  }

  .tooltip::part(popup) {
    z-index: var(--sl-z-index-tooltip);
  }

  .tooltip[placement^='top']::part(popup) {
    transform-origin: bottom;
  }

  .tooltip[placement^='bottom']::part(popup) {
    transform-origin: top;
  }

  .tooltip[placement^='left']::part(popup) {
    transform-origin: right;
  }

  .tooltip[placement^='right']::part(popup) {
    transform-origin: left;
  }

  .tooltip__body {
    display: block;
    width: max-content;
    max-width: var(--max-width);
    border-radius: var(--sl-tooltip-border-radius);
    background-color: var(--sl-tooltip-background-color);
    font-family: var(--sl-tooltip-font-family);
    font-size: var(--sl-tooltip-font-size);
    font-weight: var(--sl-tooltip-font-weight);
    line-height: var(--sl-tooltip-line-height);
    text-align: start;
    white-space: normal;
    color: var(--sl-tooltip-color);
    padding: var(--sl-tooltip-padding);
    pointer-events: none;
    user-select: none;
    -webkit-user-select: none;
  }
`;var _i=B`
  :host {
    --arrow-color: var(--sl-color-neutral-1000);
    --arrow-size: 6px;

    /*
     * These properties are computed to account for the arrow's dimensions after being rotated 45º. The constant
     * 0.7071 is derived from sin(45), which is the diagonal size of the arrow's container after rotating.
     */
    --arrow-size-diagonal: calc(var(--arrow-size) * 0.7071);
    --arrow-padding-offset: calc(var(--arrow-size-diagonal) - var(--arrow-size));

    display: contents;
  }

  .popup {
    position: absolute;
    isolation: isolate;
    max-width: var(--auto-size-available-width, none);
    max-height: var(--auto-size-available-height, none);
  }

  .popup--fixed {
    position: fixed;
  }

  .popup:not(.popup--active) {
    display: none;
  }

  .popup__arrow {
    position: absolute;
    width: calc(var(--arrow-size-diagonal) * 2);
    height: calc(var(--arrow-size-diagonal) * 2);
    rotate: 45deg;
    background: var(--arrow-color);
    z-index: -1;
  }

  /* Hover bridge */
  .popup-hover-bridge:not(.popup-hover-bridge--visible) {
    display: none;
  }

  .popup-hover-bridge {
    position: fixed;
    z-index: calc(var(--sl-z-index-dropdown) - 1);
    top: 0;
    right: 0;
    bottom: 0;
    left: 0;
    clip-path: polygon(
      var(--hover-bridge-top-left-x, 0) var(--hover-bridge-top-left-y, 0),
      var(--hover-bridge-top-right-x, 0) var(--hover-bridge-top-right-y, 0),
      var(--hover-bridge-bottom-right-x, 0) var(--hover-bridge-bottom-right-y, 0),
      var(--hover-bridge-bottom-left-x, 0) var(--hover-bridge-bottom-left-y, 0)
    );
  }
`;var de=new Set,$t=new Map,ft,fe="ltr",me="en",xi=typeof MutationObserver<"u"&&typeof document<"u"&&typeof document.documentElement<"u";if(xi){let t=new MutationObserver($i);fe=document.documentElement.dir||"ltr",me=document.documentElement.lang||navigator.language,t.observe(document.documentElement,{attributes:!0,attributeFilter:["dir","lang"]})}function jt(...t){t.map(e=>{let i=e.$code.toLowerCase();$t.has(i)?$t.set(i,Object.assign(Object.assign({},$t.get(i)),e)):$t.set(i,e),ft||(ft=e)}),$i()}function $i(){xi&&(fe=document.documentElement.dir||"ltr",me=document.documentElement.lang||navigator.language),[...de.keys()].map(t=>{typeof t.requestUpdate=="function"&&t.requestUpdate()})}var Ai=class{constructor(t){this.host=t,this.host.addController(this)}hostConnected(){de.add(this.host)}hostDisconnected(){de.delete(this.host)}dir(){return`${this.host.dir||fe}`.toLowerCase()}lang(){return`${this.host.lang||me}`.toLowerCase()}getTranslationData(t){var e,i;let r=new Intl.Locale(t.replace(/_/g,"-")),o=r?.language.toLowerCase(),s=(i=(e=r?.region)===null||e===void 0?void 0:e.toLowerCase())!==null&&i!==void 0?i:"",n=$t.get(`${o}-${s}`),a=$t.get(o);return{locale:r,language:o,region:s,primary:n,secondary:a}}exists(t,e){var i;let{primary:r,secondary:o}=this.getTranslationData((i=e.lang)!==null&&i!==void 0?i:this.lang());return e=Object.assign({includeFallback:!1},e),!!(r&&r[t]||o&&o[t]||e.includeFallback&&ft&&ft[t])}term(t,...e){let{primary:i,secondary:r}=this.getTranslationData(this.lang()),o;if(i&&i[t])o=i[t];else if(r&&r[t])o=r[t];else if(ft&&ft[t])o=ft[t];else return console.error(`No translation found for: ${String(t)}`),String(t);return typeof o=="function"?o(...e):o}date(t,e){return t=new Date(t),new Intl.DateTimeFormat(this.lang(),e).format(t)}number(t,e){return t=Number(t),isNaN(t)?"":new Intl.NumberFormat(this.lang(),e).format(t)}relativeTime(t,e,i){return new Intl.RelativeTimeFormat(this.lang(),i).format(t,e)}};var Ei={$code:"en",$name:"English",$dir:"ltr",carousel:"Carousel",clearEntry:"Clear entry",close:"Close",copied:"Copied",copy:"Copy",currentValue:"Current value",error:"Error",goToSlide:(t,e)=>`Go to slide ${t} of ${e}`,hidePassword:"Hide password",loading:"Loading",nextSlide:"Next slide",numOptionsSelected:t=>t===0?"No options selected":t===1?"1 option selected":`${t} options selected`,previousSlide:"Previous slide",progress:"Progress",remove:"Remove",resize:"Resize",scrollToEnd:"Scroll to end",scrollToStart:"Scroll to start",selectAColorFromTheScreen:"Select a color from the screen",showPassword:"Show password",slideNum:t=>`Slide ${t}`,toggleColorFormat:"Toggle color format"};jt(Ei);var Ci=Ei;var At=class extends Ai{};jt(Ci);var Si={ATTRIBUTE:1,CHILD:2,PROPERTY:3,BOOLEAN_ATTRIBUTE:4,EVENT:5,ELEMENT:6},Pi=t=>(...e)=>({_$litDirective$:t,values:e}),Oi=class{constructor(t){}get _$AU(){return this._$AM._$AU}_$AT(t,e,i){this._$Ct=t,this._$AM=e,this._$Ci=i}_$AS(t,e){return this.update(t,e)}update(t,e){return this.render(...e)}};/*! Bundled license information:

lit-html/directive.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*/var Q=Pi(class extends Oi{constructor(t){var e;if(super(t),t.type!==Si.ATTRIBUTE||t.name!=="class"||((e=t.strings)==null?void 0:e.length)>2)throw Error("`classMap()` can only be used in the `class` attribute and must be the only part in the attribute.")}render(t){return" "+Object.keys(t).filter(e=>t[e]).join(" ")+" "}update(t,[e]){var i,r;if(this.st===void 0){this.st=new Set,t.strings!==void 0&&(this.nt=new Set(t.strings.join(" ").split(/\s/).filter(s=>s!=="")));for(let s in e)e[s]&&!((i=this.nt)!=null&&i.has(s))&&this.st.add(s);return this.render(e)}let o=t.element.classList;for(let s of this.st)s in e||(o.remove(s),this.st.delete(s));for(let s in e){let n=!!e[s];n===this.st.has(s)||(r=this.nt)!=null&&r.has(s)||(n?(o.add(s),this.st.add(s)):(o.remove(s),this.st.delete(s)))}return ot}});/*! Bundled license information:

lit-html/directives/class-map.js:
  (**
   * @license
   * Copyright 2018 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*/var q=B`
  :host {
    box-sizing: border-box;
  }

  :host *,
  :host *::before,
  :host *::after {
    box-sizing: inherit;
  }

  [hidden] {
    display: none !important;
  }
`;var Li=Object.defineProperty,Pr=Object.defineProperties,Or=Object.getOwnPropertyDescriptor,Rr=Object.getOwnPropertyDescriptors,Wt=Object.getOwnPropertySymbols,Ti=Object.prototype.hasOwnProperty,ki=Object.prototype.propertyIsEnumerable;var zi=t=>{throw TypeError(t)},Ri=(t,e,i)=>e in t?Li(t,e,{enumerable:!0,configurable:!0,writable:!0,value:i}):t[e]=i,$=(t,e)=>{for(var i in e||(e={}))Ti.call(e,i)&&Ri(t,i,e[i]);if(Wt)for(var i of Wt(e))ki.call(e,i)&&Ri(t,i,e[i]);return t},P=(t,e)=>Pr(t,Rr(e)),qt=(t,e)=>{var i={};for(var r in t)Ti.call(t,r)&&e.indexOf(r)<0&&(i[r]=t[r]);if(t!=null&&Wt)for(var r of Wt(t))e.indexOf(r)<0&&ki.call(t,r)&&(i[r]=t[r]);return i};var d=(t,e,i,r)=>{for(var o=r>1?void 0:r?Or(e,i):e,s=t.length-1,n;s>=0;s--)(n=t[s])&&(o=(r?n(e,i,o):n(o))||o);return r&&o&&Li(e,i,o),o},Mi=(t,e,i)=>e.has(t)||zi("Cannot "+i),Bi=(t,e,i)=>(Mi(t,e,"read from private field"),i?i.call(t):e.get(t)),Di=(t,e,i)=>e.has(t)?zi("Cannot add the same private member more than once"):e instanceof WeakSet?e.add(t):e.set(t,i),Ni=(t,e,i,r)=>(Mi(t,e,"write to private field"),r?r.call(t,i):e.set(t,i),i);var Lr={attribute:!0,type:String,converter:zt,reflect:!1,hasChanged:Vt},Tr=(t=Lr,e,i)=>{let{kind:r,metadata:o}=i,s=globalThis.litPropertyMetadata.get(o);if(s===void 0&&globalThis.litPropertyMetadata.set(o,s=new Map),s.set(i.name,t),r==="accessor"){let{name:n}=i;return{set(a){let l=e.get.call(this);e.set.call(this,a),this.requestUpdate(n,l,t)},init(a){return a!==void 0&&this.P(n,void 0,t),a}}}if(r==="setter"){let{name:n}=i;return function(a){let l=this[n];e.call(this,a),this.requestUpdate(n,l,t)}}throw Error("Unsupported decorator location: "+r)};function m(t){return(e,i)=>typeof i=="object"?Tr(t,e,i):((r,o,s)=>{let n=o.hasOwnProperty(s);return o.constructor.createProperty(s,n?P($({},r),{wrapped:!0}):r),n?Object.getOwnPropertyDescriptor(o,s):void 0})(t,e,i)}function Kt(t){return m(P($({},t),{state:!0,attribute:!1}))}var Hi=(t,e,i)=>(i.configurable=!0,i.enumerable=!0,Reflect.decorate&&typeof e!="object"&&Object.defineProperty(t,e,i),i);function tt(t,e){return(i,r,o)=>{let s=n=>{var a,l;return(l=(a=n.renderRoot)==null?void 0:a.querySelector(t))!=null?l:null};if(e){let{get:n,set:a}=typeof r=="object"?i:o??(()=>{let l=Symbol();return{get(){return this[l]},set(c){this[l]=c}}})();return Hi(i,r,{get(){let l=n.call(this);return l===void 0&&(l=s(this),(l!==null||this.hasUpdated)&&a.call(this,l)),l}})}return Hi(i,r,{get(){return s(this)}})}}var Yt,O=class extends _t{constructor(){super(),Di(this,Yt,!1),this.initialReflectedProperties=new Map,Object.entries(this.constructor.dependencies).forEach(([t,e])=>{this.constructor.define(t,e)})}emit(t,e){let i=new CustomEvent(t,$({bubbles:!0,cancelable:!1,composed:!0,detail:{}},e));return this.dispatchEvent(i),i}static define(t,e=this,i={}){let r=customElements.get(t);if(!r){try{customElements.define(t,e,i)}catch{customElements.define(t,class extends e{},i)}return}let o=" (unknown version)",s=o;"version"in e&&e.version&&(o=" v"+e.version),"version"in r&&r.version&&(s=" v"+r.version),!(o&&s&&o===s)&&console.warn(`Attempted to register <${t}>${o}, but <${t}>${s} has already been registered.`)}attributeChangedCallback(t,e,i){Bi(this,Yt)||(this.constructor.elementProperties.forEach((r,o)=>{r.reflect&&this[o]!=null&&this.initialReflectedProperties.set(o,this[o])}),Ni(this,Yt,!0)),super.attributeChangedCallback(t,e,i)}willUpdate(t){super.willUpdate(t),this.initialReflectedProperties.forEach((e,i)=>{t.has(i)&&this[i]==null&&(this[i]=e)})}};Yt=new WeakMap;O.version="2.20.1";O.dependencies={};d([m()],O.prototype,"dir",2);d([m()],O.prototype,"lang",2);/*! Bundled license information:

@lit/reactive-element/decorators/property.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/decorators/state.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/decorators/event-options.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/decorators/base.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/decorators/query.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/decorators/query-async.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/decorators/custom-element.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/decorators/query-all.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/decorators/query-assigned-elements.js:
  (**
   * @license
   * Copyright 2021 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/decorators/query-assigned-nodes.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*/var st=Math.min,T=Math.max,Gt=Math.round,Xt=Math.floor,Y=t=>({x:t,y:t}),kr={left:"right",right:"left",bottom:"top",top:"bottom"},zr={start:"end",end:"start"};function ye(t,e,i){return T(t,st(e,i))}function St(t,e){return typeof t=="function"?t(e):t}function nt(t){return t.split("-")[0]}function Pt(t){return t.split("-")[1]}function Wi(t){return t==="x"?"y":"x"}function _e(t){return t==="y"?"height":"width"}function mt(t){return["top","bottom"].includes(nt(t))?"y":"x"}function xe(t){return Wi(mt(t))}function Mr(t,e,i){i===void 0&&(i=!1);let r=Pt(t),o=xe(t),s=_e(o),n=o==="x"?r===(i?"end":"start")?"right":"left":r==="start"?"bottom":"top";return e.reference[s]>e.floating[s]&&(n=Jt(n)),[n,Jt(n)]}function Br(t){let e=Jt(t);return[be(t),e,be(e)]}function be(t){return t.replace(/start|end/g,e=>zr[e])}function Dr(t,e,i){let r=["left","right"],o=["right","left"],s=["top","bottom"],n=["bottom","top"];switch(t){case"top":case"bottom":return i?e?o:r:e?r:o;case"left":case"right":return e?s:n;default:return[]}}function Nr(t,e,i,r){let o=Pt(t),s=Dr(nt(t),i==="start",r);return o&&(s=s.map(n=>n+"-"+o),e&&(s=s.concat(s.map(be)))),s}function Jt(t){return t.replace(/left|right|bottom|top/g,e=>kr[e])}function Hr(t){return $({top:0,right:0,bottom:0,left:0},t)}function qi(t){return typeof t!="number"?Hr(t):{top:t,right:t,bottom:t,left:t}}function Qt(t){let{x:e,y:i,width:r,height:o}=t;return{width:r,height:o,top:i,left:e,right:e+r,bottom:i+o,x:e,y:i}}function Ui(t,e,i){let{reference:r,floating:o}=t,s=mt(e),n=xe(e),a=_e(n),l=nt(e),c=s==="y",p=r.x+r.width/2-o.width/2,h=r.y+r.height/2-o.height/2,f=r[a]/2-o[a]/2,u;switch(l){case"top":u={x:p,y:r.y-o.height};break;case"bottom":u={x:p,y:r.y+r.height};break;case"right":u={x:r.x+r.width,y:h};break;case"left":u={x:r.x-o.width,y:h};break;default:u={x:r.x,y:r.y}}switch(Pt(e)){case"start":u[n]-=f*(i&&c?-1:1);break;case"end":u[n]+=f*(i&&c?-1:1);break}return u}var Ur=async(t,e,i)=>{let{placement:r="bottom",strategy:o="absolute",middleware:s=[],platform:n}=i,a=s.filter(Boolean),l=await(n.isRTL==null?void 0:n.isRTL(e)),c=await n.getElementRects({reference:t,floating:e,strategy:o}),{x:p,y:h}=Ui(c,r,l),f=r,u={},g=0;for(let v=0;v<a.length;v++){let{name:b,fn:y}=a[v],{x:w,y:_,data:A,reset:E}=await y({x:p,y:h,initialPlacement:r,placement:f,strategy:o,middlewareData:u,rects:c,platform:n,elements:{reference:t,floating:e}});p=w??p,h=_??h,u=P($({},u),{[b]:$($({},u[b]),A)}),E&&g<=50&&(g++,typeof E=="object"&&(E.placement&&(f=E.placement),E.rects&&(c=E.rects===!0?await n.getElementRects({reference:t,floating:e,strategy:o}):E.rects),{x:p,y:h}=Ui(c,f,l)),v=-1)}return{x:p,y:h,placement:f,strategy:o,middlewareData:u}};async function $e(t,e){var i;e===void 0&&(e={});let{x:r,y:o,platform:s,rects:n,elements:a,strategy:l}=t,{boundary:c="clippingAncestors",rootBoundary:p="viewport",elementContext:h="floating",altBoundary:f=!1,padding:u=0}=St(e,t),g=qi(u),b=a[f?h==="floating"?"reference":"floating":h],y=Qt(await s.getClippingRect({element:(i=await(s.isElement==null?void 0:s.isElement(b)))==null||i?b:b.contextElement||await(s.getDocumentElement==null?void 0:s.getDocumentElement(a.floating)),boundary:c,rootBoundary:p,strategy:l})),w=h==="floating"?{x:r,y:o,width:n.floating.width,height:n.floating.height}:n.reference,_=await(s.getOffsetParent==null?void 0:s.getOffsetParent(a.floating)),A=await(s.isElement==null?void 0:s.isElement(_))?await(s.getScale==null?void 0:s.getScale(_))||{x:1,y:1}:{x:1,y:1},E=Qt(s.convertOffsetParentRelativeRectToViewportRelativeRect?await s.convertOffsetParentRelativeRectToViewportRelativeRect({elements:a,rect:w,offsetParent:_,strategy:l}):w);return{top:(y.top-E.top+g.top)/A.y,bottom:(E.bottom-y.bottom+g.bottom)/A.y,left:(y.left-E.left+g.left)/A.x,right:(E.right-y.right+g.right)/A.x}}var Ir=t=>({name:"arrow",options:t,async fn(e){let{x:i,y:r,placement:o,rects:s,platform:n,elements:a,middlewareData:l}=e,{element:c,padding:p=0}=St(t,e)||{};if(c==null)return{};let h=qi(p),f={x:i,y:r},u=xe(o),g=_e(u),v=await n.getDimensions(c),b=u==="y",y=b?"top":"left",w=b?"bottom":"right",_=b?"clientHeight":"clientWidth",A=s.reference[g]+s.reference[u]-f[u]-s.floating[g],E=f[u]-s.reference[u],z=await(n.getOffsetParent==null?void 0:n.getOffsetParent(c)),F=z?z[_]:0;(!F||!await(n.isElement==null?void 0:n.isElement(z)))&&(F=a.floating[_]||s.floating[g]);let ct=A/2-E/2,V=F/2-v[g]/2-1,j=st(h[y],V),D=st(h[w],V),W=j,et=F-v[g]-D,L=F/2-v[g]/2+ct,N=ye(W,L,et),yt=!l.arrow&&Pt(o)!=null&&L!==N&&s.reference[g]/2-(L<W?j:D)-v[g]/2<0,G=yt?L<W?L-W:L-et:0;return{[u]:f[u]+G,data:$({[u]:N,centerOffset:L-N-G},yt&&{alignmentOffset:G}),reset:yt}}}),Fr=function(t){return t===void 0&&(t={}),{name:"flip",options:t,async fn(e){var i,r;let{placement:o,middlewareData:s,rects:n,initialPlacement:a,platform:l,elements:c}=e,p=St(t,e),{mainAxis:h=!0,crossAxis:f=!0,fallbackPlacements:u,fallbackStrategy:g="bestFit",fallbackAxisSideDirection:v="none",flipAlignment:b=!0}=p,y=qt(p,["mainAxis","crossAxis","fallbackPlacements","fallbackStrategy","fallbackAxisSideDirection","flipAlignment"]);if((i=s.arrow)!=null&&i.alignmentOffset)return{};let w=nt(o),_=mt(a),A=nt(a)===a,E=await(l.isRTL==null?void 0:l.isRTL(c.floating)),z=u||(A||!b?[Jt(a)]:Br(a)),F=v!=="none";!u&&F&&z.push(...Nr(a,b,v,E));let ct=[a,...z],V=await $e(e,y),j=[],D=((r=s.flip)==null?void 0:r.overflows)||[];if(h&&j.push(V[w]),f){let N=Mr(o,n,E);j.push(V[N[0]],V[N[1]])}if(D=[...D,{placement:o,overflows:j}],!j.every(N=>N<=0)){var W,et;let N=(((W=s.flip)==null?void 0:W.index)||0)+1,yt=ct[N];if(yt)return{data:{index:N,overflows:D},reset:{placement:yt}};let G=(et=D.filter(bt=>bt.overflows[0]<=0).sort((bt,it)=>bt.overflows[1]-it.overflows[1])[0])==null?void 0:et.placement;if(!G)switch(g){case"bestFit":{var L;let bt=(L=D.filter(it=>{if(F){let rt=mt(it.placement);return rt===_||rt==="y"}return!0}).map(it=>[it.placement,it.overflows.filter(rt=>rt>0).reduce((rt,gr)=>rt+gr,0)]).sort((it,rt)=>it[1]-rt[1])[0])==null?void 0:L[0];bt&&(G=bt);break}case"initialPlacement":G=a;break}if(o!==G)return{reset:{placement:G}}}return{}}}};async function Vr(t,e){let{placement:i,platform:r,elements:o}=t,s=await(r.isRTL==null?void 0:r.isRTL(o.floating)),n=nt(i),a=Pt(i),l=mt(i)==="y",c=["left","top"].includes(n)?-1:1,p=s&&l?-1:1,h=St(e,t),{mainAxis:f,crossAxis:u,alignmentAxis:g}=typeof h=="number"?{mainAxis:h,crossAxis:0,alignmentAxis:null}:{mainAxis:h.mainAxis||0,crossAxis:h.crossAxis||0,alignmentAxis:h.alignmentAxis};return a&&typeof g=="number"&&(u=a==="end"?g*-1:g),l?{x:u*p,y:f*c}:{x:f*c,y:u*p}}var jr=function(t){return t===void 0&&(t=0),{name:"offset",options:t,async fn(e){var i,r;let{x:o,y:s,placement:n,middlewareData:a}=e,l=await Vr(e,t);return n===((i=a.offset)==null?void 0:i.placement)&&(r=a.arrow)!=null&&r.alignmentOffset?{}:{x:o+l.x,y:s+l.y,data:P($({},l),{placement:n})}}}},Wr=function(t){return t===void 0&&(t={}),{name:"shift",options:t,async fn(e){let{x:i,y:r,placement:o}=e,s=St(t,e),{mainAxis:n=!0,crossAxis:a=!1,limiter:l={fn:y=>{let{x:w,y:_}=y;return{x:w,y:_}}}}=s,c=qt(s,["mainAxis","crossAxis","limiter"]),p={x:i,y:r},h=await $e(e,c),f=mt(nt(o)),u=Wi(f),g=p[u],v=p[f];if(n){let y=u==="y"?"top":"left",w=u==="y"?"bottom":"right",_=g+h[y],A=g-h[w];g=ye(_,g,A)}if(a){let y=f==="y"?"top":"left",w=f==="y"?"bottom":"right",_=v+h[y],A=v-h[w];v=ye(_,v,A)}let b=l.fn(P($({},e),{[u]:g,[f]:v}));return P($({},b),{data:{x:b.x-i,y:b.y-r,enabled:{[u]:n,[f]:a}}})}}},qr=function(t){return t===void 0&&(t={}),{name:"size",options:t,async fn(e){var i,r;let{placement:o,rects:s,platform:n,elements:a}=e,l=St(t,e),{apply:c=()=>{}}=l,p=qt(l,["apply"]),h=await $e(e,p),f=nt(o),u=Pt(o),g=mt(o)==="y",{width:v,height:b}=s.floating,y,w;f==="top"||f==="bottom"?(y=f,w=u===(await(n.isRTL==null?void 0:n.isRTL(a.floating))?"start":"end")?"left":"right"):(w=f,y=u==="end"?"top":"bottom");let _=b-h.top-h.bottom,A=v-h.left-h.right,E=st(b-h[y],_),z=st(v-h[w],A),F=!e.middlewareData.shift,ct=E,V=z;if((i=e.middlewareData.shift)!=null&&i.enabled.x&&(V=A),(r=e.middlewareData.shift)!=null&&r.enabled.y&&(ct=_),F&&!u){let D=T(h.left,0),W=T(h.right,0),et=T(h.top,0),L=T(h.bottom,0);g?V=v-2*(D!==0||W!==0?D+W:T(h.left,h.right)):ct=b-2*(et!==0||L!==0?et+L:T(h.top,h.bottom))}await c(P($({},e),{availableWidth:V,availableHeight:ct}));let j=await n.getDimensions(a.floating);return v!==j.width||b!==j.height?{reset:{rects:!0}}:{}}}};function te(){return typeof window<"u"}function Ot(t){return Yi(t)?(t.nodeName||"").toLowerCase():"#document"}function k(t){var e;return(t==null||(e=t.ownerDocument)==null?void 0:e.defaultView)||window}function X(t){var e;return(e=(Yi(t)?t.ownerDocument:t.document)||window.document)==null?void 0:e.documentElement}function Yi(t){return te()?t instanceof Node||t instanceof k(t).Node:!1}function H(t){return te()?t instanceof Element||t instanceof k(t).Element:!1}function K(t){return te()?t instanceof HTMLElement||t instanceof k(t).HTMLElement:!1}function Ii(t){return!te()||typeof ShadowRoot>"u"?!1:t instanceof ShadowRoot||t instanceof k(t).ShadowRoot}function Dt(t){let{overflow:e,overflowX:i,overflowY:r,display:o}=U(t);return/auto|scroll|overlay|hidden|clip/.test(e+r+i)&&!["inline","contents"].includes(o)}function Yr(t){return["table","td","th"].includes(Ot(t))}function ee(t){return[":popover-open",":modal"].some(e=>{try{return t.matches(e)}catch{return!1}})}function ie(t){let e=Ae(),i=H(t)?U(t):t;return i.transform!=="none"||i.perspective!=="none"||(i.containerType?i.containerType!=="normal":!1)||!e&&(i.backdropFilter?i.backdropFilter!=="none":!1)||!e&&(i.filter?i.filter!=="none":!1)||["transform","perspective","filter"].some(r=>(i.willChange||"").includes(r))||["paint","layout","strict","content"].some(r=>(i.contain||"").includes(r))}function Kr(t){let e=at(t);for(;K(e)&&!Ct(e);){if(ie(e))return e;if(ee(e))return null;e=at(e)}return null}function Ae(){return typeof CSS>"u"||!CSS.supports?!1:CSS.supports("-webkit-backdrop-filter","none")}function Ct(t){return["html","body","#document"].includes(Ot(t))}function U(t){return k(t).getComputedStyle(t)}function re(t){return H(t)?{scrollLeft:t.scrollLeft,scrollTop:t.scrollTop}:{scrollLeft:t.scrollX,scrollTop:t.scrollY}}function at(t){if(Ot(t)==="html")return t;let e=t.assignedSlot||t.parentNode||Ii(t)&&t.host||X(t);return Ii(e)?e.host:e}function Ki(t){let e=at(t);return Ct(e)?t.ownerDocument?t.ownerDocument.body:t.body:K(e)&&Dt(e)?e:Ki(e)}function Bt(t,e,i){var r;e===void 0&&(e=[]),i===void 0&&(i=!0);let o=Ki(t),s=o===((r=t.ownerDocument)==null?void 0:r.body),n=k(o);if(s){let a=we(n);return e.concat(n,n.visualViewport||[],Dt(o)?o:[],a&&i?Bt(a):[])}return e.concat(o,Bt(o,[],i))}function we(t){return t.parent&&Object.getPrototypeOf(t.parent)?t.frameElement:null}function Xi(t){let e=U(t),i=parseFloat(e.width)||0,r=parseFloat(e.height)||0,o=K(t),s=o?t.offsetWidth:i,n=o?t.offsetHeight:r,a=Gt(i)!==s||Gt(r)!==n;return a&&(i=s,r=n),{width:i,height:r,$:a}}function Ee(t){return H(t)?t:t.contextElement}function Et(t){let e=Ee(t);if(!K(e))return Y(1);let i=e.getBoundingClientRect(),{width:r,height:o,$:s}=Xi(e),n=(s?Gt(i.width):i.width)/r,a=(s?Gt(i.height):i.height)/o;return(!n||!Number.isFinite(n))&&(n=1),(!a||!Number.isFinite(a))&&(a=1),{x:n,y:a}}var Xr=Y(0);function Zi(t){let e=k(t);return!Ae()||!e.visualViewport?Xr:{x:e.visualViewport.offsetLeft,y:e.visualViewport.offsetTop}}function Zr(t,e,i){return e===void 0&&(e=!1),!i||e&&i!==k(t)?!1:e}function gt(t,e,i,r){e===void 0&&(e=!1),i===void 0&&(i=!1);let o=t.getBoundingClientRect(),s=Ee(t),n=Y(1);e&&(r?H(r)&&(n=Et(r)):n=Et(t));let a=Zr(s,i,r)?Zi(s):Y(0),l=(o.left+a.x)/n.x,c=(o.top+a.y)/n.y,p=o.width/n.x,h=o.height/n.y;if(s){let f=k(s),u=r&&H(r)?k(r):r,g=f,v=we(g);for(;v&&r&&u!==g;){let b=Et(v),y=v.getBoundingClientRect(),w=U(v),_=y.left+(v.clientLeft+parseFloat(w.paddingLeft))*b.x,A=y.top+(v.clientTop+parseFloat(w.paddingTop))*b.y;l*=b.x,c*=b.y,p*=b.x,h*=b.y,l+=_,c+=A,g=k(v),v=we(g)}}return Qt({width:p,height:h,x:l,y:c})}function Ce(t,e){let i=re(t).scrollLeft;return e?e.left+i:gt(X(t)).left+i}function Gi(t,e,i){i===void 0&&(i=!1);let r=t.getBoundingClientRect(),o=r.left+e.scrollLeft-(i?0:Ce(t,r)),s=r.top+e.scrollTop;return{x:o,y:s}}function Gr(t){let{elements:e,rect:i,offsetParent:r,strategy:o}=t,s=o==="fixed",n=X(r),a=e?ee(e.floating):!1;if(r===n||a&&s)return i;let l={scrollLeft:0,scrollTop:0},c=Y(1),p=Y(0),h=K(r);if((h||!h&&!s)&&((Ot(r)!=="body"||Dt(n))&&(l=re(r)),K(r))){let u=gt(r);c=Et(r),p.x=u.x+r.clientLeft,p.y=u.y+r.clientTop}let f=n&&!h&&!s?Gi(n,l,!0):Y(0);return{width:i.width*c.x,height:i.height*c.y,x:i.x*c.x-l.scrollLeft*c.x+p.x+f.x,y:i.y*c.y-l.scrollTop*c.y+p.y+f.y}}function Jr(t){return Array.from(t.getClientRects())}function Qr(t){let e=X(t),i=re(t),r=t.ownerDocument.body,o=T(e.scrollWidth,e.clientWidth,r.scrollWidth,r.clientWidth),s=T(e.scrollHeight,e.clientHeight,r.scrollHeight,r.clientHeight),n=-i.scrollLeft+Ce(t),a=-i.scrollTop;return U(r).direction==="rtl"&&(n+=T(e.clientWidth,r.clientWidth)-o),{width:o,height:s,x:n,y:a}}function to(t,e){let i=k(t),r=X(t),o=i.visualViewport,s=r.clientWidth,n=r.clientHeight,a=0,l=0;if(o){s=o.width,n=o.height;let c=Ae();(!c||c&&e==="fixed")&&(a=o.offsetLeft,l=o.offsetTop)}return{width:s,height:n,x:a,y:l}}function eo(t,e){let i=gt(t,!0,e==="fixed"),r=i.top+t.clientTop,o=i.left+t.clientLeft,s=K(t)?Et(t):Y(1),n=t.clientWidth*s.x,a=t.clientHeight*s.y,l=o*s.x,c=r*s.y;return{width:n,height:a,x:l,y:c}}function Fi(t,e,i){let r;if(e==="viewport")r=to(t,i);else if(e==="document")r=Qr(X(t));else if(H(e))r=eo(e,i);else{let o=Zi(t);r={x:e.x-o.x,y:e.y-o.y,width:e.width,height:e.height}}return Qt(r)}function Ji(t,e){let i=at(t);return i===e||!H(i)||Ct(i)?!1:U(i).position==="fixed"||Ji(i,e)}function io(t,e){let i=e.get(t);if(i)return i;let r=Bt(t,[],!1).filter(a=>H(a)&&Ot(a)!=="body"),o=null,s=U(t).position==="fixed",n=s?at(t):t;for(;H(n)&&!Ct(n);){let a=U(n),l=ie(n);!l&&a.position==="fixed"&&(o=null),(s?!l&&!o:!l&&a.position==="static"&&!!o&&["absolute","fixed"].includes(o.position)||Dt(n)&&!l&&Ji(t,n))?r=r.filter(p=>p!==n):o=a,n=at(n)}return e.set(t,r),r}function ro(t){let{element:e,boundary:i,rootBoundary:r,strategy:o}=t,n=[...i==="clippingAncestors"?ee(e)?[]:io(e,this._c):[].concat(i),r],a=n[0],l=n.reduce((c,p)=>{let h=Fi(e,p,o);return c.top=T(h.top,c.top),c.right=st(h.right,c.right),c.bottom=st(h.bottom,c.bottom),c.left=T(h.left,c.left),c},Fi(e,a,o));return{width:l.right-l.left,height:l.bottom-l.top,x:l.left,y:l.top}}function oo(t){let{width:e,height:i}=Xi(t);return{width:e,height:i}}function so(t,e,i){let r=K(e),o=X(e),s=i==="fixed",n=gt(t,!0,s,e),a={scrollLeft:0,scrollTop:0},l=Y(0);if(r||!r&&!s)if((Ot(e)!=="body"||Dt(o))&&(a=re(e)),r){let f=gt(e,!0,s,e);l.x=f.x+e.clientLeft,l.y=f.y+e.clientTop}else o&&(l.x=Ce(o));let c=o&&!r&&!s?Gi(o,a):Y(0),p=n.left+a.scrollLeft-l.x-c.x,h=n.top+a.scrollTop-l.y-c.y;return{x:p,y:h,width:n.width,height:n.height}}function ge(t){return U(t).position==="static"}function Vi(t,e){if(!K(t)||U(t).position==="fixed")return null;if(e)return e(t);let i=t.offsetParent;return X(t)===i&&(i=i.ownerDocument.body),i}function Qi(t,e){let i=k(t);if(ee(t))return i;if(!K(t)){let o=at(t);for(;o&&!Ct(o);){if(H(o)&&!ge(o))return o;o=at(o)}return i}let r=Vi(t,e);for(;r&&Yr(r)&&ge(r);)r=Vi(r,e);return r&&Ct(r)&&ge(r)&&!ie(r)?i:r||Kr(t)||i}var no=async function(t){let e=this.getOffsetParent||Qi,i=this.getDimensions,r=await i(t.floating);return{reference:so(t.reference,await e(t.floating),t.strategy),floating:{x:0,y:0,width:r.width,height:r.height}}};function ao(t){return U(t).direction==="rtl"}var Zt={convertOffsetParentRelativeRectToViewportRelativeRect:Gr,getDocumentElement:X,getClippingRect:ro,getOffsetParent:Qi,getElementRects:no,getClientRects:Jr,getDimensions:oo,getScale:Et,isElement:H,isRTL:ao};function lo(t,e){let i=null,r,o=X(t);function s(){var a;clearTimeout(r),(a=i)==null||a.disconnect(),i=null}function n(a,l){a===void 0&&(a=!1),l===void 0&&(l=1),s();let{left:c,top:p,width:h,height:f}=t.getBoundingClientRect();if(a||e(),!h||!f)return;let u=Xt(p),g=Xt(o.clientWidth-(c+h)),v=Xt(o.clientHeight-(p+f)),b=Xt(c),w={rootMargin:-u+"px "+-g+"px "+-v+"px "+-b+"px",threshold:T(0,st(1,l))||1},_=!0;function A(E){let z=E[0].intersectionRatio;if(z!==l){if(!_)return n();z?n(!1,z):r=setTimeout(()=>{n(!1,1e-7)},1e3)}_=!1}try{i=new IntersectionObserver(A,P($({},w),{root:o.ownerDocument}))}catch{i=new IntersectionObserver(A,w)}i.observe(t)}return n(!0),s}function co(t,e,i,r){r===void 0&&(r={});let{ancestorScroll:o=!0,ancestorResize:s=!0,elementResize:n=typeof ResizeObserver=="function",layoutShift:a=typeof IntersectionObserver=="function",animationFrame:l=!1}=r,c=Ee(t),p=o||s?[...c?Bt(c):[],...Bt(e)]:[];p.forEach(y=>{o&&y.addEventListener("scroll",i,{passive:!0}),s&&y.addEventListener("resize",i)});let h=c&&a?lo(c,i):null,f=-1,u=null;n&&(u=new ResizeObserver(y=>{let[w]=y;w&&w.target===c&&u&&(u.unobserve(e),cancelAnimationFrame(f),f=requestAnimationFrame(()=>{var _;(_=u)==null||_.observe(e)})),i()}),c&&!l&&u.observe(c),u.observe(e));let g,v=l?gt(t):null;l&&b();function b(){let y=gt(t);v&&(y.x!==v.x||y.y!==v.y||y.width!==v.width||y.height!==v.height)&&i(),v=y,g=requestAnimationFrame(b)}return i(),()=>{var y;p.forEach(w=>{o&&w.removeEventListener("scroll",i),s&&w.removeEventListener("resize",i)}),h?.(),(y=u)==null||y.disconnect(),u=null,l&&cancelAnimationFrame(g)}}var ho=jr,po=Wr,uo=Fr,ji=qr,fo=Ir,mo=(t,e,i)=>{let r=new Map,o=$({platform:Zt},i),s=P($({},o.platform),{_c:r});return Ur(t,e,P($({},o),{platform:s}))};function go(t){return vo(t)}function ve(t){return t.assignedSlot?t.assignedSlot:t.parentNode instanceof ShadowRoot?t.parentNode.host:t.parentNode}function vo(t){for(let e=t;e;e=ve(e))if(e instanceof Element&&getComputedStyle(e).display==="none")return null;for(let e=ve(t);e;e=ve(e)){if(!(e instanceof Element))continue;let i=getComputedStyle(e);if(i.display!=="contents"&&(i.position!=="static"||ie(i)||e.tagName==="BODY"))return e}return null}function yo(t){return t!==null&&typeof t=="object"&&"getBoundingClientRect"in t&&("contextElement"in t?t.contextElement instanceof Element:!0)}var x=class extends O{constructor(){super(...arguments),this.localize=new At(this),this.active=!1,this.placement="top",this.strategy="absolute",this.distance=0,this.skidding=0,this.arrow=!1,this.arrowPlacement="anchor",this.arrowPadding=10,this.flip=!1,this.flipFallbackPlacements="",this.flipFallbackStrategy="best-fit",this.flipPadding=0,this.shift=!1,this.shiftPadding=0,this.autoSizePadding=0,this.hoverBridge=!1,this.updateHoverBridge=()=>{if(this.hoverBridge&&this.anchorEl){let t=this.anchorEl.getBoundingClientRect(),e=this.popup.getBoundingClientRect(),i=this.placement.includes("top")||this.placement.includes("bottom"),r=0,o=0,s=0,n=0,a=0,l=0,c=0,p=0;i?t.top<e.top?(r=t.left,o=t.bottom,s=t.right,n=t.bottom,a=e.left,l=e.top,c=e.right,p=e.top):(r=e.left,o=e.bottom,s=e.right,n=e.bottom,a=t.left,l=t.top,c=t.right,p=t.top):t.left<e.left?(r=t.right,o=t.top,s=e.left,n=e.top,a=t.right,l=t.bottom,c=e.left,p=e.bottom):(r=e.right,o=e.top,s=t.left,n=t.top,a=e.right,l=e.bottom,c=t.left,p=t.bottom),this.style.setProperty("--hover-bridge-top-left-x",`${r}px`),this.style.setProperty("--hover-bridge-top-left-y",`${o}px`),this.style.setProperty("--hover-bridge-top-right-x",`${s}px`),this.style.setProperty("--hover-bridge-top-right-y",`${n}px`),this.style.setProperty("--hover-bridge-bottom-left-x",`${a}px`),this.style.setProperty("--hover-bridge-bottom-left-y",`${l}px`),this.style.setProperty("--hover-bridge-bottom-right-x",`${c}px`),this.style.setProperty("--hover-bridge-bottom-right-y",`${p}px`)}}}async connectedCallback(){super.connectedCallback(),await this.updateComplete,this.start()}disconnectedCallback(){super.disconnectedCallback(),this.stop()}async updated(t){super.updated(t),t.has("active")&&(this.active?this.start():this.stop()),t.has("anchor")&&this.handleAnchorChange(),this.active&&(await this.updateComplete,this.reposition())}async handleAnchorChange(){if(await this.stop(),this.anchor&&typeof this.anchor=="string"){let t=this.getRootNode();this.anchorEl=t.getElementById(this.anchor)}else this.anchor instanceof Element||yo(this.anchor)?this.anchorEl=this.anchor:this.anchorEl=this.querySelector('[slot="anchor"]');this.anchorEl instanceof HTMLSlotElement&&(this.anchorEl=this.anchorEl.assignedElements({flatten:!0})[0]),this.anchorEl&&this.active&&this.start()}start(){!this.anchorEl||!this.active||(this.cleanup=co(this.anchorEl,this.popup,()=>{this.reposition()}))}async stop(){return new Promise(t=>{this.cleanup?(this.cleanup(),this.cleanup=void 0,this.removeAttribute("data-current-placement"),this.style.removeProperty("--auto-size-available-width"),this.style.removeProperty("--auto-size-available-height"),requestAnimationFrame(()=>t())):t()})}reposition(){if(!this.active||!this.anchorEl)return;let t=[ho({mainAxis:this.distance,crossAxis:this.skidding})];this.sync?t.push(ji({apply:({rects:i})=>{let r=this.sync==="width"||this.sync==="both",o=this.sync==="height"||this.sync==="both";this.popup.style.width=r?`${i.reference.width}px`:"",this.popup.style.height=o?`${i.reference.height}px`:""}})):(this.popup.style.width="",this.popup.style.height=""),this.flip&&t.push(uo({boundary:this.flipBoundary,fallbackPlacements:this.flipFallbackPlacements,fallbackStrategy:this.flipFallbackStrategy==="best-fit"?"bestFit":"initialPlacement",padding:this.flipPadding})),this.shift&&t.push(po({boundary:this.shiftBoundary,padding:this.shiftPadding})),this.autoSize?t.push(ji({boundary:this.autoSizeBoundary,padding:this.autoSizePadding,apply:({availableWidth:i,availableHeight:r})=>{this.autoSize==="vertical"||this.autoSize==="both"?this.style.setProperty("--auto-size-available-height",`${r}px`):this.style.removeProperty("--auto-size-available-height"),this.autoSize==="horizontal"||this.autoSize==="both"?this.style.setProperty("--auto-size-available-width",`${i}px`):this.style.removeProperty("--auto-size-available-width")}})):(this.style.removeProperty("--auto-size-available-width"),this.style.removeProperty("--auto-size-available-height")),this.arrow&&t.push(fo({element:this.arrowEl,padding:this.arrowPadding}));let e=this.strategy==="absolute"?i=>Zt.getOffsetParent(i,go):Zt.getOffsetParent;mo(this.anchorEl,this.popup,{placement:this.placement,middleware:t,strategy:this.strategy,platform:P($({},Zt),{getOffsetParent:e})}).then(({x:i,y:r,middlewareData:o,placement:s})=>{let n=this.localize.dir()==="rtl",a={top:"bottom",right:"left",bottom:"top",left:"right"}[s.split("-")[0]];if(this.setAttribute("data-current-placement",s),Object.assign(this.popup.style,{left:`${i}px`,top:`${r}px`}),this.arrow){let l=o.arrow.x,c=o.arrow.y,p="",h="",f="",u="";if(this.arrowPlacement==="start"){let g=typeof l=="number"?`calc(${this.arrowPadding}px - var(--arrow-padding-offset))`:"";p=typeof c=="number"?`calc(${this.arrowPadding}px - var(--arrow-padding-offset))`:"",h=n?g:"",u=n?"":g}else if(this.arrowPlacement==="end"){let g=typeof l=="number"?`calc(${this.arrowPadding}px - var(--arrow-padding-offset))`:"";h=n?"":g,u=n?g:"",f=typeof c=="number"?`calc(${this.arrowPadding}px - var(--arrow-padding-offset))`:""}else this.arrowPlacement==="center"?(u=typeof l=="number"?"calc(50% - var(--arrow-size-diagonal))":"",p=typeof c=="number"?"calc(50% - var(--arrow-size-diagonal))":""):(u=typeof l=="number"?`${l}px`:"",p=typeof c=="number"?`${c}px`:"");Object.assign(this.arrowEl.style,{top:p,right:h,bottom:f,left:u,[a]:"calc(var(--arrow-size-diagonal) * -1)"})}}),requestAnimationFrame(()=>this.updateHoverBridge()),this.emit("sl-reposition")}render(){return M`
      <slot name="anchor" @slotchange=${this.handleAnchorChange}></slot>

      <span
        part="hover-bridge"
        class=${Q({"popup-hover-bridge":!0,"popup-hover-bridge--visible":this.hoverBridge&&this.active})}
      ></span>

      <div
        part="popup"
        class=${Q({popup:!0,"popup--active":this.active,"popup--fixed":this.strategy==="fixed","popup--has-arrow":this.arrow})}
      >
        <slot></slot>
        ${this.arrow?M`<div part="arrow" class="popup__arrow" role="presentation"></div>`:""}
      </div>
    `}};x.styles=[q,_i];d([tt(".popup")],x.prototype,"popup",2);d([tt(".popup__arrow")],x.prototype,"arrowEl",2);d([m()],x.prototype,"anchor",2);d([m({type:Boolean,reflect:!0})],x.prototype,"active",2);d([m({reflect:!0})],x.prototype,"placement",2);d([m({reflect:!0})],x.prototype,"strategy",2);d([m({type:Number})],x.prototype,"distance",2);d([m({type:Number})],x.prototype,"skidding",2);d([m({type:Boolean})],x.prototype,"arrow",2);d([m({attribute:"arrow-placement"})],x.prototype,"arrowPlacement",2);d([m({attribute:"arrow-padding",type:Number})],x.prototype,"arrowPadding",2);d([m({type:Boolean})],x.prototype,"flip",2);d([m({attribute:"flip-fallback-placements",converter:{fromAttribute:t=>t.split(" ").map(e=>e.trim()).filter(e=>e!==""),toAttribute:t=>t.join(" ")}})],x.prototype,"flipFallbackPlacements",2);d([m({attribute:"flip-fallback-strategy"})],x.prototype,"flipFallbackStrategy",2);d([m({type:Object})],x.prototype,"flipBoundary",2);d([m({attribute:"flip-padding",type:Number})],x.prototype,"flipPadding",2);d([m({type:Boolean})],x.prototype,"shift",2);d([m({type:Object})],x.prototype,"shiftBoundary",2);d([m({attribute:"shift-padding",type:Number})],x.prototype,"shiftPadding",2);d([m({attribute:"auto-size"})],x.prototype,"autoSize",2);d([m()],x.prototype,"sync",2);d([m({type:Object})],x.prototype,"autoSizeBoundary",2);d([m({attribute:"auto-size-padding",type:Number})],x.prototype,"autoSizePadding",2);d([m({attribute:"hover-bridge",type:Boolean})],x.prototype,"hoverBridge",2);var er=new Map,bo=new WeakMap;function wo(t){return t??{keyframes:[],options:{duration:0}}}function tr(t,e){return e.toLowerCase()==="rtl"?{keyframes:t.rtlKeyframes||t.keyframes,options:t.options}:t}function Se(t,e){er.set(t,wo(e))}function Pe(t,e,i){let r=bo.get(t);if(r?.[e])return tr(r[e],i.dir);let o=er.get(e);return o?tr(o,i.dir):{keyframes:[],options:{duration:0}}}function Oe(t,e){return new Promise(i=>{function r(o){o.target===t&&(t.removeEventListener(e,r),i())}t.addEventListener(e,r)})}function Re(t,e,i){return new Promise(r=>{if(i?.duration===1/0)throw new Error("Promise-based animations must be finite.");let o=t.animate(e,P($({},i),{duration:_o()?0:i.duration}));o.addEventListener("cancel",r,{once:!0}),o.addEventListener("finish",r,{once:!0})})}function Le(t){return t=t.toString().toLowerCase(),t.indexOf("ms")>-1?parseFloat(t):t.indexOf("s")>-1?parseFloat(t)*1e3:parseFloat(t)}function _o(){return window.matchMedia("(prefers-reduced-motion: reduce)").matches}function Te(t){return Promise.all(t.getAnimations().map(e=>new Promise(i=>{e.cancel(),requestAnimationFrame(i)})))}function vt(t,e){let i=$({waitUntilFirstUpdate:!1},e);return(r,o)=>{let{update:s}=r,n=Array.isArray(t)?t:[t];r.update=function(a){n.forEach(l=>{let c=l;if(a.has(c)){let p=a.get(c),h=this[c];p!==h&&(!i.waitUntilFirstUpdate||this.hasUpdated)&&this[o](p,h)}}),s.call(this,a)}}}var S=class extends O{constructor(){super(),this.localize=new At(this),this.content="",this.placement="top",this.disabled=!1,this.distance=8,this.open=!1,this.skidding=0,this.trigger="hover focus",this.hoist=!1,this.handleBlur=()=>{this.hasTrigger("focus")&&this.hide()},this.handleClick=()=>{this.hasTrigger("click")&&(this.open?this.hide():this.show())},this.handleFocus=()=>{this.hasTrigger("focus")&&this.show()},this.handleDocumentKeyDown=t=>{t.key==="Escape"&&(t.stopPropagation(),this.hide())},this.handleMouseOver=()=>{if(this.hasTrigger("hover")){let t=Le(getComputedStyle(this).getPropertyValue("--show-delay"));clearTimeout(this.hoverTimeout),this.hoverTimeout=window.setTimeout(()=>this.show(),t)}},this.handleMouseOut=()=>{if(this.hasTrigger("hover")){let t=Le(getComputedStyle(this).getPropertyValue("--hide-delay"));clearTimeout(this.hoverTimeout),this.hoverTimeout=window.setTimeout(()=>this.hide(),t)}},this.addEventListener("blur",this.handleBlur,!0),this.addEventListener("focus",this.handleFocus,!0),this.addEventListener("click",this.handleClick),this.addEventListener("mouseover",this.handleMouseOver),this.addEventListener("mouseout",this.handleMouseOut)}disconnectedCallback(){var t;super.disconnectedCallback(),(t=this.closeWatcher)==null||t.destroy(),document.removeEventListener("keydown",this.handleDocumentKeyDown)}firstUpdated(){this.body.hidden=!this.open,this.open&&(this.popup.active=!0,this.popup.reposition())}hasTrigger(t){return this.trigger.split(" ").includes(t)}async handleOpenChange(){var t,e;if(this.open){if(this.disabled)return;this.emit("sl-show"),"CloseWatcher"in window?((t=this.closeWatcher)==null||t.destroy(),this.closeWatcher=new CloseWatcher,this.closeWatcher.onclose=()=>{this.hide()}):document.addEventListener("keydown",this.handleDocumentKeyDown),await Te(this.body),this.body.hidden=!1,this.popup.active=!0;let{keyframes:i,options:r}=Pe(this,"tooltip.show",{dir:this.localize.dir()});await Re(this.popup.popup,i,r),this.popup.reposition(),this.emit("sl-after-show")}else{this.emit("sl-hide"),(e=this.closeWatcher)==null||e.destroy(),document.removeEventListener("keydown",this.handleDocumentKeyDown),await Te(this.body);let{keyframes:i,options:r}=Pe(this,"tooltip.hide",{dir:this.localize.dir()});await Re(this.popup.popup,i,r),this.popup.active=!1,this.body.hidden=!0,this.emit("sl-after-hide")}}async handleOptionsChange(){this.hasUpdated&&(await this.updateComplete,this.popup.reposition())}handleDisabledChange(){this.disabled&&this.open&&this.hide()}async show(){if(!this.open)return this.open=!0,Oe(this,"sl-after-show")}async hide(){if(this.open)return this.open=!1,Oe(this,"sl-after-hide")}render(){return M`
      <sl-popup
        part="base"
        exportparts="
          popup:base__popup,
          arrow:base__arrow
        "
        class=${Q({tooltip:!0,"tooltip--open":this.open})}
        placement=${this.placement}
        distance=${this.distance}
        skidding=${this.skidding}
        strategy=${this.hoist?"fixed":"absolute"}
        flip
        shift
        arrow
        hover-bridge
      >
        ${""}
        <slot slot="anchor" aria-describedby="tooltip"></slot>

        ${""}
        <div part="body" id="tooltip" class="tooltip__body" role="tooltip" aria-live=${this.open?"polite":"off"}>
          <slot name="content">${this.content}</slot>
        </div>
      </sl-popup>
    `}};S.styles=[q,wi];S.dependencies={"sl-popup":x};d([tt("slot:not([name])")],S.prototype,"defaultSlot",2);d([tt(".tooltip__body")],S.prototype,"body",2);d([tt("sl-popup")],S.prototype,"popup",2);d([m()],S.prototype,"content",2);d([m()],S.prototype,"placement",2);d([m({type:Boolean,reflect:!0})],S.prototype,"disabled",2);d([m({type:Number})],S.prototype,"distance",2);d([m({type:Boolean,reflect:!0})],S.prototype,"open",2);d([m({type:Number})],S.prototype,"skidding",2);d([m()],S.prototype,"trigger",2);d([m({type:Boolean})],S.prototype,"hoist",2);d([vt("open",{waitUntilFirstUpdate:!0})],S.prototype,"handleOpenChange",1);d([vt(["content","distance","hoist","placement","skidding"])],S.prototype,"handleOptionsChange",1);d([vt("disabled")],S.prototype,"handleDisabledChange",1);Se("tooltip.show",{keyframes:[{opacity:0,scale:.8},{opacity:1,scale:1}],options:{duration:150,easing:"ease"}});Se("tooltip.hide",{keyframes:[{opacity:1,scale:1},{opacity:0,scale:.8}],options:{duration:150,easing:"ease"}});S.define("sl-tooltip");var ir=B`
  :host {
    display: inline-block;
  }

  .tag {
    display: flex;
    align-items: center;
    border: solid 1px;
    line-height: 1;
    white-space: nowrap;
    user-select: none;
    -webkit-user-select: none;
  }

  .tag__remove::part(base) {
    color: inherit;
    padding: 0;
  }

  /*
   * Variant modifiers
   */

  .tag--primary {
    background-color: var(--sl-color-primary-50);
    border-color: var(--sl-color-primary-200);
    color: var(--sl-color-primary-800);
  }

  .tag--primary:active > sl-icon-button {
    color: var(--sl-color-primary-600);
  }

  .tag--success {
    background-color: var(--sl-color-success-50);
    border-color: var(--sl-color-success-200);
    color: var(--sl-color-success-800);
  }

  .tag--success:active > sl-icon-button {
    color: var(--sl-color-success-600);
  }

  .tag--neutral {
    background-color: var(--sl-color-neutral-50);
    border-color: var(--sl-color-neutral-200);
    color: var(--sl-color-neutral-800);
  }

  .tag--neutral:active > sl-icon-button {
    color: var(--sl-color-neutral-600);
  }

  .tag--warning {
    background-color: var(--sl-color-warning-50);
    border-color: var(--sl-color-warning-200);
    color: var(--sl-color-warning-800);
  }

  .tag--warning:active > sl-icon-button {
    color: var(--sl-color-warning-600);
  }

  .tag--danger {
    background-color: var(--sl-color-danger-50);
    border-color: var(--sl-color-danger-200);
    color: var(--sl-color-danger-800);
  }

  .tag--danger:active > sl-icon-button {
    color: var(--sl-color-danger-600);
  }

  /*
   * Size modifiers
   */

  .tag--small {
    font-size: var(--sl-button-font-size-small);
    height: calc(var(--sl-input-height-small) * 0.8);
    line-height: calc(var(--sl-input-height-small) - var(--sl-input-border-width) * 2);
    border-radius: var(--sl-input-border-radius-small);
    padding: 0 var(--sl-spacing-x-small);
  }

  .tag--medium {
    font-size: var(--sl-button-font-size-medium);
    height: calc(var(--sl-input-height-medium) * 0.8);
    line-height: calc(var(--sl-input-height-medium) - var(--sl-input-border-width) * 2);
    border-radius: var(--sl-input-border-radius-medium);
    padding: 0 var(--sl-spacing-small);
  }

  .tag--large {
    font-size: var(--sl-button-font-size-large);
    height: calc(var(--sl-input-height-large) * 0.8);
    line-height: calc(var(--sl-input-height-large) - var(--sl-input-border-width) * 2);
    border-radius: var(--sl-input-border-radius-large);
    padding: 0 var(--sl-spacing-medium);
  }

  .tag__remove {
    margin-inline-start: var(--sl-spacing-x-small);
  }

  /*
   * Pill modifier
   */

  .tag--pill {
    border-radius: var(--sl-border-radius-pill);
  }
`;var rr=B`
  :host {
    display: inline-block;
    color: var(--sl-color-neutral-600);
  }

  .icon-button {
    flex: 0 0 auto;
    display: flex;
    align-items: center;
    background: none;
    border: none;
    border-radius: var(--sl-border-radius-medium);
    font-size: inherit;
    color: inherit;
    padding: var(--sl-spacing-x-small);
    cursor: pointer;
    transition: var(--sl-transition-x-fast) color;
    -webkit-appearance: none;
  }

  .icon-button:hover:not(.icon-button--disabled),
  .icon-button:focus-visible:not(.icon-button--disabled) {
    color: var(--sl-color-primary-600);
  }

  .icon-button:active:not(.icon-button--disabled) {
    color: var(--sl-color-primary-700);
  }

  .icon-button:focus {
    outline: none;
  }

  .icon-button--disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .icon-button:focus-visible {
    outline: var(--sl-focus-ring);
    outline-offset: var(--sl-focus-ring-offset);
  }

  .icon-button__icon {
    pointer-events: none;
  }
`;var sr=Symbol.for(""),xo=t=>{if(t?.r===sr)return t?._$litStatic$},ke=(t,...e)=>({_$litStatic$:e.reduce((i,r,o)=>i+(s=>{if(s._$litStatic$!==void 0)return s._$litStatic$;throw Error(`Value passed to 'literal' function must be a 'literal' result: ${s}. Use 'unsafeStatic' to pass non-literal values, but
            take care to ensure page security.`)})(r)+t[o+1],t[0]),r:sr}),or=new Map,ze=t=>(e,...i)=>{let r=i.length,o,s,n=[],a=[],l,c=0,p=!1;for(;c<r;){for(l=e[c];c<r&&(s=i[c],(o=xo(s))!==void 0);)l+=o+e[++c],p=!0;c!==r&&a.push(s),n.push(l),c++}if(c===r&&n.push(e[r]),p){let h=n.join("$$lit$$");(e=or.get(h))===void 0&&(n.raw=n,or.set(h,e=n)),i=a}return t(e,...i)},nr=ze(M),un=ze(ai),dn=ze(li);/*! Bundled license information:

lit-html/static.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*/var I=t=>t??C;/*! Bundled license information:

lit-html/directives/if-defined.js:
  (**
   * @license
   * Copyright 2018 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*/var{I:yn}=yi,ar=(t,e)=>e===void 0?t?._$litType$!==void 0:t?._$litType$===e;/*! Bundled license information:

lit-html/directive-helpers.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*/var Me="";function lr(t){Me=t}function cr(t=""){if(!Me){let e=[...document.getElementsByTagName("script")],i=e.find(r=>r.hasAttribute("data-shoelace"));if(i)lr(i.getAttribute("data-shoelace"));else{let r=e.find(s=>/shoelace(\.min)?\.js($|\?)/.test(s.src)||/shoelace-autoloader(\.min)?\.js($|\?)/.test(s.src)),o="";r&&(o=r.getAttribute("src")),lr(o.split("/").slice(0,-1).join("/"))}}return Me.replace(/\/$/,"")+(t?`/${t.replace(/^\//,"")}`:"")}var $o={name:"default",resolver:t=>cr(`assets/icons/${t}.svg`)},hr=$o;var pr={caret:`
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <polyline points="6 9 12 15 18 9"></polyline>
    </svg>
  `,check:`
    <svg part="checked-icon" class="checkbox__icon" viewBox="0 0 16 16">
      <g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd" stroke-linecap="round">
        <g stroke="currentColor">
          <g transform="translate(3.428571, 3.428571)">
            <path d="M0,5.71428571 L3.42857143,9.14285714"></path>
            <path d="M9.14285714,0 L3.42857143,9.14285714"></path>
          </g>
        </g>
      </g>
    </svg>
  `,"chevron-down":`
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-chevron-down" viewBox="0 0 16 16">
      <path fill-rule="evenodd" d="M1.646 4.646a.5.5 0 0 1 .708 0L8 10.293l5.646-5.647a.5.5 0 0 1 .708.708l-6 6a.5.5 0 0 1-.708 0l-6-6a.5.5 0 0 1 0-.708z"/>
    </svg>
  `,"chevron-left":`
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-chevron-left" viewBox="0 0 16 16">
      <path fill-rule="evenodd" d="M11.354 1.646a.5.5 0 0 1 0 .708L5.707 8l5.647 5.646a.5.5 0 0 1-.708.708l-6-6a.5.5 0 0 1 0-.708l6-6a.5.5 0 0 1 .708 0z"/>
    </svg>
  `,"chevron-right":`
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-chevron-right" viewBox="0 0 16 16">
      <path fill-rule="evenodd" d="M4.646 1.646a.5.5 0 0 1 .708 0l6 6a.5.5 0 0 1 0 .708l-6 6a.5.5 0 0 1-.708-.708L10.293 8 4.646 2.354a.5.5 0 0 1 0-.708z"/>
    </svg>
  `,copy:`
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-copy" viewBox="0 0 16 16">
      <path fill-rule="evenodd" d="M4 2a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V2Zm2-1a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1H6ZM2 5a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1v-1h1v1a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h1v1H2Z"/>
    </svg>
  `,eye:`
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-eye" viewBox="0 0 16 16">
      <path d="M16 8s-3-5.5-8-5.5S0 8 0 8s3 5.5 8 5.5S16 8 16 8zM1.173 8a13.133 13.133 0 0 1 1.66-2.043C4.12 4.668 5.88 3.5 8 3.5c2.12 0 3.879 1.168 5.168 2.457A13.133 13.133 0 0 1 14.828 8c-.058.087-.122.183-.195.288-.335.48-.83 1.12-1.465 1.755C11.879 11.332 10.119 12.5 8 12.5c-2.12 0-3.879-1.168-5.168-2.457A13.134 13.134 0 0 1 1.172 8z"/>
      <path d="M8 5.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5zM4.5 8a3.5 3.5 0 1 1 7 0 3.5 3.5 0 0 1-7 0z"/>
    </svg>
  `,"eye-slash":`
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-eye-slash" viewBox="0 0 16 16">
      <path d="M13.359 11.238C15.06 9.72 16 8 16 8s-3-5.5-8-5.5a7.028 7.028 0 0 0-2.79.588l.77.771A5.944 5.944 0 0 1 8 3.5c2.12 0 3.879 1.168 5.168 2.457A13.134 13.134 0 0 1 14.828 8c-.058.087-.122.183-.195.288-.335.48-.83 1.12-1.465 1.755-.165.165-.337.328-.517.486l.708.709z"/>
      <path d="M11.297 9.176a3.5 3.5 0 0 0-4.474-4.474l.823.823a2.5 2.5 0 0 1 2.829 2.829l.822.822zm-2.943 1.299.822.822a3.5 3.5 0 0 1-4.474-4.474l.823.823a2.5 2.5 0 0 0 2.829 2.829z"/>
      <path d="M3.35 5.47c-.18.16-.353.322-.518.487A13.134 13.134 0 0 0 1.172 8l.195.288c.335.48.83 1.12 1.465 1.755C4.121 11.332 5.881 12.5 8 12.5c.716 0 1.39-.133 2.02-.36l.77.772A7.029 7.029 0 0 1 8 13.5C3 13.5 0 8 0 8s.939-1.721 2.641-3.238l.708.709zm10.296 8.884-12-12 .708-.708 12 12-.708.708z"/>
    </svg>
  `,eyedropper:`
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-eyedropper" viewBox="0 0 16 16">
      <path d="M13.354.646a1.207 1.207 0 0 0-1.708 0L8.5 3.793l-.646-.647a.5.5 0 1 0-.708.708L8.293 5l-7.147 7.146A.5.5 0 0 0 1 12.5v1.793l-.854.853a.5.5 0 1 0 .708.707L1.707 15H3.5a.5.5 0 0 0 .354-.146L11 7.707l1.146 1.147a.5.5 0 0 0 .708-.708l-.647-.646 3.147-3.146a1.207 1.207 0 0 0 0-1.708l-2-2zM2 12.707l7-7L10.293 7l-7 7H2v-1.293z"></path>
    </svg>
  `,"grip-vertical":`
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-grip-vertical" viewBox="0 0 16 16">
      <path d="M7 2a1 1 0 1 1-2 0 1 1 0 0 1 2 0zm3 0a1 1 0 1 1-2 0 1 1 0 0 1 2 0zM7 5a1 1 0 1 1-2 0 1 1 0 0 1 2 0zm3 0a1 1 0 1 1-2 0 1 1 0 0 1 2 0zM7 8a1 1 0 1 1-2 0 1 1 0 0 1 2 0zm3 0a1 1 0 1 1-2 0 1 1 0 0 1 2 0zm-3 3a1 1 0 1 1-2 0 1 1 0 0 1 2 0zm3 0a1 1 0 1 1-2 0 1 1 0 0 1 2 0zm-3 3a1 1 0 1 1-2 0 1 1 0 0 1 2 0zm3 0a1 1 0 1 1-2 0 1 1 0 0 1 2 0z"></path>
    </svg>
  `,indeterminate:`
    <svg part="indeterminate-icon" class="checkbox__icon" viewBox="0 0 16 16">
      <g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd" stroke-linecap="round">
        <g stroke="currentColor" stroke-width="2">
          <g transform="translate(2.285714, 6.857143)">
            <path d="M10.2857143,1.14285714 L1.14285714,1.14285714"></path>
          </g>
        </g>
      </g>
    </svg>
  `,"person-fill":`
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-person-fill" viewBox="0 0 16 16">
      <path d="M3 14s-1 0-1-1 1-4 6-4 6 3 6 4-1 1-1 1H3zm5-6a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"/>
    </svg>
  `,"play-fill":`
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-play-fill" viewBox="0 0 16 16">
      <path d="m11.596 8.697-6.363 3.692c-.54.313-1.233-.066-1.233-.697V4.308c0-.63.692-1.01 1.233-.696l6.363 3.692a.802.802 0 0 1 0 1.393z"></path>
    </svg>
  `,"pause-fill":`
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-pause-fill" viewBox="0 0 16 16">
      <path d="M5.5 3.5A1.5 1.5 0 0 1 7 5v6a1.5 1.5 0 0 1-3 0V5a1.5 1.5 0 0 1 1.5-1.5zm5 0A1.5 1.5 0 0 1 12 5v6a1.5 1.5 0 0 1-3 0V5a1.5 1.5 0 0 1 1.5-1.5z"></path>
    </svg>
  `,radio:`
    <svg part="checked-icon" class="radio__icon" viewBox="0 0 16 16">
      <g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
        <g fill="currentColor">
          <circle cx="8" cy="8" r="3.42857143"></circle>
        </g>
      </g>
    </svg>
  `,"star-fill":`
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-star-fill" viewBox="0 0 16 16">
      <path d="M3.612 15.443c-.386.198-.824-.149-.746-.592l.83-4.73L.173 6.765c-.329-.314-.158-.888.283-.95l4.898-.696L7.538.792c.197-.39.73-.39.927 0l2.184 4.327 4.898.696c.441.062.612.636.282.95l-3.522 3.356.83 4.73c.078.443-.36.79-.746.592L8 13.187l-4.389 2.256z"/>
    </svg>
  `,"x-lg":`
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-x-lg" viewBox="0 0 16 16">
      <path d="M2.146 2.854a.5.5 0 1 1 .708-.708L8 7.293l5.146-5.147a.5.5 0 0 1 .708.708L8.707 8l5.147 5.146a.5.5 0 0 1-.708.708L8 8.707l-5.146 5.147a.5.5 0 0 1-.708-.708L7.293 8 2.146 2.854Z"/>
    </svg>
  `,"x-circle-fill":`
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-x-circle-fill" viewBox="0 0 16 16">
      <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zM5.354 4.646a.5.5 0 1 0-.708.708L7.293 8l-2.647 2.646a.5.5 0 0 0 .708.708L8 8.707l2.646 2.647a.5.5 0 0 0 .708-.708L8.707 8l2.647-2.646a.5.5 0 0 0-.708-.708L8 7.293 5.354 4.646z"></path>
    </svg>
  `},Ao={name:"system",resolver:t=>t in pr?`data:image/svg+xml,${encodeURIComponent(pr[t])}`:""},ur=Ao;var Eo=[hr,ur],Be=[];function dr(t){Be.push(t)}function fr(t){Be=Be.filter(e=>e!==t)}function De(t){return Eo.find(e=>e.name===t)}var mr=B`
  :host {
    display: inline-block;
    width: 1em;
    height: 1em;
    box-sizing: content-box !important;
  }

  svg {
    display: block;
    height: 100%;
    width: 100%;
  }
`;var Nt=Symbol(),oe=Symbol(),Ne,He=new Map,Z=class extends O{constructor(){super(...arguments),this.initialRender=!1,this.svg=null,this.label="",this.library="default"}async resolveIcon(t,e){var i;let r;if(e?.spriteSheet)return this.svg=M`<svg part="svg">
        <use part="use" href="${t}"></use>
      </svg>`,this.svg;try{if(r=await fetch(t,{mode:"cors"}),!r.ok)return r.status===410?Nt:oe}catch{return oe}try{let o=document.createElement("div");o.innerHTML=await r.text();let s=o.firstElementChild;if(((i=s?.tagName)==null?void 0:i.toLowerCase())!=="svg")return Nt;Ne||(Ne=new DOMParser);let a=Ne.parseFromString(s.outerHTML,"text/html").body.querySelector("svg");return a?(a.part.add("svg"),document.adoptNode(a)):Nt}catch{return Nt}}connectedCallback(){super.connectedCallback(),dr(this)}firstUpdated(){this.initialRender=!0,this.setIcon()}disconnectedCallback(){super.disconnectedCallback(),fr(this)}getIconSource(){let t=De(this.library);return this.name&&t?{url:t.resolver(this.name),fromLibrary:!0}:{url:this.src,fromLibrary:!1}}handleLabelChange(){typeof this.label=="string"&&this.label.length>0?(this.setAttribute("role","img"),this.setAttribute("aria-label",this.label),this.removeAttribute("aria-hidden")):(this.removeAttribute("role"),this.removeAttribute("aria-label"),this.setAttribute("aria-hidden","true"))}async setIcon(){var t;let{url:e,fromLibrary:i}=this.getIconSource(),r=i?De(this.library):void 0;if(!e){this.svg=null;return}let o=He.get(e);if(o||(o=this.resolveIcon(e,r),He.set(e,o)),!this.initialRender)return;let s=await o;if(s===oe&&He.delete(e),e===this.getIconSource().url){if(ar(s)){if(this.svg=s,r){await this.updateComplete;let n=this.shadowRoot.querySelector("[part='svg']");typeof r.mutator=="function"&&n&&r.mutator(n)}return}switch(s){case oe:case Nt:this.svg=null,this.emit("sl-error");break;default:this.svg=s.cloneNode(!0),(t=r?.mutator)==null||t.call(r,this.svg),this.emit("sl-load")}}}render(){return this.svg}};Z.styles=[q,mr];d([Kt()],Z.prototype,"svg",2);d([m({reflect:!0})],Z.prototype,"name",2);d([m()],Z.prototype,"src",2);d([m()],Z.prototype,"label",2);d([m({reflect:!0})],Z.prototype,"library",2);d([vt("label")],Z.prototype,"handleLabelChange",1);d([vt(["name","src","library"])],Z.prototype,"setIcon",1);var R=class extends O{constructor(){super(...arguments),this.hasFocus=!1,this.label="",this.disabled=!1}handleBlur(){this.hasFocus=!1,this.emit("sl-blur")}handleFocus(){this.hasFocus=!0,this.emit("sl-focus")}handleClick(t){this.disabled&&(t.preventDefault(),t.stopPropagation())}click(){this.button.click()}focus(t){this.button.focus(t)}blur(){this.button.blur()}render(){let t=!!this.href,e=t?ke`a`:ke`button`;return nr`
      <${e}
        part="base"
        class=${Q({"icon-button":!0,"icon-button--disabled":!t&&this.disabled,"icon-button--focused":this.hasFocus})}
        ?disabled=${I(t?void 0:this.disabled)}
        type=${I(t?void 0:"button")}
        href=${I(t?this.href:void 0)}
        target=${I(t?this.target:void 0)}
        download=${I(t?this.download:void 0)}
        rel=${I(t&&this.target?"noreferrer noopener":void 0)}
        role=${I(t?void 0:"button")}
        aria-disabled=${this.disabled?"true":"false"}
        aria-label="${this.label}"
        tabindex=${this.disabled?"-1":"0"}
        @blur=${this.handleBlur}
        @focus=${this.handleFocus}
        @click=${this.handleClick}
      >
        <sl-icon
          class="icon-button__icon"
          name=${I(this.name)}
          library=${I(this.library)}
          src=${I(this.src)}
          aria-hidden="true"
        ></sl-icon>
      </${e}>
    `}};R.styles=[q,rr];R.dependencies={"sl-icon":Z};d([tt(".icon-button")],R.prototype,"button",2);d([Kt()],R.prototype,"hasFocus",2);d([m()],R.prototype,"name",2);d([m()],R.prototype,"library",2);d([m()],R.prototype,"src",2);d([m()],R.prototype,"href",2);d([m()],R.prototype,"target",2);d([m()],R.prototype,"download",2);d([m()],R.prototype,"label",2);d([m({type:Boolean,reflect:!0})],R.prototype,"disabled",2);var lt=class extends O{constructor(){super(...arguments),this.localize=new At(this),this.variant="neutral",this.size="medium",this.pill=!1,this.removable=!1}handleRemoveClick(){this.emit("sl-remove")}render(){return M`
      <span
        part="base"
        class=${Q({tag:!0,"tag--primary":this.variant==="primary","tag--success":this.variant==="success","tag--neutral":this.variant==="neutral","tag--warning":this.variant==="warning","tag--danger":this.variant==="danger","tag--text":this.variant==="text","tag--small":this.size==="small","tag--medium":this.size==="medium","tag--large":this.size==="large","tag--pill":this.pill,"tag--removable":this.removable})}
      >
        <slot part="content" class="tag__content"></slot>

        ${this.removable?M`
              <sl-icon-button
                part="remove-button"
                exportparts="base:remove-button__base"
                name="x-lg"
                library="system"
                label=${this.localize.term("remove")}
                class="tag__remove"
                @click=${this.handleRemoveClick}
                tabindex="-1"
              ></sl-icon-button>
            `:""}
      </span>
    `}};lt.styles=[q,ir];lt.dependencies={"sl-icon-button":R};d([m({reflect:!0})],lt.prototype,"variant",2);d([m({reflect:!0})],lt.prototype,"size",2);d([m({type:Boolean,reflect:!0})],lt.prototype,"pill",2);d([m({type:Boolean})],lt.prototype,"removable",2);lt.define("sl-tag");
