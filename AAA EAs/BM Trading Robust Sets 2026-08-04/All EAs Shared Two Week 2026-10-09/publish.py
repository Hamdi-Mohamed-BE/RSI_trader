"""Offline recent combined results. Does not update the website or launch MT5."""
from pathlib import Path
from datetime import datetime, timezone, date, timedelta
from collections import defaultdict
import csv, hashlib, html, json, math, sys

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
sys.path.insert(0,str(BASE.parent/'EA store'))
from app.portfolio_analytics import allocation_replay, performance

START,END='2026-09-25','2026-10-09'
INITIAL=10000.
CONTRACTS={'XAUUSD':100.,'XAGUSD':5000.,'USDJPY':100000.,'EURUSD':100000.,'USTEC':1.,'US30':1.,'BTCUSD':1.,'ETHUSD':1.}

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def epoch(text):return datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp()
def iso(timestamp):return datetime.fromtimestamp(timestamp,timezone.utc).isoformat()
def boundary(trade):return any('end of test' in s.lower() for s in trade['exit_comments'])

def risk_rows(case,row,path):
    with (path.parent/'deals.csv').open(encoding='utf-8-sig') as stream:deals=list(csv.DictReader(stream))
    grouped=defaultdict(list)
    for d in deals:grouped[int(d['position_id'])].append(d)
    out=[]
    for t in case['trades']:
        if boundary(t):continue
        parts=grouped[t['position_id']]
        opened=[d for d in parts if int(d['entry'])==0]
        exits=[d for d in parts if int(d['entry'])==1]
        assert len(opened)==1 and len(exits)==t['exit_legs']
        a=opened[0]
        op=int(a['time_msc'])/1000
        cl=max(int(d['time_msc'])/1000 for d in exits)
        assert epoch(START)<=op<=cl<epoch(END)
        key=row['slug'];symbol=row['symbol'];contract=CONTRACTS[symbol]
        news=key.startswith('news-pulse-')
        hourly=key.endswith('hourly-profiles')
        planned_price=float(a['order_price_open'])
        if hourly:
            assert t['sl']==0
            unit=float(row['input_settings']['InpHistoricalLossPoints'])*contract
            reference='Frozen historical maximum loss distance; NO protective stop'
        else:
            assert t['sl']>0
            # A pending news order is sized before it fills. Its requested entry
            # price, NOT its gap-shifted fill, defines the planned stop budget.
            risk_price=planned_price if news else t['open_price']
            assert risk_price>0 and (t['sl']<risk_price)==(t['side']=='Long'),('Initial stop geometry',key,t['position_id'])
            unit=abs(risk_price-t['sl'])*contract/(t['sl'] if symbol=='USDJPY' else 1.)
            reference='Requested entry-to-stop distance, per news order' if news else 'Filled initial entry-to-stop distance'
        assert math.isfinite(unit) and unit>0 and t['volume']>0
        out.append(dict(key=key,symbol=symbol,news=news,op=op,cl=max(cl,op+.000001),native_position_id=t['position_id'],
            unit_risk=unit,unit_gross=t['gross']/t['volume'],unit_comm=(t['commission']+t['fee'])/t['volume'],unit_swap=t['swap']/t['volume'],
            open_price=t['open_price'],close_price=t['close_price'],initial_sl=t['sl'],initial_tp=t['tp'],side=t['side'],
            requested_entry_price=planned_price,entry_order_type=int(a['order_type']),
            lane=str(t['magic']) if key=='3-way-gold' else key,partial=t['partial'],exit_legs=t['exit_legs'],
            exit_comments=t['exit_comments'],entry_comment=t['entry_comment'],
            risk_weight=.5 if key=='xau-weakness' else 1.,risk_reference=reference))
    return out

def detailed_replay(rows,adaptive=True):
    """Same current website model, with an admission/size receipt for each trade."""
    begin,finish=epoch(START),epoch(END)
    eligible=[r for r in rows if begin<=r['op']<r['cl']<finish and r['unit_risk']>0]
    events=sorted([(r['op'],1,i) for i,r in enumerate(eligible)]+[(r['cl'],0,i) for i,r in enumerate(eligible)])
    balance=peak=INITIAL;active={};closed=[];receipts=[];lossruns=defaultdict(int);daily=defaultdict(float)
    for timestamp,kind,i in events:
        r=eligible[i];key=r['key'];lane=r.get('lane',key);day=iso(timestamp)[:10]
        if kind==1:
            reason='Nonpositive closed balance' if balance<=0 else 'Adaptive daily closed-loss admission stop' if adaptive and not r['news'] and daily[day]<=-INITIAL*.05 else None
            if reason:
                receipts.append(dict(index=i,slug=key,native_position_id=r['native_position_id'],open_time=iso(timestamp),admitted=False,reason=reason));continue
            selected_percent=.10 if r['news'] else 1.
            multiplier=r['risk_weight'];dd=(peak-balance)/peak*100
            if adaptive and not r['news']:
                multiplier*=.25 if dd>=7 else .5 if dd>=4 else 1
                multiplier*=.25 if lossruns[lane]>=5 else .5 if lossruns[lane]>=3 else 1
                if key=='nasdaq-5m-candle-momentum':multiplier*=.25
            budget=balance*selected_percent/100*multiplier
            lot=budget/r['unit_risk']
            receipt=dict(index=i,slug=key,native_position_id=r['native_position_id'],open_time=iso(timestamp),admitted=True,
                balance_at_entry=balance,selected_percent=selected_percent,effective_percent=selected_percent*multiplier,
                initial_risk_cash=budget,fractional_lot=lot,closed_drawdown_at_entry=dd,prior_lane_losses=lossruns[lane])
            receipts.append(receipt);active[i]=(lot,receipt)
        elif i in active:
            lot,receipt=active.pop(i)
            gross,commission,swap=lot*r['unit_gross'],lot*r['unit_comm'],lot*r['unit_swap']
            net=gross+commission+swap
            balance+=net;peak=max(peak,balance);daily[day]+=net
            lossruns[lane]=lossruns[lane]+1 if net<-.005 else 0
            closed.append(dict(slug=key,position_id=i,native_position_id=r['native_position_id'],symbol=r['symbol'],side=r['side'],
                open_time=iso(r['op']),close_time=iso(timestamp),open_price=r['open_price'],close_price=r['close_price'],
                initial_sl=r['initial_sl'],initial_tp=r['initial_tp'],net_profit=net,gross_profit=gross,commission_and_fees=commission,swap=swap,
                balance_after=balance,partial=r['partial'],exit_legs=r['exit_legs'],exit_comments=r['exit_comments'],
                risk_reference=r['risk_reference'],initial_risk_cash=receipt['initial_risk_cash'],effective_percent=receipt['effective_percent'],
                fractional_lot=lot,net_r=net/receipt['initial_risk_cash']))
    assert not active
    # Independent verification against the pre-existing allocation model.
    reference_rows=eligible if adaptive else [dict(r,risk_weight=.1 if r['news'] else r['risk_weight']) for r in eligible]
    expected,info=allocation_replay(reference_rows,START,END,'percent',1,INITIAL,adaptive=adaptive,news_percent=.10)
    assert len(expected)==len(closed)
    for a,b in zip(closed,expected):
        assert a['slug']==b['slug'] and a['position_id']==b['position_id'] and a['close_time']==b['close_time']
        assert abs(a['net_profit']-b['net_profit'])<1e-8
    assert sum(not r['admitted'] for r in receipts)==info['skipped_entries']
    return closed,receipts,info

def day_table(trades):
    out=[];balance=INITIAL
    for offset in range((date.fromisoformat(END)-date.fromisoformat(START)).days):
        day=(date.fromisoformat(START)+timedelta(days=offset)).isoformat()
        closed=[t for t in trades if t['close_time'][:10]==day]
        opens=sum(t['open_time'][:10]==day for t in trades)
        anchor=peak=balance;dd=0
        for t in closed:balance+=t['net_profit'];peak=max(peak,balance);dd=max(dd,peak-balance)
        out.append(dict(date=day,entries=opens,closed=len(closed),wins=sum(t['net_profit']>.005 for t in closed),losses=sum(t['net_profit']<-.005 for t in closed),
            net_profit=balance-anchor,balance=balance,daily_closed_drawdown_cash=dd))
    return out

def scenario(rows,adaptive):
    trades,receipts,info=detailed_replay(rows,adaptive)
    stats,curve,_=performance(trades,START,END,INITIAL)
    days=day_table(trades)
    assert abs(sum(d['net_profit'] for d in days)-stats['net_profit'])<1e-7
    assert abs(max(d['daily_closed_drawdown_cash'] for d in days)-stats['max_daily_closed_drawdown_cash'])<1e-7
    assert abs(sum(t['net_profit'] for t in trades)-stats['net_profit'])<1e-7
    assert stats['sharpe_ratio'] is None,'14 days must not be presented as a reliable annualised Sharpe'
    return dict(stats=stats,curve=curve,trades=trades,admissions=receipts,daily=days,controls=info)

def fmt(value,places=2):return '—' if value is None else f'{value:,.{places}f}'
def esc(text):return html.escape(str(text))
def colour(value):return 'gain' if value>0 else 'loss' if value<0 else ''

def chart(curve):
    x0,x1=epoch(START),epoch(END);lo=min(p['balance'] for p in curve);hi=max(p['balance'] for p in curve)
    padding=max(50,(hi-lo)*.08);lo-=padding;hi+=padding
    def xy(p):return (70+880*(datetime.fromisoformat(p['time']).timestamp()-x0)/(x1-x0),25+260*(hi-p['balance'])/(hi-lo))
    points=' '.join(f'{x:.2f},{y:.2f}' for x,y in map(xy,curve))
    grid=''.join(f'<line x1="70" x2="950" y1="{25+260*i/4}" y2="{25+260*i/4}" stroke="#28483b"/><text x="60" y="{30+260*i/4}" text-anchor="end" fill="#aec8ba" font-size="12">${fmt(hi-(hi-lo)*i/4,0)}</text>' for i in range(5))
    return '<svg viewBox="0 0 1000 330" role="img" aria-label="Combined closed-balance curve">'+grid+f'<polyline points="{points}" fill="none" stroke="#61f5bf" stroke-width="2.5"/><text x="70" y="315" fill="#aec8ba">25 Sep 2026</text><text x="950" y="315" text-anchor="end" fill="#aec8ba">9 Oct boundary</text></svg>'

def render(summary):
    main=summary['scenarios']['current_adaptive'];equal=summary['scenarios']['equal_base_risk_diagnostic'];s=main['stats'];coverage=summary['coverage']
    metrics=[('Net return',fmt(s['return_pct'])+'%'),('Net P/L','$'+fmt(s['net_profit'])),('Final balance','$'+fmt(s['final_balance'])),('Win rate',fmt(s['win_rate_pct'])+'%'),
        ('Profit factor',fmt(s['profit_factor'])),('Completed positions',str(s['trades'])),('Max closed DD',fmt(s['max_drawdown_pct'])+'% / $'+fmt(s['max_drawdown_cash'])),
        ('Max daily closed DD','$'+fmt(s['max_daily_closed_drawdown_cash'])),('Win / loss streak',str(s['max_win_streak'])+' / '+str(s['max_loss_streak'])),('Trades per weekday',fmt(s['trades_per_weekday']))]
    cards=''.join('<div class="card"><small>'+title+'</small><strong>'+value+'</strong></div>' for title,value in metrics)
    comparisons=''.join('<tr><td>'+title+'</td><td>'+fmt(s[key])+'</td><td>'+fmt(equal['stats'][key])+'</td></tr>' for title,key in
        [('Return %','return_pct'),('Net USD','net_profit'),('PF','profit_factor'),('Win rate %','win_rate_pct'),('Closed DD %','max_drawdown_pct'),('Daily closed DD USD','max_daily_closed_drawdown_cash'),('Positions','trades'),('Max win streak','max_win_streak'),('Max loss streak','max_loss_streak')])
    member_rows=[]
    for member in summary['members']:
        key=member['slug'];ts=[t for t in main['trades'] if t['slug']==key]
        stats=performance(ts,START,END,INITIAL)[0]
        status=member['status']
        if status=='tested':
            status=('No naturally completed positions' if not member['completed_positions'] else 'Tested')
            if member['boundary_positions']:status+='; '+str(member['boundary_positions'])+' open at end excluded'
            status+=' · '+member['history_quality']
        contribution=sum(t['net_profit'] for t in ts)
        member_rows.append('<tr><td>'+esc(member['label'])+'</td><td>'+esc(member['symbol'])+'</td><td>'+esc(status)+'</td><td>'+str(len(ts))+'</td><td>'+fmt(stats['win_rate_pct'])+'</td><td>'+fmt(stats['profit_factor'])+'</td><td class="'+colour(contribution)+'">'+('$'+fmt(contribution) if member['status']=='tested' else 'Missing')+'</td><td>'+str(stats['max_win_streak'])+' / '+str(stats['max_loss_streak'])+'</td></tr>')
    daily_rows=''.join('<tr><td>'+d['date']+'</td><td>'+str(d['entries'])+'</td><td>'+str(d['closed'])+'</td><td>'+str(d['wins'])+' / '+str(d['losses'])+'</td><td class="'+colour(d['net_profit'])+'">$'+fmt(d['net_profit'])+'</td><td>$'+fmt(d['balance'])+'</td><td>$'+fmt(d['daily_closed_drawdown_cash'])+'</td></tr>' for d in main['daily'])
    trade_rows=''.join('<tr><td>'+str(i+1)+'</td><td>'+esc(t['slug'])+'</td><td>'+t['open_time'].replace('T',' ').replace('+00:00','')+'</td><td>'+t['close_time'].replace('T',' ').replace('+00:00','')+'</td><td>'+t['side']+'</td><td>'+fmt(t['effective_percent'],3)+'%</td><td>$'+fmt(t['initial_risk_cash'])+'</td><td class="'+colour(t['net_profit'])+'">$'+fmt(t['net_profit'])+'</td><td>'+fmt(t['net_r'])+'</td><td>$'+fmt(t['balance_after'])+'</td></tr>' for i,t in enumerate(main['trades']))
    missing='; '.join(m['label']+': '+m['reason'] for m in summary['members'] if m['status']!='tested')
    warnings=''.join('<li>'+esc(note)+'</li>' for note in summary['limitations'])
    document='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>All EAs · Two-week shared portfolio</title>
<style>body{background:#071812;color:#ecf8f0;font:15px system-ui;margin:28px auto;max-width:1500px;padding:0 22px}h1{font-size:30px}h2{margin-top:40px}p,li{color:#b8cfc2;line-height:1.6}a{color:#64f5c2}.note{border:1px solid #88723c;background:#292b14;padding:16px;border-radius:12px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(225px,1fr));gap:12px}.card{padding:20px;border:1px solid #2c4f40;border-radius:12px}.card small{display:block;color:#b8cfc2}.card strong{display:block;font-size:24px;margin-top:10px}table{border-collapse:collapse;width:100%;margin-top:18px}th,td{padding:10px;text-align:right;border-bottom:1px solid #29483b}th:first-child,td:first-child{text-align:left}.wide{overflow:auto}th{white-space:nowrap}.gain{color:#65f7bf}.loss{color:#ff858b}svg{width:100%;max-height:420px}summary{cursor:pointer;color:#65f7bf;padding:18px 0}</style></head><body>
<h1>All EAs together · last two completed weeks</h1><p>25 September–8 October 2026 inclusive. 9 October 00:00 is the end-exclusive boundary. $10,000 starting balance. Current full-roster settings, no optimisation or deployment.</p>
'''
    document+='<p class="note"><strong>Partial coverage: '+str(coverage['tested'])+' / '+str(coverage['total'])+' EAs tested.</strong> '+esc(missing)+' Missing members are not treated as zero-profit tests.</p>'
    document+='<p>Selected base risk: <strong>1% normal EAs, 0.10% per news order</strong>, dynamically sized from shared closed balance. Main view uses the website’s approximate full-portfolio adaptive model: 4%/7% closed DD → half/quarter risk; 3/5 consecutive lane losses → half/quarter; Nasdaq 5M ×0.25; XAU Weakness allocates half the idea budget to each entry. At −$500 daily closed P/L, new normal entries are blocked; open trades are not forcibly closed and news bypasses this replayed admission gate. These are modeled admission rules, not guaranteed loss ceilings or a certification that every live EA implements identical guards.</p>'
    document+='<div class="cards">'+cards+'</div><h2>Combined closed-balance curve</h2>'+chart(main['curve'])
    document+='<p>Floating-equity drawdown is not measured. Sharpe: not reported for a 14-day sample. No annualised short-sample Sharpe is presented as reliable evidence.</p>'
    document+='<details open><summary>Same signals without adaptive risk cuts · diagnostic only</summary><p>The comparison gives Nasdaq 5M the full 1% base setting and removes loss/DD/daily adaptive cuts. News remains 0.10%; the existing XAU Weakness two-order split is preserved. No EA selection or signal rules change.</p><table><tr><th>Metric</th><th>Main · modeled adaptive cuts</th><th>No adaptive cuts</th></tr>'+comparisons+'</table></details>'
    document+='<h2>Daily breakdown</h2><p>UTC convention; naturally completed positions only. Weekend crypto trades are included. Entry counts below count only positions naturally closed within this window.</p><div class="wide"><table><tr><th>Date</th><th>Entries</th><th>Closed</th><th>Wins / losses</th><th>Net P/L</th><th>Balance</th><th>Daily closed DD</th></tr>'+daily_rows+'</table></div>'
    document+='<h2>Every EA · contribution to the same account</h2><p>These P/L contributions add up to the main combined result. Trade counts/win rates/PF use admitted whole positions after costs. No-trade results and missing evidence are distinct. PF — means no recorded losing positions, or no trades; it is not a validated infinite edge.</p><div class="wide"><table><tr><th>EA</th><th>Asset</th><th>Evidence</th><th>Trades</th><th>Win %</th><th>PF</th><th>Shared-account P/L</th><th>Streaks W / L</th></tr>'+''.join(member_rows)+'</table></div>'
    document+='<details><summary>Full trade-by-trade breakdown</summary><div class="wide"><table><tr><th>#</th><th>EA</th><th>Entry UTC</th><th>Exit UTC</th><th>Side</th><th>Effective risk</th><th>Initial risk</th><th>Net P/L</th><th>Net R</th><th>Balance</th></tr>'+trade_rows+'</table></div></details>'
    document+='<h2>Audit and limitations</h2><ul>'+warnings+'</ul><p>News chronology checked against <a href="https://www.bls.gov/schedule/2026/09_sched.htm">September BLS schedule</a>, <a href="https://www.bls.gov/schedule/2026/10_sched.htm">October BLS schedule</a> and <a href="https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm">Federal Reserve calendar</a>. The sole watched release inside this window was NFP, 2 October 08:30 ET / 12:30 UTC.</p><p>All native case outputs, frozen inputs, source hashes, admission receipts and summary are saved beside this report. Research only; no guarantee of future results.</p></body></html>'
    (ROOT/'Results.html').write_text(document,encoding='utf-8')

def main():
    plan=read(ROOT/'PLAN.json');state=read(ROOT/'RUN_STATUS.json')
    assert state['window']==[START,END]
    expected={r['case_id'] for r in plan['cases']}
    assert set(state['complete'])|set(state['missing'])|set(state['failed'])==expected,'Native cases still pending'
    pooled=[];members=[]
    for row in plan['cases']:
        key=row['case_id'];member=dict(slug=row['slug'],label=row['label'],symbol=row['symbol'])
        if key not in state['complete']:
            member.update(status='missing' if key in state['missing'] else 'failed',reason=state['missing'].get(key,state['failed'].get(key,{}).get('error')))
        else:
            receipt=state['complete'][key];path=Path(receipt['path'])
            assert sha(path)==receipt['sha256']
            case=read(path)
            assert case['window']==[START.replace('-','.'),END.replace('-','.')] and case['no_live_changes']
            assert abs(sum(t['net'] for t in case['trades'])-case['native']['net_profit'])<.031
            normalized=risk_rows(case,row,path);pooled.extend(normalized)
            member.update(status='tested',completed_positions=len(normalized),native_positions=len(case['trades']),boundary_positions=sum(boundary(t) for t in case['trades']),
                result_sha256=receipt['sha256'],history_quality=case['native']['history_quality'],flags=case['flags'],calendar_audit=case.get('calendar_audit'),native_result=str(path))
        members.append(member)
    pooled.sort(key=lambda r:(r['key'],r['native_position_id']))
    assert len({(r['key'],r['native_position_id']) for r in pooled})==len(pooled)
    primary=scenario(pooled,True);diagnostic=scenario(pooled,False)
    assert all(sha(p)==v for row in plan['cases'] for p,v in row['production_hashes'].items()),'Production files changed during test'
    summary=dict(window=dict(start=START,end_exclusive=END),initial_balance=INITIAL,
        selected_risk=dict(normal_percent=1,news_percent_per_order=.10),
        coverage=dict(tested=sum(m['status']=='tested' for m in members),total=37,missing=[m['slug'] for m in members if m['status']!='tested']),
        members=members,scenarios=dict(current_adaptive=primary,equal_base_risk_diagnostic=diagnostic),
        no_live_changes=True,production_unchanged=True,native_simultaneous_portfolio=False,
        limitations=[
            'Combined evidence is an offline chronological shared-closed-balance risk replay of independent native Exness MT5 tests, not a simultaneous native shared-margin backtest or the live-account journal. The main adaptive overlay matches the existing website model; identical live per-EA governor coverage and loss-lane behavior are not certified by this overlay.',
            'Frozen full-roster production sources/sets/binaries verified before and after tests. Tester-only read-only wrapper rejects non-tester execution. Dedicated empty-profile terminal; live terminal not used or modified.',
            'Real-tick model with 150 ms delay; verify every member history-quality label. Source journals may contain rejected stops or volumes; only actual fills are included. Rejected entries are not idealised into successful trades.',
            'Fresh strategy sessions start at the requested boundary; no positions carried in. MT5 forced end-of-test liquidations are excluded, not treated as natural strategy exits. Native signals depend on this fresh-start convention.',
            'News risk uses requested order-entry-to-original-stop distance, read from native order history; gap-shifted filled-stop distances are not used to inflate news R. Separate order fills each receive a 0.10% budget; a two-sided event can expose approximately 0.20% before costs, gaps or rounding.',
            'Normal stop risk uses filled original entry-to-stop distance; USDJPY cash conversion is approximated at its stop price. Hourly profiles use their unchanged historical loss-distance reference and have NO protective stop; future losses can exceed that reference.',
            'Fractional lots and unlimited shared margin; broker lot minimum/step/max rounding, shared-equity sizing, pending-order capital reservation and rejected-signal retries are not reconstructed. Partial exits and whole-position costs are recognised at final close for the combined model.',
            'Millisecond native deal timestamps order the replay; equal-time exits precede entries, then deterministic slug/position order. Tester timestamps are treated as UTC consistently with the saved research clock conventions.',
            'Only closed-balance total/daily drawdowns are reported. Intratrade floating-equity DD is unavailable and is not substituted with an estimated value. Daily closed-P/L admission stops are not hard drawdown caps.',
            'Four News Pulse calendar audits cover one NFP event. This is a verified schedule receipt, not a point-in-time historical calendar vintage. Gold News V9 is missing because historical AI predictions cannot be recovered safely from its current live bridge.',
            'Fourteen calendar days are too short to infer a reliable Sharpe, pass rate or stable strategy edge. No automatic live selection, optimisation, website publication, BAT changes or Git push were made.',
        ])
    write(ROOT/'SUMMARY.json',summary);write(ROOT/'RISK_ROWS.json',pooled)
    render(summary)
    write(ROOT/'VERIFICATION.json',dict(native_cash_reconciled=True,source_hashes_unchanged=True,all_members_accounted_for=True,
        allocation_matches_existing_engine=True,daily_cash_matches_total=True,no_duplicate_positions=True,
        coverage=summary['coverage'],news_risk_reference='requested order price, not gap-shifted fill',no_live_changes=True,
        stats=primary['stats']))
    print(json.dumps(dict(coverage=summary['coverage'],main=primary['stats'],without_adaptive=diagnostic['stats']),indent=2))

if __name__=='__main__':main()
