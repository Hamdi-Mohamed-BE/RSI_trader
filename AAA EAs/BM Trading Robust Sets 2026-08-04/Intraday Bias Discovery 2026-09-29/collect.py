"""No-trade, isolated portable tester data collection. Never use the live API."""
from pathlib import Path
import gzip,hashlib,json,os,shutil,subprocess,time,msvcrt,socket
ROOT=Path(__file__).resolve().parent
TESTER=ROOT.parent/'_Backtests/MT5-DMC-20260811'
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files'
SYMS='US30 USTEC US500 XAUUSD BTCUSD ETHUSD EURUSD GBPUSD USDJPY AUDUSD NZDUSD USDCAD USDCHF'.split()
def run(args,**kwargs):return subprocess.run(args,creationflags=subprocess.CREATE_NO_WINDOW,**kwargs)
def read(p):
 b=p.read_bytes();return b.decode('utf-16') if b[:2] in (b'\xff\xfe',b'\xfe\xff') else b.decode('utf-8-sig',errors='replace')
def main():
 assert TESTER.resolve()!=Path('C:/Program Files/MetaTrader 5').resolve()
 paths=run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process -Filter \"Name = 'terminal64.exe'\" | Select-Object -ExpandProperty ExecutablePath"],capture_output=True,text=True).stdout
 assert str(TESTER).lower() not in paths.lower(),'Isolated research tester is busy; nothing stopped'
 lease=(TESTER/'intraday-collector.lock').open('a+b');lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
 with socket.socket() as s:assert s.connect_ex(('127.0.0.1',3000))!=0,'Tester agent port busy'
 log=ROOT/'ExportBias.compile.log'
 run(f'"{TESTER/"MetaEditor64.exe"}" /portable /compile:"{ROOT/"ExportBias.mq5"}" /log:"{log}"',timeout=120)
 assert '0 errors, 0 warnings' in read(log),read(log)
 dest=TESTER/'MQL5/Experts/AAA Research/IntradayBias20260929';dest.mkdir(parents=True,exist_ok=True)
 shutil.copy2(ROOT/'ExportBias.ex5',dest/'ExportBias.ex5')
 # Reuse existing isolated demo configuration without exposing account fields.
 previous=ROOT.parent/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini'
 header=read(previous).split('[Experts]')[0].split('[Tester]')[0]
 assert '[Common]' in header and 'Exness-MT5Trial16' in header
 ini=ROOT/'collector.ini'
 ini.write_text(header+'\n[Experts]\nEnabled=0\nAllowLiveTrading=0\nAllowDllImport=0\n[Tester]\nExpert=AAA Research\\IntradayBias20260929\\ExportBias\nSymbol=USTEC\nPeriod=M5\nDeposit=10000\nCurrency=USD\nLeverage=1:2000\nModel=2\nOptimization=0\nFromDate=2021.09.01\nToDate=2026.09.27\nShutdownTerminal=1\nUseLocal=1\nUseRemote=0\nUseCloud=0\nVisual=0\n',encoding='utf-8-sig')
 def logs():return list((TESTER/'logs').glob('*.log'))+list((TESTER/'Tester/logs').glob('*.log'))+list((TESTER/'Tester').glob('Agent-*/logs/*.log'))
 offsets={p:p.stat().st_size for p in logs()};start=time.time()
 proc=subprocess.Popen(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=TESTER,creationflags=subprocess.CREATE_NO_WINDOW)
 print('Owned data-only tester started; PID',proc.pid,flush=True)
 try:proc.wait(timeout=900)
 except subprocess.TimeoutExpired:
  proc.terminate();proc.wait(timeout=15);raise RuntimeError('Owned data collector timed out; live terminal untouched')
 journal=''
 for p in logs():
  if p.stat().st_mtime<start-2:continue
  with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')
 (ROOT/f'collector-journal-{int(start)}.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 records=[];(ROOT/'data').mkdir(exist_ok=True)
 for name in [s+'_M5' for s in SYMS]+['specs']:
  p=COMMON/f'CalyxBias20260929_{name}.csv'
  if not p.exists() or p.stat().st_mtime<start-2:raise RuntimeError('Missing fresh export '+name+'; inspect collector journal')
  b=p.read_bytes();out=ROOT/'data'/f'{name}.csv.gz';out.write_bytes(gzip.compress(b,mtime=0));records.append(dict(file=out.name,sha256=hashlib.sha256(b).hexdigest(),bytes=len(b)))
 info=dict(files=records,elapsed_seconds=time.time()-start,coverage=[x[x.index('BIAS_'):] for x in journal.splitlines() if 'BIAS_' in x])
 (ROOT/'COLLECTION.json').write_text(json.dumps(info,indent=2),encoding='utf-8');print(json.dumps(info),flush=True)
 lease.close()
if __name__=='__main__':main()
