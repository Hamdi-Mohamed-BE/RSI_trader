"""Placement contract checks; never connect to or trade on the active terminal.

Numerical geometry and executions are additionally exercised by the isolated
native MT5 harness in News XAU Placement Fix 2026-10-03.
"""
import re
import json
import hashlib
import pytest
from app.catalog import PACKAGE_ROOT

SOURCE = PACKAGE_ROOT/'AAA Final EAs/AAA Final News Pulse XAU Event Specific EA/AAA Final News Pulse XAU Event Specific EA.mq5'


def function(code, name):
    start = re.search(r'(?m)^(?:bool|void|int|double|string|datetime)\s+'+name+r'\(', code).start()
    brace = code.index('{', start)
    depth = 1
    end = brace+1
    while depth:
        depth += (code[end]=='{')-(code[end]=='}')
        end += 1
    return code[brace:end]


def test_event_geometry_and_selected_settings():
    code = SOURCE.read_text()
    body = function(code, 'NP_ApplyEventParameters')
    for kind, lead in [('NFP',10), ('CPI',5), ('FOMC',60)]:
        match = re.search(r'if\(kind=="'+kind+r'"\)\s*\{(.*?)\}', body, re.S)
        assert match, kind
        row = match.group(1)
        for value in [f'g_np_lead={lead}', 'g_np_offset=6', 'g_np_stop=10',
                      'g_np_hold=30', 'g_np_closed_m1=false']:
            assert value in row, (kind, value)
    settings = (PACKAGE_ROOT/'Selected Portfolio Settings 2026-09-01/12A News Pulse XAU Two Sided - HARD 1.5 TOTAL.set').read_text()
    for value in ['InpMarketFallbackOnCrossedLevel=true', 'InpEnableBuySide=true',
                  'InpEnableSellSide=true', 'InpStopLossPrice=10',
                  'InpForceCloseSecondsAfterEvent=30', 'InpUseXauEventSpecific=true']:
        assert value in settings


def test_send_requires_ack_and_preserves_unknown_request_intent():
    code = SOURCE.read_text()
    body = function(code, 'NP_SendSide')
    assert body.index('g_side_inflight|=bit;NP_SaveState();') < body.index('AAA_Trade.Buy(')
    assert body.index('(g_side_accepted & bit)!=0') < body.index('AAA_Trade.Buy(')
    assert body.index('(g_side_inflight & bit)!=0') < body.index('AAA_Trade.Buy(')
    assert 'sent && (rc==TRADE_RETCODE_DONE' in body
    assert 'TRADE_RETCODE_PLACED' in body and 'TRADE_RETCODE_DONE_PARTIAL' in body
    uncertain = body[body.index('if(rc==0'):body.index('g_side_inflight&=~bit;', body.index('if(rc==0'))]
    for rc in ['TRADE_RETCODE_TIMEOUT','TRADE_RETCODE_CONNECTION','TRADE_RETCODE_ERROR']:
        assert rc in uncertain
    assert 'return false;' in uncertain
    assert 'now>=g_active_event_time' in body
    assert body.index('NP_PlanSide(') < body.index('AAA_LotsForRisk(') < body.index('AAA_Trade.Buy(')


def test_both_sides_independent_and_only_missing_sides_retry():
    code = SOURCE.read_text()
    body = function(code, 'NP_SendStraddle')
    assert 'if(allow_buy && (g_side_required & 1)!=0) NP_SendSide(true' in body
    assert 'if(allow_sell && (g_side_required & 2)!=0) NP_SendSide(false' in body
    assert '(g_side_accepted & g_side_required)==g_side_required' in body
    run = function(code, 'NP_Run')
    assert 'now>=g_active_event_time' in run
    assert '(g_side_accepted & g_side_required)==g_side_required' in run
    assert 'now-g_last_placement_attempt<1' in run
    reconcile = function(code, 'NP_ReconcileSides')
    for value in ['OrdersTotal()', 'PositionsTotal()', 'HistoryOrdersTotal()',
                  'ORDER_STATE_REJECTED', 'ORDER_MAGIC)!=InpMagic']:
        assert value in reconcile
    assert 'GlobalVariablesFlush();' in function(code, 'NP_SaveState')
    assert 'NP_LoadSideState();' in function(code, 'OnInit')


def test_deadline_closes_only_owned_exposure():
    code = SOURCE.read_text()
    lifecycle = function(code, 'NP_ManageLifecycle')
    assert 'NP_ServerNow()>=g_active_event_time+g_np_hold' in lifecycle
    assert 'NP_DeletePendingOrders();' in lifecycle and 'NP_ClosePositions();' in lifecycle
    assert '!AAA_HasExposure(_Symbol,InpMagic)' in lifecycle
    assert '!NP_IsOurOrderSelected()' in function(code, 'NP_DeletePendingOrders')
    assert '!NP_IsOurPositionSelected()' in function(code, 'NP_ClosePositions')
    assert 'POSITION_MAGIC)==InpMagic' in function(code, 'NP_IsOurPositionSelected')
    assert 'ORDER_MAGIC)==InpMagic' in function(code, 'NP_IsOurOrderSelected')
    placement = function(code, 'NP_SendStraddle')
    assert 'placement_time+120' in placement and '60*MathCeil' in placement


def test_changed_xau_does_not_publish_previous_geometry_results():
    from app.news_evidence import load_news_summary
    from app.catalog import get_product
    for period in ['6m','1y','3y','5y']:
        assert load_news_summary('news-pulse-xau',period) is None
    assert get_product('news-pulse-xau').evidence is None


def test_new_cache_requires_current_source_helper_and_settings(tmp_path, monkeypatch):
    from app import news_evidence
    monkeypatch.setattr(news_evidence,'CACHE_ROOT',tmp_path)
    path=tmp_path/'products/news-pulse-xau/standard/1y.json'
    path.parent.mkdir(parents=True)
    payload=dict(strategy_profile=news_evidence.ACTIVE_XAU_PROFILE,news_evidence_version=1,
                 period_key='1y',independent_native_run=True,calendar_verified=True,
                 available_from='2025-10-03',available_to='2026-10-03',
                 stats={'from':'2025-10-03','to':'2026-10-03'})
    bindings={
        'source_sha256':SOURCE,
        'placement_helper_sha256':SOURCE.parent/'NewsPulsePlacement.mqh',
        'set_sha256':PACKAGE_ROOT/'Selected Portfolio Settings 2026-09-01/12A News Pulse XAU Two Sided - HARD 1.5 TOTAL.set',
    }
    payload.update({k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in bindings.items()})
    path.write_text(json.dumps(payload))
    assert news_evidence.load_news_summary('news-pulse-xau','1y') is not None
    for key in bindings:
        bad={**payload,key:'stale'}
        path.write_text(json.dumps(bad))
        assert news_evidence.load_news_summary('news-pulse-xau','1y') is None


def test_native_release_receipts_match_current_compiled_build():
    root=PACKAGE_ROOT/'News XAU Placement Fix 2026-10-03'
    release=json.loads((root/'RELEASE.json').read_text())
    assert release['compile_passed'] and not release['active_terminal_changed']
    # The previous release remains immutable history, not the v2.21 build.
    baseline=PACKAGE_ROOT/'News Placement All Assets 2026-10-03/baseline'/SOURCE.name
    assert release['source_sha256']==hashlib.sha256(baseline.read_bytes()).hexdigest()
    assert release['binary_sha256']==hashlib.sha256(baseline.with_suffix('.ex5').read_bytes()).hexdigest()
    assert release['helper_sha256']==hashlib.sha256((SOURCE.parent/'NewsPulsePlacement.mqh').read_bytes()).hexdigest()
    fault=json.loads((root/'FAULT_CHECK.json').read_text())
    assert fault['passed'] and fault['not_performance_evidence']
    analysis=json.loads((root/'ANALYSIS.json').read_text())
    for result in analysis['comparisons']:
        if result['name'].startswith('New-'):
            assert result['accepted_sides']==60 and result['complete_two_sided_events']==30
            assert result['max_same_side_per_event']==1 and result['closure_violations']==0
