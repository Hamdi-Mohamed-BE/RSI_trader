const fs=require('fs');
const path=require('path');
const {chromium}=require('C:/Users/hama101/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const root=__dirname;
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage();
 const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.goto('file:///'+path.join(root,'Results.html').replaceAll('\\','/'));
 const results=[];
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:950});
  await page.evaluate(()=>window.scrollTo(0,0));
  await page.screenshot({path:path.join(root,'preview-'+width+'.png'),fullPage:false});
  await page.locator('.scroll').first().screenshot({path:path.join(root,'comparison-'+width+'.png')});
  await page.locator('svg').first().screenshot({path:path.join(root,'equity-'+width+'.png')});
  const state=await page.evaluate(()=>({width:innerWidth,body:document.body.scrollWidth,
   tables:document.querySelectorAll('table').length,plots:document.querySelectorAll('svg path').length,
   rows:document.querySelectorAll('tbody tr').length,title:document.querySelector('h1').textContent}));
  if(state.body>width+2)throw Error('Document-level overflow '+JSON.stringify(state));
  if(state.tables<3 || state.plots<4 || state.rows<16)throw Error('Missing result content '+JSON.stringify(state));
  results.push(state);
 }
 const detail=page.locator('details').first();await detail.locator('summary').click();
 if(!(await detail.getAttribute('open')) && !(await detail.evaluate(e=>e.open)))throw Error('Disclosure failed');
 if(errors.length)throw Error(errors.join('\n'));
 fs.writeFileSync(path.join(root,'QA.json'),JSON.stringify({results,errors,disclosure:true},null,2));
 await browser.close();process.stdout.write(JSON.stringify({verified:true,results}));
})().catch(e=>{process.stderr.write(String(e));process.exit(1)});
