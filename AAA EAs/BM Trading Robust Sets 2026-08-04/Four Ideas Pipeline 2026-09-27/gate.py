"""Frozen stage-4 decision. No optimization, risk scaling, or ranking after the fact."""
import pipeline as p
import json,gzip
def load(path):return json.loads(path.read_text())
def main():
 rows=[];decisions=[]
 for i,c in enumerate(p.CASES[:4]):
  checks=[]
  for period in ('6m','1y','3y','5y'):
   folder=p.RAW/'native'/c['id'] if period=='1y' else p.ROOT/'native'/f"{c['id']}-{period}-m4"
   if not (folder/'AUDIT.json').exists():continue
   r=load(folder/'run.json');a=load(folder/'AUDIT.json');trades=load(folder/'trades.json')
   row=dict(id=c['id'],label=c['label'],period=period,**a['net'],equity_dd_pct=r['metrics']['max_equity_dd_pct'],quality=r['metrics']['history_quality'],late_exits=len(a['late_exits']),first_trade=trades[0]['open_time'] if trades else None,last_trade=trades[-1]['close_time'] if trades else None,report_sha=r['report_sha'],source=str(folder))
   journal=gzip.decompress((folder/'journal.txt.gz').read_bytes()).decode()
   row['history_warnings']=sorted(set(line.split('\t')[-1] for line in journal.splitlines() if any(w in line.lower() for w in ('start time changed','not enough history','no history data'))))
   if period in ('3y','5y'):
    control=p.ROOT/'native'/f"{p.CASES[i+4]['id']}-{period}-m4"
    if (control/'AUDIT.json').exists():
     cr=load(control/'run.json');ca=load(control/'AUDIT.json')
     score=row['return_pct']/row['equity_dd_pct'] if row['equity_dd_pct'] else 0
     cs=ca['net']['return_pct']/cr['metrics']['max_equity_dd_pct'] if cr['metrics']['max_equity_dd_pct'] else 0
     tests=dict(positive=row['net_usd']>0,pf=(row['profit_factor'] or 0)>=1.15,trades=row['trades']>=30,control=score>cs,history_no_fatal_warning=not row['history_warnings'])
     row.update(control_return_pct=ca['net']['return_pct'],control_equity_dd_pct=cr['metrics']['max_equity_dd_pct'],control_pf=ca['net']['profit_factor'],return_dd=score,control_return_dd=cs,tests=tests)
     checks.append(dict(period=period,**tests))
   rows.append(row)
  full=len(checks)==2
  passed=full and all(all(v for k,v in x.items() if k!='period') for x in checks)
  decisions.append(dict(id=c['id'],status='PASS_NUMERIC_GATE' if passed else 'FAIL' if full else 'PENDING',checks=checks,optimization_allowed=passed))
 result=dict(decisions=decisions,rows=rows,all_confirmed=all(x['status']!='PENDING' for x in decisions),control_criterion=p.freeze()['gate']['control'])
 p.save(p.ROOT/'GATE.json',result)
 print(json.dumps(decisions,indent=2))
if __name__=='__main__':main()
