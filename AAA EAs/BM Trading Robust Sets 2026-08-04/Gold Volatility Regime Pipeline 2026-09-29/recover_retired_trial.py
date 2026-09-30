"""Archive the completed, retired native run after its parent runner was stopped.
Does not launch a terminal or use its result for model selection.
"""
import csv,gzip,io,json,shutil
from datetime import datetime
import search as s
folder=s.OUT/'validation-1'
if (folder/'results.json').exists():raise SystemExit('Already archived')
manifest=json.loads((folder/'manifest.json').read_text());began=json.loads((folder/'owned-process.json').read_text())['started']
settings=dict(line.split('=',1) for line in next(folder.glob('*.set')).read_text().splitlines() if '=' in line)
tag=settings['InpTag'];stem=tag+'-0';report=s.TESTER/'reports/gold-vol-search-20260929'/(tag+'.htm')
assert report.exists() and report.stat().st_mtime>=began-2
net=json.loads((s.COMMON/(stem+'-net.json')).read_text());tp=s.COMMON/(stem+'-trades.csv')
assert tp.stat().st_mtime>=began-2
trades=[{k:float(v) for k,v in t.items()} for t in csv.DictReader(io.StringIO(tp.read_text()))]
metrics=s._native_metrics(report);assert abs(metrics['net_profit']-net['net_profit'])<.15
net.update(s.trade_stats(trades,manifest['start'],manifest['end']));net['max_actual_risk_pct']/=manifest['cases'][0]['max_pos']
row=dict(index=0,parameters=manifest['cases'][0],net=net,metrics=metrics,stage='validation-1',start=manifest['start'],end=manifest['end'],model=4,
         binary_sha=s.sha(folder/'Gold Volatility Search.ex5'),parameters_sha=s.digest(manifest['cases'][0]),report_sha=s.sha(report),clean=not any(net[k] for k in s.FLAGS),
         retired=True,reason='Inactive second slot halved trade risk; not eligible for selection. Completed report harvested without rerunning.')
for suffix in ('net.json','trades.csv','signals.csv','trace.csv'):
    p=s.COMMON/(stem+'-'+suffix);assert p.exists() and p.stat().st_mtime>=began-2
    (folder/('0-'+suffix+'.gz')).write_bytes(gzip.compress(p.read_bytes(),mtime=0))
(folder/(report.name+'.gz')).write_bytes(gzip.compress(report.read_bytes(),mtime=0));s.save(folder/'results.json',[row]);print('Retired native trial archived; no selection or new run.')
