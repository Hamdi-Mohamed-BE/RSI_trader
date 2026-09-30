"""Passive native quote-availability diagnostics; source indicators are not trading rules."""
import pipeline as p
import subprocess,time,gzip,json,shutil
ROOT=p.ROOT
def main():
 p.original.free()
 src=ROOT/'TimingProbe.mq5';log=ROOT/'timing-compile.log';start=time.time()
 subprocess.run(f'"{p.TESTER/"MetaEditor64.exe"}" /portable /compile:"{src}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
 assert '0 errors, 0 warnings' in p.h.text(log)
 assert src.with_suffix('.ex5').stat().st_mtime>start-2
 dest=p.TESTER/'MQL5/Experts/AAA Research/Four Ideas Timing 20260927';dest.mkdir(parents=True,exist_ok=True)
 shutil.copy2(src.with_suffix('.ex5'),dest/'TimingProbe.ex5')
 results={}
 for sym in ('USDJPY','US30','USTEC'):
  folder=ROOT/'timing'/sym;folder.mkdir(parents=True,exist_ok=True)
  original=(ROOT/'native'/('usdjpy-morning-5y-m1' if sym=='USDJPY' else 'us30-tuesday-5y-m1' if sym=='US30' else 'us100-daily-5y-m1')/'tester.ini').read_text(encoding='utf-8-sig')
  lines=[x for x in original.splitlines() if not x.startswith('ExpertParameters=')]
  lines=['Expert=AAA Research\\Four Ideas Timing 20260927\\TimingProbe' if x.startswith('Expert=') else 'Report=reports\\four-pipeline-20260927\\timing-'+sym+'.htm' if x.startswith('Report=') else x for x in lines]
  ini=folder/'tester.ini';ini.write_text('\n'.join(lines)+'\n',encoding='utf-8-sig')
  p.original.free();offset={f:f.stat().st_size for f in p.h.logfiles()};start=time.time()
  print('TIMING PROBE '+sym,flush=True)
  proc=subprocess.Popen(f'"{p.TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=p.TESTER,creationflags=subprocess.CREATE_NO_WINDOW)
  proc.wait(timeout=600)
  journal=''
  for f in p.h.logfiles():
   if f.stat().st_mtime<start-2:continue
   with f.open('rb') as h:h.seek(offset.get(f,0));journal+='\n'+h.read().decode('utf-16-le',errors='replace')
  (folder/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
  months={};sessions=set()
  for line in journal.splitlines():
   if 'CLOCK_MONTH|' in line:
    v=line[line.index('CLOCK_MONTH|'):].split('|')
    months[v[2]]=dict(zip(['minutes','broker_0105','monday_0105','broker_2350','broker_0600','broker_1800','ny_1555'],map(int,v[3:10])))|dict(first_quote_utc=v[10],last_quote_utc=v[11])
   if 'CLOCK_TRADE_SESSION|' in line:sessions.add(line[line.index('CLOCK_TRADE_SESSION|'):])
  assert len(months)==61,(sym,len(months))
  results[sym]=dict(monthly=months,current_trade_session_metadata=sorted(sessions),source_sha=p.h.sha(src),binary_sha=p.h.sha(src.with_suffix('.ex5')))
  p.save(folder/'COVERAGE.json',results[sym])
 p.save(ROOT/'TIMING_COVERAGE.json',results)
if __name__=='__main__':main()
