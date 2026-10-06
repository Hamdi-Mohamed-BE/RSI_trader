const {chromium}=require('C:/Users/hama101/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path'),{fileURLToPath}=require('url');
(async()=>{
 const browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1600,height:1100}});const errors=[];
 page.on('pageerror',e=>errors.push(e.message));await page.goto('file:///'+path.join(__dirname,'Results.html').replace(/\\/g,'/'));
 const text=await page.locator('body').innerText();
 for(const x of ['NO REPLACEMENT RECOMMENDATION','Native current versus candidate','2026-10-05','Gold and Silver news','10,000-path','NOT RUN'])if(!text.includes(x))throw Error('Missing '+x);
 if(await page.locator('svg').count()!==6)throw Error('Missing equity/drawdown charts');
 for(const href of await page.locator('a[href]').evaluateAll(xs=>xs.map(x=>x.getAttribute('href')))){
  if(/^https?:/.test(href))continue;const p=href.startsWith('file:')?fileURLToPath(href):path.resolve(__dirname,decodeURIComponent(href.split('#')[0]));if(!fs.existsSync(p))throw Error('Missing '+p);
 }
 await page.screenshot({path:path.join(__dirname,'Preview.png'),fullPage:false});
 await page.locator('.scroll').first().screenshot({path:path.join(__dirname,'Comparison Preview.png')});
 await page.locator('svg').first().screenshot({path:path.join(__dirname,'Equity Preview.png')});
 await page.setViewportSize({width:420,height:950});await page.evaluate(()=>scrollTo(0,0));
 if(await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth))throw Error('Mobile overflow');
 await page.screenshot({path:path.join(__dirname,'Mobile Preview.png'),fullPage:false});
 await page.locator('summary').first().click();if(!await page.locator('details').first().getAttribute('open') && !(await page.locator('details').first().evaluate(e=>e.open)))throw Error('Details not working');
 if(errors.length)throw Error(errors.join('\n'));fs.writeFileSync(path.join(__dirname,'html-qa.json'),JSON.stringify({six_graphs:true,local_links:true,mobile_overflow:false,page_errors:errors},null,2));
 await browser.close();console.log('HTML, charts, details, links and mobile verified');
})().catch(e=>{console.error(e);process.exit(1)});
