'use strict';

// End-to-end: the real board, in a real browser, against the real Python
// collector. Covers the two browser-facing repairs:
// - P1-01: a poisoned outbox event must not block later valid events; valid
//   events are counted exactly once and the poison is never accepted.
// - P1-04: the board served from a loopback origin may write to the local
//   collector under the default cross-origin policy.
// Run after `python3 -B tools/build.py --output-dir .preview`.

const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const { randomUUID } = require('node:crypto');
const { mkdtempSync, readFileSync } = require('node:fs');
const { tmpdir } = require('node:os');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');
const telemetry = require('../board/src/telemetria/telemetria.js');

const root = path.join(__dirname, '..');
const board = process.argv[2] ||
  path.join(root, '.preview/design-router-pizarra-v1.4-offline.html');

function startCollector() {
  return new Promise((resolve, reject) => {
    const directory = mkdtempSync(path.join(tmpdir(), 'telemetry-collector-'));
    const child = spawn('python3', ['-B', '-m', 'telemetry.collector',
      '--db', path.join(directory, 'db.sqlite3'), '--host', '127.0.0.1', '--port', '0'],
      { cwd: root });
    let stderr = '';
    const timer = setTimeout(() => reject(new Error('collector did not start')), 15000);
    child.stderr.on('data', chunk => {
      stderr += chunk;
      const match = stderr.match(/http:\/\/127\.0\.0\.1:(\d+)\//);
      if (match) {
        clearTimeout(timer);
        resolve({ child, origin: `http://127.0.0.1:${match[1]}` });
      }
    });
    child.on('exit', code => reject(new Error(`collector exited early: ${code}`)));
  });
}

function serveBoard(html) {
  return new Promise(resolve => {
    const server = http.createServer((_request, response) => {
      response.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      response.end(html);
    });
    server.listen(0, '127.0.0.1', () => resolve({
      server,
      origin: `http://127.0.0.1:${server.address().port}`
    }));
  });
}

async function checkQuotaRecovery(browser, boardOrigin, collectorOrigin) {
  const context = await browser.newContext();
  const counts = async () => (await (await fetch(collectorOrigin + '/v1/metrics?window=all')).json()).event_counts;
  try {
    const before = await counts();
    const writer = await context.newPage();
    const reader = await context.newPage();
    for (const page of [writer, reader]) {
      await page.goto(boardOrigin);
      await page.evaluate(endpoint => {
        window.client = DesignRouterTelemetry.createClient({ endpoint });
      }, collectorOrigin);
    }
    const now = Date.now();
    await writer.clock.install({ time: new Date(now) });
    await writer.clock.pauseAt(new Date(now + 1000));
    await writer.evaluate(endpoint => {
      // Leave room for the smaller selection record. A peer may flush before
      // the producer gets another chance to persist its larger invocation.
      const selection = { selectedFunctions: ['type-choice'], support: { read: [{ skill: { id: 's' } }] } };
      const scope = { route: 'tipografia', scope: 'function' };
      const probe = DesignRouterTelemetry.createClient({ endpoint, storage: sessionStorage });
      probe.schedule = () => {};
      const [invocation, child] = probe.trackEvaluation(selection, scope);
      const size = event => {
        const key = Object.keys(sessionStorage).find(key => key.endsWith(event.event_id));
        return key.length + sessionStorage.getItem(key).length;
      };
      const childSize = size(child);
      if (childSize >= size(invocation)) throw new Error('fixture requires a smaller selection');
      localStorage.setItem('sync', '0');
      let low = 0, high = 8 * 1024 * 1024;
      while (high - low > 1) {
        const length = Math.floor((low + high) / 2);
        try {
          localStorage.setItem('filler', 'x'.repeat(length));
          low = length;
        } catch (error) {
          if (error.name !== 'QuotaExceededError') throw error;
          high = length;
        }
      }
      localStorage.setItem('filler', 'x'.repeat(low - childSize));
      window.client.trackEvaluation(selection, scope);
      localStorage.setItem('sync', '1');
    }, collectorOrigin);
    await reader.waitForFunction(() => localStorage.getItem('sync') === '1');
    await reader.evaluate(() => window.client.flush());
    await writer.evaluate(() => localStorage.removeItem('filler'));
    assert.equal(await writer.evaluate(() => window.client.flush()), true);
    const after = await counts();
    for (const name of ['router.invoked', 'skill.selected']) {
      assert.equal(after[name], (before[name] || 0) + 1, name + ' must reach SQLite exactly once');
    }
  } finally {
    await context.close();
  }
}

async function checkDashboardRange(browser, origin) {
  const post = await fetch(origin + '/v1/events', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ schema: telemetry.SCHEMA, events: [{
      name: 'router.invoked', command: 'status', source: 'cli',
      event_id: randomUUID(), evaluation_id: randomUUID(), instance_id: randomUUID(),
      occurred_at: new Date(Date.now() - 15 * 86400000).toISOString(),
      tree_version: '0.4', router_version: '1.4.0'
    }] })
  });
  assert.equal(post.status, 202);
  const url = origin + '/v1/metrics?window=';
  const week = await (await fetch(url + '7d')).json();
  const all = await (await fetch(url + 'all')).json();
  assert.equal(all.totals.invocations, week.totals.invocations + 1);

  for (const status of [200, 503]) {
    const page = await browser.newPage();
    let release;
    const resume = new Promise(resolve => { release = resolve; });
    try {
      await page.route(url + 'all', async route => {
        await resume;
        await route.fulfill({ status, json: all });
      });
      await Promise.all([page.waitForRequest(url + 'all'), page.goto(origin, { waitUntil: 'domcontentloaded' })]);
      await page.locator('[data-window="7d"]').click();
      await page.waitForFunction(count => document.querySelector('#k-invocations').textContent === String(count),
        week.totals.invocations);
      const bounds = await page.locator('#bounds').innerText();
      const response = page.waitForResponse(url + 'all');
      release();
      await (await response).finished();
      await page.evaluate(() => new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done))));
      assert.equal(await page.locator('[data-window="7d"]').getAttribute('aria-pressed'), 'true');
      assert.equal(await page.locator('#k-invocations').innerText(), String(week.totals.invocations));
      assert.equal(await page.locator('#bounds').innerText(), bounds);
      assert.equal(await page.locator('#status').getAttribute('data-kind'), 'info');
    } finally {
      release();
      await page.close();
    }
  }
}

(async () => {
  assert.ok(board, 'board HTML is required');
  const html = readFileSync(board, 'utf8');
  const collector = await startCollector();
  const fixture = await serveBoard(html);
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const keys = telemetry.keys.forEndpoint(collector.origin);
    await page.addInitScript(({ outbox, collectorOrigin }) => {
      window.DESIGN_ROUTER_TELEMETRY = { endpoint: collectorOrigin, routerVersion: '1.3.0' };
      // P1-01: a poisoned event already sitting in the outbox.
      const poisoned = {
        event_id: 'poison-poison-poison-poison-poisonpoisonpoison',
        name: 'router.invoked',
        occurred_at: new Date().toISOString(),
        source: 'board',
        instance_id: '22222222-2222-4222-8222-222222222222',
        router_version: '1.3.0',
        tree_version: '0.4',
        evaluation_id: 'not-a-valid-evaluation-id',
        command: 'board'
      };
      window.localStorage.setItem(outbox, JSON.stringify([poisoned]));
    }, { outbox: keys.outbox, collectorOrigin: collector.origin });
    await page.goto(fixture.origin + '/', { waitUntil: 'load' });
    await page.waitForSelector('#capRouteButtons [data-route]');
    await page.waitForTimeout(400);

    const before = JSON.parse(await (await fetch(collector.origin + '/v1/metrics?window=all')).text());
    const initialEvents = before.totals.events;
    const initialInvocations = before.totals.invocations;

    await page.click('#capRouteButtons [data-route="auditoria"]');
    await page.waitForTimeout(500);

    const metrics = JSON.parse(await (await fetch(collector.origin + '/v1/metrics?window=all')).text());
    assert.ok(metrics.totals.events > initialEvents,
      'valid board events must reach the real collector despite the poison');
    assert.ok(metrics.totals.invocations >= initialInvocations + 1,
      'a route click must record an invocation');
    assert.ok(metrics.totals.evaluations >= 1, 'board evaluations must be counted');

    // No event may be counted twice; the poison must never be accepted.
    const events = JSON.parse(await (await fetch(collector.origin + '/v1/metrics?window=all&limit=100')).text());
    const byName = events.event_counts;
    assert.equal(Object.values(byName).reduce((a, b) => a + b, 0), metrics.totals.events,
      'one response, one snapshot');
    assert.equal(metrics.observability['router.invoked'], 'observed');
    assert.equal(metrics.observability['skill.execution_started'], 'schema_supported_no_emitter',
      'no host is integrated, so execution stays explicitly unobservable');

    const queue = await page.evaluate(key => window.localStorage.getItem(key), keys.outbox);
    const pending = JSON.parse(queue || '[]');
    assert.equal(pending.length, 0, 'the poisoned event must not wedge the queue');
    const rejected = JSON.parse(
      await page.evaluate(key => window.localStorage.getItem(key), keys.rejected) || '[]');
    assert.ok(rejected.some(event => event.evaluation_id === 'not-a-valid-evaluation-id'),
      'the poison is kept isolated for inspection, not silently lost');

    // Dashboard rendered by the real collector from system-generated data.
    await page.goto(collector.origin + '/', { waitUntil: 'load' });
    await page.waitForTimeout(400);
    const invocations = Number(await page.locator('#k-invocations').innerText());
    assert.ok(invocations >= 2, 'the dashboard must show real invocations');
    assert.match(await page.locator('#skills-executed').innerText(), /No observable/,
      'with no host ever integrated, the dashboard must say so');
    assert.match(await page.locator('#observability').innerText(), /schema_supported_no_emitter/);
    const statusText = await page.locator('#status').innerText();
    assert.match(statusText, /Datos reales: \d+ eventos aceptados/);

    await page.close();
    await checkDashboardRange(browser, collector.origin);
    await checkQuotaRecovery(browser, fixture.origin, collector.origin);
    console.log('PASS colector real: eventos válidos contados una vez, veneno aislado, política de origen aplicada');
  } finally {
    await browser.close();
    fixture.server.closeAllConnections();
    fixture.server.close();
    collector.child.kill('SIGTERM');
  }
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
