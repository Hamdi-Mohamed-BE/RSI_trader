const {chromium}=require('C:/Users/hama101/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path');
(async()=>{
 const root=__dirname,browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1050}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto('file:///'+path.join(root,'Results.html').replace(/\\/g,'/'));
 await page.screenshot({path:path.join(root,'Preview.png'),fullPage:false});
 const links=await page.locator('a[href]').evaluateAll(xs=>xs.map(x=>x.getAttribute('href')));
 for(const link of links)if(!/^https?:/.test(link)&&!fs.existsSync(path.join(root,decodeURIComponent(link))))throw Error('Broken link '+link);
 if(await page.locator('svg').count()!==2)throw Error('Expected two charts');
 await page.locator('svg').first().screenshot({path:path.join(root,'Balance Preview.png')});
 await page.setViewportSize({width:420,height:950});await page.evaluate(()=>window.scrollTo(0,0));
 await page.screenshot({path:path.join(root,'Mobile Preview.png'),fullPage:false});
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
 if(overflow||errors.length)throw Error('Layout/script errors '+JSON.stringify(errors));
 fs.writeFileSync(path.join(root,'html-qa.json'),JSON.stringify({ok:true,charts:2,links:links.length,mobile_overflow:false,errors},null,2));
 await browser.close();console.log('HTML QA passed');
})().catch(e=>{console.error(e);process.exit(1)});
