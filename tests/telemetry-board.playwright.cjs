'use strict';

// Browser-level check: the real board resolves a selection, the telemetry
// client posts only observable events, and disabling the endpoint stops all
// traffic. Run after `python3 -B tools/build.py --output-dir .preview`.

const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');

const file = process.argv[2] || path.join(__dirname, '../.preview/design-router-pizarra-v1.4-offline.html');

function receipt(payload) {
  return { schema: 'design-router-telemetry/1', accepted: payload.events.length, duplicates: 0 };
}

function serve(html) {
  const events = [];
  const server = http.createServer((request, response) => {
    if (request.method === 'OPTIONS') {
      response.writeHead(204, {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'content-type, authorization',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
      });
      response.end();
      return;
    }
    if (request.method === 'GET' && request.url.split('?')[0] === '/board.html') {
      response.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      response.end(html);
      return;
    }
    if (request.method === 'POST' && request.url === '/v1/events') {
      let body = '';
      request.setEncoding('utf8');
      request.on('data', chunk => { body += chunk; });
      request.on('end', () => {
        try {
          const payload = JSON.parse(body);
          events.push(...(payload.events || []));
          response.writeHead(202, { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' });
          response.end(JSON.stringify(receipt(payload)));
        } catch (_) {
          response.writeHead(400, { 'Content-Type': 'application/json' });
          response.end('{"error":"INVALID_JSON"}');
        }
      });
      return;
    }
    response.writeHead(404);
    response.end();
  });
  return new Promise(resolve => {
    server.listen(0, '127.0.0.1', () => resolve({
      server,
      events,
      origin: `http://127.0.0.1:${server.address().port}`
    }));
  });
}

async function checkCollectorSwitch(browser, origin) {
  const page = await browser.newPage();
  const board = origin + '/board.html';
  const collectorA = origin + '/tenant-a';
  const collectorB = origin + '/tenant-b';
  const sentToA = [];
  const sentToB = [];
  let offline = true;
  try {
    await page.route(collectorA + '/v1/events', async route => {
      sentToA.push(...route.request().postDataJSON().events.map(event => event.event_id));
      await route.fulfill(offline ? { status: 503 } : { status: 202, json: receipt(route.request().postDataJSON()) });
    });
    await page.route(collectorB + '/v1/events', async route => {
      sentToB.push(...route.request().postDataJSON().events.map(event => event.event_id));
      await route.fulfill({ status: 202, json: receipt(route.request().postDataJSON()) });
    });
    await page.addInitScript(endpoint => {
      if (location.search === '?inline') window.DESIGN_ROUTER_TELEMETRY = { endpoint };
    }, collectorB);
    await page.goto(board);
    await page.evaluate(endpoint => window.DesignRouterTelemetry.configure(endpoint), collectorA);

    const loadAndWait = (url, endpoint) => Promise.all([
      page.waitForResponse(endpoint + '/v1/events'),
      page.goto(url)
    ]);
    const [failed] = await loadAndWait(board, collectorA);
    assert.equal(failed.status(), 503);
    const pending = new Set(sentToA);
    assert.ok(pending.size > 0);

    const [switched] = await loadAndWait(board + '?inline', collectorB);
    assert.equal(switched.status(), 202);
    assert.ok(sentToB.length > 0);
    assert.ok(sentToB.every(id => !pending.has(id)), 'the inline collector received an A event');

    offline = false;
    sentToA.length = 0;
    const [recovered] = await loadAndWait(board, collectorA);
    assert.equal(recovered.status(), 202);
    assert.deepEqual(sentToA.filter(id => pending.has(id)).sort(), [...pending].sort(),
      'each pending event returns to its original collector exactly once');
    assert.ok(sentToA.every(id => !sentToB.includes(id)), 'A received a B event');
  } finally {
    await page.close();
  }
}

async function checkSharedOptOut(browser, fixture) {
  const context = await browser.newContext();
  try {
    const settings = await context.newPage();
    const board = fixture.origin + '/board.html';
    await settings.goto(board);
    await settings.evaluate(url => window.DesignRouterTelemetry.configure(url), fixture.origin);
    const otherTab = await context.newPage();
    const isPost = response => response.request().method() === 'POST' &&
      response.url() === fixture.origin + '/v1/events' && response.status() === 202;
    await Promise.all([otherTab.waitForResponse(isPost), otherTab.goto(board)]);
    await Promise.all([otherTab.waitForResponse(isPost), otherTab.click('#capRouteButtons [data-route="auditoria"]')]);
    // A completed HTTP response does not imply the client has retired its
    // outbox entries. Verify the queue is drained before revocation.
    await otherTab.waitForFunction(endpoint => {
      const keys = DesignRouterTelemetry.keys.forEndpoint(endpoint);
      return !Object.keys(localStorage).some(key => key.startsWith(keys.entryPrefix));
    }, fixture.origin);
    const outbox = async () => otherTab.evaluate(endpoint => {
      const keys = DesignRouterTelemetry.keys.forEndpoint(endpoint);
      return Object.keys(localStorage).filter(key => key.startsWith(keys.entryPrefix)).sort();
    }, fixture.origin);
    const before = await outbox();
    const posts = [];
    otherTab.on('request', req => {
      if (req.method() === 'POST') posts.push(req.url());
    });
    await settings.evaluate(() => window.DesignRouterTelemetry.configure(null));
    await otherTab.click('#capRouteButtons [data-route="color"]');
    await otherTab.evaluate(() => window.dispatchEvent(new Event('online')));
    await otherTab.waitForTimeout(400);
    assert.deepEqual(posts, [], 'an already-open tab must respect revocation on its next click and flush');
    assert.deepEqual(await outbox(), before, 'an opted-out tab must not enqueue new events');
  } finally {
    await context.close();
  }
}

(async () => {
  const html = readFileSync(file, 'utf8');
  const fixture = await serve(html);
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    await page.addInitScript(origin => {
      window.DESIGN_ROUTER_TELEMETRY = { endpoint: origin, routerVersion: '1.3.0' };
    }, fixture.origin);
    await page.goto(fixture.origin + '/board.html', { waitUntil: 'load' });
    await page.waitForSelector('#capRouteButtons [data-route]');
    await page.waitForTimeout(300);

    const initial = fixture.events.length;
    assert.ok(initial > 0, 'the initial evaluation must be counted');
    assert.ok(fixture.events.some(event => event.name === 'router.invoked'));

    await page.click('#capRouteButtons [data-route="auditoria"]');
    await page.waitForTimeout(300);
    const functions = page.locator('#capFunctionList [data-cap]');
    if (await functions.count()) {
      await functions.first().click();
      await page.waitForTimeout(300);
    }
    await page.selectOption('#minScope', 'scenario').catch(() => {});
    await page.waitForTimeout(500);

    assert.ok(fixture.events.length > initial, 'user actions must add events');
    assert.ok(fixture.events.every(event => event.name !== 'decision.node_visited'));
    assert.ok(fixture.events.some(event => event.name === 'skill.selected'));
    assert.ok(fixture.events.every(event => !event.name.startsWith('skill.execution')));
    assert.ok(fixture.events.every(event => !('prompt' in event) && !('message' in event)));
    assert.ok(fixture.events.every(event => event.source === 'board'));
    assert.ok(fixture.events.every(event => /^[0-9a-f-]{36}$/.test(event.event_id)));

    const disabled = await browser.newPage({ viewport: { width: 1200, height: 900 } });
    const before = fixture.events.length;
    await disabled.goto(fixture.origin + '/board.html', { waitUntil: 'load' });
    await disabled.waitForSelector('#capRouteButtons [data-route]');
    await disabled.click('#capRouteButtons [data-route="color"]');
    await disabled.waitForTimeout(400);
    assert.equal(fixture.events.length, before, 'without an endpoint the board must stay silent');
    await disabled.close();

    await page.close();
    await checkCollectorSwitch(browser, fixture.origin);
    await checkSharedOptOut(browser, fixture);
    console.log(`PASS tablero: ${fixture.events.length} eventos observados, sin ejecuciones inventadas`);
  } finally {
    await browser.close();
    fixture.server.close();
  }
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
