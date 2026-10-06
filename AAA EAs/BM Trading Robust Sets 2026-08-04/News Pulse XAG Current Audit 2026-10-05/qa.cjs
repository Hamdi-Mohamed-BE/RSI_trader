const {chromium}=require('C:/Users/hama101/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path');
(async()=>{
 const browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1500,height:1050}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('file:///'+path.join(__dirname,'Results.html').replace(/\\/g,'/'));
 const data=JSON.parse(fs.readFileSync(path.join(__dirname,'RESULTS.json'),'utf8'));
 if(await page.locator('#performance tbody tr').count()!==data.length)throw Error('Missing case rows');
 const text=await page.locator('#outcome').innerText();
 if(!text.includes('not a validated new winner')||!text.includes('No parameters optimised'))throw Error('Qualification missing');
 for(const href of await page.locator('a[href]').evaluateAll(a=>a.map(x=>x.getAttribute('href')))){
  if(/^https?:/.test(href))continue;
  if(!fs.existsSync(path.resolve(__dirname,decodeURIComponent(href.split('#')[0]))))throw Error('Missing link '+href);
 }
 await page.screenshot({path:path.join(__dirname,'Preview.png')});
 if(data.some(x=>x.case==='1Y-150')){
  if(await page.locator('#equity-chart polyline').count()!==1)throw Error('Missing year curve');
  await page.locator('#equity-chart').screenshot({path:path.join(__dirname,'Equity Preview.png')});
  await page.locator('#dd-chart').screenshot({path:path.join(__dirname,'Drawdown Preview.png')});
 }
 if(await page.locator('#delay-chart polyline').count()!==data.filter(x=>/^3M-/.test(x.case)).length)throw Error('Missing delay curve');
 await page.locator('details summary').first().click();
 if(await page.locator('details[open]').count()!==1)throw Error('Disclosure failed');
 await page.setViewportSize({width:420,height:950});await page.evaluate(()=>scrollTo(0,0));
 await page.screenshot({path:path.join(__dirname,'Mobile Preview.png')});
 if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile overflow');
 if(errors.length)throw Error(errors.join('\n'));
 fs.writeFileSync(path.join(__dirname,'html-qa.json'),JSON.stringify({case_rows:data.length,evidence_links_checked:true,charts_checked:true,disclosure:true,mobile_outer_overflow:false,page_errors:errors},null,2));
 await browser.close();console.log('Tables, links, curves and desktop/mobile layout verified.');
})().catch(e=>{console.error(e);process.exit(1)});
