// Render and inspect only this generated research report, not the user's browser.
const { chromium } = require('C:/Users/hama101/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const { pathToFileURL } = require('node:url');
const path = require('node:path');
(async () => {
  const browser = await chromium.launch({headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1400,height:1050}});
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto(pathToFileURL(path.join(__dirname,'Results.html')).href);
    const text=await page.locator('body').innerText();
    for(const expected of ['EURUSD','GBPUSD','USDJPY','-63.18','Fresh-start 2026','three-year screen is preliminary']) {
      if(!text.includes(expected))throw Error('Missing evidence: '+expected);
    }
    if(await page.locator('table').count()!==6)throw Error('Missing metric table');
    for(const table of await page.locator('table').all()) {
      if(await table.locator('tr').count()!==7)throw Error('Expected six sizing/pair rows and one header');
    }
    if(await page.locator('svg polyline').count()!==6)throw Error('Missing account curves');
    await page.screenshot({path:path.join(__dirname,'Report preview.png')});
    await page.setViewportSize({width:420,height:850});
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2);
    if(overflow)throw Error('Whole-page horizontal overflow on mobile');
    if(errors.length)throw Error(errors.join('\n'));
    console.log(JSON.stringify({render:'passed',tables:6,curves:6,mobile_overflow:false,errors:errors.length}));
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
