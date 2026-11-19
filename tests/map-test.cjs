'use strict';

const assert = require('node:assert/strict');
const { access } = require('node:fs/promises');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

const input = process.argv[2];
const root = 'Q00';
const foundations = 'F00';
const displayNode = 'py-runner-show-node';
const runnerFile = 'file-skills-design-tree-scripts-runner-py';
const localFile = input ? pathToFileURL(path.resolve(input)).href : '';
const headingId = id => `router-node-${id}`;
const indexNode = (page, id) =>
  page.locator(`#routerNodeIndex a[data-router-target="${id}"]`);
const relation = (page, id) =>
  page.locator(`#routerNodeDetail a[data-router-target="${id}"]`).first();

async function shown(page, id) {
  await page.locator(`#routerNodeDetail > h3[id="${headingId(id)}"]`).waitFor({ state: 'visible' });
}

async function openMap(page) {
  await page.locator('#routerNodeView').click();
  await shown(page, root);
  assert.equal(await page.locator('#routerNodeView').getAttribute('aria-pressed'), 'true');
}

async function followRelation(page, id) {
  const link = relation(page, id);
  if (!(await link.isVisible())) {
    const summary = link.locator('xpath=ancestor::details[1]/summary');
    if (await summary.isVisible()) await summary.click();
  }
  await link.click();
  await shown(page, id);
  assert.equal(new URL(page.url()).hash, `#${headingId(id)}`);
}

async function selectFiles(page) {
  const groups = page.locator('#routerNodeGroup');
  await groups.selectOption({ label: 'Archivos del plugin' });
  assert.equal(await groups.inputValue(), 'Archivos del plugin');
}

async function checkViewport(page, width) {
  const measures = await page.evaluate(() => {
    const selectors = {
      document: document.documentElement,
      panel: document.querySelector('#routerNodePanel'),
      detail: document.querySelector('#routerNodeDetail'),
      filters: document.querySelector('.router-node-filter')
    };
    return Object.fromEntries(Object.entries(selectors).map(([key, node]) =>
      [key, { client: node.clientWidth, scroll: node.scrollWidth }]));
  });
  for (const [key, { client, scroll }] of Object.entries(measures)) {
    assert.ok(client > 0 && client <= width, `${width}px ${key}: clientWidth ${client}`);
    assert.ok(scroll <= client + 1, `${width}px ${key}: scrollWidth ${scroll} > ${client}`);
  }
}

const tests = {
  '1. Tablero → Q00 → ficha de código Python real': async page => {
    await openMap(page);
    const detail = page.locator('#routerNodeDetail');
    assert.match(await detail.locator('h3').textContent(), /punto de partida/i);
    assert.equal(await detail.getByRole('heading', { name: 'Consultado desde código Python' }).isVisible(), true);
    await followRelation(page, displayNode);
    await detail.getByText('Ver fuente', { exact: true }).click();
    assert.match(await detail.locator('pre').innerText(), /def packet\(self,state,node_id\):/);
  },
  '2. Q00 → F00 → atrás → adelante, con URL y selección': async page => {
    await openMap(page);
    await followRelation(page, foundations);
    assert.match(await page.locator('#routerNodeDetail h3').innerText(), /fundaciones/i);
    assert.equal(await indexNode(page, foundations).getAttribute('aria-current'), 'location');
    await page.goBack();
    await shown(page, root);
    assert.equal(new URL(page.url()).hash, '');
    assert.equal(await indexNode(page, root).getAttribute('aria-current'), 'location');
    await page.goForward();
    await shown(page, foundations);
    assert.equal(new URL(page.url()).hash, '#router-node-F00');
    assert.equal(await indexNode(page, foundations).getAttribute('aria-current'), 'location');
  },
  '3. Búsqueda por alias E03__F00 y filtro Archivos': async page => {
    await openMap(page);
    const search = page.locator('#routerNodeSearch');
    await search.fill('E03__F00');
    assert.equal(await indexNode(page, foundations).isVisible(), true);
    await indexNode(page, foundations).click();
    await shown(page, foundations);
    await selectFiles(page);
    assert.equal(await page.locator('#routerNodeIndex a').count(), 0);
    assert.match(await page.locator('#routerNodeCount').innerText(), /sin nodos/i);
    await search.fill('runner.py');
    assert.equal(await indexNode(page, runnerFile).isVisible(), true);
    assert.equal(await page.locator('#routerNodeIndex a').count(), 1);
  },
  '4. Ficha runner.py y símbolo con línea y fuente': async page => {
    await openMap(page);
    await selectFiles(page);
    await page.locator('#routerNodeSearch').fill('runner.py');
    await indexNode(page, runnerFile).click();
    await shown(page, runnerFile);
    const detail = page.locator('#routerNodeDetail');
    assert.equal(await detail.locator('h3').innerText(), 'runner.py');
    assert.match(await detail.locator('dl').innerText(), /skills\/design-tree\/scripts\/runner\.py/);
    await detail.getByText('Ver fuente', { exact: true }).click();
    assert.match(await detail.locator('pre').innerText(), /\b[0-9a-f]{64}\b/);
    await followRelation(page, displayNode);
    const fields = await detail.locator('dl').innerText();
    assert.match(fields, /skills\/design-tree\/scripts\/runner\.py:[1-9]\d*/);
    assert.match(fields, /Router\.packet/);
    await detail.getByText('Ver fuente', { exact: true }).click();
    assert.match(await detail.locator('pre').innerText(), /def packet\(self,state,node_id\):/);
  },
  '5. Apertura directa desde file:/// con enlace profundo': async page => {
    await page.goto(`${localFile}#${headingId(displayNode)}`);
    await shown(page, displayNode);
    assert.equal(new URL(page.url()).protocol, 'file:');
    assert.equal(new URL(page.url()).hash, '#router-node-py-runner-show-node');
    assert.equal(await page.locator('#routerNodeView').getAttribute('aria-pressed'), 'true');
    assert.equal(await indexNode(page, displayNode).getAttribute('aria-current'), 'location');
  },
  '6. Salir de la vista y volver a usar el simulador': async page => {
    await openMap(page);
    await followRelation(page, foundations);
    await page.locator('#capabilityMapView').click();
    assert.equal(await page.locator('#routerNodePanel').isVisible(), false);
    assert.equal(await page.locator('#routerNodeView').getAttribute('aria-pressed'), 'false');
    assert.equal(await page.locator('#capabilityPanel').isVisible(), true);
    assert.equal(new URL(page.url()).hash, '');
    await page.locator('#capabilityPanel [data-route="auditoria"]').click();
    await page.locator('#minScope').selectOption('function');
    await page.locator('#minDomain').selectOption('G2');
    assert.deepEqual(await page.evaluate(() => window.__minimalRouterPreview.getState().owners), ['G2']);
    await page.locator('#routerNodeView').click();
    await shown(page, foundations);
  },
  '7. Controles alcanzables y sin overflow a 390 y 320 CSS px': async page => {
    for (const width of [390, 320]) {
      await page.setViewportSize({ width, height: 844 });
      await page.goto(localFile);
      await openMap(page);
      const sidebarToggle = page.locator('#stageNavigationToggle');
      if (await sidebarToggle.count() && await sidebarToggle.getAttribute('aria-expanded') === 'false') {
        await sidebarToggle.press('Enter');
      }
      await checkViewport(page, width);
      await selectFiles(page);
      await page.locator('#routerNodeSearch').fill('runner.py');
      await indexNode(page, runnerFile).click();
      await shown(page, runnerFile);
      await followRelation(page, displayNode);
      await page.locator('#routerNodeDetail').getByText('Ver fuente', { exact: true }).click();
      assert.equal(await page.locator('#routerNodeDetail pre').isVisible(), true);
      await checkViewport(page, width);
      await page.locator('#capabilityMapView').click();
      assert.equal(await page.locator('#capabilityPanel').isVisible(), true);
    }
  }
};

(async () => {
  if (!input) throw new Error('Uso: node map-test.cjs RUTA_HTML');
  await access(input);
  const browser = await chromium.launch({
    executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
    headless: true
  });
  let failed = 0;
  try {
    for (const [label, test] of Object.entries(tests)) {
      const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      page.setDefaultTimeout(7000);
      await page.route(/^https?:\/\//, route => route.abort());
      try {
        await page.goto(localFile);
        await test(page);
        assert.deepEqual(errors, []);
        console.log(`PASS ${label}`);
      } catch (error) {
        failed++;
        console.error(`FAIL ${label}\n${error.stack}\nURL ${page.url()}\nErrores JS ${JSON.stringify(errors)}`);
      } finally {
        await page.close();
      }
    }
  } finally {
    await browser.close();
  }
  console.log(`${Object.keys(tests).length - failed}/${Object.keys(tests).length} casos aprobados`);
  process.exitCode = failed ? 1 : 0;
})().catch(error => {
  console.error(`Suite no iniciada: ${error.message}`);
  process.exitCode = 2;
});
