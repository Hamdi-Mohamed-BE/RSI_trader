const {chromium}=require('C:/Users/hama101/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const {pathToFileURL}=require('node:url');
const fs=require('node:fs');const path=require('node:path');
(async()=>{
  const browser=await chromium.launch({headless:true,args:['--disable-gpu']});
  try{
    const page=await browser.newPage({viewport:{width:1400,height:1050}});
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto(pathToFileURL(path.join(__dirname,'Results.html')).href);
    const text=await page.locator('body').innerText();
    for(const x of ['Gold','US100','Bitcoin','-7.95','-3.26','-7.84','100% real ticks','not fixed 3R','No live']){
      if(!text.includes(x))throw Error('Missing report evidence: '+x);
    }
    if(await page.locator('table').count()!==7)throw Error('Missing metric table');
    if(await page.locator('svg polyline').count()!==3)throw Error('Missing independent asset curve');
    const downloads=await page.locator('a[href$="-trades.csv"]').evaluateAll(a=>a.map(x=>x.getAttribute('href')));
    if(downloads.length!==6 || downloads.some(x=>!fs.existsSync(path.join(__dirname,x))))throw Error('Trade download unavailable');
    await page.screenshot({path:path.join(__dirname,'Report preview.png')});
    await page.setViewportSize({width:420,height:850});
    if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2))throw Error('Mobile page overflow');
    if(errors.length)throw Error(errors.join('\n'));
    console.log(JSON.stringify({render:'passed',tables:7,curves:3,downloads:6,mobile_overflow:false,errors:0}));
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
