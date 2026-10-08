"""Offline calculator checks: no terminal, trade API, or account access."""
from datetime import datetime, timezone
import json
import math

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.portfolio_analytics import allocation_replay, performance
from app.portfolios import portfolio_by_slug, portfolio_history, portfolio_scenario

client=TestClient(app)


def epoch(value):
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp()


def row(key, opening, closing, pnl):
    return dict(key=key,op=epoch(opening),cl=epoch(closing),unit_risk=100,
                unit_gross=pnl,unit_comm=0,unit_swap=0)


def test_percent_uses_entry_balance_not_future_profit_or_close_order():
    rows=[row('a','2026-01-01T08:00','2026-01-01T10:00',100),
          row('b','2026-01-01T09:00','2026-01-01T11:00',100),
          row('c','2026-01-01T10:30','2026-01-01T12:00',100)]
    trades,_=allocation_replay(rows,'2026-01-01','2026-01-02','percent',1,10000)
    assert [t['net_profit'] for t in trades]==pytest.approx([100,100,101])
    fixed,_=allocation_replay(rows,'2026-01-01','2026-01-02','fixed',100,10000)
    assert [t['net_profit'] for t in fixed]==[100,100,100]


@pytest.mark.parametrize('mode,value',[('fixed',100),('percent',1)])
def test_split_order_idea_uses_half_budget_per_fill(mode,value):
    rows=[dict(row('split-limit','2026-01-01T08:00','2026-01-01T10:00',100),risk_weight=.5),
          dict(row('split-stop','2026-01-01T08:00','2026-01-01T11:00',100),risk_weight=.5)]
    trades,_=allocation_replay(rows,'2026-01-01','2026-01-02',mode,value,10000,adaptive=True)
    assert [t['net_profit'] for t in trades]==[50,50]


@pytest.mark.parametrize('mode,value',[('fixed',150),('percent',1.5)])
def test_daily_latch_blocks_only_new_entries_and_resets(mode,value):
    rows=[row('a','2026-01-01T08:00','2026-01-01T10:00',-200),
          row('already-open','2026-01-01T09:00','2026-01-01T11:00',-100),
          row('blocked','2026-01-01T10:30','2026-01-01T12:00',100),
          row('next-day','2026-01-02T08:00','2026-01-02T10:00',100)]
    trades,audit=allocation_replay(rows,'2026-01-01','2026-01-03','fixed',100,10000,
                                   daily_mode=mode,daily_value=value)
    assert [t['slug'] for t in trades]==['a','already-open','next-day']
    assert sum(t['net_profit'] for t in trades)==-200
    assert audit['skipped_entries']==1 and audit['daily_stopped_days']==1


def test_daily_closed_dd_is_intraday_peak_and_equity_is_not_fabricated():
    trades=[dict(close_time='2026-01-01T08:00:00+00:00',net_profit=100),
            dict(close_time='2026-01-01T09:00:00+00:00',net_profit=-200),
            dict(close_time='2026-01-02T09:00:00+00:00',net_profit=-50)]
    stats,_,_=performance(trades,'2026-01-01','2026-01-03')
    assert stats['max_daily_closed_drawdown_cash']==200
    assert stats['max_daily_closed_drawdown_pct']==pytest.approx(200/10100*100)
    assert stats['max_daily_closed_loss_pct']==1
    assert stats['max_daily_equity_drawdown_pct'] is None


def test_idle_guarded_tail_and_calendar_months_are_not_chart_gaps():
    trades=[dict(close_time='2021-10-15T09:00:00+00:00',net_profit=-100)]
    stats,curve,months=performance(trades,'2021-10-06','2026-10-06')
    assert stats['trades']==1 and stats['net_profit']==-100
    assert curve[-1]==dict(time='2026-10-06T00:00:00+00:00',balance=9900)
    assert len(months)==61 and months[0]['month']=='2021-10'
    assert months[-1]==dict(month='2026-10',trades=0,net_profit=0)
    assert sum(m['net_profit'] for m in months)==-100


def test_orb_reference_matches_fixed_and_not_linear_percent_rescaling():
    p=portfolio_by_slug('orbs-only'); reference=portfolio_history(p)
    one=portfolio_scenario(p,risk_mode='fixed',risk_value=50)
    two=portfolio_scenario(p,risk_mode='fixed',risk_value=100)
    dynamic=portfolio_scenario(p,risk_mode='percent',risk_value=1)
    assert one['stats']['net_profit']==pytest.approx(reference['stats']['net_profit'])
    assert two['stats']['net_profit']==pytest.approx(one['stats']['net_profit']*2)
    assert two['stats']['trades']==one['stats']['trades']==135
    assert dynamic['stats']['net_profit']!=pytest.approx(two['stats']['net_profit'])
    assert dynamic['curve'][-1]['balance']==pytest.approx(dynamic['stats']['final_balance'])
    assert sum(m['net_profit'] for m in dynamic['months'])==pytest.approx(dynamic['stats']['net_profit'])


def test_ftmo_guarded_fixed_reference_and_ceiling():
    p=portfolio_by_slug('ftmo')
    fixed=portfolio_scenario(p,risk_mode='fixed',risk_value=50)
    higher=portfolio_scenario(p,risk_mode='fixed',risk_value=200)
    reference=portfolio_history(p)
    assert fixed['stats']['trades']==reference['stats']['trades']==836
    assert fixed['stats']['net_profit']==pytest.approx(reference['stats']['net_profit'])
    assert higher['stats']==fixed['stats'] # Retained hard ceiling, not a fourfold scale.
    assert fixed['stats']['max_daily_equity_drawdown_pct'] is None
    assert fixed['stats']['max_daily_stop_reserve_loss_cash']>0
    assert 'PROXY' in fixed['scope']


def test_ftmo_long_history_keeps_loss_buffer_and_restarts_each_window():
    p=portfolio_by_slug('ftmo')
    five=portfolio_scenario(p,'5y',risk_mode='fixed',risk_value=50)
    three=portfolio_scenario(p,'3y',risk_mode='fixed',risk_value=50)
    assert five['available'] and three['available']
    assert five['start']=='2021-10-06' and three['start']=='2023-10-06'
    assert five['stats']['trades']==213 and three['stats']['trades']==2409
    assert five['stats']['return_pct']<0<three['stats']['return_pct']
    assert five['scenario']['skips']['total_loss_buffer_rejected']>0
    assert five['scenario']['unclosed_positions']==0
    assert 'continuous account' in five['scope'] and '$9,200 buffer blocked' in five['scope']
    assert five['stats']['net_profit']==pytest.approx(portfolio_history(p,'5y')['stats']['net_profit'])
    assert five['stats']['max_daily_equity_drawdown_pct'] is None


@pytest.mark.parametrize('slug',['ftmo','current14-orb05','orbs-only','full-eas'])
def test_custom_api_and_fragment_are_valid_and_have_daily_fields(slug):
    params=dict(period='3m',risk_mode='percent',risk_value=.5,
                daily_limit_mode='fixed',daily_limit_value=100)
    response=client.get('/api/portfolios/'+slug,params=params)
    assert response.status_code==200
    history=response.json()
    assert history['id']=='3m' and history['risk_settings']['daily_limit_value']==100
    assert math.isfinite(history['stats']['return_pct'])
    assert history['stats']['max_daily_equity_drawdown_pct'] is None
    assert history['stats']['max_daily_closed_drawdown_pct']>=0
    assert 'NOT liquidated' in history['scope']
    html=client.get('/portfolios/'+slug+'/history',params=params)
    assert html.status_code==200 and 'Previous results' not in html.text
    assert 'Max daily closed DD · USD' in html.text
    assert 'data-metric="max_daily_closed_drawdown_cash"' in html.text
    assert 'data-metric="max_daily_equity_drawdown_pct"' not in html.text
    assert 'Unavailable' not in html.text
    if slug=='full-eas':
        if history.get('evidence_kind'):assert 'NOT a native simultaneous 37-EA account backtest' in history['scope']
        else:assert 'NOT a test of the current 37-EA settings' in history['scope']


def test_custom_closed_dd_replays_risk_and_daily_admissions_not_reference_scale():
    p=portfolio_by_slug('current14-orb05')
    low=portfolio_scenario(p,'3m',risk_mode='fixed',risk_value=100)
    high=portfolio_scenario(p,'3m',risk_mode='fixed',risk_value=200)
    limited=portfolio_scenario(p,'3m',risk_mode='fixed',risk_value=200,
                               daily_limit_mode='fixed',daily_limit_value=450)
    dynamic=portfolio_scenario(p,'3m',risk_mode='percent',risk_value=2,
                               daily_limit_mode='percent',daily_limit_value=4.5)
    larger=portfolio_scenario(p,'3m',risk_mode='fixed',risk_value=100,initial_balance=20000)
    assert high['stats']['max_daily_closed_drawdown_cash']==pytest.approx(
        2*low['stats']['max_daily_closed_drawdown_cash'])
    assert high['stats']['max_drawdown_cash']==pytest.approx(2*low['stats']['max_drawdown_cash'])
    assert larger['stats']['max_daily_closed_drawdown_cash']==pytest.approx(
        low['stats']['max_daily_closed_drawdown_cash'])
    assert larger['stats']['max_daily_closed_drawdown_pct']<low['stats']['max_daily_closed_drawdown_pct']
    assert limited['scenario']['skipped_entries']>0
    assert limited['stats']['trades']<high['stats']['trades']
    assert dynamic['stats']['max_daily_closed_drawdown_cash']!=pytest.approx(
        limited['stats']['max_daily_closed_drawdown_cash'])
    for history in (low,high,limited,dynamic,larger):
        assert history['stats']['max_daily_closed_drawdown_cash']>=0
        assert history['stats']['max_daily_equity_drawdown_pct'] is None
        assert sum(m['net_profit'] for m in history['months'])==pytest.approx(history['stats']['net_profit'])


@pytest.mark.parametrize('params',[
    dict(risk_mode='percent',risk_value=11),dict(risk_mode='fixed',risk_value=-1),
    dict(risk_mode='fixed',risk_value='nan'),dict(risk_mode='fixed',risk_value='inf'),
    dict(risk_mode='wat'),dict(risk_mode='percent',risk_value=.5,initial_balance=50),
    dict(risk_mode='fixed',daily_limit_mode='fixed',daily_limit_value=0),
    dict(risk_mode='fixed',daily_limit_mode='percent',daily_limit_value=101),
    dict(risk_mode='recorded',daily_limit_mode='fixed',daily_limit_value=50),
])
def test_invalid_inputs_return_422_not_false_results(params):
    for route in ('/api/portfolios/orbs-only','/portfolios/orbs-only/history'):
        assert client.get(route,params=dict(period='1y',**params)).status_code==422


def test_ftmo_account_size_and_missing_history_boundaries():
    assert client.get('/api/portfolios/ftmo',params=dict(risk_mode='fixed',initial_balance=20000)).status_code==422
    response=client.get('/api/portfolios/orbs-only',params=dict(period='5y',risk_mode='percent',risk_value=1))
    assert response.status_code==200 and response.json()['available']
    assert response.json()['start']=='2021-10-06'
    assert response.json()['stats']['trades']==574
    assert response.json()['curve']


@pytest.mark.parametrize('period,expected,start',[('3y',358,'2023-10-06'),('5y',574,'2021-10-06')])
def test_long_orb_risk_scenarios_use_long_ledger_not_annual_fallback(period,expected,start):
    p=portfolio_by_slug('orbs-only')
    reference=portfolio_history(p,period)
    fixed=portfolio_scenario(p,period,risk_mode='fixed',risk_value=50)
    doubled=portfolio_scenario(p,period,risk_mode='fixed',risk_value=100)
    dynamic=portfolio_scenario(p,period,risk_mode='percent',risk_value=1.5,
                               daily_limit_mode='percent',daily_limit_value=3)
    assert fixed['stats']['trades']==reference['stats']['trades']==expected
    assert fixed['start']==start and fixed['end_exclusive']=='2026-10-06'
    assert fixed['stats']['net_profit']==pytest.approx(reference['stats']['net_profit'])
    assert doubled['stats']['net_profit']==pytest.approx(2*fixed['stats']['net_profit'])
    assert dynamic['stats']['net_profit']!=pytest.approx(3*fixed['stats']['net_profit'])
    assert dynamic['source_history_quality']==reference['source_history_quality']
    assert 'not independent native tests' in dynamic['scope']
    assert fixed['stats']['max_daily_equity_drawdown_pct'] is None


def test_news_budget_and_nasdaq_taper_are_separate():
    rows=[dict(row('news-pulse-xau','2026-01-01T08:00','2026-01-01T10:00',100),news=True),
          row('nasdaq-5m-candle-momentum','2026-01-01T08:00','2026-01-01T10:00',100),
          row('normal','2026-01-01T08:00','2026-01-01T10:00',100)]
    trades,_=allocation_replay(rows,'2026-01-01','2026-01-02','fixed',50,10000,adaptive=True,news_percent=.1)
    assert {t['slug']:t['net_profit'] for t in trades}=={'news-pulse-xau':10,'nasdaq-5m-candle-momentum':12.5,'normal':50}


def test_three_way_adaptive_loss_taper_uses_each_module_magic_lane():
    rows=[dict(row('3-way-gold',f'2026-01-01T0{i}:00',f'2026-01-01T0{i}:30',-100),lane='momentum') for i in (1,2,3)]
    rows += [dict(row('3-way-gold','2026-01-01T09:00','2026-01-01T10:00',100),lane='breakout'),
             dict(row('3-way-gold','2026-01-01T09:30','2026-01-01T10:30',100),lane='momentum')]
    trades,_=allocation_replay(rows,'2026-01-01','2026-01-02','fixed',100,10000,adaptive=True)
    assert [t['net_profit'] for t in trades]==pytest.approx([-100,-100,-100,100,50])


def test_mixed_publication_versions_never_produce_a_risk_result(tmp_path,monkeypatch):
    import app.portfolios as module
    wrong=tmp_path/'ledger.json';wrong.write_text('{}')
    monkeypatch.setattr(module,'RISK_LEDGER',wrong)
    module._risk_rows.cache_clear();module._scenario.cache_clear()
    try:
        with pytest.raises(ValueError,match='mixed-version'):
            portfolio_scenario(portfolio_by_slug('orbs-only'),'5y',risk_mode='fixed',risk_value=50)
    finally:
        module._risk_rows.cache_clear();module._scenario.cache_clear()
