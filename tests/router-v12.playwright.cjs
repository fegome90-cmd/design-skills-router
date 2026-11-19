'use strict';

const assert = require('node:assert/strict');
const { readFile } = require('node:fs/promises');
const { createHash } = require('node:crypto');
const path = require('node:path');
const { chromium } = require('playwright');
// Captured in Chromium from release/design-router-pizarra-v1.3.html before extraction.
const selectionG5 = require('./fixtures/selection-g5.json');

const file = process.argv[2] || path.join(__dirname, '../release/design-router-pizarra-v1.2.html');
const audit = (page, value = 'function') => page.locator('[data-route="auditoria"]').first().click()
  .then(() => page.locator('#minScope').selectOption(value));
const selectDomain = (page, value) => page.locator('#minDomain').selectOption(value);
const selectedOwners = page => page.evaluate(() => window.__minimalRouterPreview.getState().owners);
const selectStatus = (page, domain) => page.locator(`[data-review-status="${domain}"]`);
const reason = (page, domain) => page.locator(`[data-review-reason="${domain}"]`);
const review = page => page.locator('#minReviewToggle').click();

async function exportDoc(page) {
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.locator('#minExport').click()
  ]);
  const doc = JSON.parse(await readFile(await download.path(), 'utf8'));
  if (doc.status === 'DRAFT') assert.match(download.suggestedFilename(), /-borrador\.json$/);
  return doc;
}

function assertSafety(doc) {
  assert.match(doc.schema, /\/1\.2$/);
  assert.equal(doc.human_gate, 'NOT_APPROVED');
  assert.deepEqual(doc.skills_executed, []);
  for (const item of Object.values(doc.applicability)) {
    assert.equal(item.reviewed, false);
    assert.equal(item.verified, false);
    assert.equal(item.approved, false);
  }
}

const cases = {
  'Base: fuente G2, microtipografía G3 y escenario G2 + G3': async page => {
    for (const [id, owner] of [['type-choice', 'G2'], ['type-micro', 'G3']]) {
      await page.locator(`[data-cap="${id}"]`).first().click();
      assert.deepEqual(await selectedOwners(page), [owner]);
      const doc = await exportDoc(page);
      assert.deepEqual(doc.selected_functions, [id]);
      assert.deepEqual(doc.source_pins.map(pin => pin.id), [owner]);
      assert.equal(doc.mode_status, 'ORIENTATION_ONLY');
      assertSafety(doc);
    }
    await page.locator('#minScope').selectOption('scenario');
    assert.deepEqual((await selectedOwners(page)).sort(), ['G2', 'G3']);
    await page.locator('#minScope').selectOption('function');
    await page.locator('[data-route="color"]').first().click();
    assert.deepEqual(await selectedOwners(page), ['G4']);
    for (const view of ['stageMapView', 'skillNetworkView', 'proposalBoardView', 'compareSkillsView',
      'allComparisonsView', 'capabilityMapView']) {
      await page.locator(`#${view}`).click();
    }
    assert.equal(await page.locator('#capabilityPanel').isVisible(), true);
  },
  'SEM-01: auditoría de tipografía, solo función': async page => {
    await audit(page);
    await selectDomain(page, 'G2');
    assert.deepEqual(await selectedOwners(page), ['G2']);
  },
  'SEM-02: auditoría de layout, escenario completo': async page => {
    await audit(page, 'scenario');
    await selectDomain(page, 'G5');
    assert.deepEqual(await selectedOwners(page), ['G5']);
    const doc = await exportDoc(page);
    assert.deepEqual(doc, selectionG5.document);
    assertSafety(doc);

    const permit = page.locator('#minPermit');
    const permitNote = page.locator('#minPermitNote');
    assert.equal(await permit.inputValue(), selectionG5.permission.value);
    assert.equal(await permit.locator('option:checked').textContent(), selectionG5.permission.label);
    assert.equal(await permit.locator('option[value="sandbox"]').isDisabled(), true);
    assert.equal(await permitNote.isVisible(), true);
    assert.equal(await permitNote.textContent(), selectionG5.permission.note);

    const support = page.locator('#minSupport');
    const warning = support.locator('.min-support-warning');
    assert.equal(await warning.isVisible(), true);
    assert.equal(await warning.textContent(), selectionG5.support.warning);

    const catalog = JSON.parse(await page.locator('#capabilityMapData').textContent());
    const breakUi = catalog.skills.find(skill => skill.id === 'X45');
    assert.equal(breakUi.name, 'break-ui');
    const contributions = breakUi.contributions.filter(item => doc.selected_functions.includes(item.function_id));
    const groups = await support.locator('details[data-effect-group]').all();
    assert.equal(groups.length, selectionG5.support.groups.length);
    assert.equal(contributions.length, groups.length);
    for (const [index, expected] of selectionG5.support.groups.entries()) {
      const group = groups[index];
      assert.equal(await group.getAttribute('data-effect-group'), expected.id);
      const summary = group.locator('summary');
      assert.equal(await summary.textContent(), expected.summary);
      if ((await group.getAttribute('open')) === null) await summary.click();
      const items = group.locator('.min-support-item');
      assert.deepEqual(await items.locator('strong').allTextContents(), expected.names);
      const row = items.filter({ has: page.getByText(breakUi.name, { exact: true }) });
      assert.equal(await row.isVisible(), true);
      const [functionLabel, trigger] = await row.locator('small').allTextContents();
      assert.equal(functionLabel, expected.functionLabel);
      assert.equal(trigger, expected.breakUi.trigger);
      assert.deepEqual(contributions.find(item => item.trigger === trigger), expected.breakUi);
    }

    assert.deepEqual(Object.fromEntries(doc.selected_functions.map(id => [
      id, catalog.functions.find(fn => fn.id === id).nodes
    ])), selectionG5.nodesByFunction);

    await selectDomain(page, 'G2');
    assert.deepEqual(await selectedOwners(page), ['G2']);
  },
  'STATE-03: N/A vacío y N/A de G2 requerido': async page => {
    await audit(page);
    await selectDomain(page, 'G2');
    await review(page);
    await selectStatus(page, 'G4').selectOption('not_applicable');
    await selectStatus(page, 'G2').selectOption('not_applicable');
    await reason(page, 'G2').fill('Justificación que no resuelve la contradicción');
    const doc = await exportDoc(page);
    assert.equal(doc.applicability.G4.applicability, 'not_applicable');
    assert.equal(doc.applicability.G4.reason, '');
    assert.equal(doc.validation.valid, false);
    assert.equal(doc.status, 'DRAFT');
    assert.ok(doc.validation.errors.some(error => error.code === 'REQUIRED_DOMAIN_NOT_APPLICABLE' && error.domain === 'G2'));
    assert.ok(doc.validation.errors.some(error => error.code === 'MISSING_JUSTIFICATION' && error.domain === 'G4'));
    assertSafety(doc);
  },
  'TRACE-04: expediente descargado conserva ámbito y huella de política': async page => {
    await audit(page);
    await selectDomain(page, 'G2');
    const doc = await exportDoc(page);
    assert.equal(doc.selected_route, 'auditoria');
    assert.equal(doc.selected_scope, 'function');
    assert.equal(doc.selected_domain, 'G2');
    const policy = await page.locator('#minRouteData').textContent();
    assert.equal(doc.policy_hash, createHash('sha256').update(policy.trim()).digest('hex'));
    assert.ok(doc.policy_version);
    assert.ok(doc.completeness);
    assertSafety(doc);
  },
  'UX-05: cambio con teclado conserva select exacto y selección dentro del texto': async page => {
    await review(page);
    const status = selectStatus(page, 'G4');
    await status.focus();
    // Native select type-ahead chooses the option «No aplica» on macOS and Linux.
    await page.keyboard.press('n');
    assert.equal(await status.inputValue(), 'not_applicable');
    assert.equal(await status.evaluate(node => node === document.activeElement), true);
    await page.keyboard.press('Tab');
    const input = reason(page, 'G4');
    assert.equal(await input.evaluate(node => node === document.activeElement), true);
    await page.keyboard.insertText('abcde');
    await page.keyboard.press('ArrowLeft');
    await page.keyboard.press('Shift+ArrowLeft');
    const selection = node => [node === document.activeElement, node.selectionStart, node.selectionEnd];
    assert.deepEqual(await input.evaluate(selection), [true, 3, 4]);
    await input.dispatchEvent('input');
    assert.deepEqual(await input.evaluate(selection), [true, 3, 4]);
    await input.dispatchEvent('change');
    assert.deepEqual(await input.evaluate(selection), [true, 3, 4]);
    await page.keyboard.insertText('X');
    assert.equal(await input.inputValue(), 'abcXe');
    await page.keyboard.press('Tab');
    assert.equal(await input.evaluate(node => node === document.activeElement), false);
    assert.equal((await exportDoc(page)).applicability.G4.reason, 'abcXe');
  },
  'Auditoría sin ámbito en ambos alcances': async page => {
    for (const scope of ['function', 'scenario']) {
      await audit(page, scope);
      const doc = await exportDoc(page);
      assert.deepEqual(doc.proposed_owners, []);
      assert.ok(doc.selected_domain === null || doc.selected_domain === '');
      assert.equal(doc.validation.valid, false);
      assert.ok(doc.validation.errors.some(error => error.code === 'AUDIT_DOMAIN_REQUIRED'));
      assertSafety(doc);
    }
  },
  'Ida y vuelta entre dominios con justificaciones independientes': async page => {
    await audit(page);
    await selectDomain(page, 'G2');
    await review(page);
    await selectStatus(page, 'G4').selectOption('not_applicable');
    await reason(page, 'G4').fill('Fuera del ámbito tipográfico <&>');
    await selectDomain(page, 'G5');
    assert.notEqual(await selectStatus(page, 'G4').inputValue(), 'not_applicable');
    await selectStatus(page, 'G4').selectOption('not_applicable');
    await reason(page, 'G4').fill('Fuera de revisión de layout');
    assert.equal((await exportDoc(page)).applicability.G4.reason, 'Fuera de revisión de layout');
    await selectDomain(page, 'G2');
    assert.equal(await reason(page, 'G4').inputValue(), 'Fuera del ámbito tipográfico <&>');
    assert.equal((await exportDoc(page)).applicability.G4.reason, 'Fuera del ámbito tipográfico <&>');
    await selectDomain(page, 'G5');
    assert.equal(await reason(page, 'G4').inputValue(), 'Fuera de revisión de layout');
  },
  'POLICY-08: al entrar en auditoría se bloquea sandbox y se conserva lectura efectiva': async page => {
    const permissions = page.locator('#minPermit');
    await permissions.selectOption('sandbox');
    await audit(page);
    await selectDomain(page, 'G2');
    const unavailable = await permissions.evaluate(select => select.disabled || !Array.from(select.options)
      .some(option => option.value === 'sandbox' && !option.disabled));
    assert.equal(unavailable, true);
    const doc = await exportDoc(page);
    assert.equal(doc.simulated_permission, 'read');
    assertSafety(doc);
  },
  'VIS-07: los apoyos de escritura están visibles o se pueden desplegar': async page => {
    await page.locator('[data-route="componentes"]').first().click();
    await page.locator('#minScope').selectOption('scenario');
    const write = page.locator('#minSupport details[data-effect-group="write"]');
    await write.locator('summary').click();
    assert.equal(await write.locator('.min-support-item.is-write').last().isVisible(), true);
    const result = await page.locator('#minSupport').evaluate(node => {
      const data = JSON.parse(document.querySelector('#capabilityMapData').textContent);
      const policy = JSON.parse(document.querySelector('#minRouteData').textContent);
      const functions = data.routes.find(route => route.id === 'componentes').functions;
      const expected = data.skills.flatMap(skill => skill.contributions)
        .filter(contribution => functions.includes(contribution.function_id) && policy.writes.includes(contribution.effect));
      return { expected: expected.length, actual: node.querySelectorAll('.min-support-item.is-write').length };
    });
    assert.ok(result.expected > 0);
    assert.equal(result.actual, result.expected);
  },
  'Responsive: 320, 390, 768 y 1440 CSS px sin desborde al abrir requisitos': async page => {
    await audit(page, 'scenario');
    await selectDomain(page, 'G5');
    await review(page);
    await selectStatus(page, 'G4').selectOption('not_applicable');
    await reason(page, 'G4').fill('Una justificación suficientemente larga para comprobar los controles en un ancho móvil.');
    for (const width of [320, 390, 768, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      const dimensions = await page.evaluate(() => [
        document.documentElement.scrollWidth, document.documentElement.clientWidth
      ]);
      assert.ok(dimensions[0] <= dimensions[1], `${width}px: ${dimensions.join(' > ')}`);
      assert.equal(await page.locator('#minExport').isVisible(), true);
    }
  },
  'Búsqueda vacía en modo función única no exporta una función no seleccionada': async page => {
    await page.locator('#minScope').selectOption('function');
    await page.locator('#capSearch').fill('zzz-sin-coincidencias-999');
    await page.locator('#capFunctionList .cap-empty').waitFor({ state: 'visible' });
    const doc = await exportDoc(page);
    assert.deepEqual(doc.selected_functions, []);
    assert.deepEqual(doc.requested_functions, []);
    assert.deepEqual(doc.proposed_owners, []);
    assert.equal(doc.validation.valid, false);
    assert.equal(doc.status, 'DRAFT');
    assert.ok(doc.validation.errors.some(error => error.code === 'FUNCTION_REQUIRED'));
    assertSafety(doc);
  },
  async 'busqueda vacia en auditoria pide funcion sin culpar al dominio'(page) {
    await page.locator('#capRouteButtons [data-route="auditoria"]').click();
    await page.locator('#minScope').selectOption('function');
    await page.locator('#minDomain').selectOption('G5');
    await page.locator('#capSearch').fill('termino-sin-coincidencias-xyz');
    const primaryText = await page.locator('#minPrimary').textContent();
    assert.ok(!primaryText.includes('queda fuera del dominio de auditoría'), primaryText);
    assert.ok(primaryText.includes('Falta delimitar dominio o función'), primaryText);
  }
};

(async () => {
  const html = await readFile(file, 'utf8');
  const executablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE;
  const browser = await chromium.launch({ executablePath, headless: true });
  let failures = 0;
  try {
    for (const [name, check] of Object.entries(cases)) {
      const page = await browser.newPage({ viewport: { width: 1280, height: 850 }, acceptDownloads: true });
      page.setDefaultTimeout(4000);
      await page.route('**/*', route => route.abort());
      const uncaught = [];
      page.on('pageerror', error => uncaught.push(error.message));
      try {
        await page.setContent(html, { waitUntil: 'domcontentloaded' });
        await check(page);
        assert.deepEqual(uncaught, []);
        console.log(`PASS ${name}`);
      } catch (error) {
        failures++;
        console.error(`FAIL ${name}\n${error.stack}`);
      } finally {
        await page.close();
      }
    }
  } finally {
    await browser.close();
  }
  console.log(`${Object.keys(cases).length - failures}/${Object.keys(cases).length} casos aprobados`);
  process.exitCode = failures === 0 ? 0 : 1;
})().catch(error => {
  console.error(`Suite no iniciada: ${error.message}`);
  process.exitCode = 2;
});
