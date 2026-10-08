"""Post-freeze evidence audit and offline report; no parameter selection here."""
from pathlib import Path
from datetime import datetime
import gzip,html,importlib.util,math,re
import numpy as np,pandas as pd
import runner as r,build_engine as e
R=r.R;C=r.CONFIG
EQUITY_CACHE={}
spec=importlib.util.spec_from_file_location('calyx_evidence_audit',R.parent.parent/'Calyx Research Pipeline/calyx_pipeline.py')
# dataclasses require the imported module to be registered.
import sys
a=importlib.util.module_from_spec(spec);sys.modules[spec.name]=a;spec.loader.exec_module(a)

def path_for(row,suffix):return R/'native'/row['stage']/(str(row['index'])+'-'+suffix+'.csv.gz')

def equity(row):
 identity=(row['stage'],row['index'],path_for(row,'equity').stat().st_mtime_ns)
 if identity in EQUITY_CACHE:return EQUITY_CACHE[identity]
 df=pd.read_csv(path_for(row,'equity'))
 assert not df.empty and df.epoch.is_monotonic_increasing
 assert abs(float(df.iloc[-1].balance)-10000-row['metrics']['net'])<.03
 df['day']=pd.to_datetime(df.epoch,unit='s').dt.normalize()
 observed_end=min(pd.Timestamp(row['end'])-pd.Timedelta(days=1),pd.Timestamp(row['native']['last_quote_epoch'],unit='s').normalize())
 dates=pd.date_range(row['start'],observed_end)
 end=df.groupby('day')[['balance','equity']].last().reindex(dates).ffill().fillna(10000)
 # Every final position is liquidated by MT5 before OnTester. Native DD
 # covers every tick; this one-minute path is not a replacement for it.
 ret=end.equity.pct_change().fillna(end.equity.iloc[0]/10000-1)
 EQUITY_CACHE.clear();EQUITY_CACHE[identity]=(df,end,ret)
 return df,end,ret

def monte_carlo(pnl,returns,seed):
 """Circular five-observation blocks, 10k paths, bounded memory."""
 rng=np.random.default_rng(seed);paths=10000;block=5
 def indices(length):
  starts=rng.integers(0,length,size=(paths,math.ceil(length/block)))
  return ((starts[:,:,None]+np.arange(block))%length).reshape(paths,-1)[:,:length]
 p=np.asarray(pnl,float);rs=np.asarray(returns,float)
 sampled=p[indices(len(p))];gp=np.maximum(sampled,0).sum(axis=1);gl=-np.minimum(sampled,0).sum(axis=1)
 pfs=np.divide(gp,gl,out=np.full(paths,np.nan),where=gl>0)
 x=rs[indices(len(rs))];curves=np.cumprod(np.maximum(0,1+x),axis=1)
 peaks=np.maximum.accumulate(np.concatenate([np.ones((paths,1)),curves],axis=1),axis=1)[:,1:]
 dd=np.max((peaks-curves)/peaks,axis=1)*100;final=(curves[:,-1]-1)*100
 def qs(z):return np.nanquantile(z,[.05,.5,.95]).tolist()
 return dict(paths=paths,block=block,seed=seed,return_p05_p50_p95=qs(final),pf_p05_p50_p95=qs(pfs),
  max_dd_p05_p50_p95=qs(dd),probability_profit_pct=float(np.mean(final>0)*100),
  daily_5pct_breach_proxy_pct=float(np.mean(np.any(x<=-.05,axis=1))*100),
  initial_balance_10pct_breach_proxy_pct=float(np.mean(np.any(curves<=.9,axis=1))*100),
  scope='Closed-balance daily returns / trade cash separately resampled in circular five-observation blocks. Monte Carlo omits floating/intraday extrema and does not resize/reexecute synthetic trades. Breaches are closed-P&L proxies, not FTMO challenge probabilities.')

def quote_cost(row):
 q=pd.read_csv(path_for(row,'quotes'));q=q[(q.entry==0)&(q.volume>0)&(q.spread_cash>=0)&(q.epoch>=pd.Timestamp('2026-01-02').timestamp())]
 if q.empty:return dict(status='unavailable',observations=0)
 cost=float((q.spread_cash/q.volume).median())
 if cost<=0:
  return dict(status='unavailable_zero_spread_quotes',observations=len(q),median_extra_usd_per_lot=0,
   scope='All sampled 2026 entry quotes have identical bid/ask. Charging another zero spread is not a meaningful stress test. No positive broker cost was invented; the mandatory extra-cost gate fails. Results may be optimistic if this feed does not represent executable spreads.')
 p=[t['net_profit']-cost*t['volume'] for t in row['trades']]
 return dict(status='measured_extra_spread_sensitivity',observations=len(q),median_extra_usd_per_lot=cost,
  mean_extra_usd_per_trade=float(np.mean([cost*t['volume'] for t in row['trades']])),net=sum(p),return_pct=sum(p)/100,pf=a.profit_factor(p),
  win_rate_pct=sum(v>0 for v in p)/len(p)*100,
  scope='One additional full quoted bid/ask spread per round trip, using the median entry spread cash per lot measured on available 2026 native real-tick quotes. Existing spread, commissions and swaps already remain in baseline P&L. Indicative widening sensitivity, not an exact rerun with widened quotes or a guaranteed future spread.')

def audit(row,trials,seed):
 df,daily,ret=equity(row);p=[t['net_profit'] for t in row['trades']];n=len(p)
 assert n>0
 wl=a.wilson_interval(sum(v>0 for v in p),n)
 # Follow the central policy's closed-P&L proxy; native floating DD and
 # daily-equity Sharpe are separately retained, never substituted by MC.
 cash=pd.Series(0.,index=daily.index)
 for t in row['trades']:cash.loc[pd.Timestamp(t['close_time']).normalize()]+=t['net_profit']
 balance=10000+cash.cumsum();closed_ret=cash/balance.shift(1).fillna(10000)
 mc=monte_carlo(p,closed_ret,seed);cost=quote_cost(row)
 outcomes=[a.TradeOutcome(datetime.fromisoformat(t['close_time']),t['net_profit']) for t in row['trades']]
 thirds=a.subperiods(outcomes);sharpe=a.sharpe_statistics(ret.tolist(),trials,365)
 half=a.profit_factor(p[len(p)//2:])
 sample_dd=float(np.max(1-df.equity/np.maximum.accumulate(np.maximum(10000,df.equity)))*100)
 gates=dict(minimum_30_trades=n>=30,positive_return=row['metrics']['net']>0,pf_above_1=(row['metrics']['pf'] or 0)>1,
  bootstrap_return_p05_positive=mc['return_p05_p50_p95'][0]>0,bootstrap_pf_p05_above_1=mc['pf_p05_p50_p95'][0]>1,
  deflated_sharpe_95pct=sharpe['deflated_sharpe_pct']>=95,recent_half_pf_above_1=half>1,
  two_of_three_chronological_parts_positive=sum(x['net_profit']>0 for x in thirds)>=2,
  total_breach_proxy_below_5pct=mc['initial_balance_10pct_breach_proxy_pct']<5,
  measured_cost_stress_pf_above_1=cost.get('pf',0)>1,native_floating_path_present=True)
 return dict(metrics=row['metrics'],wilson95_pct=[100*x for x in wl],monte_carlo=mc,sharpe=sharpe,recent_half_pf=half,
  thirds=thirds,cost_stress=cost,native_dd_pct=row['metrics']['equity_dd'],sampled_minute_dd_pct=sample_dd,
  daily_equity_expected_shortfall_95_pct=a.expected_shortfall(ret.tolist())*100,
  daily_closed_balance_expected_shortfall_95_pct=a.expected_shortfall(closed_ret.tolist())*100,
  gates=gates,all_gates_pass=all(gates.values()),
  verdict='PASS_FOR_FORWARD_RESEARCH' if all(gates.values()) else 'WATCH_ONLY' if row['metrics']['net']>0 and (row['metrics']['pf'] or 0)>1 else 'REJECT',
  live_promotion=False,deflated_sharpe_note='Uses central pipeline independent-trial approximation with every unique searched configuration; not a correction for all researcher choices or a promise of future Sharpe.')

def f(v,d=2):return '—' if v is None or not math.isfinite(float(v)) else f'{float(v):.{d}f}'
def pct(v):return f'{v:+.2f}%'
def esc(v):return html.escape(str(v))
def table(headers,rows):return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+esc(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'

def quality(row):
 if not (R/'native'/row['stage']/'report.htm.gz').exists():
  journal=gzip.decompress((R/'native'/row['stage']/'journal.txt.gz').read_bytes()).decode('utf-8',errors='replace')
  notes=sorted(set(x.strip() for x in re.findall(r'[^\r\n]*(?:real ticks|ticks data begins from)[^\r\n]*',journal,re.I)))
  return dict(history_quality='Model 4; native optimisation export (no per-pass HTML percentage)',real_tick_notes=notes,dynamic_helper_rejection_log_lines=0)
 raw=gzip.decompress((R/'native'/row['stage']/'report.htm.gz').read_bytes())
 text=raw.decode('utf-16') if raw[:2] in [b'\xff\xfe',b'\xfe\xff'] else raw.decode('utf-8',errors='replace')
 match=re.search(r'>\s*History Quality:\s*</td>\s*<td[^>]*>\s*<b>(.*?)</b>',text,re.I|re.S)
 history=html.unescape(re.sub('<[^>]+>','',match.group(1))).strip() if match else 'not reported'
 journal=gzip.decompress((R/'native'/row['stage']/'journal.txt.gz').read_bytes()).decode('utf-8',errors='replace')
 notes=sorted(set(x.strip() for x in re.findall(r'[^\r\n]*(?:real ticks|ticks data begins from)[^\r\n]*',journal,re.I)))
 return dict(history_quality=history,real_tick_notes=notes,dynamic_helper_rejection_log_lines=len(re.findall('Dynamic trailing SL modification failed',journal)))
