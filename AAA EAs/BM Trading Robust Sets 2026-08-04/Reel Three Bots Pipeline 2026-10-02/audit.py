"""Reconciled position ledgers -> robustness. Never simple sequential HTML pairing."""
from search import *
import numpy as np
import random
sys.path.insert(0,str(BASE.parent/'Calyx Research Pipeline'))
import calyx_pipeline as cp

def cost_evidence(name,d):
    journal=gzip.decompress((OUT/name/'journal.txt.gz').read_bytes()).decode()
    # Native market-order journal quotes: actual bid/ask, not arbitrary stress inputs.
    pat=r'(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})\s+market (?:buy|sell) [\d.]+ (DE30|XAUUSD)[^\n]*?\(([\d.]+) / ([\d.]+)(?: / [\d.]+)?\)'
    values={}
    for stamp,symbol,bid,ask in re.findall(pat,journal):
        t=datetime.strptime(stamp,'%Y.%m.%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp()
        if len(d) and d.open_epoch.min()<=t<=d.close_epoch.max():
            spread=float(ask)-float(bid)
            if spread>0:values.setdefault(symbol,[]).append(spread)
    measured={s:dict(quote_count=len(v),median=float(np.median(v)),p90=float(np.quantile(v,.9))) for s,v in values.items()}
    costs=[]
    for r in d.itertuples():
        symbol='DE30' if r.module=='A_RANGE' else 'XAUUSD'
        if symbol not in measured or abs(r.open_price-r.initial_sl)<=0:return dict(status='not_available',reason='No usable native bid/ask sample for every module',quotes=measured),None
        # Price-to-USD sensitivity is backed out from the EA's OrderCalcProfit initial-risk evidence.
        costs.append(measured[symbol]['p90']*r.actual_risk/abs(r.open_price-r.initial_sl))
    return dict(status='measured_native_quote_stress',quotes=measured,scenario='One additional p90 observed native bid/ask spread per closed position. Quotes mix entries and forced closes; not a per-fill slippage estimate. Older simulated quotes are broker-model evidence, not historical live fills.'),np.asarray(costs)

def reshuffle_and_removal(pnl,seed):
    rng=np.random.default_rng(seed);dd=[];loss=[];removal={10:[],20:[]};pfs={10:[],20:[]}
    for i in range(10000):
        p=rng.permutation(pnl);balance=10000+np.cumsum(p);peak=np.maximum.accumulate(np.r_[10000,balance]);dd.append(float(np.max((peak[1:]-balance)/peak[1:])*100));loss.append(cp.streaks(p.tolist())[1])
        for pct in removal:
            keep=rng.choice(len(pnl),size=max(1,round(len(pnl)*(1-pct/100))),replace=False);v=pnl[keep];removal[pct].append(float(v.sum()/100));pfs[pct].append(cp.profit_factor(v.tolist()))
    return dict(paths=10000,scope='Closed cash P/L; no floating equity, lot recomputation or shared-margin replay',reshuffle=dict(dd_p50=float(np.median(dd)),dd_p95=float(np.quantile(dd,.95)),loss_streak_p95=float(np.quantile(loss,.95))),removal={str(p):dict(return_p05=float(np.quantile(removal[p],.05)),return_p50=float(np.median(removal[p])),pf_p05=cp.quantile(pfs[p],.05)) for p in removal})

def position_limits(name,d,row):
    manifest=load(OUT/name/'manifest.json')
    cases=manifest['cases'];selected=manifest.get('slots') or [0]
    labels={0:'A_RANGE',1:'B_ATR',2:'C_DON'}
    limits={labels[cases[i]['module']]:cases[i]['maxpos'] for i in selected}
    observed={}
    for module,g in d.groupby('module'):
        events=[]
        for r in g.itertuples():
            if r.close_epoch>r.open_epoch:events.extend([(r.open_epoch,1),(r.close_epoch,-1)])
        live=peak=0
        for _,delta in sorted(events):live+=delta;peak=max(peak,live)
        observed[module]=peak
    passed=all(observed.get(k,0)<=limit for k,limit in limits.items()) and row['net']['max_open']<=sum(limits.values())
    return dict(passed=passed,limits=limits,ledger_observed=observed,native_max_open=row['net']['max_open'],scope='Ledger timestamps have one-second resolution; same-second opens/closes are not separable. Native max-open counter provides an additional total-position check.')

def data_evidence(name):
    manifest=load(OUT/name/'manifest.json')
    journal=gzip.decompress((OUT/name/'journal.txt.gz').read_bytes()).decode('utf-8',errors='replace')
    selected=manifest.get('slots') or [0]
    warm=datetime.strptime(manifest['start'],'%Y.%m.%d')-timedelta(days=manifest['warmup'])
    issues=[]
    for i in selected:
        c=manifest['cases'][i];symbol='DE30' if c['module']==0 else 'XAUUSD'
        for date in set(re.findall(re.escape(symbol)+r'[^\n]*?history begins from (\d{4}\.\d{2}\.\d{2})',journal)):
            if datetime.strptime(date,'%Y.%m.%d')>warm:
                issues.append(f'{symbol} history begins {date}, later than frozen warm-up start {warm:%Y.%m.%d}')
        failed=[line for line in journal.splitlines() if 'cannot load indicator' in line and '('+symbol+')' in line]
        atr_required=c['module']==1 or c['stop'] in [2,3,4] or c['trail'] in [2,5,6] or c['entry'] in [2,3] or c['filter'] in [5,6]
        adx_required=c['filter'] in [3,4,8]
        for line in failed:
            if ('Average True Range' in line and atr_required) or ('Average Directional Movement Index' in line and adx_required):
                issues.append(line.strip())
    return dict(passed=not issues,issues=sorted(set(issues)),scope='Post-run check of frozen warm-up coverage and required indicator handles; a missing module is not a valid full-portfolio holdout.')

def audit(name,row,trials):
    d=read_ledger(name).sort_values(['close_epoch','position_id']);p=d.net_profit.to_numpy()
    if not len(d):return dict(verdict='REJECT',reason='No trades')
    # Include the entire frozen calendar, including inactive beginning/end days.
    # Same zero-filled calendar convention as the report's closed-P/L Sharpe.
    days=pd.date_range(row['start'],row['end'],freq='D',inclusive='left')
    closed_days=pd.to_datetime(d.close_epoch,unit='s').dt.normalize()
    daily=pd.Series(p,index=closed_days.values).groupby(level=0).sum().reindex(days,fill_value=0.0)
    balance=10000+daily.cumsum();returns=(daily/balance.shift(1).fillna(10000)).tolist()
    years=len(days)/365.25
    cache=OUT/name/'robustness-cache.json'
    signature=digest(dict(ledger=sha(OUT/name/'0-trades.csv.gz'),native=row,logic=sha(Path(__file__)),pipeline=sha(Path(cp.__file__))))
    if cache.exists():
        saved=load(cache)
        if saved.get('signature')==signature:
            result=saved['result'];result['sharpe']=cp.sharpe_statistics(returns,trials,min(365,len(days)/max(years,.01)))
            result['gates']['dsr95']=result['sharpe']['deflated_sharpe_pct']>=95
            result['tested_configurations']=trials
            result['data_evidence']=data_evidence(name);result['gates']['data_history']=result['data_evidence']['passed']
            result['verdict']='PASS_ROBUSTNESS_SCREEN' if all(result['gates'].values()) else ('WATCH_ONLY' if p.sum()>0 and cp.profit_factor(p.tolist())>1 else 'REJECT')
            return cp.json_safe(result)
    boot=cp.bootstrap(p.tolist(),returns,paths=10000,block=5,daily_loss_limit_pct=5,total_loss_limit_pct=10,seed=20261002)
    sharpe=cp.sharpe_statistics(returns,trials,min(365,len(days)/max(years,.01)))
    third=[];a=datetime.strptime(row['start'],'%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp();z=datetime.strptime(row['end'],'%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp()
    for i in range(3):
        v=d[(d.close_epoch>=a+(z-a)*i/3)&(d.close_epoch<a+(z-a)*(i+1)/3)].net_profit.tolist();third.append(dict(trades=len(v),net=sum(v),pf=cp.profit_factor(v)))
    recent=d[d.close_epoch>=(a+z)/2].net_profit.tolist();cost,extra=cost_evidence(name,d);limits=position_limits(name,d,row)
    stress=None if extra is None else dict(extra_total_usd=float(extra.sum()),net=float((p-extra).sum()),pf=cp.profit_factor((p-extra).tolist()),return_pct=float((p-extra).sum()/100))
    gates=dict(clean_execution=row['clean'],minimum30=len(d)>=30,positive_net=p.sum()>0,pf_gt1=cp.profit_factor(p.tolist())>1,bootstrap_p05_return=boot.get('return_p05_pct',-1)>0,bootstrap_p05_pf=boot.get('profit_factor_p05',0)>1,bootstrap_profit95=boot.get('probability_profit_pct',0)>=95,dsr95=sharpe['deflated_sharpe_pct']>=95,two_calendar_thirds=sum(t['net']>0 for t in third)>=2,recent_half_pf=cp.profit_factor(recent)>1,closed_total_breach_lt5=boot.get('closed_pnl_total_limit_breach_pct',100)<5,measured_cost_stress=stress is not None and stress['net']>0 and stress['pf']>1)
    gates={k:bool(v) for k,v in gates.items()}
    gates['position_limits']=bool(limits['passed'])
    evidence=data_evidence(name);gates['data_history']=evidence['passed']
    result=dict(verdict='PASS_ROBUSTNESS_SCREEN' if all(gates.values()) else ('WATCH_ONLY' if p.sum()>0 and cp.profit_factor(p.tolist())>1 else 'REJECT'),stats=row['stats'],native_equity_dd=row['net']['equity_dd_pct'],calendar_days=len(days),gates=gates,bootstrap=boot,sharpe=sharpe,calendar_thirds=third,recent_half_pf=cp.profit_factor(recent),cost_evidence=cost,cost_stress=stress,perturbations=reshuffle_and_removal(p,20261002),scope='Conditional historical resampling, not a return forecast or FTMO phase/payout probability. Full zero-filled frozen daily calendar; DSR is an approximate conservative multiple-testing screen, not an exact independent-trial estimate.')
    result['position_limits']=limits;result['data_evidence']=evidence
    result['closed_loss_proxy_definition']='Bootstrap daily check: sampled daily loss >=5% of preceding closed balance. Total check: sampled closed balance <=90% of initial balance. This is not FTMO daily midnight-reset balance/equity accounting or a phase/payout simulation.'
    result['risk_evidence']=dict(requested_risk_usd_min=float(d.requested_risk.min()),requested_risk_usd_max=float(d.requested_risk.max()),actual_to_requested_mean=float((d.actual_risk/d.requested_risk).mean()),actual_to_requested_max=float((d.actual_risk/d.requested_risk).max()),scope='Initial stop-loss risk from native fills, excluding commissions, swap and gaps after entry; a nominal sizing target is not a guaranteed loss cap.')
    result['tested_configurations']=trials;result=cp.json_safe(result)
    save(cache,dict(signature=signature,result=result,scope='Intermediate calculation cache. Final trial count and DSR are recomputed after native study completion. Not a promotion result.'))
    return result

def precompute():
    # No tester access: compute expensive ledger resampling while native tests run.
    trials=sum(len(load(p)['cases']) for p in OUT.glob('*/manifest.json'))
    names=[]
    for p in sorted(OUT.glob('*/results.json')):
        name=p.parent.name
        if not name.startswith(('raw-','frozen-','combo-')) or '-control-' in name:continue
        if not any(name.endswith(s) for s in ['5y','1y','development','holdout','5y-m4','1y-m4']):continue
        names.append(name)
    for name in names:
        status('PRECOMPUTE (PROVISIONAL TRIAL COUNT) '+name,trials=trials)
        audit(name,load(OUT/name/'results.json')[0],trials)
    print('Partial resampling cached; final DSR and promotion remain pending.',flush=True)

def main():
    trials=load(ROOT/'TRIAL ACCOUNTING.json')['passes'];frozen=load(ROOT/'FROZEN PICKS.json');comb=load(ROOT/'COMBINATIONS.json');raw=load(ROOT/'RAW GATES.json');results={}
    for m in 'ABC':
        for per in ['5y','1y']:
            name=f'raw-{m}-{per}-m4';status('ROBUSTNESS '+name);results[name]=audit(name,raw[m]['runs'][per],trials);save(ROOT/'ROBUSTNESS.json',results)
    for m,p in frozen.items():
        if not p.get('periods'):continue
        for per in ['5y','development','holdout','1y']:
            if not p['periods'].get(per):continue
            name=f'frozen-{m}-{per}';status('ROBUSTNESS '+name);results[name]=audit(name,p['periods'][per],trials);save(ROOT/'ROBUSTNESS.json',results)
        robust=results.get(f'frozen-{m}-5y',{}).get('verdict')=='PASS_ROBUSTNESS_SCREEN' and results.get(f'frozen-{m}-holdout',{}).get('verdict')=='PASS_ROBUSTNESS_SCREEN'
        p['final_verdict']=('FORWARD_TEST_CANDIDATE' if raw[m]['gate']=='PASS' else 'EXPLORATORY_SCREEN_PASS_NEEDS_REVIEW') if p['verdict']=='PASSED_NATIVE_CHECKS' and robust else 'REJECTED_OR_RESEARCH_ONLY'
    for label,p in comb.items():
        for per in ['5y','holdout','1y']:
            if per not in p['periods']:continue
            name=f'combo-{label}-{per}';status('ROBUSTNESS '+name);results[name]=audit(name,p['periods'][per],trials);save(ROOT/'ROBUSTNESS.json',results)
    save(ROOT/'FROZEN PICKS.json',frozen)
    # Correlations are closed-day P/L diagnostics, not intraday floating exposure.
    daily={}
    for m,p in frozen.items():
        if not p.get('periods'):continue
        d=read_ledger(f'frozen-{m}-5y');daily[m]=pd.Series(d.net_profit.to_numpy(),index=pd.to_datetime(d.close_epoch,unit='s').dt.normalize().values).groupby(level=0).sum()
    df=pd.DataFrame(daily).fillna(0).reindex(pd.date_range(*WEB['5y'],freq='D',inclusive='left'),fill_value=0)
    save(ROOT/'OVERLAP.json',cp.json_safe(dict(scope='Full frozen calendar of standalone closing-day P/L; the shared portfolio has its own native balance/equity simulation',daily_correlation=df.corr().to_dict())))
    status('ROBUSTNESS COMPLETE',trials=trials)

if __name__=='__main__':precompute() if len(sys.argv)>1 and sys.argv[1]=='precompute' else main()
