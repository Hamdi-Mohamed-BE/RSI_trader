"""Selected production/research parity. One isolated tester, no live API."""
from pathlib import Path
import importlib.util, json, gzip, shutil, os
R=Path(__file__).resolve().parent;B=R.parent;S=B/'ADX DI Five Bot Review 2026-10-03'
os.environ['EA_STORE_DISABLE_MT5']='1'
sp=importlib.util.spec_from_file_location('study_runner',S/'run.py');m=importlib.util.module_from_spec(sp)
# The frozen runner's INI contains its expert folder literally. Redirect BOTH
# the copy target and that INI reference; never accidentally test the old EA.
exec(compile((S/'run.py').read_text().replace('ADXDI20261003','ADXDIRelease20261003'),str(S/'run.py'),'exec'),m.__dict__)
m.R=R;m.OUT=R/'native';m.DEST=m.T/'MQL5/Experts/AAA Research/ADXDIRelease20261003'
profiles=json.loads((R/'SELECTION.json').read_text())['profiles'];bots=json.loads((S/'bots.json').read_text())
checks={}
for slug,p in profiles.items():
 key=p['key'];folder=m.DEST/key;folder.mkdir(parents=True,exist_ok=True);shutil.copy2(B/p['expert'],folder/'Original.ex5')
 b=dict(bots[key]);b['inputs']=p['inputs'];b['original']=str(B/p['expert'])
 result=m.case(key,b,'BASE',True)
 old=json.loads(gzip.decompress((S/'native'/p['research_case']/'trades.json.gz').read_bytes()))
 new=json.loads(gzip.decompress((m.OUT/result['tag']/'trades.json.gz').read_bytes()))
 fields=['open_time','close_time','side','volume','open_price','close_price','commission','swap','net_profit']
 assert len(old)==len(new) and all(all(x[k]==y[k] for k in fields) for x,y in zip(old,new)),slug
 checks[slug]=dict(trades=len(new),identical_entry_exit_volume_costs=True,fields=fields,expert_sha=p['expert_sha'],research_case=p['research_case'])
 m.save(R/'PARITY.json',dict(passed=True,checks=checks,live_terminal_changed=False))
 print('PARITY',slug,len(new),'identical',flush=True)
