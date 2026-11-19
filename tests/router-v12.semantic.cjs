'use strict';

// Offline contract runner. It executes the assembled inline router in Node.
// Only routing, serialization, and generated markup are evidence from this runner.
const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const file = process.argv[2] || path.join(__dirname, '../release/design-router-pizarra-v1.2.html');
const scripts = [...readFileSync(file, 'utf8').matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)];
const inlineJson = id => scripts.find(([, attrs]) => attrs.includes(`id="${id}"`))[2];
const router = scripts.find(([, , source]) => source.includes('window.__minimalRouterPreview'))[2];
const policy = JSON.parse(inlineJson('minRouteData'));
const inventory = JSON.parse(inlineJson('capabilityMapData'));

function board() {
  let route = 'tipografia';
  let active = 'type-choice';
  let blob;
  let filename;
  const elements = new Map();
  class Element {
    constructor(id) {
      this.id = id;
      this.listeners = new Map();
      this.children = new Map();
      this.dataset = {};
      this.style = {};
      this.classList = { add() {}, toggle() {} };
      this.textContent = '';
      this.innerHTML = '';
      this.hidden = false;
      this.value = '';
      this.valueWrites = 0;
    }
    set value(next) {
      this.valueWrites++;
      this.currentValue = next;
    }
    get value() { return this.currentValue; }
    addEventListener(type, listener) {
      this.listeners.set(type, listener);
    }
    hasAttribute() { return false; }
    setAttribute() {}
    removeAttribute() {}
    append() {}
    contains() { return false; }
    click() { filename = this.download; }
    remove() {}
    insertAdjacentHTML(_position, markup) { this.innerHTML += markup; }
    get firstElementChild() { return this.querySelectorAll('[data-review-owner]')[0] || null; }
    querySelector(selector) {
      if (this.id === 'capRouteButtons') return { dataset: { route } };
      if (this.id === 'capFunctionList') return { dataset: { cap: active } };
      if (!this.children.has(selector)) this.children.set(selector, new Element(selector));
      return this.children.get(selector);
    }
    querySelectorAll(selector) {
      if (this.id !== 'minCoverage' || !this.innerHTML || selector !== '[data-review-owner]') return [];
      return policy.reviewable_domains.map(owner => {
        const row = this.querySelector(owner);
        row.dataset.reviewOwner = owner;
        return row;
      });
    }
  }

  const el = id => {
    if (!elements.has(id)) elements.set(id, new Element(id));
    return elements.get(id);
  };
  for (const id of ['capabilityMapData', 'minRouteData']) el(id).textContent = inlineJson(id);

  const context = {
    Blob,
    document: {
      readyState: 'complete',
      getElementById: el,
      createElement: id => new Element(id),
      body: new Element('body')
    },
    window: {},
    URL: {
      createObjectURL(value) { blob = value; return 'blob:qa'; },
      revokeObjectURL() {}
    },
    setTimeout() {},
    queueMicrotask
  };
  vm.runInNewContext(router, context, { filename: file });

  const trigger = (id, type, target) => el(id).listeners.get(type)({ target });
  return {
    el,
    state: () => JSON.parse(JSON.stringify(context.window.__minimalRouterPreview.getState())),
    route(value) {
      route = value;
      active = inventory.routes.find(item => item.id === value).functions[0];
      trigger('capRouteButtons', 'click', { closest: () => true });
    },
    function(value) {
      active = value;
      trigger('capFunctionList', 'click', { closest: () => true });
    },
    scope(value) { trigger('minScope', 'change', { value }); },
    domain(value) { trigger('minDomain', 'change', { value }); },
    permit(value) { trigger('minPermit', 'change', { value }); },
    status(owner, value) {
      trigger('minCoverage', 'change', { value, dataset: { reviewStatus: owner } });
    },
    reason(owner, value) {
      const input = el('minCoverage').querySelector(owner).querySelector('input');
      input.value = value;
      trigger('minCoverage', 'input', { value, dataset: { reviewReason: owner } });
    },
    async download() {
      trigger('minExport', 'click');
      return { filename, doc: JSON.parse(await blob.text()) };
    }
  };
}

const tests = {
  'Base: fuente G2, microtipografía G3 y escenario G2 + G3': async b => {
    for (const [name, owner] of [['type-choice', 'G2'], ['type-micro', 'G3']]) {
      b.function(name);
      const { doc } = await b.download();
      assert.deepEqual(doc.selected_functions, [name]);
      assert.deepEqual(doc.proposed_owners, [owner]);
      assert.deepEqual(doc.source_pins.map(pin => pin.id), [owner]);
      assert.equal(doc.mode_status, 'ORIENTATION_ONLY');
      assert.equal(doc.human_gate, 'NOT_APPROVED');
      assert.deepEqual(doc.skills_executed, []);
      assert.ok(Object.values(doc.applicability).every(item => !item.reviewed && !item.verified && !item.approved));
    }
    b.scope('scenario');
    assert.deepEqual(b.state().owners.sort(), ['G2', 'G3']);
    b.route('color');
    assert.deepEqual(b.state().owners, ['G4']);
  },
  'SEM-01, visual QA tipográfica de función única': b => {
    b.route('auditoria');
    b.domain('G2');
    assert.deepEqual(b.state().functions, ['visual-qa']);
    assert.deepEqual(b.state().owners, ['G2']);
  },
  'SEM-02, escenario focalizado G5 y G2 sin especialista de movimiento': b => {
    b.route('auditoria');
    b.scope('scenario');
    for (const owner of ['G5', 'G2']) {
      b.domain(owner);
      assert.deepEqual(b.state().owners, [owner]);
      assert.ok(!b.state().functions.includes('motion-review'));
      assert.doesNotMatch(b.el('minSupport').innerHTML, /review-animations/i);
    }
    b.domain('G7');
    assert.deepEqual(b.state().owners, ['G7']);
    assert.ok(b.state().functions.includes('motion-review'));
  },
  'STATE-03, N/A requerido y razón vacía marcados en borrador': async b => {
    b.route('auditoria');
    b.domain('G2');
    b.status('G4', 'not_applicable');
    b.status('G2', 'not_applicable');
    b.reason('G2', 'Razón registrada');
    const { doc, filename } = await b.download();
    assert.equal(doc.applicability.G4.reason, '');
    assert.equal(doc.applicability.G2.reason, 'Razón registrada');
    assert.equal(doc.validation.valid, false);
    assert.equal(doc.completeness.complete, false);
    assert.deepEqual(doc.validation.errors.map(error => [error.code, error.domain]), [
      ['REQUIRED_DOMAIN_NOT_APPLICABLE', 'G2'], ['MISSING_JUSTIFICATION', 'G4']
    ]);
    assert.equal(doc.status, 'DRAFT');
    assert.match(filename, /-borrador\.json$/);
  },
  'TRACE-04, dominio, versión y SHA-256 verificable': async b => {
    b.route('auditoria');
    b.domain('G2');
    const { doc } = await b.download();
    assert.equal(doc.schema, 'design-router-minimal-selection-export/1.2');
    assert.equal(doc.selected_route, 'auditoria');
    assert.equal(doc.selected_scope, 'function');
    assert.equal(doc.selected_domain, 'G2');
    assert.ok(doc.policy_version);
    assert.equal(doc.policy_hash, createHash('sha256').update(inlineJson('minRouteData').trim()).digest('hex'));
    assert.equal(doc.validation.valid, true);
    assert.equal(doc.completeness.complete, false);
  },
  'UX-05 estructural: la fila permanece y el código no reescribe el texto editado': b => {
    const coverage = b.el('minCoverage');
    const initialMarkup = coverage.innerHTML;
    const row = coverage.querySelector('G4');
    const select = row.querySelector('select');
    const input = row.querySelector('input');
    assert.ok(input.hidden);
    b.status('G4', 'not_applicable');
    assert.equal(input.hidden, false);
    assert.equal(select.value, 'not_applicable');
    const writes = input.valueWrites;
    b.reason('G4', 'Cambio');
    assert.equal(input.valueWrites, writes + 1);
    assert.equal(coverage.innerHTML, initialMarkup);
    assert.equal(coverage.querySelector('G4').querySelector('input'), input);
    assert.equal(coverage.querySelector('G4').querySelector('select'), select);
    b.status('G4', 'pending');
    assert.equal(input.hidden, true);
  },
  'Sin dominio e incompatibilidad explícita': async b => {
    b.route('auditoria');
    for (const scope of ['function', 'scenario']) {
      b.scope(scope);
      const { doc } = await b.download();
      assert.equal(doc.selected_domain, null);
      assert.deepEqual(doc.proposed_owners, []);
      assert.deepEqual(doc.selected_functions, []);
      assert.equal(doc.validation.valid, false);
      assert.equal(doc.validation.errors[0].code, 'AUDIT_DOMAIN_REQUIRED');
    }
    b.scope('function');
    b.function('motion-review');
    b.domain('G5');
    const { doc } = await b.download();
    assert.equal(doc.selected_domain, 'G5');
    assert.deepEqual(doc.proposed_owners, []);
    assert.equal(doc.validation.errors[0].code, 'AUDIT_FUNCTION_OUTSIDE_DOMAIN');
  },
  'Ida y vuelta conserva revisiones por dominio, función y alcance': async b => {
    b.route('auditoria');
    b.domain('G2');
    b.status('G4', 'not_applicable');
    b.reason('G4', 'Tipografía <&>');
    b.domain('G5');
    assert.equal((await b.download()).doc.applicability.G4.applicability, 'pending');
    b.status('G4', 'not_applicable');
    b.reason('G4', 'Layout');
    b.scope('scenario');
    assert.equal((await b.download()).doc.selected_domain, null);
    b.domain('G7');
    b.scope('function');
    assert.equal((await b.download()).doc.applicability.G4.reason, 'Layout');
    b.domain('G2');
    assert.equal((await b.download()).doc.applicability.G4.reason, 'Tipografía <&>');
    b.route('tipografia');
    b.route('auditoria');
    assert.equal((await b.download()).doc.selected_domain, 'G2');
    assert.equal((await b.download()).doc.applicability.G4.reason, 'Tipografía <&>');
  },
  'POLICY-08, permiso de auditoría resistente al cambio de ruta y a eventos': async b => {
    b.permit('sandbox');
    b.route('auditoria');
    b.domain('G5');
    assert.equal(b.el('minPermit').querySelector('option[value="sandbox"]').disabled, true);
    b.permit('sandbox');
    assert.equal((await b.download()).doc.simulated_permission, 'read');
    b.route('tipografia');
    assert.equal((await b.download()).doc.simulated_permission, 'read');
  },
  'VIS-07, todos los apoyos de escritura y de consulta en componentes y movimiento': b => {
    for (const key of ['componentes', 'movimiento']) {
      b.route(key);
      b.scope('scenario');
      const functions = inventory.routes.find(route => route.id === key).functions;
      const contributions = inventory.skills.flatMap(skill => skill.contributions)
        .filter(contribution => functions.includes(contribution.function_id));
      const write = contributions.filter(contribution => policy.writes.includes(contribution.effect)).length;
      const read = contributions.filter(contribution => !policy.writes.includes(contribution.effect)
        && !['externo', 'excluir'].includes(contribution.effect)).length;
      assert.ok(write > 0 && read > 0);
      const markup = b.el('minSupport').innerHTML;
      assert.equal((markup.match(/class="min-support-item is-write"/g) || []).length, write);
      assert.equal((markup.match(/class="min-support-item "/g) || []).length, read);
    }
  },
  'Propuesta válida y completa conserva el gate humano': async b => {
    for (const owner of policy.reviewable_domains) b.status(owner, 'applies');
    const { doc, filename } = await b.download();
    assert.equal(doc.validation.valid, true);
    assert.equal(doc.completeness.complete, true);
    assert.equal(doc.status, 'PROPOSAL');
    assert.doesNotMatch(filename, /-borrador\.json$/);
    assert.equal(doc.human_gate, 'NOT_APPROVED');
    assert.deepEqual(doc.skills_executed, []);
  }
};

(async () => {
  let failures = 0;
  for (const [name, test] of Object.entries(tests)) {
    try {
      await test(board());
      console.log(`PASS ${name}`);
    } catch (error) {
      failures++;
      console.error(`FAIL ${name}\n${error.stack}`);
    }
  }
  console.log(`${Object.keys(tests).length - failures}/${Object.keys(tests).length} casos de contrato aprobados`);
  process.exitCode = failures === 0 ? 0 : 1;
})();
