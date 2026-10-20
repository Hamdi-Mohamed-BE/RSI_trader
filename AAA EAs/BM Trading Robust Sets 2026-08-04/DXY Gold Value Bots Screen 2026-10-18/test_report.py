"""Read-only report contract, receipt-binding, and isolated JavaScript checks."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

import report


class ReportTests(unittest.TestCase):
    def test_payload_has_exact_frozen_outcome_counts(self):
        data = report.payload()
        plan = data["plan"]
        expected = {(p["id"], ea, cost, view) for p in plan["periods"]
                    for ea in (*plan["scope"], "combined")
                    for cost in ("recorded", "stress") for view in ("baseline", "primary", "secondary")}
        actual = {(r["period"], r["ea"], r["cost"], r["view"]) for r in data["results"]}
        self.assertEqual(actual, expected)
        self.assertEqual(len(data["results"]), len(expected))
        self.assertEqual(len(data["rows"]), data["source_audit"]["validated_rows"])
        self.assertEqual(sum(data["source_audit"]["counts"].values()), len(data["rows"]))
        self.assertEqual(len(data["features"]), len(data["rows"]))
        self.assertEqual(set(data["sources"]), set(plan["scope"]))
        self.assertEqual(data["results_sha256"], hashlib.sha256((report.ROOT / "RESULTS.json").read_bytes()).hexdigest())

    def test_pending_receipt_is_not_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(report.verified_receipt(Path(folder) / "none.json", "x")["status"], "PENDING")

    def test_only_matching_pass_receipt_is_displayed(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "receipt.json"
            for receipt, expected in [
                ({"status": "PASS", "result_sha256": "right", "checks": 123}, "PASS"),
                ({"status": "PASS", "results_sha256": "right", "checks": 123}, "PASS"),
                ({"status": "PASS", "result_sha256": "old", "checks": 123}, "NOT BOUND"),
                ({"status": "FAIL", "result_sha256": "right", "checks": 123}, "NOT BOUND"),
                ({"status": "PASS", "checks": 123}, "NOT BOUND"),
            ]:
                p.write_text(json.dumps(receipt), encoding="utf-8")
                self.assertEqual(report.verified_receipt(p, "right")["status"], expected)

    def test_required_disclosures_are_present(self):
        for phrase in ("not a new native filtered-EA backtest", "no compounding", "unrestricted",
                       "not floating equity", "not an official ICE", "15% real ticks globally",
                       "counterfactual later signals", "not a genuinely untouched",
                       "original trade unchanged", "not a winner selected", "No live bots",
                       "two-consecutive-loss daily pause", "shadow signals",
                       "current original M15", "long-only", "12 invalid-stop hits",
                       "two unique rejected buy attempts", "admitted fills",
                       "separate from the earlier EMA3/ORB screen", "native filled entry timestamp",
                       "not an executable cross-feed latency guarantee", "1ms close-order epsilon",
                       "not measured millisecond execution precision", "not a feasible funded-account path"):
            self.assertIn(phrase, report.HTML)
        self.assertNotIn("fetch(", report.HTML)
        self.assertNotIn("XMLHttpRequest", report.HTML)
        self.assertNotIn('src="http', report.HTML)

    def test_default_and_table_boundaries(self):
        self.assertIn("period:'1y'", report.HTML)
        self.assertIn("cost:'recorded'", report.HTML)
        self.assertIn('<table id="monthly"></table>', report.HTML)
        self.assertIn('<table id="trades"></table>', report.HTML)
        self.assertIn("return html+'</tbody></table>'", report.HTML)

    @unittest.skipUnless(shutil.which("node"), "Node unavailable")
    def test_all_period_cost_ea_and_trade_filters_execute(self):
        # A minimal detached DOM avoids opening a browser or changing any app.
        js = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(PATH,'utf8'),elements={};
class E{constructor(){this.children=[];this.dataset={};this.attrs={};this.textContent='';this.innerHTML='';this.value='';this.classList={toggle(){}};}setAttribute(k,v){this.attrs[k]=v;}append(e){this.children.push(e);}getAttribute(k){return this.attrs[k];}}
for(const hit of html.matchAll(/<[^>]+\bid="([^"]+)"[^>]*>/g))elements[hit[1]]=new E();
elements['embedded-data'].textContent=html.match(/<script id="embedded-data" type="application\/json">([\s\S]*?)<\/script>/)[1];
const document={getElementById:id=>{assert.ok(elements[id],id);return elements[id];},createElement:()=>new E(),querySelectorAll:()=>elements.periods.children};
const context=vm.createContext({document,console});
const script=html.match(/<script>\s*([\s\S]*?)<\/script>\s*<\/body>/)[1];
vm.runInContext(script,context);
const config=JSON.parse(elements['embedded-data'].textContent),keys=['combined',...config.plan.scope];
assert.equal(elements.periods.children.length,config.plan.periods.length);assert.equal(elements.ea.children.length,keys.length);
assert.equal(elements.scopeCount.textContent,String(config.plan.scope.length));
const period1y=config.plan.periods.find(p=>p.id==='1y');
assert.ok(elements.window.textContent.includes(period1y.start));assert.ok(elements.window.textContent.includes(period1y.end_exclusive));
assert.match(elements.comparison.innerHTML,/<table><thead>/);
assert.ok(elements.comparison.innerHTML.includes('Combined '+config.plan.scope.length+' EAs'));
assert.equal((elements.comparison.innerHTML.match(/<tr/g)||[]).length,config.plan.scope.length+2);
const audit=config.source_audit,fnum=x=>x.toLocaleString('en-US',{minimumFractionDigits:0,maximumFractionDigits:0});
assert.ok(elements.verification.innerHTML.includes(fnum(audit.validated_rows)+' natural closed positions'));
assert.ok(elements.verification.innerHTML.includes(fnum(audit.native_deals_reconciled)+' native deals reconciled'));
assert.ok(elements.verification.innerHTML.includes(fnum(audit.initial_stop_normalizations_checked)+' initial-stop normalizations checked'));
assert.ok(!elements.verification.innerHTML.includes('— accounting checks'));
let renders=0;
for(const p of config.plan.periods)for(const cost of ['recorded','stress'])for(const ea of keys){
 const period=p.id;
 vm.runInContext('Object.assign(state,'+JSON.stringify({period,cost,ea})+');render()',context);
 const expected=config.plan.periods.find(x=>x.id===period);
 assert.ok(elements.window.textContent.includes(expected.start));assert.ok(elements.window.textContent.includes(expected.end_exclusive));
 assert.match(elements.monthly.innerHTML,/<thead>/);assert.match(elements.coverage.innerHTML,/candidates have valid/);
 assert.match(elements.secondary.innerHTML,/<table>/);
 const base=config.results.find(x=>x.period===period&&x.cost===cost&&x.ea===ea&&x.view==='baseline');
 const filtered=config.results.find(x=>x.period===period&&x.cost===cost&&x.ea===ea&&x.view==='primary');
 const impaired=[...base.curve,...filtered.curve].some(x=>x.balance<=0);
 assert.equal(elements.capitalWarning.hidden,!impaired);
 if(impaired)assert.match(elements.capitalWarning.textContent,/not a feasible funded-account path/);
 for(const mode of ['vetoed','all','missing']){
  vm.runInContext('state.tradeView='+JSON.stringify(mode)+';renderTrades()',context);
  assert.ok(!elements.trades.innerHTML.includes('NaN'));assert.ok(!elements.stats.innerHTML.includes('NaN'));
  assert.match(elements.trades.innerHTML,/<thead>/);
 }
 renders++;
}
const feature=config.features.find(f=>f.primary_veto),row=config.rows.find(r=>r.key+':'+Number(r.position_id)===feature.id);
if(row){
 vm.runInContext('state.cost="stress"',context);
 const result=vm.runInContext('normalizedCash('+JSON.stringify(row)+')',context);
 const expected=(row.unit_gross+row.unit_comm+row.unit_swap-config.plan.stress.extra_per_lot_roundtrip+Math.min(0,row.unit_swap))/row.unit_risk*config.plan.metrics.fixed_initial_stop_risk;
 assert.ok(Math.abs(result-expected)<1e-9);
}
assert.ok(elements.footer.innerHTML.includes(config.results_sha256));
process.stdout.write(JSON.stringify({status:'PASS',render_combinations:renders,trade_modes:3}));
'''
        js = js.replace("PATH", json.dumps(str(report.ROOT / "Results.html")))
        p = subprocess.run([shutil.which("node"), "-e", js], capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, p.stdout + "\n" + p.stderr)
        plan = report.read(report.ROOT / "PLAN.json")
        self.assertEqual(json.loads(p.stdout)["render_combinations"], len(plan["periods"]) * 2 * (len(plan["scope"]) + 1))


if __name__ == "__main__":
    unittest.main()

