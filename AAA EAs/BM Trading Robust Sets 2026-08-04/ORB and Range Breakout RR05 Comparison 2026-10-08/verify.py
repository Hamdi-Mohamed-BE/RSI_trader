"""Independent cash/trade/input/target/provenance checks on completed research pairs."""
from pathlib import Path
from collections import defaultdict
from decimal import Decimal as D
import csv, hashlib, json, math

ROOT=Path(__file__).resolve().parent
PRIOR=ROOT.parent/'US100 H1 ORB RR05 Comparison 2026-10-08/Agent3010'

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def close(a,b,tol=1e-8):assert a is None and b is None or a is not None and b is not None and abs(a-b)<tol,(a,b)

def verify_case(folder,value):
 with (folder/'deals.csv').open(encoding='utf-8-sig') as stream:deals=list(csv.DictReader(stream))
 positions=defaultdict(list);seen=set()
 for d in deals:
  assert d['deal'] not in seen;seen.add(d['deal']);positions[d['position_id']].append(d)
 profits=[];target_ratios=[];net=D(0)
 for items in positions.values():
  entries=[x for x in items if int(x['entry'])==0];exits=[x for x in items if int(x['entry'])==1]
  assert len(entries)==1 and exits
  entry=entries[0]
  assert sum(D(x['volume']) for x in exits)==D(entry['volume'])
  assert all(x['type']!=entry['type'] for x in exits)
  pnl=sum((sum(D(x[k]) for k in ['gross','commission','swap','fee']) for x in items),D(0))
  profits.append((int(exits[-1]['epoch']),int(exits[-1]['deal']),float(pnl)))
  net+=pnl
  if 'sl' in entry and 'tp' in entry:
   ep,sl,tp=[float(entry[k]) for k in ['price','sl','tp']]
   if sl and tp and ep!=sl:target_ratios.append(abs(tp-ep)/abs(ep-sl))
 profits.sort();wins=[x[2] for x in profits if x[2]>0];losses=[x[2] for x in profits if x[2]<0]
 m=value['metrics'];close(float(net),m['net_profit'],.031);close(float(net),value['native']['net_profit'],.031)
 close(float(net)/100,m['return_pct'])
 assert len(profits)==m['trades'] and len(wins)==m['wins'] and len(losses)==m['losses']
 close(sum(wins)/-sum(losses) if losses else None,m['pf'])
 close(100*len(wins)/len(profits) if profits else None,m['win_rate'])
 close(sum(wins)/len(wins) if wins else None,m['avg_win'])
 close(sum(losses)/len(losses) if losses else None,m['avg_loss'])
 w=l=mw=ml=0
 for _,_,p in profits:w=w+1 if p>0 else 0;l=l+1 if p<0 else 0;mw=max(mw,w);ml=max(ml,l)
 assert (mw,ml)==(m['win_streak'],m['loss_streak'])
 assert sha(folder/'report.htm')==value['report_sha256']
 ordered=sorted(target_ratios)
 return dict(positions=len(profits),cash=float(net),target_ratios_count=len(ordered),
  target_ratio_min=min(ordered) if ordered else None,target_ratio_max=max(ordered) if ordered else None,
  target_ratio_median=ordered[len(ordered)//2] if ordered else None,
  broker_error_flags=value.get('flags',{}),unsupported_set_inputs=value.get('unsupported_set_inputs',[]))

def main():
 plan=read(ROOT/'PLAN.json');output=[]
 for row in plan['setups']:
  file=ROOT/'comparisons'/(row['slug']+'.json')
  if not file.exists():continue
  pair=read(file);cases={}
  for kind in ['current','half']:
   value=pair[kind];folder=(PRIOR if pair.get('reused_verified_comparison') else ROOT)/'native'/value['tag']
   cases[kind]=verify_case(folder,value)
   assert float(value['inputs']['InpRiskPercent'])==1
   assert value['inputs'].get('InpAdaptivePortfolioControls','false')=='false'
  if not pair.get('reused_verified_comparison'):
   differences={k for k in pair['current']['inputs'] if pair['current']['inputs'][k]!=pair['half']['inputs'].get(k) and k!='InpRR05AuditTag'}
   assert differences and differences<=set(row['candidate_overrides']),differences
   assert all(float(pair['half']['inputs'][k])==float(v) for k,v in row['candidate_overrides'].items())
   assert pair['current']['binary_sha256']==pair['half']['binary_sha256']
  assert all(sha(Path(p))==digest for p,digest in row['production_hashes'].items())
  output.append(dict(slug=row['slug'],cases=cases,production_hashes_unchanged=True))
 summary=dict(verified=len(output),total=len(plan['setups']),cash_trades_streaks_inputs_and_provenance_verified=True,cases=output)
 (ROOT/'INDEPENDENT_CHECK.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
 print(json.dumps(dict(verified=len(output),total=len(plan['setups']),checks_passed=True,
  cases=[dict(slug=x['slug'],half_target_median=x['cases']['half']['target_ratio_median'],
    flags=x['cases']['half']['broker_error_flags']) for x in output]),indent=2))

if __name__=='__main__':main()
