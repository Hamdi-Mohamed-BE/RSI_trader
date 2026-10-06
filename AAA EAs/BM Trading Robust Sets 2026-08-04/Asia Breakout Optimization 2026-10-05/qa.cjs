const {chromium}=require('C:/Users/hama101/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs');const path=require('path');const {pathToFileURL}=require('url');
(async()=>{
 const browser=await chromium.launch({headless:true});const errors=[];const page=await browser.newPage({viewport:{width:1440,height:1000}});
 page.on('pageerror',e=>errors.push(e.message));await page.goto(pathToFileURL(path.join(__dirname,'Results.html')).href);await page.waitForLoadState('load');
 const results=await page.evaluate(()=>({title:document.title,graphs:document.querySelectorAll('svg').length,tables:document.querySelectorAll('table').length,
  horizontal:document.documentElement.scrollWidth>innerWidth,hasNaN:/\bNaN\b|\bundefined\b/.test(document.body.innerText),brokenImages:[...document.images].filter(i=>!i.complete||i.naturalWidth===0).length}));
 await page.screenshot({path:path.join(__dirname,'Preview.png'),fullPage:false});await page.setViewportSize({width:390,height:844});
 const mobile=await page.evaluate(()=>({horizontal:document.documentElement.scrollWidth>innerWidth,graphs:document.querySelectorAll('svg').length}));
 await page.screenshot({path:path.join(__dirname,'Preview-mobile.png'),fullPage:false});
 if(errors.length||results.horizontal||mobile.horizontal||results.hasNaN||results.brokenImages||results.graphs!==6)throw Error(JSON.stringify({errors,results,mobile}));
 fs.writeFileSync(path.join(__dirname,'html-qa.json'),JSON.stringify({errors,results,mobile},null,2));await browser.close();console.log(JSON.stringify({errors,results,mobile}));
})().catch(e=>{console.error(e);process.exit(1)});
