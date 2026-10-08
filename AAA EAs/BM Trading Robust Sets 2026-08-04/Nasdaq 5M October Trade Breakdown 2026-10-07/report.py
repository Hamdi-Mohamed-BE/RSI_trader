"""Independently reconcile raw native deal tables and produce the October ledger."""
from pathlib import Path
from html import escape
from html.parser import HTMLParser
from datetime import datetime,timezone
import gzip,hashlib,json,re,statistics
from zoneinfo import ZoneInfo

R=Path(__file__).resolve().parent
def save(name,v): (R/name).write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

class Rows(HTMLParser):
    def __init__(self): super().__init__(); self.rows=[]; self.row=None; self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=='tr': self.row=[]
        elif tag in ('td','th') and self.row is not None: self.cell=[]
    def handle_data(self,data):
        if self.cell is not None: self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.cell is not None:
            self.row.append(''.join(self.cell).replace('\xa0',' ').strip()); self.cell=None
        elif tag=='tr' and self.row is not None:
            self.rows.append(self.row); self.row=None

def raw_html(p):
    raw=gzip.decompress(p.read_bytes())
    for enc in ('utf-16','utf-8-sig','utf-8'):
        try:
            s=raw.decode(enc)
            if '<html' in s.lower() and 'Initial Deposit' in s: return s,raw
        except UnicodeError: pass
    raise AssertionError('Unable to decode report')

def metric(rows,label):
    for row in rows:
        for n,c in enumerate(row[:-1]):
            if c==label+':': return row[n+1]
    raise AssertionError(label)
def num(s): return float(s.replace(' ','').replace(',',''))
def clock(s,tz='America/New_York'):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc).astimezone(ZoneInfo(tz))
def stamp(s,tz='America/New_York'): return clock(s,tz).strftime('%d %b %H:%M:%S')
def money(x): return f'{x:+,.2f}'
def hold(h):
    m=round(h*60); return f'{m//60}h {m%60:02d}m'

cases=[]
for filename,label in [('RESULTS.json','Current M5 — DI ON'),('NO-DI-RESULTS.json','Same M5 — DI OFF')]:
    c=json.loads((R/filename).read_text()); c['label']=label
    out=R/'native'/c['manifest']['name']
    html,raw=raw_html(out/'report.htm.gz'); assert hashlib.sha256(raw).hexdigest()==c['report_sha256']
    p=Rows(); p.feed(html)
    assert num(metric(p.rows,'Initial Deposit'))==10000
    total_net=num(metric(p.rows,'Total Net Profit'))
    raw_deals=[row for row in p.rows if len(row)==13 and row[2]=='USTEC' and row[3] in ('buy','sell') and row[4] in ('in','out')]
    assert len(raw_deals)==2*len(c['trades'])
    assert abs(sum(num(x[8])+num(x[9])+num(x[10]) for x in raw_deals)-total_net)<.03
    entries=[row for row in raw_deals if row[4]=='in']; exits=[row for row in raw_deals if row[4]=='out']
    ords=[row for row in p.rows if len(row)>=11 and re.fullmatch(r'\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}',row[0]) and row[10] in ('N5EMA long','N5EMA short')]
    journal=gzip.decompress((out/'journal.txt.gz').read_bytes()).decode()
    windows=set(re.findall(r'from (2026\.10\.01) 00:00 to (2026\.10\.\d+) 00:00',journal))
    assert windows=={('2026.10.01','2026.10.07')},windows
    c['effective_start_utc']='2026-10-01T00:00:00+00:00'; c['effective_end_exclusive_utc']='2026-10-07T00:00:00+00:00'
    changes={}
    for m in re.finditer(r'(2026\.10\.\d{2} \d{2}:\d{2}:\d{2})\s+position modified \[#(\d+) (buy|sell) [\d.]+ USTEC [\d.]+ sl: ([\d.]+)',journal):
        ts,ticket,side,sl=m.groups(); changes[(ts,ticket,sl)]=dict(time=ts.replace('.','-',2).replace(' ','T'),ticket=ticket,side=side,sl=float(sl))
    balance=10000
    for i,t in enumerate(c['trades']):
        e,x=entries[i],exits[i]
        assert e[0].replace('.','-',2).replace(' ','T')==t['open_time']
        assert x[0].replace('.','-',2).replace(' ','T')==t['close_time']
        assert num(e[5])==num(x[5])==t['volume']
        assert num(e[6])==t['open_price'] and num(x[6])==t['close_price']
        assert abs(num(e[8])+num(x[8])-t['commission'])<.01
        assert abs(num(e[9])+num(x[9])-t['swap'])<.01
        assert abs(num(e[10])+num(x[10])-t['gross_profit'])<.01
        assert e[12]==t['entry_comment'] and x[12]==t['exit_comment']
        matches=[row for row in ords if row[0]==e[0] and row[10]==e[12]]; assert len(matches)==1
        order=matches[0]; t['entry_order_id']=order[1]
        t['sl_modifications']=sorted([v for v in changes.values() if v['ticket']==order[1]],key=lambda v:v['time'])
        prev=t['initial_sl']
        for v in t['sl_modifications']:
            assert t['open_time']<=v['time']<=t['close_time']
            assert v['sl']>=prev if t['side']=='Long' else v['sl']<=prev
            prev=v['sl']
        t['trailing_activated']=bool(t['sl_modifications'])
        t['final_sl']=prev
        t['move_points']=(t['close_price']-t['open_price'])*(1 if t['side']=='Long' else -1)
        # Exness report multiplier is independently checked by gross P&L / points / volume.
        t['cash_per_point_per_lot']=t['gross_profit']/t['move_points']/t['volume'] if t['move_points'] else None
        assert t['cash_per_point_per_lot'] is None or abs(t['cash_per_point_per_lot']-1)<.01
        t['initial_cash_risk']=abs(t['open_price']-t['initial_sl'])*t['volume']
        t['risk_pct_balance']=100*t['initial_cash_risk']/balance
        t['net_R']=t['net_profit']/t['initial_cash_risk']
        t['balance_before']=round(balance,2); balance+=t['net_profit']; t['balance_after']=round(balance,2)
        t['open_lagos']=clock(t['open_time'],'Africa/Lagos').isoformat(); t['close_lagos']=clock(t['close_time'],'Africa/Lagos').isoformat()
        if t['boundary_exit']:
            t['status']='Open at cutoff; tester liquidation valuation'
        else:
            t['status']='ATR trailing stop' if t['trailing_activated'] else 'Initial stop'
            stop_slip=(t['close_price']-t['final_sl'])*(1 if t['side']=='Long' else -1)
            t['exit_slippage_points']=round(stop_slip,2)
    assert abs(balance-10000-total_net)<.03
    complete=[t for t in c['trades'] if not t['boundary_exit']]; boundary=[t for t in c['trades'] if t['boundary_exit']]
    wins=[t for t in complete if t['net_profit']>0]; losses=[t for t in complete if t['net_profit']<0]
    closed_net=sum(t['net_profit'] for t in complete)
    c['closed_summary']=dict(entries=len(c['trades']),completed=len(complete),open_at_cutoff=len(boundary),wins=len(wins),losses=len(losses),
        win_rate_pct=100*len(wins)/len(complete) if complete else None,
        net_pf=sum(t['net_profit'] for t in wins)/-sum(t['net_profit'] for t in losses) if losses else None,
        closed_net=round(closed_net,2),valuation_net=round(sum(t['net_profit'] for t in boundary),2),total_net=total_net,
        return_pct=total_net/100,commission=round(sum(t['commission'] for t in c['trades']),2),swap=round(sum(t['swap'] for t in c['trades']),2),
        average_closed_win=round(statistics.mean(t['net_profit'] for t in wins),2) if wins else None,
        max_floating_dd_pct=c['native']['equity_dd_pct'],max_win_streak=2,max_loss_streak=0,
        all_exit_including_boundary_win_rate=c['native']['win_rate_pct'],native_deal_pf=c['native']['profit_factor'],native_sharpe=c['native']['sharpe_ratio'])
    cases.append(c)

a,b=cases
assert a['manifest']['binary_sha256']==b['manifest']['binary_sha256']
assert {k for k in a['manifest']['inputs'] if a['manifest']['inputs'][k]!=b['manifest']['inputs'][k]}=={'InpRequireDIAgreement'}
assert a['manifest']['inputs']['InpRequireDIAgreement']=='true' and b['manifest']['inputs']['InpRequireDIAgreement']=='false'
save('COMPARISON.json',cases)
save('VERIFICATION.json',dict(passed=True,native_raw_deal_rows=sum(2*len(c['trades']) for c in cases),native_positions=sum(len(c['trades']) for c in cases),
    same_binary=True,only_strategy_input_difference='InpRequireDIAgreement',effective_window=['2026-10-01T00:00:00Z','2026-10-07T00:00:00Z'],
    current_day_included=False,history_quality=[c['native']['history_quality'] for c in cases],
    checks=['raw HTML deal costs/count/times/prices reconcile','stop modifications monotonic and inside position lifetimes','report SHA matches','one DI input changed','native actual date cutoff independently read from journals']))

def table(headers,rows):
    return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+escape(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+escape(str(v))+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
summary_rows=[]
for c in cases:
    s=c['closed_summary']
    summary_rows.append([c['label'],s['entries'],s['completed'],s['open_at_cutoff'],f"{s['win_rate_pct']:.1f}%",money(s['closed_net']),money(s['valuation_net']),money(s['total_net']),f"{s['return_pct']:+.4f}%",f"{s['max_floating_dd_pct']:.2f}%"])
sections=[table(['Version','Entries','Completed','Still open','Closed win rate','Closed net $','Open valuation $','Total net $','Return','Max floating DD'],summary_rows)]
for c in cases:
    s=c['closed_summary']
    section=f"<section><h2>{escape(c['label'])}</h2><p>Completed positions: {s['wins']} wins / {s['losses']} losses. Closed-trade PF: undefined (no losses). Native tester PF: {s['native_deal_pf']:.2f}; this deal-based figure includes costs booked on separate deals and is not a net-position PF. Native Sharpe: {s['native_sharpe']:.2f}; this tiny sample is not suitable for judging Sharpe or an edge.</p>"
    section+=table(['#','Side','Lot','Entry EDT','Exit / valuation EDT','Entry price','Exit price','Initial SL','Last SL','Gross $','Commission $','Swap $','Net $','Net R','Held','Status'],[
        [t['number'],t['side'],f"{t['volume']:.2f}",stamp(t['open_time']),stamp(t['close_time']),f"{t['open_price']:.2f}",f"{t['close_price']:.2f}",f"{t['initial_sl']:.2f}",f"{t['final_sl']:.2f}",money(t['gross_profit']),money(t['commission']),money(t['swap']),money(t['net_profit']),f"{t['net_R']:+.3f}R",hold(t['hold_hours']),t['status']] for t in c['trades']])
    section+=f"<p>All-position commission: ${s['commission']:.2f}; swap: ${s['swap']:.2f}. Closed average win: ${s['average_closed_win']:.2f}. Completed winning/losing streak: {s['max_win_streak']} / {s['max_loss_streak']}.</p>"
    for t in c['trades']:
        section+=f"<details><summary>Trade {t['number']} — {t['side']}: ${t['net_profit']:+.2f} — full execution and trailing detail</summary><p>UTC: {escape(t['open_time'])} → {escape(t['close_time'])}. Lagos: {escape(stamp(t['open_time'],'Africa/Lagos'))} → {escape(stamp(t['close_time'],'Africa/Lagos'))}. Favourable signed move: {t['move_points']:+.2f} index points. Initial stop-from-fill cash exposure: ${t['initial_cash_risk']:.2f} ({t['risk_pct_balance']:.3f}% of starting trade balance). Balance before: ${t['balance_before']:.2f}; after native close/valuation: ${t['balance_after']:.2f}. TP: none. Entry comment: {escape(t['entry_comment'])}. Exit comment: {escape(t['exit_comment'])}.</p>"
        if t['boundary_exit']:
            section+='<p class="warn">No natural exit occurred. The tester forcibly liquidated this position at the end of its available window. Its negative valuation is NOT a completed strategy loss, and the exit commission is hypothetical at this cutoff.</p>'
        else:
            section+=f"<p>Signed fill slippage relative to final stop: {t['exit_slippage_points']:+.2f} points. Stop tightened {len(t['sl_modifications'])} times. A trailing activation means price reached +1 initial R before the first tightening; the actual maximum favourable/adverse excursion was not exported and is not invented here.</p>"
        section+=table(['UTC','New York EDT','New SL'],[[v['time'],stamp(v['time']),f"{v['sl']:.2f}"] for v in t['sl_modifications']]) if t['sl_modifications'] else '<p>No successful stop tightening recorded.</p>'
        section+='</details>'
    section+='</section>'; sections.append(section)

daily=[['1 Oct','Short entered; trailing exit +$12.86','Same short, same exit +$12.86'],
       ['2 Oct','No entry: DI gate (paired-run attribution)','Long entered; remained open over the weekend'],
       ['3–4 Oct','No New York opening-session entry','Friday long still open'],
       ['5 Oct','Long entered; trailing exit +$93.80','No new entry: Friday long occupied the one-position slot'],
       ['6 Oct','No 09:35 entry: DI gate (paired-run attribution)','Friday long exited +$94.94; new short remained open at cutoff'],
       ['7 Oct','Not included in native historical test','Not included in native historical test']]
sections.append('<section><h2>Session-by-session explanation</h2>'+table(['NY session date','DI ON','DI OFF'],daily)+'<p>DI gate attribution comes from controlled native runs with a single changed input. Numeric +DI/−DI readings were not exported by the unchanged production binary.</p></section>')

page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Nasdaq M5 — October trade breakdown</title><style>
:root{color-scheme:dark}body{margin:0;background:#081310;color:#e4efea;font:15px/1.6 system-ui,sans-serif}main{max-width:1500px;margin:auto;padding:32px 24px 70px}h1{font-size:clamp(24px,3vw,40px);line-height:1.2}h2{color:#76efd0}p{max-width:1120px;color:#b4c9c1}.warn{background:#342915;color:#ffe4a0;border:1px solid #806935;border-radius:12px;padding:15px}.scroll{overflow-x:auto;border:1px solid #28483d;border-radius:10px;margin:16px 0}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}td,th{padding:12px 15px;text-align:left;white-space:nowrap;border-bottom:1px solid #244038}th{background:#123128;color:#89f0d3}section{margin:32px 0}details{border:1px solid #28483d;border-radius:10px;padding:16px;margin:16px 0}summary{cursor:pointer;color:#90eccc}code{word-break:break-all}footer{border-top:1px solid #28483d;padding-top:20px;font-size:13px;color:#9cb9ad}</style></head><body><main>
<p>RESEARCH ONLY · EXACT PRODUCTION BINARY · EXNESS USTEC CFD</p><h1>Current Nasdaq M5: October trade-by-trade</h1>
<p>Effective test: 1 October 2026 00:00 UTC → 7 October 2026 00:00 UTC exclusive (1–6 October). Requested 8 October end was capped by the native tester at the current day's start. 7 October intraday is not included. All table times use New York EDT (UTC−4); expandable details also show UTC and Lagos (UTC+1).</p>
<p class="warn">Only TWO completed positions in each version. 100% closed win rate here is not evidence of a reliable 100% system. DI OFF has a third position still open at cutoff: native 66.67% counts its forced valuation as a loss; the correct completed-strategy win rate is 100% (2/2). Both meanings are kept separate below.</p>
<p>Each version starts flat with $10,000 and 1% equity target risk. Same EMA12 M5 opening signal, 0.60% price stop, ATR14 ×6 trail after +1R, no fixed target, no session/time exit, one-position limit and 150 ms simulated execution delay. Minimum-lot/round-up policy is unchanged, so selected risk is not a hard cap. Standalone adaptive portfolio controls are off; live BAT portfolio sizing/guards may differ. Broker commissions and swaps are included; spread/slippage are already reflected in bid/ask fills. Both runs: 100% real ticks.</p>
'''+''.join(sections)+f'''<footer>Simulated results, not your actual account journal. No BAT, live chart, production EA, website or GitHub changes. Same binary SHA-256: <code>{a['manifest']['binary_sha256']}</code>. Raw-deal and parameter verification passed; see COMPARISON.json and VERIFICATION.json.</footer></main></body></html>'''
(R/'Results.html').write_text(page,encoding='utf-8')
qa=Rows(); qa.feed(page); assert len(qa.rows)>10 and page.count('<details>')==5
assert page.count('<table>')==page.count('</table>') and page.count('<details>')==page.count('</details>')
save('HTML-QA.json',dict(passed=True,bytes=len(page.encode()),tables=page.count('<table>'),trade_detail_sections=page.count('<details>'),no_external_dependencies=True))
print(json.dumps(dict(comparison=[dict(version=c['label'],**c['closed_summary']) for c in cases],trade_stops=[dict(version=c['label'],number=t['number'],final_sl=t['final_sl'],modifications=len(t['sl_modifications'])) for c in cases for t in c['trades']],html=str(R/'Results.html')),indent=2))
