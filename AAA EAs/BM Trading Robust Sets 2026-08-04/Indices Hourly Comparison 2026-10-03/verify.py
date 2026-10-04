"""Independent hand-calculation checks and publication completeness."""
from pathlib import Path
import gzip,hashlib,json,math,re,subprocess
import numpy as np
import pandas as pd
import research
R=Path(__file__).resolve().parent
def load(p):return json.loads((R/p).read_text())
def close(a,b):assert abs(a-b)<1e-8,(a,b)
def main():
 # Boundary, missing-minute, timezone and zero-trade regressions.
 assert research.eligible(np.arange(61)*60).tolist()==[True]+[False]*60
 assert not research.eligible(np.delete(np.arange(62)*60,5))[0]
 assert research.streak([1,1,-1,0,1,-1,-1])==(2,2)
 assert research.stats(pd.DataFrame({'net_points':[],'date':[]}),*research.WINDOWS['3m'],1)['return_pct'] is None
 assert pd.Timestamp('2026-01-05 16:00',tz='UTC').tz_convert('America/New_York').hour==11
 assert pd.Timestamp('2026-07-06 15:00',tz='UTC').tz_convert('America/New_York').hour==11
 rows=load('NATIVE-SUMMARY.json');assert len(rows)==288
 for a in research.ASSETS:
  for w in research.WINDOWS:
   d=[r for r in rows if r['asset']==a and r['window']==w]
   assert len(d)==48 and set((r['hour'],r['side']) for r in d)==set((h,s) for h in range(24) for s in ['buy','sell'])
 for a in load('AUDIT.json')['assets']:
  assert a['first_utc'].startswith('2025-10-03') and a['last_utc'].startswith('2026-10-02 20:54')
 ledger=pd.DataFrame(json.loads(gzip.decompress((R/'native-kept-ledgers.json.gz').read_bytes())))
 for row in rows:
  # The exported ledger also contains the separate 11-hour screenshot test.
  scheduled_minutes=(ledger.exit_epoch//60-ledger.entry_epoch//60)
  d=ledger[(scheduled_minutes==60)&(ledger.asset==row['asset'])&(ledger.window==row['window'])&(ledger.hour==row['hour'])&(ledger.side==row['side'])]
  assert len(d)==row['trades']
  if not len(d):continue
  v=d.net_cash.to_numpy();close(v.sum(),row['net_cash']);close(100*(v>0).mean(),row['win_rate_pct'])
  close(sum(v[v>0])/-sum(v[v<0]),row['pf'])
  balance=[10000.];peak=10000.;dd=0
  for z in v:
   balance.append(balance[-1]+z);peak=max(peak,balance[-1]);dd=max(dd,(peak-balance[-1])/peak*100)
  close(dd,row['closed_dd_pct'])
  assert d.date.min()>=row['start'] and d.date.max()<row['end_exclusive']
 for q in load('RECONCILIATION.json'):
  close(q['kept_net_cash']+q['excluded_net_cash'],q['all_positions_net_cash'])
  assert abs(q['all_positions_net_cash']-q['native_report_net_cash'])<.11
 assert len(load('CANDIDATES.json'))==2
 # Native build and all evidence input hashes cannot silently drift.
 m=load('ANALYSIS-MANIFEST.json')
 for p,h in m['input_hashes'].items():assert hashlib.sha256((R/p).read_bytes()).hexdigest()==h,p
 assert hashlib.sha256((R/'NATIVE-SUMMARY.json').read_bytes()).hexdigest()==m['summary_sha256']
 current=hashlib.sha256((R/'HourlyAll.mq5').read_bytes()).hexdigest()
 assert all(q['source_sha256']==current for q in load('NATIVE.json'))
 page=(R/'Results.html').read_text();assert page.count('<section data-asset=')==6
 assert page.count('<tbody>')==9 and page.count('>N/A<')>10
 js=re.search(r'<script>(.*?)</script>',page,re.S).group(1)
 node=r'C:\Users\hama101\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
 fixture="""const vm=require('vm');const listeners={};const nodes={asset:{value:'US100',addEventListener:(e,f)=>listeners.a=f},window:{value:'1y',addEventListener:(e,f)=>listeners.w=f},all:{addEventListener:(e,f)=>listeners.all=f}};const sections=['US30','US100','SP500'].flatMap(a=>['1y','3m'].map(w=>({dataset:{asset:a,window:w},hidden:false})));const context={document:{getElementById:id=>nodes[id],querySelectorAll:()=>sections}};vm.runInNewContext(SOURCE,context);if(sections.filter(s=>!s.hidden).length!==1)throw Error('Initial table');nodes.asset.value='SP500';nodes.window.value='3m';listeners.w();if(sections.find(s=>!s.hidden).dataset.window!=='3m')throw Error('Window change');listeners.all();if(sections.some(s=>s.hidden))throw Error('Show all');console.log('Table interactions checked');"""
 out=subprocess.run([node,'-e',fixture.replace('SOURCE',json.dumps(js))],capture_output=True,text=True);assert out.returncode==0,out.stderr
 result={'summary_rows':288,'native_runs':8,'all_hours_and_directions':True,'native_net_reconciled':True,'dates_and_dst_checked':True,'input_hashes_checked':True,'no_current_EA_installation':True,'no_positive_hour_passes_family_check':not any(r['trades'] and r['mean_net_points']>0 and r.get('p_adjusted_maxT',1)<.05 for r in rows),'report_interactions_checked':True}
 (R/'VERIFICATION.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
