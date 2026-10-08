"""Independent raw-deal reconciliation, yearly net results and offline ledger."""
from pathlib import Path
from html import escape
from html.parser import HTMLParser
from datetime import datetime,timezone
import gzip,hashlib,json,re,statistics,math
import numpy as np
import pandas as pd

R=Path(__file__).resolve().parent
def save(name,v):(R/name).write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
class Rows(HTMLParser):
    def __init__(self):super().__init__();self.rows=[];self.row=None;self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=='tr':self.row=[]
        elif tag in ('td','th') and self.row is not None:self.cell=[]
    def handle_data(self,data):
        if self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.cell is not None:self.row.append(''.join(self.cell).replace('\xa0',' ').strip());self.cell=None
        elif tag=='tr' and self.row is not None:self.rows.append(self.row);self.row=None
def number(s):return float(s.replace(' ','').replace(',',''))
def metric(rows,label):
    for row in rows:
        for i,v in enumerate(row[:-1]):
            if v==label+':':return row[i+1]
    raise AssertionError(label)
def money(x):return f'{x:+,.2f}'
def fmt(x,dp=2):return '—' if x is None else f'{x:.{dp}f}'
def stats(ts,initial):
    pnls=[t['net_profit'] for t in ts];positive=sum(x for x in pnls if x>0);negative=-sum(x for x in pnls if x<0)
    mw=ml=w=l=0;balance=peak=initial;dd=0
    for x in pnls:
        if x>0:w+=1;l=0
        elif x<0:l+=1;w=0
        else:w=l=0
        mw=max(mw,w);ml=max(ml,l);balance+=x;peak=max(peak,balance);dd=max(dd,100*(peak-balance)/peak)
    return dict(trades=len(ts),wins=sum(x>0 for x in pnls),losses=sum(x<0 for x in pnls),win_rate_pct=100*sum(x>0 for x in pnls)/len(ts) if ts else None,
        net=round(sum(pnls),2),return_pct=sum(pnls)/initial*100,pf=positive/negative if negative else None,net_R=sum(t['net_R'] for t in ts),
        closed_balance_dd_pct=dd,max_win_streak=mw,max_loss_streak=ml,average_net=statistics.mean(pnls) if pnls else None,
        average_win=statistics.mean(x for x in pnls if x>0) if positive else None,average_loss=statistics.mean(x for x in pnls if x<0) if negative else None,
        commission=round(sum(t['commission'] for t in ts),2),swap=round(sum(t['swap'] for t in ts),2))

cases=json.loads((R/'RESULTS.json').read_text());assert len(cases)==3 and all(c['manifest']['name'].endswith('-final') for c in cases)
calendar=json.loads((R/'CALENDAR.json').read_text())
source=(R/'EA/BollingerResearch.mq5').read_text()
assert all(str(key) in source for key in calendar['closed']+calendar['early_close_1300'])
verification=[];summaries=[]
for c in cases:
    out=R/'native'/c['manifest']['name'];raw=gzip.decompress((out/'report.htm.gz').read_bytes());assert hashlib.sha256(raw).hexdigest()==c['report_sha256']
    try:html=raw.decode('utf-16')
    except UnicodeError:html=raw.decode('utf-8-sig')
    p=Rows();p.feed(html)
    assert number(metric(p.rows,'Initial Deposit'))==10000
    net=number(metric(p.rows,'Total Net Profit'));assert abs(net-sum(t['net_profit'] for t in c['trades']))<.03
    deals=[row for row in p.rows if len(row)==13 and row[2]=='USTEC' and row[3] in ('buy','sell') and row[4] in ('in','out')]
    assert len(deals)==2*len(c['trades']) and abs(sum(number(x[8])+number(x[9])+number(x[10]) for x in deals)-net)<.03
    entries=[x for x in deals if x[4]=='in'];exits=[x for x in deals if x[4]=='out'];balance=10000
    for t,e,x in zip(c['trades'],entries,exits):
        assert e[0].replace('.','-',2).replace(' ','T')==t['open_time'] and x[0].replace('.','-',2).replace(' ','T')==t['close_time']
        assert number(e[5])==number(x[5])==t['volume'] and number(e[6])==t['open_price'] and number(x[6])==t['close_price']
        assert abs(number(e[8])+number(x[8])-t['commission'])<.011
        assert abs(number(e[9])+number(x[9])-t['swap'])<.011
        assert abs(number(e[10])+number(x[10])-t['gross_profit'])<.011
        assert abs(t['net_R']-t['net_profit']/t['initial_risk_cash'])<1e-9
        assert t['open_ny'][:10]==t['close_ny'][:10],'Position crossed cash-session date'
        key=int(t['open_ny'][:10].replace('-',''));assert key not in calendar['closed']
        ny=pd.Timestamp(t['open_ny']);end=778 if key in calendar['early_close_1300'] else 958
        assert 570<=ny.hour*60+ny.minute<end
        assert t['initial_sl']<t['open_price'] if t['side']=='Long' else t['initial_sl']>t['open_price']
        if c['manifest']['inputs']['InpVariant']!='1':assert t['initial_tp']==0
        t['balance_before']=round(balance,2);balance+=t['net_profit'];t['balance_after']=round(balance,2)
    bars=pd.DataFrame(json.loads((out/'bar-checks.json').read_text())).sort_values('signal_time')
    assert bars['signal_time'].is_unique
    middle=bars['close'].rolling(20).mean();sd=bars['close'].rolling(20).std(ddof=0)
    # Discard the initial warmup, which uses cached pre-2020 observations not included in trace.
    err_mid=(bars['middle']-middle).abs().iloc[20:]
    err_up=(bars['upper']-(middle+2*sd)).abs().iloc[20:]
    err_low=(bars['lower']-(middle-2*sd)).abs().iloc[20:]
    indicator_checks=int((err_mid<1e-5).sum());mismatches=int((err_mid>=1e-5).sum())
    # Missing BB_BAR readings cannot justify mismatched windows; fail and inspect rather than claim parity.
    assert mismatches==0 and err_up.max()<1e-4 and err_low.max()<1e-4,(mismatches,err_mid.max(),err_up.max(),err_low.max())
    total=stats(c['trades'],10000);total['floating_dd_pct']=c['native']['equity_dd_pct'];total['native_sharpe']=c['native']['sharpe_ratio'];total['daily_closed_balance_sharpe']=c['summary']['daily_realized_sharpe']
    yearly=[];initial=10000
    for y in range(2020,2024):
        ts=[t for t in c['trades'] if t['close_time'].startswith(str(y))];row=dict(year=y,start_balance=round(initial,2),**stats(ts,initial));initial+=row['net'];row['end_balance']=round(initial,2);yearly.append(row)
    assert abs(initial-balance)<.03
    shorts=[t for t in c['trades'] if t['side']=='Short'];longs=[t for t in c['trades'] if t['side']=='Long']
    summary=dict(version=c['manifest']['label'],name=c['manifest']['name'],total=total,yearly=yearly,long=stats(longs,10000),short=stats(shorts,10000),exit_reasons=c['summary']['exit_reasons'],
        history_quality=c['native']['history_quality'],tick_mode=c['manifest']['tick_mode'])
    summaries.append(summary)
    verification.append(dict(case=c['manifest']['name'],raw_deals=len(deals),positions=len(c['trades']),reconciled=True,lookahead_checks=c['signal_checks'],
        independently_checked_band_windows=indicator_checks,maximum_band_error=float(max(err_mid.max(),err_up.max(),err_low.max())),boundary_exits=c['summary']['boundary_exits'],cross_session_date_holdings=0))
assert len(set(c['manifest']['binary_sha256'] for c in cases))==1
assert all(c['manifest']['from_date']=='2020-01-01' and c['manifest']['end_exclusive']=='2024-01-01' for c in cases)
save('SUMMARY.json',summaries);save('VERIFICATION.json',dict(passed=True,cases=verification,compiled_binary_same=True,parameters_not_optimised=True))

def table(headers,rows):
    return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+escape(v)+'</th>' for v in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+escape(str(v))+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
headers=['Version','Trades','Win rate','Net PF','Net R','Return','Net profit $','Max floating DD','Native Sharpe','Max W / L streak']
overview=table(headers,[[s['version'],s['total']['trades'],fmt(s['total']['win_rate_pct'],1)+'%',fmt(s['total']['pf']),money(s['total']['net_R'])+'R',money(s['total']['return_pct'])+'%',money(s['total']['net']),fmt(s['total']['floating_dd_pct'])+'%',fmt(s['total']['native_sharpe']),f"{s['total']['max_win_streak']} / {s['total']['max_loss_streak']}"] for s in summaries])
sections=[]
for s,c in zip(summaries,cases):
    section='<section><h2>'+escape(s['version'])+'</h2>'
    section+=table(['Year','Trades','Win rate','Net PF','Net R','Return on year-start balance','Net $','Closed balance DD only','W / L streak','Start $','End $'],[[y['year'],y['trades'],fmt(y['win_rate_pct'],1)+'%',fmt(y['pf']),money(y['net_R'])+'R',money(y['return_pct'])+'%',money(y['net']),fmt(y['closed_balance_dd_pct'])+'%',f"{y['max_win_streak']} / {y['max_loss_streak']}",fmt(y['start_balance']),fmt(y['end_balance'])] for y in s['yearly']])
    section+=f"<p>Average net trade ${s['total']['average_net']:.2f}; average win ${s['total']['average_win']:.2f}; average loss ${s['total']['average_loss']:.2f}. Commission ${s['total']['commission']:.2f}; swap ${s['total']['swap']:.2f}. Native reported history quality: {escape(s['history_quality'])}. The selected tick mode is simulated from historical minute bars regardless of that label.</p>"
    section+=table(['Direction','Trades','Win rate','Net PF','Net R','Net $'],[[label,v['trades'],fmt(v['win_rate_pct'],1)+'%',fmt(v['pf']),money(v['net_R'])+'R',money(v['net'])] for label,v in [('Long',s['long']),('Short',s['short'])]])
    section+=table(['Exit reason','Positions'],[[k,v] for k,v in s['exit_reasons'].items()])
    out=R/'native'/s['name'];image=out/(s['name']+'.png')
    if image.exists():section+=f'<img class="native" src="native/{s["name"]}/{image.name}" alt="Native tester balance and equity curve">'
    section+='<details><summary>Every trade — expand full ledger</summary>'
    section+=table(['#','Entry UTC','Exit UTC','Side','Lots','Entry','Initial SL','Initial TP','Exit price','Exit reason','Net $','Net R','Held hours','Commission $','Swap $','Balance $'],[[t['number'],t['open_time'],t['close_time'],t['side'],fmt(t['volume']),fmt(t['open_price']),fmt(t['initial_sl']),fmt(t['initial_tp']) if t['initial_tp'] else 'None',fmt(t['close_price']),t['exit_reason'],money(t['net_profit']),fmt(t['net_R'],3)+'R',fmt(t['hold_hours']),money(t['commission']),money(t['swap']),fmt(t['balance_after'])] for t in c['trades']])
    section+='</details></section>';sections.append(section)
page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bollinger US100 H1 — 2020–2023 raw test</title><style>:root{color-scheme:dark}body{margin:0;background:#081410;color:#e5f2ec;font:15px/1.6 system-ui,sans-serif}main{max-width:1500px;margin:auto;padding:32px 24px 70px}h1{font-size:clamp(25px,3vw,40px);line-height:1.25}h2,summary{color:#82ebc7}p{max-width:1150px;color:#b9cec4}.warn{padding:16px;background:#372e18;color:#f6dea4;border:1px solid #786537;border-radius:12px}.scroll{overflow:auto;border:1px solid #2b493d;border-radius:10px;margin:18px 0}table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}td,th{padding:11px 14px;text-align:left;white-space:nowrap;border-bottom:1px solid #243d32}th{background:#15372a;color:#9be9c7}section{margin:34px 0}details{border:1px solid #2b493d;border-radius:10px;padding:16px}summary{cursor:pointer}.native{max-width:100%;height:auto;background:white;border-radius:8px}a{color:#88e8c0}footer{border-top:1px solid #2b493d;padding-top:18px;font-size:13px}</style></head><body><main><p>RESEARCH ONLY · NO OPTIMISATION · NO LIVE CHANGES</p><h1>Bollinger breakout vs reversal: US100 H1</h1><p>1 January 2020 → 31 December 2023 inclusive. Exness USTEC CFD, USD10,000 flat start, 1% equity target risk per position, broker-valid lots rounded down, 150 ms simulated execution delay.</p>
<p class="warn">The clip did not provide its code, instrument, exact bands, stop or session. This is a transparent baseline recreation, NOT a claim of reproducing its +72R, +122R or random-strategy significance. Historical 2020–2023 ticks are generated from minute bars, not authentic tick records. Intrabar fills and stop/target ordering are model-dependent. No post-2023/OOS test or 100-random-strategy comparison has been performed.</p>
<h2>Frozen rules and assumptions</h2><p>Bollinger 20 SMA ±2 population standard deviations of completed H1 closes, ATR14, initial stop 2×signal ATR. Indicators use the continuous CFD session; entries are restricted to the US cash session, weekdays 09:30–15:58 New York normally (DST-aware). UTC-aligned H1 bars mean the first eligible hourly decision is normally 10:00 NY. Close above upper band buys; below lower band sells; any completed outside-band candle qualifies while flat. One position at a time; no DI/ADX/news filter. No same-bar reversal after a midpoint exit.</p><p>Main exit: a long exits after a completed H1 close at/below the developing middle band; a short at/above it. This is a closed-bar exit, NOT a continuously moving broker stop. Initial hard stop remains active. Scheduled flattening is 15:58 NY normally and 12:58 NY on published 13:00 half-days, with liquidation one minute before an earlier native broker-session close. This buffer avoids missing final-minute archived quotes and broker trade pauses. Published 2020–2023 holidays and half-days are encoded; the final runs have no cross-session-date holdings. Earlier failed or carried-overnight revisions are diagnostic evidence only, not the final performance comparison. Both controls share the same hard stop/session calendar; fixed 2R removes the middle-band exit, while contrarian flips entry direction and exits favourably back through the middle.</p>
'''+overview+''.join(sections)+'''<section><h2>How to interpret the figures</h2><p>Net-position PF = sum of winning position P&amp;L ÷ absolute sum of losing position P&amp;L, including entry/exit commission and swaps. R = each net position P&amp;L ÷ its original stop cash exposure from the filled entry, then summed; it is not the compounded account return. Overall floating drawdown and native Sharpe come from the tester. Yearly drawdown is CLOSED-BALANCE ONLY, not floating-equity drawdown. Yearly percentages use the continuous run's balance at each year's start, not four independently reset $10,000 accounts. Spread/slippage are embedded in native bid/ask fills. Target risk excludes costs/gaps and is not a guarantee of maximum loss.</p><p>Implementation references: <a href="https://www.mql5.com/en/docs/indicators/ibands">MetaQuotes iBands buffers</a>, <a href="https://www.mql5.com/en/docs/indicators/iatr">native ATR</a>, <a href="https://www.metatrader5.com/en/terminal/help/algotrading/testing">MT5 testing modes</a>. Session calendar: <a href="https://ir.theice.com/press/news-details/2019/NYSE-Group-Announces-2020-2021-and-2022-Holiday-and-Early-Closings-Calendar/default.aspx">2020–2022 official calendar</a>, <a href="https://ir.theice.com/press/news-details/2021/NYSE-Group-Announces-2022-2023-and-2024-Holiday-and-Early-Closings-Calendar/default.aspx">2022–2023 official calendar</a>. These document the tools/calendar, not evidence for strategy profitability.</p></section><footer>See SUMMARY.json for metrics, VERIFICATION.json for independent native-deal/cost/indicator/calendar checks, and native/*/trades.csv for full export. All three final runs share one research-only binary and differ only in the declared entry/exit variant. No production EA, installer, live account or website changed.</footer></main></body></html>'''
(R/'Results.html').write_text(page,encoding='utf-8')
qa=Rows();qa.feed(page);assert page.count('<table>')==page.count('</table>') and page.count('<details>')==3
assert len([row for row in qa.rows if row and re.fullmatch(r'\d+',row[0]) and len(row)==16])==sum(len(c['trades']) for c in cases)
save('HTML-QA.json',dict(passed=True,bytes=len(page.encode()),tables=page.count('<table>'),trade_ledgers=3,positions=sum(len(c['trades']) for c in cases)))
print(json.dumps(summaries,indent=2))
