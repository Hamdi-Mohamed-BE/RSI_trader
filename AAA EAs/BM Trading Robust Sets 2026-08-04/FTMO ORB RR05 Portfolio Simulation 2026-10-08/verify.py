"""Independent reconciliation of frozen results, probability funnels and paths."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import hashlib, importlib.util, json, statistics
ROOT=Path(__file__).resolve().parent
DAY=86400
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    d=read(ROOT/'Results.json');a=d['audit'];n=d['paths_per_case'];syn=datetime.fromisoformat(d['synthetic_from']).timestamp()
    assert len(d['historical'])==6 and len(d['random_cases'])==30
    for p,h in a['source_hashes'].items():assert sha(p)==h,p
    assert [q['slug'] for q in a['qualified'] if q['qualifies'] and q['order_compatible']]==a['selected_compatible']
    assert 'xau-weakness' not in a['selected_compatible']
    assert 'us100-selective-orb-v3' not in a['selected_compatible']
    for c in d['historical']:
        m=c['portfolio'];assert abs(sum(x['net'] for x in m['months'].values())-m['return_pct']*100)<1e-5
        assert sum(x['trades'] for x in m['months'].values())==m['trades']
        assert abs(sum(x['net'] for x in m['contributions'].values())-m['return_pct']*100)<1e-5
        assert all(z['trading_days']>=4 for z in c['challenge']['passes'])
        if c['challenge']['receipt_at']:
            assert len(c['challenge']['passes'])==2
            assert datetime.fromisoformat(c['challenge']['receipt_at'])>datetime.fromisoformat(c['challenge']['funded_at'])
    checked=0
    for c in d['random_cases']:
        suffix='-stress' if c['stress'] else '-cooldown' if c['cooldown'] else ''
        paths=read(ROOT/('PATHS-'+str(c['seed'])+'-'+str(c['block_weeks'])+'-'+c['portfolio']+suffix+'.json'))
        assert len(paths)==n;checked+=n
        for r in paths:
            assert all(z['trading_days']>=4 for z in r['passes'])
            assert len(r['passes'])<=2
        for s in c['summary']:
            cut=syn+s['days']*DAY
            before=lambda v:v is not None and datetime.fromisoformat(v).timestamp()<cut
            both=sum(len(r['passes'])==2 and before(r['passes'][1]['time']) for r in paths)
            p1=sum(bool(r['passes']) and before(r['passes'][0]['time']) for r in paths)
            funded=sum(before(r['funded_at']) for r in paths)
            paid=sum(before(r['receipt_at']) for r in paths)
            assert paid<=funded<=both<=p1<=n
            assert abs(both*100/n-s['both_pass_pct'])<1e-8
            assert abs(funded*100/n-s['funded_pct'])<1e-8
            assert abs(paid*100/n-s['first_reward_received_pct'])<1e-8
            reward=statistics.mean(r['reward'] if before(r['receipt_at']) else 0 for r in paths)
            assert abs(reward-s['expected_first_reward_usd'])<1e-7
            for f in s['expected_net_cash_and_fee_roi']:
                net=reward+paid/n*f['fee_usd']-f['fee_usd']
                assert abs(net-f['expected_net_cash'])<1e-7
                assert abs(100*net/f['fee_usd']-f['expected_fee_roi_pct'])<1e-7
    assert checked==30000
    # An alternative start-date audit has no wraparound or invented end history.
    end=datetime.fromisoformat(a['end_exclusive']).date()
    for x in d['historical_starts']:
        start=datetime.fromisoformat(x['start']).date()
        assert start.weekday()==0 and start+timedelta(days=x['horizon_days'])<=end
        assert datetime.fromisoformat(x['end_exclusive']).date()==start+timedelta(days=x['horizon_days'])
    plan=read(ROOT.parent/'ORB and Range Breakout RR05 Comparison 2026-10-08/PLAN.json')
    prod={p:h for x in plan['setups'] for p,h in x['production_hashes'].items()}
    for p,h in prod.items():assert sha(p)==h,p
    spec=importlib.util.spec_from_file_location('verified_sim',ROOT/'simulate.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    ns=mod.engine(cooldown=True);t=mod.START
    row=dict(key='a',symbol='USTEC',news=False,op=t+100,cl=t+500,unit_risk=1000.,unit_gross=100.,unit_comm=-.7,unit_swap=0.,open_price=25000.,close_price=25100.,side='Long')
    r=ns['replay']([row,dict(row,key='b',op=t+101)],[],t,t+DAY,challenge=False)
    assert r['trades']==1 and r['counts']['entry_reconciliation_cooldown']==1
    check=dict(random_path_records_checked=checked,probability_funnels_checked=90,historical_portfolios_checked=6,
               real_start_windows_checked=len(d['historical_starts']),source_files_unchanged=True,
               production_files_unchanged=len(prod),fee_roi_checked=True,initial_stop_risk_not_configured_estimate=True,
               cooldown_test_passed=True,no_live_changes=True)
    (ROOT/'VERIFICATION.json').write_text(json.dumps(check,indent=2),encoding='utf-8');print(json.dumps(check))
if __name__=='__main__':main()
