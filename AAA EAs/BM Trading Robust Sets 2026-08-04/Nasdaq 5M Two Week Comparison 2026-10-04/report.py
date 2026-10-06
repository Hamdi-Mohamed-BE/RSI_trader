"""Reconcile completed reports and render an offline comparison; no MT5 execution."""
from pathlib import Path
import base64,csv,gzip,hashlib,html,json,re
from datetime import datetime

R=Path(__file__).resolve().parent
def clean(s):return html.unescape(re.sub('<[^>]+>','',s)).strip()
def money(v):return f'{v:+,.2f}'
def write_json(p,data):p.write_text(json.dumps(data,indent=2,allow_nan=False),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def streaks(trades):
    w=l=mw=ml=0
    for t in sorted(trades,key=lambda t:t['close_time']):
        if t['net_profit']>0:w+=1;l=0
        elif t['net_profit']<0:l+=1;w=0
        else:w=l=0
        mw=max(mw,w);ml=max(ml,l)
    return mw,ml
def pf(r):return 'N/A — no net losing trades' if r['net_pf'] is None else f"{r['net_pf']:.2f}"
LABELS={'CURRENT':'Current · DI ON','CURRENT_NO_DI':'Current · DI OFF','OLD':'Previous · DI ON'}
def cells(values):return '<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in values)+'</tr>'
def table(head,body):return '<div class="scroll"><table><thead>'+cells(head)+'</thead><tbody>'+body+'</tbody></table></div>'
def native_image(name):
    p=R/'native'/name/(name+'.png')
    return '<img alt="Native MT5 balance graph" src="data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode()+'">'

rows=json.loads((R/'RESULTS.json').read_text(encoding='utf-8'))
by_name={r['manifest']['version']:r for r in rows}
assert set(by_name)=={'CURRENT','OLD','CURRENT_NO_DI'},'Wait for all three completed native runs'
cur,old,no_di=[by_name[k] for k in ['CURRENT','OLD','CURRENT_NO_DI']]
rows=[cur,no_di,old]
input_differences={k:(cur['manifest']['inputs'].get(k),no_di['manifest']['inputs'].get(k)) for k in set(cur['manifest']['inputs'])|set(no_di['manifest']['inputs']) if cur['manifest']['inputs'].get(k)!=no_di['manifest']['inputs'].get(k)}
assert input_differences=={'InpRequireDIAgreement':('true','false')}
assert cur['manifest']['binary_sha256']==no_di['manifest']['binary_sha256']
for k in ['start','end_exclusive','deposit','risk_percent','model','delay_ms','symbol','timeframe','broker','set_sha256']:
    assert cur['manifest'][k]==no_di['manifest'][k],k
checks=[]
for r in rows:
    name=r['manifest']['version'];folder=R/'native'/name
    raw=gzip.decompress((folder/'report.htm.gz').read_bytes())
    assert hashlib.sha256(raw).hexdigest()==r['report_sha256']
    text=raw.decode('utf-16')
    chunk=text[text.lower().index('<b>orders</b>'):text.lower().index('<b>deals</b>')]
    orders=[]
    for body in re.findall(r'<tr\b[^>]*>(.*?)</tr>',chunk,re.S|re.I):
        c=[clean(x) for x in re.findall(r'<td\b[^>]*>(.*?)</td>',body,re.S|re.I)]
        if len(c)>=11 and re.fullmatch(r'\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}',c[0]):orders.append(c)
    assert len(orders)==2*len(r['trades'])
    r['orders']=orders
    prior=None
    for t in r['trades']:
        key=t['open_time'].replace('-','.').replace('T',' ')
        match=[o for o in orders if o[0]==key and o[10]==t['entry_comment']]
        assert len(match)==1
        t['initial_sl']=float(match[0][6].replace(' ',''))
        t['initial_tp']=float(match[0][7].replace(' ','')) if match[0][7] else None
        assert t['initial_sl']<t['open_price'] if t['side']=='Long' else t['initial_sl']>t['open_price']
        if name.startswith('CURRENT'):
            assert t['initial_tp'] is None
            if t['exit_comment'].startswith('sl '):
                exit_sl=float(t['exit_comment'].split()[1])
                profitable=exit_sl>t['open_price'] if t['side']=='Long' else exit_sl<t['open_price']
                t['exit_reason']='ATR trailing stop (in profit)' if profitable else 'Protective stop'
        assert prior is None or prior<=t['open_time']
        prior=t['close_time']
        assert abs(t['gross_profit']+t['commission']+t['swap']-t['net_profit'])<.015
    assert len(set(t['open_ny'][:10] for t in r['trades']))==len(r['trades'])
    assert r['native']['history_quality']=='100% real ticks'
    if name!='CURRENT_NO_DI':assert r['end_liquidations']==0
    assert abs(sum(t['net_profit'] for t in r['trades'])-r['native']['net_profit'])<.015
    assert sha(Path(r['manifest']['expert_source']))==r['manifest']['binary_sha256']
    assert sha(Path(r['manifest']['settings_source']))==r['manifest']['set_sha256']
    write_json(folder/'results.json',r);write_json(folder/'orders.json',orders);write_json(folder/'trades.json',r['trades'])
    with (folder/'trades.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(r['trades'][0]));w.writeheader();w.writerows(r['trades'])
    checks.append({'version':name,'positions':len(r['trades']),'end_liquidations':r['end_liquidations'],'checks':'passed: exact source hashes, report hash, net reconciliation, entries, stops, no overlap, labelled boundary exits, real-tick quality'})
checks.append({'filter_ablation':'same current binary and source preset; only InpRequireDIAgreement differs','input_differences':input_differences})
write_json(R/'RESULTS.json',rows);write_json(R/'verification.json',checks)
assert [(t['open_time'],t['side'],t['open_price']) for t in cur['trades']]==[(t['open_time'],t['side'],t['open_price']) for t in old['trades']]
summary=[]
for r in rows:
    n=r['native'];mw,ml=streaks(r['trades'])
    summary.append([LABELS[r['manifest']['version']],money(n['net_profit']),f"{100*n['net_profit']/10000:.2f}%",r['positions'],f"{r['net_win_rate_pct']:.1f}%",pf(r),f"{n['equity_dd_pct']:.2f}%",n['sharpe_ratio'],f'{mw} / {ml}',money(r['commission']+r['swap'])])
paired=''.join(cells([a['open_ny'][:10],a['side'],a['close_ny'],money(a['net_profit']),b['close_ny'],money(b['net_profit']),money(a['net_profit']-b['net_profit'])]) for a,b in zip(cur['trades'],old['trades']))
entries={r['manifest']['version']:{t['open_time']:t for t in r['trades']} for r in rows}
all_entries=sorted(set().union(*(set(v) for v in entries.values())))
ablation=''
for entry in all_entries:
    ts=[entries[r['manifest']['version']].get(entry) for r in rows]
    first=next(t for t in ts if t)
    values=[first['open_ny'],first['side']]
    for t in ts:values.extend([t['close_ny'],money(t['net_profit'])] if t else ['No entry','—'])
    ablation+=cells(values)
sections=[]
for r in rows:
    name=r['manifest']['version'];body=''
    for t in r['trades']:
        body+=cells([t['number'],t['side'],t['open_ny'],t['close_ny'],t['volume'],f"{t['open_price']:,.2f}",f"{t['close_price']:,.2f}",f"{t['initial_sl']:,.2f}",'None' if t['initial_tp'] is None else f"{t['initial_tp']:,.2f}",money(t['gross_profit']),money(t['commission']),money(t['swap']),money(t['net_profit']),t['hold_hours'],t['exit_reason']])
    settings=('DI14 ON' if name=='CURRENT' else 'DI OFF')+' • 0.60% price stop • ATR14 × 6 trailing from +1 initial R • no TP • overnight/weekend holding' if name.startswith('CURRENT') else 'DI14 • 4 × ATR14 initial stop • fixed 2.5R TP • 15:55 New York session close • no ATR trailing'
    sections.append(f'<section><p class="tag">{name}</p><h2>{settings}</h2><p>Native MT5 balance graph; the horizontal scale is the tester’s transaction index, not elapsed days. This image is not a floating-equity curve. Maximum equity drawdown above comes from the native report. Tables below use New York time.</p>{native_image(name)}'+table(['#','Side','Entry NY','Exit NY','Lots','Entry price','Exit price','Initial SL','Initial TP','Gross $','Commission $','Swap $','Net $','Hours held','Exit'],body)+f'<p><a href="native/{name}/trades.csv">Trade CSV with New York and UTC times</a></p></section>')
delta=cur['native']['net_profit']-old['native']['net_profit']
filter_delta=no_di['native']['net_profit']-cur['native']['net_profit']
natural=[t for t in no_di['trades'] if not t['boundary_exit']]
natural_net=sum(t['net_profit'] for t in natural)
natural_wins=sum(t['net_profit']>0 for t in natural)
boundary_net=sum(t['net_profit'] for t in no_di['trades'] if t['boundary_exit'])
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Nasdaq 5M · Two-week comparison</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#071310;color:#ecf8f1;font:15px/1.6 system-ui,sans-serif}main{max-width:1460px;margin:auto;padding:40px 24px}h1{font-size:clamp(30px,5vw,56px);line-height:1.1;max-width:900px}h2{font-size:22px}p{color:#b3ccc1}.tag{color:#77ffd0;letter-spacing:.14em;font-size:12px}section{border:1px solid #25463a;background:#0b1b16;border-radius:16px;padding:24px;margin:24px 0}.notice{padding:16px;border:1px solid #927a37;border-radius:12px;background:#25291a;color:#ffe7a4}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;white-space:nowrap;font-size:13px}td{padding:12px;border-bottom:1px solid #234134;text-align:right}td:first-child{text-align:left}thead{color:#89e8c1;background:#10271e}img{display:block;max-width:100%;height:auto;background:white;margin:16px 0;border-radius:8px}a{color:#80ffd0}li{margin:8px 0}code{overflow-wrap:anywhere}.muted{color:#9bb4a7}
</style><main><p class="tag">CALYX · NATIVE MT5 · CURRENT DI-ON / CURRENT DI-OFF / PREVIOUS</p><h1>Nasdaq 5M.<br>Does DI help?</h1>
<p>20 September–3 October 2026 inclusive · USTEC M5 · $10,000 starting balance per version · selected 1% equity risk · fresh, flat starting state.</p>
<div class="notice">Only two weeks of trades. This is a recent retrospective snapshot—not independent validation or an expected future win rate. The current configuration was selected on 28 September; the earlier part of this window is retrospective, not out-of-sample. DI-off is a single-input experiment, not a live configuration change.</div>
'''
page+=f'<section><h2>Three-way results</h2><p>Current DI-on versus old: ${delta:+.2f}. Current DI-off versus current DI-on: ${filter_delta:+.2f}. Both current variants use exactly the same compiled binary; only DI agreement changes.</p>'+table(['Version','Net $','Return','Trades','Net win rate','Net-position PF','Max equity DD','MT5 Sharpe','Max W/L streak','Costs $'],''.join(cells(x) for x in summary))+'<p>Net-position PF includes commission and swap per complete trade. A version with no net losing trade has no finite PF estimate. Native MT5 PF values can differ because costs/deals are grouped differently. Native Sharpe values are reproduced unchanged and are unstable over such a short sample.</p></section>'
page+=f'<section class="notice"><h2>DI-off boundary position</h2><p>The main results include {no_di["end_liquidations"]} test-end liquidation, net ${boundary_net:+.2f}. This is a valuation/forced close at the end of the research window, not a normal strategy signal. Before that forced close, {len(natural)} naturally exited trades totalled ${natural_net:+.2f}, with {natural_wins} wins / {len(natural)-natural_wins} losses ({100*natural_wins/len(natural):.1f}% win rate). Ignoring the open position would overstate the window-end result; we retain its loss in the headline comparison.</p></section>'
page+='<section><h2>All entry dates, including DI-off</h2><p>New York timestamps. A missing entry can reflect DI filtering or an existing carried position; removing DI changes subsequent trade availability and compounding, not just the added trades.</p>'+table(['Entry NY','Side','DI-on exit NY','DI-on net $','DI-off exit NY','DI-off net $','Old exit NY','Old net $'],ablation)+'</section>'
page+='<section><h2>Matched entry breakdown</h2><p>All entries were at 09:35 New York time (13:35 UTC). Every old-version exit was the scheduled 15:55 session close. All current-version exits were ATR trailing stops in profit.</p>'+table(['Entry date','Side','Current exit NY','Current net $','Old exit NY','Old net $','Difference $'],paired)+'</section>'
page+=''.join(sections)
page+='''<section><h2>What was—and was not—tested</h2><ul>
<li>Exact production binaries, verified by SHA-256; no optimization or recompilation. Current DI-off changes only InpRequireDIAgreement=false versus current DI-on. Both original results are preserved.</li>
<li>Exness-MT5Trial16 isolated research terminal, recorded bid/ask, 100% real ticks, 150 ms execution delay, recorded commission and swaps, USD 1:2000 tester leverage.</li>
<li>All three versions use the completed 09:30–09:35 NY M5 candle versus EMA12. Current and old require DI14 direction agreement; current DI-off does not. No additional bullish/bearish candle-body filter or ADX threshold.</li>
<li>The current version uses a wider percentage-based stop; the old uses an ATR stop. Equal percentage risk therefore does not imply equal lots. Production upward/minimum-lot rounding is retained, so actual planned stop risk can exceed the selected 1% slightly; gaps can exceed it further.</li>
<li>No adaptive portfolio sizing, Nasdaq 0.25× multiplier, FTMO guards, other EAs, manual closures or inherited positions. This is not a reconstruction of your live account’s P&amp;L.</li>
<li>Boundary liquidations, if present, are labelled in the detailed trade tables. Net results and position counts reconcile against each native report.</li>
<li>Live terminals, website, BAT launchers and trading configurations were left untouched.</li>
</ul><p><a href="RESULTS.json">Full measured data and source hashes</a> · <a href="verification.json">Verification checks</a> · <a href="PROTOCOL.txt">Original frozen protocol</a> · <a href="NO_DI_PROTOCOL.txt">DI-off addendum</a></p></section></main></html>'''
(R/'Results.html').write_text(page,encoding='utf-8')
print(json.dumps({'report':str(R/'Results.html'),'checks':checks,'difference_usd':round(delta,2),'di_off_minus_di_on_usd':round(filter_delta,2),'summary':summary},indent=2))
