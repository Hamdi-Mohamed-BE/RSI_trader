const { chromium } = require('C:/Users/hama101/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('fs');
const path = require('path');
const {fileURLToPath} = require('url');
(async () => {
  const browser = await chromium.launch({headless: true});
  const page = await browser.newPage({viewport: {width: 1600, height: 1100}});
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto('file:///' + path.join(__dirname, 'Results.html').replace(/\\/g, '/'));
  if (await page.locator('tbody tr').count() !== 37) throw Error('Inventory count');
  const keepNote = await page.locator('#future-bat-keeps').innerText();
  if (!keepNote.includes('candidate 1.5R') || !keepNote.includes('packaged in reviwed_Eas') || !keepNote.includes('robustness screen failed')) throw Error('Missing user keep decision or warnings');
  const deferred = await page.locator('#deferred-news').innerText();
  if (!deferred.includes('Gold and Silver news') || !deferred.includes('DEFERRED BY USER') || !deferred.includes('Gold Overnight Value Area')) throw Error('Missing news defer decision');
  if (await page.locator('#gold-overnight-update').count()) {
    const update=await page.locator('#gold-overnight-update').innerText();
    if (!update.includes('no replacement recommended') || !update.includes('Asia Breakout Gold') || !update.includes('replacement candidate is NOT selected') || !update.includes('unchanged original Gold Overnight rules are now selected')) throw Error('Missing optimisation outcome or owner-original/candidate distinction');
  }
  for (const [filter, expected] of [['keep',25],['pause',6],['review',6]]) {
    await page.locator(`[data-filter="${filter}"]`).click();
    if (await page.locator('tbody tr:visible').count() !== expected) throw Error('Category count '+filter);
  }
  await page.locator('[data-filter="all"]').click();
  await page.locator('#search').fill('RSI');
  if (await page.locator('tbody tr:visible').count() !== 1) throw Error('Search');
  await page.locator('#search').fill('');
  const links = await page.locator('a[href]').evaluateAll(xs => xs.map(x => x.getAttribute('href')));
  for (const href of links) {
    if (/^https?:/.test(href)) continue;
    const target = /^file:/.test(href) ? fileURLToPath(href) : path.resolve(__dirname, decodeURIComponent(href.split('#')[0]));
    if (!fs.existsSync(target)) throw Error('Missing evidence '+target);
  }
  await page.evaluate(()=>window.scrollTo(0,0));
  await page.screenshot({path: path.join(__dirname, 'Preview.png'), fullPage: false});
  await page.locator('[data-filter="pause"]').click();
  await page.locator('.tablewrap').screenshot({path: path.join(__dirname, 'Pause Preview.png')});
  await page.locator('[data-filter="all"]').click();
  await page.setViewportSize({width:420,height:950});
  await page.evaluate(()=>window.scrollTo(0,0));
  await page.screenshot({path: path.join(__dirname, 'Mobile Preview.png'), fullPage:false});
  if (await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth)) throw Error('Mobile page overflow');
  if(errors.length) throw Error(errors.join('\n'));
  fs.writeFileSync(path.join(__dirname,'html-qa.json'),JSON.stringify({rows:37,filters:[25,6,6],search:true,local_links_checked:true,mobile_outer_overflow:false,page_errors:errors},null,2));
  await browser.close();
  console.log('Report rendering and controls verified.');
})().catch(e=>{console.error(e);process.exit(1)});
