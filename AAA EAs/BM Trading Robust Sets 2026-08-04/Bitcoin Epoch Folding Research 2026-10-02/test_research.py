import numpy as np
import pandas as pd
from analyze import causal_prediction, qlike, mean_phase, return_series, rv_bins, calendar_factors, phase_index
import analyze


def test_one_step_uses_only_past():
    y=np.array([1.,4.,9.,16.]);f=np.array([1.,2.,1.,2.])
    pred,state=causal_prediction(y,f,2.,.5)
    assert np.allclose(pred,[2.,3.,1.75,10.75])
    changed=y.copy();changed[2:]*=100
    other,_=causal_prediction(changed,f,2.,.5)
    assert np.array_equal(pred[:3],other[:3])


def test_constant_forecast_has_zero_loss():
    assert np.allclose(qlike(np.ones(10),np.ones(10)),0)
    assert np.isnan(qlike(np.array([0.]),np.array([1.]))[0])


def test_fold_recovers_known_signal():
    x=np.tile([1.,2.,3.,4.],100)
    m,n=mean_phase(x,np.arange(len(x))%4,4)
    assert np.array_equal(m,[1,2,3,4]) and np.array_equal(n,[100]*4)


def test_gap_is_not_a_multi_minute_return():
    index=pd.date_range('2026-01-01',periods=32,freq='min',tz='UTC').delete(10)
    f=pd.DataFrame({'time':index,'close':np.arange(len(index))+100.})
    r=return_series(f)
    assert pd.isna(r.iloc[10]) and pd.isna(r.iloc[11])
    rv=rv_bins(r)
    assert pd.isna(rv.iloc[0]) and np.isfinite(rv.iloc[1])


def test_synthetic_weekly_pattern_recovered():
    index=pd.date_range('2025-01-06',periods=180*96,freq='15min',tz='UTC')
    y=np.where(index.dayofweek<5,2.,.5)*np.where(index.hour>=12,2.,1.)
    factors=calendar_factors(pd.Series(y,index=index))
    w=factors[3].reshape(7,96)
    assert w[:5].mean()>w[5:].mean()*1.5
    assert np.mean(factors[2][48:])>np.mean(factors[2][:48])*1.5
    assert all(np.isclose(np.mean(f),1) for f in factors)


def test_calendar_phase_alignment():
    i=pd.DatetimeIndex(['2026-09-28T00:00Z','2026-10-04T23:45Z'])
    assert np.array_equal(phase_index(i,3),[0,671])


def test_future_mutation_cannot_change_previous_forecasts(monkeypatch):
    monkeypatch.setattr(analyze,'TEST_END',analyze.TEST_START+pd.Timedelta(days=3))
    index=pd.date_range(pd.Timestamp('2025-04-01',tz='UTC'),analyze.TEST_END,freq='15min',inclusive='left')
    rng=np.random.default_rng(731)
    original=pd.Series(rng.lognormal(-10,.7,len(index)),index=index)
    altered=original.copy()
    altered.loc[altered.index>=analyze.TEST_START+pd.Timedelta(days=2)]*=100
    a=analyze.forecast(original);b=analyze.forecast(altered)
    before=a.index<analyze.TEST_START+pd.Timedelta(days=2)
    assert np.array_equal(a.loc[before].to_numpy(),b.loc[before].to_numpy())
