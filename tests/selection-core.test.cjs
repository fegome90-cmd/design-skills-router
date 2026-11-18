'use strict';

const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const { copyFileSync, mkdtempSync, rmSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join } = require('node:path');
const { after, before, test } = require('node:test');
const baseline = require('./fixtures/selection-g5.json');

const root = join(__dirname, '..');
let isolatedDirectory;
let resolveSelection;
let catalog;
let policy;

before(() => {
  isolatedDirectory = mkdtempSync(join(tmpdir(), 'design-router-selection-'));
  const files = {
    'selection-core.cjs': 'board/src/simulador/selection-core.cjs',
    'policy.json': 'board/src/simulador/politica.json',
    'catalog.json': 'board/src/mapa-funcional/datos.json'
  };
  for (const [name, source] of Object.entries(files)) {
    copyFileSync(join(root, source), join(isolatedDirectory, name));
  }
  ({ resolveSelection } = require(join(isolatedDirectory, 'selection-core.cjs')));
  catalog = require(join(isolatedDirectory, 'catalog.json'));
  policy = require(join(isolatedDirectory, 'policy.json'));
});

after(() => {
  if (isolatedDirectory) rmSync(isolatedDirectory, { recursive: true, force: true });
});

test('the isolated core reproduces the legacy Chromium G5 audit scenario', () => {
  const output = execFileSync(process.execPath, ['-e', `
    const { resolveSelection } = require('./selection-core.cjs');
    const catalog = require('./catalog.json');
    const policy = require('./policy.json');
    const result = resolveSelection({
      route: 'auditoria', scope: 'scenario', domain: 'G5', permit: 'sandbox'
    }, { catalog, policy });
    process.stdout.write(JSON.stringify(result));
  `], { cwd: isolatedDirectory, encoding: 'utf8' });
  const result = JSON.parse(output);
  const { document, permission, support, nodesByFunction } = baseline;

  assert.deepEqual(result.requestedFunctions, document.requested_functions);
  assert.deepEqual(result.selectedFunctions, document.selected_functions);
  assert.deepEqual(result.owners, document.proposed_owners);
  assert.equal(result.domain, document.selected_domain);
  assert.deepEqual(result.domainOptions, ['G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7']);
  assert.equal(result.showDomain, true);
  assert.equal(result.domainRequired, true);
  assert.equal(result.permit, permission.value);
  assert.equal(result.audit, true);
  assert.deepEqual(result.profile, policy.profiles.auditoria);
  assert.equal(result.profile.mode, document.mode);
  assert.deepEqual(result.profile.prereqs, document.prerequisites);
  assert.deepEqual(result.nodesByFunction, nodesByFunction);
  assert.deepEqual(result.assessments, document.applicability);
  assert.deepEqual(result.counts, { applies: 1, pending: 6, notApplicable: 0 });
  assert.deepEqual(result.validation, document.validation);
  assert.deepEqual(result.completeness, document.completeness);
  for (const group of support.groups) {
    const contributions = result.support[group.id];
    const { skill, ...breakUi } = contributions.find(item => item.skill.name === 'break-ui');
    assert.deepEqual(contributions.map(item => item.skill.name), group.names);
    assert.deepEqual(breakUi, group.breakUi);
  }
});

test('the audit uses its first function by default and requires a valid domain', () => {
  const cases = [
    ['function', '', ['visual-qa']],
    ['scenario', 'G0', ['visual-qa', 'accessibility', 'stress-test', 'motion-review']]
  ];
  for (const [scope, domain, requested] of cases) {
    const result = resolveSelection({ route: 'auditoria', scope, domain }, { catalog, policy });

    assert.deepEqual(result.requestedFunctions, requested);
    assert.equal(result.domain, '');
    assert.equal(result.domainRequired, true);
    assert.deepEqual(result.selectedFunctions, []);
    assert.deepEqual(result.owners, []);
    assert.deepEqual(result.validation, {
      valid: false,
      errors: [{ code: 'AUDIT_DOMAIN_REQUIRED', message: 'Falta delimitar el dominio de la auditoría.' }]
    });
    assert.equal(result.completeness.complete, false);
  }
});

test('visual QA qualifies for G2 through the audit override', () => {
  const result = resolveSelection({ route: 'auditoria', functionId: 'visual-qa', domain: 'G2' }, { catalog, policy });

  assert.deepEqual(result.selectedFunctions, ['visual-qa']);
  assert.deepEqual(result.owners, ['G2']);
  assert.deepEqual(result.nodesByFunction, { 'visual-qa': ['QA01'] });
  assert.equal(result.validation.valid, true);
});

test('a G5 audit keeps an incompatible motion request visible in validation', () => {
  const result = resolveSelection({ route: 'auditoria', functionId: 'motion-review', domain: 'G5' }, { catalog, policy });

  assert.equal(result.domain, 'G5');
  assert.deepEqual(result.requestedFunctions, ['motion-review']);
  assert.deepEqual(result.selectedFunctions, []);
  assert.deepEqual(result.owners, []);
  assert.deepEqual(result.support, { read: [], write: [] });
  assert.deepEqual(result.nodesByFunction, {});
  assert.deepEqual(result.validation, {
    valid: false,
    errors: [{ code: 'AUDIT_FUNCTION_OUTSIDE_DOMAIN', message: 'La función seleccionada queda fuera del dominio de auditoría.' }]
  });
});

test('review decisions apply only to the records supplied for a selection', () => {
  const input = Object.freeze({
    route: 'auditoria', functionId: 'visual-qa', domain: 'G2',
    reviews: Object.freeze({
      G1: Object.freeze({ status: 'not_applicable', reason: '  Fuera de alcance  ' }),
      G2: Object.freeze({ status: 'not_applicable', reason: 'Razón registrada' }),
      G4: Object.freeze({ status: 'not_applicable', reason: ' ' })
    })
  });
  const dependencies = { catalog, policy };
  const reviewed = resolveSelection(input, dependencies);

  assert.deepEqual(reviewed.assessments.G1, {
    applicability: 'not_applicable', reason: '  Fuera de alcance  ', reviewed: false, verified: false, approved: false
  });
  assert.deepEqual(reviewed.counts, { applies: 0, pending: 4, notApplicable: 1 });
  assert.deepEqual(reviewed.validation, {
    valid: false,
    errors: [
      {
        code: 'REQUIRED_DOMAIN_NOT_APPLICABLE', domain: 'G2',
        message: 'Contradicción: el dominio pertenece a la ruta propuesta.'
      },
      { code: 'MISSING_JUSTIFICATION', domain: 'G4', message: 'Falta justificar por qué no aplica.' }
    ]
  });
  assert.deepEqual(reviewed.completeness, { complete: false, pending_domains: ['G3', 'G5', 'G6', 'G7'] });

  const other = resolveSelection({ route: 'auditoria', functionId: 'visual-qa', domain: 'G5' }, dependencies);
  assert.equal(other.assessments.G1.applicability, 'pending');
  assert.equal(other.assessments.G1.reason, '');
  assert.equal(other.assessments.G2.applicability, 'pending');
  assert.equal(other.assessments.G5.applicability, 'applies');
  assert.deepEqual(resolveSelection(input, dependencies), reviewed);
});

test('an audit-mode profile constrains sandbox while the actual route controls owner filtering', () => {
  const input = { route: 'tipografia', scope: 'scenario', permit: 'sandbox' };
  const normal = resolveSelection(input, { catalog, policy });
  const auditProfile = { ...policy.profiles.tipografia, mode: 'Audit · read-only' };
  const withAuditProfile = { ...policy, profiles: { ...policy.profiles, tipografia: auditProfile } };
  const constrained = resolveSelection(input, { catalog, policy: withAuditProfile });

  assert.equal(normal.permit, 'sandbox');
  assert.equal(normal.audit, false);
  assert.equal(constrained.permit, 'read');
  assert.equal(constrained.audit, true);
  assert.equal(constrained.profile, auditProfile);
  assert.deepEqual(constrained.selectedFunctions, ['type-choice', 'type-micro', 'accessibility']);
  assert.deepEqual(constrained.owners, ['G2', 'G3']);
  assert.equal(constrained.domainRequired, false);
});

test('typography accessibility uses its contextual owner and accepts another reviewable domain', () => {
  const input = { route: 'tipografia', functionId: 'accessibility' };
  const implicit = resolveSelection(input, { catalog, policy });
  const explicit = resolveSelection({ ...input, domain: 'G4' }, { catalog, policy });
  const hidden = resolveSelection({ ...input, functionId: 'type-choice', domain: 'G4' }, { catalog, policy });

  assert.equal(implicit.showDomain, true);
  assert.equal(implicit.domainRequired, false);
  assert.deepEqual(implicit.domainOptions, ['G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7']);
  assert.deepEqual(implicit.owners, ['G3']);
  assert.equal(explicit.domain, 'G4');
  assert.deepEqual(explicit.owners, ['G4']);
  assert.deepEqual(explicit.nodesByFunction, { accessibility: ['AC01', 'TY03'] });
  assert.equal(hidden.showDomain, false);
  assert.deepEqual(hidden.domainOptions, []);
  assert.equal(hidden.domain, '');
  assert.equal(hidden.profile, policy.profiles['solo-fuente']);
  assert.deepEqual(hidden.owners, ['G2']);
});

test('explicit empty function in single-function scope requires a selection and proposes no owner', () => {
  const result = resolveSelection({ route: 'tipografia', scope: 'function', functionId: '' }, { catalog, policy });
  assert.deepEqual(result.requestedFunctions, []);
  assert.deepEqual(result.selectedFunctions, []);
  assert.deepEqual(result.owners, []);
  assert.equal(result.validation.valid, false);
  assert.equal(result.completeness.complete, false);
  assert.deepEqual(result.validation.errors, [
    { code: 'FUNCTION_REQUIRED', message: 'Falta seleccionar una función.' }
  ]);

  const auditEmpty = resolveSelection(
    { route: 'auditoria', scope: 'function', functionId: '', domain: 'G2' },
    { catalog, policy }
  );
  assert.deepEqual(auditEmpty.selectedFunctions, []);
  assert.deepEqual(auditEmpty.owners, []);
  assert.equal(auditEmpty.validation.valid, false);
  assert.deepEqual(auditEmpty.validation.errors, [
    { code: 'FUNCTION_REQUIRED', message: 'Falta seleccionar una función.' }
  ]);
});
