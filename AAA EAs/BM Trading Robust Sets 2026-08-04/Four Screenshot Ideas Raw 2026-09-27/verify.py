"""Final reproducibility, clock and accounting review. Offline only."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
import hashlib,json,math
import audit
ROOT=Path(__file__).resolve().parent
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 build=audit.load(ROOT/'BUILD.json');result=audit.load(ROOT/'RESULTS.json')
 for name,key in [('FourIdeas.mq5','source_sha'),('FourIdeas.ex5','binary_sha'),('RULES.md','rules_sha'),('run-config.json','config_sha')]:assert digest(ROOT/name)==build[key]
 reports=list((ROOT/'native').glob('*/run.json'));assert len(reports)==12
 for p in reports:
  run=audit.load(p);assert run['build']==build
  assert audit.load(p.parent/'AUDIT.json')['ok']
 assert len(result['records'])==8
 for r in result['records']:
  assert sum(m['trades'] for m in r['months'].values())==r['net']['trades']
  assert abs(sum(m['net_usd'] for m in r['months'].values())-r['net']['net_usd'])<1e-7
  assert abs(sum(t['net_profit'] for t in r['trades'])-r['net']['net_usd'])<1e-7
  for t in r['trades']:assert math.isfinite(t['net_profit']) and t['volume']>0 and t['holding_hours']>=0
  assert r['net']['max_win_streak']<=r['net']['trades'] and r['net']['max_loss_streak']<=r['net']['trades']
 # Independently compare the MQL US-DST formula against the timezone database,
 # including UTC hours surrounding both transitions.
 checks=0;ny=ZoneInfo('America/New_York')
 for year in (2025,2026):
  def sunday(month,nth):
   first=datetime(year,month,1,tzinfo=timezone.utc)
   return 1+(6-first.weekday())%7+(nth-1)*7
  begin=datetime(year,3,sunday(3,2),7,tzinfo=timezone.utc)
  end=datetime(year,11,sunday(11,1),6,tzinfo=timezone.utc)
  for transition in (begin,end):
   for hours in range(-12,13):
    t=transition+timedelta(hours=hours)
    mql=(t+timedelta(hours=-4 if begin<=t<end else -5)).replace(tzinfo=None)
    assert mql==t.astimezone(ny).replace(tzinfo=None);checks+=1
 inputs=Path(r'C:\Users\hama101\.codex-remote-attachments\019fcad5-6b3d-7de2-b1b2-01580f22a7c0\a43d350c-a054-438b-8ef7-d89d7428bc9c')
 source_images={str(p):digest(p) for p in sorted(inputs.glob('*.jpg'))};assert len(source_images)==3
 out=dict(ok=True,native_reports=12,primary_year_runs=4,control_year_runs=4,smokes=4,
  tested_strategy_definitions=4,optimized=False,trades_audited=sum(audit.load(p.parent/'AUDIT.json')['trades_checked'] for p in reports),
  clock_transition_checks=checks,monthly_ledgers_reconciled=8,source_hashes_verified=True,
  source_screenshots=source_images,
  limitations=['73% real tick coverage','Broker clock convention inferred, not source-broker verified',
   'Scheduled exits can be delayed by native broker session specification or holidays',
   'No-stop strategies use notional sizing, not capped stop risk','One year and small US30 sample do not establish robustness'])
 audit.runner.save(ROOT/'FINAL_CHECKS.json',out);print(json.dumps(out,indent=2))
if __name__=='__main__':main()
