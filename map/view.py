"""Add the plugin code map to the existing router research board."""

import json
import re


STYLE = """
<style id="router-node-style">
.app.router-nodes-active{--stage-navigation-width:0px;--inspector-width:0px}
.app.router-nodes-active > .sidebar{display:none!important}
.app.router-nodes-active :is(#inspector,.workspace-header,#nativeBoard,#drawioHost,
 #capabilityPanel,#semanticPanel,#proposalPanel,#comparisonPanel,#allComparisonsPanel,.canvas-stamp,
 .canvas-actions,.foot,.toolbar .search,.toolbar .toggle-btn,.toolbar .zoom-controls,.toolbar .view-label,
 #mobileInspect,#engineButton){display:none!important}
.app.router-nodes-active .toolbar{min-height:46px;flex:none;padding:6px 16px}
#routerNodePanel[hidden]{display:none}
.router-node-cli-link{display:inline-block;margin-top:.45rem;color:#3d446d;font-weight:650}
.router-node-cli-link:focus-visible{outline:2px solid #3d446d;outline-offset:2px}
#routerNodePanel{position:absolute;inset:0;z-index:15;overflow:auto;background:#f5f2ec;
 color:#262b3f;line-height:1.5;font-size:1rem;overflow-wrap:anywhere}
#routerNodePanel :is(a, input, select, summary, [tabindex]):focus-visible{outline:2px solid #3d446d;outline-offset:2px}
#routerNodePanel a{color:#3d446d}
#routerNodePanel header{padding:20px clamp(14px,4vw,48px);background:#faf8f4;border-bottom:1px solid #ded9d4}
#routerNodePanel h2,#routerNodePanel h3{font-family:var(--display,Georgia,serif);line-height:1.16;margin:0}
#routerNodePanel h2{font-size:clamp(1.55rem,4vw,2.25rem)}
#routerNodePanel h3{font-size:clamp(1.3rem,3vw,1.85rem)}
#routerNodePanel header p{margin:.35rem 0 0;color:#525766}
#routerNodePanel .router-node-layout{display:grid;grid-template-columns:minmax(16rem,28%) minmax(0,1fr);
 align-items:start;gap:clamp(12px,2vw,28px);padding:clamp(12px,4vw,48px)}
.app.stage-navigation-collapsed #routerNodePanel .router-node-layout{grid-template-columns:minmax(0,1fr)}
#routerNodePanel .router-node-index,#routerNodeDetail{min-width:0;border:1px solid #dfdad3;border-radius:12px;background:#faf8f4;padding:clamp(12px,2vw,24px)}
#routerNodePanel label{display:block;font-weight:700}
#routerNodePanel :is(input,select){width:100%;min-height:2.65rem;border:1px solid #a6a1b4;border-radius:8px;
 background:#fff;color:#262b3f;font:inherit;padding:.45rem .65rem;margin:.35rem 0}
#routerNodePanel .router-node-filter{display:grid;grid-template-columns:1fr;gap:.1rem}
#routerNodeIndex{max-height:clamp(14rem,48vh,36rem);overflow:auto;scrollbar-width:thin}
#routerNodeCount{font-size:.875rem;color:#525766;margin:.4rem 0}
#routerNodePanel ul{padding:0;margin:0;list-style:none}
#routerNodePanel h3.router-node-group{margin:.85rem 0 .25rem;font-size:.875rem;font-weight:700;color:#4c4663}
#routerNodeIndex a{display:block;text-decoration:none;border:1px solid transparent;border-radius:8px;padding:.5rem .6rem}
#routerNodeIndex a:hover,#routerNodeIndex a[aria-current]{background:#f0edf6;border-color:#c0b7d3}
#routerNodeIndex a[aria-current]{box-shadow:inset 3px 0 #554675}
#routerNodeIndex small,#routerNodePanel .router-node-meta{display:block;font-size:.875rem;color:#525766}
#routerNodePanel .router-node-file{font-family:var(--mono,monospace);font-size:.9rem}
#routerNodePanel .router-node-meta{margin:.4rem 0;font-weight:700}
#routerNodePanel .router-node-fields{display:grid;grid-template-columns:max-content minmax(0,1fr);gap:.3rem .85rem;margin:1rem 0}
#routerNodePanel .router-node-fields dt{font-weight:700}
#routerNodePanel .router-node-fields dd{min-width:0;margin:0}
#routerNodePanel .router-node-links{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.75rem;margin:1rem 0}
#routerNodePanel .router-node-links section{border:1px solid #dfdad3;border-radius:8px;padding:.75rem;min-width:0}
#routerNodePanel h4{font-size:1rem;margin:0 0 .45rem}
#routerNodePanel .router-node-links li+li{margin-top:.55rem;padding-top:.55rem;border-top:1px solid #e4e0da}
#routerNodePanel .router-node-links details{margin:0;padding:0;border:0;background:transparent}
#routerNodePanel .router-node-links details ul{margin-top:.65rem}
#routerNodePanel .router-node-links p{margin:.2rem 0 0;color:#525766;font-size:.9rem}
#routerNodePanel #routerNodeDetail > details{padding:.65rem .8rem;border:1px solid #c7bfd5;border-radius:8px;background:#f0edf6}
#routerNodePanel summary{cursor:pointer;font-weight:700}
#routerNodePanel pre{white-space:pre-wrap;font:.875rem/1.5 var(--mono,monospace);overflow-wrap:anywhere}
@media (max-width:740px){
 #routerNodePanel .router-node-layout,#routerNodePanel .router-node-links{grid-template-columns:minmax(0,1fr)}
 #routerNodeIndex{max-height:12rem;overflow:auto}
}
@media (max-width:380px){
 #routerNodePanel .router-node-fields{grid-template-columns:minmax(0,1fr);gap:.15rem}
 #routerNodePanel .router-node-fields dd{margin-bottom:.4rem}
}
</style>
"""

PANEL = """
<section id="routerNodePanel" aria-labelledby="routerNodeTitle" hidden>
 <header>
  <h2 id="routerNodeTitle" tabindex="-1">Mapa del plugin</h2>
  <p id="routerNodePlugin"></p>
 </header>
 <div class="router-node-layout">
  <nav id="routerNodeNavigation" class="router-node-index" data-board-sidebar aria-label="Índice de nodos del plugin">
   <div class="router-node-filter">
    <label for="routerNodeSearch">Buscar nodos</label>
    <input type="search" id="routerNodeSearch" placeholder="Archivo, ID o símbolo" autocomplete="off" aria-controls="routerNodeIndex">
    <label for="routerNodeGroup">Grupo</label>
    <select id="routerNodeGroup" aria-controls="routerNodeIndex"><option value="">Todos los grupos</option></select>
   </div>
   <p id="routerNodeCount" role="status"></p>
   <div id="routerNodeIndex"></div>
  </nav>
  <article id="routerNodeDetail" aria-label="Detalle del nodo"></article>
 </div>
</section>
"""

SCRIPT = r"""
<script id="router-node-script">
(() => {
 'use strict';
 const byId = id => document.getElementById(id);
 const {nodes, edges, plugin} = JSON.parse(byId('routerNodeData').textContent);
 const nodeById = new Map(nodes.map(node => [String(node.id), node]));
 const incoming = new Map(), outgoing = new Map();
 function addEdge(index, id, edge) {
  if (!index.has(id)) index.set(id, []);
  index.get(id).push(edge);
 }
 for (const edge of edges) {
  const from = String(edge.from), to = String(edge.to);
  if (!nodeById.has(from) || !nodeById.has(to)) continue;
  addEdge(outgoing, from, edge);
  addEdge(incoming, to, edge);
 }
 const view = byId('routerNodeView'), panel = byId('routerNodePanel');
 const app = document.querySelector('.app'), index = byId('routerNodeIndex');
 const search = byId('routerNodeSearch'), groupFilter = byId('routerNodeGroup');
 const detail = byId('routerNodeDetail');
 const defaultId = nodeById.has('Q00') ? 'Q00' : nodes[0]?.id;
 const groupOf = node => node.group || 'Otros nodos';
 const otherViews = [...view.parentElement.querySelectorAll('button[aria-controls]')].filter(button => button !== view);
 const nodePrefix = 'router-node-';
 let selectedId = null;

 function make(tag, content, className) {
  const item = document.createElement(tag);
  if (content != null) item.textContent = String(content);
  if (className) item.className = className;
  return item;
 }
 function nodeHash(id) { return '#' + nodePrefix + encodeURIComponent(id); }
 function normalized(value) {
  return String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('es');
 }
 function fromHash() {
  if (!location.hash.startsWith('#' + nodePrefix)) return null;
  try {
   const id = decodeURIComponent(location.hash.slice(nodePrefix.length + 1));
   return nodeById.has(id) ? id : null;
  } catch {
   return null;
  }
 }
 function nodeLink(node, indexLink = false) {
  const id = String(node.id), link = make('a', node.title || id);
  link.setAttribute('href', nodeHash(id));
  link.dataset.routerTarget = id;
  if (indexLink) link.append(make('small', [id, node.path].filter(Boolean).join(' · ')));
  return link;
 }
 function markCurrent() {
  for (const link of index.querySelectorAll('a[data-router-target]')) {
   if (link.dataset.routerTarget === selectedId) link.setAttribute('aria-current', 'location');
   else link.removeAttribute('aria-current');
  }
 }
 function renderIndex() {
  const query = normalized(search.value).trim().split(/\s+/).filter(Boolean);
  const matches = nodes.filter(node => {
   if (groupFilter.value && groupOf(node) !== groupFilter.value) return false;
   const searchable = normalized([node.id, node.title, node.path, node.symbol, node.group, ...(node.aliases || [])].join(' '));
   return query.every(term => searchable.includes(term));
  });
  const groups = new Map();
  for (const node of matches) {
   const group = groupOf(node);
   if (!groups.has(group)) groups.set(group, []);
   groups.get(group).push(node);
  }
  const output = document.createDocumentFragment();
  for (const [group, items] of groups) {
   const heading = make('h3', group, 'router-node-group'), list = make('ul');
   for (const node of items) {
    const row = make('li');
    row.append(nodeLink(node, true));
    list.append(row);
   }
   output.append(heading, list);
  }
  index.replaceChildren(output);
  byId('routerNodeCount').textContent = query.length || groupFilter.value
   ? (matches.length ? `${matches.length} de ${nodes.length} nodos` : 'Sin nodos para esta búsqueda.')
   : `${nodes.length} ${nodes.length === 1 ? 'nodo' : 'nodos'}`;
  markCurrent();
 }
 function neighbors(title, items, end) {
  if (!items?.length) return null;
  const section = make('section'), list = make('ul');
  if (items.length > 14) {
   const disclosure = make('details');
   disclosure.append(make('summary', `${title} · ${items.length}`), list);
   section.append(disclosure);
  } else {
   section.append(make('h4', title), list);
  }
  for (const edge of items) {
   const other = nodeById.get(String(edge[end]));
   const row = make('li'), link = nodeLink(other);
   if (other.title && other.title !== other.id) link.append(document.createTextNode(` · ${other.id}`));
   row.append(link);
   if (edge.condition) row.append(make('p', edge.condition));
   list.append(row);
  }
  return section;
 }
 function select(id, focus = false) {
  const node = nodeById.get(id);
  if (!node) return;
  if (selectedId === id && detail.firstElementChild) {
   if (focus) byId(nodePrefix + id).focus();
   return;
  }
  selectedId = id;
  const heading = make('h3', node.title || id);
  heading.id = nodePrefix + id;
  heading.tabIndex = -1;
  const meta = make('p', [id, node.group].filter(Boolean).join(' · '), 'router-node-meta');
  const fields = make('dl', null, 'router-node-fields');
  const path = node.path ? node.path + (node.line ? ':' + node.line : '') : '';
  for (const [label, value] of [['Archivo', path], ['Símbolo', node.symbol]]) {
   if (!value) continue;
   fields.append(make('dt', label));
   const cell = make('dd');
   cell.append(make('code', value, 'router-node-file'));
   fields.append(cell);
  }
  const summary = node.summary ? make('p', node.summary) : null;
  const related = make('div', null, 'router-node-links');
  const outEdges = outgoing.get(id) || [], inEdges = incoming.get(id) || [];
  const isPython = (edge, key) => /\.py$/i.test(nodeById.get(String(edge[key]))?.path || '');
  if (id === 'Q00') {
   for (const [title, edges, key] of [
    ['Accede a código Python', outEdges, 'to'],
    ['Consultado desde código Python', inEdges, 'from'],
   ]) {
    const section = neighbors(title, edges.filter(edge => isPython(edge, key)), key);
    if (section) related.append(section);
   }
  }
  const out = neighbors('Conduce a', outEdges.filter(edge => id !== 'Q00' || !isPython(edge, 'to')), 'to');
  const inc = neighbors('Llega desde', inEdges.filter(edge => id !== 'Q00' || !isPython(edge, 'from')), 'from');
  if (out) related.append(out);
  if (inc) related.append(inc);
  const content = [heading, meta];
  if (fields.childElementCount) content.push(fields);
  if (summary) content.push(summary);
  if (related.childElementCount) content.push(related);
  else content.push(make('p', 'Sin relaciones registradas para este nodo.', 'router-node-meta'));
  if (node.source) {
   const disclosure = make('details');
   disclosure.append(make('summary', 'Ver fuente'), make('pre', node.source));
   content.push(disclosure);
  }
  detail.replaceChildren(...content);
  markCurrent();
  if (focus) heading.focus();
 }
 function open(id = selectedId || defaultId) {
  if (panel.hidden) {
   byId('stageMapView').click();
   app.classList.add('router-nodes-active');
   panel.hidden = false;
   view.setAttribute('aria-pressed', 'true');
   for (const button of otherViews) button.setAttribute('aria-pressed', 'false');
  }
  if (id != null) select(String(id));
  else detail.textContent = 'El mapa aún no contiene nodos.';
 }
 function close() {
  if (panel.hidden) return;
  panel.hidden = true;
  view.setAttribute('aria-pressed', 'false');
  app.classList.remove('router-nodes-active');
  if (fromHash() !== null) {
   const url = new URL(location.href);
   url.hash = '';
   history.replaceState(history.state, '', url);
  }
 }
 function syncLocation() {
  const id = fromHash();
  if (id !== null) open(id);
  else if (!panel.hidden && defaultId != null) select(String(defaultId));
 }
 function init() {
  const info = [plugin.name || 'Design Skills Router'];
  if (plugin.version) info.push('v' + plugin.version);
  if (plugin.release) info.push(plugin.release);
  byId('routerNodePlugin').textContent = info.join(' · ');
  const groups = [...new Set(nodes.map(groupOf))].sort((a, b) => a.localeCompare(b, 'es'));
  for (const group of groups) {
   const option = make('option', group);
   option.value = group;
   groupFilter.append(option);
  }
  renderIndex();
  view.addEventListener('click', () => { open(); byId('routerNodeTitle').focus({preventScroll:true}); });
  for (const button of otherViews) button.addEventListener('click', close, true);
  search.addEventListener('input', renderIndex);
  groupFilter.addEventListener('change', renderIndex);
  panel.addEventListener('click', event => {
   const link = event.target.closest('a[data-router-target]');
   if (!link || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
   event.preventDefault();
   if (location.hash !== link.hash) history.pushState(history.state, '', link.hash);
   select(link.dataset.routerTarget, true);
  });
  window.addEventListener('hashchange', syncLocation);
  window.addEventListener('popstate', syncLocation);
  syncLocation();
 }
 if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, {once:true});
 else init();
})();
</script>
"""


def insert_after(html, pattern, content):
    match = re.search(pattern, html)
    if match is None:
        raise ValueError(f"Missing router canvas anchor: {pattern}")
    return html[:match.end()] + content + html[match.end():]


def render(html, graph):
    """Return a self-contained board with an index and deep links for plugin nodes."""
    if 'id="routerNodePanel"' in html:
        raise ValueError("The board already contains a plugin map")
    payload = json.dumps(graph, ensure_ascii=True, separators=(",", ":"))
    payload = payload.replace("<", r"\u003c").replace(">", r"\u003e").replace("&", r"\u0026")
    button = (
        '<button type="button" id="routerNodeView" aria-pressed="false" '
        'aria-controls="routerNodePanel">Mapa del plugin</button>'
    )
    html = insert_after(html, r'<button\b[^>]*\bid="stageMapView"[^>]*>[^<]*</button>', button)
    if any(node["id"] == "py-runner-start" for node in graph["nodes"]):
        cli_link = (
            '<a class="router-node-cli-link" href="#router-node-py-runner-start">'
            'Ver entrada CLI en Python</a>'
        )
        html = insert_after(html, r'<details class="intro-disclosure">.*?</details>', cli_link)
    html = insert_after(html, r'<section\b[^>]*\bid="canvasFrame"[^>]*>', PANEL)
    html = html.replace("</head>", STYLE + "\n</head>", 1)
    bundle = f'<script id="routerNodeData" type="application/json">{payload}</script>\n' + SCRIPT
    return html.replace("</body>", bundle + "\n</body>", 1)
