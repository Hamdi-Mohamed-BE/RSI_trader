const {chromium}=require('C:/Users/hama101/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const {pathToFileURL}=require('url');const fs=require('fs');const path=require('path');
(async()=>{
 const root=__dirname;const browser=await chromium.launch({headless:true,args:['--disable-gpu']});
 const result=JSON.parse(fs.readFileSync(path.join(root,'SUMMARY.json'),'utf8'));
 if(result.verification.completed!==26||Object.keys(result.verification.failed).length)throw Error('Incomplete native batch');
 const page=await browser.newPage({viewport:{width:1500,height:1100}});let errors=[];
 page.on('pageerror',e=>errors.push(String(e)));
 await page.goto(pathToFileURL(path.join(root,'Results.html')).href);
 const first=await page.locator('section.window:not(.hidden)').count();if(first!==1)throw Error('Initial period visibility');
 await page.getByRole('button',{name:'Three years',exact:true}).click();
 if(await page.locator('section.window:not(.hidden)').getAttribute('data-window')!=='3y')throw Error('3y filter');
 await page.getByRole('button',{name:'Both',exact:true}).click();
 if(await page.locator('section.window:not(.hidden)').count()!==2)throw Error('Both filter');
 const evidence=await page.evaluate(()=>({title:document.title,tables:document.querySelectorAll('section table').length,
  rowCounts:[...document.querySelectorAll('section table tbody')].map(x=>x.querySelectorAll('tr').length),cases:document.querySelectorAll('details.case').length,
  links:[...document.querySelectorAll('a[href$=".csv"],a[href$=".htm"]')].map(x=>x.getAttribute('href'))}));
 if(evidence.rowCounts.some(x=>x!==13)||evidence.cases!==26||errors.length)throw Error(JSON.stringify({evidence,errors}));
 for(const link of evidence.links)if(!fs.existsSync(path.join(root,link)))throw Error('Missing '+link);
 await page.getByRole('button',{name:'Last year',exact:true}).click();
 await page.screenshot({path:path.join(root,'Report preview.png')});
 await page.setViewportSize({width:390,height:844});
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);
 if(overflow)throw Error('Mobile overflow');
 fs.writeFileSync(path.join(root,'HTML QA.json'),JSON.stringify({evidence,errors,mobile_overflow:overflow},null,2));
 await browser.close();console.log('HTML QA passed');
})().catch(e=>{console.error(e);process.exit(1)});
