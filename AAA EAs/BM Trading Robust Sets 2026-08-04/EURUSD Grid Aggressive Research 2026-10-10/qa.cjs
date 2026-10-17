const {chromium}=require('C:/Users/hama101/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const {pathToFileURL}=require('url');const fs=require('fs');const path=require('path');
(async()=>{
 const root=__dirname,browser=await chromium.launch({headless:true,args:['--disable-gpu']});
 const page=await browser.newPage({viewport:{width:1550,height:1100}});let errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.goto(pathToFileURL(path.join(root,'Results.html')).href);
 if(await page.locator('details.case').count()!==38)throw Error('Expected 36 new + 2 controls');
 const links=await page.locator('a').evaluateAll(xs=>xs.map(x=>x.getAttribute('href')).filter(x=>!x.startsWith('https:')));
 for(const x of links)if(!fs.existsSync(path.resolve(root,x)))throw Error('Missing '+x);
 await page.getByRole('button',{name:'Capped research',exact:true}).click();
 if(await page.locator('details.case:not(.hidden)').count()!==30)throw Error('Capped filter');
 await page.getByRole('button',{name:'Uncapped stress',exact:true}).click();
 if(await page.locator('details.case:not(.hidden)').count()!==6)throw Error('Stress filter');
 await page.getByRole('button',{name:'All cases',exact:true}).click();await page.screenshot({path:path.join(root,'Report preview.png')});
 await page.setViewportSize({width:390,height:844});const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
 if(overflow||errors.length)throw Error(JSON.stringify({overflow,errors}));
 fs.writeFileSync(path.join(root,'HTML QA.json'),JSON.stringify({cases:38,links:links.length,filters_passed:true,mobile_overflow:overflow,errors},null,2));
 await browser.close();console.log('HTML QA passed');
})().catch(e=>{console.error(e);process.exit(1)});
