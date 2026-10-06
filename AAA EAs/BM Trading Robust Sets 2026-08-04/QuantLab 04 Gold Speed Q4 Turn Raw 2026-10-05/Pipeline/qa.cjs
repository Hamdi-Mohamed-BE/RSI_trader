// Generated-artifact QA only; independent headless browser, no user session.
const {chromium}=require('C:/Users/hama101/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path'),{pathToFileURL}=require('url');
(async()=>{let browser;try{browser=await chromium.launch({headless:true})}catch{browser=await chromium.launch({headless:true,channel:'msedge'})}
const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto(pathToFileURL(path.join(__dirname,'Results.html')).href);const charts=await page.locator('svg').count();if(charts<4)throw Error('Expected shared curves and MC missing');
for(const link of await page.locator('a').evaluateAll(xs=>xs.map(x=>x.getAttribute('href')))){if(!link.startsWith('#')&&!link.startsWith('https:')&&!fs.existsSync(path.join(__dirname,link)))throw Error('Missing artifact '+link)}
await page.screenshot({path:path.join(__dirname,'Preview.png')});await page.locator('.graph').nth(1).evaluate(e=>e.scrollIntoView({block:'start'}));await page.screenshot({path:path.join(__dirname,'Graphs Preview.png')});
await page.setViewportSize({width:420,height:860});await page.goto(pathToFileURL(path.join(__dirname,'Results.html')).href);if(await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+1))throw Error('Mobile overflow');
await page.screenshot({path:path.join(__dirname,'Mobile Preview.png')});await browser.close();if(errors.length)throw Error(errors.join('\n'));
fs.writeFileSync(path.join(__dirname,'html-qa.json'),JSON.stringify({passed:true,charts,local_links:true,page_errors:errors,mobile_width:420,page_overflow:false},null,2));console.log('Artifact charts, links, browser errors and mobile width: PASS',charts);
})().catch(e=>{console.error(e);process.exit(1)});
