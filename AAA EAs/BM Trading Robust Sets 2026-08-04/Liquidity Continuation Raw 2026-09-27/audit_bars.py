"""Independent historical-bar rebuild AFTER the main grid releases the isolated tester."""
from pathlib import Path
from datetime import datetime,timezone
import gzip,hashlib,json,re,shutil,subprocess,time
import numpy as np
import run as runner
from verify import fields
ROOT=runner.ROOT;TESTER=runner.TESTER;DEST=TESTER/'MQL5/Experts/AAA Research/Liquidity Audit 20260927'
DT=np.dtype([('time','<i8'),('open','<f8'),('high','<f8'),('low','<f8'),('close','<f8'),('tick_volume','<i8')])
def export():
 runner.free();log=ROOT/'ExportAudit.compile.log'
 subprocess.run(f'"{TESTER/"metaeditor64.exe"}" /portable /compile:"{ROOT/"ExportAudit.mq5"}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=120)
 assert '0 errors, 0 warnings' in runner.read(log),runner.read(log)
 DEST.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'ExportAudit.ex5',DEST/'ExportAudit.ex5')
 out=ROOT/'bar-audit';out.mkdir(exist_ok=True)
 common=(ROOT/'native/US30-touch-1y/tester.ini').read_text(encoding='utf-8-sig').split('[Experts]')[0]
 for asset,symbol in runner.CFG['symbols'].items():
  cached=[out/f'{symbol}-{tf}.bin.gz' for tf in ('M5','D1')]
  if all(p.exists() for p in cached):
   first=[np.frombuffer(gzip.decompress(p.read_bytes()),dtype=DT)['time'][0] for p in cached]
   if all(t<int(datetime(2021,9,1,tzinfo=timezone.utc).timestamp()) for t in first):continue
   # Preserve the too-short initial export, then request an earlier tester window.
   old=out/'short-window-attempt';old.mkdir(exist_ok=True)
   for p in cached+[out/f'{symbol}.ini',out/f'{symbol}.journal.gz']:
    if p.exists() and not (old/p.name).exists():shutil.copy2(p,old/p.name)
  runner.free();ini=out/f'{symbol}.ini';ini.write_text(common+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\Liquidity Audit 20260927\\ExportAudit
Symbol={symbol}
Period=M5
Deposit=10000
Currency=USD
Leverage=1:2000
Model=1
Optimization=0
FromDate=2021.01.01
ToDate=2026.09.27
Report=reports\\liquidity-20260927\\audit-{symbol}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
  before={p:p.stat().st_size for p in runner.logs()};began=time.time()
  print('EXPORT '+symbol,flush=True)
  p=subprocess.Popen(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=TESTER,creationflags=subprocess.CREATE_NO_WINDOW)
  try:p.wait(timeout=300)
  except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=30);raise
  journal=''
  for log in runner.logs():
   if log.stat().st_mtime<began-2:continue
   with log.open('rb') as f:f.seek(before.get(log,0));journal+=f.read().decode('utf-16-le',errors='replace')
  (out/f'{symbol}.journal.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
  assert 'LC_AUDIT_FAILED' not in journal and 'LC_AUDIT_FILE_FAILED' not in journal
  for tf in ('M5','D1'):
   files=[f for f in (TESTER/'Tester').glob(f'Agent-*/MQL5/Files/LC_AUDIT_{symbol}_{tf}.bin') if f.stat().st_mtime>=began-2]
   assert len(files)==1,(symbol,tf,'export missing',journal[-1500:])
   b=files[0].read_bytes();assert len(b)%48==0
   (out/f'{symbol}-{tf}.bin.gz').write_bytes(gzip.compress(b,mtime=0))
def check():
 out=ROOT/'bar-audit';results=[];data=[]
 for asset,symbol in runner.CFG['symbols'].items():
  rates={tf:np.frombuffer(gzip.decompress((out/f'{symbol}-{tf}.bin.gz').read_bytes()),dtype=DT) for tf in ('M5','D1')}
  m=rates['M5'];d=rates['D1'];mt=m['time'];dt=d['time']
  for tf,bars in rates.items():
   p=out/f'{symbol}-{tf}.bin.gz'
   data.append(dict(symbol=symbol,timeframe=tf,rows=len(bars),first_utc=datetime.fromtimestamp(int(bars['time'][0]),timezone.utc).isoformat(),last_utc=datetime.fromtimestamp(int(bars['time'][-1]),timezone.utc).isoformat(),gzip_sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
  assert mt[0]<int(datetime(2021,9,1,tzinfo=timezone.utc).timestamp()) and dt[0]<mt[0]+86400,'Insufficient bar export coverage'
  assert np.all(np.diff(mt)>0) and np.all(np.diff(dt)>0),'Duplicate/out-of-order bars'
  prev=np.roll(m['close'],1);tr=np.maximum(m['high'],prev)-np.minimum(m['low'],prev);tr[0]=0
  atr=np.convolve(tr,np.ones(14)/14,mode='full')[:len(tr)]
  for p in sorted((ROOT/'native').glob(asset+'-*/run.json')):
   r=json.loads(p.read_text());journal=gzip.decompress((p.parent/'journal.txt.gz').read_bytes()).decode()
   lines=list(set(re.findall(r'LC_[^\r\n]+',journal)));orders=[fields(l) for l in lines if l.startswith('LC_ORDER')]
   levels=[fields(l) for l in lines if l.startswith('LC_LEVEL')];touches=[fields(l) for l in lines if l.startswith('LC_TOUCH')]
   tick=float(fields(r['symbol_spec'][0])['tick']);errors=[];level_checks=0;atr_checks=0;retest_checks=0
   for lv in levels:
    t=int(lv['at']);i=int(lv['i']);day=t-t%86400;side=1 if i%2==0 else -1
    if i<2:
     j=np.searchsorted(dt,day)-1
     expected=d['high' if side>0 else 'low'][j]
    elif i<6:
     a,b=(day,day+21600) if i<4 else (day+25200,day+36000)
     subset=m[np.searchsorted(mt,a):np.searchsorted(mt,b)]
     if not len(subset):errors.append(['missing_session',lv]);continue
     expected=np.max(subset['high']) if side>0 else np.min(subset['low'])
    else:
     weekday=datetime.fromtimestamp(t,timezone.utc).weekday();monday=day-weekday*86400
     subset=d[np.searchsorted(dt,monday-7*86400):np.searchsorted(dt,monday)]
     if not len(subset):errors.append(['missing_week',lv]);continue
     expected=np.max(subset['high']) if side>0 else np.min(subset['low'])
    level_checks+=1
    if abs(expected-float(lv['real']))>max(1e-6,tick/2):errors.append(['real_level',i,t,float(expected),float(lv['real'])])
   for o in orders:
    t=int(o['at']);j=np.searchsorted(mt,t,side='right')-2
    # Closed previous M5 ATR; binary export must cover the exact entry bar.
    if j<14:errors.append(['missing_atr',t]);continue
    atr_checks+=1
    if abs(atr[j]-float(o['atr']))>max(1e-6,tick/100):errors.append(['ATR',t,float(atr[j]),float(o['atr'])])
    if r['variant'].startswith('retest'):
     side=int(o['type']);level=float(o['level']);ts=[x for x in touches if x['i']==o['i'] and int(x['at'])<t and abs(float(x['level'])-level)<1e-7]
     if not ts:errors.append(['no_touch',t]);continue
     touch=max(int(x['at']) for x in ts);broken=None;found=False
     for k in range(np.searchsorted(mt,touch//300*300),j+1):
      bar=m[k];close_time=int(bar['time'])+300
      if close_time<=touch:continue
      outside=side*(bar['close']-level)>0
      if broken is None:
       if outside:broken=int(bar['time'])
      elif int(bar['time'])>broken and outside and (bar['low']<=level if side>0 else bar['high']>=level):
       if k==j:found=True
       break
     retest_checks+=1
     if not found:errors.append(['retest_bars',t,touch,level])
   row=dict(case=p.parent.name,level_checks=level_checks,atr_checks=atr_checks,retest_checks=retest_checks,error_count=len(errors),examples=errors[:20]);results.append(row)
   print(row['case'],level_checks,atr_checks,retest_checks,'errors',len(errors),flush=True)
 runner.save(ROOT/'BAR_VERIFICATION.json',dict(cases=results,total_errors=sum(r['error_count'] for r in results),total_level_checks=sum(r['level_checks'] for r in results),total_atr_checks=sum(r['atr_checks'] for r in results),total_retest_checks=sum(r['retest_checks'] for r in results),data=data,checker_sha256=runner.sha(ROOT/'audit_bars.py'),exporter_sha256=runner.sha(ROOT/'ExportAudit.mq5'),source='Native historical M5/D1 export; independent Python level/ATR/confirmation rebuild; no performance changes'))
if __name__=='__main__':export();check()
