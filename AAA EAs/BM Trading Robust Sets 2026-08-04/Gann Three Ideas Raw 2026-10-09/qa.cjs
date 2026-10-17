const {chromium}=require('C:/Users/hama101/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const {pathToFileURL}=require('node:url');const fs=require('node:fs');const path=require('node:path');
(async()=>{
  const summary=JSON.parse(fs.readFileSync(path.join(__dirname,'SUMMARY.json'),'utf8'));
  if(!summary.complete || summary.completed!==42)throw Error('Cannot deliver incomplete research');
  const browser=await chromium.launch({headless:true,args:['--disable-gpu']});
  try{
    const page=await browser.newPage({viewport:{width:1550,height:1050}});const errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto(pathToFileURL(path.join(__dirname,'Results.html')).href);
    const text=await page.locator('body').innerText();
    for(const x of ['42 / 42','Gold','US100','Bitcoin','0.5%','two-year validation','100%','No live','Calendar-year returns']){
      if(!text.includes(x))throw Error('Missing evidence: '+x);
    }
    if(await page.locator('table').count()!==10)throw Error('Missing metric table');
    if(await page.locator('svg').count()!==3 || await page.locator('svg polyline').count()!==21)throw Error('Missing account curve');
    await page.locator('summary').filter({hasText:'Native audits'}).click();
    const downloads=await page.locator('a[href$="-trades.csv"]').evaluateAll(a=>a.map(x=>x.getAttribute('href')));
    if(downloads.length!==42 || downloads.some(x=>!fs.existsSync(path.join(__dirname,x))))throw Error('Unavailable trade breakdown');
    await page.locator('summary').filter({hasText:'Native audits'}).click();
    await page.evaluate(()=>window.scrollTo(0,0));
    await page.screenshot({path:path.join(__dirname,'Report preview.png')});
    await page.setViewportSize({width:420,height:850});
    if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2))throw Error('Mobile page overflow');
    if(errors.length)throw Error(errors.join('\n'));
    console.log(JSON.stringify({render:'passed',tables:10,charts:3,curves:21,downloads:42,mobile_overflow:false,js_errors:0}));
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
