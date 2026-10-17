// Render the local research artifact only; no user browser or live account.
const { chromium } = require('C:/Users/hama101/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const { pathToFileURL } = require('node:url');
const path = require('node:path');
(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1400, height: 1100 } });
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(pathToFileURL(path.join(__dirname, 'Results.html')).href);
    const text = await page.locator('body').innerText();
    for (const expected of ['36 / 37', '-5.73%', '176', '43.18%', '-20.04', '9.13%', '14-day']) {
      if (!text.includes(expected)) throw Error('Missing displayed evidence: ' + expected);
    }
    if (errors.length) throw Error(errors.join('\n'));
    await page.screenshot({ path: path.join(__dirname, 'Report preview.png') });
    const rows = await page.locator('table').nth(2).locator('tr').count();
    if (rows !== 38) throw Error('Expected all 37 member rows plus header, got ' + rows);
    console.log(JSON.stringify({ render: 'passed', memberRows: rows - 1, javascriptErrors: errors.length }));
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
