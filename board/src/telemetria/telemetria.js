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
      const base = typeof document !== 'undefined' ? document.baseURI : undefined;
      const parsed = new URL(endpoint, base);
      parsed.pathname = parsed.pathname.replace(/\/+$/, '') + '/v1/events';
      parsed.hash = '';
      return parsed.toString();
    } catch (_) {
      return endpoint.replace(/#.*$/, '').replace(/\?.*$/, '').replace(/\/+$/, '') + '/v1/events';
    }
  }

  // SHA-256 (FIPS 180-4, §6.2). Storage keys are needed synchronously:
  // trackEvaluation must persist even if the page closes before another task.
  function sha256(text) {
    const roundConstants = [
      0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
      0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
      0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
      0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
      0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
      0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
      0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
      0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
    ];
    const state = new Uint32Array([
      0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
    ]);
    const input = new TextEncoder().encode(text);
    const padded = new Uint8Array(Math.ceil((input.length + 9) / 64) * 64);
    padded.set(input);
    padded[input.length] = 0x80;
    const view = new DataView(padded.buffer);
    const bitLength = input.length * 8;
    view.setUint32(padded.length - 8, Math.floor(bitLength / 0x100000000));
    view.setUint32(padded.length - 4, bitLength);

    const words = new Uint32Array(64);
    const rotate = (x, n) => (x >>> n) | (x << (32 - n));
    for (let offset = 0; offset < padded.length; offset += 64) {
      for (let i = 0; i < 16; i++) words[i] = view.getUint32(offset + i * 4);
      for (let i = 16; i < 64; i++) {
        const x = words[i - 15], y = words[i - 2];
        const sigma0 = rotate(x, 7) ^ rotate(x, 18) ^ (x >>> 3);
        const sigma1 = rotate(y, 17) ^ rotate(y, 19) ^ (y >>> 10);
        words[i] = words[i - 16] + sigma0 + words[i - 7] + sigma1;
      }
      let [a, b, c, d, e, f, g, h] = state;
      for (let i = 0; i < 64; i++) {
        const sum1 = rotate(e, 6) ^ rotate(e, 11) ^ rotate(e, 25);
        const choose = (e & f) ^ (~e & g);
        const t1 = h + sum1 + choose + roundConstants[i] + words[i];
        const sum0 = rotate(a, 2) ^ rotate(a, 13) ^ rotate(a, 22);
        const majority = (a & b) ^ (a & c) ^ (b & c);
        [a, b, c, d, e, f, g, h] = [(t1 + sum0 + majority) >>> 0, a, b, c, (d + t1) >>> 0, e, f, g];
      }
      const block = [a, b, c, d, e, f, g, h];
      for (let i = 0; i < state.length; i++) state[i] += block[i];
    }
    return Array.from(state, word => word.toString(16).padStart(8, '0')).join('');
  }

  function collectorKeys(endpoint) {
    const eventsUrl = buildEventsUrl(endpoint);
    // Signed inline endpoints stay in memory. Old, unscoped queues have
    // no reliable destination and remain untouched for local inspection.
    const scope = ':' + sha256(eventsUrl);
    return {
      eventsUrl,
      outbox: OUTBOX_KEY + scope,
      shardPrefix: OUTBOX_KEY + scope + ':tab.',
      entryPrefix: OUTBOX_KEY + scope + ':event.',
      rejected: REJECTED_KEY + scope
    };
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

  function listStorageKeys(storage, prefix) {
    if (!canEnumerateStorage(storage)) return [];
    const keys = [];
    try {
      if (typeof Storage !== 'undefined' && storage instanceof Storage) {
        return Object.keys(storage).filter(key => key.startsWith(prefix)).sort();
      }
      for (let i = 0; i < storage.length; i++) {
        const key = storage.key(i);
        if (typeof key === 'string' && key.startsWith(prefix)) {
          keys.push(key);
        }
      }
    } catch (_) {
      return [];
    }
    keys.sort();
    return keys;
  }

  function eventSignature(item) {
    try {
      return JSON.stringify(item);
    } catch (_) {
      return null;
    }
  }

  function appendUnique(base, additions, max) {
    const merged = base.slice();
    const seen = new Set(merged.map(item => item && item.event_id).filter(Boolean));
    const seenSigs = new Set();
    for (const item of merged) {
      if (item && !item.event_id) {
        const sig = eventSignature(item);
        if (sig) seenSigs.add(sig);
      }
    }
    for (const item of additions) {
      const id = item && item.event_id;
      if (id) {
        if (seen.has(id)) continue;
        seen.add(id);
      } else if (item) {
        const sig = eventSignature(item);
        if (sig) {
          if (seenSigs.has(sig)) continue;
          seenSigs.add(sig);
        }
      }
      merged.push(item);
    }
    return merged.length > max ? merged.slice(-max) : merged;
  }

  function filterOutBatch(list, items) {
    const refs = new Set(items);
    const ids = new Set(items.map(item => item && item.event_id).filter(Boolean));
    const sigs = new Set();
    for (const item of items) {
      if (!item || item.event_id) continue;
      const sig = eventSignature(item);
      if (sig) sigs.add(sig);
    }
    return list.filter(item => {
      if (refs.has(item)) return false;
      if (item && item.event_id && ids.has(item.event_id)) return false;
      if (item && !item.event_id && sigs.size) {
        const sig = eventSignature(item);
        if (sig && sigs.has(sig)) return false;
      }
      return true;
    });
  }

  function runWithFlushLock(name, fn) {
    try {
      if (typeof navigator !== 'undefined' && navigator.locks && typeof navigator.locks.request === 'function') {
        return navigator.locks.request(name, fn);
      }
    } catch (_) {}
    return fn();
  }

  async function confirmed(response, count) {
    if (response.status !== 202) return false;
    const body = await response.json();
    return body && body.schema === SCHEMA &&
      Number.isSafeInteger(body.accepted) && body.accepted >= 0 &&
      Number.isSafeInteger(body.duplicates) && body.duplicates >= 0 &&
      body.accepted + body.duplicates === count;
  }

  function retryAfter(response) {
    const header = response.headers && response.headers.get('Retry-After');
    const delay = header && /^\d+$/.test(header) ? Number(header) * 1000 : Date.parse(header) - Date.now();
    return Number.isFinite(delay) ? Math.max(1000, delay) : 60000;
  }

  function createClient(options, persisted = {}) {
    const config = options || {};
    const storage = safeStorage(config.storage);
    const fetcher = config.fetch || (typeof fetch === 'function' ? fetch : null);
    const hasEndpointOption = Object.prototype.hasOwnProperty.call(config, 'endpoint');
    const endpoint = hasEndpointOption ? (config.endpoint || null) : (storage ? read(storage, ENDPOINT_KEY) : null);
    const enabled = Boolean(config.enabled !== false && endpoint && fetcher);
    const followsStorage = persisted.endpoint ?? !hasEndpointOption;
    const active = () => enabled && (!followsStorage || read(storage, ENDPOINT_KEY) === endpoint);
    const { eventsUrl, outbox, shardPrefix, entryPrefix, rejected: rejectedKey } = collectorKeys(endpoint);
    const enumerable = enabled && canEnumerateStorage(storage);

    // Delivered or permanently rejected event identities kept in memory so a
    // full/unwritable localStorage can never resurrect and resend them—even for
    // malformed stored entries lacking event_id that deserialize as new objects.
    const retiredIds = new Set();
    const retiredSignatures = new Set();
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
        } else {
          const sig = eventSignature(item);
          if (sig) {
            retiredSignatures.add(sig);
            if (retiredSignatures.size > MAX_RETIRED) {
              const oldest = retiredSignatures.values().next().value;
              retiredSignatures.delete(oldest);
            }
          }
        }
      }
    };
    const excludeRetired = (list) => list.filter(item => {
      if (!item) return false;
      if (typeof item === 'object' && retiredRefs.has(item)) return false;
      if (item.event_id && retiredIds.has(item.event_id)) return false;
      if (!item.event_id && retiredSignatures.size) {
        const sig = eventSignature(item);
        if (sig && retiredSignatures.has(sig)) return false;
      }
      return true;
    });

    let queue = [];
    let queueUnsynced = false;
    // Failed synchronous writes stay with the producer until a send or a
    // later write succeeds. Stored events each have one immutable key.
    const volatileEntries = new Map();
    // Events the collector rejected permanently. Kept for inspection so a
    // rejection is never a silent loss; never retried.
    let rejected = enabled ? readList(storage, rejectedKey, MAX_REJECTED) || [] : [];
    let rejectedUnsynced = false;

    let instanceId = enabled ? config.instanceId || read(storage, INSTANCE_KEY) : null;
    if (enabled && !instanceId) {
      instanceId = uuid();
      write(storage, INSTANCE_KEY, instanceId);
    }
    let flushTimer = null;
    let inFlightFlush = null;

    let retryAt = 0;
    const cancelTimer = () => {
      if (flushTimer !== null) clearTimeout(flushTimer);
      flushTimer = null;
    };

    function readLegacy(keys) {
      const stored = readList(storage, outbox, MAX_OUTBOX) || [];
      // Older boards used a mirror plus per-tab shards. At a full mirror,
      // shard-only records are the first candidates for eviction.
      let shards = [];
      for (const key of keys) {
        shards = appendUnique(shards, readList(storage, key, MAX_OUTBOX) || [], Infinity);
      }
      const extra = filterOutBatch(shards, stored);
      return excludeRetired(stored.length === MAX_OUTBOX ? extra.concat(stored) : stored.concat(extra));
    }

    function removeLegacy(keys, items) {
      if (!items.length) return;
      for (const key of [outbox, ...keys]) {
        const stored = readList(storage, key, MAX_OUTBOX);
        if (!stored || !stored.length) continue;
        const remaining = filterOutBatch(stored, items);
        if (remaining.length === stored.length) continue;
        if (remaining.length || key === outbox) write(storage, key, JSON.stringify(remaining));
        else remove(storage, key);
      }
    }

    function snapshot() {
      const keys = listStorageKeys(storage, outbox + ':');
      const legacyKeys = keys.filter(key => key.startsWith(shardPrefix));
      let legacy = readLegacy(legacyKeys);
      const entries = keys.filter(key => key.startsWith(entryPrefix) && !retiredIds.has(entryId(key)));
      const excess = legacy.length + entries.length - MAX_OUTBOX;
      if (excess > 0) {
        let entryCount = Math.min(entries.length, excess);
        let dropped = [];
        if (legacy.length) {
          // Legacy tabs still write while a newer tab is open. Compare the
          // occurrence times of the two formats. Within an immutable queue,
          // the key already records capture order (even on clock rollback).
          const oldest = legacy.slice().sort((a, b) => eventTime(a) - eventTime(b));
          let fromLegacy = 0;
          entryCount = 0;
          while (fromLegacy + entryCount < excess) {
            const key = entries[entryCount];
            if (!key || (fromLegacy < oldest.length && eventTime(oldest[fromLegacy]) < storedTime(key))) {
              fromLegacy++;
            } else {
              entryCount++;
            }
          }
          dropped = oldest.slice(0, fromLegacy);
        }
        removeLegacy(legacyKeys, dropped);
        markRetired(dropped);
        legacy = filterOutBatch(legacy, dropped);
        for (const key of entries.splice(0, entryCount)) {
          markRetired([{ event_id: entryId(key) }]);
          remove(storage, key);
        }
      }
      // RAM-only writes can use free event slots, but cannot evict a durable
      // record: if the producer closes, its in-memory replacement vanishes.
      const spare = MAX_OUTBOX - legacy.length - entries.length;
      if (volatileEntries.size > spare) {
        for (const key of [...volatileEntries.keys()].slice(spare)) volatileEntries.delete(key);
      }
      if (volatileEntries.size) {
        entries.push(...volatileEntries.keys());
        entries.sort();
      }
      return { legacy, entries };
    }

    function eventTime(event) {
      const stamp = event && Date.parse(event.occurred_at);
      return Number.isFinite(stamp) ? stamp : -Infinity;
    }

    function storedTime(key) {
      try { return eventTime(JSON.parse(read(storage, key))); } catch (_) { return -Infinity; }
    }

    function loadOutbox(limit = 100) {
      if (!enumerable) {
        const stored = readList(storage, outbox, MAX_OUTBOX);
        let pending = stored ?? queue;
        if (stored && queueUnsynced) pending = appendUnique(stored, queue, MAX_OUTBOX);
        return excludeRetired(pending).slice(0, limit);
      }
      const { legacy, entries } = snapshot();
      const pending = legacy.slice(0, limit);
      for (const key of entries) {
        if (pending.length >= limit) break;
        let event = volatileEntries.get(key);
        if (!event) {
          const raw = read(storage, key);
          if (raw === null) continue; // Another tab already removed it.
          try { event = JSON.parse(raw); } catch (_) {}
        }
        if (!event || event.event_id !== entryId(key)) {
          // Locally corrupt bytes cannot be acknowledged by the collector.
          // Keep a diagnostic, without copying arbitrary data from storage.
          const diagnostic = { event_id: entryId(key), error: 'INVALID_STORED_EVENT' };
          recordRejected([diagnostic]);
          markRetired([diagnostic]);
          remove(storage, key);
          continue;
        }
        pending.push(event);
      }
      return pending;
    }

    const loadRejected = () => {
      const stored = readList(storage, rejectedKey, MAX_REJECTED);
      if (stored === null) return rejected;
      return rejectedUnsynced ? appendUnique(stored, rejected, MAX_REJECTED) : stored;
    };

    const saveOutbox = (next) => {
      const cleaned = excludeRetired(next);
      queue = cleaned.length > MAX_OUTBOX ? cleaned.slice(-MAX_OUTBOX) : cleaned;
      if (storage) {
        queueUnsynced = !write(storage, outbox, JSON.stringify(queue));
      }
    };

    const saveRejected = (next) => {
      rejected = next.length > MAX_REJECTED ? next.slice(-MAX_REJECTED) : next;
      if (storage) {
        rejectedUnsynced = !write(storage, rejectedKey, JSON.stringify(rejected));
      }
    };

    function entryId(key) {
      return key.slice(key.lastIndexOf('.') + 1);
    }

    function persistVolatile() {
      for (const [key, event] of volatileEntries) {
        // Another tab may send this prefix immediately. Never publish a
        // skill.selected if its preceding router.invoked failed to persist.
        if (!write(storage, key, JSON.stringify(event))) break;
        volatileEntries.delete(key);
      }
    }

    function enqueue(events) {
      if (!enumerable) {
        saveOutbox(appendUnique(loadOutbox(MAX_OUTBOX), events, MAX_OUTBOX));
        return;
      }
      // A sortable batch prefix preserves evaluation order, including events
      // generated in the same millisecond. Concurrent tabs never overwrite
      // one another's payload, even without the Web Locks API.
      const fresh = events.slice(-MAX_OUTBOX);
      const { legacy, entries } = snapshot();
      const lastKey = entries[entries.length - 1];
      const lastOrder = lastKey ? Number(lastKey.slice(entryPrefix.length, entryPrefix.length + 16)) : 0;
      const order = String(Math.max(Date.now(), lastOrder + 1)).padStart(16, '0');
      const prefix = entryPrefix + order + '.' + fresh[0].evaluation_id + '.';
      for (let i = 0; i < fresh.length; i++) {
        const key = prefix + String(i).padStart(8, '0') + '.' + fresh[i].event_id;
        volatileEntries.set(key, fresh[i]);
      }
      persistVolatile();
      // Admit first. Only successful writes can displace older persisted
      // entries. The same reconciliation runs on reload after interruption.
      if (legacy.length + entries.length + fresh.length > MAX_OUTBOX) snapshot();
    }

    let reconciliationPending = false;
    const reconcileOutbox = (changedKey) => {
      if (!active()) {
        cancelTimer();
        retryAt = 0;
      } else if (enumerable && changedKey && changedKey.startsWith(outbox + ':') && !reconciliationPending) {
        reconciliationPending = true;
        setTimeout(() => {
          reconciliationPending = false;
          if (active()) snapshot();
        }, 0);
      }
    };

    const removeBatchFromQueue = (items) => {
      markRetired(items);
      if (enumerable) {
        const keys = listStorageKeys(storage, outbox + ':');
        removeLegacy(keys.filter(key => key.startsWith(shardPrefix)), items);
        const ids = new Set(items.map(item => item && item.event_id));
        for (const key of [...keys, ...volatileEntries.keys()]) {
          if (key.startsWith(entryPrefix) && ids.has(entryId(key))) {
            volatileEntries.delete(key);
            remove(storage, key);
          }
        }
      } else {
        saveOutbox(loadOutbox(MAX_OUTBOX));
      }
      if (rejectedUnsynced) saveRejected(loadRejected());
    };

    const recordRejected = (items) => {
      const current = loadRejected();
      saveRejected(appendUnique(current, items, MAX_REJECTED));
    };

    const client = {
      get enabled() { return active(); },
      endpoint,
      instanceId,
      reconcileOutbox,
      trackEvaluation(selection, context) {
        if (!active()) return [];
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
        enqueue(events);
        client.schedule();
        return events;
      },
      schedule() {
        if (!active() || flushTimer !== null || typeof setTimeout !== 'function') return;
        const delay = retryAt ? Math.max(1, retryAt - Date.now()) : 120;
        flushTimer = setTimeout(() => { flushTimer = null; client.flush(); }, Math.min(delay, 2147483647));
      },
      flush() {
        if (!active()) {
          cancelTimer();
          return Promise.resolve(true);
        }
        if (Date.now() < retryAt) {
          client.schedule();
          return Promise.resolve(false);
        }
        retryAt = 0;
        persistVolatile();
        if (inFlightFlush) return inFlightFlush;
        if (rejectedUnsynced) {
          saveRejected(loadRejected());
        }
        if (!loadOutbox(1).length) return Promise.resolve(true);
        let settled = false;
        let run;
        run = (async () => {
          try {
            return await runWithFlushLock(outbox, async () => {
              let allDelivered = true;
              // Every iteration removes at least one event from the queue or stops,
              // so a poisoned event can never wedge the loop or the queue.
              let attempts = 0;
              while (attempts++ < MAX_OUTBOX) {
                if (!active()) break;
                const batch = loadOutbox();
                if (!batch.length) break;
                let outcome; // 'delivered' | 'retry' | { reject: index|null }
                try {
                  const headers = { 'Content-Type': 'application/json' };
                  const token = persisted.token ? storedTokenFor(storage, endpoint) : config.token;
                  if (token) headers.Authorization = 'Bearer ' + token;
                  const response = await fetcher(eventsUrl, {
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
                    outcome = await confirmed(response, batch.length) ? 'delivered' : 'retry';
                  } else if (response.status === 429) {
                    retryAt = Date.now() + retryAfter(response);
                    cancelTimer();
                    client.schedule();
                    outcome = 'retry';
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
              if (loadOutbox(1).length > 0) {
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
    if (active() && loadOutbox(1).length) client.schedule();
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

  function storedTokenFor(storage, endpoint) {
    const storedToken = read(storage, TOKEN_KEY);
    const storedOrigin = read(storage, TOKEN_ORIGIN_KEY);
    const currentOrigin = endpointOrigin(endpoint);
    return (storedToken && storedOrigin && currentOrigin && storedOrigin === currentOrigin)
      ? storedToken
      : undefined;
  }

  function automaticConfig(win) {
    const inline = win && win.DESIGN_ROUTER_TELEMETRY;
    if (inline && inline.endpoint) return inline;
    let winStorage = null;
    try { winStorage = win && win.localStorage; } catch (_) {}
    const storage = safeStorage(winStorage);
    const endpoint = storage ? read(storage, ENDPOINT_KEY) : null;
    if (!endpoint) return null;
    return {
      endpoint,
      token: storedTokenFor(storage, endpoint),
      routerVersion: ROUTER_VERSION
    };
  }

  function init(win, doc, options) {
    if (!win || !doc || !doc.addEventListener) return null;
    const overrides = options || {};
    const config = automaticConfig(win);
    if (!config && !overrides.endpoint) return null;
    const merged = { ...(config || {}), ...overrides };
    const hasOverrideEndpoint = Object.prototype.hasOwnProperty.call(overrides, 'endpoint');
    if (hasOverrideEndpoint && !Object.prototype.hasOwnProperty.call(overrides, 'token')) {
      if (!overrides.endpoint) {
        merged.endpoint = null;
        merged.token = undefined;
      } else {
        const baseOrigin = config && config.endpoint ? endpointOrigin(config.endpoint) : null;
        const overrideOrigin = endpointOrigin(overrides.endpoint);
        if (!baseOrigin || !overrideOrigin || baseOrigin !== overrideOrigin) {
          merged.token = undefined;
        }
      }
    }
    const followsStorage = !hasOverrideEndpoint && !(win.DESIGN_ROUTER_TELEMETRY && win.DESIGN_ROUTER_TELEMETRY.endpoint);
    if (followsStorage && !merged.storage) {
      try { merged.storage = win.localStorage; } catch (_) {}
    }
    const client = createClient(merged, {
      endpoint: followsStorage,
      token: followsStorage && !Object.prototype.hasOwnProperty.call(overrides, 'token')
    });
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
        if (event && (event.key === null || typeof event.key === 'string')) {
          client.reconcileOutbox(event.key);
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
      REJECTED_KEY,
      forEndpoint: collectorKeys
    }
  };
});
