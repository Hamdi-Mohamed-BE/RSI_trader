"""Independent native trace, causal signal, cash-flow and risk verification."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from html.parser import HTMLParser
from urllib.parse import unquote
import collections, hashlib, json
import numpy as np
import pandas as pd

R=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def mql_offset(t):
    def sunday(year,month,n):
        first=datetime(year,month,1,tzinfo=timezone.utc)
        return 1+(6-first.weekday())%7+7*(n-1)
    start=datetime(t.year,3,sunday(t.year,3,2),7,tzinfo=timezone.utc)
    end=datetime(t.year,11,sunday(t.year,11,1),6,tzinfo=timezone.utc)
    return -4 if start<=t<end else -5

def verify(folder='native'):
    out=R/folder;build=json.loads((R/'build.json').read_text());status=json.loads((out/'status.json').read_text());assert status['ok']
    assert build['source']==sha(R/'NY Open Range US100.mq5')==status['build']['source']
    assert build['binary']==sha(R/'NY Open Range US100.ex5')==status['build']['binary']
    assert build['protocol']==sha(R/'PROTOCOL.txt') and build['preset']==sha(R/'NY Open Range US100 1pct.set')
    assert status['report_sha256']==sha(out/'report.htm')
    assert all(v==0 for k,v in status['flags'].items() if k!='invalid_stops')
    # No lookahead: a signal bar must have fully finished before order submission.
    decisions=pd.read_csv(out/'decisions.csv',encoding='utf-16')
    rejected=decisions[decisions.reason=='entry_failed']
    assert rejected.retcode.eq(10016).all()
    assert len(rejected)==status['broker_stop_rejections']
    sent=decisions[decisions.reason=='entry_sent'].copy()
    sent['ny']=pd.to_datetime(sent.epoch,unit='s',utc=True).dt.tz_convert('America/New_York')
    sent['bar_ny']=pd.to_datetime(sent.bar_epoch,unit='s',utc=True).dt.tz_convert('America/New_York')
    assert (sent.epoch>=sent.bar_epoch+900).all()
    assert (sent.bar_ny.dt.hour*100+sent.bar_ny.dt.minute).between(945,1459).all()
    assert sent.ny.dt.date.nunique()==len(sent)
    assert sent.range_high.gt(sent.range_low).all()
    assert sent.rvol.ge(1-1e-9).all() and sent.atr_pct.between(.1-1e-9,.6+1e-9).all()
    # 1% of actual entry equity and no minimum-lot forced oversizing.
    assert np.allclose(sent.risk_budget,sent.sizing_equity*.01,atol=1e-7)
    assert np.allclose(sent.sizing_equity,sent.sizing_balance,atol=1e-7)
    planned=sent.lots*sent.unit_loss
    assert (planned<=sent.risk_budget+1e-6).all()
    assert (sent.lots>=sent.volume_min).all()
    assert np.allclose(sent.lots/sent.volume_step,np.round(sent.lots/sent.volume_step),atol=1e-6)
    # Independently recalculate RVOL from every audited M15 bar, excluding signal.
    bars=pd.read_csv(out/'bars.csv',encoding='utf-16').set_index('epoch')
    bars['rvol_check']=bars.tick_volume/bars.tick_volume.shift(1).rolling(20,min_periods=1).mean()
    bars['atr_pct_check']=bars.atr/bars.close*100
    lookup=bars.loc[sent.bar_epoch]
    assert np.allclose(lookup.rvol_check.to_numpy(),sent.rvol.to_numpy(),atol=1e-7)
    assert np.allclose(lookup.atr.to_numpy(),sent.atr.to_numpy(),atol=1e-7)
    assert np.allclose(lookup.atr_pct_check.to_numpy(),sent.atr_pct.to_numpy(),atol=1e-7)
    # Day ranges independently reconstructed with New York calendar/DST.
    bars['ny']=pd.to_datetime(bars.index,unit='s',utc=True).tz_convert('America/New_York')
    opening=bars[(bars.ny.dt.hour==9)&(bars.ny.dt.minute==30)].copy()
    opening['day']=opening.ny.dt.date
    opening=opening.set_index('day')
    assert np.allclose(opening.loc[sent.bar_ny.dt.date].high.to_numpy(),sent.range_high.to_numpy(),atol=1e-8)
    assert np.allclose(opening.loc[sent.bar_ny.dt.date].low.to_numpy(),sent.range_low.to_numpy(),atol=1e-8)
    trades=json.loads((out/'trades.json').read_text())
    assert len(trades)==status['native']['trades']==len(sent)
    assert abs(sum(t['net_profit'] for t in trades)-status['native']['net_profit'])<.03
    sorted_entries=sorted(trades,key=lambda t:t['open_time'])
    expected_balance=10000
    for i,t in enumerate(sorted_entries):
        assert abs(t['gross_profit']+t['commission']+t['swap']-t['net_profit'])<.011
        dt=datetime.fromisoformat(t['open_time']).replace(tzinfo=timezone.utc).astimezone(ZoneInfo('America/New_York'))
        assert dt.date()==sent.iloc[i].ny.date()
        assert abs(t['volume']-sent.iloc[i].lots)<1e-8
        assert abs(expected_balance-sent.iloc[i].sizing_balance)<.03
        expected_balance+=t['net_profit']
        if t['side']=='Long':assert sent.iloc[i].signal_close>sent.iloc[i].range_high
        else:assert sent.iloc[i].signal_close<sent.iloc[i].range_low
        signal=sent.iloc[i].signal_close;atr=sent.iloc[i].atr
        # Rounded native SL/TP remain within 0.051 price points of source's anchors.
        sign=1 if t['side']=='Long' else -1
        assert abs(sent.iloc[i].sl-(signal-sign*.4*atr))<=.051
        assert abs(sent.iloc[i].tp-(signal+sign*.16*atr))<=.051
    eq=pd.read_csv(out/'equity.csv',encoding='utf-16')
    assert abs(eq.balance.iloc[-1]-status['native']['final_balance'])<.03
    start=datetime(2023,10,6,tzinfo=timezone.utc);end=datetime(2026,10,6,tzinfo=timezone.utc);hours=0
    while start<end:
        assert mql_offset(start)==start.astimezone(ZoneInfo('America/New_York')).utcoffset().total_seconds()/3600
        hours+=1;start+=timedelta(hours=1)
    reasons=lambda t:'TP' if t['exit_comment'].startswith('tp') else 'SL' if t['exit_comment'].startswith('sl') else 'session/other'
    holds=[(datetime.fromisoformat(t['close_time'])-datetime.fromisoformat(t['open_time'])).total_seconds() for t in trades]
    realised_loss_pct=[-t['net_profit']/sent.iloc[i].sizing_equity*100 for i,t in enumerate(sorted_entries) if t['net_profit']<0]
    result={'ok':True,'folder':folder,'dst_hours_checked':hours,'cashflow_and_native_counts_match':True,
      'causal_completed_bar_entries':True,'one_entry_per_ny_day':True,'independent_rvol_atr_range_checks':True,
      'risk_budget_matches_1pct_equity':True,'lot_steps_floor_not_oversize':True,'planned_risk_percent_max':float((planned/sent.sizing_equity*100).max()),
      'realised_net_loss_percent_max':max(realised_loss_pct) if realised_loss_pct else 0,
      'maximum_hold_seconds':max(holds) if holds else 0,'exit_reasons':dict(collections.Counter(map(reasons,trades))),
      'long_short':dict(collections.Counter(t['side'] for t in trades)),'net':round(sum(t['net_profit'] for t in trades),2)}
    result['broker_invalid_stop_rejections']=len(rejected)
    if folder=='native' and (R/'Results.html').exists():
        class Links(HTMLParser):
            def __init__(self):super().__init__();self.links=[]
            def handle_starttag(self,tag,attrs):
                if tag=='a':self.links.extend(v for k,v in attrs if k=='href')
        page=(R/'Results.html').read_text(encoding='utf-8');parser=Links();parser.feed(page)
        assert all((R/unquote(link)).exists() for link in parser.links)
        metrics=json.loads((R/'results.json').read_text())
        assert sum(y['trades'] for y in metrics['years'])==len(trades)
        assert abs(sum(y['net'] for y in metrics['years'])-metrics['summary']['net'])<.001
        assert status['native']['history_quality'] in page
        result['report_links_verified']=len(parser.links)
        result['annual_counts_and_pnl_reconcile']=True
    (R/('verification.json' if folder=='native' else 'smoke-verification.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    import sys
    verify(sys.argv[1] if len(sys.argv)>1 else 'native')
