'use strict';

const assert = require('node:assert/strict');
const { resolve } = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

async function main() {
  const documentUrl = pathToFileURL(resolve(process.argv[2])).href;
  const browser = await chromium.launch({
    executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
    headless: true
  });
  try {
    const page = await browser.newPage({ acceptDownloads: true, viewport: { width: 1440, height: 960 } });
    const errors = [];
    const network = [];
    page.on('pageerror', err => errors.push(err.message));
    await page.route(/^https?:\/\//, route => {
      network.push(route.request().url());
      return route.abort();
    });
    await page.goto(documentUrl);
    await page.waitForFunction(() => customElements.get('sl-tooltip') && customElements.get('sl-tag'));
    const fonts = await page.evaluate(async () => Promise.all([
      document.fonts.load('500 16px Fraunces', 'áÉñ'),
      document.fonts.load('400 16px "IBM Plex Sans"', 'áÉñ'),
      document.fonts.load('400 16px "IBM Plex Mono"', 'áÉñ')
    ]).then(families => families.map(family => family.some(face => face.status === 'loaded'))));
    assert.deepEqual(fonts, [true, true, true]);
    await page.locator('#stageMapView').click();
    await page.locator('#engineButton').click();
    await page.waitForFunction(() => document.querySelector('#engineBadge').textContent.includes('SVG LOCAL'));
    const downloadPromise = page.waitForEvent('download');
    await page.locator('#exportDrawio').click();
    const download = await downloadPromise;
    assert.match(download.suggestedFilename(), /\.drawio$/);
    await page.locator('#routerNodeView').click();
    await page.locator('#routerNodeDetail #router-node-Q00').waitFor({ state: 'visible' });
    assert.deepEqual(errors, []);
    assert.deepEqual(network, []);
    console.log(`Chromium ${browser.version()}, cero solicitudes HTTP(S).`);
    console.log('PASS: archivo local, componentes, fuentes, fallback SVG, exportación y mapa de nodos sin solicitudes HTTP.');
  } finally {
    await browser.close();
  }
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
