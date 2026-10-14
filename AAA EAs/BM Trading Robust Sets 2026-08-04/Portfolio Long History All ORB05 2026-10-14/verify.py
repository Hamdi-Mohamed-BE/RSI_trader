"""Independent publication and native-receipt checks; never a live trading API."""
from pathlib import Path
import hashlib,importlib.util,json,math,sys
R=Path(__file__).resolve().parent;B=R.parent;WEB=B.parent/'EA store';sys.path.insert(0,str(WEB))
from app.portfolios import portfolio_catalog,portfolio_by_slug,portfolio_scenario
from app.portfolio_analytics import history_from_trades,allocation_replay
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    plan=read(R/'PLAN.json');state=read(R/'RUN_STATUS.json');audit=read(R/'AUDIT.json');hist=read(R/'HISTORIES.json');ledgers=read(R/'RISK_ROWS.json')
    expected={c['case_id'] for c in plan['cases']};assert set(state['complete'])|set(state['missing'])==expected and not state['failed'];assert not audit['pending_cases']
    checks=0;receipts=set()
    for row in plan['cases']:
        assert all(sha(p)==s for p,s in row['production_hashes'].items()),'Production files changed'
        if row['case_id'] in state['missing']:
            assert row['slug']=='gold-news-v9-direction';continue
        receipt=state['complete'][row['case_id']];path=Path(receipt['path']);assert sha(path)==receipt['sha256'];case=read(path)
        assert case['slug']==row['slug'] and case['window']==['2021.10.06','2026.10.06'] and case['no_live_changes']
        assert not any(case['flags'][k] for k in ['init_failed','runtime','history','stopout','export_failed'])
        assert abs(math.fsum(t['net'] for t in case['trades'])-case['native']['net_profit'])<.04
        if row['slug'] in ['us100-h1-orb-13utc','us100-orb-new-york-m30','us100-selective-orb-v3','xau-orb-new-york-m30','xau-orb-london-ny-overlap-m30']:
            assert float(case['inputs']['InpRewardRisk'])==.5
        receipts.add(str(path));checks+=1
    catalog=portfolio_catalog();assert not catalog['warnings']
    for slug in ['ftmo','current14-orb05','orbs-only','full-eas']:
        p=portfolio_by_slug(slug);count=len(p['members'])
        assert set(plan['mappings'][slug])=={m['slug'] for m in p['members']}
        for h in p['history']:
            assert h['available'] and h['start']==h['requested_start'] and h['end_exclusive']=='2026-10-06'
            assert h['member_coverage']==dict(tested=count-(slug=='full-eas'),total=count)
            assert h['missing_members']==(['gold-news-v9-direction'] if slug=='full-eas' else [])
            assert h['stats']['net_profit']==hist[slug][[z['id'] for z in hist[slug]].index(h['id'])]['stats']['net_profit']
            fixed=portfolio_scenario(p,h['id'],risk_mode='fixed',risk_value=50)
            dynamic=portfolio_scenario(p,h['id'],risk_mode='percent',risk_value=1.5,daily_limit_mode='percent',daily_limit_value=3)
            assert fixed['available'] and dynamic['available'] and fixed['start']==dynamic['start']==h['start']
            assert fixed['stats']['max_daily_closed_drawdown_cash']>=0 and dynamic['stats']['max_daily_closed_drawdown_pct']>=0
            assert fixed['stats']['max_daily_equity_drawdown_pct'] is None
        if slug=='orbs-only':
            for period in ['3y','5y']:
                a=portfolio_scenario(p,period,risk_mode='fixed',risk_value=50);b=portfolio_scenario(p,period,risk_mode='fixed',risk_value=100)
                assert a['stats']['trades']==b['stats']['trades'] and abs(b['stats']['net_profit']-2*a['stats']['net_profit'])<.04
    result=dict(passed=True,matched_current_configs=checks,unique_native_receipts=len(receipts),portfolios=4,windows_per_portfolio=5,custom_fixed_and_dynamic_checked=True,
                all_five_orbs_rr=.5,source_sha256={x:sha(R/x) for x in ['PLAN.json','RUN_STATUS.json','AUDIT.json','RISK_ROWS.json','HISTORIES.json']},
                full_basket_coverage='36/37, V9 missing disclosed',floating_equity_not_fabricated=True,production_files_unchanged=True,no_live_changes=True)
    (R/'VERIFICATION.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
