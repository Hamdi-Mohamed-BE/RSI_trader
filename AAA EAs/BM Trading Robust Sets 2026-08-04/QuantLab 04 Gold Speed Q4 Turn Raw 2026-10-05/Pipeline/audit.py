"""Exact native deal audit and empirical robustness; no terminal/account API."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
from collections import defaultdict
import csv,gzip,hashlib,importlib.util,json,re,sys,statistics
import numpy as np
import pandas as pd
import search as n
R=n.ROOT
spec=importlib.util.spec_from_file_location('gold04raw',R.parent/'run.py');raw=importlib.util.module_from_spec(spec);spec.loader.exec_module(raw)
spec=importlib.util.spec_from_file_location('calyx',n.BASE.parent/'Calyx Research Pipeline/calyx_pipeline.py');c=importlib.util.module_from_spec(spec);sys.modules[spec.name]=c;spec.loader.exec_module(c)

def frame(r,kind):
    return pd.read_csv(__import__('io').BytesIO(gzip.decompress((n.OUT/r['stage']/('0-'+kind+'.csv.gz')).read_bytes())))

def native_deal_check(body,df):
 """Independently check exports against native HTML deal rows and close reasons."""
 from app.mt5_evidence_jobs import _clean,_number
 body=body[body.lower().index('<b>deals</b>'):];rows={}
 for rr in re.findall(r'<tr\b[^>]*>(.*?)</tr>',body,re.S|re.I):
  cells=[_clean(x) for x in re.findall(r'<td\b[^>]*>(.*?)</td>',rr,re.S|re.I)]
  if len(cells)<13 or not cells[2] or cells[3].lower() not in ('buy','sell'):continue
  deal=int(cells[1]);assert deal not in rows;rows[deal]=cells
 assert set(rows)==set(int(x['deal']) for x in df)
 for d in df:
  c=rows[int(d['deal'])];assert int(c[7])==int(d['order']) and c[4].lower()==('in' if int(d['entry'])==0 else 'out')
  assert c[3].lower()==('buy' if int(d['type'])==0 else 'sell')
  assert int(datetime.strptime(c[0],'%Y.%m.%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp())==int(d['epoch'])
  for key,col in [('volume',5),('price',6),('commission',8),('swap',9),('gross',10)]:assert abs(float(d[key])-_number(c[col]))<.011
 return rows

def exact(r):
    trades,ledger=raw.reconstruct(frame(r,'deals').to_dict('records'),frame(r,'trades').to_dict('records'))
    assert abs(sum(t['net_profit'] for t in trades)-r['stats']['net'])<.021
    folder=n.OUT/r['stage'];manifest=n.load(folder/'manifest.json')
    assert n.sha(folder/'Logic.mqh')==manifest['logic']==n.sha(n.EA/'Logic.mqh')
    report=next(folder.glob('*.htm.gz'));archive=gzip.decompress(report.read_bytes());assert hashlib.sha256(archive).hexdigest()==r['report_sha']
    text=archive.decode('utf-16') if archive[:2] in (b'\xff\xfe',b'\xfe\xff') else archive.decode('utf-8-sig')
    reportrows=native_deal_check(text,frame(r,'deals').to_dict('records'))
    for t in trades:
        t['exit_comment']=reportrows[t['last_exit_deal']][12];t['boundary_exit']='end of test' in t['exit_comment'].lower()
    journal=gzip.decompress((folder/'journal.txt.gz').read_bytes()).decode()
    receipts={}
    for a in re.findall(r'GT_RISK position=(\d+) budget=([\d.]+) quote_cash=([\d.]+) actual_cash=([\d.]+)',journal):
        pos=int(a[0]);receipts[pos]=dict(budget=float(a[1]),quote=float(a[2]),actual=float(a[3]))
    assert set(receipts)=={t['position_id'] for t in trades},(r['stage'],len(receipts),len(trades))
    for t in trades:
        a=receipts[t['position_id']]
        assert a['quote']<=a['budget']+.011 and a['actual']>0
        assert abs(a['budget']-t['requested_risk'])<1e-6 and abs(a['actual']-t['actual_risk'])<1e-6
    riskdiff=[abs(a['actual']-a['quote']) for a in receipts.values()]
    rates=n.stats(frame(r,'trades'),r['start'],r['end'],equity_dd=r['net']['equity_dd_pct'])
    sample=frame(r,'trace');stride=max(1,(len(sample)+1999)//2000)
    display=pd.concat([sample.iloc[::stride],sample.tail(1)]).drop_duplicates('time')
    bal=[10000]+[x['balance'] for x in ledger];peaks=np.maximum.accumulate(bal)
    dd=float(np.max((peaks-np.array(bal))/peaks)*100)
    minlot=re.findall(r'GT_SUMMARY minlot_skips=(\d+)',journal)
    out=dict(tag=r['stage'],start=r['start'],end_exclusive=r['end'],symbol=r['symbol'],risk_pct=r['risk_percent'],stats=rates,native=r['native'],report_sha256=r['report_sha'],
      trades=trades,ledger=ledger,equity_sample=display.to_dict('records'),equity_sample_note=f'Native five-minute trace retained in gz evidence; chart sample thinned every {stride} rows. Native equity DD is authoritative, not recomputed from thinning.',receipts=receipts,closed_deal_balance_dd_pct=dd,
      measured_fill_stop_cash_difference_p95=float(np.quantile(riskdiff,.95)) if riskdiff else None,minlot_skips=int(minlot[-1]) if minlot else None,
      audit=dict(position_ids_and_partial_costs_reconciled=True,native_html_deal_row_crosscheck=True,native_profit_reconciled=True,quoted_risk_verified=True,source_report_hash_verified=True,compiler_zero_warnings='0 errors, 0 warnings' in n.read(folder/'compile.log'),native_equity_dd_not_sampled=True),
      quality_notes=sorted(set(re.findall(r'real ticks begin from[^\r\n]*|real ticks absent[^\r\n]*',journal,re.I)))[:8])
    n.save(folder/'EXACT AUDIT.json',out);return out

def daily(r):
    cash=defaultdict(float)
    for d in r['ledger']:cash[d['time'][:10]]+=d['cash_flow']
    dates=pd.date_range(r['start'].replace('.','-'),pd.Timestamp(r['end_exclusive'].replace('.','-'))-pd.Timedelta(days=1),freq='D')
    balance=10000.;returns=[]
    for d in dates:
        p=cash[d.strftime('%Y-%m-%d')];returns.append(p/balance);balance+=p
    assert abs(balance-(10000+r['stats']['net']))<.021
    return dates,np.array(returns)

def common(r,count,cost):
    cache=R/'mc-cache'/('common-'+n.digest(dict(report=r['report_sha256'],code=n.sha(Path(__file__)),library=n.sha(n.BASE.parent/'Calyx Research Pipeline/calyx_pipeline.py'),count=count,cost=cost,label=r['tag']))+'.json')
    if cache.exists():return n.load(cache)
    outcomes=[c.TradeOutcome(datetime.fromisoformat(t['close_time']),t['net_profit'],t['commission']+t['fee'],t['swap']) for t in r['trades']]
    native=r['native']
    meta=dict(source_report='exact position-ID native deals plus native HTML',initial_balance=10000,reported_net_profit=r['stats']['net'],reported_profit_factor=r['stats']['pf'],reported_win_rate_pct=r['stats']['win_pct'],reported_max_drawdown_pct=native['equity_dd_pct'],reported_trades=len(outcomes),reported_sharpe=native['sharpe_ratio'],history_quality=native['history_quality'])
    c.parse_mt5_report=lambda _: (meta,outcomes)
    dates,returns=daily(r);c.daily_returns=lambda _,initial:(list(dates.date),list(returns),[])
    a=c.audit_report(Path('exact-native'),label=r['tag'],paths=10000,block=5,tested_configurations=count,daily_loss_limit_pct=5,total_loss_limit_pct=10,extra_cost_per_trade=cost,seed=20261005)
    a['scope']='Actual deal-timed daily cash flows incl. entry fees and partial exits. Bootstrap/DSR are empirical closed-balance diagnostics, not floating FTMO pass probability. DSR trial-count approximation treats searched settings as independent; correlated trials make it conservative but non-normal/nonstationary returns remain limitations.'
    result=c.json_safe(a);n.save(cache,result);return result

def monte(r):
    cache=R/'mc-cache'/('monte-'+n.digest(dict(report=r['report_sha256'],code=n.sha(Path(__file__)),library=n.sha(n.BASE.parent/'Calyx Research Pipeline/calyx_pipeline.py'),label=r['tag']))+'.json')
    if cache.exists():return n.load(cache)
    rng=np.random.default_rng(20261005);p=np.array([t['net_profit'] for t in r['trades']]);paths=10000
    if not len(p):return dict(paths=paths,status='insufficient_data')
    width=min(5,len(p));st=rng.integers(0,len(p),(paths,(len(p)+width-1)//width));ix=(st[:,:,None]+np.arange(width))%len(p);draw=p[ix.reshape(paths,-1)[:,:len(p)]]
    ends=draw.sum(axis=1)/100;gp=np.maximum(draw,0).sum(axis=1);gl=-np.minimum(draw,0).sum(axis=1);pf=np.divide(gp,gl,out=np.full(paths,99.),where=gl>0)
    shuffle=[];losing=[];fans=[]
    for _ in range(paths):
        order=rng.permutation(p);curve=np.r_[10000,10000+np.cumsum(order)];pk=np.maximum.accumulate(curve);shuffle.append(np.max((pk-curve)/pk)*100);losing.append(c.streaks(order.tolist())[1])
    missed=[]
    for fraction in [.1,.2]:
        keep=max(1,round(len(p)*(1-fraction)));results=np.array([rng.choice(p,keep,replace=False).sum()/100 for _ in range(paths)])
        missed.append(dict(skip_pct=int(fraction*100),return_p05_pct=float(np.quantile(results,.05)),median_return_pct=float(np.median(results)),profit_probability_pct=float((results>0).mean()*100)))
    dates,rets=daily(r);width=min(5,len(rets));st=rng.integers(0,len(rets),(paths,(len(rets)+width-1)//width));ix=(st[:,:,None]+np.arange(width))%len(rets);draw=rets[ix.reshape(paths,-1)[:,:len(rets)]]
    balance=10000*np.cumprod(1+draw,axis=1);balance=np.column_stack([np.full(paths,10000.),balance]);pk=np.maximum.accumulate(balance,axis=1);dd=np.max((pk-balance)/pk,axis=1)*100;qs=np.quantile(balance,[.05,.5,.95],axis=0)
    result=dict(paths=paths,block=5,trade_block_profit_probability_pct=float((ends>0).mean()*100),trade_block_return_p05_pct=float(np.quantile(ends,.05)),trade_block_return_median_pct=float(np.median(ends)),trade_block_pf_p05=float(np.quantile(pf,.05)),trade_block_pf_median=float(np.median(pf)),shuffle_closed_dd_median_pct=float(np.median(shuffle)),shuffle_closed_dd_p95_pct=float(np.quantile(shuffle,.95)),shuffle_loss_streak_p95=float(np.quantile(losing,.95)),daily_block_closed_dd_p95_pct=float(np.quantile(dd,.95)),missed_trades=missed,fan=dict(dates=[d.strftime('%Y-%m-%d') for d in dates],p05=qs[0].tolist(),p50=qs[1].tolist(),p95=qs[2].tolist()),scope='Five-trade block resamples fixed actual cash outcomes; five-day block resamples deal-timed cash returns. No broker or overlapping equity resimulation.')
    n.save(cache,result);return result

def summary_rows(exacts,silver):
    def row(label,r):
        return dict(symbol=r['symbol'],window=label,start=r['start'],end_exclusive=r['end_exclusive'],**r['stats'],native_sharpe=r['native']['sharpe_ratio'],history_quality=r['native']['history_quality'])
    return [row(k,r) for k,r in exacts.items()]+[row('XAG1Y',silver)]


def main():
    frozen=n.load(R/'FROZEN FINAL.json');account=n.load(R/'TRIAL ACCOUNTING.json')
    if (R/'CONTROLLER RESTART.txt').exists():
        account['interrupted_attempt_upper_bound']=81
    account['failed_native_attempts']=len(list(n.OUT.glob('*/FAILED-ATTEMPT-*-empty.htm')))
    account['all_included_in_DSR']=account['total_native_passes']+account.get('interrupted_attempt_upper_bound',0)+account['failed_native_attempts']
    n.save(R/'TRIAL ACCOUNTING.json',account)
    count=account['all_included_in_DSR'];results=n.load(R/'FINAL RESULTS.json')
    exacts={k:exact(r) for k,r in results.items()};other=[]
    for r in n.load(R/'RISK RESULTS.json')+n.load(R/'MODULE RESULTS.json')+list(n.load(R/'CONTROLS.json').values())+[n.load(R/'XAG RESULTS.json')]:other.append(exact(r))
    cost=exacts['1Y']['measured_fill_stop_cash_difference_p95'];audits={k:common(exacts[k],count,cost) for k in ['DEV','VAL','HOLD','5Y','3Y','1Y','6M','3M']}
    mc={k:monte(exacts[k]) for k in ['DEV','VAL','HOLD','1Y','6M','3M']}
    comparator={}
    if (R/'TUNED COMPARATOR RESULTS.json').exists():
        comparator={k:exact(r) for k,r in n.load(R/'TUNED COMPARATOR RESULTS.json').items()}
    yearly=[]
    for y in range(2021,2027):
        ts=[t for t in exacts['5Y']['trades'] if t['close_time'].startswith(str(y))];yearly.append(dict(year=y,**raw.metrics(ts),scope='Contribution to one shared five-year account, not fresh annual tests; partial 2021/2026'))
    gates=dict(native_execution_clean=all(r['clean'] for r in results.values()),validation_qualified=frozen['qualified_validation'],hold_count30=exacts['HOLD']['stats']['trades']>=30,hold_positive_pf115=exacts['HOLD']['stats']['net']>0 and (exacts['HOLD']['stats']['pf'] or 0)>=1.15,
      hold_locked_statistical=all(audits['HOLD']['gates'].values()),recent_year_positive_pf115=exacts['1Y']['stats']['net']>0 and (exacts['1Y']['stats']['pf'] or 0)>=1.15,recent_6m_positive=exacts['6M']['stats']['net']>0,recent_3m_positive=exacts['3M']['stats']['net']>0,
      independent_wider_spread_stress=False,intraday_continuous_equity_path=False,hold_real_ticks=exacts['HOLD']['native']['history_quality']=='100% real ticks')
    verdict='RESEARCH_WATCH_NO_PROMOTION' if gates['validation_qualified'] and gates['hold_positive_pf115'] else 'REJECT_NO_DEPLOYMENT'
    out=dict(verdict=verdict,gates=gates,trial_accounting=n.load(R/'TRIAL ACCOUNTING.json'),frozen=frozen,exact=exacts,other=other,common_audits=audits,monte_carlo=mc,calendar_years=yearly,tuned_comparator=comparator,
      measured_cost_stress=dict(extra_usd_per_position=cost,method='Another copy of observed P95 absolute executable-quote vs delayed-fill stop-cash difference. Sensitivity, not independent spread-stress certification.'),
      deferred=dict(FTMO='No continuous floating-equity path; missing independent spread stress and locked gate(s). No credible pass-days/payout odds produced.',portfolio_overlap='No qualified new portfolio addition approved. Standalone trio shared-account results are native, not a portfolio ledger overlay.',nested_walk_forward='Chronological development/validation and reserved earlier confirmation plus fixed-final yearly contributions. Not a claimed nested walk-forward optimiser. Production not authorised.'),
      limitations=['Public idea reconstruction; numerical rules ours.','Earlier confirmation unused for this exact model but related research reused this market era. Latest year already seen, not untouched OOS.','Before 2026-01-01 broker generated ticks; exact delay/fees do not repair missing historical ticks.','Five-minute equity plots can miss intrabar peaks; native summary equity DD reported separately.','Minimum lot risk skips and changing compounding can prevent direct linear risk scaling.'])
    def plain(x):
        if isinstance(x,np.generic):return plain(x.item())
        if isinstance(x,dict):return {k:plain(v) for k,v in x.items()}
        if isinstance(x,list):return [plain(v) for v in x]
        return x
    out=plain(out);n.save(R/'AUDIT.json',out)
    rows=summary_rows(exacts,other[-1])
    with (R/'FINAL SUMMARY.csv').open('w',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps(dict(verdict=verdict,gates=gates,year=exacts['1Y']['stats'],hold=exacts['HOLD']['stats'],MC={k:v for k,v in mc['1Y'].items() if k!='fan'}),indent=2))

if __name__=='__main__':main()
