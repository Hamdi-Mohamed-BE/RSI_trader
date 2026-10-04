"""Offline checks only; importing the runner never starts an MT5 case."""
import importlib.util,json,re,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('next_filter_runner',R/'run.py');run=importlib.util.module_from_spec(sp);sp.loader.exec_module(run)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def test_production_sources_inputs_and_helpers_untouched():
    for b in json.loads((R/'bots.json').read_text()).values():
        assert sha(Path(b['source']))==b['source_sha'] and sha(Path(b['original']))==b['original_sha']
        assert sha(Path(b['setting']))==b['set_sha']
        assert all(sha(Path(p))==digest for p,digest in b['helpers'].items())
def test_default_off_no_live_initialization_no_lookahead():
    s=(R/'EA/StudyFilter.mqh').read_text()
    assert 'InpStudyADXGate=0' in s and 'InpStudyDI=false' in s
    assert '!MQLInfoInteger(MQL_TESTER)' in s and 'bar+sec<=TimeCurrent()' in s
    assert 'CopyBuffer(h,0,1,1,a)' in s and 'CopyBuffer(h,0,2,1,prev)' in s
    assert not re.search(r'CopyBuffer\([^,]+,[^,]+,0,',s)
def test_predefined_search_count_and_frozen_scope():
    assert sum(len(run.variants(k)) for k in ('weakness','sell','squeeze','trio','orb'))==37
    assert len(run.variants('trio'))==11 and len(run.variants('squeeze'))==8
    f=json.loads((R/'run-config.json').read_text())
    assert not f['full_pipeline'] and not f['promotion']
    assert f['protocol_sha']==sha(R/'PROTOCOL.txt') and f['filter_sha']==sha(R/'EA/StudyFilter.mqh')
def test_trio_does_not_filter_calendar_or_protective_exits():
    s=(R/'EA/trio/Research.mq5').read_text()
    assert 'if(m<2&&!StudyAllow(side,TF(s),m+1))return false;' in s
    assert s.count('!StudyAllow(')==1 and 'void Manage(int s' in s
def test_all_compile_clean():
    builds=json.loads((R/'BUILD.json').read_text());assert len(builds)==5
    for key,b in builds.items():
        assert '0 errors, 0 warnings' in b['compile_tail']
        assert sha(R/'EA'/key/'Research.mq5')==b['source_sha']
def test_completed_cases_exact_manifest_and_report():
    for p in (R/'native').glob('*/result.json'):
        r=json.loads(p.read_text());m=json.loads((p.parent/'manifest.json').read_text())
        import gzip
        assert hashlib.sha256(gzip.decompress((p.parent/'report.htm.gz').read_bytes())).hexdigest()==r['report_sha']
        assert m['model']==4 and m['delay_ms']==150 and m['protocol_sha']==sha(R/'PROTOCOL.txt')
        body=(p.parent/'tester.ini').read_text(encoding='utf-8-sig')
        assert 'AllowLiveTrading=0' in body and 'UseRemote=0' in body and 'UseCloud=0' in body

def test_cash_metrics_flat_trade_streak_reset_and_empty_sample():
    native=dict(equity_dd_pct=2.5,history_quality='test only')
    rows=[dict(net_profit=v,close_time=f'2026-01-{i+1:02d}T10:00:00',commission=0,swap=0)
          for i,v in enumerate([100,-50,25,0,40,30,-20,-10])]
    s=run.stats(rows,native,'2026.01.01','2026.01.10')
    assert s['trades']==8 and s['net']==115 and abs(s['return_pct']-1.15)<1e-12
    assert s['pf']==195/80 and s['win_pct']==50
    assert s['max_win_streak']==2 and s['max_loss_streak']==2 and s['equity_dd_pct']==2.5
    empty=run.stats([],native,'2026.01.01','2026.01.10')
    assert empty['pf'] is None and empty['trades']==0 and empty['win_pct']==0 and empty['closed_dd_pct']==0
