"""Fresh original-source replay to separate broker cost drift from logic parity."""
import shutil
import raw_runner as rr
import runner as r
def main():
 rr.prepare()
 for bot,slug in [('gold','gp-xauusd-eighth-rejection-3y'),('us100','gp-ustec-time-cycle-3y'),('btc','gp-btcusd-quartile-control-3y')]:
  row=next(x for x in rr.cases() if x['slug']==slug)
  row=row|dict(slug='gp-fresh-original-'+bot+'-parity')
  row['input_settings']=row['input_settings']|dict(InpSignalAuditTag=row['slug'])
  rr.n.START=row['start'];rr.n.END=rr.CFG['end_exclusive'].replace('-','.')
  binary,info=rr.n.build(row);q=rr.n.run_case(row,'raw',binary,info)
  folder=r.R/'native'/q['tag'];shutil.copy2(rr.g.SIGNALS/(row['slug']+'.csv'),folder/'signals.csv')
  rr.audit(q,folder);r.save(folder/'results.json',q)
if __name__=='__main__':
 with r.lease():main()
