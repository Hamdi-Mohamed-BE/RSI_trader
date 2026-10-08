"""Three sequential isolated native raw tests; never calls a live trading API."""
from pathlib import Path
import gzip, hashlib, html, importlib.util, json, os, re, shutil, subprocess, sys, time
import numpy as np
import pandas as pd

R=Path(__file__).resolve().parent; B=R.parent
os.environ['EA_STORE_DISABLE_MT5']='1'
spec=importlib.util.spec_from_file_location('golden_native_helper',B/'FTMO Exit Management Research 2026-09-27/run.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
T=h.TESTER
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files'
START='2023-10-06'; END='2026-10-06'
CASES={1:('Vault Break','M30','vault'),2:('VWAP Pullback ADX','M1','vwap'),3:('Overnight Bias ORB','M15','overnight')}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def paths(mode,smoke=False):
    name,tf,slug=CASES[mode]
    return name,tf,slug,R/(name+'.mq5'),R/(name+' 1pct.set'),R/slug/('smoke' if smoke else 'native')
def params(p):return dict(line.strip().split('=',1) for line in p.read_text().splitlines() if '=' in line and not line.startswith(';'))
def fingerprints():
    return {p.name:sha(p) for p in [R/'Golden Trio Engine.mqh',R/'PROTOCOL.txt',R/'run-config.json']+
      [R/(x[0]+ext) for x in CASES.values() for ext in ['.mq5',' 1pct.set']]}
def inputs(report):
    body=h._read_report(report);start=body.lower().find('inputs:');end=body.lower().find('company:',start)
    return dict(html.unescape(x).strip().split('=',1) for x in re.findall(r'<b>([^<]+=[^<]*)</b>',body[start:end],re.I|re.S))
def compile_all():
    h.free();binaries={}
    for mode in CASES:
        name,tf,slug,source,preset,out=paths(mode);log=R/(slug+'-compile.log');began=time.time()
        subprocess.run(f'"{T/"MetaEditor64.exe"}" /portable /compile:"{source}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
        body=h.text(log);assert '0 errors, 0 warnings' in body,body[-3000:]
        binary=source.with_suffix('.ex5');assert binary.stat().st_mtime>=began-2
        dest=T/'MQL5/Experts/AAA Research/Golden Trio 20261006';dest.mkdir(parents=True,exist_ok=True)
        shutil.copy2(binary,dest/binary.name);binaries[name]=sha(binary)
        print(name+': compiled zero errors/warnings',flush=True)
    save(R/'build.json',{'files':fingerprints(),'binaries':binaries})

def run_case(mode,smoke=False):
    name,tf,slug,source,preset,out=paths(mode,smoke);out.mkdir(parents=True,exist_ok=True)
    build=json.loads((R/'build.json').read_text());assert build['files']==fingerprints()
    assert build['binaries'][name]==sha(source.with_suffix('.ex5'))
    empty=T/'MQL5/Profiles/Charts/Calyx Research Empty';assert empty.is_dir() and not list(empty.glob('*.chr'))
    tag='golden-trio-'+slug+'-20261006';setname=tag+'.set';shutil.copy2(preset,T/'MQL5/Profiles/Tester'/setname)
    expected=params(preset);assert float(expected['InpRiskPct'])==1 and len(expected)==14
    # Private account header remains local and is never copied to public artifacts.
    header=h.text(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
    start,end=('2026.09.01','2026.09.08') if smoke else (START.replace('-','.'),END.replace('-','.'))
    case='smoke' if smoke else 'raw';ini=out/'tester.ini';reportdir=T/'reports'/tag;reportdir.mkdir(parents=True,exist_ok=True)
    expert='AAA Research\\Golden Trio 20261006\\'+name
    ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert={expert}
ExpertParameters={setname}
Symbol=USTEC
Period={tf}
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate={start}
ToDate={end}
Report=reports\\{tag}\\{case}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
    h.free();offsets={p:p.stat().st_size for p in h.logfiles()};began=time.time()
    proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW)
    save(out/'owned-process.json',{'pid':proc.pid,'terminal':str(T),'started':began})
    print(f'{name}: isolated native {case} test started, PID {proc.pid}',flush=True)
    while proc.poll() is None and time.time()-began<2400:
        time.sleep(20);print(f'{name}: native tester {int(time.time()-began)}s',flush=True)
    if proc.poll() is None:
        proc.terminate();proc.wait(timeout=30);raise RuntimeError('Owned isolated tester timed out')
    journal=''
    for p in h.logfiles():
        if p.stat().st_mtime<began-2:continue
        with p.open('rb') as f:f.seek(offsets.get(p,0));journal+='\n'+f.read().decode('utf-16-le',errors='replace')
    (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
    report=reportdir/(case+'.htm')
    assert report.exists() and report.stat().st_mtime>=began-2,'No fresh native report'
    actual=inputs(report)
    for k,v in expected.items():assert h._same_setting(v,actual.get(k,'')),k
    body=h._read_report(report);assert start in body and end in body and 'USTEC' in body and tf in body
    flags={k:len(re.findall(v,journal,re.I)) for k,v in {'init_failed':r'initialization failed|INIT_FAILED','critical':r'critical error|access violation','invalid_volume':r'invalid volume','stopout':r'stop out','margin':r'not enough money'}.items()}
    assert not any(flags.values()),flags
    shutil.copy2(report,out/'report.htm')
    for p in reportdir.glob(case+'*.png'):shutil.copy2(p,out/p.name)
    for suffix in ['decisions','equity','bars','sessions']:
        p=COMMON/(tag+'-'+suffix+'.csv');assert p.exists() and p.stat().st_mtime>=began-2;shutil.copy2(p,out/(suffix+'.csv'))
    decisions=pd.read_csv(out/'decisions.csv',encoding='utf-16')
    rejected=decisions[decisions.reason=='entry_failed'];assert rejected.retcode.eq(10016).all(),'Unexplained rejection'
    stamps=set(re.findall(r'(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})\s+failed market[^\r\n]*\[Invalid stops\]',journal,re.I))
    rejected_stamps=set(pd.to_datetime(rejected.epoch,unit='s',utc=True).dt.strftime('%Y.%m.%d %H:%M:%S'))
    assert stamps==rejected_stamps,'Unreconciled native order error'
    trades=h._native_trades(report,name);m=h._native_metrics(report)
    assert len(trades)==m['trades']==len(decisions[decisions.reason=='entry_sent'])
    assert abs(sum(t['net_profit'] for t in trades)-m['net_profit'])<.04
    from app.mt5_evidence_jobs import _metric,_number
    m['equity_drawdown_relative_pct']=_number(_metric(body,'Equity Drawdown Relative'))
    save(out/'trades.json',trades)
    save(out/'status.json',{'ok':True,'from':start,'end_exclusive':end,'native':m,'elapsed_seconds':time.time()-began,'inputs':expected,'flags':flags,
      'report_sha256':sha(report),'build':build,'broker_stop_rejections':len(rejected),
      'real_tick_notes':sorted(set(re.findall(r'USTEC\s*:\s*real ticks begin from[^\r\n]*',journal)))})
    import verify
    verify.verify(mode,smoke)
    if not smoke:analyse(mode)
    print(name+': completed '+json.dumps(m),flush=True)

def stats(trades,start,end,initial=10000):
    vals=[t['net_profit'] for t in trades];wins=[v for v in vals if v>0];losses=[v for v in vals if v<0]
    ws=ls=mw=ml=0;balance=peak=initial;dd=0
    for v in vals:
        ws=ws+1 if v>0 else 0;ls=ls+1 if v<0 else 0;mw=max(mw,ws);ml=max(ml,ls)
        balance+=v;peak=max(peak,balance);dd=max(dd,(peak-balance)/peak*100)
    days=pd.bdate_range(start,pd.Timestamp(end)-pd.Timedelta(days=1));daily=pd.Series(0.,index=days)
    for t in trades:
        date=pd.Timestamp(t['close_time']).normalize()
        if date in daily.index:daily.loc[date]+=t['net_profit']
    previous=(initial+daily.cumsum()).shift(1).fillna(initial);returns=daily/previous
    sd=returns.std(ddof=1);sharpe=float(np.sqrt(252)*returns.mean()/sd) if sd>0 else None
    return {'trades':len(vals),'wins':len(wins),'losses':len(losses),'flat':len(vals)-len(wins)-len(losses),
      'net':sum(vals),'return_pct':sum(vals)/initial*100,'pf':sum(wins)/-sum(losses) if losses else None,
      'win_rate':len(wins)/len(vals)*100 if vals else None,'closed_balance_dd':dd,'daily_balance_sharpe':sharpe,
      'win_streak':mw,'loss_streak':ml,'avg_win':sum(wins)/len(wins) if wins else None,'avg_loss':sum(losses)/len(losses) if losses else None,
      'commission':sum(t['commission'] for t in trades),'swap':sum(t['swap'] for t in trades),
      'trades_per_month':len(vals)/((pd.Timestamp(end)-pd.Timestamp(start)).days/30.4375),'trades_per_weekday':len(vals)/len(days)}

def analyse(mode):
    name,tf,slug,source,preset,out=paths(mode);status=json.loads((out/'status.json').read_text());trades=json.loads((out/'trades.json').read_text())
    eq=pd.read_csv(out/'equity.csv',encoding='utf-16');dec=pd.read_csv(out/'decisions.csv',encoding='utf-16')
    total=stats(trades,START,END);total['equity_dd']=status['native']['equity_drawdown_relative_pct']
    def window(label,start,end):
        selected=[t for t in trades if pd.Timestamp(start)<=pd.Timestamp(t['close_time'])<pd.Timestamp(end)]
        initial=10000+sum(t['net_profit'] for t in trades if pd.Timestamp(t['close_time'])<pd.Timestamp(start))
        m=stats(selected,start,end,initial);a=int(pd.Timestamp(start,tz='UTC').timestamp());b=int(pd.Timestamp(end,tz='UTC').timestamp())
        floating=eq[(eq.epoch>=a)&(eq.epoch<b)].equity
        values=np.r_[initial,floating.to_numpy()];peaks=np.maximum.accumulate(values)
        m['equity_dd']=float(np.max((peaks-values)/peaks*100));m['period']=label;m['from']=start;m['end_exclusive']=end
        return m
    years=[]
    for year in [2023,2024,2025,2026]:
        start=max(START,f'{year}-01-01');end=min(END,f'{year+1}-01-01');years.append(window(str(year),start,end))
    recent=[window(label,start,END) for label,start in [('Last year','2025-10-06'),('Last 6 months','2026-04-06'),('Last 3 months','2026-07-06'),('2026 real-tick slice','2026-01-01')]]
    result={'name':name,'mode':mode,'timeframe':tf,'from':START,'through':'2026-10-05','summary':total,'years':years,'recent':recent,
      'native':status['native'],'real_tick_notes':status['real_tick_notes'],'decisions':{str(k):int(v) for k,v in dec.reason.value_counts().items()},
      'verification':json.loads((out.parent/'verification.json').read_text()),'broker_stop_rejections':status['broker_stop_rejections']}
    save(out.parent/'results.json',result);pd.DataFrame(trades).to_csv(out.parent/'Trades.csv',index=False)
    months=pd.period_range(START,pd.Timestamp(END)-pd.Timedelta(days=1),freq='M')
    monthly=[]
    for month in months:
        start=max(START,str(month.start_time.date()));end=min(END,str((month.end_time.normalize()+pd.Timedelta(days=1)).date()))
        monthly.append(window(str(month),start,end))
    pd.DataFrame(monthly).to_csv(out.parent/'Monthly.csv',index=False)
    build_report(result,trades);index_report()
    print('NET RESULT '+name+': '+json.dumps(total),flush=True)

def fmt(v):return '—' if v is None else f'{v:.2f}'
def table_row(label,m):
    keys=['trades','trades_per_month','trades_per_weekday','return_pct','pf','win_rate','equity_dd','daily_balance_sharpe','win_streak','loss_streak']
    return '<tr><td>'+html.escape(label)+'</td>'+''.join('<td>'+(str(m[k]) if k in ['trades','win_streak','loss_streak'] else fmt(m[k]))+'</td>' for k in keys)+'</tr>'
HEADER='<tr><th>Period / strategy</th><th>Trades</th><th>/ month</th><th>/ weekday</th><th>Return %</th><th>Net PF</th><th>Win %</th><th>Equity DD %</th><th>Daily Sharpe</th><th>Win run</th><th>Loss run</th></tr>'
STYLE='body{background:#08150f;color:#effff5;font:16px system-ui;max-width:1400px;margin:30px auto;padding:20px}p,li{line-height:1.6}a{color:#70efb7}.notice{border:1px solid #a88535;padding:18px;border-radius:12px;background:#252416}.muted{color:#a9c2b4}.scroll{overflow:auto}table{width:100%;border-collapse:collapse;margin:24px 0;font-variant-numeric:tabular-nums}th,td{padding:12px;border-bottom:1px solid #2b4b37;text-align:right}th:first-child,td:first-child{text-align:left}svg{width:100%;height:320px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(350px,1fr));gap:20px}.panel{border:1px solid #2b4b37;border-radius:14px;padding:18px}pre{white-space:pre-wrap}'
def chart(trades):
    bal=10000;points=[(pd.Timestamp(START,tz='UTC').timestamp(),bal)]
    for t in trades:bal+=t['net_profit'];points.append((pd.Timestamp(t['close_time'],tz='UTC').timestamp(),bal))
    lo=min(p[1] for p in points);hi=max(p[1] for p in points);start=points[0][0];end=pd.Timestamp(END,tz='UTC').timestamp()
    mapped=' '.join(f'{90+970*(t-start)/(end-start):.2f},{260-220*(v-lo)/(hi-lo or 1):.2f}' for t,v in points)
    return f'<svg viewBox="0 0 1100 320" role="img" aria-label="Closed trade balance"><polyline fill="none" stroke="#70efb7" stroke-width="2" points="{mapped}"/><text x="0" y="35" fill="#a9c2b4">${hi:,.0f}</text><text x="0" y="265" fill="#a9c2b4">${lo:,.0f}</text><text x="90" y="300" fill="#a9c2b4">Oct 2023</text><text x="940" y="300" fill="#a9c2b4">Oct 2026</text></svg>'
def build_report(r,trades):
    mode=r['mode'];name,tf,slug,source,preset,out=paths(mode);m=r['summary'];audit=r['verification']
    source_time={1:506,2:1354,3:2150}[mode]
    carries=audit.get('overnight_carries',[])
    rules={
      1:'Long only. M30 close above midnight price +0.30×SMA15(session ATR) and above midnight VWAP. Enter at next-bar quote 10:00–14:30 Chicago, up to 3 trades/day. Stop 75 Nasdaq points, target 40 points; flatten 14:30. Underlying Wilder ATR14 and HLC3 tick-volume VWAP are ours.',
      2:'Long only. M1 close above 08:30–09:00 Chicago range high arms; wick touch and reclaim of VWAP; ADX>20 flat/decreasing, possibly on a later bar. Next-bar entry. Stop last 20 lows, target last 5 highs, including signal. Flatten 15:55. OUR defaults: Wilder ADX14, midnight HLC3 tick-volume VWAP, 1 trade/day, eligibility begins with the 09:59 candle closing at 10:00 and ends 14:30; stage state persists until fill/day reset.',
      3:'Prior 23:00–08:30 Chicago overnight range; 08:30 open in upper/lower third freezes long/short bias; middle third skips. First 08:30–08:45 M15 candle is OR. Later close beyond that side of OR with ADX>20; next-bar entry. Stop 0.30×SMA15(session ATR), target 3R, 1 trade/day, flatten 14:30. Wilder ATR14/ADX14 and inclusive third boundaries are ours.'
    }[mode]
    page=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{name} — raw 3 years</title><style>{STYLE}</style></head><body>
<p class="muted">CALYX · GOLDEN TRIO · RAW RECONSTRUCTION · NO LIVE CHANGES</p><h1>{name} — US100 {tf}</h1><p>6 October 2023–5 October 2026 · Exness USTEC · $10,000 initial deposit · 1% current equity planned risk</p>
<div class="notice">Independently written CFD reconstruction, NOT the speaker's original code. Unspecified settings are frozen as OUR defaults in the protocol. Different futures volume, contract sizing and indicators can change the outcome. No optimisation, control-based validation, untouched holdout or prop-pass claim.</div>
<h2>Frozen entry and exit rules</h2><p>{html.escape(rules)}</p>
<h2>Full 3-year result</h2><div class="scroll"><table><thead>{HEADER}</thead><tbody>{table_row('Full 3 years',m)}</tbody></table></div>
<h2>Closed-trade balance</h2>{chart(trades)}<p class="muted">Graph is closed balance, not floating equity. Headline DD comes from native tick-level MT5 equity.</p>
<h2>Calendar years</h2><div class="scroll"><table><thead>{HEADER}</thead><tbody>{''.join(table_row(y['from']+' to '+str((pd.Timestamp(y['end_exclusive'])-pd.Timedelta(days=1)).date()),y) for y in r['years'])}</tbody></table></div>
<h2>Recent diagnostic slices</h2><div class="scroll"><table><thead>{HEADER}</thead><tbody>{''.join(table_row(y['period']+' · '+y['from'],y) for y in r['recent'])}</tbody></table></div>
<p class="muted">Calendar/recent returns use each slice's starting closed balance on the same continuing compounded account. Slice DD is minute-sampled floating equity; full-period DD is native tick-level. Net PF/WR include complete position costs. Sharpe = weekday daily closed-balance returns including zero-trade weekdays, annualised sqrt(252), zero risk-free rate. Weekdays include exchange holidays.</p>
<h2>Risk and execution verification</h2><p>{audit['entries_verified']} entries audited: causal closed-bar signals, Chicago DST, frozen range/VWAP/ATR rules, ADX values, lot steps and native cash flow. Largest planned stop risk {audit['planned_risk_percent_max']:.4f}% of entry equity; largest realised net loss {audit['realised_net_loss_percent_max']:.2f}%. {r['broker_stop_rejections']} broker rejections were not forced. Historical risk is not a future loss cap.</p>
<p>Average net win ${fmt(m['avg_win'])}; average net loss ${fmt(m['avg_loss'])}; commission ${fmt(m['commission'])}; swap ${fmt(m['swap'])}. Native report PF {r['native']['profit_factor']:.2f}/WR {r['native']['win_rate_pct']:.2f}% may differ from complete-position net figures.</p>
<div class="notice">Scheduled time exits require an available quote and an open market. There were {len(carries)} positions carried across Chicago calendar dates; early closures or historical quote gaps can prevent the scheduled flatten and introduce gap loss/swap. No holiday-specific or missing-quote exit rule was added. Largest realised net loss: {audit['realised_net_loss_percent_max']:.2f}% of entry equity.</div><details><summary>Cross-date positions</summary><pre>{html.escape(json.dumps(carries,indent=2))}</pre></details>
<h2>Tick coverage</h2><p>Native Model 4, 150ms delay; reported history quality {html.escape(r['native']['history_quality'])}.</p><pre>{html.escape(chr(10).join(r['real_tick_notes']))}</pre><p>Older missing real ticks are modelled by MT5. This is especially important for the narrow M1 pullback target. Results are historical and provisional, not expected returns.</p>
<details><summary>Signal/skip counts</summary><pre>{html.escape(json.dumps(r['decisions'],indent=2))}</pre></details>
<p><a href="../Results.html">All three strategies</a> · <a href="Trades.csv">Trade-by-trade CSV</a> · <a href="Monthly.csv">All months</a> · <a href="native/report.htm">Native report</a> · <a href="../{name}.mq5">Research source</a> · <a href="../{name}%201pct.set">1% preset</a> · <a href="../Golden%20Trio%20Engine.mqh">Shared engine</a> · <a href="../PROTOCOL.txt">Rules and assumptions</a> · <a href="verification.json">Independent audit</a> · <a href="https://www.youtube.com/watch?v=A0G14JYYVTk&t={source_time}s">Original interview chapter</a></p></body></html>'''
    (out.parent/'Results.html').write_text(page,encoding='utf-8')
def index_report():
    completed=[]
    for mode,(name,tf,slug) in CASES.items():
        p=R/slug/'results.json'
        evidence=R/slug/'native/status.json'
        if p.exists() and evidence.exists():
            status=json.loads(evidence.read_text())
            # Never show superseded audit-pass metrics while corrected runs are pending.
            if status['build']==json.loads((R/'build.json').read_text()):completed.append(json.loads(p.read_text()))
    rows=''.join(table_row(r['name'],r['summary']) for r in completed)
    panels=''
    for r in completed:
        slug=CASES[r['mode']][2];trades=json.loads((R/slug/'native/trades.json').read_text())
        panels+=f'<section class="panel"><h2>{r["name"]}</h2>{chart(trades)}<p><a href="{slug}/Results.html">Full results, years, recent slices and every trade</a></p></section>'
    page=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Golden Trio — raw results</title><style>{STYLE}</style></head><body><p class="muted">CALYX · RESEARCH ONLY</p><h1>Golden Trio — three separate US100 raw tests</h1><p>6 Oct 2023–5 Oct 2026 · $10,000 starting capital per independent test · 1% equity risk per trade</p><div class="notice">{len(completed)} of 3 strategies completed. CFD reconstructions with explicitly labelled assumptions, not original code. No live bots, BATs or website changed. No optimisation or shared-portfolio results. Native real-tick coverage is incomplete before 2026; see individual reports.</div><div class="scroll"><table><thead>{HEADER}</thead><tbody>{rows}</tbody></table></div><div class="grid">{panels}</div><p><a href="PROTOCOL.txt">Frozen complete rules/assumptions</a> · <a href="run-config.json">Frozen study settings</a> · <a href="https://www.youtube.com/watch?v=A0G14JYYVTk">Primary source interview</a></p></body></html>'''
    (R/'Results.html').write_text(page,encoding='utf-8');save(R/'results.json',completed)

if __name__=='__main__':
    command=sys.argv[1] if len(sys.argv)>1 else 'compile'
    modes=[int(sys.argv[2])] if len(sys.argv)>2 else list(CASES)
    if command=='analyse':
        for mode in modes:analyse(mode)
    else:
        import msvcrt
        with (B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
            lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
            if command=='compile':compile_all()
            elif command in ['run','smoke']:
                for mode in modes:run_case(mode,command=='smoke')
            else:raise ValueError(command)
