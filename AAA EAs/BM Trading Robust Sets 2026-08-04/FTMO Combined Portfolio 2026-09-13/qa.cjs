const { chromium } = require('C:/Users/hama101/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const path = require('path');
const fs = require('fs');
const {pathToFileURL} = require('url');
(async()=>{
  const browser=await chromium.launch({channel:'msedge',headless:true});
  const checks=[];
  for(const scheme of ['light','dark']) for(const width of [736,360]) {
    const page=await browser.newPage({viewport:{width:width+32,height:1200},deviceScaleFactor:1,colorScheme:scheme});
    const errors=[];page.on('pageerror',err=>errors.push(err.message));
    await page.goto(pathToFileURL(path.join(__dirname,'interactive-preview.html')).href);
    const f=page.frameLocator('iframe');
    const root=f.locator('#ftmo-ten-ea');
    await root.locator('svg circle').first().waitFor({timeout:30000});
    const rootHeight=await root.evaluate(e=>Math.ceil(e.getBoundingClientRect().height));
    await page.setViewportSize({width:width+32,height:rootHeight+80});
    const measure=await root.evaluate(e=>({width:e.getBoundingClientRect().width,scroll:e.scrollWidth,client:e.clientWidth,svgs:e.querySelectorAll('svg.ftmo-chart').length}));
    if(measure.scroll>measure.client+2)throw Error('Horizontal clipping '+JSON.stringify(measure));
    await f.locator('#ftmo-month').selectOption('0');
    if(!(await f.locator('#ftmo-detail').innerText()).includes('25 closed trades'))throw Error('Month selection failed');
    await f.locator('#ftmo-risk').selectOption('stop-envelope');
    if(!(await f.locator('#ftmo-status').innerText()).includes('HALTED'))throw Error('Failure scenario did not change');
    await f.locator('#ftmo-account').selectOption('challenge');
    if(!(await f.locator('#ftmo-totals').innerText()).includes('$0 possible payouts'))throw Error('Evaluation payout violation');
    await f.locator('#ftmo-risk').selectOption('lower-news');
    await f.locator('#ftmo-account').selectOption('funded');
    await f.locator('#ftmo-month').selectOption('35');
    const legend=f.locator('#ftmo-pl-legend button').first();
    await legend.click();
    if(await legend.getAttribute('aria-pressed')!=='false')throw Error('Legend failed');
    await legend.click();
    const hit=f.locator('#ftmo-pl [data-chart-hit]');
    await hit.hover({position:{x:Math.min(width/2,160),y:80}});
    if(await f.locator('#ftmo-pl [data-chart-hover-marker]').count()!==2)throw Error('Cross-series hover failed');
    await f.locator('h2').hover();
    const full=path.join(__dirname,`preview-${scheme}-${width}.png`);
    await root.screenshot({path:full});
    if(scheme==='light'&&width===736){
      const b=await root.boundingBox(); const lower=await f.locator('#ftmo-month').boundingBox();
      await page.screenshot({path:path.join(__dirname,'monthly-system-graph.png'),clip:{x:b.x,y:b.y,width:b.width,height:lower.y-b.y-20}});
    }
    checks.push({scheme,width,...measure,errors,interaction:'month,scenario,phase,legend,hover passed'});
    if(errors.length)throw Error(errors.join(';'));
    await page.close();
  }
  await browser.close();
  fs.writeFileSync(path.join(__dirname,'visual-qa.json'),JSON.stringify(checks,null,2));
  console.log(JSON.stringify(checks,null,2));
})().catch(e=>{console.error(e);process.exit(1);});
