const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const html=fs.readFileSync(path.join(__dirname,'../../top 5/Performance and Setup.html'),'utf8');
const nodes={};
function node(id){return nodes[id]??=( {value:({risk:'fixed',period:'6m',selection:'all',customBalance:'10000',customRisk:'1'})[id]??'',hidden:false,textContent:'',innerHTML:'',children:[],setAttribute(){},getAttribute(){return '0 0 720 300'},replaceChildren(...v){this.children=v;this.innerHTML=''},append(...v){this.children.push(...v)},addEventListener(){},querySelectorAll(){return []},scrollIntoView(){}});}
const ctx=vm.createContext({document:{getElementById:node,createElementNS:()=>node(Symbol()),createElement:()=>node(Symbol())},console});
vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],ctx);
const run=s=>vm.runInContext(s,ctx);
assert(node('cards').innerHTML.includes('MAX CLOSED-BALANCE DRAWDOWN'));
assert(node('cards').innerHTML.includes('6.36%'));
assert.strictEqual((node('eaDetailCards').innerHTML.match(/<article /g)||[]).length,5);
assert.strictEqual((node('eaDetailCards').innerHTML.match(/Exact shipped settings/g)||[]).length,5);
assert(node('eaDetailCards').innerHTML.includes('STANDARD ORB edition'));
assert(node('eaDetailCards').innerHTML.includes('CURRENT BALANCE'));
assert(!node('eaDetailCards').innerHTML.includes('undefined'));
assert.strictEqual(run('Object.keys(DATA.ea_details.entries).length'),5);
assert.strictEqual((node('eaDetailCards').innerHTML.match(/https:\/\/calyx.duckdns.org\/eas\//g)||[]).length,5);
assert.strictEqual((node('eaDetailCards').innerHTML.match(/\?period=6m/g)||[]).length,5);
for(const mode of ['fixed','balance','custom'])for(const period of ['3m','6m'])for(const slug of ['all',...run('DATA.bots.map(b=>b.slug)')]){
 node('risk').value=mode;node('period').value=period;node('selection').value=slug;run('render()');
 assert(!/NaN|Infinity/.test(node('cards').innerHTML));assert(node('balanceChart').children.length>0);
 if(mode==='custom')assert(node('kind').textContent.includes('ESTIMATE'));
 if(mode!=='custom'&&slug!=='all')assert(node('cards').innerHTML.includes('MAX EQUITY DRAWDOWN'));
}
const baseline=run("DATA.datasets.fixed['6m'].all.net_profit");
assert(Math.abs(run("customStats(DATA.datasets.fixed['6m'].all,20000,0.5).net_profit")-baseline)<1e-8);
assert(Math.abs(run("customStats(DATA.datasets.fixed['6m'].all,10000,2).net_profit")-2*baseline)<1e-8);
assert.strictEqual(run('maxCashDrawdown([[0,100],[1,120],[2,90],[3,110]])'),30);
node('risk').value='custom';node('customBalance').value='0';run('render()');assert(node('scope').textContent.includes('Invalid'));assert.strictEqual(node('cards').innerHTML,'');
node('customBalance').value='20000';node('customRisk').value='0.5';run('render()');assert(node('cards').innerHTML.length>0);
assert(run("customStats(DATA.datasets.fixed['6m'].all,20000,0.5).equity_dd_pct")===null);
console.log('PASS: 36 report scenarios, custom scaling, drawdown math, input validation/recovery; native equity preserved, estimates labelled.');
