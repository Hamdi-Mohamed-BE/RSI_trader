"""Two honest comparison views: delivery policy and normalized research policy.

Only public frozen receipts are read. No trading, installation, website edits,
historical-client-chart replacement, or optimization is performed here.
"""
from collections import Counter
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from urllib.parse import quote

ROOT=Path(__file__).resolve().parent
ACTUAL=ROOT.parent/'Prop Ready 1K Risk Replay 2026-10-17/Actual5Percent'
_spec=importlib.util.spec_from_file_location('comparison_readonly_report_helpers',ACTUAL/'report.py')
shared=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(shared)
base=shared.base
h,cash,percent,number,table=shared.h,shared.cash,shared.percent,shared.number,shared.table
PROFILES={'top5':'Top 5 · Nasdaq DI OFF','prop_ready':'Prop Ready · Nasdaq/JPY DI ON'}
VIEWS={'as_packaged':'As packaged · different risk systems',
       'common_research':'Common research policy · normalized risk'}


def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def profile(r):return r.get('portfolio',r.get('scenario',{}).get('portfolio','unknown'))
def view(r):return r.get('view',r.get('scenario',{}).get('view','unknown'))


def case_label(r):
    return PROFILES.get(profile(r),profile(r))+' · '+shared.title(r)+' · '+(
        'extra-cost sensitivity' if r.get('stress') else 'source-account costs')


def plan_for(data,r):
    plan=dict(data['plan']);window=plan.get('window_utc',[])
    if len(window)==2:plan.update(start_utc=window[0],end_exclusive_utc=window[1])
    roster=plan.get('portfolios',{}).get(profile(r),[])
    if isinstance(roster,dict):roster=roster.get('priority',roster.get('eas',[]))
    plan['priority']=roster
    return plan


def risk_observations(r):
    admitted=[d for d in r.get('decisions',[]) if d.get('reason')=='opened']
    risks=[d['stop_risk'] for d in admitted if base.finite(d.get('stop_risk'))]
    percentages=[100*d['stop_risk']/d['equity'] for d in admitted
        if base.finite(d.get('stop_risk')) and base.finite(d.get('equity')) and d['equity']>0]
    overrides=sum(d.get('minimum_lot_override',False) for d in admitted)
    return admitted,risks,percentages,overrides


def validity(r):
    m=r.get('metrics',{})
    if m.get('capital_exhaustion_epoch') is not None:
        return 'Capital exhausted '+base.dt(m['capital_exhaustion_epoch'])+' UTC; later path not executable'
    if m.get('historical_path_executable_uncertainty'):
        return 'Execution uncertainty; broker stopout not reconstructed'
    if m.get('hard_loss_latch'):
        return 'New-entry hard loss latch reached; open exposure not forcibly closed'
    if profile(r)=='top5' and view(r)=='as_packaged':
        return 'No sampled exhaustion; this package has no portfolio loss latch'
    return 'No sampled exhaustion/hard latch; not a safety guarantee'


def outcome_table(rows,initial):
    values=[]
    for r in rows:
        m=r.get('metrics',{});admitted,risks,ratios,overrides=risk_observations(r)
        eq=m.get('ending_sampled_equity')
        er=m.get('ending_equity_return_pct',(eq/initial-1)*100 if base.finite(eq) else None)
        values.append([PROFILES.get(profile(r),profile(r)),shared.title(r),len(admitted),m.get('trades',len(r.get('trades',[]))),
            m.get('open_positions',0),cash(m.get('ending_balance')),percent(m.get('return_pct'),True),cash(eq),percent(er,True),
            base.pf(m),percent(m.get('win_rate_pct')),number(m.get('daily_closed_return_sharpe')),
            percent(m.get('max_closed_dd_pct')),percent(m.get('max_sampled_equity_dd_pct')),
            cash(m.get('max_daily_closed_dd_cash')),cash(m.get('max_daily_sampled_equity_dd_cash')),
            str(m.get('max_win_streak',0))+' / '+str(m.get('max_loss_streak',0)),
            number(m.get('average_trades_per_weekday')),number(m.get('average_trades_per_calendar_day')),
            ' / '.join(cash(v) for v in (min(risks),max(risks))) if risks else '—',overrides])
    return table(['Portfolio / DI setting','Requested input','Admitted','Closed','Still open','Ending cash','Cash return',
        'Ending sampled equity','Equity return','Closed PF','Closed wins','UTC daily Sharpe','Closed DD','Sampled DD',
        'Daily closed DD','Daily sampled DD','Win / loss streak','Closes / weekday','Closes / calendar day',
        'Actual stop risk min / max','Min-lot override entries'],values)


def cash_bridge(rows,initial):
    values=[]
    for r in rows:
        m=r.get('metrics',{});closed=sum(t.get('net',0) for t in r.get('trades',[]))
        balance,eq=m.get('ending_balance'),m.get('ending_sampled_equity')
        change=balance-initial if base.finite(balance) else None
        other=change-closed if base.finite(change) else None
        floating=eq-balance if base.finite(eq) and base.finite(balance) else None
        values.append([PROFILES.get(profile(r),profile(r)),shared.title(r),cash(closed,True),cash(other,True),
            cash(change,True),cash(floating,True),validity(r)])
    return table(['Portfolio','Input','Whole closed-position net','Other paid cash / open entry charges',
        'Cash profit since start','Unrealized sampled floating','Path status'],values)


def chart(rows,key):
    plots=[]
    for r in rows:
        pts=base.reduced_curve(r.get('curve',[]),420)
        if pts:plots.append((r,pts))
    if not plots:return '<p>No recorded curve.</p>'
    points=[p for _,ps in plots for p in ps]
    lo=min(p['equity'] for p in points);hi=max(p['equity'] for p in points)
    padding=max(.5,(hi-lo)*.08);lo-=padding;hi+=padding
    first=min(p['epoch'] for p in points);last=max(p['epoch'] for p in points)
    x=lambda t:1000*(t-first)/max(1,last-first)
    y=lambda value:220*(hi-value)/max(1e-12,hi-lo)
    text='<div class="legend">'
    for r,_ in plots:
        cls=profile(r)+(' compound' if r.get('scenario',{}).get('id')=='compound5' else ' fixed')
        text+='<span class="'+h(cls)+'">'+h(PROFILES.get(profile(r),profile(r))+' · '+shared.title(r))+'</span>'
    text+='</div><div class="chart-grid"><div class="y-labels"><span>'+h(cash(hi))+'</span><span>'+h(cash((hi+lo)/2))+'</span><span>'+h(cash(lo))+'</span></div>'
    text+='<svg viewBox="0 0 1000 220" preserveAspectRatio="none" role="img" aria-labelledby="chart-title-'+h(key)+'"><title id="chart-title-'+h(key)+'">USD sampled equity · '+h(key)+'</title>'
    for yy in (0,110,220):text+='<line x1="0" x2="1000" y1="'+str(yy)+'" y2="'+str(yy)+'"/>'
    for r,pts in plots:
        cls=profile(r)+(' compound' if r.get('scenario',{}).get('id')=='compound5' else ' fixed')
        path=' '.join(('M' if i==0 else 'L')+f'{x(p["epoch"]):.2f},{y(p["equity"]):.2f}' for i,p in enumerate(pts))
        text+='<path class="'+h(cls)+'" d="'+path+'"/>'
    text+='</svg><div class="x-labels"><span>'+base.dt(first)[:10]+'</span><span>'+base.dt((first+last)/2)[:10]+'</span><span>'+base.dt(last)[:10]+'</span></div></div>'
    return text


def open_positions(r,plan):
    metrics=r.get('metrics',{});positions=r.get('open_positions',[])
    if not isinstance(positions,list):positions=[]
    eq,balance=metrics.get('ending_sampled_equity'),metrics.get('ending_balance')
    floating=eq-balance if base.finite(eq) and base.finite(balance) else None
    end=datetime.fromisoformat(plan['end_exclusive_utc']).timestamp()-1
    values=[]
    for p in positions:
        mark=p.get('mark_epoch')
        values.append([base.label(p.get('ea','')),base.dt(p.get('op')),number(p.get('lots'),3),
            cash(p.get('initial_risk',p.get('risk'))),cash(p.get('paid_entry_cash'),True),base.dt(mark),
            number(end-mark,0) if base.finite(mark) else 'Unknown',cash(p.get('sampled_floating'),True)])
    return ('<p>'+h(metrics.get('open_positions',len(positions)))+' position(s) open; '+h(cash(floating,True))+
        ' sampled floating P&amp;L. This is not banked or part of closed PF/win rate. Paid entry charges are already cash.</p>'+
        table(['EA','Opened UTC','Lots','Initial stop risk','Paid entry cash','Last owned mark UTC',
            'Seconds from mark to horizon','Sampled floating P&L'],values))


def admission_table(r):
    opened,risks,ratios,overrides=risk_observations(r)
    reasons=Counter(d.get('reason','unknown') for d in r.get('decisions',[]))
    summary=[['First admitted entry UTC',base.dt(min(d['epoch'] for d in opened)) if opened else 'None'],
        ['Last admitted entry UTC',base.dt(max(d['epoch'] for d in opened)) if opened else 'None'],
        ['Actual stop-risk min / max',' / '.join(cash(v) for v in (min(risks),max(risks))) if risks else '—'],
        ['Entry stop risk / equity min / max',' / '.join(percent(v) for v in (min(ratios),max(ratios))) if ratios else '—'],
        ['Minimum-lot override admissions',overrides],['Path status',validity(r)]]
    return table(['Admission / risk field','Recorded value'],summary)+table(['Entry decision','Count'],
        [[base.REASONS.get(k,k),v] for k,v in sorted(reasons.items())])


def cash_calendar_tables(r,plan):
    days,months=base.cash_periods(r,plan)
    month_rows=[[m['month'],cash(m['net_cash'],True),
        percent(100*m['net_cash']/m['start_balance'] if m['start_balance']>0 else None,True),
        m['entries'],m['closes'],m['wins'],m['losses'],cash(m['end_balance'])] for m in months]
    day_rows=[[d['date']+(' · partial' if d['partial'] else ''),cash(d['net_cash'],True),d['entries'],
        d['closes'],d['wins'],d['losses'],cash(d['end_balance'])] for d in days]
    return (table(['Prague month','Net cash change','Return in displayed month portion','Entries','Closes',
        'Wins','Losses','Ending cash'],month_rows),
        table(['Prague day','Net cash change','Entries','Closes','Wins','Losses','Ending cash'],day_rows))


def evidence(root):
    if root is None:return ''
    names=('RESULTS.json','PLAN.json','FROZEN.json','VERIFICATION.json','INPUTS.json','native/native_cases.json')
    return '<nav class="links" aria-label="Public evidence">'+' · '.join('<a href="'+quote(name,safe='/')+'">'+h(name)+'</a>'
        for name in names if (Path(root)/name).is_file())+'</nav>'


def verified_receipt(root):
    """Do not attach an audit or its forensics to a different results file."""
    if root is None:return None
    root=Path(root);receipt=root/'VERIFICATION.json'
    if not receipt.is_file():return None
    verification=load(receipt)
    expected=verification.get('result_sha256',verification.get('results_sha256'))
    actual=hashlib.sha256((root/'RESULTS.json').read_bytes()).hexdigest()
    if verification.get('status')!='PASS' or not expected or expected!=actual:
        raise ValueError('Independent verification is not PASS for these exact results')
    return verification


def package_status(root):
    if root is None:return ''
    root=Path(root)
    client=root.parents[2]/'clients/top 5'
    links=[]
    for name in ('Performance and Setup.html','Install Top 5.bat'):
        target=client/name
        if target.is_file():
            relative=os.path.relpath(target,root).replace('\\','/')
            links.append('<a href="'+quote(relative,safe='/')+'">'+h(name)+'</a>')
    return ('<p class="muted">Local package status: Top 5 Nasdaq DI defaults OFF; Prop Ready remains unchanged. '
        'This report does not install or reapply charts. '+(' · '.join(links))+'.</p>')


def findings(results,verification=None):
    exhausted=[r for r in results if r.get('metrics',{}).get('capital_exhaustion_epoch') is not None]
    text='<div class="warning"><strong>5% risk is not supported as prop-safe by this comparison.</strong><p>The as-packaged view compares what the launchers actually request, including their different safety policies. It is not equal risk. The common-policy view gives both portfolios the same research-only sizing and entry guards; it is not a change to either delivered package.</p>'
    def case(portfolio,policy,risk,stress=False):
        return next((r for r in results if profile(r)==portfolio and view(r)==policy and
            r.get('scenario',{}).get('id')==risk and bool(r.get('stress'))==stress),None)
    fixed=case('top5','as_packaged','fixed50')
    compound=case('top5','as_packaged','compound5')
    stress=case('top5','as_packaged','fixed50',True)
    if fixed and compound and stress:
        fm,cm,sm=(r.get('metrics',{}) for r in (fixed,compound,stress))
        text+=('<p><strong>Top 5 delivered policy:</strong> fixed $50 ended at '+h(cash(fm.get('ending_balance')))+
            ' cash ('+h(percent(fm.get('return_pct'),True))+'), but suffered '+h(percent(fm.get('max_sampled_equity_dd_pct')))+
            ' sampled peak-to-trough equity DD. A small cash gain does not compensate for that drawdown. '
            'Its 5%-balance version returned '+h(percent(cm.get('return_pct'),True))+' cash with '+h(percent(cm.get('max_sampled_equity_dd_pct')))+
            ' sampled DD. Extra-cost sensitivity changes fixed-$50 cash return to '+h(percent(sm.get('return_pct'),True))+
            '. '+h(fm.get('open_positions',0))+' ending position(s) remain open: their floating profit is not banked.</p>')
        _,_,_,overrides=risk_observations(fixed)
        _,_,_,compound_overrides=risk_observations(compound)
        over=[d for d in fixed.get('decisions',[]) if d.get('reason')=='opened' and d.get('minimum_lot_override') and
            base.finite(d.get('stop_risk')) and base.finite(d.get('budget')) and d['stop_risk']>d['budget']]
        if over:
            largest=max(over,key=lambda d:d['stop_risk'])
            ratio=100*largest['stop_risk']/largest['equity'] if largest.get('equity',0)>0 else None
            text+=('<p><strong>The selected amount is not a hard risk cap:</strong> the delivered minimum-lot override '
                'was used on '+h(overrides)+' entries in fixed-$50 mode and '+h(compound_overrides)+
                ' in 5%-balance mode. The largest fixed-$50 initial stop risk was '+h(cash(largest['stop_risk']))+
                ' against a '+h(cash(largest['budget']))+' budget ('+h(percent(ratio))+' of entry equity), before gaps and financing.</p>')
    prop=case('prop_ready','as_packaged','fixed50')
    if prop:
        pm=prop.get('metrics',{})
        text+=('<p><strong>Prop Ready’s quiet result is a cap, not a 5% test:</strong> '+h(percent(pm.get('return_pct'),True))+
            ' cash on '+h(pm.get('trades',0))+' closed positions; both requested inputs still meet the $5 reference cap. '
            'It must not be called a better equal-risk 5% result.</p>')
    if exhausted:
        text+='<p><strong>Sampled capital exhaustion occurred in '+h(len(exhausted))+' case(s).</strong> Broker forced-liquidation/stopout timing is not reconstructed; subsequent arithmetic cannot be promoted as an executable account path. Review the path-status column.</p>'
    common=[r for r in results if view(r)=='common_research' and not r.get('stress')]
    if common:
        text+='<p><strong>Source-cost snapshot under the common research policy:</strong></p><ul>'
        for risk in ('fixed50','compound5'):
            paired=[r for r in common if r.get('scenario',{}).get('id')==risk]
            paired.sort(key=lambda r:list(PROFILES).index(profile(r)))
            bits=[]
            for r in paired:
                m=r.get('metrics',{})
                bits.append(PROFILES.get(profile(r),profile(r))+': '+percent(m.get('return_pct'),True)+
                    ' cash / '+percent(m.get('ending_equity_return_pct'),True)+' sampled equity, PF '+base.pf(m)+
                    ', '+str(m.get('trades',0))+' closed')
            text+='<li>'+h(('Fixed $50' if risk=='fixed50' else '5% current equity')+' — '+'; '.join(bits))+'.</li>'
        text+='</ul>'
    common_all=[r for r in results if view(r)=='common_research']
    if common_all and all(r.get('metrics',{}).get('return_pct',0)<0 for r in common_all):
        text+='<p><strong>All eight common-policy cases lost cash.</strong> The common guards are hypothetical 10%-daily / 20%-initial entry rules, not an FTMO account model. No 60–70% pass-rate result is computed or implied here.</p>'
    text+='<p>Do not choose by the biggest sampled-equity return: open Nasdaq P&amp;L may be unbanked, minimum-lot overrides can exceed selected risk, and guard thresholds can change which later trades are admitted. Two exposed months do not establish a best live portfolio or safe 5% risk.</p></div>'
    if verification:
        text+='<p class="muted">Independent arithmetic/state audit: '+h(verification.get('status'))+' · '+h(f"{verification.get('checks',0):,}")+' checks against these exact frozen results. This verifies the replay, not a trading edge.</p>'
        gap=verification.get('largest_gap_loss')
        if gap:
            values=[['Opened / naturally stopped UTC',gap.get('open_utc','')+' → '+gap.get('close_utc','')],
                ['Entry / original stop / actual exit',number(gap.get('entry_price'),2)+' / '+number(gap.get('original_stop'),2)+' / '+number(gap.get('actual_exit'),2)],
                ['Fill beyond original stop',number(gap.get('adverse_stop_fill_difference_points'),2)+' points'],
                ['Lots / planned stop risk',number(gap.get('lots'),2)+' / '+cash(gap.get('planned_stop_cash'))],
                ['Gross / commission / swap / net',' / '.join(cash(gap.get(k),True) for k in ('gross','commission','swap','net'))],
                ['Natural native exit comment',gap.get('native_exit_comment','')]]
            text+=('<div class="warning"><strong>A real stop gap broke the research loss floor.</strong><p>Top 5 common-policy fixed-$50 Nasdaq trade 36 crossed the weekend: '
                'its planned stop risk was '+h(cash(gap.get('planned_stop_cash')))+' but the realized net loss was '+h(cash(gap.get('net'),True))+
                '. The Sunday reopening filled beyond the original stop, with weekend swap added. Ending cash '+h(cash(case('top5','common_research','fixed50')['metrics']['ending_balance']))+
                ' fell below the $800 research floor. This was a genuine source stop fill, not synthetic final liquidation or a sizing bug. '
                'An entry guard cannot guarantee an exit price or cap drawdown.</p>'+table(['Verified gap receipt','Recorded value'],values)+'</div>')
    return text


def render(data,root=None):
    results=data.get('results',[])
    if not results:raise ValueError('No completed profile comparisons; no empty report')
    plan=data['plan'];window=plan['window_utc'];initial=plan.get('initial_balance',1000)
    keys={(profile(r),view(r),r.get('scenario',{}).get('id'),bool(r.get('stress'))) for r in results}
    expected={(p,v,s,c) for p in PROFILES for v in VIEWS for s in ('fixed50','compound5') for c in (False,True)}
    if keys!=expected or len(results)!=16:raise ValueError('Expected all 16 frozen comparison cases, without duplicates')
    panels=[]
    for policy in VIEWS:
        for stress in (False,True):
            rows=[r for r in results if view(r)==policy and bool(r.get('stress'))==stress]
            rows.sort(key=lambda r:(list(PROFILES).index(profile(r)),r['scenario']['id']!='fixed50'))
            key=policy+('-stress' if stress else '-source')
            panels.append('<section id="'+key+'"><h2>'+h(VIEWS[policy])+' · '+h('extra-cost sensitivity' if stress else 'source-account costs')+'</h2>'+
                '<p class="muted">'+('Different delivery caps, rounding and percentage bases. These rows are not an equal-risk ranking.' if policy=='as_packaged' else
                'Both portfolios use strict floor/skip sizing and the same actual-$50 / 5%-equity, 10%-daily / 20%-initial research entry guards. Neither delivery is changed.')+'</p>'+
                outcome_table(rows,initial)+'<h3>Cash, closed profit and unrealized exposure</h3>'+cash_bridge(rows,initial)+
                '<h3>Sampled equity paths</h3>'+chart(rows,key)+'</section>')
    rosters=[]
    for key in PROFILES:
        roster=plan['portfolios'][key]
        if isinstance(roster,dict):roster=roster.get('priority',roster.get('eas',[]))
        rosters.append('<div><h3>'+h(PROFILES[key])+' · '+str(len(roster))+' EAs</h3><ol>'+''.join('<li>'+h(base.label(s))+'</li>' for s in roster)+'</ol></div>')
    details=[]
    for i,r in enumerate(results):
        case_plan=plan_for(data,r);monthly,daily=cash_calendar_tables(r,case_plan)
        details.append('<details class="case" id="case-'+str(i)+'"><summary>'+h(VIEWS[view(r)]+' · '+case_label(r))+'</summary>'+
            '<h3>Per-EA admitted results</h3>'+shared.per_ea(r,case_plan)+
            '<h3>Admissions and guard counts</h3>'+admission_table(r)+
            '<h3>Monthly cash changes</h3>'+monthly+
            '<h3>Open exposure and mark times</h3>'+open_positions(r,case_plan)+
            '<details><summary>Daily cash dates, including no-trade days</summary>'+daily+'</details>'+
            '<details><summary>All closed positions · trade by trade</summary>'+shared.ledger(r)+'</details>'+
            '<details><summary>Every candidate entry decision</summary>'+shared.decisions(r)+'</details>'+
            '<details><summary>Sample quality and state receipts</summary><pre>'+h(json.dumps(dict(
                scenario=r.get('scenario'),mark_quality=r.get('mark_quality'),metrics=r.get('metrics')),indent=2,allow_nan=False))+'</pre></details></details>')
    coverage=[]
    for portfolio,source in data.get('coverage',{}).items():
        coverage.append('<h3>'+h(PROFILES.get(portfolio,portfolio))+'</h3>'+base.source_coverage(source))
    verification=verified_receipt(root)
    values={'@@WINDOW@@':h(window[0])+' → '+h(window[1])+' (end exclusive)',
        '@@INITIAL@@':cash(initial),'@@FINDINGS@@':findings(results,verification)+package_status(root),'@@PANELS@@':''.join(panels),
        '@@ROSTERS@@':''.join(rosters),'@@DETAILS@@':''.join(details),'@@COVERAGE@@':''.join(coverage),
        '@@PLAN@@':h(json.dumps(plan,indent=2,allow_nan=False)),'@@EVIDENCE@@':evidence(root)}
    html=TEMPLATE
    for key,value in values.items():html=html.replace(key,value)
    return html


TEMPLATE='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Top 5 DI OFF vs Prop Ready DI ON · matched risk replay</title><style>
:root{color-scheme:dark;--bg:#07130f;--ink:#eafff5;--muted:#aac9bd;--line:#254b3c;--green:#73ebba;--blue:#a2c1ff;--warn:#ffda95}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.65 system-ui,-apple-system,"Segoe UI",sans-serif}main{max-width:1550px;margin:auto;padding:36px 24px 70px}h1{font-size:clamp(30px,4vw,48px);line-height:1.14;max-width:1050px}h2{font-size:25px;line-height:1.25}h3{font-size:18px;margin:24px 0 12px}p,ul{max-width:1200px}.eyebrow{font:12px ui-monospace,monospace;letter-spacing:.12em;color:var(--green);text-transform:uppercase}.muted{color:var(--muted)}a{color:var(--green)}section{border-top:1px solid var(--line);padding-top:26px;margin-top:32px}.warning{border:1px solid #78633a;background:#2b271b;color:var(--warn);padding:18px 22px;border-radius:12px;margin:22px 0}.table-wrap{max-width:100%;overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums}th,td{padding:13px 10px;border-bottom:1px solid var(--line);text-align:right;vertical-align:top}th{color:var(--muted);min-width:95px}td{white-space:nowrap}td:first-child,th:first-child{text-align:left;min-width:170px}td:nth-child(2){white-space:normal}tbody tr:hover{background:#102a20}details{margin:20px 0}summary{color:var(--green);padding:10px 0;cursor:pointer}.case>summary{font-size:17px}.case{border-top:1px solid var(--line);padding-top:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.6 ui-monospace,monospace;color:var(--muted)}.legend{display:flex;gap:15px 24px;flex-wrap:wrap;margin:14px 0;color:var(--muted);font-size:13px}.legend span:before{content:"";display:inline-block;width:28px;height:3px;vertical-align:middle;margin-right:8px;background:var(--green)}.legend .prop_ready:before{background:var(--blue)}.legend .compound:before{background:repeating-linear-gradient(to right,var(--green) 0 6px,transparent 6px 9px)}.legend .prop_ready.compound:before{background:repeating-linear-gradient(to right,var(--blue) 0 6px,transparent 6px 9px)}.chart-grid{display:grid;grid-template-columns:90px minmax(0,1fr);grid-template-rows:220px auto;column-gap:10px}.chart-grid svg{width:100%;height:220px;overflow:visible}.chart-grid line{stroke:var(--line);stroke-width:1;vector-effect:non-scaling-stroke}.chart-grid path{fill:none;stroke-width:2;vector-effect:non-scaling-stroke;stroke:var(--green)}.chart-grid path.prop_ready{stroke:var(--blue)}.chart-grid path.compound{stroke-dasharray:6 3}.y-labels{display:flex;flex-direction:column;justify-content:space-between;text-align:right;font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums}.x-labels{grid-column:2;display:flex;justify-content:space-between;font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums;margin-top:8px}.links{display:flex;gap:9px;flex-wrap:wrap;font-size:13px}.rosters{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:20px 40px}footer{color:var(--muted);font-size:12px;margin-top:35px}@media(max-width:600px){main{padding:24px 14px 55px}h2{font-size:22px}.warning{padding:15px}.chart-grid{grid-template-columns:75px minmax(0,1fr);column-gap:6px}.x-labels{font-size:11px;gap:6px}.y-labels{font-size:11px}th,td{padding:11px 8px}}@media(max-width:350px){.x-labels span:nth-child(2){display:none}}
</style></head><body><main>
<header><div class="eyebrow">Calyx · new comparison study · no account deployment</div><h1>Top 5 with Nasdaq DI OFF<br>versus Prop Ready with DI ON</h1><p>@@INITIAL@@ initial cash for each replay · @@WINDOW@@</p>
<p>Top 5 uses its current client default: Nasdaq DI agreement <strong>OFF</strong>. Prop Ready retains Nasdaq and USDJPY DI agreement <strong>ON</strong>. Each portfolio keeps its own strategy rules, stops, exits and membership; this is not a clean isolated DI-only experiment.</p>
<p class="muted">This study uses fresh two-month Top 5 source tests and the frozen Prop Ready source tests—not the old Top 5 September 3-/6-month chart archive. That client archive remains explicitly historical DI-ON/skip-min evidence. Only the local Top 5 client default was changed; Prop Ready, website and live accounts were not changed. Historical tester mode permits research dates outside the client licence window by its existing design; the delivery licence was not renewed, extended or disabled.</p>
<div class="warning"><strong>Source feed is not the connected demo.</strong> Native source trades use isolated Exness-MT5Trial16 Raw-like pricing. Lot/margin snapshots target your Exness-MT5Trial15 USD demo, which is Pro-like and has different quotes/spreads. Source-account costs are not exact current-demo execution. Extra-cost sensitivity adds current snapshot spread at each side plus doubled negative swap, retaining source commissions—not exact historical Pro repricing.</div></header>
@@FINDINGS@@
<section><h2>Exactly which portfolios?</h2><div class="rosters">@@ROSTERS@@</div><p class="muted">Priority follows the frozen rosters. Standalone signals are replayed chronologically against each portfolio’s cash, sizing and guard state. This is not a simultaneous native shared-account backtest, nor a subtraction of old portfolio P&amp;L rows.</p></section>
<section><h2>Read the two policy views correctly</h2><ul>
<li><strong>As packaged · Top 5:</strong> fixed USD or percentage of current <strong>balance</strong>, floor lots then override up to broker minimum when needed. That override can exceed selected risk. No portfolio daily-loss/open-risk cap is invented. Estimated free margin is checked; actual broker liquidation is not reconstructed.</li>
<li><strong>As packaged · Prop Ready:</strong> requested $50 or 5% of sampled equity still meets original source ceilings, the <strong>$5 reference cap</strong> on $1,000, strict minimum-lot skip, and existing shared/daily/reserve guards. Its quiet result is not comparable to uncapped Top 5 risk.</li>
<li><strong>Common research · both:</strong> actual fixed $50 or 5% of current sampled equity; strict down-round/skip; 10% Prague day-anchor loss pause and 20% initial-capital new-entry halt. Projected/reserved equity must remain above $800; retain 125% original risk, known negative swap and $0.50/position. Aggregate/symbol limits 2×/1× current budget, 80% margin capacity, seven entries/three losses per day and a three-second wait.</li>
</ul><p class="muted">Common-policy changes are hypothetical and not installed. This is not an FTMO challenge or funded-account pass model. Neither stop/guard policy guarantees realized daily losses or peak-to-trough DD; existing positions are not forcibly liquidated. A 20% loss needs a 25% recovery.</p></section>
@@PANELS@@
<section><h2>All case details · EAs, cash dates, trades and guards</h2><p class="muted">Closed-position PF/win rate/streaks exclude open positions. Cash includes paid entry charges; sampled equity adds unbanked floating marks. Daily/monthly cash dates use Europe/Prague; UTC window boundaries create partial days. Relative monthly return is unavailable if opening cash is zero/negative. Sharpe uses all 61 UTC daily closed-cash returns and √365 when valid. Frequency is closed positions per weekday/calendar day, not guaranteed new signals per day.</p>@@DETAILS@@</section>
<section><h2>Coverage and limits</h2>@@COVERAGE@@<p>Past-only five-minute owned-position samples are carried forward with timestamps; no future interpolation. Drawdowns are sampled estimates, not tick-certified portfolio extremes. Plot reduction is presentation-only. Native boundary-forced closes remain in original cash-reconciliation evidence but are censored in this replay, not booked as natural exits. Explicit final/export-only snapshots are excluded from owned-position floating marks. An admitted boundary-censored position therefore remains open, with paid entry charges in cash and its last valid floating mark unbanked. Export-only audit corrections do not change the strategy rules or make these exposed dates out of sample. Missing open-swap samples and stale-mark ages are disclosed in each case.</p><p>Initial risk and margins prefer source entry-time <a href="https://www.mql5.com/en/docs/trading/ordercalcprofit">OrderCalcProfit</a>/<a href="https://www.mql5.com/en/docs/trading/ordercalcmargin">OrderCalcMargin</a> receipts. Linear lot resizing cannot recreate changed liquidity tiers, broker stopout, current-stop timelines or new signals caused by rejected trades. Cost/rounding changes can produce different admitted trade paths; more-cost cases are not necessarily paired-trade deductions.</p><p class="muted">These are already-exposed recent dates, not untouched validation. No optimization, Monte Carlo, prop pass probability or low blow-up estimate is claimed. <a href="https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins/leveraged-investing-strategies-know-risks-using-these-advanced-investment-tools">Investor.gov · general leverage risks</a>.</p><details><summary>Frozen comparison plan</summary><pre>@@PLAN@@</pre></details>@@EVIDENCE@@</section>
<footer>Local research only. Historical Top 5 charts are preserved; current default metadata is separated. No live account, Prop Ready preset or global website was changed by this simulation.</footer>
</main></body></html>'''


def main():
    if not (ROOT/'RESULTS.json').is_file():
        print('Comparison report template ready; no completed outcomes, no empty HTML generated.')
        return
    (ROOT/'Results.html').write_text(render(load(ROOT/'RESULTS.json'),ROOT),encoding='utf-8')
    print('Created '+str(ROOT/'Results.html'))


if __name__=='__main__':main()
