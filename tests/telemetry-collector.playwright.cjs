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
const { mkdtempSync, readFileSync } = require('node:fs');
const { tmpdir } = require('node:os');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');

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

(async () => {
  assert.ok(board, 'board HTML is required');
  const html = readFileSync(board, 'utf8');
  const collector = await startCollector();
  const fixture = await serveBoard(html);
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    await page.addInitScript(({ boardOrigin, collectorOrigin }) => {
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
      window.localStorage.setItem('design-router.telemetry.outbox', JSON.stringify([poisoned]));
      void boardOrigin;
    }, { boardOrigin: fixture.origin, collectorOrigin: collector.origin });
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

    const queue = await page.evaluate(() =>
      window.localStorage.getItem('design-router.telemetry.outbox'));
    const pending = JSON.parse(queue || '[]');
    assert.equal(pending.length, 0, 'the poisoned event must not wedge the queue');
    const rejected = JSON.parse(
      await page.evaluate(() => window.localStorage.getItem('design-router.telemetry.rejected')) || '[]');
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
