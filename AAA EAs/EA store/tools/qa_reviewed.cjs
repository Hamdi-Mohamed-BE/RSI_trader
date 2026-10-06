const {chromium}=require('C:/Users/hama101/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs');const path=require('path');
(async()=>{
  const origin=process.argv[2]||'http://127.0.0.1:8080';
  const out=path.resolve(__dirname,'../../BM Trading Robust Sets 2026-08-04/Reviewed EA Deployment 2026-10-06');
  const browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1600,height:1100}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(origin+'/ea-review',{waitUntil:'networkidle'});
  if(await page.locator('[data-review-phase]').count()!==37)throw Error('Review total');
  for(const [phase,n] of [['live',25],['paused',6],['review',6],['all',37]]){
    await page.selectOption('#review-phase',phase);
    if(await page.locator('[data-review-phase]:visible').count()!==n)throw Error('Review phase '+phase);
  }
  await page.fill('#review-search','DMC');if(await page.locator('[data-review-phase]:visible').count()!==3)throw Error('DMC search');
  await page.fill('#review-search','');await page.screenshot({path:path.join(out,'Website review desktop.png')});
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(out,'Website review mobile.png')});
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw Error('Review mobile overflow');
  await page.setViewportSize({width:1600,height:1100});
  await page.goto(origin+'/eas?period=1y',{waitUntil:'networkidle'});
  if(await page.locator('#product-grid .product-card').count()!==37)throw Error('Catalogue total');
  for(const [phase,n] of [['live',25],['paused',6],['review',6],['all',37]]){
    await page.selectOption('#phase-filter',phase);
    if(await page.locator('#product-grid .product-card:visible').count()!==n)throw Error('Catalogue phase '+phase);
  }
  await page.selectOption('#phase-filter','live');await page.screenshot({path:path.join(out,'Website catalogue desktop.png')});
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(out,'Website catalogue mobile.png')});
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw Error('Catalogue mobile overflow');
  for(const [route,selector,rowSelector] of [['/ea-review','#review-phase','[data-review-phase]'],['/eas?period=1y','#phase-filter','#product-grid .product-card']]){
    await page.goto(origin+route+(route.includes('?')?'&':'?')+'phase=live',{waitUntil:'networkidle'});
    if(await page.locator(rowSelector).count()!==25)throw Error('Server live scope');
    await Promise.all([page.waitForURL(url=>url.searchParams.get('phase')==='paused'),page.selectOption(selector,'paused')]);
    await page.waitForLoadState('networkidle');
    if(await page.locator(rowSelector).count()!==6)throw Error('Server-to-server phase change');
    await Promise.all([page.waitForURL(url=>url.searchParams.get('phase')==='all'),page.selectOption(selector,'all')]);
    await page.waitForLoadState('networkidle');
    if(await page.locator(rowSelector).count()!==37)throw Error('Server-to-all phase change');
  }
  await page.goto(origin+'/eas/xau-trend-progression?period=1y',{waitUntil:'networkidle'});
  if(!(await page.locator('body').innerText()).includes('normal 0.6R cache remains separate'))throw Error('Trend version ambiguity');
  if(errors.length)throw Error(errors.join('\n'));
  fs.writeFileSync(path.join(out,'UI QA.json'),JSON.stringify({review_rows:37,phases:[25,6,6],search:true,catalogue_client_filters:true,server_scope_transitions:true,mobile_overflow:false,version_warning:true,page_errors:errors},null,2));
  await browser.close();console.log('Reviewed website desktop/mobile and phase filters verified.');
})().catch(e=>{console.error(e);process.exit(1)});
