// Local artifact logic QA; not browser automation or live-site manipulation.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(path.join(__dirname,'Results.html'),'utf8');
const raw=html.match(/<script id="research-data" type="application\/json">([\s\S]*?)<\/script>/)[1];
const data=JSON.parse(raw),code=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)[1];
const values={policy:'guarded_buffer_7',method:'bootstrap',floating:'full_stop_reserve_stress',cost:'',period:'1y','date-portfolio':'ftmo','date-firm':'ftmo'};
const elements={};for(const id of ['research-data','rules','policy','method','floating','cost','period','policy-note','mode-note','challenge-table','diagnostics','comparison','literal-warning','history-cards','date-portfolio','date-firm','dates','membership','limits','source-hash','engine-hash']){
  elements[id]={value:values[id],checked:false,textContent:id==='research-data'?raw:'',innerHTML:'',classList:{toggle(){}},addEventListener(){}};
}
const sandbox={document:{getElementById:id=>{assert.ok(elements[id],`Unknown element ${id}`);return elements[id]}}};
vm.createContext(sandbox);vm.runInContext(code,sandbox);
const count=(id,pattern)=>(elements[id].innerHTML.match(pattern)||[]).length;
let runs=0;for(const policy of data.plan.policies)for(const method of ['bootstrap','rolling'])for(const floating of ['closed_only','full_stop_reserve_stress'])for(const cost of [false,true])for(const period of ['1y','6m','3m']){
  Object.assign(elements.policy,{value:policy});elements.method.value=method;elements.floating.value=floating;elements.cost.checked=cost;elements.period.value=period;
  vm.runInContext('render()',sandbox);
  assert.equal(count('challenge-table',/<tr>/g),12);assert.equal(count('diagnostics',/<tr>/g),12);assert.equal(count('comparison',/<tr>/g),12);
  assert.equal(count('history-cards',/<article /g),4);assert.equal(count('dates',/<tr>/g),27);
  assert.equal(elements['challenge-table'].innerHTML.includes('undefined'),false);
  assert.equal(elements['history-cards'].innerHTML.includes('NaN'),false);
  runs++;
}
for(const p of Object.keys(data.plan.members))for(const f of data.plan.firms){elements['date-portfolio'].value=p;elements['date-firm'].value=f.id;vm.runInContext('renderDates()',sandbox);assert.equal(count('dates',/<tr>/g),27)}
assert.equal(data.native_mt5_execution,false);assert.equal(data.live_changes,false);assert.equal(data.results.length,360);
assert.ok(data.plan.limitations.some(s=>s.includes('<=')||s.includes('NOT')));
console.log(`Passed ${runs} report-control combinations, 12 date views, data decoding and table counts.`);
