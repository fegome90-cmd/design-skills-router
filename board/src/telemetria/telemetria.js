/* Design Skills Router — opt-in browser telemetry client.
 *
 * OFF by default. Activates only when an explicit endpoint is configured via
 * window.DESIGN_ROUTER_TELEMETRY = { endpoint: 'http://127.0.0.1:8787' } or
 * localStorage['design-router.telemetry.endpoint'].
 *
 * The client sends only stable catalog/tree identifiers and an anonymous
 * random installation UUID. It never reads user text, file paths or host data.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) {
    module.exports = api;
  } else {
    root.DesignRouterTelemetry = api;
    api.init(root, root.document);
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const SCHEMA = 'design-router-telemetry/1';
  const ENDPOINT_KEY = 'design-router.telemetry.endpoint';
  const TOKEN_KEY = 'design-router.telemetry.token';
  const TOKEN_ORIGIN_KEY = 'design-router.telemetry.token_origin';
  const INSTANCE_KEY = 'design-router.telemetry.instance_id';
  const OUTBOX_KEY = 'design-router.telemetry.outbox';
  const OUTBOX_SHARD_PREFIX = 'design-router.telemetry.outbox.tab.';
  const REJECTED_KEY = 'design-router.telemetry.rejected';
  const FLUSH_LOCK_NAME = 'design-router.telemetry.flush';
  const ROUTER_VERSION = '1.4.0';
  const MAX_OUTBOX = 1000;
  const MAX_REJECTED = 100;
  const MAX_RETIRED = MAX_OUTBOX * 4;

  function uuid() {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      return crypto.randomUUID();
    }
    const bytes = new Uint8Array(16);
    if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
      crypto.getRandomValues(bytes);
    } else {
      for (let i = 0; i < bytes.length; i++) bytes[i] = Math.floor(Math.random() * 256);
    }
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    const hex = Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
  }

  function nowIso() {
    return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
  }

  function endpointOrigin(endpoint) {
    if (!endpoint || typeof endpoint !== 'string') return null;
    try {
      const parsed = new URL(endpoint);
      return parsed.origin && parsed.origin !== 'null' ? parsed.origin : null;
    } catch (_) {
      return null;
    }
  }

  function buildEventsUrl(endpoint) {
    if (!endpoint || typeof endpoint !== 'string') return '';
    try {
      const parsed = new URL(endpoint);
      parsed.pathname = parsed.pathname.replace(/\/+$/, '') + '/v1/events';
      parsed.hash = '';
      return parsed.toString();
    } catch (_) {
      return endpoint.replace(/#.*$/, '').replace(/\?.*$/, '').replace(/\/+$/, '') + '/v1/events';
    }
  }

  function canonicalSkillId(skill) {
    if (!skill || typeof skill !== 'object') return null;
    if (skill.repo && skill.name) return `${skill.repo}/${skill.name}`;
    return skill.id || null;
  }

  function buildEvaluationEvents(selection, context) {
    const {
      evaluationId, instanceId, routerVersion = ROUTER_VERSION, treeVersion = '0.4',
      route, scope, occurredAt = nowIso(), newId = uuid
    } = context || {};
    if (!selection || !evaluationId || !instanceId) return [];
    const base = {
      source: 'board',
      instance_id: instanceId,
      router_version: routerVersion,
      tree_version: treeVersion
    };
    const event = (name, fields) => Object.assign({
      event_id: newId(),
      name,
      occurred_at: occurredAt,
      ...base
    }, fields);
    const events = [event('router.invoked', {
      evaluation_id: evaluationId,
      command: 'board',
      ...(route ? { route } : {}),
      ...(scope ? { scope } : {}),
      ...(scope === 'function' && selection.selectedFunctions && selection.selectedFunctions.length === 1
        ? { function_id: selection.selectedFunctions[0] } : {})
    })];

    // nodesByFunction is a lookup derived from the selection, not a packet
    // visit. The board must not emit decision.node_visited from it.

    const skills = new Set();
    const support = selection.support || {};
    for (const group of ['read', 'write']) {
      for (const item of support[group] || []) {
        const skillId = canonicalSkillId(item && item.skill);
        if (!skillId || skills.has(skillId)) continue;
        skills.add(skillId);
        events.push(event('skill.selected', {
          evaluation_id: evaluationId,
          skill_id: skillId,
          ...(item.function_id ? { function_id: item.function_id } : {})
        }));
      }
    }
    return events;
  }

  function safeStorage(storage) {
    if (storage) return storage;
    try {
      if (typeof localStorage !== 'undefined') return localStorage;
    } catch (_) {}
    return null;
  }

  function read(storage, key) {
    try { return storage ? storage.getItem(key) : null; } catch (_) { return null; }
  }

  function write(storage, key, value) {
    if (!storage) return false;
    try {
      storage.setItem(key, value);
      return true;
    } catch (_) {
      return false;
    }
  }

  function remove(storage, key) {
    if (!storage) return;
    try {
      if (typeof storage.removeItem === 'function') {
        storage.removeItem(key);
      } else {
        storage.setItem(key, '');
      }
    } catch (_) {}
  }

  function readList(storage, key, max) {
    if (!storage) return null;
    try {
      const saved = storage.getItem(key);
      if (saved === null || saved === undefined || saved === '') return [];
      const parsed = JSON.parse(saved);
      return Array.isArray(parsed) ? parsed.slice(-max) : [];
    } catch (_) {
      return null;
    }
  }

  function canEnumerateStorage(storage) {
    try {
      return Boolean(storage && typeof storage.length === 'number' && typeof storage.key === 'function');
    } catch (_) {
      return false;
    }
  }

  function listShardKeys(storage) {
    if (!canEnumerateStorage(storage)) return [];
    const keys = [];
    try {
      for (let i = 0; i < storage.length; i++) {
        const key = storage.key(i);
        if (typeof key === 'string' && key.startsWith(OUTBOX_SHARD_PREFIX)) {
          keys.push(key);
        }
      }
    } catch (_) {
      return [];
    }
    keys.sort();
    return keys;
  }

  function appendUnique(base, additions, max) {
    const merged = base.slice();
    const seen = new Set(merged.map(item => item && item.event_id).filter(Boolean));
    for (const item of additions) {
      const id = item && item.event_id;
      if (id && seen.has(id)) continue;
      if (id) seen.add(id);
      merged.push(item);
    }
    return merged.length > max ? merged.slice(-max) : merged;
  }

  function filterOutBatch(list, items) {
    const refs = new Set(items);
    const ids = new Set(items.map(item => item && item.event_id).filter(Boolean));
    return list.filter(item => !refs.has(item) && !(item && item.event_id && ids.has(item.event_id)));
  }

  function runWithFlushLock(fn) {
    try {
      if (typeof navigator !== 'undefined' && navigator.locks && typeof navigator.locks.request === 'function') {
        return navigator.locks.request(FLUSH_LOCK_NAME, fn);
      }
    } catch (_) {}
    return fn();
  }

  function createClient(options) {
    const config = options || {};
    const storage = safeStorage(config.storage);
    const fetcher = config.fetch || (typeof fetch === 'function' ? fetch : null);
    const endpoint = config.endpoint || (storage ? read(storage, ENDPOINT_KEY) : null);
    const enabled = Boolean(config.enabled !== false && endpoint && fetcher);
    const supportsShards = canEnumerateStorage(storage);
    const shardKey = supportsShards ? OUTBOX_SHARD_PREFIX + uuid().slice(0, 12) : null;

    // Delivered or permanently rejected event identities kept in memory so a
    // full/unwritable localStorage can never resurrect and resend them.
    const retiredIds = new Set();
    const retiredRefs = new WeakSet();
    const markRetired = (items) => {
      for (const item of items) {
        if (item && typeof item === 'object') retiredRefs.add(item);
        const id = item && item.event_id;
        if (id) {
          retiredIds.add(id);
          if (retiredIds.size > MAX_RETIRED) {
            const oldest = retiredIds.values().next().value;
            retiredIds.delete(oldest);
          }
        }
      }
    };
    const excludeRetired = (list) => list.filter(item => {
      if (!item) return false;
      if (typeof item === 'object' && retiredRefs.has(item)) return false;
      if (item.event_id && retiredIds.has(item.event_id)) return false;
      return true;
    });

    let queue = readList(storage, OUTBOX_KEY, MAX_OUTBOX) || [];
    let queueUnsynced = false;
    let shardQueue = [];
    let shardUnsynced = false;
    // Events the collector rejected permanently. Kept for inspection so a
    // rejection is never a silent loss; never retried.
    let rejected = readList(storage, REJECTED_KEY, MAX_REJECTED) || [];
    let rejectedUnsynced = false;

    let instanceId = config.instanceId || (storage ? read(storage, INSTANCE_KEY) : null);
    if (!instanceId) {
      instanceId = uuid();
      write(storage, INSTANCE_KEY, instanceId);
    }
    let flushTimer = null;
    let inFlightFlush = null;

    const loadOutbox = () => {
      const stored = readList(storage, OUTBOX_KEY, MAX_OUTBOX);
      if (stored === null) return excludeRetired(queue);
      let merged = stored;
      if (supportsShards) {
        for (const key of listShardKeys(storage)) {
          const shard = readList(storage, key, MAX_OUTBOX);
          if (shard && shard.length) {
            merged = appendUnique(merged, shard, MAX_OUTBOX);
          }
        }
      }
      if (queueUnsynced || shardUnsynced) {
        merged = appendUnique(merged, queue, MAX_OUTBOX);
      }
      return excludeRetired(merged);
    };

    const loadRejected = () => {
      const stored = readList(storage, REJECTED_KEY, MAX_REJECTED);
      if (stored === null) return rejected;
      return rejectedUnsynced ? appendUnique(stored, rejected, MAX_REJECTED) : stored;
    };

    const saveOutbox = (next) => {
      const cleaned = excludeRetired(next);
      queue = cleaned.length > MAX_OUTBOX ? cleaned.slice(-MAX_OUTBOX) : cleaned;
      if (storage) {
        queueUnsynced = !write(storage, OUTBOX_KEY, JSON.stringify(queue));
      }
    };

    const saveRejected = (next) => {
      rejected = next.length > MAX_REJECTED ? next.slice(-MAX_REJECTED) : next;
      if (storage) {
        rejectedUnsynced = !write(storage, REJECTED_KEY, JSON.stringify(rejected));
      }
    };

    const appendToShard = (events) => {
      if (!supportsShards || !shardKey) return;
      const existing = shardUnsynced ? shardQueue : (readList(storage, shardKey, MAX_OUTBOX) || []);
      shardQueue = excludeRetired(appendUnique(existing, events, MAX_OUTBOX));
      shardUnsynced = !write(storage, shardKey, JSON.stringify(shardQueue));
    };

    const removeBatchFromShards = (items) => {
      if (!supportsShards) return;
      if (shardQueue.length) {
        shardQueue = excludeRetired(filterOutBatch(shardQueue, items));
      }
      for (const key of listShardKeys(storage)) {
        const shard = readList(storage, key, MAX_OUTBOX);
        if (!shard) continue;
        const remaining = excludeRetired(filterOutBatch(shard, items));
        if (remaining.length === shard.length) continue;
        if (remaining.length === 0) {
          remove(storage, key);
          if (key === shardKey) shardUnsynced = false;
        } else {
          const ok = write(storage, key, JSON.stringify(remaining));
          if (key === shardKey) shardUnsynced = !ok;
        }
      }
    };

    const reconcileOutbox = () => {
      if (!storage || !supportsShards) return;
      const merged = loadOutbox();
      const current = readList(storage, OUTBOX_KEY, MAX_OUTBOX);
      if (current === null) return;
      const currentIds = new Set(current.map(e => e && e.event_id).filter(Boolean));
      const missing = merged.some(e => e && e.event_id && !currentIds.has(e.event_id));
      if (missing) {
        saveOutbox(merged);
      }
    };

    const removeBatchFromQueue = (items) => {
      markRetired(items);
      removeBatchFromShards(items);
      const current = loadOutbox();
      saveOutbox(filterOutBatch(current, items));
    };

    const recordRejected = (items) => {
      const current = loadRejected();
      saveRejected(appendUnique(current, items, MAX_REJECTED));
    };

    const client = {
      enabled,
      endpoint,
      instanceId,
      reconcileOutbox,
      trackEvaluation(selection, context) {
        if (!enabled) return [];
        const events = buildEvaluationEvents(selection, {
          evaluationId: uuid(),
          instanceId,
          routerVersion: config.routerVersion,
          treeVersion: config.treeVersion,
          route: context && context.route,
          scope: context && context.scope,
          newId: uuid
        });
        if (!events.length) return [];
        // Persist first to this tab's uncontended shard (when enumerable
        // localStorage is available), then mirror the merged queue into
        // OUTBOX_KEY so concurrent tabs never overwrite each other during 503s.
        appendToShard(events);
        const current = loadOutbox();
        saveOutbox(appendUnique(current, events, MAX_OUTBOX));
        client.schedule();
        return events;
      },
      schedule() {
        if (!enabled || flushTimer !== null || typeof setTimeout !== 'function') return;
        flushTimer = setTimeout(() => { flushTimer = null; client.flush(); }, 120);
      },
      flush() {
        if (!enabled) return Promise.resolve(true);
        if (inFlightFlush) return inFlightFlush;
        queue = loadOutbox();
        if (!queue.length) return Promise.resolve(true);
        let settled = false;
        let run;
        run = (async () => {
          try {
            return await runWithFlushLock(async () => {
              let allDelivered = true;
              // Every iteration removes at least one event from the queue or stops,
              // so a poisoned event can never wedge the loop or the queue.
              let attempts = 0;
              while (attempts++ < MAX_OUTBOX) {
                queue = loadOutbox();
                if (!queue.length) break;
                const batch = queue.slice(0, 100);
                let outcome; // 'delivered' | 'retry' | { reject: index|null }
                try {
                  const headers = { 'Content-Type': 'application/json' };
                  if (config.token) headers.Authorization = 'Bearer ' + config.token;
                  const response = await fetcher(buildEventsUrl(endpoint), {
                    method: 'POST',
                    headers,
                    body: JSON.stringify({ schema: SCHEMA, events: batch }),
                    keepalive: true,
                    credentials: 'omit',
                    cache: 'no-store'
                  });
                  if (!response) {
                    outcome = 'retry';
                  } else if (response.ok) {
                    outcome = 'delivered';
                  } else if (response.status === 400 || response.status === 422) {
                    // The collector validates transactionally and names the index of
                    // the first offending event; only that event is at fault.
                    let index = null;
                    try {
                      const body = await response.json();
                      if (Number.isInteger(body && body.index) && body.index >= 0 && body.index < batch.length) {
                        index = body.index;
                      }
                    } catch (_) { index = null; }
                    outcome = { reject: index };
                  } else if (response.status === 413 || response.status === 415) {
                    outcome = { reject: null };
                  } else {
                    outcome = 'retry';
                  }
                } catch (_) {
                  outcome = 'retry';
                }
                if (outcome === 'delivered') {
                  removeBatchFromQueue(batch);
                  continue;
                }
                if (outcome === 'retry') {
                  reconcileOutbox();
                  allDelivered = false;
                  break;
                }
                if (outcome.reject === null) {
                  // Batch-level rejection: nothing in this batch is salvageable.
                  recordRejected(batch);
                  removeBatchFromQueue(batch);
                } else {
                  // Isolate the single rejected event by identity; the rest keep their order.
                  const poisoned = batch[outcome.reject];
                  if (poisoned !== undefined) {
                    recordRejected([poisoned]);
                    removeBatchFromQueue([poisoned]);
                  }
                }
              }
              if (loadOutbox().length > 0) {
                allDelivered = false;
              }
              return allDelivered;
            });
          } finally {
            settled = true;
            if (inFlightFlush === run) inFlightFlush = null;
          }
        })();
        if (!settled) inFlightFlush = run;
        return run;
      }
    };
    queue = loadOutbox();
    if (enabled && queue.length) client.schedule();
    return client;
  }

  function configure(endpoint, options) {
    const storage = safeStorage(options && options.storage);
    // Always clear previous credentials first so a quota failure on a new
    // collector can never leave an older collector's token bound to the new origin.
    remove(storage, TOKEN_KEY);
    remove(storage, TOKEN_ORIGIN_KEY);
    if (!endpoint) {
      remove(storage, ENDPOINT_KEY);
      return endpoint;
    }
    const wroteEndpoint = write(storage, ENDPOINT_KEY, endpoint);
    if (!wroteEndpoint) return endpoint;
    const origin = endpointOrigin(endpoint);
    if (options && options.token && origin) {
      const wroteToken = write(storage, TOKEN_KEY, options.token);
      const wroteOrigin = wroteToken && write(storage, TOKEN_ORIGIN_KEY, origin);
      if (!wroteToken || !wroteOrigin) {
        remove(storage, TOKEN_KEY);
        remove(storage, TOKEN_ORIGIN_KEY);
      }
    }
    return endpoint;
  }

  function automaticConfig(win) {
    const inline = win && win.DESIGN_ROUTER_TELEMETRY;
    if (inline && inline.endpoint) return inline;
    let winStorage = null;
    try { winStorage = win && win.localStorage; } catch (_) {}
    const storage = safeStorage(winStorage);
    const endpoint = storage ? read(storage, ENDPOINT_KEY) : null;
    if (!endpoint) return null;
    const storedToken = read(storage, TOKEN_KEY);
    const storedOrigin = read(storage, TOKEN_ORIGIN_KEY);
    const currentOrigin = endpointOrigin(endpoint);
    const token = (storedToken && storedOrigin && currentOrigin && storedOrigin === currentOrigin)
      ? storedToken
      : undefined;
    return {
      endpoint,
      token,
      routerVersion: ROUTER_VERSION
    };
  }

  function init(win, doc, options) {
    if (!win || !doc || !doc.addEventListener) return null;
    const overrides = options || {};
    const config = automaticConfig(win);
    if (!config && !overrides.endpoint) return null;
    const merged = { ...(config || {}), ...overrides };
    if (overrides.endpoint && !Object.prototype.hasOwnProperty.call(overrides, 'token')) {
      const baseOrigin = config && config.endpoint ? endpointOrigin(config.endpoint) : null;
      const overrideOrigin = endpointOrigin(overrides.endpoint);
      if (!baseOrigin || !overrideOrigin || baseOrigin !== overrideOrigin) {
        merged.token = undefined;
      }
    }
    const client = createClient(merged);
    if (!client.enabled) return client;

    const evaluate = () => {
      const preview = win.__minimalRouterPreview;
      if (!preview || typeof preview.getSelection !== 'function' || typeof preview.getState !== 'function') return;
      const state = preview.getState();
      const selection = preview.getSelection();
      client.trackEvaluation(selection, { route: state.route, scope: state.scope });
    };
    const later = typeof setTimeout === 'function' ? setTimeout : (fn => fn());

    // Capture phase: the board re-renders the route and function button lists
    // synchronously during the click, detaching the target before a bubble
    // listener on document can resolve closest(). During capture the target is
    // still attached, so delegation against the live tree works.
    doc.addEventListener('click', event => {
      const target = event.target;
      if (!target || typeof target.closest !== 'function') return;
      if (target.closest('#capRouteButtons [data-route]') || target.closest('#capFunctionList [data-cap]')) {
        later(evaluate, 0);
      }
    }, true);
    doc.addEventListener('change', event => {
      const target = event.target;
      if (!target) return;
      if (['minScope', 'minDomain', 'minPermit'].includes(target.id) || target.dataset?.reviewStatus) {
        later(evaluate, 0);
      }
    });
    if (typeof win.addEventListener === 'function') {
      win.addEventListener('online', () => {
        client.flush();
      });
      win.addEventListener('storage', event => {
        if (event && typeof event.key === 'string' && event.key.startsWith(OUTBOX_SHARD_PREFIX)) {
          client.reconcileOutbox();
        }
      });
    }
    if (doc.readyState === 'loading') {
      doc.addEventListener('DOMContentLoaded', () => later(evaluate, 0), { once: true });
    } else {
      later(evaluate, 0);
    }
    return client;
  }

  return {
    SCHEMA,
    ROUTER_VERSION,
    buildEvaluationEvents,
    createClient,
    configure,
    automaticConfig,
    init,
    keys: {
      ENDPOINT_KEY,
      TOKEN_KEY,
      TOKEN_ORIGIN_KEY,
      INSTANCE_KEY,
      OUTBOX_KEY,
      OUTBOX_SHARD_PREFIX,
      REJECTED_KEY
    }
  };
});
