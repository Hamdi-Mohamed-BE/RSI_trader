"""Independent direct-deal reconciliation plus preservation/coverage audit."""
from __future__ import annotations
import hashlib,json,re,shutil
from collections import defaultdict
from pathlib import Path
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 b=p.read_bytes();return b.decode('utf-16') if b[:2] in (b'\xff\xfe',b'\xfe\xff') else b.decode('utf-8-sig')
def number(s):return float(s.replace(' ','').replace('\xa0','')) if s else 0.0
def main():
 meta=json.loads((ROOT/'manifest.json').read_text())
 assert len(meta['cases'])==12
 assert meta['rules_sha256']==sha(ROOT/'RULES.md')
 installer=read(ROOT.parent/'_Auto Deploy/Install-BMTradingPortfolio.ps1')
 evidence=[]
 snapshot=ROOT/'source-snapshot'
 snapshot_index={}
 for slug,item in meta['cases'].items():
  assert str(Path(item['preset']).relative_to(ROOT.parent)).replace('/','\\') in installer
  for f,digest in item['dependencies'].items():
   original=Path(f);assert sha(original)==digest,(slug,f)
   target=snapshot/original.relative_to(ROOT.parent)
   target.parent.mkdir(parents=True,exist_ok=True)
   if not target.exists():shutil.copy2(original,target)
   assert sha(target)==digest
   snapshot_index[f]=dict(snapshot=str(target.relative_to(ROOT)),sha256=digest)
  assert sha(Path(item['preset']))==item['preset_sha256']
  assert sha(ROOT/(slug+'.mq5'))==item['wrapper_sha256']
  assert sha(ROOT/(slug+'.ex5'))==item['binary_sha256']
  assert 'if(!StudyGuard())return INIT_FAILED' in read(ROOT/(slug+'.mq5'))
  assert '0 errors, 0 warnings' in read(ROOT/(slug+'.compile.log'))
  expected_overrides={'InpTesterServerClockMode':'0','InpResearchBrokerUtcOffsetMinutes':'0'} if slug=='dmc' else {}
  assert item['clock_overrides']==expected_overrides
  for key,value in item['original_params'].items():
   assert item['params'][key]==expected_overrides.get(key,value),(slug,key)
  p=ROOT/'native'/item['params']['InpStudyCase']
  if not (p/'summary.json').exists():continue
  summary=json.loads((p/'summary.json').read_text());trades=json.loads((p/'trades.json').read_text())
  report=p/(item['params']['InpStudyCase']+'.htm');assert sha(report)==summary['report_sha256']
  section=False;cash=commission=swap=gross=0;last_balance=10000;entries=exits=0;months=defaultdict(float)
  for row in BeautifulSoup(read(report),'html.parser').find_all('tr'):
   if row.get_text(' ',strip=True)=='Deals':section=True;continue
   if not section:continue
   cells=[' '.join(c.get_text(' ',strip=True).split()) for c in row.find_all('td')]
   if len(cells)!=13 or not re.fullmatch(r'\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}',cells[0]):continue
   if cells[3]=='balance':continue
   assert cells[2]=='US500' and cells[4] in ('in','out'),cells
   c,s,g=map(number,(cells[8],cells[9],cells[10]));cash+=c+s+g;commission+=c;swap+=s;gross+=g
   last_balance=number(cells[11]);assert abs(last_balance-10000-cash)<.06
   entries+=cells[4]=='in';exits+=cells[4]=='out'
  assert entries==exits==len(trades)==summary['trades']
  assert abs(cash-summary['net_profit'])<.08
  assert abs(cash-sum(t['net_profit'] for t in trades))<.08
  assert abs(commission-summary['commission'])<.06 and abs(swap-summary['swap'])<.06
  assert abs(last_balance-summary['final_balance'])<.06
  assert summary['max_drawdown_pct']>=summary['native_equity_dd_pct']
  assert summary['max_drawdown_pct']>=summary['tick_observed_equity_dd_pct']
  for t in trades:
   assert '2025-09-19'<=t['open_time']<'2026-09-19'
   assert t['open_time']<=t['close_time']<'2026-09-19'
   assert t['initial_risk_usd'] and t['initial_risk_usd']>0
   months[t['close_time'][:7]]+=t['net_profit']
  for m in summary['months']:assert abs(months[m['month']]-m['net_profit'])<.03
  evidence.append(dict(slug=slug,trades=len(trades),net_profit=round(cash,2),commission=round(commission,2),swap=round(swap,2),history_quality=summary['history_quality'],status='passed'))
 result=dict(status='passed' if len(evidence)==12 else 'partial',complete=len(evidence),expected=12,checks=['12 installer-backed active presets','all original source/include/SET hashes unchanged','all wrapper binaries match manifest','tester-only guard','only DMC broker-clock overrides','zero-error zero-warning compilation','direct native Deals cash flow and balance reconciliation','entry/exit counts and trade ledger reconciliation','commission and swap reconciliation','date window and original protective-stop checks','monthly reconciliation','conservative floating-equity drawdown'],cases=evidence)
 (ROOT/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 (ROOT/'source-snapshot.json').write_text(json.dumps(snapshot_index,indent=2),encoding='utf-8')
 (ROOT/'VERIFICATION.md').write_text('# Transfer audit\n\n'+f"Status: {result['status']}; {len(evidence)} of 12 native cases reconciled.\n\n"+'\n'.join('- '+s for s in result['checks'])+'\n',encoding='utf-8')
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
