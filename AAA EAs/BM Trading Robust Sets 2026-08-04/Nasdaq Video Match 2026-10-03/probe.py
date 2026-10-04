from pathlib import Path
import gzip,hashlib,importlib.util,json,os,re,shutil,subprocess,time
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
os.environ['EA_STORE_DISABLE_MT5']='1'
sp=importlib.util.spec_from_file_location('video_probe_helper',BASE/'FTMO Exit Management Research 2026-09-27/run.py');h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
TESTER=h.TESTER
def main():
 h.free();src=ROOT/'HistoryProbe.mq5';log=ROOT/'probe-compile.log'
 subprocess.run(f'"{TESTER/"metaeditor64.exe"}" /portable /compile:"{src}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=120)
 assert '0 errors, 0 warnings' in h.text(log),h.text(log)[-1000:]
 dest=TESTER/'MQL5/Experts/AAA Research/VideoMatch20261003';dest.mkdir(parents=True,exist_ok=True);shutil.copy2(src.with_suffix('.ex5'),dest/'HistoryProbe.ex5')
 header=h.text(BASE/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
 ini=ROOT/'probe.ini';ini.write_text(header+'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\VideoMatch20261003\\HistoryProbe
Symbol=USTEC
Period=M1
Deposit=10000
Currency=USD
Leverage=1:2000
Model=2
Optimization=0
FromDate=2017.10.02
ToDate=2026.10.02
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 profile=TESTER/'MQL5/Profiles/Charts/Calyx Research Empty';assert profile.is_dir() and not list(profile.glob('*.chr'))
 offsets={p:p.stat().st_size for p in h.logfiles()};began=time.time()
 si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
 proc=subprocess.Popen(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=TESTER,creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=si)
 (ROOT/'owned-process.json').write_text(json.dumps(dict(pid=proc.pid,executable=str(TESTER/'terminal64.exe'))))
 try:proc.wait(timeout=600)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=20);raise RuntimeError('Owned probe timed out')
 journal=''
 for p in h.logfiles():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')
 (ROOT/'probe-journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 notes=sorted(set(re.findall(r'[^\n]*(?:VIDEO_MATCH_HISTORY|history data begins|start time changed|history begins)[^\n]*',journal)))
 assert proc.returncode==0 and any('VIDEO_MATCH_HISTORY' in x for x in notes),'Probe failed'
 result=dict(requested_start='2017.10.02',end_exclusive='2026.10.02',notes=notes,seconds=time.time()-began,protocol_sha256=hashlib.sha256((ROOT/'PROTOCOL.txt').read_bytes()).hexdigest())
 (ROOT/'HISTORY.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':main()
