"""Causal, cash-funded daily SMA200 replication; no fitting."""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parent
START=pd.Timestamp('2010-10-02');END=pd.Timestamp('2026-10-02')
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False,default=str),encoding='utf-8')
def load(symbol):
 path=ROOT/'data/us_stock'/f'{symbol}_2009-01-01_to_2026-10-02.csv';d=pd.read_csv(path,parse_dates=['date']).set_index('date').sort_index()
 assert d.index.is_unique
 fields=['open','high','low','close','adj_close'];null=d[fields].isna()
 assert not (null.any(axis=1)&~null.all(axis=1)).any(),'Partial missing OHLC'
 dropped=int(null.all(axis=1).sum());d=d[~null.all(axis=1)].copy()
 assert (d[fields]>0).all().all();assert ((d.high>=d[['open','close','low']].max(axis=1)-1e-5)&(d.low<=d[['open','close','high']].min(axis=1)+1e-5)).all()
 assert d.index.max()==pd.Timestamp('2026-10-01'),'Not the requested complete final day'
 d['adjusted_open']=d.open*d.adj_close/d.close;d['sma']=d.adj_close.rolling(200,min_periods=200).mean()
 manifest={'source':'ai_trader fetch_market_data daily CSV','sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'rows_valid':len(d),'missing_calendar_rows_removed':dropped,'first_valid':str(d.index.min().date()),'last_valid':str(d.index.max().date()),'first_sma':str(d.sma.first_valid_index().date()),'sma_window':200,'splits_and_dividends':'adj_close/close adjustment factor applied once to open; adjusted synthetic reinvested total-return series'}
 save(ROOT/'data'/f'{symbol}-manifest.json',manifest);return d
def states(d):
 out=[];held=False
 for x in d.itertuples():
  if np.isnan(x.sma):held=False
  elif x.adj_close>x.sma:held=True
  elif x.adj_close<x.sma:held=False
  out.append(held)
 return pd.Series(out,index=d.index,dtype=bool)
def runs(p):
 bestwin=bestloss=w=l=0
 for x in p:
  if x>0:w+=1;l=0;bestwin=max(bestwin,w)
  elif x<0:l+=1;w=0;bestloss=max(bestloss,l)
  else:w=l=0
 return bestwin,bestloss
def backtest(d,start,end=END,cost_bps=0,timing='next_open'):
 wanted=states(d)
 if timing=='next_open':wanted=wanted.shift(1,fill_value=False)
 else:assert timing=='same_close'
 z=d[(d.index>=start)&(d.index<end)].copy();target=wanted.reindex(z.index)
 cash=10000.;qty=0.;entry=None;trades=[];equity=[];fee=cost_bps/10000
 for date,x in z.iterrows():
  price=x.adjusted_open if timing=='next_open' else x.adj_close
  if target.loc[date] and qty==0:
   before=cash;qty=cash/(price*(1+fee));cash=0.;entry={'entry_date':date,'entry_signal_date':d.index[d.index.get_loc(date)-1] if timing=='next_open' else date,'entry_price':price,'capital_at_entry':before,'qty':qty,'entry_fee':qty*price*fee}
  elif not target.loc[date] and qty>0:
   cash=qty*price*(1-fee);trades.append(entry|{'exit_date':date,'exit_signal_date':d.index[d.index.get_loc(date)-1] if timing=='next_open' else date,'exit_price':price,'exit_fee':qty*price*fee,'net_profit':cash-entry['capital_at_entry'],'trade_return_pct':100*(cash/entry['capital_at_entry']-1),'capital_after_exit':cash});qty=0.;entry=None
  equity.append({'date':date,'equity':cash+qty*x.adj_close,'cash':cash,'qty':qty,'held':qty>0,'signal':bool(target.loc[date]),'close':x.adj_close,'sma':None if np.isnan(x.sma) else x.sma})
 eq=pd.DataFrame(equity).set_index('date');t=pd.DataFrame(trades);p=t.net_profit.to_numpy() if len(t) else np.array([])
 e=eq.equity.to_numpy();peak=np.maximum.accumulate(np.r_[10000,e])[1:];dd=100*(peak-e)/peak
 daily=pd.Series(np.r_[e[0]/10000-1,e[1:]/e[:-1]-1]);sd=daily.std(ddof=1);sharpe=float(daily.mean()/sd*np.sqrt(252)) if sd>0 else None
 years=(eq.index[-1]-eq.index[0]).days/365.2425;gp=p[p>0].sum();gl=-p[p<0].sum();mw,ml=runs(p)
 out={'requested_start':str(pd.Timestamp(start).date()),'first_session':str(eq.index[0].date()),'last_session':str(eq.index[-1].date()),'timing':timing,'cost_bps_per_side':cost_bps,'initial_balance':10000,'final_marked_equity':float(e[-1]),'return_pct':float((e[-1]/10000-1)*100),'cagr_pct':float(((e[-1]/10000)**(1/years)-1)*100),'max_daily_close_equity_dd_pct':float(dd.max()),'sharpe_daily_252':sharpe,'closed_trades':len(p),'win_pct':float((p>0).mean()*100) if len(p) else None,'net_pf_closed_trades':float(gp/gl) if gl else None,'max_win_streak':mw,'max_loss_streak':ml,'exposure_pct':float(eq.held.mean()*100),'final_open_position':bool(qty>0),'open_position_unrealized_net':float(e[-1]-entry['capital_at_entry']) if entry else 0.,'fees_paid':float(t[['entry_fee','exit_fee']].sum().sum() if len(t) else 0)+(entry['entry_fee'] if entry else 0),'eligible_sessions':int(z.sma.notna().sum())}
 eq['dd_pct']=dd;return out,eq,t
def benchmark(d,start,end=END):
 z=d[(d.index>=start)&(d.index<end)];e=10000*z.adj_close/z.adjusted_open.iloc[0];peak=np.maximum.accumulate(np.r_[10000,e])[1:]
 return {'return_pct':float((e.iloc[-1]/10000-1)*100),'max_daily_close_dd_pct':float((100*(peak-e)/peak).max()),'final_equity':float(e.iloc[-1])}
def main():
 data={s:load(s) for s in ['QQQ','TQQQ']};common=max(START,max(d.sma.first_valid_index()+pd.Timedelta(days=1) for d in data.values()));rows=[]
 for symbol,d in data.items():
  for label,start in [('16y',START),('common-start',common),('5y',pd.Timestamp('2021-10-02')),('3y',pd.Timestamp('2023-10-02')),('1y',pd.Timestamp('2025-10-02'))]:
   for suffix,cost,timing in [('baseline',0,'next_open')]+([('cost-5bp',5,'next_open'),('same-close',0,'same_close')] if label=='16y' else []):
    key=f'{symbol}-{label}-{suffix}';stats,eq,trades=backtest(d,start,cost_bps=cost,timing=timing);stats.update(symbol=symbol,window=label,key=key,buy_hold=benchmark(d,start))
    out=ROOT/'etf'/key;out.mkdir(parents=True,exist_ok=True);eq.to_csv(out/'equity.csv');trades.to_csv(out/'trades.csv',index=False);save(out/'stats.json',stats);rows.append(stats)
 save(ROOT/'ETF RESULTS.json',rows);save(ROOT/'ETF DATA LOCK.json',{'common_eligible_start':str(common.date()),'protocol_sha256':hashlib.sha256((ROOT/'PROTOCOL.txt').read_bytes()).hexdigest(),'data':{s:json.loads((ROOT/'data'/f'{s}-manifest.json').read_text()) for s in data}})
 print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
