"""Causal seasonality forecasting and dependent-noise epoch-fold tests."""
from pathlib import Path
import hashlib
import json
import math
import numpy as np
import pandas as pd
from scipy.signal import lfilter
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parent
TEST_START = pd.Timestamp('2025-10-02', tz='UTC')
TEST_END = pd.Timestamp('2026-10-02', tz='UTC')
MODELS = ['EWMA baseline', 'Hourly', 'Daily', 'Daily + weekly']
PERIODS = [30,45,60,90,120,180,240,360,480,720,1440,2880,4320,10080]
SEED = 20261002


def save(name, value):
    (ROOT/name).write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')


def return_series(frame):
    frame = frame.set_index('time').sort_index()
    grid = pd.date_range(frame.index.min(), frame.index.max(), freq='min')
    close = frame.close.reindex(grid)
    return np.log(close).diff()


def rv_bins(r):
    # A timestamp denotes the OPEN of a minute candle; close is available one minute later.
    # First return of a bin is close(open=t) / close(open=t-1), known at t+1.
    count = r.resample('15min').count()
    rv = r.pow(2).resample('15min').sum(min_count=15)
    return rv.where(count==15)


def mean_phase(values, phase, n):
    ok = np.isfinite(values)
    count = np.bincount(phase[ok], minlength=n)
    total = np.bincount(phase[ok], weights=values[ok], minlength=n)
    return np.divide(total, count, out=np.ones(n), where=count>0), count


def smooth(a):
    return (np.roll(a,1,axis=-1)+a+np.roll(a,-1,axis=-1))/3


def unit_factor(a):
    a=np.clip(a,.15,6)
    return a/np.mean(a)


def calendar_factors(train):
    index=train.index
    week=index.normalize()-pd.to_timedelta(index.dayofweek,unit='D')
    wmeans=train.groupby(week).transform('mean')
    normalized=(train/wmeans).to_numpy()
    slot=(index.hour*4+index.minute//15).to_numpy()
    hourly,_=mean_phase(normalized,slot%4,4)
    daily,_=mean_phase(normalized,slot,96)
    daily=unit_factor(smooth(daily))
    wp=(index.dayofweek*96+slot).to_numpy()
    weekly,count=mean_phase(normalized,wp,672)
    weekly=smooth(weekly.reshape(7,96)).reshape(-1)
    shrink=count/(count+30)
    weekly=unit_factor(shrink*weekly+(1-shrink)*np.tile(daily,7))
    return [np.ones(1),unit_factor(hourly),daily,weekly]


def phase_index(index, model):
    slot=np.asarray(index.hour*4+index.minute//15,dtype=int)
    if model==0: return np.zeros(len(index),dtype=int)
    if model==1: return slot%4
    if model==2: return slot
    return np.asarray(index.dayofweek*96+slot,dtype=int)


def causal_prediction(y, factors, state, lam):
    y=np.asarray(y)
    if np.isfinite(y).all():
        filtered,_=lfilter([1-lam],[1,-lam],y/factors,zi=[lam*state])
        predictions=np.r_[state,filtered[:-1]]*factors
        return predictions,float(filtered[-1])
    pred=[]
    for value,f in zip(y,factors):
        pred.append(state*f)
        if np.isfinite(value): state=lam*state+(1-lam)*value/f
    return np.asarray(pred),state


def qlike(y,p):
    out=np.full_like(np.asarray(y,dtype=float),np.nan)
    ok=(y>0)&np.isfinite(y)&(p>0)&np.isfinite(p)
    z=y[ok]/p[ok]
    out[ok]=z-np.log(z)-1
    return out


def forecast(rv, lam=.97, verbose=False):
    out=[]
    for day in pd.date_range(TEST_START,TEST_END,freq='D',inclusive='left'):
        train=rv[(rv.index>=day-pd.Timedelta(days=180))&(rv.index<day)]
        assert len(train)>=170*96
        recent=train[train.index>=day-pd.Timedelta(days=7)]
        today=rv[(rv.index>=day)&(rv.index<day+pd.Timedelta(days=1))]
        assert len(today)==96
        patterns=calendar_factors(train)
        row=pd.DataFrame({'time':today.index,'realized_variance':today.values})
        for model,pattern in enumerate(patterns):
            past_f=pattern[phase_index(recent.index,model)]
            seed=float(np.nanmean(recent.values/past_f))
            _,state=causal_prediction(recent.values,past_f,seed,lam)
            now_f=pattern[phase_index(today.index,model)]
            pred,_=causal_prediction(today.values,now_f,state,lam)
            row[f'forecast_{model}']=pred
            row[f'qlike_{model}']=qlike(today.values,pred)
        out.append(row)
        if verbose and (day.day==1 or day==TEST_START):
            print('FORECASTED',lam,str(day.date()),flush=True)
    return pd.concat(out,ignore_index=True).set_index('time')


def block_indices(n,block,rng,reps):
    starts=rng.integers(0,n,size=(reps,math.ceil(n/block)))
    return ((starts[:,:,None]+np.arange(block))%n).reshape(reps,-1)[:,:n]


def score_forecasts(frame,block=7,reps=5000):
    daily=frame[[f'qlike_{i}' for i in range(4)]].resample('D').mean()
    assert not daily.isna().any().any()
    ix=block_indices(len(daily),block,np.random.default_rng(SEED+block),reps)
    means=daily.to_numpy()[ix].mean(axis=1)
    comparisons=[(1,0),(2,0),(3,0),(3,2)]
    results=[]
    for new,old in comparisons:
        ratio=(1-means[:,new]/means[:,old])*100
        delta=daily.iloc[:,old].to_numpy()-daily.iloc[:,new].to_numpy()
        # Centered paired null bootstrap, one-sided: does the new model reduce loss?
        centered=delta-delta.mean()
        p=(1+np.sum(centered[ix].mean(axis=1)>=delta.mean()))/(reps+1)
        lo,hi=np.quantile(ratio,[.025,.975])
        results.append(dict(model=MODELS[new],versus=MODELS[old],
                            reduction_pct=float((1-daily.iloc[:,new].mean()/daily.iloc[:,old].mean())*100),
                            ci95_pct=[float(lo),float(hi)],p_unadjusted=float(p),block_days=block))
    order=np.argsort([r['p_unadjusted'] for r in results]); current=0
    for rank,i in enumerate(order):
        current=max(current,min(1,results[i]['p_unadjusted']*(len(results)-rank)))
        results[i]['p_holm']=float(current)
    return daily,results


def folded_stat(values, phases, n):
    m,c=mean_phase(values,phases,n)
    assert (c>0).all()
    return float(np.mean((m/np.mean(values)-1)**2))


def period_search(r,block_days=7,permutations=999):
    train=r[(r.index>=pd.Timestamp('2025-04-01',tz='UTC'))&(r.index<TEST_START)].abs()
    five=train.resample('5min').mean().where(train.resample('5min').count()==5)
    first=five.index.min().normalize()
    first+=pd.Timedelta(days=(7-first.dayofweek)%7)
    width=block_days*288
    end=five.index.max().normalize()+pd.Timedelta(days=1)
    nblocks=int((end-first).total_seconds()//(block_days*86400))
    cut=five[(five.index>=first)&(five.index<first+pd.Timedelta(days=nblocks*block_days))]
    assert len(cut)==nblocks*width and not cut.isna().any()
    matrix=cut.to_numpy().reshape(nblocks,width)
    matrix=matrix/matrix.mean(axis=1,keepdims=True)
    values=matrix.reshape(-1)
    ids=np.arange(len(values))
    bins=[p//5 for p in PERIODS]
    phases=[ids%n for n in bins]
    observed=np.array([folded_stat(values,phase,n) for phase,n in zip(phases,bins)])
    exceed=np.zeros(len(bins),dtype=int)
    rng=np.random.default_rng(SEED+block_days)
    base=np.arange(width)
    for j in range(permutations):
        offsets=rng.integers(0,width,size=nblocks)
        shifted=np.take_along_axis(matrix,(base[None,:]+offsets[:,None])%width,axis=1).reshape(-1)
        stats=np.array([folded_stat(shifted,phase,n) for phase,n in zip(phases,bins)])
        exceed+=stats>=observed
    return [dict(period_minutes=p,statistic=float(s),p_unadjusted=float((e+1)/(permutations+1)),
                 p_bonferroni=float(min(1,(e+1)/(permutations+1)*len(PERIODS))),
                 survives=bool((e+1)/(permutations+1)*len(PERIODS)<.05),
                 shift_block_days=block_days,blocks=nblocks,permutations=permutations)
            for p,s,e in zip(PERIODS,observed,exceed)]


def empirical_profiles(r):
    test=r[(r.index>=TEST_START)&(r.index<TEST_END)]
    normalized=test.abs()/test.abs().groupby(test.index.normalize()).transform('mean')
    hourly=normalized.groupby(normalized.index.hour).mean()
    minutehour=normalized.groupby(normalized.index.minute).mean()
    # Weekday average absolute returns is descriptive, not a signed-return signal.
    weekday=test.abs().groupby(test.index.dayofweek).mean()/test.abs().mean()
    daily=normalized.resample('15min').mean().groupby(lambda t:t.hour*4+t.minute//15).mean()
    monthly=[]
    for month,part in normalized.groupby(normalized.index.strftime('%Y-%m')):
        profile=part.groupby(part.index.hour).mean().reindex(range(24))
        monthly.append(dict(month=month,hour_profile=[float(x) for x in profile],days=int(part.index.normalize().nunique())))
    first=test[test.index<TEST_START+pd.Timedelta(days=182)]
    second=test[test.index>=TEST_START+pd.Timedelta(days=182)]
    a=first.abs()/first.abs().groupby(first.index.normalize()).transform('mean')
    b=second.abs()/second.abs().groupby(second.index.normalize()).transform('mean')
    ap=a.groupby(a.index.hour).mean();bp=b.groupby(b.index.hour).mean()
    corr=spearmanr(ap,bp)
    top=hourly.nlargest(3).index.to_list();quiet=hourly.nsmallest(3).index.to_list()
    return dict(hour_profile=[float(x) for x in hourly.reindex(range(24))],
                minute_of_hour_profile=[float(x) for x in minutehour.reindex(range(60))],
                daily_15min_profile=[float(x) for x in daily.reindex(range(96))],
                weekday_profile=[float(x) for x in weekday.reindex(range(7))],monthly=monthly,
                first_half_hour_profile=[float(x) for x in ap.reindex(range(24))],
                second_half_hour_profile=[float(x) for x in bp.reindex(range(24))],
                first_second_half_spearman=float(corr.statistic),
                busiest_hours_utc=[int(h) for h in top],quietest_hours_utc=[int(h) for h in quiet],
                busiest_vs_quietest_abs_return_ratio=float(hourly.loc[top].mean()/hourly.loc[quiet].mean()),
                signed_up_minute_fraction=float((test>0).mean()),
                zero_return_minute_fraction=float((test==0).mean()))


def main():
    source=json.loads((ROOT/'DATA MANIFEST.json').read_text())
    assert source['data_sha256']==hashlib.sha256((ROOT/'Data/BTCUSDT-1m.npz').read_bytes()).hexdigest()
    with np.load(ROOT/'Data/BTCUSDT-1m.npz') as raw:
        f=pd.DataFrame({col:raw[col] for col in raw.files})
    f['time']=pd.to_datetime(f.time,unit='ns',utc=True)
    r=return_series(f);rv=rv_bins(r)
    test_r=r[(r.index>=TEST_START)&(r.index<TEST_END)]
    assert len(test_r)==365*1440
    print('RETURN COVERAGE',len(test_r),'missing',int(test_r.isna().sum()),flush=True)
    forecasts=forecast(rv,verbose=True)
    forecasts.to_csv(ROOT/'FORECASTS.csv.gz',compression='gzip')
    daily,primary=score_forecasts(forecasts)
    daily.to_csv(ROOT/'DAILY SCORES.csv')
    _,robust=score_forecasts(forecasts,block=14)
    monthly=forecasts[[f'qlike_{i}' for i in range(4)]].groupby(forecasts.index.strftime('%Y-%m')).mean()
    monthly['daily_weekly_reduction_pct']=(1-monthly.qlike_3/monthly.qlike_0)*100
    monthly.to_csv(ROOT/'MONTHLY SCORES.csv')
    scores=[dict(model=MODELS[i],mean_qlike=float(forecasts[f'qlike_{i}'].mean()),
                 reduction_vs_baseline_pct=float((1-forecasts[f'qlike_{i}'].mean()/forecasts.qlike_0.mean())*100)) for i in range(4)]
    sensitivity=[]
    for lam in [.94,.99]:
        s=forecast(rv,lam,verbose=True)
        sensitivity.append(dict(lambda_=lam,models=[dict(model=MODELS[i],mean_qlike=float(s[f'qlike_{i}'].mean()),
            reduction_pct=float((1-s[f'qlike_{i}'].mean()/s.qlike_0.mean())*100)) for i in range(4)]))
    print('PERIOD SEARCH (TRAINING ONLY)',flush=True)
    search=period_search(r)
    search14=period_search(r,block_days=14)
    save('PERIOD SEARCH.json',dict(primary=search,sensitivity_14day=search14))
    profiles=empirical_profiles(r)
    fullmonths=monthly.loc[(monthly.index>'2025-10')&(monthly.index<'2026-10')]
    result=dict(instrument='Binance spot BTCUSDT',test_start=str(TEST_START),test_end_exclusive=str(TEST_END),
                test_days=365,test_minute_returns=len(test_r),missing_minute_returns=int(test_r.isna().sum()),
                test_rv_bins=len(forecasts),excluded_rv_bins=int(forecasts.qlike_0.isna().sum()),
                zero_rv_bins=int((forecasts.realized_variance==0).sum()),models=scores,
                primary_comparisons=primary,block14_comparisons=robust,lambda_sensitivity=sensitivity,
                better_complete_months_weekly=int((fullmonths.daily_weekly_reduction_pct>0).sum()),
                complete_months=int(len(fullmonths)),profiles=profiles,
                period_search_training_only=search,
                protocol_sha256=hashlib.sha256((ROOT/'PROTOCOL.txt').read_bytes()).hexdigest(),
                data_manifest_sha256=hashlib.sha256((ROOT/'DATA MANIFEST.json').read_bytes()).hexdigest(),
                forecast_sha256=hashlib.sha256((ROOT/'FORECASTS.csv.gz').read_bytes()).hexdigest(),
                qualification='Retrospective research; volatility forecasts only, not a trading P&L backtest. Single venue, fixed protocol.')
    save('RESULTS.json',result)
    print(json.dumps(dict(models=scores,comparisons=primary,periods_surviving=[x['period_minutes'] for x in search if x['survives']]),indent=2),flush=True)


if __name__=='__main__': main()
