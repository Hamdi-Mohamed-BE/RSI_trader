"""Independent Python checks of dates, exported indicators, requested risk and whole-position cash."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
from html.parser import HTMLParser
from zoneinfo import ZoneInfo
import gzip,io,json,math
import numpy as np
import pandas as pd
import runner as r
R=r.R
def csv(folder,stem):return pd.read_csv(io.BytesIO(gzip.decompress((folder/(stem+'.csv.gz')).read_bytes())),encoding='utf-16')
def candles(dec,bars,sessions,cfg,anchor=None,risk_pct=1):
    sent=dec[dec.reason=='entry_sent'];seconds=int(cfg['tf'])*60
    assert (sent.epoch>=sent.bar_epoch+seconds).all(),'Future signal candle'
    assert np.allclose(sent.risk_budget,sent.sizing_equity*risk_pct/100,atol=1e-6),'Risk input mismatch'
    assert (sent.lots*sent.unit_loss<=sent.risk_budget+1e-6).all(),'Planned lot risk exceeds selected budget'
    assert sent.lots.ge(sent.volume_min).all()
    assert np.allclose(sent.lots/sent.volume_step,np.round(sent.lots/sent.volume_step),atol=1e-6)
    bars['date']=pd.to_datetime(bars.epoch,unit='s',utc=True).dt.tz_convert('America/Chicago').dt.date
    if cfg['tf']==240:
        assert anchor is not None
        anchor['date']=pd.to_datetime(anchor.epoch,unit='s',utc=True).dt.tz_convert('America/Chicago').dt.date
        groups={date:(g.epoch.to_numpy(),np.cumsum(((g.high+g.low+g.close)/3*g.tick_volume).to_numpy()),np.cumsum(g.tick_volume.to_numpy()),g.open.iloc[0]) for date,g in anchor.groupby('date',sort=False)}
        computed=[]
        for x in bars.itertuples():
            date=pd.Timestamp(x.evaluation_epoch,unit='s',tz='UTC').tz_convert('America/Chicago').date()
            group=groups.get(date);n=np.searchsorted(group[0],x.epoch+seconds,side='left') if group is not None else 0
            computed.append(float(group[1][n-1]/group[2][n-1]) if n and group[2][n-1]>0 else 0)
        for x in sent.itertuples():
            date=pd.Timestamp(x.epoch,unit='s',tz='UTC').tz_convert('America/Chicago').date()
            group=groups.get(date);n=np.searchsorted(group[0],x.bar_epoch+seconds,side='left') if group is not None else 0
            assert n>0 and abs(group[3]-x.midnight_open)<1e-7,'H4 midnight anchor mismatch'
    else:
        weighted=(bars.high+bars.low+bars.close)/3*bars.tick_volume
        computed=weighted.groupby(bars.date).cumsum()/bars.tick_volume.groupby(bars.date).cumsum()
    assert np.allclose(computed,bars.vwap,atol=1e-7),'VWAP mismatch'
    previous=None;seed=[];atr=0;values=[];dates=[];period=int(cfg['atr']);mean=int(cfg['mean'])
    for row in sessions.itertuples():
        tr=row.high-row.low if previous is None else max(row.high-row.low,abs(row.high-previous),abs(row.low-previous));previous=row.close
        assert abs(tr-row.tr)<1e-7;seed.append(tr)
        if len(seed)==period:atr=sum(seed)/period
        elif len(seed)>period:atr=(atr*(period-1)+tr)/period
        assert abs(atr-row.atr)<1e-7,'Session ATR mismatch'
        if len(seed)>=period:values.append(atr);dates.append(row.day)
    values=np.asarray(values);dates=np.asarray(dates)
    for x in sent.itertuples():
        day=int(pd.Timestamp(x.epoch,unit='s',tz='UTC').tz_convert('America/Chicago').strftime('%Y%m%d'));past=values[dates<day]
        assert len(past)>=mean and abs(past[-mean:].mean()-x.noise_mean)<1e-7,'Future/session ATR mean mismatch'
    tr=pd.concat([bars.high-bars.low,(bars.high-bars.close.shift()).abs(),(bars.low-bars.close.shift()).abs()],axis=1).max(axis=1)
    up=bars.high.diff();down=-bars.low.diff();plus=up.where((up>down)&(up>0),0).ewm(alpha=1/14,adjust=False).mean();minus=down.where((down>up)&(down>0),0).ewm(alpha=1/14,adjust=False).mean();a=tr.ewm(alpha=1/14,adjust=False).mean()
    p=100*plus/a;m=100*minus/a;dx=(100*(p-m).abs()/(p+m)).fillna(0);check=dx.ewm(alpha=1/14,adjust=False).mean()
    if len(bars)>500:assert np.allclose(check.iloc[500:],bars.adx.iloc[500:],atol=1e-5),'Independent Wilder ADX mismatch'
    return dict(requests=len(sent),bars=len(bars),sessions=len(sessions),maximum_planned_risk_pct=float((sent.lots*sent.unit_loss/sent.sizing_equity*100).max()) if len(sent) else 0)
def main():
    checks={};cfg=r.CONFIG
    assert cfg['development']==['2021-10-07','2023-10-07'] and cfg['validation']==['2023-10-07','2024-10-07'] and cfg['oos']==['2024-10-07','2026-10-07']
    assert cfg['live_changes'] is False and cfg['push'] is False
    from search_plan import RAW
    for bot in RAW:
        parity=r.load(R/('PARITY '+bot+'.json'));assert parity['exact']
        evaluations=r.load(R/(bot+' EVALUATION.json'));frozen=r.load(R/(bot+' FROZEN.json'))
        oosmanifest=R/'native'/(bot+'-candidate-OOS')/'manifest.json'
        assert (R/(bot+' FROZEN.json')).stat().st_mtime<=oosmanifest.stat().st_mtime,'Frozen file created after OOS'
        for key,rec in evaluations.items():
            assert rec['model']==4;assert rec['parameters']==(RAW[bot] if key.startswith('Raw') else frozen['parameters'])
            assert rec['metrics']['trades']==len(rec['trades']) and abs(sum(t['net_profit'] for t in rec['trades'])-rec['native']['net'])<.03
            folder=R/'native'/rec['stage'];dec=csv(folder,'0-decisions');bars=csv(folder,'0-bars');sessions=csv(folder,'0-sessions');anchor=csv(folder,'0-anchor-bars') if rec['parameters']['tf']==240 else None;indicator=candles(dec,bars,sessions,rec['parameters'],anchor)
            eq=csv(folder,'0-equity');assert abs(eq.balance.iloc[-1]-rec['native']['balance'])<.03
            values=np.r_[10000,eq.equity.to_numpy()];sampled=float(np.max(1-values/np.maximum.accumulate(values))*100)
            assert sampled<=rec['metrics']['equity_dd']+.02,'Sampled drawdown exceeds native tick DD'
            for t in rec['trades']:
                assert abs(t['closed_volume']-t['volume'])<1e-7;assert abs(t['profit']+t['commission']+t['swap']+t['fee']-t['net_profit'])<1e-6
                assert pd.Timestamp(t['open_time'])>=pd.Timestamp(rec['start']) and pd.Timestamp(t['close_time'])<pd.Timestamp(rec['end'])
            checks[bot+' '+key]=indicator|dict(native_cash_reconciled=True,model=4,native_equity_dd=rec['metrics']['equity_dd'],minute_sampled_equity_dd=sampled)
        for key,rec in r.load(R/(bot+' DIAGNOSTICS.json')).items():
            assert rec['model']==4 and rec['parameters']==frozen['parameters']
            assert rec['complete_positions'] and abs(sum(t['net_profit'] for t in rec['trades'])-rec['native']['net'])<.03
            folder=R/'native'/rec['stage'];anchor=csv(folder,'0-anchor-bars') if rec['parameters']['tf']==240 else None
            checks[bot+' diagnostic '+key]=candles(csv(folder,'0-decisions'),csv(folder,'0-bars'),csv(folder,'0-sessions'),rec['parameters'],anchor,risk_pct=rec['risk_pct'])|dict(native_cash_reconciled=True,model=4)
    # Check Chicago DST independently, including all five years and both transition weekends.
    cursor=datetime(2021,10,7,tzinfo=timezone.utc);end=datetime(2026,10,7,tzinfo=timezone.utc);count=0
    def sunday(y,m,n):return 1+(6-datetime(y,m,1).weekday())%7+7*(n-1)
    while cursor<end:
        a=datetime(cursor.year,3,sunday(cursor.year,3,2),8,tzinfo=timezone.utc);b=datetime(cursor.year,11,sunday(cursor.year,11,1),7,tzinfo=timezone.utc)
        assert (-5 if a<=cursor<b else -6)==cursor.astimezone(ZoneInfo('America/Chicago')).utcoffset().total_seconds()/3600
        count+=1;cursor+=timedelta(hours=1)
    page=(R/'Results.html').read_text(encoding='utf-8');assert 'retrospective OOS' in page and 'No live bots' in page and 'Raw 5Y' in page and 'Candidate OOS' in page
    assert 'nan' not in page.lower() and 'Infinity' not in page
    r.save(R/'VERIFICATION.json',dict(ok=True,checks=checks,dst_hours=count,split_nonoverlap=True,frozen_before_oos=True,live_changes=False))
    r.status('Independent verification passed',checks=len(checks),dst_hours=count)
if __name__=='__main__':main()
