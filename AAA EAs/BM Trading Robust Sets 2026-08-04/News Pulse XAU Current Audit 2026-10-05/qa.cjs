const { chromium } = require('C:/Users/hama101/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('fs'), path = require('path');
const {fileURLToPath} = require('url');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1500,height:1080}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('file:///'+path.join(__dirname,'Results.html').replace(/\\/g,'/'));
 const data=JSON.parse(fs.readFileSync(path.join(__dirname,'RESULTS.json'),'utf8'));
 const skips=fs.existsSync(path.join(__dirname,'NOT RUN.json'))?JSON.parse(fs.readFileSync(path.join(__dirname,'NOT RUN.json'),'utf8')):[];
 if(await page.locator('#performance tbody tr').count()!==data.length+skips.length)throw Error('Missing case rows');
 const notice=await page.locator('#outcome').innerText();
 if(!notice.includes('not a validated new winner')||!notice.includes('No parameters optimised'))throw Error('Missing qualification warning');
 const links=await page.locator('a[href]').evaluateAll(xs=>xs.map(x=>x.getAttribute('href')));
 for(const href of links){
  if(/^https?:/.test(href))continue;
  const local=href.split('#')[0];
  const target=/^file:/.test(local)?fileURLToPath(local):path.resolve(__dirname,decodeURIComponent(local));
  if(!fs.existsSync(target))throw Error('Missing evidence link '+target);
 }
 await page.screenshot({path:path.join(__dirname,'Preview.png'),fullPage:false});
 if(data.some(x=>x.case==='1Y-150')){
  await page.locator('#equity-chart').screenshot({path:path.join(__dirname,'Equity Preview.png')});
  await page.locator('#dd-chart').screenshot({path:path.join(__dirname,'Drawdown Preview.png')});
  const charts=await page.locator('#equity-chart polyline').count();
  if(charts!==data.filter(x=>['1Y-150','1Y-1000','1Y-3000'].includes(x.case)).length)throw Error('Missing curve');
 }
 await page.locator('details summary').first().click();
 if(await page.locator('details[open]').count()!==1)throw Error('Disclosure not working');
 await page.setViewportSize({width:420,height:950});
 await page.evaluate(()=>window.scrollTo(0,0));
 await page.screenshot({path:path.join(__dirname,'Mobile Preview.png'),fullPage:false});
 if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile outer overflow');
 if(errors.length)throw Error(errors.join('\n'));
 fs.writeFileSync(path.join(__dirname,'html-qa.json'),JSON.stringify({case_rows:data.length+skips.length,local_links_checked:true,disclosure:true,charts_checked:data.some(x=>x.case==='1Y-150'),mobile_outer_overflow:false,page_errors:errors},null,2));
 await browser.close();console.log('Native audit tables, evidence links, charts and mobile rendering verified.');
})().catch(e=>{console.error(e);process.exit(1)});
