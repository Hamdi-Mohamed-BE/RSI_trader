"""Focused two-EA report; earlier reports and frozen ledgers stay read-only."""
from collections import Counter
from datetime import datetime,timezone
import importlib.util
import hashlib
import json
from pathlib import Path
from urllib.parse import quote

ROOT=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location('actual5_readonly_report_helpers',ROOT.parent/'report.py')
prior=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prior)
h,cash,percent,number,table=prior.h,prior.cash,prior.percent,prior.number,prior.table
SLUGS=('xau-rsi-vwap','nasdaq-5m-candle-momentum')


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def reference_results(data):
    if not data:
        return []
    return prior.split_results(data)[0]


def comparison(results, reference):
    """Pair policies and cost bases; never subtract component P&L."""
    rows=[]
    for result in results:
        matches=[r for r in reference if r.get('scenario',{}).get('id')==result.get('scenario',{}).get('id')
                 and bool(r.get('stress'))==bool(result.get('stress'))]
        old=matches[0] if len(matches)==1 else None
        nm=result.get('metrics',{});om=old.get('metrics',{}) if old else {}
        delta=nm['return_pct']-om['return_pct'] if prior.base.finite(nm.get('return_pct')) and prior.base.finite(om.get('return_pct')) else None
        rows.append([prior.title(result),'Extra-cost sensitivity' if result.get('stress') else 'Source-account costs',
            nm.get('trades',0),om.get('trades','—'),cash(nm.get('ending_balance')),cash(om.get('ending_balance')),
            percent(nm.get('return_pct'),True),percent(om.get('return_pct'),True),
            (('+' if delta>0 else '')+number(delta)+' pp') if delta is not None else '—',
            prior.base.pf(nm),prior.base.pf(om),percent(nm.get('win_rate_pct')),percent(om.get('win_rate_pct')),
            percent(nm.get('max_sampled_equity_dd_pct')),percent(om.get('max_sampled_equity_dd_pct')),
            nm.get('open_positions',0),om.get('open_positions','—')])
    return table(['Risk policy','Cost basis','2 EAs closed','9 EAs closed','2 EAs ending cash','9 EAs ending cash',
        '2 EAs cash return','9 EAs cash return','Return difference','2 EAs closed PF','9 EAs closed PF',
        '2 EAs wins','9 EAs wins','2 EAs sampled DD','9 EAs sampled DD','2 EAs open','9 EAs open'],rows)


def open_exposure(result,plan):
    metrics=result.get('metrics',{})
    positions=result.get('open_positions',[])
    if not isinstance(positions,list):positions=[]
    equity,balance=metrics.get('ending_sampled_equity'),metrics.get('ending_balance')
    floating=equity-balance if prior.base.finite(equity) and prior.base.finite(balance) else None
    rows=[]
    finish=datetime.fromisoformat(plan['end_exclusive_utc']).timestamp()-1
    for p in positions:
        mark=p.get('mark_epoch')
        rows.append([prior.base.label(p.get('ea','')),prior.base.dt(p.get('op')),number(p.get('lots'),3),
            cash(p.get('initial_risk',p.get('risk'))),cash(p.get('paid_entry_cash'),True),
            prior.base.dt(mark),number(finish-mark,0) if prior.base.finite(mark) else 'No owned sample',
            cash(p.get('sampled_floating',p.get('floating')),True)])
    return ('<p><strong>'+h(metrics.get('open_positions',len(positions)))+' position(s) still open.</strong> '+
        'Total final sampled floating P&amp;L: '+h(cash(floating,True))+'. This is not banked or included in closed PF/win rate. Entry cash fees are already included in ending balance.</p>'+
        table(['EA','Opened UTC','Lots','Original stop risk','Entry cash already paid','Last owned mark UTC',
               'Seconds from last mark to UTC horizon','Final sampled floating P&L'],rows)+
        '<p class="muted">The last owned mark is carried forward, not interpolated from a future quote. Closed-session time to the UTC horizon is disclosed above; it is not a fresh quote. No artificial tester-end close is booked.</p>')


def evidence(root):
    if root is None:return ''
    names=('RESULTS.json','PLAN.json','FROZEN.json','VERIFICATION.json','../RESULTS.json','../FROZEN.json',
        '../../INPUTS.json','../../BROKER.json','../../FROZEN.json','../../DEMO-BENCHMARKS.json')
    return '<nav class="links" aria-label="Public evidence">'+' · '.join(
        '<a href="'+quote(name,safe='/..')+'">'+h(name)+'</a>' for name in names if (Path(root)/name).is_file())+'</nav>'


def findings(results, reference):
    source=[r for r in results if not r.get('stress')]
    rows=[]
    for r in source:
        m=r.get('metrics',{})
        rows.append(prior.title(r)+': '+percent(m.get('return_pct'),True)+' cash return, '+
            percent(m.get('ending_equity_return_pct'),True)+' sampled-equity return, '+
            str(m.get('trades',len(r.get('trades',[]))))+' closed positions and '+
            str(m.get('open_positions',0))+' still open.')
    text='<div class="warning"><strong>What the new two-EA replay shows</strong><ul>'+''.join('<li>'+h(x)+'</li>' for x in rows)+'</ul>'
    text+='<p>This is a fresh admission replay after filtering the candidate universe to these two EAs. Removing seven EAs changes overlap, reservations and future admission paths; it is not the old portfolio ledger minus seven P&amp;L rows. The same 10% daily / 20% initial-capital research controls remain in force.</p>'
    if source and all(r.get('metrics',{}).get('return_pct',0)<0 for r in source):
        text+='<p><strong>Both source-cost cash outcomes are negative.</strong> The reduced profile does not make 5% per trade a validated live setting.</p>'
    else:
        text+='<p>A better recent result still does not validate 5% per trade, compounding, or a future return target. These two already-exposed months are not a new out-of-sample test.</p>'
    fixed=next((r for r in source if r.get('scenario',{}).get('mode')=='fixed'),None)
    dynamic=next((r for r in source if r.get('scenario',{}).get('mode')=='percent'),None)
    stressed=next((r for r in results if fixed and r.get('stress') and r.get('scenario',{}).get('id')==fixed.get('scenario',{}).get('id')),None)
    if fixed and stressed:
        fm,sm=fixed.get('metrics',{}),stressed.get('metrics',{})
        if fm.get('return_pct',0)>0 and sm.get('return_pct',0)<0:
            text+='<p><strong>The positive fixed-risk result is not cost-robust in this replay.</strong> '+h(
                'Fixed $50 source costs show '+percent(fm.get('return_pct'),True)+' cash return; '+
                'the extra-cost sensitivity shows '+percent(sm.get('return_pct'),True)+
                '. Guards admit different trades in those two paths, so the difference is not a paired-fee deduction.')+'</p>'
    if fixed and dynamic:
        matched={d.get('id'):d for d in dynamic.get('decisions',[])}
        admitted_fixed=[d for d in fixed.get('decisions',[]) if d.get('reason')=='opened']
        lotdiff=next((d for d in admitted_fixed if matched.get(d.get('id'),{}).get('reason')=='opened'
            and abs(d.get('volume',0)-matched[d['id']].get('volume',0))>1e-9),None)
        admissiondiff=next((d for d in fixed.get('decisions',[]) if d.get('id') in matched and
            (d.get('reason')=='opened')!=(matched[d['id']].get('reason')=='opened')),None)
        examples=[]
        if lotdiff:
            alt=matched[lotdiff['id']]
            examples.append('First lot-size difference: '+prior.base.dt(lotdiff.get('epoch'))+' UTC, '+
                prior.base.label(lotdiff.get('ea',''))+' fixed '+number(lotdiff.get('volume'),3)+
                ' lots versus compounded '+number(alt.get('volume'),3)+' lots; the dynamic budget was '+cash(alt.get('budget'))+'.')
        if admissiondiff:
            alt=matched[admissiondiff['id']]
            dynamic_close=next((t for t in dynamic.get('trades',[]) if t.get('id')==alt.get('id')),None)
            examples.append('First admission difference: '+prior.base.dt(admissiondiff.get('epoch'))+' UTC, '+
                prior.base.label(admissiondiff.get('ea',''))+'. Fixed equity '+cash(admissiondiff.get('equity'))+
                ' led to '+prior.base.REASONS.get(admissiondiff.get('reason'),admissiondiff.get('reason',''))+
                '; compounded equity '+cash(alt.get('equity'))+' led to '+
                prior.base.REASONS.get(alt.get('reason'),alt.get('reason',''))+
                (', and the compounded position closed '+cash(dynamic_close.get('net'),True) if dynamic_close else '')+'.')
        if examples:
            text+='<p><strong>Why fixed and compounded results can separate sharply:</strong> lot-step rounding and guard decisions create different trade paths—not proof that compounding is inherently worse.</p><ul>'+''.join('<li>'+h(s)+'</li>' for s in examples)+'</ul>'
    text+='</div>'
    # Keep the independently derived cost-path explanation, without its generic
    # earlier profile headline, when the selected trade sets actually differ.
    path_note=prior.outcome_note(results)
    if 'Not a paired-trade cost comparison' in path_note:
        start=path_note.find('<p><strong>Not a paired-trade cost comparison')
        text+='<div class="warning">'+path_note[start:path_note.rfind('</div>')]+'</div>'
    return text


def cash_bridge(results,initial):
    rows=[]
    for r in results:
        m=r.get('metrics',{});closed=sum(t.get('net',0) for t in r.get('trades',[]))
        balance=m.get('ending_balance');equity=m.get('ending_sampled_equity')
        cash_profit=balance-initial if prior.base.finite(balance) else None
        adjustment=cash_profit-closed if prior.base.finite(cash_profit) else None
        floating=equity-balance if prior.base.finite(equity) and prior.base.finite(balance) else None
        rows.append([prior.title(r),'Extra-cost sensitivity' if r.get('stress') else 'Source costs',
            cash(closed,True),cash(adjustment,True),cash(cash_profit,True),cash(floating,True),cash(equity)])
    return table(['Policy','Cost basis','Whole closed-position net','Other paid cash / open entry charges',
        'Cash profit since $1,000','Unrealized sampled floating','Ending sampled equity'],rows)


def threshold_note(verification,initial):
    if not verification or verification.get('status')!='PASS':return ''
    fixed=next((d for d in verification.get('cost_path_diagnostics',[]) if d.get('scenario')=='fixed50'),None)
    pair=fixed.get('first_admission_divergence',{}) if fixed else {}
    original,stress=pair.get('recorded',{}),pair.get('stress',{})
    a,b=original.get('projected_protected_cash'),stress.get('projected_protected_cash')
    floor=initial*.8
    if not(prior.base.finite(a) and prior.base.finite(b) and a>=floor>b):return ''
    text=('Independent guard-path audit: at '+prior.base.dt(original.get('epoch'))+' UTC, '+
        'the fixed-$50 source path projected protected cash of $'+number(a,4)+
        ' and admitted the Nasdaq candidate. With the extra-cost path it was $'+number(b,4)+
        ', missing the $'+number(floor,2)+' admission buffer by only $'+number(floor-b,4)+
        '. That tiny threshold crossing rejected the same winning source trade and changed later admissions. '+
        'The apparent best result is therefore highly guard-threshold sensitive, not a robustly validated edge.')
    return '<div class="warning"><strong>A fragile admission threshold</strong><p>'+h(text)+'</p></div>'


def render(data, reference=None, root=None,verification=None):
    results=reference_results(data)
    if not results:raise ValueError('No completed two-EA outcomes')
    plan=prior.normalized_plan(data)
    # Candidate filtering is part of the frozen replay, not report-side ledger
    # subtraction. Refuse misleading membership rather than hide extra EAs.
    actual=set(plan.get('priority',[]))
    if actual!=set(SLUGS):raise ValueError('The report requires exactly Nasdaq 5M and XAU RSI VWAP')
    reference=reference_results(reference)
    sections=[]
    for i,r in enumerate(results):
        monthly,daily=prior.monthly(r,plan)
        reasons=Counter(d.get('reason','unknown') for d in r.get('decisions',[]))
        reason_table=table(['Entry decision','Count'],[[prior.base.REASONS.get(k,k),v] for k,v in sorted(reasons.items())])
        sections.append('<section id="view-'+str(i)+'"><h2>'+h(prior.title(r))+' · '+
            h('extra-cost sensitivity' if r.get('stress') else 'source-account costs')+'</h2>'+
            '<h3>Each EA’s admitted results</h3>'+prior.per_ea(r,plan)+
            '<h3>Open positions and sampled marks</h3>'+open_exposure(r,plan)+
            '<h3>Monthly cash changes</h3>'+monthly+
            '<details><summary>Every daily date and cash change</summary>'+daily+'</details>'+
            '<details><summary>All closed positions · trade by trade</summary>'+prior.ledger(r)+'</details>'+
            '<details><summary>Every entry decision and guard count</summary>'+reason_table+prior.decisions(r)+'</details>'+
            '<details><summary>Sample and guard receipts</summary><pre>'+h(json.dumps(dict(
                scenario=r.get('scenario'),mark_quality=r.get('mark_quality'),
                first_breach_epoch=r.get('metrics',{}).get('first_breach_epoch'),
                paused_days=r.get('metrics',{}).get('paused_days')),indent=2,allow_nan=False))+'</pre></details></section>')
    tokens={
        '@@WINDOW@@':h(plan['start_utc'])+' → '+h(plan['end_exclusive_utc'])+' (end exclusive)',
        '@@INITIAL@@':cash(plan.get('initial_balance',1000)),
        '@@FINDINGS@@':findings(results,reference),'@@SUMMARY@@':prior.summary_table(results,plan.get('initial_balance',1000)),
        '@@COMPARE@@':comparison(results,reference),'@@ADMISSIONS@@':prior.admission_table(results),
        '@@CASHBRIDGE@@':cash_bridge(results,plan.get('initial_balance',1000)),
        '@@THRESHOLD@@':threshold_note(verification,plan.get('initial_balance',1000)),
        '@@CURVES@@':prior.chart(results,False)+prior.chart(results,True),
        '@@DETAILS@@':''.join(sections),'@@EVIDENCE@@':evidence(root),
        '@@POLICY@@':h(json.dumps(plan,indent=2,allow_nan=False)),
    }
    html=TEMPLATE
    for key,value in tokens.items():html=html.replace(key,value)
    return html


TEMPLATE='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Nasdaq 5M + RSI VWAP · actual 5% risk replay</title><style>
:root{color-scheme:dark;--bg:#07130f;--panel:#0d231b;--ink:#eafff5;--muted:#aac9bd;--line:#254b3c;--green:#73ebba;--blue:#a2c1ff;--warn:#ffda95}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.65 system-ui,-apple-system,"Segoe UI",sans-serif}main{max-width:1450px;margin:auto;padding:36px 24px 70px}h1{font-size:clamp(30px,4vw,48px);line-height:1.14;max-width:1050px}h2{font-size:25px;line-height:1.25}h3{font-size:18px;margin:24px 0 12px}p,ul{max-width:1160px}.eyebrow{font:12px ui-monospace,monospace;letter-spacing:.12em;color:var(--green);text-transform:uppercase}.muted{color:var(--muted)}a{color:var(--green)}section{border-top:1px solid var(--line);padding-top:26px;margin-top:32px}.warning{border:1px solid #78633a;background:#2b271b;color:var(--warn);padding:18px 22px;border-radius:12px;margin:22px 0}.table-wrap{max-width:100%;overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums}th,td{padding:13px 10px;border-bottom:1px solid var(--line);text-align:right;vertical-align:top}th{color:var(--muted);min-width:95px}td{white-space:nowrap}td:first-child,th:first-child{text-align:left;min-width:170px}td:nth-child(2){white-space:normal}tbody tr:hover{background:#102a20}details{margin:20px 0}summary{color:var(--green);padding:10px 0;cursor:pointer}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.6 ui-monospace,monospace;color:var(--muted)}.legend{display:flex;gap:22px;flex-wrap:wrap;margin:14px 0;color:var(--muted);font-size:13px}.legend span:before{content:"";display:inline-block;width:28px;height:3px;vertical-align:middle;margin-right:8px;background:var(--green)}.legend .series-1:before{background:var(--blue)}.chart-panel{margin:28px 0 36px}.chart-grid{display:grid;grid-template-columns:85px minmax(0,1fr);grid-template-rows:220px auto;column-gap:10px}.chart-grid svg{width:100%;height:220px;overflow:visible}.chart-grid line{stroke:var(--line);stroke-width:1;vector-effect:non-scaling-stroke}.chart-grid path{fill:none;stroke-width:2;vector-effect:non-scaling-stroke;stroke:var(--green)}.chart-grid path.series-1{stroke:var(--blue);stroke-dasharray:6 3}.y-labels{display:flex;flex-direction:column;justify-content:space-between;text-align:right;font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums}.x-labels{grid-column:2;display:flex;justify-content:space-between;font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums;margin-top:8px}.links{display:flex;gap:9px;flex-wrap:wrap;font-size:13px}footer{color:var(--muted);font-size:12px;margin-top:35px}@media(max-width:600px){main{padding:24px 14px 55px}h2{font-size:22px}.warning{padding:15px}.chart-grid{grid-template-columns:72px minmax(0,1fr);column-gap:6px}.x-labels{font-size:11px;gap:6px}.y-labels{font-size:11px}th,td{padding:11px 8px}}@media(max-width:350px){.x-labels span:nth-child(2){display:none}}
</style></head><body><main>
<header><div class="eyebrow">Calyx · two-EA research · not deployed</div><h1>Nasdaq 5M + Gold RSI VWAP<br>Actual 5% risk and compounding</h1>
<p>@@INITIAL@@ initial cash · @@WINDOW@@</p><p><strong>Only these two EAs:</strong> Nasdaq 5M candle momentum and XAU RSI VWAP. Nasdaq’s existing <strong>DI filter stays ON</strong>; RSI VWAP rules stay unchanged. Candidates are filtered <em>before</em> the shared admission replay, retaining RSI’s priority ahead of Nasdaq. No fresh strategy optimization or DI experiment was run.</p>
<p><strong>Requested risk:</strong> fixed $50 per position versus 5% of current past-only sampled equity, rounded down to the broker lot step. The old $5 cap/source-volume ceiling is bypassed only in this research experiment. Nothing is changed in live bots, BATs, accounts or the website.</p>
<div class="warning"><strong>5% per trade remains aggressive.</strong> The same research policy pauses new entries at 10% day-anchor loss and halts new entries at 20% loss of initial capital; it does not forcibly close existing positions. A 20% loss needs a 25% recovery. These limits do not guarantee a maximum daily loss or peak-to-trough drawdown.</div>
<p class="muted"><strong>Feed/cost adaptation, not exact current-demo execution:</strong> historical sources are Exness-MT5Trial16 (Raw-like), whereas target sizing uses your Exness-MT5Trial15 USD demo (Pro-like). Native source Nasdaq receipts can have zero spread plus commissions; the demo snapshot has positive spreads. Base retains source-account costs. Stress adds one current-demo spread at each side plus doubled negative swap; it is not exact historical Pro repricing or a native simultaneous account test.</p></header>

@@FINDINGS@@
@@THRESHOLD@@
<section><h2>Two-EA outcomes · fixed versus compounded risk</h2>@@SUMMARY@@<p class="muted">Cash and sampled-equity returns are separate. Equity includes unbanked open P&amp;L; PF, wins and streaks use closed positions only. Paid entry charges on an open position are already in cash. A strong unrealized Nasdaq move must not be presented as a closed gain.</p></section>

<section><h2>Closed profit → cash → sampled equity</h2>@@CASHBRIDGE@@<p class="muted">Closed-position net includes that position’s full entry/exit charges. A still-open position’s paid entry fee is additional cash already deducted, but its eventual net trade result is unknown. The last column adds the final sampled floating mark to cash; it is not a closed return.</p></section>

<section><h2>Compared with the same-risk nine-EA experiment</h2>@@COMPARE@@<p class="muted">Each row matches fixed-$50 or dynamic-5% policy and source/stress cost basis. The nine-EA reference is the earlier frozen actual-risk replay, not the old $5-capped profile. Different membership changes guard admission paths; return differences are not a causal estimate of which removed EA has an edge.</p></section>

<section><h2>What risk was actually admitted?</h2>@@ADMISSIONS@@<p class="muted">Requested risk is a ceiling before lot-step rounding, not an exact realized-loss amount. A last admitted date can precede the source-coverage end because later candidates are rejected by guards. Actual filled stop losses can exceed initial-stop risk through costs/slippage.</p></section>

<section><h2>Sampled-equity paths · fixed versus compounding</h2>@@CURVES@@<p class="muted">Axes: USD sampled equity and UTC dates. Past-only owned-position five-minute samples are carried forward, never future-interpolated. Plot reduction preserves local extrema for display; drawdown metrics use the full sampled replay, not these reduced plots. This is not tick-certified floating drawdown.</p></section>

<section><h2>Unchanged research-only risk policy</h2><ul>
<li>Fixed $50 or 5% of current sampled equity before entry fees; round lots down and skip if broker minimum lot cannot fit.</li>
<li>New-entry pause at 10% loss from Prague day-start cash; permanent new-entry halt at $800 sampled equity (20% initial-capital loss). No automatic position liquidation. The $800 projected/reserved-equity admission buffer may block orders earlier.</li>
<li>Total retained original stop risk at most twice the current requested budget; same-symbol risk at most one budget. Reserve 125% initial risk plus known negative open swap and $0.50 per open position. Missing swap samples are not invented.</li>
<li>Estimated margin capacity 80%; seven entries and three net losing positions per Prague day; three-second entry wait and fixed source priority. Profitable stop movement does not release retained original-risk reservations.</li>
</ul><details><summary>Frozen plan and limitations</summary><pre>@@POLICY@@</pre></details></section>

@@DETAILS@@

<section><h2>Cash dates, source limits and evidence</h2><p>Daily/monthly tables are rebuilt from chronological balance changes, including entry fees for positions that are still open. Dates use Europe/Prague like the guard reset; partial boundary dates arise from the UTC test window. Sharpe, when supplied, uses all 61 UTC daily closed-cash returns and √365—not a confidence score.</p><p>Initial risk/margin prefer source entry-time <a href="https://www.mql5.com/en/docs/trading/ordercalcprofit">OrderCalcProfit</a> / <a href="https://www.mql5.com/en/docs/trading/ordercalcmargin">OrderCalcMargin</a> receipts. Broker lot/margin metadata and spread benchmarks are snapshots, not historical cost schedules. Higher lots are linear resizes of existing native fills; liquidity tiers and new signals after rejected positions are not reconstructed.</p><p class="muted">Both EAs’ original rules and source records are unchanged. Choosing this subset after seeing the earlier result is retrospective research, not independent validation. No Monte Carlo, future pass rate or low blow-up probability is claimed. <a href="https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins/leveraged-investing-strategies-know-risks-using-these-advanced-investment-tools">General leverage risks · Investor.gov</a>.</p>@@EVIDENCE@@</section>
<footer>Research-only two-EA admission replay. Earlier frozen reports, live settings and the nine-EA comparison source remain unchanged.</footer>
</main></body></html>'''


def main():
    if not (ROOT/'RESULTS.json').is_file():
        print('Two-EA report template ready; no outcomes yet, so no empty report generated.')
        return
    reference=load(ROOT.parent/'RESULTS.json')
    verification=load(ROOT/'VERIFICATION.json') if (ROOT/'VERIFICATION.json').is_file() else None
    if verification and verification.get('results_sha256')!=hashlib.sha256((ROOT/'RESULTS.json').read_bytes()).hexdigest():
        raise ValueError('Verification receipt does not match current two-EA outcomes')
    (ROOT/'Results.html').write_text(render(load(ROOT/'RESULTS.json'),reference,ROOT,verification),encoding='utf-8')
    print('Created '+str(ROOT/'Results.html'))


if __name__=='__main__':main()
