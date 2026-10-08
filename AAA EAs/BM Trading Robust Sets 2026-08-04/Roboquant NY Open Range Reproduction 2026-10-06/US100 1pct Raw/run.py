"""One frozen native USTEC research test; no live API and no optimisation."""
from pathlib import Path
from datetime import datetime, timezone
import gzip, hashlib, html, importlib.util, json, math, os, re, shutil, subprocess, sys, time
import numpy as np
import pandas as pd

R=Path(__file__).resolve().parent
B=R.parent.parent
os.environ['EA_STORE_DISABLE_MT5']='1'
spec=importlib.util.spec_from_file_location('ny_orb_helper',B/'FTMO Exit Management Research 2026-09-27/run.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
T=h.TESTER
SOURCE=R/'NY Open Range US100.mq5'
SET=R/'NY Open Range US100 1pct.set'
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files'
TAG='rq-ny-orb-1pct-20261006'
EXPERT='AAA Research/Roboquant NY ORB 20261006/NY Open Range US100'
START='2023-10-06';END='2026-10-06'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,obj):path.write_text(json.dumps(obj,indent=2,allow_nan=False),encoding='utf-8')
def parameters():
    return {line.split('=',1)[0]:line.split('=',1)[1].split('||')[0] for line in SET.read_text().splitlines() if '=' in line and not line.lstrip().startswith(';')}

def report_inputs(report):
    body=h._read_report(report);marker=body.lower().find('inputs:');end=body.lower().find('company:',marker)
    section=body[marker:end if end>marker else len(body)]
    values={}
    for raw in re.findall(r'<b>([^<]+=[^<]*)</b>',section,re.I|re.S):
        clean=html.unescape(raw).strip();name,value=clean.split('=',1);values[name.strip()]=value.strip()
    return values

def compile_ea():
    h.free();log=R/'compile.log';began=time.time()
    subprocess.run(f'"{T/"MetaEditor64.exe"}" /portable /compile:"{SOURCE}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
    body=h.text(log)
    assert '0 errors, 0 warnings' in body,body[-2500:]
    assert SOURCE.with_suffix('.ex5').stat().st_mtime>=began-2
    target=T/'MQL5/Experts'/Path(EXPERT).parent;target.mkdir(parents=True,exist_ok=True)
    shutil.copy2(SOURCE.with_suffix('.ex5'),target/SOURCE.with_suffix('.ex5').name)
    save(R/'build.json',{'source':sha(SOURCE),'binary':sha(SOURCE.with_suffix('.ex5')),'protocol':sha(R/'PROTOCOL.txt'),'preset':sha(SET),'compiler':body[-400:]})
    print('Compiled: zero errors and warnings',flush=True)

def run_case(smoke=False):
    out=R/('smoke' if smoke else 'native');out.mkdir(exist_ok=True)
    build=json.loads((R/'build.json').read_text())
    assert build['source']==sha(SOURCE) and build['binary']==sha(SOURCE.with_suffix('.ex5'))
    assert build['protocol']==sha(R/'PROTOCOL.txt') and build['preset']==sha(SET)
    empty=T/'MQL5/Profiles/Charts/Calyx Research Empty'
    assert empty.is_dir() and not list(empty.glob('*.chr'))
    setname=TAG+'.set';shutil.copy2(SET,T/'MQL5/Profiles/Tester'/setname)
    inputs=parameters();assert len(inputs)==20 and inputs['risk_mode']=='0' and float(inputs['risk_pct'])==1
    # This existing private isolated account header is never printed or embedded in public results.
    header=h.text(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
    start,end=('2026.09.01','2026.09.08') if smoke else (START.replace('-','.'),END.replace('-','.'))
    case='smoke' if smoke else 'raw'
    ini=out/'tester.ini'
    ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert={EXPERT.replace('/',chr(92))}
ExpertParameters={setname}
Symbol=USTEC
Period=M15
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate={start}
ToDate={end}
Report=reports\\{TAG}\\{case}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
    reportdir=T/'reports'/TAG;reportdir.mkdir(parents=True,exist_ok=True)
    h.free();offsets={p:p.stat().st_size for p in h.logfiles()};began=time.time()
    proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW)
    save(out/'owned-process.json',{'pid':proc.pid,'terminal':str(T),'started':began})
    print(f'Native {case} run started in isolated tester, PID {proc.pid}',flush=True)
    deadline=began+2400
    while proc.poll() is None and time.time()<deadline:
        time.sleep(20);print(f'Native {case} tester running: {int(time.time()-began)} seconds',flush=True)
    if proc.poll() is None:
        proc.terminate();proc.wait(timeout=30)
        save(out/'status.json',{'ok':False,'reason':'Owned isolated tester timed out'})
        raise RuntimeError('Owned isolated tester timed out')
    journal=''
    for path in h.logfiles():
        if path.stat().st_mtime<began-2:continue
        with path.open('rb') as f:
            f.seek(offsets.get(path,0));journal+='\n'+str(path.relative_to(T))+'\n'+f.read().decode('utf-16-le',errors='replace')
    (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
    report=reportdir/(case+'.htm')
    if not report.exists() or report.stat().st_mtime<began-2:
        flags={k:len(re.findall(v,journal,re.I)) for k,v in {'authorization':r'authorization.*failed|authentication.*failed','connection':r'connect.*failed|no connection','history':r'no history|history not found'}.items()}
        save(out/'status.json',{'ok':False,'reason':'No fresh report','exit_code':proc.returncode,'flags':flags})
        raise RuntimeError('No fresh native report; redacted categories: '+json.dumps(flags))
    collect(smoke,report,journal,began,start,end,build,inputs)

def collect(smoke,report,journal,began,start,end,build,inputs):
    out=R/('smoke' if smoke else 'native');reportdir=report.parent;case='smoke' if smoke else 'raw'
    assert report.exists() and report.stat().st_mtime>=began-2
    actual=report_inputs(report)
    for k,v in inputs.items():assert h._same_setting(v,actual.get(k,'')),k
    body=h._read_report(report);assert start in body and end in body and 'USTEC' in body
    flags={k:len(re.findall(v,journal,re.I)) for k,v in {'init_failed':r'initialization failed|INIT_FAILED','critical':r'critical error|access violation','invalid_stops':r'invalid stops','invalid_volume':r'invalid volume','stopout':r'stop out'}.items()}
    assert not any(v for k,v in flags.items() if k!='invalid_stops'),flags
    shutil.copy2(report,out/'report.htm')
    for path in reportdir.glob(case+'*.png'):shutil.copy2(path,out/path.name)
    for suffix in ['decisions','equity','bars']:
        path=COMMON/f'{TAG}-{suffix}.csv';assert path.exists() and path.stat().st_mtime>=began-2
        shutil.copy2(path,out/(suffix+'.csv'))
    decisions=pd.read_csv(out/'decisions.csv',encoding='utf-16')
    rejected=decisions[decisions.reason=='entry_failed']
    assert rejected.retcode.eq(10016).all(), 'Unexplained order rejection'
    # MT5 writes each rejection to agent and terminal logs, often twice per log.
    # Reconcile unique timestamps, not duplicated log-line counts, to the EA trace.
    stamps=set(re.findall(r'(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})\s+failed market[^\r\n]*\[Invalid stops\]',journal,re.I))
    rejected_stamps=set(pd.to_datetime(rejected.epoch,unit='s',utc=True).dt.strftime('%Y.%m.%d %H:%M:%S'))
    assert stamps==rejected_stamps, (stamps,rejected_stamps)
    trades=h._native_trades(report,'NY Open Range US100 1pct');m=h._native_metrics(report)
    assert len(trades)==m['trades']
    assert abs(sum(t['net_profit'] for t in trades)-m['net_profit'])<0.03
    save(out/'trades.json',trades)
    save(out/'status.json',{'ok':True,'from':start,'end_exclusive':end,'elapsed_seconds':time.time()-began,'native':m,'flags':flags,'inputs':inputs,
       'real_tick_notes':sorted(set(re.findall(r'[^\r\n]*real ticks begin from[^\r\n]*',journal))),
       'build':build,'report_sha256':sha(report),'broker_stop_rejections':len(rejected)})
    print('Native run completed: '+json.dumps(m),flush=True)
    if not smoke:analyse()

def stats(trades,start,end,initial=10000):
    vals=[x['net_profit'] for x in trades];wins=[v for v in vals if v>0];losses=[v for v in vals if v<0]
    ws=ls=mw=ml=0;balance=peak=initial;dd=0
    for v in vals:
        ws=ws+1 if v>0 else 0;ls=ls+1 if v<0 else 0;mw=max(mw,ws);ml=max(ml,ls)
        balance+=v;peak=max(peak,balance);dd=max(dd,(peak-balance)/peak*100)
    days=pd.bdate_range(start,pd.Timestamp(end)-pd.Timedelta(days=1));daily=pd.Series(0.0,index=days)
    for t in trades:
        dt=pd.Timestamp(t['close_time']).normalize()
        if dt in daily.index:daily.loc[dt]+=t['net_profit']
    balances=initial+daily.cumsum();previous=balances.shift(1).fillna(initial);ret=daily/previous
    sd=ret.std(ddof=1);sharpe=float(np.sqrt(252)*ret.mean()/sd) if sd>0 else None
    return {'trades':len(vals),'wins':len(wins),'losses':len(losses),'flat':len(vals)-len(wins)-len(losses),
      'win_rate':100*len(wins)/len(vals) if vals else None,'pf':sum(wins)/-sum(losses) if losses else None,
      'net':sum(vals),'return_pct':100*sum(vals)/initial,'closed_balance_dd':dd,'daily_balance_sharpe':sharpe,
      'win_streak':mw,'loss_streak':ml,'avg_win':sum(wins)/len(wins) if wins else None,'avg_loss':sum(losses)/len(losses) if losses else None,
      'best_trade':max(vals) if vals else None,'worst_trade':min(vals) if vals else None,
      'commission':sum(t['commission'] for t in trades),'swap':sum(t['swap'] for t in trades),
      'trades_per_month':len(vals)/((pd.Timestamp(end)-pd.Timestamp(start)).days/30.4375)}

def analyse():
    out=R/'native';status=json.loads((out/'status.json').read_text());assert status['ok']
    trades=json.loads((out/'trades.json').read_text());total=stats(trades,START,END)
    from app.mt5_evidence_jobs import _metric, _number
    native_body=h._read_report(out/'report.htm')
    status['native']['equity_drawdown_relative_pct']=_number(_metric(native_body,'Equity Drawdown Relative'))
    equity=pd.read_csv(out/'equity.csv',encoding='utf-16')
    decisions=pd.read_csv(out/'decisions.csv',encoding='utf-16')
    sent=decisions[decisions.reason=='entry_sent'].copy()
    sent['ny']=pd.to_datetime(sent.epoch,unit='s',utc=True).dt.tz_convert('America/New_York')
    assert len(sent)==len(trades)==sent.ny.dt.date.nunique()
    assert abs(equity.balance.iloc[-1]-status['native']['final_balance'])<0.03
    years=[]
    for year in [2023,2024,2025,2026]:
        start=max(pd.Timestamp(f'{year}-01-01'),pd.Timestamp(START));end=min(pd.Timestamp(f'{year+1}-01-01'),pd.Timestamp(END))
        selected=[t for t in trades if start<=pd.Timestamp(t['close_time'])<end]
        initial=10000+sum(t['net_profit'] for t in trades if pd.Timestamp(t['close_time'])<start)
        years.append({'period':f'{start.date()} to {(end-pd.Timedelta(days=1)).date()}','start_balance':initial,**stats(selected,start,end,initial)})
    recent=[]
    for label,start in [('Last year','2025-10-06'),('Last 6 months','2026-04-06'),('Last 3 months','2026-07-06'),('2026 available real ticks','2026-01-01')]:
        selected=[t for t in trades if pd.Timestamp(t['close_time'])>=pd.Timestamp(start)]
        initial=10000+sum(t['net_profit'] for t in trades if pd.Timestamp(t['close_time'])<pd.Timestamp(start))
        recent.append({'period':label,'dates':f'{start} to 2026-10-05',**stats(selected,start,END,initial)})
    result={'from':START,'through':'2026-10-05','risk':'1% equity per trade, compounding','summary':total,'native':status['native'],'years':years,'recent':recent,
            'decisions':{str(k):int(v) for k,v in decisions.reason.value_counts().items()},
            'real_tick_notes':sorted(set(re.findall(r'USTEC\s*:\s*real ticks begin from[^\r\n]*','\n'.join(status['real_tick_notes'])))),
            'broker_stop_rejections':status['broker_stop_rejections'],
            'native_vs_net_note':'Native PF/win rate differ from whole-position NET figures because the latter include entry commission.',
            'verification':json.loads((R/'verification.json').read_text()) if (R/'verification.json').exists() else None}
    save(R/'results.json',result);pd.DataFrame(trades).to_csv(R/'Trades.csv',index=False)
    build_report(result,trades)
    print('NET RESULTS '+json.dumps(total),flush=True)

def build_report(result,trades):
    total=result['summary'];native=result['native']
    def fmt(value):return '—' if value is None else f'{value:.2f}'
    def row(label,m):
        keys=['trades','return_pct','pf','win_rate','daily_balance_sharpe','win_streak','loss_streak','closed_balance_dd']
        return '<tr><td>'+html.escape(label)+'</td>'+''.join('<td>'+(str(m[k]) if k in ['trades','win_streak','loss_streak'] else fmt(m[k]))+'</td>' for k in keys)+'</tr>'
    audit=result.get('verification')
    audit_html=''
    if audit:
        audit_html=f'''<h2>Execution and risk audit</h2><p>Passed independent checks: all {total['trades']} trades and cash flows reconcile with the native report; completed-bar entries, RVOL, ATR, opening range, DST, lot steps and percentage budgets verified. Largest planned initial-stop risk {audit['planned_risk_percent_max']:.4f}% of entry equity. Largest realised net loss {audit['realised_net_loss_percent_max']:.2f}% including costs and delayed fills.</p><p>{result['broker_stop_rejections']} submitted orders were rejected for invalid stops and were not forced through; {result['decisions'].get('broker_stop_skip',0)} signals were also skipped by the pre-send broker-stop check. No entry retry, stop widening or optimisation was added.</p><p>Native MT5 headline PF {native['profit_factor']:.2f} and win rate {native['win_rate_pct']:.2f}% differ from the net figures above because entry commission is included in the whole-position analysis. There were {audit['exit_reasons'].get('TP',0)} TP exits and {audit['exit_reasons'].get('SL',0)} SL exits; a TP exit is not necessarily a net winner after spread/fees.</p>'''
    balance=10000;points=[[pd.Timestamp(START,tz='UTC').timestamp()*1000,balance]]
    for t in trades:
        balance+=t['net_profit'];points.append([pd.Timestamp(t['close_time'],tz='UTC').timestamp()*1000,round(balance,2)])
    report=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NY Open Range US100 — 1% risk raw test</title>
<style>body{{background:#08150f;color:#edfff5;font:16px system-ui;max-width:1200px;margin:32px auto;padding:20px}}h1{{font-size:40px}}p,li{{line-height:1.6}}.muted{{color:#abc5b6}}.notice{{border:1px solid #85702e;border-radius:12px;padding:20px;background:#242618}}a{{color:#60edba}}table{{width:100%;border-collapse:collapse;margin:24px 0;font-variant-numeric:tabular-nums}}th,td{{padding:12px;border-bottom:1px solid #2c4939;text-align:right}}th:first-child,td:first-child{{text-align:left}}.scroll{{overflow:auto}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:24px 0}}.card{{border:1px solid #2c4939;border-radius:12px;padding:20px}}.card strong{{font-size:28px;display:block;color:#60edba}}svg{{width:100%;height:320px}}code{{overflow-wrap:anywhere}}</style></head><body>
<p class="muted">CALYX · RAW ISOLATED RESEARCH · NO OPTIMISATION OR LIVE CHANGES</p><h1>NY Open Range Breakout — US100</h1><p>6 October 2023–5 October 2026 · Exness USTEC · $10,000 initial capital · 1% current equity planned stop risk per trade</p>
<div class="notice">A CFD adaptation of the retrieved Roboquant MNQ 15m code and preset. Only the strategy risk mode changes to percentage sizing; CFD tick volume, fractional lots, Bid/Ask fills and MT5 ATR differ from the original platform. NOT a verified reproduction of the site's futures benchmark. Real-tick coverage below is essential because the target is only 0.4R. Historical results are not forecasts.</div>
<div class="grid">{''.join(f'<div class="card">{label}<strong>{fmt(value)}{unit}</strong></div>' for label,value,unit in [('Net return',total['return_pct'],'%'),('Net PF',total['pf'],''),('Net win rate',total['win_rate'],'%'),('Native equity DD',native['equity_drawdown_relative_pct'],'%'),('Trades',total['trades'],''),('Daily closing Sharpe',total['daily_balance_sharpe'],'')])}</div>
<h2>Closed balance</h2><svg id="chart" viewBox="0 0 1100 320" role="img" aria-label="Closed trade balance in USD over the three year test"></svg><p id="hover" class="muted"></p>
<h2>Full period and calendar years</h2><div class="scroll"><table><thead><tr><th>Period</th><th>Trades</th><th>Return %</th><th>Net PF</th><th>Net win %</th><th>Daily Sharpe</th><th>Win streak</th><th>Loss streak</th><th>Closed DD %</th></tr></thead><tbody>{row('Full 3 years',total)+''.join(row(y['period'],y) for y in result['years'])}</tbody></table></div>
<h2>Recent slices</h2><div class="scroll"><table><thead><tr><th>Period through 5 Oct 2026</th><th>Trades</th><th>Return %</th><th>Net PF</th><th>Net win %</th><th>Daily Sharpe</th><th>Win streak</th><th>Loss streak</th><th>Closed DD %</th></tr></thead><tbody>{''.join(row(y['period']+' · '+y['dates'],y) for y in result['recent'])}</tbody></table></div>
<p class="muted">These are slices of one continuing compounded account, not independently reset tests. Each return uses the slice's starting closed balance. Net PF and win rate include both entry and exit costs, unlike some MT5 headline calculations. Sharpe uses weekday daily closed-balance returns including zero-trade weekdays, annualised sqrt(252), zero risk-free rate. Native equity drawdown includes floating P&amp;L; the closed DD columns do not.</p>
<h2>Trades, streaks and costs</h2><p>Wins {total['wins']} · Losses {total['losses']} · Flat {total['flat']} · Maximum winning run {total['win_streak']} · Maximum losing run {total['loss_streak']} · {fmt(total['trades_per_month'])} trades/month.</p><p>Average win ${fmt(total['avg_win'])} · Average loss ${fmt(total['avg_loss'])} · Best trade ${fmt(total['best_trade'])} · Worst trade ${fmt(total['worst_trade'])} · Commission ${fmt(total['commission'])} · Swap ${fmt(total['swap'])}. Broker spread and delayed fills are embedded in prices.</p>
<h2>Rules preserved</h2><p>09:30–09:45 ET range; entry on later completed M15 close beyond range. RVOL ≥1 versus previous 20 bars excluding signal; ATR14 as price percent [0.10%,0.60%]. Stop 0.4 ATR14, target 0.4R =0.16 ATR14; both directions; one attempt/day; no trailing or added filters. Source's bar-open clock checks retained (15:00 cutoff input and 15:55 flatten input are not exact tick timers).</p>
{audit_html}
<h2>Native execution and tick coverage</h2><p>Model 4 ·150ms delay · Broker-generated earlier ticks where real ticks are unavailable · Reported quality {html.escape(native['history_quality'])}.</p><pre>{html.escape(chr(10).join(result['real_tick_notes']))}</pre><p>Risk is a planned initial-stop budget, not a guaranteed loss cap. Broker lot steps are rounded down; minimum-volume/invalid-stop signals skip. Costs, slippage and gaps may exceed 1%.</p>
<details><summary>Signal decision counts</summary><pre>{html.escape(json.dumps(result['decisions'],indent=2))}</pre></details>
<p><a href="Trades.csv">Every trade (CSV)</a> · <a href="native/report.htm">Native MT5 report</a> · <a href="NY%20Open%20Range%20US100.mq5">MT5 research code</a> · <a href="NY%20Open%20Range%20US100%201pct.set">1% MT5 preset</a> · <a href="PROTOCOL.txt">Frozen protocol</a> · <a href="results.json">Full metrics</a> · <a href="verification.json">Independent verification</a> · <a href="../ny_open_range_breakout.rq">Retrieved original source</a> · <a href="../ny-open-range-breakout-mnq-15m.set">Original fixed-risk preset</a> · <a href="../ny-open-range-breakout-mnq-15m-1pct.set">1% Roboquant preset</a></p>
<script>const data={json.dumps(points)};const svg=document.getElementById('chart');const ns='http://www.w3.org/2000/svg';const min=Math.min(...data.map(x=>x[1])),max=Math.max(...data.map(x=>x[1]));const x=t=>90+970*(t-data[0][0])/(data.at(-1)[0]-data[0][0]);const y=v=>260-220*(v-min)/(max-min||1);function text(px,py,s){{const e=document.createElementNS(ns,'text');e.setAttribute('x',px);e.setAttribute('y',py);e.setAttribute('fill','#abc5b6');e.setAttribute('font-size',16);e.textContent=s;svg.appendChild(e)}}svg.innerHTML='<polyline fill="none" stroke="#60edba" stroke-width="2" points="'+data.map(p=>x(p[0])+','+y(p[1])).join(' ')+'"/>';text(3,44,'$'+max.toFixed(0));text(3,264,'$'+min.toFixed(0));text(90,298,'Oct 2023');text(490,298,'UTC date');text(970,298,'Oct 2026');svg.onmousemove=e=>{{const t=data[0][0]+(e.offsetX/svg.clientWidth*1100-90)/970*(data.at(-1)[0]-data[0][0]);const p=data.reduce((a,b)=>Math.abs(b[0]-t)<Math.abs(a[0]-t)?b:a);document.getElementById('hover').textContent=new Date(p[0]).toISOString().slice(0,19)+' UTC — $'+p[1].toFixed(2)}};</script></body></html>'''
    (R/'Results.html').write_text(report,encoding='utf-8')

if __name__=='__main__':
    command=sys.argv[1] if len(sys.argv)>1 else 'all'
    if command=='analyse':analyse()
    else:
        import msvcrt
        with (B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
            lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
            if command in ['compile','all']:compile_ea()
            if command=='smoke':run_case(True)
            if command in ['run','all']:run_case(False)
            if command=='collect-smoke':
                out=R/'smoke';owned=json.loads((out/'owned-process.json').read_text())
                collect(True,T/'reports'/TAG/'smoke.htm',gzip.decompress((out/'journal.txt.gz').read_bytes()).decode(),owned['started'],'2026.09.01','2026.09.08',json.loads((R/'build.json').read_text()),parameters())
            if command=='collect-full':
                out=R/'native';owned=json.loads((out/'owned-process.json').read_text())
                collect(False,T/'reports'/TAG/'raw.htm',gzip.decompress((out/'journal.txt.gz').read_bytes()).decode(),owned['started'],START.replace('-','.'),END.replace('-','.'),json.loads((R/'build.json').read_text()),parameters())
