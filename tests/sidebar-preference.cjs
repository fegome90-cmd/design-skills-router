'use strict';

const assert = require('node:assert/strict');
const { pathToFileURL } = require('node:url');
const { resolve } = require('node:path');
const { chromium } = require('playwright');

const views = new Map([
  ['stageMapView', ['#stageNavigation']],
  ['routerNodeView', ['.router-node-index']],
  ['skillNetworkView', ['#stageNavigation']],
  ['proposalBoardView', ['#stageNavigation']],
  ['compareSkillsView', ['#stageNavigation']],
  ['capabilityMapView', ['#stageNavigation', '.cap-functions']],
  ['allComparisonsView', ['#stageNavigation', '.more-index']],
]);
const panels = [...new Set([...views.values()].flat())];

async function visitViews(page, expanded) {
  const toggle = page.locator('#stageNavigationToggle');
  for (const [id, visiblePanels] of views) {
    await page.locator(`#${id}`).press('Enter');
    assert.equal(await toggle.isVisible(), true, `${id}: sidebar control is reachable`);
    assert.equal(await toggle.getAttribute('aria-expanded'), String(expanded), id);
    assert.equal(await toggle.innerText(), expanded ? 'Ocultar paneles' : 'Mostrar paneles', id);
    assert.ok(await toggle.evaluate(button => {
      const { left, right, top, bottom } = button.getBoundingClientRect();
      return left >= 0 && right <= innerWidth &&
        document.elementFromPoint((left + right) / 2, (top + bottom) / 2) === button;
    }), `${id}: sidebar control is clickable without scrolling`);
    for (const selector of panels) {
      assert.equal(await page.locator(selector).isVisible(),
        expanded && visiblePanels.includes(selector), `${id}: ${selector}`);
    }
  }
}

async function main() {
  const input = process.argv[2];
  if (!input) throw new Error('Usage: node tests/sidebar-preference.cjs PREVIEW_HTML');
  const url = pathToFileURL(resolve(input)).href;
  const browser = await chromium.launch({
    executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
  });
  try {
    for (const width of [973, 390, 320]) {
      const page = await browser.newPage({ viewport: { width, height: 992 } });
      const errors = [];
      page.setDefaultTimeout(4000);
      page.on('pageerror', error => errors.push(error.message));
      await page.route(/^https?:\/\//, route => route.abort());
      await page.goto(url);
      const toggle = page.locator('#stageNavigationToggle');
      const controlled = (await toggle.getAttribute('aria-controls')).split(' ');
      for (const selector of panels) {
        assert.ok(controlled.includes(await page.locator(selector).getAttribute('id')), selector);
      }
      const defaultExpanded = width > 840;
      assert.equal(await toggle.getAttribute('aria-expanded'), String(defaultExpanded));
      if (defaultExpanded) {
        await page.locator('#stageButtons button').first().focus();
        await page.setViewportSize({ width: 820, height: 992 });
        await page.waitForFunction(() => document.activeElement.id === 'stageNavigationToggle');
        await page.setViewportSize({ width, height: 992 });
        await page.waitForFunction(() =>
          document.querySelector('#stageNavigationToggle').getAttribute('aria-expanded') === 'true');
        await toggle.press('Enter');
      }
      await visitViews(page, false);
      await toggle.press('Space');
      await page.reload();
      await visitViews(page, true);
      await toggle.press('Enter');
      await page.reload();
      await visitViews(page, false);
      assert.deepEqual(errors, []);
      console.log(`PASS ${width}px: shared sidebar preference across seven views and reload`);
      await page.close();
    }
  } finally {
    await browser.close();
  }
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
