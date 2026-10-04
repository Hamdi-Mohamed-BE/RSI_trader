"""Independent native fill clock, net profit and bar/native reconciliation."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
root=Path(__file__).resolve().parent;rows=json.loads((root/'NATIVE SUMMARY.json').read_text());checks=[]
bars=pd.read_csv(root/'hourly-trades.csv');summ=pd.read_csv(root/'hourly-summary.csv')
for r in rows:
 name=r['manifest']['window'];d=pd.DataFrame(json.loads((root/'native'/name/'trades.json').read_text()));f=pd.read_csv(root/'native'/name/'fills.csv.gz');op=pd.to_datetime(d.open_time,utc=True);cl=pd.to_datetime(d.close_time,utc=True)
 ony=op.dt.tz_convert('America/New_York');cny=cl.dt.tz_convert('America/New_York')
 assert ((ony.dt.hour==11)&(ony.dt.minute==0)).all()
 assert ((cny.dt.hour==12)&(cny.dt.minute==0)).all()
 assert (ony.dt.date==cny.dt.date).all() and not ony.dt.date.duplicated().any()
 assert (d.volume==1).all() and (d.side=='Long').all() and (d.swap==0).all()
 assert (f.retcode==10009).all() and len(f)==2*len(d)
 # CFD contract/tick specs are $1/index point/lot.
 assert np.max(abs(d.close_price-d.open_price-d.gross_profit))<.011
 assert np.max(abs(d.gross_profit+d.commission+d.swap-d.net_profit))<.011
 assert abs(d.net_profit.sum()-r['metrics']['net_profit'])<.01
 # MT5's displayed Profit Trades includes gross breakeven trades; the report
 # below consistently uses strictly positive net deal P&L after commissions.
 assert abs((d.gross_profit>=0).mean()*100-r['metrics']['win_rate_pct'])<.011
 buy=f[f.action=='BUY'];sell=f[f.action=='CLOSE'];assert len(buy)==len(d)==len(sell)
 assert np.max(abs(buy.result_price.to_numpy()-d.open_price.to_numpy()))<.011
 assert np.max(abs(sell.result_price.to_numpy()-d.close_price.to_numpy()))<.011
 d['date']=ony.dt.strftime('%Y-%m-%d');start=r['manifest']['start'].replace('.','-');end=r['manifest']['end'].replace('.','-')
 approximate=bars[(bars.hour==11)&(bars.date>=start)&(bars.date<end)]
 merged=d.merge(approximate,on='date',how='inner');common_difference=float((merged.gross_profit-merged.net_points).sum());approx_net=float(approximate.net_points.sum());actual_net=float(d.net_profit.sum())
 # Exact reconciliation: shared-date quote/execution changes, additional native
 # days excluded by full-minute-bar requirement, and broker deal costs.
 extra=float(d[~d.date.isin(approximate.date)].gross_profit.sum());missing=float(approximate[~approximate.date.isin(d.date)].net_points.sum());cost=float(d.commission.sum()+d.swap.sum())
 assert abs(actual_net-(approx_net+common_difference+extra-missing+cost))<1e-6
 checks.append(dict(window=name,trades=len(d),bar_trades=len(approximate),shared_days=len(merged),extra_native_days=int((~d.date.isin(approximate.date)).sum()),missing_native_days=int((~approximate.date.isin(d.date)).sum()),bar_net_before_commission=approx_net,quote_execution_difference_shared_days=common_difference,extra_days_gross=extra,missing_days_bar_net=missing,commission=cost,native_net=actual_net,median_entry_quote_spread=float((buy.ask-buy.bid).median()),mean_entry_quote_spread=float((buy.ask-buy.bid).mean()),entry_spread_zero_fraction=float((buy.ask==buy.bid).mean()),max_hold_seconds=float((cl-op).dt.total_seconds().max()),min_hold_seconds=float((cl-op).dt.total_seconds().min()),verified_native_pf=float(d.net_profit[d.net_profit>0].sum()/-d.net_profit[d.net_profit<0].sum())))
result=dict(verified_native_rows=sum(z['trades'] for z in checks),windows=len(checks),no_wrong_hour_or_side=True,all_fills_successful=True,reconciliation=checks)
(root/'NATIVE VERIFICATION.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
