"""Independent report for the explicitly requested uncapped 5% risk experiment.

Reads only public frozen receipts. Never changes the earlier capped replay,
production settings, terminals, live positions, or the website.
"""
from collections import Counter
from datetime import datetime, timezone
import importlib.util
import json
import math
from pathlib import Path
import statistics
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('prop1k_capped_report_helpers', ROOT.parent/'report.py')
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
h, cash, percent, number, table = base.h, base.cash, base.percent, base.number, base.table


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def title(result):
    return result.get('scenario', {}).get('label', result.get('label', 'Unnamed replay'))


def normalized_plan(data):
    """Keep input protocol untouched; bridge child and parent receipt schemas."""
    plan=dict(data['plan'])
    window=plan.get('window_utc',[])
    if len(window)==2:
        plan.setdefault('start_utc',window[0]);plan.setdefault('end_exclusive_utc',window[1])
    if not plan.get('priority'):
        plan['priority']=list(dict.fromkeys(c.get('ea') for c in data.get('coverage',[]) if c.get('ea')))
    if not plan.get('priority'):
        plan['priority']=list(dict.fromkeys(d.get('ea') for r in data.get('results',[])
            for d in r.get('decisions',[]) if d.get('ea')))
    return plan


def split_results(data):
    results=data.get('results',[])
    tagged=any('guard_policy' in r.get('scenario',{}) for r in results)
    if not tagged:
        return results,data.get('controls',[])
    primary=[r for r in results if r.get('scenario',{}).get('guard_policy')=='research_10daily_20total']
    controls=data.get('controls',[])+[r for r in results if r not in primary]
    return primary,controls


def entries(result):
    return sum(d.get('reason') == 'opened' for d in result.get('decisions', []))


def summary_table(results, initial=1000):
    rows = []
    for r in results:
        m = r.get('metrics', {})
        equity = m.get('ending_sampled_equity')
        er = m.get('ending_equity_return_pct',
                   (equity/initial-1)*100 if base.finite(equity) else None)
        rows.append([title(r), 'Extra-cost sensitivity' if r.get('stress') else 'Source-account recorded costs',
            entries(r), m.get('trades', len(r.get('trades', []))), cash(m.get('ending_balance')),
            percent(m.get('return_pct'), True), cash(equity), percent(er, True),
            base.pf(m), percent(m.get('win_rate_pct')), percent(m.get('max_closed_dd_pct')),
            percent(m.get('max_sampled_equity_dd_pct')), cash(m.get('max_daily_sampled_equity_dd_cash')),
            str(m.get('max_win_streak', 0))+' / '+str(m.get('max_loss_streak', 0)),
            number(m.get('daily_closed_return_sharpe')), m.get('open_positions', 0),
            'Reached' if m.get('hard_loss_latch') else 'Not reached'])
    return table(['Requested allocation', 'Cost basis', 'Admitted', 'Closed', 'Ending cash', 'Cash return',
        'Ending sampled equity', 'Equity return', 'Closed PF', 'Closed win rate', 'Closed DD', 'Sampled equity DD',
        'Daily sampled DD', 'Win / loss streak', 'UTC daily Sharpe', 'Still open', 'Permanent loss latch'], rows)


def per_ea(result, plan):
    rows = []
    slugs = plan.get('priority', result.get('per_ea', {}).keys())
    for slug in slugs:
        ds = [d for d in result.get('decisions', []) if d.get('ea') == slug]
        ts = [t for t in result.get('trades', []) if t.get('ea') == slug]
        summary = base.trade_summary(ts)
        admitted = [d for d in ds if d.get('reason') == 'opened']
        risks = [d['stop_risk'] for d in admitted if base.finite(d.get('stop_risk'))]
        used = [100*d['stop_risk']/d['equity'] for d in admitted
                if base.finite(d.get('stop_risk')) and base.finite(d.get('equity')) and d['equity'] > 0]
        counts = Counter(d.get('reason') for d in ds)
        rows.append([base.label(slug), len(ds), len(admitted), len(ts),
            counts.get('minimum_lot_over_budget', 0), base.pf(summary), percent(summary['win_rate']),
            cash(summary['net'], True),
            ' / '.join(cash(x) for x in (min(risks), statistics.median(risks), max(risks))) if risks else '—',
            percent(statistics.mean(used)) if used else '—'])
    return table(['EA', 'Source fills', 'Admitted', 'Closed', 'Min-lot skips', 'Closed PF', 'Closed wins',
        'Closed net', 'Actual initial stop risk min / median / max', 'Mean entry stop risk / equity'], rows)


def admission_table(results):
    rows=[]
    for r in results:
        opened=[d for d in r.get('decisions',[]) if d.get('reason')=='opened']
        risks=[d['stop_risk'] for d in opened if base.finite(d.get('stop_risk'))]
        ratios=[100*d['stop_risk']/d['equity'] for d in opened
                if base.finite(d.get('stop_risk')) and base.finite(d.get('equity')) and d['equity']>0]
        reasons=Counter(d.get('reason','unknown') for d in r.get('decisions',[]) if d.get('reason')!='opened')
        rows.append([title(r),'Extra-cost sensitivity' if r.get('stress') else 'Source costs',
            cash(opened[0].get('stop_risk')) if opened else '—',
            ' / '.join(cash(v) for v in (min(risks),statistics.median(risks),max(risks))) if risks else '—',
            ' / '.join(percent(v) for v in (min(ratios),max(ratios))) if ratios else '—',
            base.dt(min(d['epoch'] for d in opened)) if opened else 'No admission',
            base.dt(max(d['epoch'] for d in opened)) if opened else 'No admission',
            '; '.join(base.REASONS.get(reason,reason)+': '+str(count) for reason,count in reasons.most_common())])
    return table(['Allocation','Cost basis','First actual stop risk','Actual risk min / median / max',
        'Entry stop risk / equity: min / max','First admitted entry UTC','Last admitted entry UTC','All rejection reasons / counts'],rows)


def outcome_note(results):
    source=[r for r in results if not r.get('stress')]
    lost=source and all(r.get('metrics',{}).get('return_pct',0)<0 for r in source)
    text=('<strong>Both source-cost 5% approaches lost money in this window.</strong> '
          'Compounding did not rescue the strategy subset or establish a live edge. '
          if lost else '<strong>This is an aggressive, retrospective research comparison.</strong> ')
    text+='The protected-equity admission buffer can stop new trades before a hard loss latch is reached; “not reached” is not proof of safety. The 20% initial-capital loss threshold is not a 20% peak-to-trough drawdown cap.'
    changing=False
    for first in source:
        pair=next((r for r in results if r.get('stress') and r.get('scenario',{}).get('id')==first.get('scenario',{}).get('id')),None)
        if pair:
            original={d.get('id') for d in first.get('decisions',[]) if d.get('reason')=='opened'}
            alternative={d.get('id') for d in pair.get('decisions',[]) if d.get('reason')=='opened'}
            changing|=original!=alternative
    if changing:
        text+='<p><strong>Not a paired-trade cost comparison:</strong> extra costs change equity, guards and which later trades get admitted. A stressed view can therefore have more trades or a smaller final loss. That does not mean paying higher costs improves an edge; compare its changed admission path and rejection counts.</p>'
        fixed=next((r for r in source if r.get('scenario',{}).get('mode')=='fixed'),None)
        pair=next((r for r in results if fixed and r.get('stress') and r.get('scenario',{}).get('id')==fixed.get('scenario',{}).get('id')),None)
        if fixed and pair:
            counterpart={d.get('id'):d for d in pair.get('decisions',[])}
            diverged=next((d for d in fixed.get('decisions',[]) if d.get('reason')=='opened'
                and counterpart.get(d.get('id'),{}).get('reason') not in (None,'opened')),None)
            if diverged:
                alternative=counterpart[diverged['id']]
                closed=next((t for t in fixed.get('trades',[]) if t.get('id')==diverged['id']),{})
                detail=('The fixed-$50 paths first diverged on '+base.dt(diverged.get('epoch'))+' UTC: '+
                    base.label(diverged.get('ea',''))+' was admitted in the source-cost view at '+
                    cash(diverged.get('equity'))+' sampled equity, with '+cash(diverged.get('stop_risk'))+
                    ' initial stop risk'+(' and ultimately '+cash(closed.get('net'),True)+' closed net' if closed else '')+
                    '. In the extra-cost view equity was '+cash(alternative.get('equity'))+
                    ', and the same candidate was rejected by '+base.REASONS.get(alternative.get('reason'),alternative.get('reason','the guard'))+
                    '. Later admissions therefore follow a different path.')
                text+='<p>'+h(detail)+'</p>'
    return '<div class="warning">'+text+'</div>'


def monthly(result, plan):
    days, months = base.cash_periods(result, plan)
    mr = [[r['month'], cash(r['net_cash'], True),
           percent(100*r['net_cash']/r['start_balance'] if r['start_balance'] else None, True),
           r['entries'], r['closes'], r['wins'], r['losses'], cash(r['end_balance'])] for r in months]
    dr = [[r['date']+(' · partial' if r['partial'] else ''),cash(r['net_cash'],True),r['entries'],
           r['closes'],r['wins'],r['losses'],cash(r['end_balance'])] for r in days]
    return (table(['Prague month', 'Net cash change', 'Cash return in displayed portion', 'Entries', 'Closes',
                    'Wins', 'Losses', 'Ending cash'], mr),
            table(['Prague day','Net cash change','Entries','Closes','Wins','Losses','Ending cash'],dr))


def ledger(result):
    rows = []
    for i, t in enumerate(result.get('trades', []), 1):
        rows.append([i,base.label(t.get('ea','')),t.get('symbol',''),t.get('side',''),base.dt(t.get('op')),
            base.dt(t.get('cl')),number(t.get('lots'),3),cash(t.get('risk')),
            cash(t.get('gross'),True),cash(t.get('commission'),True),cash(t.get('swap'),True),
            cash(t.get('net'),True),cash(t.get('balance'))])
    return table(['#','EA','Symbol','Side','Entry UTC','Exit UTC','Lots','Initial stop risk',
                  'Gross','Commission / fees','Swap','Net incl. sensitivity','Cash after exit'],rows)


def still_open(result):
    positions = result.get('open_positions', result.get('open_position_details', []))
    if isinstance(positions, dict):
        positions = list(positions.values())
    if not isinstance(positions,list):
        positions = []
    m = result.get('metrics', {})
    count = m.get('open_positions',len(positions))
    eq, balance = m.get('ending_sampled_equity'), m.get('ending_balance')
    difference = eq-balance if base.finite(eq) and base.finite(balance) else None
    text = '<p><strong>'+h(count)+' open position(s) at the endpoint.</strong> Ending sampled floating P&amp;L: '+h(cash(difference,True))+'. This amount is not banked, is not included in closed-trade PF/win rate, and can change after the test window.</p>'
    if positions:
        rows=[]
        for p in positions:
            row=p.get('row',p)
            rows.append([base.label(p.get('ea',row.get('ea',''))),p.get('symbol',row.get('symbol','')),
                base.dt(p.get('op',row.get('op'))),number(p.get('lots'),3),cash(p.get('risk',p.get('initial_risk'))),
                cash(p.get('floating',p.get('sampled_floating',p.get('unrealized',p.get('unrealized_pnl')))),True)])
        text += table(['EA','Symbol','Opened UTC','Lots','Initial stop risk','Final owned sampled floating P&L'],rows)
    elif count:
        closed={t.get('id') for t in result.get('trades',[])}
        candidates=[d for d in result.get('decisions',[]) if d.get('reason')=='opened' and d.get('id') not in closed]
        text += table(['EA','Opened UTC','Lots','Initial stop risk'],
            [[base.label(d.get('ea','')),base.dt(d.get('epoch')),number(d.get('volume'),3),cash(d.get('stop_risk'))] for d in candidates])
        text += '<p class="muted">Individual final marks were not supplied; no invented per-position value is shown.</p>'
    return text


def decisions(result):
    rows=[]
    for d in result.get('decisions',[]):
        rows.append([base.dt(d.get('epoch')),base.label(d.get('ea','')),
            base.REASONS.get(d.get('reason'),d.get('reason','')),
            cash(d.get('equity')),cash(d.get('budget')),cash(d.get('minimum_lot_risk')),
            number(d.get('volume'),3),cash(d.get('stop_risk'))])
    return table(['Source signal UTC','EA','Decision','Sampled equity','Requested risk budget',
                  'Minimum-lot stop risk','Replay lots','Allocated stop risk'],rows)


def chart(results, stress=False):
    selected = [r for r in results if bool(r.get('stress'))==stress]
    lines=[]
    for r in selected:
        points=base.reduced_curve(r.get('curve',[]),500)
        if points:
            lines.append((r,points))
    if not lines:
        return '<p>No matching recorded path.</p>'
    all_points=[p for _,ps in lines for p in ps]
    xmin=min(p['epoch'] for p in all_points);xmax=max(p['epoch'] for p in all_points)
    ymin=min(p['equity'] for p in all_points);ymax=max(p['equity'] for p in all_points)
    pad=max(.5,(ymax-ymin)*.08);lo,hi=ymin-pad,ymax+pad
    x=lambda t:1000*(t-xmin)/max(1,xmax-xmin)
    y=lambda v:220*(hi-v)/max(1e-12,hi-lo)
    label='Extra-cost sensitivity' if stress else 'Source-account recorded costs'
    title_id='equity-stress-title' if stress else 'equity-source-title'
    parts=['<div class="chart-panel"><h3>'+h(label)+'</h3><div class="legend">']
    for i,(r,_) in enumerate(lines):
        parts.append('<span class="series-'+str(i%2)+'">'+h(title(r))+'</span>')
    parts.append('</div><div class="chart-grid"><div class="y-labels"><span>'+h(cash(hi))+'</span><span>'+h(cash((hi+lo)/2))+'</span><span>'+h(cash(lo))+'</span></div>')
    parts.append('<svg viewBox="0 0 1000 220" preserveAspectRatio="none" role="img" aria-labelledby="'+title_id+'"><title id="'+title_id+'">'+h(label)+' · sampled equity in USD, not closed cash</title>')
    for yy in (0,110,220):
        parts.append('<line x1="0" x2="1000" y1="'+str(yy)+'" y2="'+str(yy)+'"/>')
    for i,(r,points) in enumerate(lines):
        d=' '.join(('M' if n==0 else 'L')+f'{x(p["epoch"]):.2f},{y(p["equity"]):.2f}' for n,p in enumerate(points))
        parts.append('<path class="series-'+str(i%2)+'" d="'+d+'"/>')
    parts.append('</svg><div class="x-labels"><span>'+base.dt(xmin)[:10]+'</span><span>'+base.dt((xmin+xmax)/2)[:10]+'</span><span>'+base.dt(xmax)[:10]+'</span></div></div></div>')
    return ''.join(parts)


def evidence(root):
    if root is None:
        return ''
    names=('RESULTS.json','PLAN.json','FROZEN.json','VERIFICATION.json','../INPUTS.json','../BROKER.json',
           '../FROZEN.json','../DEMO-BENCHMARKS.json')
    return '<nav class="links" aria-label="Public frozen evidence">'+' · '.join(
        '<a href="'+quote(n,safe='/..')+'">'+h(n)+'</a>' for n in names if (Path(root)/n).is_file())+'</nav>'


def render(data, root=None):
    results,controls=split_results(data)
    if not results:
        raise ValueError('No finished actual-risk outcomes: refusing empty report')
    plan=normalized_plan(data);initial=plan.get('initial_balance',1000)
    sections=[]
    for index,r in enumerate(results):
        m=r.get('metrics',{});month_html,day_html=monthly(r,plan)
        policy=r.get('guard_policy',data.get('guard_policy',dict(
            scenario_policy=r.get('scenario',{}).get('guard_policy'),
            guards=plan.get('guards'),exposure=plan.get('exposure'),no_liquidation=plan.get('no_liquidation'))))
        reasons=Counter(d.get('reason','unknown') for d in r.get('decisions',[]))
        reason_html=table(['Entry decision','Count'],[[base.REASONS.get(k,k),v] for k,v in sorted(reasons.items())])
        sections.append('<section id="view-'+str(index)+'"><h2>'+h(title(r))+' · '+h('extra-cost sensitivity' if r.get('stress') else 'source-account costs')+'</h2>'+
            '<h3>Per-EA admitted results</h3>'+per_ea(r,plan)+'<h3>Open exposure is not a closed gain</h3>'+still_open(r)+
            '<h3>Monthly cash changes</h3>'+month_html+
            '<details><summary>Daily dates and cash changes</summary>'+day_html+'</details>'+
            '<details><summary>All admitted closed positions</summary>'+ledger(r)+'</details>'+
            '<details><summary>Every source-entry decision and guard result</summary>'+reason_html+decisions(r)+'</details>'+
            '<details><summary>Frozen guard policy / mark quality</summary><pre>'+h(json.dumps(dict(guard_policy=policy,mark_quality=r.get('mark_quality',{})),indent=2,allow_nan=False))+'</pre></details></section>')
    tokens={
        '@@WINDOW@@':h(plan.get('start_utc','Unknown'))+' → '+h(plan.get('end_exclusive_utc','Unknown'))+' (end exclusive)',
        '@@INITIAL@@':cash(initial),'@@SUMMARY@@':summary_table(results,initial),
        '@@OUTCOME@@':outcome_note(results),'@@ADMISSIONS@@':admission_table(results),
        '@@CONTROLS@@':summary_table(controls,initial),
        '@@CURVES@@':chart(results,False)+chart(results,True),
        '@@DETAILS@@':''.join(sections),'@@EVIDENCE@@':evidence(root),
        '@@POLICY@@':h(json.dumps(data.get('guard_policy',plan.get('guard_policy',dict(
            guards=plan.get('guards'),exposure=plan.get('exposure'),no_liquidation=plan.get('no_liquidation')))),indent=2,allow_nan=False)),
        '@@GENERATED@@':h(data.get('generated_at_utc','Not supplied')),
    }
    output=TEMPLATE
    for k,v in tokens.items():
        output=output.replace(k,v)
    return output


TEMPLATE='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Prop Ready · actual 5% risk / compounding research</title><style>
:root{color-scheme:dark;--bg:#07130f;--panel:#0d231b;--ink:#eafff5;--muted:#aac9bd;--line:#254b3c;--green:#73ebba;--blue:#a2c1ff;--warn:#ffda95}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.65 system-ui,-apple-system,"Segoe UI",sans-serif}main{max-width:1450px;margin:auto;padding:36px 24px 70px}h1{font-size:clamp(30px,4vw,48px);line-height:1.14;max-width:1000px}h2{font-size:25px;line-height:1.25}h3{font-size:18px;margin:24px 0 12px}p,ul{max-width:1160px}.eyebrow{font:12px ui-monospace,monospace;letter-spacing:.12em;color:var(--green);text-transform:uppercase}.muted{color:var(--muted)}a{color:var(--green)}section{border-top:1px solid var(--line);padding-top:26px;margin-top:32px}.warning{border:1px solid #78633a;background:#2b271b;color:var(--warn);padding:18px 22px;border-radius:12px;margin:22px 0}.table-wrap{max-width:100%;overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums}th,td{padding:13px 10px;border-bottom:1px solid var(--line);text-align:right;vertical-align:top}th{color:var(--muted);min-width:95px}td{white-space:nowrap}td:first-child,th:first-child{text-align:left;min-width:170px}td:nth-child(2){white-space:normal}tbody tr:hover{background:#102a20}details{margin:20px 0}summary{color:var(--green);padding:10px 0;cursor:pointer}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.6 ui-monospace,monospace;color:var(--muted)}.legend{display:flex;gap:22px;flex-wrap:wrap;margin:14px 0;color:var(--muted);font-size:13px}.legend span:before{content:"";display:inline-block;width:28px;height:3px;vertical-align:middle;margin-right:8px;background:var(--green)}.legend .series-1:before{background:var(--blue)}.chart-panel{margin:28px 0 36px}.chart-grid{display:grid;grid-template-columns:85px minmax(0,1fr);grid-template-rows:220px auto;column-gap:10px}.chart-grid svg{width:100%;height:220px;overflow:visible}.chart-grid line{stroke:var(--line);stroke-width:1;vector-effect:non-scaling-stroke}.chart-grid path{fill:none;stroke-width:2;vector-effect:non-scaling-stroke;stroke:var(--green)}.chart-grid path.series-1{stroke:var(--blue);stroke-dasharray:6 3}.y-labels{display:flex;flex-direction:column;justify-content:space-between;text-align:right;font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums}.x-labels{grid-column:2;display:flex;justify-content:space-between;font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums;margin-top:8px}.links{display:flex;gap:9px;flex-wrap:wrap;font-size:13px}footer{color:var(--muted);font-size:12px;margin-top:35px}@media(max-width:600px){main{padding:24px 14px 55px}h2{font-size:22px}.warning{padding:15px}.chart-grid{grid-template-columns:72px minmax(0,1fr);column-gap:6px}.x-labels{font-size:11px;gap:6px}.y-labels{font-size:11px}th,td{padding:11px 8px}}@media(max-width:350px){.x-labels span:nth-child(2){display:none}}
</style></head><body><main>
<header><div class="eyebrow">Calyx · separate high-risk research · not deployed</div><h1>Actual 5% per trade, then compound</h1><p>@@INITIAL@@ initial cash · @@WINDOW@@</p>
<p>This tests the clarified request: <strong>fixed $50</strong> versus <strong>5% of current sampled equity</strong>. The earlier $5 reference cap and original strategy request ceiling are bypassed only in this separate research model. This does not alter the Prop Ready BAT or its existing safety system.</p>
<div class="warning"><strong>5% per trade is aggressive—not 5% maximum loss per day.</strong> Multiple losses, gaps or open exposures can exceed intended thresholds. A 20% account loss takes a 25% gain to recover. These two exposed months cannot establish a best live risk setting, safe compounding rate or blow-up probability.</div>
<p class="muted"><strong>Same source signals, not a new simultaneous native test.</strong> This reuses the frozen 93 standalone source positions from Exness-MT5Trial16 and adapts target sizing to your Exness-MT5Trial15 USD demo specifications. Source costs are Raw-like, including zero-spread US100/USDJPY receipts plus commissions; the target demo is Pro-like with positive observed spreads. The source-cost view is not exact current-demo execution, and adding snapshot spreads in the stress view is not exact Pro repricing.</p></header>

@@OUTCOME@@
<section><h2>Actual-risk comparison</h2>@@SUMMARY@@<p class="muted">Cash return includes realized cash and paid entry costs. Sampled-equity return also includes still-open P&amp;L, which is not banked. PF, win rate and streaks use <strong>closed positions only</strong>. A censored Nasdaq position may remain open; no tester end-of-window liquidation is invented.</p></section>

<section><h2>Actual admitted risk and admission cutoffs</h2>@@ADMISSIONS@@<p class="muted">The requested 5% is a ceiling before lot-step rounding, not a guarantee that the final loss is exactly 5%. The last admitted timestamp is not a signal-coverage end date: later candidates can be present but rejected by the protected-equity or other guards. All decisions remain in each view below.</p></section>

<section><h2>Controls · why the original 5% input was still capped</h2>@@CONTROLS@@<p class="muted">A 5% allocation entered into the unchanged profile still meets its $5 reference ceiling on $1,000. Merely removing that cap while retaining the other original guards is a different control: those guards can reject $50 requests. The actual-risk experiment below uses its own explicitly relaxed policy, not the original FTMO/profile rules.</p></section>

<section><h2>Sampled equity paths · fixed versus compounding</h2>@@CURVES@@<p class="muted">Axes: USD sampled equity and UTC dates. Lines use past-only own-position five-minute observations; visual reduction preserves bucket extrema. Neither the source data nor these curves prove tick-accurate portfolio drawdown. Open P&amp;L is included here; compare ending cash separately.</p></section>

<section><h2>Frozen research-only guard policy</h2><ul>
<li>Requested initial stop risk: fixed $50, or 5% of current sampled equity; round <strong>down</strong> to broker lot step and skip if minimum lot cannot fit.</li>
<li>Pause new entries at 10% day-anchor loss; permanently halt new entries at 20% loss of initial capital. Existing positions are not automatically liquidated by these replay latches, so realized/floating losses can exceed a threshold.</li>
<li>Portfolio open stop risk: at most twice the current requested budget; one-symbol stop risk: at most one current budget. Reserve 125% of initial stop risk, known negative open swap, and $0.50 per position. Missing open-swap samples are not invented.</li>
<li>Estimated margin capacity: 80%; at most seven entries and three losing positions per Prague day. No automatic live deployment or native account intervention.</li>
</ul><details><summary>Machine-readable policy receipt</summary><pre>@@POLICY@@</pre></details></section>

<section><h2>How to interpret compounding here</h2><p>Dynamic 5% reduces requested cash risk after losses and raises it after gains, subject to broker lot steps and the stated guards. Fixed $50 does not reduce risk with a shrinking balance: $50 is 6.25% after cash falls to $800. The reference cap is not silently raised in the old profile; this is a separately labelled uncapped experiment.</p><p>Differences can also come from admitted trade subsets and entry priority, not simply a multiplier applied to final profits. Rejected trades can change an EA’s future state, generating signals absent from standalone source runs. That missing counterfactual order stream is not recreated here.</p></section>

@@DETAILS@@

<section><h2>Costs, marks and evidence</h2><p>Source-account native fills, fees and swaps are scaled to admitted lots. The extra-cost sensitivity charges one additional current-demo snapshot spread at <strong>each</strong> side and doubles negative final swap; it retains source commissions and unchanged exits. It is not a historical spread, financing or high-margin-requirement reconstruction.</p><p>Initial-stop risk and margin prefer source entry-time <a href="https://www.mql5.com/en/docs/trading/ordercalcprofit">OrderCalcProfit</a> / <a href="https://www.mql5.com/en/docs/trading/ordercalcmargin">OrderCalcMargin</a> receipts; target current-account proxies are fallbacks, not certification of historical target-account conditions. Missing current open-swap marks, initial zero segments and stale-mark ages are disclosed in each view. Guard decisions use sampled past equity rather than a complete current-stop/tick execution stream.</p><p>Daily/monthly cash tables come from the balance curve, so an entry fee on a still-open position is not omitted. Table days reset in Europe/Prague; the UTC window creates partial boundary dates. Annualized Sharpe, when supplied, uses all 61 UTC calendar dates and √365; a short sample is not a confidence score.</p><p class="muted"><a href="https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins/leveraged-investing-strategies-know-risks-using-these-advanced-investment-tools">Investor.gov: general risks of leveraged investing</a> (not this CFD broker’s contract rules). No Monte Carlo or prospective loss probability is claimed.</p>@@EVIDENCE@@</section>
<footer>Generated @@GENERATED@@. Research-only policy comparison. No live bots, BATs, website, reference cap or earlier frozen result was changed.</footer>
</main></body></html>'''


def main():
    if not (ROOT/'RESULTS.json').is_file():
        print('Actual-risk report template ready; no outcomes yet, so no empty report generated.')
        return
    (ROOT/'Results.html').write_text(render(load(ROOT/'RESULTS.json'),ROOT),encoding='utf-8')
    print('Created '+str(ROOT/'Results.html'))


if __name__=='__main__':
    main()
