"""Render only the completed, full-warmup V2 runs; no production/site writes."""
from pathlib import Path
from datetime import datetime, timezone
import csv, gzip, html, json, math, re
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def stamp(epoch):return datetime.fromtimestamp(epoch,timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
def number(value,digits=2):return '—' if value is None else f'{value:,.{digits}f}'
def save(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')

def closed_stats(trades,opening_balance):
    profits=[t['net'] for t in trades]
    wins=[p for p in profits if p>0];losses=[p for p in profits if p<0]
    w=l=mw=ml=0;balance=peak=opening_balance;dd=0.0
    for p in profits:
        w=w+1 if p>0 else 0;l=l+1 if p<0 else 0;mw=max(mw,w);ml=max(ml,l)
        balance+=p;peak=max(peak,balance);dd=max(dd,100*(peak-balance)/peak)
    return dict(trades=len(trades),win_rate=100*len(wins)/len(trades) if trades else None,
        pf=sum(wins)/-sum(losses) if losses else None,net_profit=sum(profits),
        return_pct=100*sum(profits)/opening_balance,closed_dd_pct=dd,win_streak=mw,loss_streak=ml,
        opening_balance=opening_balance,closing_balance=balance)

def slices(result):
    out={};end=pd.Timestamp('2026-10-09',tz='UTC')
    for label,months in [('3 months',3),('6 months',6),('1 year',12)]:
        start=end-pd.DateOffset(months=months);first=start.timestamp()
        before=[t for t in result['trades'] if t['close_epoch']<first]
        selected=[t for t in result['trades'] if first<=t['close_epoch']<end.timestamp()]
        opening=10000+sum(t['net'] for t in before)
        out[label]=dict(start=start.strftime('%Y-%m-%d'),end_exclusive='2026-10-09',
            **closed_stats(selected,opening),carry_in_trades=sum(t['open_epoch']<first for t in selected))
    return out

def annual(result):
    rows=[];balance=10000
    for year in [2023,2024,2025,2026]:
        trades=[t for t in result['trades'] if datetime.fromtimestamp(t['close_epoch'],timezone.utc).year==year]
        rows.append(dict(year=year,partial=year in [2023,2026],**closed_stats(trades,balance)))
        balance+=sum(t['net'] for t in trades)
    return rows

def equity_curve(result):
    # Daily mark-to-market observations sampled from the native 5-minute audit.
    with (ROOT/'native'/result['tag']/'equity.csv').open(encoding='utf-8-sig') as stream:
        data=list(csv.DictReader(stream))
    first=pd.Timestamp(result['analysis_window'][0].replace('.','-'),tz='UTC').timestamp()
    values={}
    for point in data:
        epoch=int(point['epoch'])
        if epoch<first:continue
        values[epoch//86400]=float(point['equity'])
    return [[day*86400,100*(value/10000-1)] for day,value in sorted(values.items())]

def table(rows,full=True):
    body=''
    for row in rows:
        m=row['metrics']
        body+='<tr><td>'+html.escape(row['symbol'])+'</td><td>'+html.escape(row['mode'])+'</td>'
        body+=''.join('<td>'+number(m.get(key),digits)+'</td>' for key,digits in
            [('trades',0),('win_rate',1),('pf',2),('return_pct',2),('equity_dd_pct' if full else 'closed_dd_pct',2)])
        body+='<td>'+str(m['win_streak'])+' / '+str(m['loss_streak'])+'</td>'
        if full:body+='<td>'+number(m.get('sharpe_daily_equity'))+'</td>'
        body+='</tr>'
    labels=['Pair','Risk basis','Trades','Win %','PF','Return %','Max equity DD %' if full else 'Closed DD %','Win / loss streak']+(['Sharpe'] if full else [])
    return '<div class="table"><table><thead><tr>'+''.join('<th>'+x+'</th>' for x in labels)+'</tr></thead><tbody>'+body+'</tbody></table></div>'

def chart(rows):
    curves=[(r,equity_curve(r['result'])) for r in rows]
    if not curves or not any(c for _,c in curves):return ''
    low=min(v for _,curve in curves for _,v in curve);high=max(v for _,curve in curves for _,v in curve)
    low=min(low,0)-3;high=max(high,0)+3
    begin=min(t for _,curve in curves for t,_ in curve);end=max(t for _,curve in curves for t,_ in curve)
    colors={'EURUSD':'#78edcd','GBPUSD':'#b2ed6a','USDJPY':'#fcaa75'}
    svg='<svg viewBox="0 0 1020 310" role="img" aria-label="Independent three-year account equity curves">'
    for j in range(5):
        y=20+j*62.5;v=high-j*(high-low)/4
        svg+=f'<line x1="70" y1="{y}" x2="990" y2="{y}" stroke="#22483d"/><text x="5" y="{y+5}" fill="#98b5ac" font-size="14">{v:.0f}%</text>'
    for r,curve in curves:
        points=' '.join(f'{70+(t-begin)/(end-begin)*920:.1f},{20+(high-v)/(high-low)*250:.1f}' for t,v in curve)
        dash=' stroke-dasharray="8 5"' if r['mode']=='high-water' else ''
        svg+=f'<polyline points="{points}" fill="none" stroke="{colors[r["symbol"]]}" stroke-width="2"{dash}/>'
    svg+='<text x="70" y="303" fill="#98b5ac">9 Oct 2023</text><text x="895" y="303" fill="#98b5ac">8 Oct 2026</text></svg>'
    return svg+'<p>EURUSD: mint · GBPUSD: lime · USDJPY: orange. Solid = current balance; dashed = high-water balance. Each curve is its own $10,000 account—not a combined portfolio.</p>'

def main():
    plan=read(ROOT/'PLAN-V2.json');state=read(ROOT/'RUN_STATUS-V2.json')
    assert len(state['complete'])==12 and not state['failed'],state
    rows=[];checks=[]
    for case in plan['cases']:
        result=read(Path(state['complete'][case['slug']]['path']))
        journal=gzip.decompress((ROOT/'native'/result['tag']/'journal.txt.gz').read_bytes()).decode()
        starts=re.findall(r'real ticks begin from (\d{4}\.\d{2}\.\d{2})',journal)
        assert starts and set(starts)=={'2026.01.01'},set(starts)
        assert 'ZONE_HISTORY_INSUFFICIENT' not in journal
        assert not any(result['flags'].values()),result['flags']
        assert result['inputs']['InpRiskPercent']=='0.5'
        assert result['inputs']['InpHighWaterSizing']==str(case['mode']=='high-water').lower()
        first=pd.Timestamp(case['analysis_start'].replace('.','-'),tz='UTC').timestamp()
        assert all(t['open_epoch']>=first for t in result['trades'])
        assert abs(sum(t['net'] for t in result['trades'])-result['native']['net_profit'])<.031
        warmups=re.findall(r'ZONE_WARMUP first=(\d{4}\.\d{2}\.\d{2})',journal)
        assert warmups and pd.Timestamp(warmups[0].replace('.','-'),tz='UTC').timestamp()<=first-723*86400
        gaps=re.findall(r'[^\r\n]*(?:real ticks absent|ticks discarded)[^\r\n]*',journal,re.I)
        row=dict(symbol=case['symbol'],mode=case['mode'],window=case['window'],metrics=result['metrics'],
            real_tick_start='2026-01-01',native_engine_quality=result['native']['history_quality'],result=result,
            terminal_end_closures=result['tester_end_liquidations'])
        if case['window']=='3y':row.update(recent=slices(result),annual=annual(result))
        rows.append(row);checks.append(dict(slug=case['slug'],cash_reconciled=True,no_warmup_orders=True,
            complete_two_year_zone_history=True,active_inputs_verified=True,no_runtime_or_order_errors=True,tick_gaps=gaps))
        fields=['position_id','open_epoch','close_epoch','side','volume','open_price','close_price','sl','tp','net','gross','commission','swap','fee']
        with (ROOT/(case['slug']+'-trades.csv')).open('w',encoding='utf-8-sig',newline='') as stream:
            writer=csv.DictWriter(stream,fields+['entry_utc','exit_utc']);writer.writeheader()
            for t in result['trades']:writer.writerow({**{k:t[k] for k in fields},'entry_utc':stamp(t['open_epoch']),'exit_utc':stamp(t['close_epoch'])})
    assert not any(c['tick_gaps'] for c in checks),'Real-tick gaps need explicit investigation'
    by_window={w:[r for r in rows if r['window']==w] for w in ['3y','2026']}
    for window,group in by_window.items():
        for symbol in ['EURUSD','GBPUSD','USDJPY']:
            a,b=[r['result'] for r in group if r['symbol']==symbol]
            # Weighted whole-position exit prices can differ by machine epsilon
            # when lot size changes; compare at finer than FX quote precision.
            identities=lambda r:[(t['open_epoch'],t['close_epoch'],t['side'],round(t['open_price'],8),round(t['close_price'],8)) for t in r['trades']]
            assert identities(a)==identities(b),(symbol,window,'Sizing altered signal/fill parity')
    recent=''
    for period in ['3 months','6 months','1 year']:
        group=[dict(symbol=r['symbol'],mode=r['mode'],metrics=r['recent'][period]) for r in by_window['3y']]
        start=by_window['3y'][0]['recent'][period]['start']
        recent+='<h3>'+period+' · '+start+' → 8 Oct 2026</h3>'+table(group,False)
    annual_table='<div class="table"><table><tr><th>Pair</th><th>Risk basis</th><th>2023 partial %</th><th>2024 %</th><th>2025 %</th><th>2026 YTD %</th></tr>'
    for r in by_window['3y']:
        annual_table+='<tr><td>'+r['symbol']+'</td><td>'+r['mode']+'</td>'+''.join('<td>'+number(x['return_pct'])+'</td>' for x in r['annual'])+'</tr>'
    annual_table+='</table></div>'
    warning='This is an approved mechanical proxy, not the author’s exact unpublished code. Fixed 2R targets differ from the original nearest-structure target. No claim to reproduce +493%.'
    content='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Forex Daily Zone · raw reconstruction</title><style>
    *{box-sizing:border-box}body{margin:0;background:#07120f;color:#e9f6f0;font:16px/1.6 system-ui,sans-serif}main{max-width:1280px;margin:auto;padding:35px 26px}h1{font-size:34px;line-height:1.2}h2{margin-top:35px}h3{color:#83f1d0}p,li{color:#a8c4b9}.tag{color:#84f1cc;font-size:13px;letter-spacing:2px}.warning{padding:20px;border:1px solid #8a7631;background:#222114;border-radius:14px}.panel{padding:25px;border:1px solid #285044;border-radius:18px;margin:25px 0;background:#0b1d17}.table{overflow:auto}table{width:100%;border-collapse:collapse;white-space:nowrap;font-size:14px}th{text-align:left;color:#83edcb;padding:12px;border-bottom:1px solid #38604f}td{padding:12px;border-bottom:1px solid #1d382e}svg{width:100%;display:block;margin-top:25px}a{color:#8ff5d6}.small{font-size:13px}summary{color:#87eccb;cursor:pointer}
    </style><main><div class="tag">CALYX · RESEARCH ONLY · NO LIVE CHANGES</div><h1>Daily-zone reversal · M15</h1><p>EURUSD, GBPUSD and USDJPY · $10,000 per independent account · 0.5% sizing · 6-pip stop buffer · fixed 2R target. Raw defaults frozen before testing; no optimization.</p>'''
    content+='<div class="warning">'+warning+'<br><br>Exness real ticks begin on 1 January 2026. Earlier trading uses generated ticks from historical bars. The three-year screen is preliminary, not validated tick-level evidence. A separate fresh-start 2026 test below isolates the available real-tick trading period.</div>'
    content+='<section class="panel"><h2>Three years · 9 Oct 2023 → 8 Oct 2026</h2><p>End exclusive: 9 Oct 2026. Two extra years of no-trade engine warmup ensure complete zones at the first entry.</p>'+table(by_window['3y'])+chart(by_window['3y'])+'</section>'
    content+='<section class="panel"><h2>Fresh-start 2026 · 1 Jan → 8 Oct</h2><p>New $10,000 accounts, with two years of no-trade warmup. All trading is after the verified broker real-tick start; no absent/discarded-tick warnings. Native whole-engine quality percentages include synthetic warmup years and must not be mistaken for trading-window coverage.</p>'+table(by_window['2026'])+'</section>'
    content+='<section class="panel"><h2>Recent history slices</h2><p>These are slices of the three-year accounts, not fresh-start independent tests. Returns use each account’s closed balance at the start of the slice. Trades are grouped by final close; carry-in positions can be included. DD here is closed-balance only, not floating equity. Last-year coverage spans both generated and real ticks.</p>'+recent+'</section>'
    content+='<section class="panel"><h2>Calendar-year closed returns</h2><p>Chronological cash slices of each three-year account; 2023 starts on 9 October and 2026 ends on 8 October. Carries and account sizing differ from the fresh-start 2026 test.</p>'+annual_table+'</section>'
    rules=['D1 body highs/lows must be confirmed by two completed daily bars on each side; wicks are not used.',
        'Only prior 730 calendar days are used. Price-sort pivots and greedily cluster bands spanning no more than 60 pips; pad narrow bands to 5 pips. Require three distinct daily candles. Rebuild daily.',
        'Buy when a completed M15 close moves from above a band into it; sell when the previous close was below and the new close is inside. Fill on the next available tick.',
        'Stop 6 pips past the far zone edge. Target 2 times actual requested entry-to-stop distance. No trailing, partials, break-even or session exit.',
        'One position per pair; entries during an open position are skipped. No bias, trend, candle pattern, retest or session filters.',
        'Current-balance sizing risks 0.5% of closed balance. High-water sizing risks 0.5% of the highest observed closed balance. High-water risk becomes more than 0.5% of the remaining balance during drawdowns.',
        'Real broker lot increments are rounded down. The broker tester applies spreads, commission and swap; 150 ms execution delay. Historic fee-vintage parity with the author’s IC Markets study is not claimed.']
    content+='<details class="panel"><summary>Frozen reconstruction rules and measurement details</summary><ul>'+''.join('<li>'+html.escape(x)+'</li>' for x in rules)+'</ul><p>Full-run DD is native tick-by-tick equity drawdown. Sharpe uses daily sampled mark-to-market equity, weekday returns, √252 and zero risk-free rate. Win/loss streaks use cost-inclusive whole positions. Engine-end liquidations: '+str(sum(r['terminal_end_closures'] for r in rows))+'. Those remain included in standard native final valuations.</p><p><a href="https://www.youtube.com/watch?v=HzVSi9ux1NU">Researcher’s simplified-strategy video</a> · <a href="https://www.youtube.com/watch?v=nFIJ0z8_01w">Original rule audit</a>. Synthetic-history limitations and the reconstruction prevent treating these results as an exact replication or untouched validation of the advertised edge.</p></details>'
    content+='<p class="small">Raw output, active inputs, source hashes, native reports and cost-inclusive trade CSVs are saved beside this report. Initial partial-warmup diagnostic runs are preserved but excluded from all tables above. No production files, website or live account changed.</p></main></html>'
    (ROOT/'Results.html').write_text(content,encoding='utf-8')
    save(ROOT/'SUMMARY.json',dict(plan=plan,rows=[{k:v for k,v in r.items() if k!='result'} for r in rows],completed=12,
        limitations=[warning,'Pre-2026 trading relies on generated ticks.','Only three approved pairs, not the original 16-pair combined portfolio.'],
        comparison='Two independent account sizing methods; no combined portfolio.',no_live_changes=True))
    save(ROOT/'VERIFICATION.json',dict(cases=checks,all_native_cash_reconciled=True,full_zone_warmup=True,
        risk_modes_signal_fill_parity=True,original_partial_warmup_runs_excluded=True,no_production_changes=True))
    print(json.dumps([{k:r[k] for k in ['symbol','mode','window','metrics']} for r in rows],indent=2))

if __name__=='__main__':main()
