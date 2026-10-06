// Artifact QA only: fresh headless browser, no user/browser session access.
const {chromium}=require('C:/Users/hama101/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs');const path=require('path');const {pathToFileURL}=require('url');
(async()=>{let browser;try{browser=await chromium.launch({headless:true})}catch{browser=await chromium.launch({headless:true,channel:'msedge'})}
const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];
page.on('pageerror',e=>errors.push(e.message));await page.goto(pathToFileURL(path.join(__dirname,'Results.html')).href);
if(await page.locator('svg').count()!==5)throw Error('Five expected graph panels absent');
for(const link of await page.locator('a').evaluateAll(xs=>xs.map(x=>x.getAttribute('href')))){
if(!link.startsWith('#')&&!link.startsWith('https:')&&!fs.existsSync(path.join(__dirname,link)))throw Error('Missing artifact link '+link);}
await page.screenshot({path:path.join(__dirname,'Preview.png')});
await page.locator('.graph').nth(1).evaluate(e=>e.scrollIntoView({block:'start'}));await page.screenshot({path:path.join(__dirname,'Graphs Preview.png')});
await page.setViewportSize({width:420,height:860});await page.goto(pathToFileURL(path.join(__dirname,'Results.html')).href);
if(await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+1)){
console.log(await page.evaluate(()=>[...document.querySelectorAll('body *')].filter(x=>x.getBoundingClientRect().right>window.innerWidth+1 && !x.closest('.scroll')).map(x=>({tag:x.tagName,cl:x.className,width:x.getBoundingClientRect().width,right:x.getBoundingClientRect().right,text:x.textContent.slice(0,100)})).slice(0,25)));
await browser.close();throw Error('Mobile page overflow');}
await page.screenshot({path:path.join(__dirname,'Mobile Preview.png')});if(errors.length)throw Error(errors.join('\n'));
await browser.close();
fs.writeFileSync(path.join(__dirname,'html-qa.json'),JSON.stringify({passed:true,charts:5,local_links:true,page_errors:errors,mobile_width:420,page_overflow:false,html_sha256:require('crypto').createHash('sha256').update(fs.readFileSync(path.join(__dirname,'Results.html'))).digest('hex')},null,2));
console.log('Five charts, local links, mobile overflow and page errors: passed');
})().catch(e=>{console.error(e);process.exit(1)});
