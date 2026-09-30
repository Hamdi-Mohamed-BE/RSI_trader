"""One data-only isolated test. Imports safe runner helpers; no live APIs."""
import gzip,hashlib,json,msvcrt,shutil,subprocess,time
from pathlib import Path
import pandas as pd
from run import ROOT,BASE,TESTER,COMMON,DEST,free,read,logs,save,sha
def main():
 with (ROOT/'tester.lock').open('a+b') as lease:
  lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
  for retry in range(24):
   try:free();break
   except AssertionError:
    if retry==23:raise
    time.sleep(5)
  profile=TESTER/'MQL5/Profiles/Charts/Calyx Research Empty'
  assert profile.is_dir() and not list(profile.glob('*.chr'))
  log=ROOT/'export-compile.log';start=time.time()
  subprocess.run(f'"{TESTER/"metaeditor64.exe"}" /portable /compile:"{ROOT/"ExportHours.mq5"}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=120)
  assert '0 errors, 0 warnings' in read(log)
  shutil.copy2(ROOT/'ExportHours.ex5',DEST/'ExportHours.ex5')
  header=read(BASE/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
  ini=ROOT/'collector.ini';ini.write_text(header+'[Experts]\nEnabled=0\nAllowLiveTrading=0\nAllowDllImport=0\n[Tester]\nExpert=AAA Research\\MarketStyles20260929\\ExportHours\nSymbol=USTEC\nPeriod=H1\nDeposit=10000\nCurrency=USD\nLeverage=1:2000\nModel=2\nOptimization=0\nFromDate=2021.06.01\nToDate=2026.09.27\nShutdownTerminal=1\nUseLocal=1\nUseRemote=0\nUseCloud=0\nVisual=0\n',encoding='utf-8-sig')
  offsets={p:p.stat().st_size for p in logs()};began=time.time()
  proc=subprocess.Popen(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=TESTER,creationflags=subprocess.CREATE_NO_WINDOW)
  try:proc.wait(timeout=900)
  except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=15);raise
  journal=''
  for p in logs():
   if p.stat().st_mtime<began-2:continue
   with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')
  (ROOT/'collector-journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0));assert 'MS_EXPORT_FAIL' not in journal
  target=ROOT/'data';target.mkdir(exist_ok=True);records=[]
  for symbol in ['USTEC','BTCUSD','XAUUSD','EURUSD','GBPUSD','USDJPY']:
   p=COMMON/f'{symbol}-H1.csv';assert p.exists() and p.stat().st_mtime>=began-2
   d=pd.read_csv(p)
   assert d.time.is_unique and d.time.is_monotonic_increasing and (d.time%3600==0).all()
   assert (d.high>=d[['open','close','low']].max(axis=1)).all() and (d.low<=d[['open','close','high']].min(axis=1)).all()
   out=target/(p.name+'.gz');out.write_bytes(gzip.compress(p.read_bytes(),mtime=0));records.append(dict(file=out.name,sha256=sha(out),rows=len(d),first_epoch=int(d.time.min()),last_epoch=int(d.time.max())))
  save(ROOT/'DATA_EXPORT.json',dict(files=records,source_sha=sha(ROOT/'ExportHours.mq5'),binary_sha=sha(ROOT/'ExportHours.ex5'),logs=[s for s in journal.splitlines() if 'MS_EXPORT_' in s],seconds=time.time()-start));print('Exported six H1 histories without trading',flush=True)
if __name__=='__main__':main()
