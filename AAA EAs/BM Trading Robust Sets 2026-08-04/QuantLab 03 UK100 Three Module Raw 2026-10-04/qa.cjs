// Headless QA of this generated offline artifact only; no existing browser profile.
const { chromium } = require('C:/Users/hama101/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('fs');
const path = require('path');
const {pathToFileURL}=require('url');
(async()=>{
  let browser;
  try {browser=await chromium.launch({headless:true});}
  catch {browser=await chromium.launch({headless:true,channel:'msedge'});}
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(pathToFileURL(path.join(__dirname,'Results.html')).href);
  const links=await page.locator('a').evaluateAll(xs=>xs.map(x=>x.getAttribute('href')));
  for(const link of links){if(!link.startsWith('#')&&!link.startsWith('https:')&&!fs.existsSync(path.join(__dirname,link)))throw Error('Missing linked output: '+link);}
  if(await page.locator('svg').count()!==6)throw Error('Missing graphs');
  await page.screenshot({path:path.join(__dirname,'Preview.png')});
  await page.locator('[id="year"]').evaluate(el=>el.scrollIntoView({block:'start'}));
  await page.screenshot({path:path.join(__dirname,'Graphs Preview.png')});
  await page.setViewportSize({width:420,height:860});await page.goto(pathToFileURL(path.join(__dirname,'Results.html')).href);
  if(await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+1))throw Error('Mobile page-level overflow');
  await page.screenshot({path:path.join(__dirname,'Mobile Preview.png')});
  if(errors.length)throw Error(errors.join('\n'));
  await browser.close();console.log('HTML links, six graphs, page errors and mobile overflow: passed');
})().catch(e=>{console.error(e);process.exit(1)});
