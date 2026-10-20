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
        self.assertEqual(len(data["results"]), 216)
        self.assertEqual(len(data["rows"]), 830)
        self.assertEqual(len(data["features"]), 830)
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
                       "original trade unchanged", "not a winner selected", "No live bots"):
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
assert.equal(elements.periods.children.length,6);assert.equal(elements.ea.children.length,6);
assert.match(elements.window.textContent,/2025-10-06.*2026-10-06/);
assert.match(elements.comparison.innerHTML,/<table><thead>/);assert.match(elements.comparison.innerHTML,/Combined five EAs/);
assert.equal((elements.comparison.innerHTML.match(/<tr/g)||[]).length,7);
assert.match(elements.verification.innerHTML,/830 natural closed positions/);
assert.match(elements.verification.innerHTML,/1,660 native deals reconciled/);
assert.match(elements.verification.innerHTML,/830 initial-stop normalizations checked/);
assert.ok(!elements.verification.innerHTML.includes('— accounting checks'));
const config=JSON.parse(elements['embedded-data'].textContent),keys=['combined',...config.plan.scope];
let renders=0;
for(const period of ['3m','6m','1y','2y','3y','5y'])for(const cost of ['recorded','stress'])for(const ea of keys){
 vm.runInContext('Object.assign(state,'+JSON.stringify({period,cost,ea})+');render()',context);
 const expected=config.plan.periods.find(x=>x.id===period);
 assert.ok(elements.window.textContent.includes(expected.start));assert.ok(elements.window.textContent.includes(expected.end_exclusive));
 assert.match(elements.monthly.innerHTML,/<thead>/);assert.match(elements.coverage.innerHTML,/candidates have valid/);
 assert.match(elements.secondary.innerHTML,/<table>/);
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
 const expected=(row.unit_gross+row.unit_comm+row.unit_swap-config.plan.stress.extra_per_lot_roundtrip+Math.min(0,row.unit_swap))/row.unit_risk*100;
 assert.ok(Math.abs(result-expected)<1e-9);
}
assert.ok(elements.footer.innerHTML.includes(config.results_sha256));
process.stdout.write(JSON.stringify({status:'PASS',render_combinations:renders,trade_modes:3}));
'''
        js = js.replace("PATH", json.dumps(str(report.ROOT / "Results.html")))
        p = subprocess.run([shutil.which("node"), "-e", js], capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, p.stdout + "\n" + p.stderr)
        self.assertEqual(json.loads(p.stdout)["render_combinations"], 72)


if __name__ == "__main__":
    unittest.main()
