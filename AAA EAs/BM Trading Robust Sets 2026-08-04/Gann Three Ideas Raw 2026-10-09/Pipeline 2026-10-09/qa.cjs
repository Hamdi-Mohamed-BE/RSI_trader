const {chromium}=require('C:/Users/hama101/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const {pathToFileURL}=require('url');const fs=require('fs');const path=require('path');
(async()=>{
 const root=__dirname;const browser=await chromium.launch({headless:true,args:['--disable-gpu']});
 const page=await browser.newPage({viewport:{width:1450,height:1000}});let errors=[];
 page.on('pageerror',e=>errors.push(String(e)));
 await page.goto(pathToFileURL(path.join(root,'Results.html')).href);
 const evidence=await page.evaluate(()=>({title:document.title,tables:document.querySelectorAll('table').length,
  stopped:document.body.innerText.includes('Optimisation is NOT completed'),links:[...document.querySelectorAll('a[href$=".csv"]')].map(x=>x.getAttribute('href'))}));
 if(evidence.tables<4 || !evidence.stopped || errors.length)throw new Error(JSON.stringify({evidence,errors}));
 for(const link of evidence.links)if(!fs.existsSync(path.join(root,link)))throw new Error('Missing download '+link);
 await page.screenshot({path:path.join(root,'Report preview.png')});
 await page.setViewportSize({width:390,height:844});
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);
 if(overflow)throw new Error('Mobile body overflow');
 fs.writeFileSync(path.join(root,'HTML QA.json'),JSON.stringify({evidence,errors,mobile_overflow:overflow},null,2));
 await browser.close();console.log('HTML QA passed');
})().catch(e=>{console.error(e);process.exit(1)});
