"""Step-one frozen native comparison; separate research build, live terminals untouched."""
from pathlib import Path
from datetime import datetime,timezone
import gzip,hashlib,importlib.util,json,os,re,shutil,subprocess,time,sys
import pandas as pd
R=Path(__file__).resolve().parent;B=R.parent
os.environ['EA_STORE_DISABLE_MT5']='1'
sp=importlib.util.spec_from_file_location('two_week_native_helpers',B/'FTMO Exit Management Research 2026-09-27/run.py');h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
T=h.TESTER;OUT=R/'native';DEST=T/'MQL5/Experts/AAA Research/QuantLabSOM20261004'
START='2026.09.20';END='2026.10.04'
CASES={
 'CURRENT':dict(expert=B/'Nasdaq 5M DI ATR Deployment 2026-09-28/EA/Nasdaq 5M DI Wide ATR EA.ex5',settings=B/'Selected Portfolio Settings 2026-09-01/11 Nasdaq 5M - DI WIDE 0P60PCT ATR6 NO TP - 1PCT.set'),
 'OLD':dict(expert=B/'Active Portfolio Full Pipeline 2026-09-05/11 Nasdaq 5M Candle Momentum/EA/Nasdaq 5M Candle Momentum DI EA.ex5',settings=B/'Selected Portfolio Settings 2026-09-01/11 Nasdaq 5M Candle Momentum - OPTIMIZED 2P5R + DI AGREE M5 - HARD 1PCT.set')}
CASES['CURRENT_NO_DI']={**CASES['CURRENT'],'overrides':{'InpRequireDIAgreement':'false'}}
for key, mode in [('PARITY',0),('VIDEO_LITERAL',1),('VIDEO_SYMMETRIC',2)]:
 CASES[key]={**CASES['CURRENT'],'expert':R/'EA/Calyx Session Open Momentum Research.ex5',
             'overrides':{'InpRequireDIAgreement':'false','InpSOMBodyMode':str(mode)}}
PERIODS={'PARITY':('2026.09.20','2026.10.04'),'1Y':('2025.10.04','2026.10.04'),'3M':('2026.07.04','2026.10.04')}
WINDOW='PARITY'
def compile_research():
 h.free()
 source=R/'EA/Calyx Session Open Momentum Research.mq5'
 log=source.with_suffix('.compile.log');began=time.time()
 si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
 subprocess.run(f'"{T/"MetaEditor64.exe"}" /portable /compile:"{source}" /log:"{log}"',
                creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=si,timeout=180)
 body=h.text(log) if log.exists() else 'Missing compile log'
 assert '0 errors, 0 warnings' in body,body[-7000:]
 assert source.with_suffix('.ex5').stat().st_mtime>=began-2
 save(R/'build.json',dict(source_sha256=sha(source),binary_sha256=sha(source.with_suffix('.ex5')),compiler_tail=body[-500:]))
 status('COMPILED isolated research EA: zero errors/warnings')
def select_window(window):
 global START,END,WINDOW
 START,END=PERIODS[window];WINDOW=window

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def status(s):save(R/'status.json',dict(utc=datetime.now(timezone.utc).isoformat(),message=s));print(s,flush=True)
def order_initials(report):
 from app.mt5_evidence_jobs import _clean,_number
 text=h._read_report(report);start=text.lower().find('<b>orders</b>');end=text.lower().find('<b>deals</b>');rows=[]
 for body in re.findall(r'<tr\b[^>]*>(.*?)</tr>',text[start:end],re.S|re.I):
  c=[_clean(x) for x in re.findall(r'<td\b[^>]*>(.*?)</td>',body,re.S|re.I)]
  if len(c)>=11 and re.fullmatch(r'\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}',c[0]):rows.append(c)
 return rows
def run(name):
 c=CASES[name];folder=OUT/WINDOW/name;folder.mkdir(parents=True,exist_ok=True)
 inputs=dict(l.split('=',1) for l in c['settings'].read_text(encoding='utf-8-sig').splitlines() if '=' in l and not l.startswith(';'))
 assert inputs['InpRiskPercent']=='1.0' and inputs['InpRequireDIAgreement']=='true'
 inputs['InpAdaptivePortfolioControls']='false'
 inputs.update(c.get('overrides',{}))
 frozen=dict(version=name,window=WINDOW,start=START,end_exclusive=END,deposit=10000,risk_percent=1,model=4,delay_ms=150,symbol='USTEC',timeframe='M5',broker='Exness-MT5Trial16',expert_source=str(c['expert']),settings_source=str(c['settings']),binary_sha256=sha(c['expert']),set_sha256=sha(c['settings']),protocol_sha256=sha(R/'PROTOCOL.txt'),inputs=inputs)
 if c.get('overrides'):frozen.update(overrides=c['overrides'],addendum_sha256=sha(R/'NO_DI_PROTOCOL.txt'))
 mp=folder/'manifest.json'
 if mp.exists():assert json.loads(mp.read_text())==frozen,'Frozen inputs changed'
 else:save(mp,frozen)
 if (folder/'results.json').exists():return json.loads((folder/'results.json').read_text())
 h.free();profile=T/'MQL5/Profiles/Charts/Calyx Research Empty';assert profile.is_dir() and not list(profile.glob('*.chr'))
 DEST.mkdir(parents=True,exist_ok=True);shutil.copy2(c['expert'],DEST/(name+'.ex5'));assert sha(DEST/(name+'.ex5'))==frozen['binary_sha256']
 setname='som-'+WINDOW+'-'+name+'.set';body='\n'.join(k+'='+v for k,v in inputs.items())+'\n';(folder/setname).write_text(body);(T/'MQL5/Profiles/Tester'/setname).write_text(body)
 header=h.text(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
 rp=T/'reports/quantlab-som20261004'/(WINDOW+'-'+name+'.htm');rp.parent.mkdir(parents=True,exist_ok=True)
 ini=folder/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\QuantLabSOM20261004\\{name}
ExpertParameters={setname}
Symbol=USTEC
Period=M5
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate={START}
ToDate={END}
ForwardMode=0
Report=reports\\quantlab-som20261004\\{WINDOW}-{name}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 offsets={p:p.stat().st_size for p in h.logfiles()};began=time.time();h.free();status('START '+WINDOW+' '+name)
 si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
 proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=si)
 save(folder/'owned-process.json',dict(pid=proc.pid,executable=str(T/'terminal64.exe'),started=began))
 try:proc.wait(timeout=900)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=20);raise RuntimeError('Owned isolated test timed out')
 journal=''
 for p in h.logfiles():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')+'\n'
 (folder/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 assert proc.returncode==0 and rp.exists() and rp.stat().st_mtime>=began-2
 assert not re.search(r'initialization failed|start time changed|not enough history|invalid volume|stop out|margin call|access violation|array out of range|zero divide|N5EMA order rejected',journal,re.I),'Invalid test; see journal'
 report=h._read_report(rp);assert all(x in report for x in [START,END,'USTEC','M5'])
 actual=h._report_inputs(rp);assert all(k in actual and h._same_setting(v,actual[k]) for k,v in inputs.items()),'SET not applied'
 from app.mt5_evidence_jobs import _metric,_number
 native=h._native_metrics(rp);native['equity_dd_pct']=_number(_metric(report,'Equity Drawdown Relative'))
 trades=h._native_trades(rp,name);assert len(trades)==native['trades'];assert abs(sum(x['net_profit'] for x in trades)-native['net_profit'])<.10
 orders=order_initials(rp)
 for t in trades:
  op=pd.Timestamp(t['open_time'],tz='UTC');cl=pd.Timestamp(t['close_time'],tz='UTC');t['open_ny']=op.tz_convert('America/New_York').strftime('%Y-%m-%d %H:%M:%S');t['close_ny']=cl.tz_convert('America/New_York').strftime('%Y-%m-%d %H:%M:%S');t['hold_hours']=round((cl-op).total_seconds()/3600,3)
  assert op>=pd.Timestamp(START.replace('.','-'),tz='UTC') and cl<pd.Timestamp(END.replace('.','-'),tz='UTC')
  assert op.tz_convert('America/New_York').strftime('%H:%M')=='09:35','Unexpected entry time'
  t['boundary_exit']='end of test' in t['exit_comment'].lower()
  exit=t['exit_comment'].lower()
  t['exit_reason']='Test-end liquidation (not normal strategy exit)' if t['boundary_exit'] else 'Take profit' if exit.startswith('tp') or '[tp' in exit else 'Protective/trailing stop' if exit.startswith('sl') or '[sl' in exit else 'Session exit' if name=='OLD' and cl.tz_convert('America/New_York').strftime('%H:%M')>='15:55' else 'Market exit: '+t['exit_comment']
 save(folder/'trades.json',trades);save(folder/'orders.json',orders)
 pd.DataFrame(trades).to_csv(folder/'trades.csv',index=False)
 (folder/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
 for img in rp.parent.glob(WINDOW+'-'+name+'*.png'):shutil.copy2(img,folder/img.name)
 pnl=[t['net_profit'] for t in trades];positive=sum(x for x in pnl if x>0);negative=-sum(x for x in pnl if x<0)
 result=dict(manifest=frozen,native=native,net_pf=positive/negative if negative else None,net_win_rate_pct=100*sum(x>0 for x in pnl)/len(pnl) if pnl else None,positions=len(trades),end_liquidations=sum(t['boundary_exit'] for t in trades),commission=round(sum(t['commission'] for t in trades),2),swap=round(sum(t['swap'] for t in trades),2),stop_modify_failures=journal.count('N5EMA stop modification failed'),tick_notes=sorted(set(x for x in journal.splitlines() if re.search('real ticks begin|real ticks absent|ticks discarded',x,re.I)))[:15],seconds=round(time.time()-began,1),report_sha256=sha(rp),orders=orders,trades=trades)
 save(folder/'results.json',result);status('DONE '+WINDOW+' '+name+' '+json.dumps(native));return result
def validate_parity():
 parity=run('PARITY')
 reference=json.loads((B/'Nasdaq 5M Two Week Comparison 2026-10-04/native/CURRENT_NO_DI/results.json').read_text())
 keys=('open_time','close_time','side','volume','open_price','close_price','net_profit','commission','swap','exit_comment')
 a=[{k:t.get(k) for k in keys} for t in parity['trades']]
 b=[{k:t.get(k) for k in keys} for t in reference['trades']]
 assert a==b,'Research copy mode 0 is not trade-identical to original DI-off'
 assert parity['native']==reference['native'],'Native parity mismatch'
 save(R/'parity.json',dict(passed=True,positions=len(a),net_profit=parity['native']['net_profit'],keys=list(keys)))
 status('PARITY PASSED: original DI-off and research mode zero have identical trades and native metrics')
def main():
 if sys.argv[1]=='compile':compile_research();return
 if sys.argv[1]=='parity':select_window('PARITY');validate_parity();return
 select_window(sys.argv[1])
 names=sys.argv[2:] or ['CURRENT','CURRENT_NO_DI','OLD','VIDEO_LITERAL','VIDEO_SYMMETRIC']
 assert (R/'parity.json').exists(),'Complete parity before comparisons'
 for name in names:run(name)
 rows=[json.loads(p.read_text()) for p in sorted(OUT.glob('*/*/results.json')) if p.parent.parent.name!='PARITY']
 save(R/'RESULTS.json',rows)
 status('Finished requested cases. Step-one only; live account unchanged')
if __name__=='__main__':main()
