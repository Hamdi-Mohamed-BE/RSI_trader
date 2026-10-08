"""Independent reconciliation checks; read-only with respect to native results."""
import math
from pathlib import Path
from bs4 import BeautifulSoup
import runner as r,build_engine as e
R=r.R

def main():
 frozen=r.load(R/'FROZEN.json');checks=0;passes=0
 development=r.load(R/'DEVELOPMENT TABLE.json')
 assert len({r.digest(x['parameters']) for x in development})==frozen['unique_tested_configurations'];checks+=1
 for path in sorted((R/'native').glob('*/results.json')):
  manifest=r.load(path.parent/'manifest.json');rows=r.load(path)
  assert len(rows)==len(manifest['cases']);checks+=1
  for row,case in zip(rows,manifest['cases']):
   assert row['parameters']==case;checks+=1
   ts=row['trades'];xs=[t['net_profit'] for t in ts];net=sum(xs)
   wins=sum(x>0 for x in xs);loss=-sum(x for x in xs if x<0);gp=sum(x for x in xs if x>0)
   m=row['metrics'];native=row['native']
   assert len(ts)==m['trades']==int(native['trades']);checks+=1
   assert math.isclose(net,m['net'],abs_tol=1e-6);checks+=1
   assert math.isclose(net,native['net'],abs_tol=.03);checks+=1
   assert math.isclose(native['balance'],10000+net,abs_tol=.03);checks+=1
   assert math.isclose(m['return_pct'],net/100,abs_tol=1e-6);checks+=1
   assert math.isclose(m['win_rate_pct'],100*wins/len(xs),abs_tol=1e-6) if xs else m['win_rate_pct']==0;checks+=1
   assert math.isclose(m['pf'],gp/loss,abs_tol=1e-9) if loss else m['pf'] is None;checks+=1
   assert not native['open_position'];checks+=1
   assert row['model']==manifest['model'];checks+=1
   passes+=1
  if manifest['start']>='2024-01-01':
   assert path.parent.joinpath('manifest.json').stat().st_mtime>=R.joinpath('FROZEN.json').stat().st_mtime;checks+=1
   assert all(c==e.RAW or c==frozen['parameters'] for c in manifest['cases']);checks+=1
 parity=r.load(R/'PARITY.json');assert parity['exact'] and parity['mismatches']==[];checks+=1
 assert e.fingerprints()==r.load(R/'SOURCE AUDIT.json')['source_fingerprints'];checks+=1
 html=BeautifulSoup((R/'Results.html').read_text(encoding='utf-8'),'html.parser')
 assert html.h1 and len(html.find_all('table'))>=12 and html.svg;checks+=1
 assert not html.find_all('script');checks+=1
 assert len(html.find_all('th',string='Daily equity Sharpe'))>=1;checks+=1
 summary=r.load(R/'SUMMARY.json');audit=r.load(R/'AUDITS.json')
 assert summary['candidate_oos']==audit['OOS candidate']['metrics'];checks+=1
 assert summary['baseline_oos']==audit['OOS baseline']['metrics'];checks+=1
 assert summary['candidate_audit']['monte_carlo']['paths']==10000;checks+=1
 assert audit['proof']['production_unchanged'];checks+=1
 proof=dict(checks=checks,native_passes_reconciled=passes,unique_configurations=frozen['unique_tested_configurations'],
  parity=True,production_unchanged=True,html_structure_valid=True,holdout_after_freeze=True,
  browser_visual_check='not performed: supported browser policy blocks file URLs; no alternate-browser or local-server workaround attempted')
 r.save(R/'VERIFICATION.json',proof);print(proof)

if __name__=='__main__':main()
