'use strict';

// Dashboard contract: real numbers render, zero data is stated as zero, and
// missing execution emitters are shown as unobservable rather than invented.

const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');

const html = readFileSync(path.join(__dirname, '../telemetry/dashboard.html'));

const base = {
  schema: 'design-router-telemetry-metrics/1',
  generated_at: '2026-11-18T10:00:00.000Z',
  window: { since: null, until: null },
  totals: {
    invocations: 12, evaluations: 9, events: 30, nodes_visited: 7,
    branches_selected: 2, skills_selected: 11, executions_started: 2,
    executions_completed: 1, executions_failed: 1
  },
  skills: [
    { skill_id: 'skill/alpha', selected: 6, executions_started: 1, executions_completed: 1, executions_failed: 0 },
    { skill_id: 'skill/beta', selected: 5, executions_started: 1, executions_completed: 0, executions_failed: 1 }
  ],
  skills_executed: [
    { skill_id: 'skill/gamma', selected: 0, executions_started: 1, executions_completed: 1, executions_failed: 0 },
    { skill_id: 'skill/alpha', selected: 6, executions_started: 1, executions_completed: 1, executions_failed: 0 },
    { skill_id: 'skill/beta', selected: 5, executions_started: 1, executions_completed: 0, executions_failed: 1 }
  ],
  nodes: [{ node_id: 'Q00', visits: 5 }],
  branches: [{ node_id: 'Q00', branch_id: 'F00', selected: 2 }],
  routes: [{ route: 'auditoria', evaluations: 9 }],
  sources: [{ source: 'board', events: 20 }, { source: 'cli', events: 10 }],
  event_counts: { 'router.invoked': 12, 'skill.selected': 11 },
  daily: [{ date: '2026-11-18', invocations: 12, evaluations: 9, selections: 11, nodes: 7, started: 2, completed: 1, failed: 1 }],
  observability: {
    'router.invoked': 'observed', 'decision.node_visited': 'observed',
    'decision.branch_selected': 'observed', 'skill.selected': 'observed',
    'skill.execution_started': 'observed', 'skill.execution_completed': 'observed',
    'skill.execution_failed': 'observed'
  },
  data_quality: {
    source_of_truth: 'accepted_events', sampling: false, exact_event_counts: true,
    instances: 3, max_events_per_instance: 6, possibly_inflated: false,
    execution_counts_note: ''
  },
  bounds: { first_event_at: '2026-11-17T00:00:00Z', last_event_at: '2026-11-18T10:00:00Z', first_received_at: '2026-11-17T00:05:00Z', last_received_at: '2026-11-18T10:05:00Z' }
};

const empty = {
  ...base,
  totals: {
    invocations: 0, evaluations: 0, events: 0, nodes_visited: 0, branches_selected: 0,
    skills_selected: 0, executions_started: 0, executions_completed: 0, executions_failed: 0
  },
  skills: [], skills_executed: [], nodes: [], branches: [], routes: [], sources: [], event_counts: {}, daily: [],
  observability: {
    'router.invoked': 'observed_zero_events', 'decision.node_visited': 'observed_zero_events',
    'decision.branch_selected': 'observed_zero_events', 'skill.selected': 'observed_zero_events',
    'skill.execution_started': 'schema_supported_no_emitter',
    'skill.execution_completed': 'schema_supported_no_emitter',
    'skill.execution_failed': 'schema_supported_no_emitter'
  }
};

function serve(payload, status = 200) {
  return new Promise(resolve => {
    const server = http.createServer((request, response) => {
      if (request.url.startsWith('/v1/metrics')) {
        response.writeHead(status, { 'Content-Type': 'application/json' });
        response.end(status === 200 ? JSON.stringify(payload) : '{"error":"INTERNAL_ERROR"}');
        return;
      }
      response.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      response.end(html);
    });
    server.listen(0, '127.0.0.1', () => resolve({
      server, origin: `http://127.0.0.1:${server.address().port}`
    }));
  });
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  // Every fixture server is registered here so a failed assertion can never
  // leave one listening (which would hang the process on exit).
  const fixtures = [];
  const serve$ = async (payload, status) => {
    const fixture = await serve(payload, status);
    fixtures.push(fixture);
    return fixture;
  };
  try {
    const live = await serve$(base);
    const page = await browser.newPage({ viewport: { width: 1280, height: 1200 } });
    const errors = [];
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(live.origin + '/', { waitUntil: 'load' });
    await page.waitForTimeout(300);
    assert.equal(await page.locator('#k-invocations').innerText(), '12');
    assert.equal(await page.locator('#k-evals').innerText(), '9');
    assert.match(await page.locator('#skills-selected').innerText(), /skill\/alpha/);
    assert.match(await page.locator('#skills-executed').innerText(), /COMPLETADAS/i);
    assert.match(await page.locator('#skills-executed').innerText(), /skill\/gamma/,
      'the executed ranking must include skills never selected');
    assert.match(await page.locator('#bounds').innerText(), /Posible inflado por concentración: no/);
    assert.match(await page.locator('#bounds').innerText(),
      /Entrega al colector: 2026-11-17T00:05:00Z → 2026-11-18T10:05:00Z/,
      'the delivery bounds must be visible to the operator');
    assert.match(await page.locator('#daily').innerText(), /fecha \(utc\)/i,
      'the daily aggregation must be labeled as UTC');
    assert.match(await page.locator('#observability').innerText(), /Invocación exitosa registrada/);
    assert.match(await page.locator('#bounds').innerText(), /skill\.selected/);
    assert.deepEqual(errors, []);
    await page.close();
    live.server.closeAllConnections();
    live.server.close();

    const zero = await serve$(empty);
    const emptyPage = await browser.newPage({ viewport: { width: 1280, height: 1000 } });
    await emptyPage.goto(zero.origin + '/', { waitUntil: 'load' });
    await emptyPage.waitForTimeout(300);
    assert.match(await emptyPage.locator('#status').innerText(), /Sin datos reales/);
    assert.match(await emptyPage.locator('#skills-executed').innerText(), /No observable/);
    assert.match(await emptyPage.locator('#observability').innerText(), /schema_supported_no_emitter/);
    await emptyPage.close();
    zero.server.closeAllConnections();
    zero.server.close();

    const observedZero = {
      ...empty,
      observability: {
        ...empty.observability,
        'skill.execution_started': 'observed_zero_events',
        'skill.execution_completed': 'observed_zero_events',
        'skill.execution_failed': 'observed_zero_events'
      }
    };
    const observed = await serve$(observedZero);
    const observedPage = await browser.newPage({ viewport: { width: 1280, height: 1000 } });
    await observedPage.goto(observed.origin + '/', { waitUntil: 'load' });
    await observedPage.waitForTimeout(300);
    assert.match(await observedPage.locator('#skills-executed').innerText(), /Sin ejecuciones registradas/);
    await observedPage.close();
    observed.server.closeAllConnections();
    observed.server.close();

    const inflated = await serve$({
      ...base,
      data_quality: { ...base.data_quality, max_events_per_instance: 6420, possibly_inflated: true }
    });
    const inflatedPage = await browser.newPage({ viewport: { width: 1280, height: 1000 } });
    await inflatedPage.goto(inflated.origin + '/', { waitUntil: 'load' });
    await inflatedPage.waitForTimeout(300);
    assert.match(await inflatedPage.locator('#bounds').innerText(), /Posible inflado por concentración: sí/);
    assert.match(await inflatedPage.locator('#bounds').innerText(), /6420/);
    await inflatedPage.close();
    inflated.server.closeAllConnections();
    inflated.server.close();

    const broken = await serve$(null, 500);
    const brokenPage = await browser.newPage({ viewport: { width: 1280, height: 1000 } });
    await brokenPage.goto(broken.origin + '/', { waitUntil: 'load' });
    await brokenPage.waitForTimeout(300);
    assert.match(await brokenPage.locator('#status').innerText(), /No se pudo consultar/);
    await brokenPage.close();
    broken.server.closeAllConnections();
    broken.server.close();
    console.log('PASS dashboard: datos reales, cero, cero observado, no observable y error de consulta');
  } finally {
    await browser.close();
    for (const fixture of fixtures) {
      fixture.server.closeAllConnections();
      fixture.server.close();
    }
  }
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
