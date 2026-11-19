"""Exercise the built HTML in isolated Chromium; does not control the user's browser."""
from pathlib import Path
import json,time,sys,os,shutil
from playwright.sync_api import sync_playwright
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P));from model import expand_model,flatten
E=P/'evidence'; html=(P/'index.html').read_text();results=[]
def check(name,ok,detail=None):
 results.append(dict(name=name,pass_=bool(ok),detail=detail))

def overflow(page):return page.evaluate('({viewport:innerWidth,scroll:document.documentElement.scrollWidth})')
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH') or shutil.which('chromium'),headless=True,args=['--no-sandbox']);errors=[]
 page=b.new_page(viewport={'width':1440,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
 start=time.monotonic();page.set_content(html,wait_until='load');check('initial_render',page.locator('#branch-title').get_attribute('data-node')=='Q00',round(time.monotonic()-start,3));expected=expand_model(json.loads((P/'tree.json').read_text()));expected_rows=sorted((n['id'],n.get('candidate_key'),n.get('context_mode')) for n in flatten(expected['root']));actual_rows=page.evaluate('Object.values(nodes).map(n=>[n.id,n.candidate_key||null,n.context_mode||null]).sort((a,b)=>a[0].localeCompare(b[0]))');actual_rows=sorted(tuple(x) for x in actual_rows);check('python_js_tree_parity',actual_rows==expected_rows,len(actual_rows));check('title',page.title()=='Árbol de decisiones de diseño · v0.4');check('root_three_branches',page.locator('#canvas a[data-node="F00"]').count()==1)
 page.screenshot(path=str(E/'desktop-root.png'),full_page=False)
 page.locator('#canvas a[data-node="F00"]').click();page.wait_for_function('document.querySelector("#branch-title").dataset.node==="F00"');check('graph_click_opens_branch',page.locator('#canvas').get_attribute('data-root')=='F00')
 page.locator('#view').select_option('ART00');page.wait_for_function('document.querySelector("#branch-title").dataset.node==="ART00"');check('art_direction_has_five_questions',page.locator('#canvas a[data-node^="ART0"]').count()>=6)
 page.locator('#canvas a[data-node="ART01"]').focus();page.keyboard.press('Enter');page.wait_for_function('document.querySelector("#branch-title").dataset.node==="ART01"');check('keyboard_explores',page.locator('#canvas').get_attribute('data-root')=='ART01')
 page.locator('#inspect-current').click();check('source_details_visible',page.locator('#inspect').is_visible() and 'Fase 1' in page.locator('#inspect').inner_text());check('source_is_pinned', '5211aae' in (page.locator('#inspect a').first.get_attribute('href') or ''))
 page.locator('#up').click();page.wait_for_function('document.querySelector("#branch-title").dataset.node==="ART00"');check('parent_navigation',page.locator('#branch-title').get_attribute('data-node')=='ART00')
 # Deep links update the actual branch, not just the inspector.
 page.evaluate('location.hash="R05"');page.wait_for_function('document.querySelector("#branch-title").dataset.node==="R05"');check('hash_opens_named_candidate', page.locator('#canvas a[data-node="R05__ADOPT"]').count()==1)
 page.locator('#canvas a[data-node="R05__ADOPT"]').click();page.wait_for_function('document.querySelector("#branch-title").dataset.node==="R05__ADOPT"');check('candidate_has_bound_assessment', page.locator('#canvas a[data-node="R05__ADOPT_LICENSE"]').count()==1)
 page.locator('#inspect-current').click();check('candidate_binding_in_inspector','R05 · componente' in page.locator('#inspect').inner_text())
 # Existing project reuses the shared definition but has a unique context path.
 page.locator('#node-search').fill('E03__D10');page.locator('#search-form button').click();page.wait_for_function('document.querySelector("#branch-title").dataset.node==="E03__D10"');check('existing_path_review',page.locator('#canvas a[data-node="E03__ART00"]').count()==1)
 page.locator('#node-search').fill('<script>');page.locator('#search-form button').click();check('invalid_id_safe','No se encontró' in page.locator('#notice').inner_text())
 # Check every bookmark.
 for value in page.locator('#view option').evaluate_all('(xs)=>xs.map(x=>x.value).filter(Boolean)'):
  page.locator('#view').select_option(value);page.wait_for_function('(id)=>document.querySelector("#branch-title").dataset.node===id',arg=value);check('bookmark_'+value,page.locator('#canvas').get_attribute('data-root')==value)
  bounds=page.evaluate('''()=>{const s=document.querySelector('#canvas svg'),v=s.viewBox.baseVal;return [...s.querySelectorAll('text')].filter(t=>{const b=t.getBBox();return b.y<0||b.x<0||b.x+b.width>v.width+1||b.y+b.height>v.height+1}).map(t=>t.textContent)}''');check('svg_text_bounds_'+value,not bounds,bounds)
 check('no_runtime_errors',not errors,errors)
 for width in [320,390,768,1440]:
  pg=b.new_page(viewport={'width':width,'height':900});pg.set_content(html,wait_until='load');root_visible=pg.evaluate('''()=>{const c=document.querySelector('#canvas').getBoundingClientRect(),r=document.querySelector('#canvas a[data-node="Q00"] rect').getBoundingClientRect();return r.top>=c.top && r.bottom<=c.bottom}''');check('root_visible_in_canvas_'+str(width),root_visible);v=overflow(pg);check('initial_width_'+str(width),v['scroll']<=v['viewport'],v)
  pg.locator('#expand').click();v=overflow(pg);check('expanded_width_'+str(width),v['scroll']<=v['viewport'],v)
  check('expanded_all_instances_'+str(width),pg.locator('#outline details:not([open])').count()==0,pg.locator('#outline details').count())
  # Deep node text uses available width, not recursively shrinking columns.
  pg.locator('#view').select_option('R01');pg.wait_for_function('document.querySelector("#branch-title").dataset.node==="R01"');pg.locator('#expand').click();v=overflow(pg);check('deep_width_'+str(width),v['scroll']<=v['viewport'],v)
  if width in [320,390]:
   pg.locator('.explorer h2').scroll_into_view_if_needed();pg.screenshot(path=str(E/f'mobile-{width}-expanded.png'),full_page=False)
  pg.locator('#collapse').click();check('collapse_'+str(width),pg.locator('#outline details[open]').count()==1)
  pg.close()
 # Text spacing probe: inspect overflow, not a whole accessibility certification.
 page.locator('#view').select_option('T00');page.wait_for_function('document.querySelector("#branch-title").dataset.node==="T00"')
 page.add_style_tag(content='*{line-height:1.5!important;letter-spacing:.12em!important;word-spacing:.16em!important}p{margin-bottom:2em!important}')
 page.locator('#expand').click();v=overflow(page);check('text_spacing_document_width',v['scroll']<=v['viewport'],v)
 # Browser layout at an effective 200% viewport is a reflow probe, not real browser zoom.
 page.set_viewport_size({'width':720,'height':500});v=overflow(page);check('narrow_reflow_probe',v['scroll']<=v['viewport'],v)
 page.emulate_media(reduced_motion='reduce');check('reduced_motion_preference',page.evaluate('matchMedia("(prefers-reduced-motion: reduce)").matches'))
 check('no_errors_after_interactions',not errors,errors);b.close()
report={'browser':'Chromium /usr/bin/chromium','render_mode':'set_content from provided HTML; file URL navigation blocked by administrator; policy unchanged','scope':'Local render and interaction. Not Safari/iOS or assistive-technology certification.','passed':sum(x['pass_'] for x in results),'failed':sum(not x['pass_'] for x in results),'checks':results}
(E/'browser-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2));sys.exit(bool(report['failed']))
