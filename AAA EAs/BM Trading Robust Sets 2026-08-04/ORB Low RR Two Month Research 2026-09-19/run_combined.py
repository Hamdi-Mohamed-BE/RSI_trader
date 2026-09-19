import csv,json,shutil,subprocess,time,sys
from datetime import datetime
from pathlib import Path
import run_study as base

root=base.ROOT
verification='--verification' in sys.argv
cutoffs={}
if verification:
    for r in json.loads((root/'combined'/'results.json').read_text()):
        if int(r['target']) and not int(r['breach']):
            cutoffs[int(r['group'])]=int(datetime.strptime(base.next_business_day(int(r['target'])),'%Y.%m.%d').replace(tzinfo=base.timezone.utc).timestamp())
out=root/('combined-verification' if verification else 'combined');out.mkdir(exist_ok=True)
rows=json.loads((root/'results.json').read_text())
inputs=[]
for group,variant in enumerate(('current','rr050','rr075')):
    for r in rows:
        if r['variant']!=variant:continue
        for t in json.loads((root/'cases'/r['case']/'trades.json').read_text()):
            inputs.append([group,r['slug'],r['symbol'],int(datetime.fromisoformat(t['entry_time']).timestamp()),int(datetime.fromisoformat(t['exit_time']).timestamp()),1 if t['side']=='buy' else -1,t['volume'],t['entry_price'],t['initial_risk_usd'],t['entry_cash'],t['net_profit']-t['entry_cash']])
inputs.sort(key=lambda r:(r[3],r[0],r[1]))
assert len(inputs)==117 and all(r[4]>r[3] for r in inputs)
if verification:inputs=[r for r in inputs if r[0] in cutoffs and r[3]>=cutoffs[r[0]]]
(out/'scope.json').write_text(json.dumps({'verification':verification,'cutoffs':cutoffs,'input_trades':len(inputs)},indent=2))
with (out/'orb-combined-input.csv').open('w',newline='') as f:csv.writer(f,delimiter=';').writerows(inputs)
dest=base.TESTER/'MQL5'/'Experts'/'AAA Research'/'ORB Combined 20260919';dest.mkdir(parents=True,exist_ok=True)
(base.TESTER/'MQL5'/'Files').mkdir(exist_ok=True)
shutil.copy2(out/'orb-combined-input.csv',base.TESTER/'MQL5'/'Files'/'orb-combined-input.csv')
log=out/'compile.log';source=root/'Combined.mq5'
subprocess.run(f'"{base.TESTER / "MetaEditor64.exe"}" /portable /compile:"{source}" /log:"{log}"',creationflags=base.NO_WINDOW,timeout=45)
assert '0 errors, 0 warnings' in base.read_text(log),base.read_text(log)
shutil.copy2(source.with_suffix('.ex5'),dest/'Combined.ex5')
ini=out/'combined.ini'
template=base.PACKAGE/'Nasdaq 075R Two Month FTMO Replay 2026-09-19'/'equity-audit.ini'
content=template.read_text(encoding='utf-8-sig').replace('AAA Research\\Nasdaq075Audit20260919\\Equity Path Audit','AAA Research\\ORB Combined 20260919\\Combined').replace('calyx-nasdaq075-equity-audit-20260919','orb-combined-20260919').replace('ReplaceReport=0','ReplaceReport=1')
params=base.TESTER/'MQL5'/'Profiles'/'Tester'/'orb-combined.set'
params.write_text('InpTargetPercent='+('5' if verification else '10')+'\n')
content=content.replace('[Tester]','[Tester]\nExpertParameters=orb-combined.set')
ini.write_text(content,encoding='utf-8-sig')
journal=base.TESTER/'Tester'/'logs'/'20260919.log';offset=journal.stat().st_size
print('Starting research-only three-scenario combined equity replay',flush=True)
p=subprocess.Popen(f'"{base.TESTER / "terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',creationflags=base.NO_WINDOW)
try:p.wait(timeout=360)
except subprocess.TimeoutExpired:
    p.terminate();p.wait(timeout=15);raise
with journal.open('rb') as f:f.seek(offset);text=f.read().decode('utf-16-le',errors='replace')
(out/'journal.txt').write_text(text,encoding='utf-8')
summaries=[]
for line in text.splitlines():
    if 'COMBINED|' in line:
        d=dict(p.split('=',1) for p in line.split('COMBINED|',1)[1].split('|'))
        summaries.append(d);print(d,flush=True)
    if 'COMBINED_QA|' in line:print(line,flush=True)
assert len(summaries)==3
for filename in ('orb-combined-days.csv','orb-combined-trades.csv'):
    paths=list((base.TESTER/'Tester').glob('Agent-*/MQL5/Files/'+filename));assert len(paths)==1
    shutil.copy2(paths[0],out/filename)
(out/'results.json').write_text(json.dumps(summaries,indent=2))
