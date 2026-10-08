"""Independent closed-bar, calendar, indicator, stop-risk and cash-flow audit."""
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote,urlparse
import collections,json
import numpy as np
import pandas as pd

R=Path(__file__).resolve().parent
def verify(mode,smoke=False):
    import run as r
    name,tf,slug,source,preset,out=r.paths(mode,smoke)
    status=json.loads((out/'status.json').read_text());assert status['ok']
    build=json.loads((R/'build.json').read_text());assert build['files']==r.fingerprints()==status['build']['files']
    assert build['binaries'][name]==r.sha(source.with_suffix('.ex5'))
    assert r.sha(out/'report.htm')==status['report_sha256']
    dec=pd.read_csv(out/'decisions.csv',encoding='utf-16');sent=dec[dec.reason=='entry_sent'].copy()
    bars=pd.read_csv(out/'bars.csv',encoding='utf-16');sessions=pd.read_csv(out/'sessions.csv',encoding='utf-16')
    seconds={1:1800,2:60,3:900}[mode]
    assert (sent.epoch>=sent.bar_epoch+seconds).all(),'Future candle used'
    sent['ct']=pd.to_datetime(sent.epoch,unit='s',utc=True).dt.tz_convert('America/Chicago')
    sent['bar_ct']=pd.to_datetime(sent.bar_epoch,unit='s',utc=True).dt.tz_convert('America/Chicago')
    clock=sent.ct.dt.hour*100+sent.ct.dt.minute
    assert (clock<1430).all()
    if mode in [1,2]:assert clock.ge(1000).all()
    else:assert (sent.bar_ct.dt.hour*100+sent.bar_ct.dt.minute).ge(845).all()
    limit=3 if mode==1 else 1
    assert (sent.groupby(sent.ct.dt.date).size()<=limit).all()
    assert np.allclose(sent.risk_budget,sent.sizing_equity*.01,atol=1e-7)
    planned=sent.lots*sent.unit_loss
    assert (planned<=sent.risk_budget+1e-6).all()
    assert sent.lots.ge(sent.volume_min).all()
    assert np.allclose(sent.lots/sent.volume_step,np.round(sent.lots/sent.volume_step),atol=1e-6)
    if mode in [1,2]:assert sent.tp.gt(sent.entry_quote).all() and sent.sl.lt(sent.entry_quote).all()
    else:
        assert ((sent.tp-sent.entry_quote)*sent.bias).gt(0).all()
        assert ((sent.entry_quote-sent.sl)*sent.bias).gt(0).all()
    # Session ATR computed independently from raw exported daily/session OHLC.
    previous=None;seed=[];atr=0;av=[];dates=[]
    for row in sessions.itertuples():
        tr=row.high-row.low if previous is None else max(row.high-row.low,abs(row.high-previous),abs(row.low-previous))
        assert abs(tr-row.tr)<1e-7;previous=row.close;seed.append(tr)
        if len(seed)==14:atr=sum(seed)/14
        elif len(seed)>14:atr=(atr*13+tr)/14
        assert abs(atr-row.atr)<1e-7
        if len(seed)>=14:av.append(atr);dates.append(row.day)
    av=np.array(av);dates=np.array(dates)
    for x in sent.itertuples():
        day=int(x.ct.strftime('%Y%m%d'));past=av[dates<day]
        assert len(past)>=15 and abs(past[-15:].mean()-x.noise_mean)<1e-7
    # Midnight HLC3 * tick-volume VWAP from all exported, causal closed candles.
    bars['ct']=pd.to_datetime(bars.epoch,unit='s',utc=True).dt.tz_convert('America/Chicago')
    bars['day']=bars.ct.dt.date;bars['hhmm']=bars.ct.dt.hour*100+bars.ct.dt.minute
    bars['pv']=(bars.high+bars.low+bars.close)/3*bars.tick_volume
    bars['vwap_check']=bars.groupby('day').pv.cumsum()/bars.groupby('day').tick_volume.cumsum()
    assert np.allclose(bars.vwap_check,bars.vwap,atol=1e-7)
    lookup=bars.set_index('epoch').loc[sent.bar_epoch]
    assert np.allclose(lookup.vwap.to_numpy(),sent.vwap.to_numpy(),atol=1e-7)
    assert np.allclose(lookup.adx.to_numpy(),sent.adx.to_numpy(),atol=1e-7)
    assert np.allclose(lookup.adx_previous.to_numpy(),sent.adx_previous.to_numpy(),atol=1e-7)
    opens=bars.groupby('day').open.first()
    assert np.allclose(opens.loc[sent.bar_ct.dt.date].to_numpy(),sent.midnight_open.to_numpy(),atol=1e-7)
    # Independent Wilder ADX from the trace after enough warmup to eliminate seeds.
    tr=pd.concat([bars.high-bars.low,(bars.high-bars.close.shift()).abs(),(bars.low-bars.close.shift()).abs()],axis=1).max(axis=1)
    up=bars.high.diff();down=-bars.low.diff()
    plus=up.where((up>down)&(up>0),0).ewm(alpha=1/14,adjust=False).mean()
    minus=down.where((down>up)&(down>0),0).ewm(alpha=1/14,adjust=False).mean()
    atr_series=tr.ewm(alpha=1/14,adjust=False).mean()
    pdi=100*plus/atr_series;mdi=100*minus/atr_series
    dx=(100*(pdi-mdi).abs()/(pdi+mdi)).fillna(0)
    adx_check=dx.ewm(alpha=1/14,adjust=False).mean()
    if len(bars)>500:assert np.allclose(adx_check.iloc[500:],bars.adx.iloc[500:],atol=1e-5),'ADX mismatch'
    if mode==1:
        assert sent.signal_close.gt(sent.barrier).all() and sent.signal_close.gt(sent.vwap).all()
        assert np.allclose(sent.sl,sent.entry_quote-75,atol=.051) and np.allclose(sent.tp,sent.entry_quote+40,atol=.051)
    elif mode==2:
        opening=bars[bars.hhmm.between(830,859)].groupby('day').agg(high=('high','max'),low=('low','min'))
        assert np.allclose(opening.loc[sent.bar_ct.dt.date].high.to_numpy(),sent.range_high.to_numpy(),atol=1e-7)
        assert np.allclose(opening.loc[sent.bar_ct.dt.date].low.to_numpy(),sent.range_low.to_numpy(),atol=1e-7)
        assert sent.adx.gt(20).all() and sent.adx.le(sent.adx_previous+1e-8).all()
        assert sent.signal_close.gt(sent.vwap).all() and sent[['armed','touched','reclaimed']].eq(1).all().all()
        indexed=bars.set_index('epoch');indexed['sl_check']=indexed.low.rolling(20).min();indexed['tp_check']=indexed.high.rolling(5).max()
        assert np.allclose(indexed.loc[sent.bar_epoch].sl_check.to_numpy(),sent.sl.to_numpy(),atol=.051)
        assert np.allclose(indexed.loc[sent.bar_epoch].tp_check.to_numpy(),sent.tp.to_numpy(),atol=.051)
        # Independently replay setup state up to each trade, including delayed ADX.
        for x in sent.itertuples():
            # The 09:59 signal candle closes at the 10:00 first-entry boundary.
            same=bars[(bars.day==x.bar_ct.date())&(bars.hhmm>=959)&(bars.epoch<=x.bar_epoch)]
            armed=touch=reclaim=False
            for z in same.itertuples():
                armed=armed or z.close>x.range_high
                touch=touch or (armed and z.low<=z.vwap)
                reclaim=reclaim or (touch and z.close>z.vwap)
            assert armed and touch and reclaim
    else:
        opening=bars[bars.hhmm==830].set_index('day')
        for x in sent.itertuples():
            bar=opening.loc[x.bar_ct.date()];start=pd.Timestamp(x.bar_ct.date(),tz='America/Chicago')-pd.Timedelta(hours=1)
            overnight=bars[(pd.to_datetime(bars.epoch,unit='s',utc=True)>=start.tz_convert('UTC'))&(bars.epoch<bar.epoch)]
            hi=overnight.high.max();lo=overnight.low.min()
            assert abs(hi-x.overnight_high)<1e-7 and abs(lo-x.overnight_low)<1e-7
            assert abs(bar.high-x.range_high)<1e-7 and abs(bar.low-x.range_low)<1e-7
            bias=1 if bar.open>=hi-(hi-lo)/3 else -1 if bar.open<=lo+(hi-lo)/3 else 0
            assert bias==x.bias and x.adx>20
            assert (x.signal_close>x.range_high) if bias==1 else (x.signal_close<x.range_low)
            sign=1 if bias==1 else -1;dist=x.noise_mean*.3
            assert abs(x.sl-(x.entry_quote-sign*dist))<.051 and abs(x.tp-(x.entry_quote+sign*3*dist))<.051
    trades=json.loads((out/'trades.json').read_text());assert len(trades)==len(sent)==status['native']['trades']
    balance=10000;loss=[]
    for i,t in enumerate(sorted(trades,key=lambda t:t['open_time'])):
        x=sent.iloc[i];assert abs(t['volume']-x.lots)<1e-8
        assert abs(balance-x.sizing_equity)<.05
        assert abs(t['gross_profit']+t['commission']+t['swap']-t['net_profit'])<.011
        assert abs(pd.Timestamp(t['open_time'],tz='UTC').timestamp()-x.epoch)<=1
        if mode in [1,2]:assert t['side']=='Long'
        else:assert (t['side']=='Long')==(x.bias==1)
        if t['net_profit']<0:loss.append(-t['net_profit']/balance*100)
        balance+=t['net_profit']
    assert abs(balance-status['native']['final_balance'])<.05
    eq=pd.read_csv(out/'equity.csv',encoding='utf-16');assert abs(eq.balance.iloc[-1]-balance)<.05
    # Chicago DST offset independently checked hourly across all requested years.
    start=datetime(2023,10,6,tzinfo=timezone.utc);end=datetime(2026,10,6,tzinfo=timezone.utc);hours=0
    def sunday(y,m,n):return 1+(6-datetime(y,m,1).weekday())%7+7*(n-1)
    while start<end:
        a=datetime(start.year,3,sunday(start.year,3,2),8,tzinfo=timezone.utc)
        b=datetime(start.year,11,sunday(start.year,11,1),7,tzinfo=timezone.utc)
        offset=-5 if a<=start<b else -6
        assert offset==start.astimezone(ZoneInfo('America/Chicago')).utcoffset().total_seconds()/3600
        hours+=1;start+=timedelta(hours=1)
    carry=[{'open':t['open_time'],'close':t['close_time'],'net':t['net_profit'],'swap':t['swap']} for t in trades
      if pd.Timestamp(t['open_time'],tz='UTC').tz_convert('America/Chicago').date()!=pd.Timestamp(t['close_time'],tz='UTC').tz_convert('America/Chicago').date()]
    holds=[(pd.Timestamp(t['close_time'])-pd.Timestamp(t['open_time'])).total_seconds() for t in trades]
    result={'ok':True,'mode':mode,'entries_verified':len(sent),'sessions_verified':len(sessions),'bars_verified':len(bars),'dst_hours_checked':hours,
      'cashflows_native_parity':True,'independent_vwap_session_atr_range_adx':True,'causal_entries':True,
      'planned_risk_percent_max':float((planned/sent.sizing_equity*100).max()) if len(sent) else 0,
      'realised_net_loss_percent_max':max(loss) if loss else 0,'overnight_carries':carry,'maximum_hold_seconds':max(holds) if holds else 0,
      'exit_reasons':dict(collections.Counter('TP' if t['exit_comment'].startswith('tp') else 'SL' if t['exit_comment'].startswith('sl') else 'session/other' for t in trades))}
    r.save(out.parent/('smoke-verification.json' if smoke else 'verification.json'),result)
    print('VERIFIED '+name+': '+json.dumps(result),flush=True)
    return result

if __name__=='__main__':
    import sys
    verify(int(sys.argv[1]),len(sys.argv)>2 and sys.argv[2]=='smoke')
