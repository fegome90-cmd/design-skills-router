'use strict';

const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const { test } = require('node:test');
const telemetry = require('../board/src/telemetria/telemetria.js');
const localKeys = telemetry.keys.forEndpoint('http://127.0.0.1:8787');

const selection = {
  selectedFunctions: ['visual-qa'],
  nodesByFunction: { 'visual-qa': ['QA01', 'QA01'] },
  support: {
    read: [
      { skill: { id: 'X01' }, function_id: 'visual-qa' },
      { skill: { id: 'X01' }, function_id: 'visual-qa' }
    ],
    write: [{ skill: { id: 'G2' }, function_id: 'visual-qa' }]
  }
};

const memoryStorage = () => {
  const values = new Map();
  return {
    getItem: key => (values.has(key) ? values.get(key) : null),
    setItem: (key, value) => values.set(key, String(value)),
    values
  };
};

const context = () => ({
  evaluationId: '11111111-1111-4111-8111-111111111111',
  instanceId: '22222222-2222-4222-8222-222222222222',
  route: 'auditoria',
  scope: 'function',
  occurredAt: '2026-11-18T10:00:00.000Z',
  newId: (() => {
    let index = 0;
    return () => `33333333-3333-4333-8333-${String(index++).padStart(12, '0')}`;
  })()
});

test('evaluation events contain only observable board selections', () => {
  const events = telemetry.buildEvaluationEvents(selection, context());
  assert.equal(events.filter(event => event.name === 'router.invoked').length, 1);
  assert.equal(events.filter(event => event.name === 'decision.node_visited').length, 0);
  assert.equal(events.filter(event => event.name === 'skill.selected').length, 2);
  assert.deepEqual(
    events.map(event => event.name),
    ['router.invoked', 'skill.selected', 'skill.selected']
  );
  assert.ok(events.every(event => event.source === 'board'));
  assert.ok(events.every(event => event.command === undefined || event.command === 'board'));
  assert.ok(events.every(event => !('prompt' in event) && !('message' in event)));
});

test('the board never emits execution events', () => {
  const events = telemetry.buildEvaluationEvents(selection, context());
  assert.ok(events.every(event => !event.name.startsWith('skill.execution')));
});

test('disabled client does not persist or call fetch', async () => {
  const storage = memoryStorage();
  const client = telemetry.createClient({ storage, fetch: async () => { throw new Error('must not call'); } });
  assert.equal(client.enabled, false);
  assert.deepEqual(client.trackEvaluation(selection, { route: 'auditoria' }), []);
  assert.equal(await client.flush(), true);
  assert.equal(storage.values.size, 0);
  const optedOut = telemetry.createClient({ enabled: false, endpoint: 'https://configured.example', storage });
  assert.deepEqual(optedOut.trackEvaluation(selection, {}), []);
  assert.equal(await optedOut.flush(), true);
  assert.equal(storage.values.size, 0);
});

test('successful delivery sends one idempotent batch and clears the outbox', async () => {
  const storage = memoryStorage();
  const calls = [];
  const client = telemetry.createClient({
    storage,
    endpoint: 'http://127.0.0.1:8787',
    instanceId: context().instanceId,
    fetch: async (url, options) => {
      calls.push({ url, options, body: JSON.parse(options.body) });
      return { ok: true };
    }
  });
  const events = client.trackEvaluation(selection, { route: 'auditoria', scope: 'function' });
  assert.equal(events.length, 3);
  assert.equal(await client.flush(), true);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, 'http://127.0.0.1:8787/v1/events');
  assert.equal(calls[0].body.schema, 'design-router-telemetry/1');
  assert.equal(calls[0].body.events.length, 3);
  assert.equal(storage.getItem(localKeys.outbox), '[]');
});

test('failed delivery keeps events in the bounded outbox', async () => {
  const storage = memoryStorage();
  const client = telemetry.createClient({
    storage,
    endpoint: 'http://127.0.0.1:8787',
    instanceId: context().instanceId,
    fetch: async () => ({ ok: false })
  });
  client.trackEvaluation(selection, { route: 'auditoria' });
  assert.equal(await client.flush(), false);
  const saved = JSON.parse(storage.getItem(localKeys.outbox));
  assert.equal(saved.length, 3);
});

test('a configured token is sent as an authorization header', async () => {
  let headers;
  const client = telemetry.createClient({
    storage: memoryStorage(),
    endpoint: 'https://telemetry.example.com',
    token: 'token-value',
    instanceId: context().instanceId,
    fetch: async (_url, options) => { headers = options.headers; return { ok: true }; }
  });
  client.trackEvaluation(selection, { route: 'auditoria' });
  await client.flush();
  assert.equal(headers.Authorization, 'Bearer token-value');
});

test('init reads the selection through the read-only preview getter', async () => {
  const storage = memoryStorage();
  const handlers = new Map();
  const captures = new Map();
  const document = {
    addEventListener: (name, handler, options) => {
      handlers.set(name, handler);
      captures.set(name, options === true || Boolean(options && options.capture));
    }
  };
  const window = {
    DESIGN_ROUTER_TELEMETRY: {
      endpoint: 'http://127.0.0.1:8787',
      fetch: async () => ({ ok: true })
    },
    __minimalRouterPreview: {
      getState: () => ({ route: 'auditoria', scope: 'function' }),
      getSelection: () => selection
    }
  };
  const client = telemetry.init(window, document, { storage });
  assert.ok(client);
  await new Promise(resolve => setTimeout(resolve, 5));
  assert.equal(await client.flush(), true);
  assert.ok(handlers.has('click'));
  assert.ok(handlers.has('change'));
  // The click listener must observe clicks in capture phase: the board
  // re-renders the route/function lists during the click and detaches the
  // target before a bubble listener on document runs.
  assert.equal(captures.get('click'), true,
    'click delegation must run in capture phase to survive the board re-render');
});

test('a click that detaches its target still records the evaluation', async () => {
  const storage = memoryStorage();
  const listeners = [];
  const document = {
    addEventListener: (name, handler, options) => listeners.push({ name, handler, capture: options === true || Boolean(options && options.capture) }),
    readyState: 'complete'
  };
  const window = {
    DESIGN_ROUTER_TELEMETRY: {
      endpoint: 'http://127.0.0.1:8787',
      fetch: async () => ({ ok: true })
    },
    __minimalRouterPreview: {
      getState: () => ({ route: 'auditoria', scope: 'function' }),
      getSelection: () => selection
    }
  };
  const client = telemetry.init(window, document, { storage });
  assert.ok(client);
  const delivered = [];
  client.trackEvaluation = (sel, ctx) => { delivered.push(ctx); return []; };

  const button = {
    dataset: { route: 'auditoria' },
    closest(selector) {
      // After the board's synchronous re-render the clicked button is
      // detached: ancestor-based selectors can no longer resolve.
      return this.parentElement ? (this.matches(selector) ? this : this.parentElement.closest(selector)) : null;
    },
    matches(selector) { return selector.includes('[data-route]') && this.dataset.route !== undefined; },
    parentElement: null
  };
  const captureListener = listeners.find(l => l.name === 'click' && l.capture);
  assert.ok(captureListener, 'a capture-phase click listener must exist');
  // Simulate the real board: the click re-renders the list and only then the
  // detached target reaches the telemetry listener.
  captureListener.handler({ target: button });
  await new Promise(resolve => setTimeout(resolve, 5));
  assert.equal(delivered.length, 1, 'the evaluation must be recorded despite the detach');
  assert.equal(delivered[0].route, 'auditoria');
});

// A fetch mock that replicates the real collector's transactional validation:
// one invalid event rejects the whole batch with 422 + index; only batches
// whose events are all valid are accepted, and each accepted event is counted
// exactly once.
function transactionalCollector() {
  const accepted = [];
  const calls = [];
  const validEvent = event =>
    Boolean(event && typeof event.event_id === 'string' &&
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(event.event_id) &&
      typeof event.name === 'string' && typeof event.occurred_at === 'string' &&
      typeof event.source === 'string' && typeof event.instance_id === 'string');
  const fetch = async (_url, options) => {
    const body = JSON.parse(options.body);
    calls.push(body.events.map(event => event.event_id));
    for (let index = 0; index < body.events.length; index++) {
      if (!validEvent(body.events[index])) {
        return { ok: false, status: 422, json: async () => ({ error: 'INVALID_EVENT_ID', index }) };
      }
    }
    accepted.push(...body.events);
    return { ok: true, status: 202 };
  };
  return { fetch, accepted, calls };
}

const boardEvent = (id, name, extra = {}) => ({
  event_id: id, name, occurred_at: '2026-11-18T10:00:00.000Z', source: 'board',
  instance_id: '22222222-2222-4222-8222-222222222222',
  router_version: '1.3.0', tree_version: '0.4', ...extra
});

test('a permanently rejected event is isolated and later events are delivered exactly once', async () => {
  const storage = memoryStorage();
  const poisoned = boardEvent('not-a-uuid-at-all', 'router.invoked', { evaluation_id: '11111111-1111-4111-8111-111111111111', command: 'board' });
  storage.setItem(localKeys.outbox, JSON.stringify([poisoned]));
  const collector = transactionalCollector();
  const client = telemetry.createClient({
    storage, endpoint: 'http://127.0.0.1:8787',
    instanceId: '22222222-2222-4222-8222-222222222222',
    fetch: collector.fetch
  });
  client.trackEvaluation(selection, { route: 'auditoria', scope: 'function' });
  client.trackEvaluation({ ...selection, selectedFunctions: ['type-choice'] }, { route: 'tipografia', scope: 'function' });

  const flushed = await client.flush();

  assert.equal(flushed, true, 'flush must complete after isolating the rejection');
  const pending = JSON.parse(storage.getItem(localKeys.outbox) || '[]');
  assert.equal(pending.length, 0, 'valid events must not stay blocked behind the poison');
  const rejected = JSON.parse(storage.getItem(localKeys.rejected) || '[]');
  assert.deepEqual(rejected.map(event => event.event_id), ['not-a-uuid-at-all']);
  assert.ok(collector.accepted.length >= 2, 'valid events must reach the collector');
  const ids = collector.accepted.map(event => event.event_id);
  assert.equal(new Set(ids).size, ids.length, 'no event may be counted twice');
  assert.ok(ids.every(id => id !== 'not-a-uuid-at-all'), 'the poisoned event must never be accepted');
});

test('a poison event in the middle keeps its valid neighbours in order', async () => {
  const storage = memoryStorage();
  const first = boardEvent('11111111-1111-4111-8111-111111111111', 'router.invoked', { evaluation_id: '33333333-3333-4333-8333-333333333333', command: 'board' });
  const poisoned = boardEvent('22222222-2222-4222-8222-222222222222', 'router.invoked', { evaluation_id: 'not-good', command: 'board' });
  const last = boardEvent('44444444-4444-4444-8444-444444444444', 'router.invoked', { evaluation_id: '55555555-5555-4555-8555-555555555555', command: 'board' });
  storage.setItem(localKeys.outbox, JSON.stringify([first, poisoned, last]));
  const collector = transactionalCollector();
  const client = telemetry.createClient({
    storage, endpoint: 'http://127.0.0.1:8787',
    instanceId: '22222222-2222-4222-8222-222222222222',
    fetch: async (url, options) => {
      const body = JSON.parse(options.body);
      const index = body.events.findIndex(event => event.evaluation_id === 'not-good');
      if (index >= 0) return { ok: false, status: 422, json: async () => ({ error: 'INVALID_EVALUATION_ID', index }) };
      collector.accepted.push(...body.events);
      return { ok: true, status: 202 };
    }
  });

  assert.equal(await client.flush(), true);
  assert.deepEqual(collector.accepted.map(event => event.event_id),
    ['11111111-1111-4111-8111-111111111111', '44444444-4444-4444-8444-444444444444'],
    'neighbours must survive, once each, in causal order');
  const rejected = JSON.parse(storage.getItem(localKeys.rejected) || '[]');
  assert.deepEqual(rejected.map(event => event.event_id), ['22222222-2222-4222-8222-222222222222']);
});

test('a batch-level rejection without index quarantines that batch and the queue continues', async () => {
  const storage = memoryStorage();
  const marker = boardEvent('11111111-1111-4111-8111-111111111111', 'router.invoked', { evaluation_id: '33333333-3333-4333-8333-333333333333', command: 'board' });
  storage.setItem(localKeys.outbox, JSON.stringify([marker]));
  const calls = [];
  let failBatch = true;
  const client = telemetry.createClient({
    storage, endpoint: 'http://127.0.0.1:8787',
    instanceId: '22222222-2222-4222-8222-222222222222',
    fetch: async (_url, options) => {
      const body = JSON.parse(options.body);
      calls.push(body.events.map(event => event.event_id));
      if (failBatch && body.events.some(event => event.event_id === '11111111-1111-4111-8111-111111111111')) {
        // Batch-level rejection: the collector names no offending index.
        return { ok: false, status: 422, json: async () => ({ error: 'INVALID_BATCH_SCHEMA' }) };
      }
      return { ok: true, status: 202 };
    }
  });
  client.trackEvaluation(selection, { route: 'auditoria', scope: 'function' });

  const first = await client.flush();
  // The malformed batch is quarantined whole (mirrors the Python client) and
  // never retried; events valid on their own in a later batch still deliver.
  assert.equal(first, true, 'flush must not retry the rejected batch forever');
  assert.equal(JSON.parse(storage.getItem(localKeys.outbox) || '[]').length, 0);
  const rejected = JSON.parse(storage.getItem(localKeys.rejected) || '[]');
  assert.ok(rejected.some(event => event.event_id === '11111111-1111-4111-8111-111111111111'),
    'the rejected batch is kept for inspection, not silently lost');

  failBatch = false;
  const delivered = [];
  const client2 = telemetry.createClient({
    storage, endpoint: 'http://127.0.0.1:8787',
    instanceId: '22222222-2222-4222-8222-222222222222',
    fetch: async (_url, options) => {
      const body = JSON.parse(options.body);
      delivered.push(...body.events);
      return { ok: true, status: 202 };
    }
  });
  client2.trackEvaluation(selection, { route: 'tipografia', scope: 'function' });
  assert.equal(await client2.flush(), true);
  assert.ok(delivered.length >= 1, 'the queue keeps working after a batch-level rejection');
  assert.ok(delivered.every(event => event.event_id !== '11111111-1111-4111-8111-111111111111'));
});

test('a retryable failure still keeps the queue untouched for the next attempt', async () => {
  const storage = memoryStorage();
  const client = telemetry.createClient({
    storage, endpoint: 'http://127.0.0.1:8787',
    instanceId: '22222222-2222-4222-8222-222222222222',
    fetch: async () => ({ ok: false, status: 503 })
  });
  client.trackEvaluation(selection, { route: 'auditoria', scope: 'function' });
  assert.equal(await client.flush(), false);
  const pending = JSON.parse(storage.getItem(localKeys.outbox) || '[]');
  assert.ok(pending.length >= 1, 'a server error must keep events queued, not drop them');
  assert.equal(JSON.parse(storage.getItem(localKeys.rejected) || '[]').length, 0);
});

test('the outbox evicts the oldest events beyond its bound', async () => {
  const storage = memoryStorage();
  const client = telemetry.createClient({
    storage, endpoint: 'http://127.0.0.1:8787',
    instanceId: '22222222-2222-4222-8222-222222222222',
    // Collector returns 503 so nothing leaves the queue and no Web Lock is leaked.
    fetch: async () => ({ ok: false, status: 503 })
  });
  const returned = [];
  for (let index = 0; index < 340; index++) {
    returned.push(client.trackEvaluation(selection, { route: 'auditoria', scope: 'function' }));
  }
  const stored = JSON.parse(storage.getItem(localKeys.outbox) || '[]');
  assert.equal(stored.length, 1000, 'the queue is bounded at 1000 events');
  const firstIds = new Set(returned[0].map(event => event.event_id));
  const lastIds = new Set(returned[339].map(event => event.event_id));
  assert.ok(stored.every(event => !firstIds.has(event.event_id)),
    'the oldest evaluation is dropped, never silently kept');
  assert.ok([...lastIds].every(id => stored.some(event => event.event_id === id)),
    'the newest evaluation survives');
});

test('overlapping flushes share one in-flight run and never drop undelivered events', async () => {
  const storage = memoryStorage();
  const seeded = Array.from({ length: 101 }, (_, i) => ({
    event_id: `00000000-0000-4000-8000-${String(i + 1).padStart(12, '0')}`,
    name: 'router.invoked',
    occurred_at: '2026-11-18T00:00:00Z',
    source: 'board',
    instance_id: '22222222-2222-4222-8222-222222222222',
    router_version: '1.3.0',
    tree_version: '0.4',
    evaluation_id: `10000000-0000-4000-8000-${String(i + 1).padStart(12, '0')}`,
    command: 'board'
  }));
  storage.setItem(localKeys.outbox, JSON.stringify(seeded));

  const seenBatches = [];
  let releaseFirst;
  const firstPending = new Promise(resolve => { releaseFirst = resolve; });
  const client = telemetry.createClient({
    storage, endpoint: 'http://127.0.0.1:8787',
    instanceId: '22222222-2222-4222-8222-222222222222',
    fetch: async (_url, options) => {
      const body = JSON.parse(options.body);
      seenBatches.push(body.events.length);
      if (seenBatches.length === 1) {
        await firstPending;
        return { ok: true, status: 202 };
      }
      return { ok: false, status: 503 };
    }
  });

  const p1 = client.flush();
  const p2 = client.flush();
  assert.equal(seenBatches.length, 1, 'second flush must share the in-flight run');
  releaseFirst();
  const [r1, r2] = await Promise.all([p1, p2]);
  assert.equal(r1, false);
  assert.equal(r2, false);
  assert.deepEqual(seenBatches, [100, 1]);
  const pending = JSON.parse(storage.getItem(localKeys.outbox) || '[]');
  assert.equal(pending.length, 1, 'event 101 must survive a 503 after overlapping flush calls');
  assert.equal(pending[0].event_id, seeded[100].event_id);

  // Subsequent flush after completion must start a fresh run and deliver later events.
  const callsAfter = [];
  const client3 = telemetry.createClient({
    storage: memoryStorage(), endpoint: 'http://127.0.0.1:8787',
    instanceId: '22222222-2222-4222-8222-222222222222',
    fetch: async (_url, options) => {
      callsAfter.push(JSON.parse(options.body).events.length);
      return { ok: true, status: 202 };
    }
  });
  client3.trackEvaluation(selection, { route: 'auditoria', scope: 'function' });
  assert.equal(await client3.flush(), true);
  client3.trackEvaluation(selection, { route: 'tipografia', scope: 'function' });
  assert.equal(await client3.flush(), true);
  assert.equal(callsAfter.length, 2, 'a second flush after completion must deliver new events');
});

test('in-flight eviction during flush removes only delivered events by id', async () => {
  const storage = memoryStorage();
  let releaseFetch;
  const fetchGate = new Promise(resolve => { releaseFetch = resolve; });
  const client = telemetry.createClient({
    storage, endpoint: 'http://127.0.0.1:8787',
    instanceId: '22222222-2222-4222-8222-222222222222',
    fetch: async () => {
      await fetchGate;
      return { ok: true, status: 202 };
    }
  });
  const firstEvents = client.trackEvaluation(selection, { route: 'auditoria', scope: 'function' });
  const flushing = client.flush();
  // Enqueue > MAX_OUTBOX events while the first batch is in flight so firstEvents
  // are evicted from index 0 before the fetch resolves.
  const latestBatch = [];
  for (let i = 0; i < 350; i++) {
    latestBatch.push(client.trackEvaluation(selection, { route: 'auditoria', scope: 'function' }));
  }
  const expectedIds = new Set(JSON.parse(storage.getItem(localKeys.outbox) || '[]').map(e => e.event_id));
  for (const ev of firstEvents) assert.ok(!expectedIds.has(ev.event_id));
  // Fail the next batch once the first completes so we inspect queue state right after first batch removal.
  releaseFetch();
  await flushing;
  const remaining = JSON.parse(storage.getItem(localKeys.outbox) || '[]');
  assert.equal(remaining.length, 0);
  // Also verify single-batch removal by id when next batch returns 503:
  const storage2 = memoryStorage();
  let gate2;
  const pending2 = new Promise(resolve => { gate2 = resolve; });
  let calls = 0;
  const client2 = telemetry.createClient({
    storage: storage2, endpoint: 'http://127.0.0.1:8787',
    instanceId: '22222222-2222-4222-8222-222222222222',
    fetch: async () => {
      calls++;
      if (calls === 1) {
        await pending2;
        return { ok: true, status: 202 };
      }
      return { ok: false, status: 503 };
    }
  });
  client2.trackEvaluation(selection, { route: 'auditoria', scope: 'function' });
  const flushing2 = client2.flush();
  for (let i = 0; i < 350; i++) {
    client2.trackEvaluation(selection, { route: 'auditoria', scope: 'function' });
  }
  const beforeResolve = JSON.parse(storage2.getItem(localKeys.outbox) || '[]');
  assert.equal(beforeResolve.length, 1000);
  gate2();
  assert.equal(await flushing2, false);
  const afterResolve = JSON.parse(storage2.getItem(localKeys.outbox) || '[]');
  assert.equal(afterResolve.length, 1000,
    'evicted in-flight batch must not slice newer queued events out by position');
  assert.equal(afterResolve[0].event_id, beforeResolve[0].event_id);
});

test('flushing an empty queue never wedges subsequent flushes', async () => {
  const storage = memoryStorage();
  const requests = [];
  const client = telemetry.createClient({
    storage, endpoint: 'http://127.0.0.1:8787',
    instanceId: '22222222-2222-4222-8222-222222222222',
    fetch: async (_url, options) => {
      requests.push(JSON.parse(options.body).events);
      return { ok: true, status: 202 };
    }
  });
  // Flush on empty queue first (exact regression from d2351ca).
  assert.equal(await client.flush(), true);
  assert.equal(requests.length, 0);

  client.trackEvaluation(selection, { route: 'auditoria', scope: 'function' });
  assert.equal(await client.flush(), true);
  assert.equal(requests.length, 1, 'flush after an empty flush must still POST new events');
  assert.equal(JSON.parse(storage.getItem(localKeys.outbox) || '[]').length, 0);

  // Also verify sequential empty-flush cycle between delivered evaluations.
  assert.equal(await client.flush(), true);
  client.trackEvaluation(selection, { route: 'tipografia', scope: 'function' });
  assert.equal(await client.flush(), true);
  assert.equal(requests.length, 2);
  assert.equal(JSON.parse(storage.getItem(localKeys.outbox) || '[]').length, 0);
});

test('two tabs sharing storage preserve both evaluations during a 503 outage', async () => {
  const storage = memoryStorage();
  const failFetch = async () => ({ ok: false, status: 503 });
  const tabA = telemetry.createClient({
    storage, endpoint: 'http://127.0.0.1:8787',
    instanceId: '22222222-2222-4222-8222-222222222222',
    fetch: failFetch
  });
  const tabB = telemetry.createClient({
    storage, endpoint: 'http://127.0.0.1:8787',
    instanceId: '22222222-2222-4222-8222-222222222222',
    fetch: failFetch
  });

  const eventsA = tabA.trackEvaluation(selection, { route: 'auditoria', scope: 'function' });
  assert.equal(await tabA.flush(), false);
  const eventsB = tabB.trackEvaluation(selection, { route: 'tipografia', scope: 'function' });
  assert.equal(await tabB.flush(), false);

  const persisted = JSON.parse(storage.getItem(localKeys.outbox) || '[]');
  const persistedIds = new Set(persisted.map(event => event.event_id));
  for (const event of [...eventsA, ...eventsB]) {
    assert.ok(persistedIds.has(event.event_id), 'both tabs events must survive in shared storage');
  }
});

function enumerableStorage() {
  const storage = memoryStorage();
  return {
    get length() { return storage.values.size; },
    key: i => Array.from(storage.values.keys())[i] ?? null,
    removeItem: k => storage.values.delete(k),
    ...storage
  };
}

for (const [name, first, second, inline] of [
  ['configured origins', 'https://a.example', 'https://b.example', false],
  ['inline paths', 'https://shared.example/a', 'https://shared.example/b', true],
  ['inline queries', 'https://shared.example?tenant=a', 'https://shared.example?tenant=b', true]
]) {
  test(`an outage keeps queues isolated across ${name} and recovers on return`, async () => {
    const storage = enumerableStorage();
    telemetry.configure(first, { storage });
    const firstTab = telemetry.createClient({ storage, fetch: async () => ({ ok: false, status: 503 }) });
    const firstEvents = firstTab.trackEvaluation(selection, { route: 'auditoria' });
    assert.equal(await firstTab.flush(), false);

    const window = { localStorage: storage };
    if (inline) window.DESIGN_ROUTER_TELEMETRY = { endpoint: second };
    else telemetry.configure(second, { storage });
    const secondCollector = transactionalCollector();
    const secondTab = telemetry.init(window, { readyState: 'loading', addEventListener() {} }, {
      storage, fetch: secondCollector.fetch
    });
    const secondEvents = secondTab.trackEvaluation(selection, { route: 'tipografia' });
    assert.equal(await secondTab.flush(), true);
    assert.deepEqual(secondCollector.accepted, secondEvents);

    telemetry.configure(first + '#return', { storage });
    const recovered = transactionalCollector();
    const returningTab = telemetry.createClient({ storage, fetch: recovered.fetch });
    assert.equal(await returningTab.flush(), true);
    assert.deepEqual(recovered.accepted, firstEvents);
  });
}

test('inline endpoint secrets never appear in persisted keys or values', async () => {
  const storage = enumerableStorage();
  const secret = 'ephemeral-signed-value';
  const endpoint = 'https://collector.example/api?sig=' + secret;
  const collector = telemetry.init({ DESIGN_ROUTER_TELEMETRY: { endpoint } },
    { readyState: 'loading', addEventListener() {} },
    { storage, fetch: async () => ({ ok: false, status: 503 }) });
  collector.trackEvaluation(selection, { route: 'auditoria' });
  assert.equal(await collector.flush(), false);
  assert.ok(storage.values.size > 0);
  for (const [key, value] of storage.values) {
    assert.ok(!key.includes(secret) && !value.includes(secret));
  }
});

test('collector storage keys use SHA-256 of the normalized ingestion URL', () => {
  const urls = ['https://例え.jp/ñ?tenant=山', 'https://example.com/' + 'x'.repeat(4096)];
  // Exercise both sides of the SHA-256 padding boundary and multiple blocks.
  for (const length of [55, 56, 63, 64, 65]) {
    const prefix = 'https://example.org/';
    urls.push(prefix + 'x'.repeat(length - prefix.length - '/v1/events'.length));
  }
  for (const endpoint of urls) {
    const { eventsUrl, outbox } = telemetry.keys.forEndpoint(endpoint);
    const digest = createHash('sha256').update(eventsUrl).digest('hex');
    assert.equal(outbox, telemetry.keys.OUTBOX_KEY + ':' + digest);
  }
});

test('unattributed legacy queues and shards stay local on upgrade', async () => {
  const storage = enumerableStorage();
  const endpoint = 'https://configured.example';
  const legacyKey = 'design-router.telemetry.outbox';
  const oldShard = legacyKey + '.tab.old';
  const legacy = JSON.stringify([{ event_id: 'legacy-event' }]);
  storage.setItem(telemetry.keys.ENDPOINT_KEY, endpoint);
  storage.setItem(legacyKey, legacy);
  storage.setItem(oldShard, legacy);
  const collector = transactionalCollector();
  const client = telemetry.createClient({ storage, fetch: collector.fetch });
  const fresh = client.trackEvaluation(selection, { route: 'auditoria' });
  assert.equal(await client.flush(), true);
  assert.deepEqual(collector.calls, [fresh.map(event => event.event_id)]);
  assert.equal(storage.getItem(legacyKey), legacy);
  assert.equal(storage.getItem(oldShard), legacy);
});

test('switching collector clears previous token and binds tokens to their origin', () => {
  const storage = memoryStorage();
  telemetry.configure('http://collector-a.local:8787', { storage, token: 'secret-a' });
  const cfgA = telemetry.automaticConfig({ localStorage: storage });
  assert.equal(cfgA.endpoint, 'http://collector-a.local:8787');
  assert.equal(cfgA.token, 'secret-a');
  assert.equal(cfgA.routerVersion, '1.4.0');

  // Reconfiguring to collector B without a token must clear collector A's token.
  telemetry.configure('http://collector-b.local:9000', { storage });
  const cfgB = telemetry.automaticConfig({ localStorage: storage });
  assert.equal(cfgB.endpoint, 'http://collector-b.local:9000');
  assert.equal(cfgB.token, undefined);

  // Even if ENDPOINT_KEY is overwritten directly in storage, an origin mismatch drops the token.
  telemetry.configure('http://collector-a.local:8787', { storage, token: 'secret-a' });
  storage.setItem(telemetry.keys.ENDPOINT_KEY, 'http://collector-c.local:9001');
  const cfgC = telemetry.automaticConfig({ localStorage: storage });
  assert.equal(cfgC.endpoint, 'http://collector-c.local:9001');
  assert.equal(cfgC.token, undefined);
});

test('board telemetry defaults router_version to 1.4.0', () => {
  const events = telemetry.buildEvaluationEvents(selection, context());
  assert.ok(events.length > 0);
  for (const event of events) {
    assert.equal(event.router_version, '1.4.0');
  }
});

test('quota failure while reconfiguring never leaves previous collector token bound to new origin', () => {
  const map = new Map();
  const quotaStorage = {
    failTokenWrite: false,
    getItem: k => (map.has(k) ? map.get(k) : null),
    setItem: (k, v) => {
      if (quotaStorage.failTokenWrite && k === telemetry.keys.TOKEN_KEY) {
        throw new Error('QuotaExceededError');
      }
      map.set(k, String(v));
    },
    removeItem: k => { map.delete(k); }
  };
  telemetry.configure('http://collector-a.local:8787', { storage: quotaStorage, token: 'short-a' });
  quotaStorage.failTokenWrite = true;
  telemetry.configure('http://collector-b.local:8787', { storage: quotaStorage, token: 'much-longer-token-b' });
  const cfg = telemetry.automaticConfig({ localStorage: quotaStorage });
  assert.equal(cfg.endpoint, 'http://collector-b.local:8787');
  assert.equal(cfg.token, undefined);
  assert.equal(quotaStorage.getItem(telemetry.keys.TOKEN_KEY), null);
});

test('init endpoint override to a different origin never forwards previous inline or stored token', async () => {
  const sentHeaders = [];
  const doc = {
    readyState: 'complete',
    addEventListener() {}
  };
  const winInline = {
    DESIGN_ROUTER_TELEMETRY: { endpoint: 'http://collector-a.local:8787', token: 'inline-secret' },
    __minimalRouterPreview: {
      getState: () => ({ route: 'tipografia', scope: 'route' }),
      getSelection: () => selection
    }
  };
  const storage = memoryStorage();
  const clientA = telemetry.init(winInline, doc, {
    storage,
    endpoint: 'http://collector-b.local:9000',
    fetch: async (_url, opts) => { sentHeaders.push(opts.headers); return { ok: true, status: 202 }; }
  });
  clientA.trackEvaluation(selection, { route: 'tipografia', scope: 'route' });
  await clientA.flush();
  assert.equal(sentHeaders.length, 1);
  assert.equal(sentHeaders[0].Authorization, undefined);

  const storageB = memoryStorage();
  telemetry.configure('http://collector-a.local:8787', { storage: storageB, token: 'stored-secret' });
  const winStored = {
    localStorage: storageB,
    __minimalRouterPreview: {
      getState: () => ({ route: 'tipografia', scope: 'route' }),
      getSelection: () => selection
    }
  };
  const clientB = telemetry.init(winStored, doc, {
    storage: storageB,
    endpoint: 'http://collector-c.local:9001',
    fetch: async (_url, opts) => { sentHeaders.push(opts.headers); return { ok: true, status: 202 }; }
  });
  clientB.trackEvaluation(selection, { route: 'tipografia', scope: 'route' });
  await clientB.flush();
  assert.equal(sentHeaders.length, 2);
  assert.equal(sentHeaders[1].Authorization, undefined);
});

test('unwritable localStorage never loops delivered or rejected events 1001 times', async () => {
  const seededDelivered = boardEvent('00000000-0000-4000-8000-000000000901', 'router.invoked', { evaluation_id: '11111111-1111-4111-8111-111111111111', command: 'board' });
  const map = new Map([[localKeys.outbox, JSON.stringify([seededDelivered])]]);
  const fullStorage = {
    getItem: k => (map.has(k) ? map.get(k) : null),
    setItem: () => { throw new Error('QuotaExceededError'); },
    removeItem: () => { throw new Error('QuotaExceededError'); }
  };
  let posts = 0;
  const client = telemetry.createClient({
    endpoint: 'http://127.0.0.1:8787',
    storage: fullStorage,
    fetch: async () => { posts += 1; return { ok: true, status: 202 }; }
  });
  const ok = await client.flush();
  assert.equal(ok, true);
  assert.equal(posts, 1, 'delivered event must be sent once even when storage cannot be written');

  // Indexed 422 while storage is full must isolate bad event and deliver valid neighbor without looping.
  const poisoned = boardEvent('00000000-0000-4000-8000-000000000902', 'router.invoked', { evaluation_id: '11111111-1111-4111-8111-111111111111', command: 'bad' });
  const map2 = new Map([[localKeys.outbox, JSON.stringify([poisoned])]]);
  const fullStorage2 = {
    getItem: k => (map2.has(k) ? map2.get(k) : null),
    setItem: () => { throw new Error('QuotaExceededError'); },
    removeItem: () => { throw new Error('QuotaExceededError'); }
  };
  const postedBatches = [];
  const client2 = telemetry.createClient({
    endpoint: 'http://127.0.0.1:8787',
    storage: fullStorage2,
    fetch: async (_url, opts) => {
      const batch = JSON.parse(opts.body).events;
      postedBatches.push(batch.map(e => e.event_id));
      const badIdx = batch.findIndex(e => e.event_id === poisoned.event_id);
      if (badIdx >= 0) {
        return { ok: false, status: 422, json: async () => ({ error: 'INVALID', index: badIdx }) };
      }
      return { ok: true, status: 202 };
    }
  });
  client2.trackEvaluation(selection, { route: 'tipografia', scope: 'route' });
  const ok2 = await client2.flush();
  assert.equal(ok2, true);
  assert.equal(postedBatches.length, 2, 'must isolate poisoned event and deliver valid events in 2 POSTs');
});

test('enumerable shared storage preserves concurrent two-tab evaluations during 503 outage', async () => {
  const map = new Map();
  const browserStorage = {
    get length() { return map.size; },
    key: i => Array.from(map.keys())[i] ?? null,
    getItem: k => (map.has(k) ? map.get(k) : null),
    setItem: (k, v) => { map.set(k, String(v)); },
    removeItem: k => { map.delete(k); }
  };
  let fail = true;
  const delivered = [];
  const fetcher = async (_url, opts) => {
    if (fail) return { ok: false, status: 503 };
    delivered.push(...JSON.parse(opts.body).events);
    return { ok: true, status: 202 };
  };
  const tabA = telemetry.createClient({ endpoint: 'http://127.0.0.1:8787', storage: browserStorage, fetch: fetcher });
  const tabB = telemetry.createClient({ endpoint: 'http://127.0.0.1:8787', storage: browserStorage, fetch: fetcher });
  const expectedIds = new Set();
  for (let i = 0; i < 40; i++) {
    for (const ev of tabA.trackEvaluation({ selectedFunctions: ['type-choice'], support: { read: [], write: [] } }, { route: 'tipografia', scope: 'function' })) {
      expectedIds.add(ev.event_id);
    }
    for (const ev of tabB.trackEvaluation({ selectedFunctions: ['visual-qa'], support: { read: [], write: [] } }, { route: 'auditoria', scope: 'function' })) {
      expectedIds.add(ev.event_id);
    }
  }
  assert.equal(await tabA.flush(), false);
  assert.equal(await tabB.flush(), false);
  fail = false;
  assert.equal(await tabA.flush(), true);
  assert.equal(await tabB.flush(), true);
  const deliveredIds = new Set(delivered.map(e => e.event_id));
  assert.equal(deliveredIds.size, 80);
  for (const id of expectedIds) assert.ok(deliveredIds.has(id));
  assert.equal(JSON.parse(browserStorage.getItem(localKeys.outbox) || '[]').length, 0);
  const leftoverShards = Array.from(map.keys()).filter(k => k.startsWith(localKeys.shardPrefix));
  assert.deepEqual(leftoverShards, []);
});

test('endpoint URLs with query strings or fragments still post to /v1/events', async () => {
  const urls = [];
  for (const endpoint of ['https://collector.example?env=prod', 'https://collector.example#prod', 'https://collector.example/api/?env=1#frag']) {
    const client = telemetry.createClient({
      endpoint,
      storage: memoryStorage(),
      fetch: async (url) => { urls.push(url); return { ok: true, status: 202 }; }
    });
    client.trackEvaluation(selection, { route: 'tipografia', scope: 'route' });
    await client.flush();
  }
  assert.deepEqual(urls, [
    'https://collector.example/v1/events?env=prod',
    'https://collector.example/v1/events',
    'https://collector.example/api/v1/events?env=1'
  ]);
});

test('canonical repo/name skill_id is emitted when present and online event triggers flush', async () => {
  const canonicalSelection = {
    selectedFunctions: ['motion-audit'],
    support: {
      read: [{ skill: { id: 'X34', repo: 'emilkowalski/skills', name: 'find-animation-opportunities' }, function_id: 'motion-audit' }],
      write: [{ skill: { id: 'X01' }, function_id: 'visual-qa' }]
    }
  };
  const events = telemetry.buildEvaluationEvents(canonicalSelection, context());
  const selectedIds = events.filter(e => e.name === 'skill.selected').map(e => e.skill_id);
  assert.deepEqual(selectedIds, ['emilkowalski/skills/find-animation-opportunities', 'X01']);

  const listeners = {};
  const win = {
    DESIGN_ROUTER_TELEMETRY: { endpoint: 'http://127.0.0.1:8787' },
    addEventListener(name, fn) { listeners[name] = fn; },
    __minimalRouterPreview: {
      getState: () => ({ route: 'tipografia', scope: 'route' }),
      getSelection: () => canonicalSelection
    }
  };
  const doc = { readyState: 'complete', addEventListener() {} };
  let online = false;
  let delivered = 0;
  const client = telemetry.init(win, doc, {
    storage: memoryStorage(),
    fetch: async () => {
      if (!online) return { ok: false, status: 503 };
      delivered += 1;
      return { ok: true, status: 202 };
    }
  });
  client.trackEvaluation(canonicalSelection, { route: 'tipografia', scope: 'route' });
  assert.equal(await client.flush(), false);
  assert.equal(typeof listeners.online, 'function');
  online = true;
  listeners.online();
  await new Promise(r => setTimeout(r, 20));
  assert.ok(delivered >= 1, 'online event should flush queued events automatically');
});

test('empty endpoint override disables telemetry instead of falling back to cross-origin stored collector with inline token', async () => {
  const storage = memoryStorage();
  storage.setItem(telemetry.keys.ENDPOINT_KEY, 'http://stored-collector.local:9001');
  const win = {
    DESIGN_ROUTER_TELEMETRY: {
      endpoint: 'http://inline-collector.local:8787',
      token: 'secret-inline-token'
    },
    addEventListener() {},
    __minimalRouterPreview: {
      getState: () => ({ route: 'tipografia', scope: 'route' }),
      getSelection: () => selection
    }
  };
  const doc = { readyState: 'complete', addEventListener() {} };
  const requests = [];
  const client = telemetry.init(win, doc, {
    storage,
    endpoint: '',
    fetch: async (url, opts) => {
      requests.push({ url, headers: opts.headers });
      return { ok: true, status: 202 };
    }
  });
  assert.equal(client.enabled, false);
  assert.equal(client.endpoint, null);
  client.trackEvaluation(selection, { route: 'tipografia', scope: 'route' });
  await client.flush();
  assert.deepEqual(requests, [], 'empty endpoint override must never post to stored collector or leak inline token');

  // createClient({ endpoint: '' }) directly must also not fall back to stored endpoint.
  const direct = telemetry.createClient({
    endpoint: '',
    token: 'secret-direct-token',
    storage,
    fetch: async (url, opts) => {
      requests.push({ url, headers: opts.headers });
      return { ok: true, status: 202 };
    }
  });
  assert.equal(direct.enabled, false);
  assert.equal(direct.endpoint, null);
  direct.trackEvaluation(selection, { route: 'tipografia', scope: 'route' });
  await direct.flush();
  assert.deepEqual(requests, []);
});

test('malformed stored event without event_id does not loop under quota errors and flushes rejected diagnostics once writable', async () => {
  const malformed = { name: 'router.invoked', source: 'board', command: 'board' };
  const map = new Map([[localKeys.outbox, JSON.stringify([malformed])]]);
  let failWrites = true;
  const storage = {
    getItem: k => (map.has(k) ? map.get(k) : null),
    setItem: (k, v) => {
      if (failWrites) throw new Error('QuotaExceededError');
      map.set(k, String(v));
    },
    removeItem: k => {
      if (failWrites) throw new Error('QuotaExceededError');
      map.delete(k);
    }
  };
  const posted = [];
  const delivered = [];
  const client = telemetry.createClient({
    endpoint: 'http://127.0.0.1:8787',
    storage,
    fetch: async (_url, opts) => {
      const batch = JSON.parse(opts.body).events;
      posted.push(batch);
      const badIdx = batch.findIndex(e => !e.event_id);
      if (badIdx >= 0) {
        return { ok: false, status: 422, json: async () => ({ error: 'MISSING_EVENT_ID', index: badIdx }) };
      }
      delivered.push(...batch);
      return { ok: true, status: 202 };
    }
  });
  client.trackEvaluation(selection, { route: 'tipografia', scope: 'route' });
  const ok = await client.flush();
  assert.equal(ok, true);
  assert.equal(posted.length, 2, 'must isolate missing-event_id entry in 2 POSTs without looping');
  assert.ok(delivered.length >= 2, 'valid neighbors must be delivered');
  assert.equal(map.has(localKeys.rejected), false, 'quota error prevented initial rejected write');

  // Once storage becomes writable again, next flush persists the retained diagnostic.
  failWrites = false;
  assert.equal(await client.flush(), true);
  const savedRejected = JSON.parse(map.get(localKeys.rejected) || '[]');
  assert.equal(savedRejected.length, 1);
  assert.equal(savedRejected[0].name, 'router.invoked');
  assert.equal(savedRejected[0].event_id, undefined);
});
