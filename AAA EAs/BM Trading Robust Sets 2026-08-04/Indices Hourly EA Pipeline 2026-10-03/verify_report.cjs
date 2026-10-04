const fs=require('fs'),vm=require('vm'),path=require('path');
const html=fs.readFileSync(path.join(__dirname,'Results.html'),'utf8');
const code=html.match(/<script>([\s\S]*)<\/script>/)[1];
const elements=new Map();const document={querySelector(id){if(!elements.has(id))elements.set(id,{value:id==='#window'?'1y':'',innerHTML:'',addEventListener(event,fn){this.handler=fn}});return elements.get(id)}};
const ctx={document};vm.createContext(ctx);vm.runInContext(code,ctx,{timeout:30000});
for(const horizon of ['1y','3m','3y','5y','real2026']){
 const el=document.querySelector('#window');el.value=horizon;el.handler();
 for(const id of ['#performance','#hours','#charts','#overlay','#calendar']){
  const s=document.querySelector(id).innerHTML;if(!s||/NaN|undefined|Infinity/.test(s))throw Error(id+' malformed '+horizon);
 }
 if((document.querySelector('#charts').innerHTML.match(/<svg/g)||[]).length!==3)throw Error('Expected 3 charts');
 if(!document.querySelector('#performance').innerHTML.includes('US100'))throw Error('Missing asset');
}
if(html.includes('const DATA=__DATA__'))throw Error('Data not injected');
if(!document.querySelector('#coverage-hours').innerHTML.includes('15:00'))throw Error('Missing qualifying hour');
console.log('5 horizons, 3 asset charts each, overlay, tables and MC panels rendered without invalid numbers');
