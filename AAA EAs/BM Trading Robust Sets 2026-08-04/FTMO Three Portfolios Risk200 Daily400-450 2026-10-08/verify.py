"""Independent saved-ledger, cash, timing, source and presentation audit."""
from pathlib import Path
from datetime import datetime, timedelta
from html.parser import HTMLParser
from collections import Counter
import hashlib, json, math, statistics

ROOT = Path(__file__).resolve().parent
DAY = 86400

def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def stamp(x): return datetime.fromisoformat(x).timestamp()
def eq(a,b): assert math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-7), (a,b)

class Parser(HTMLParser):
    def __init__(self): super().__init__(); self.stack=[]; self.counts=Counter()
    def handle_starttag(self,tag,attrs):
        self.counts[tag]+=1
        if tag not in {'meta','link','img','input','br','hr','wbr'}: self.stack.append(tag)
    def handle_endtag(self,tag): assert self.stack and self.stack.pop()==tag, tag

def main():
    d=read(ROOT/'Results.json'); n=d['paths_per_case']; syn=stamp(d['synthetic_start'])
    assert n==1000 and len(d['historical'])==9 and len(d['random_cases'])==45
    assert d['legacy_13_profile_actual_ea_count']==14
    profiles={x['name']:x for x in d['profiles']}; policies={x['name']:x for x in d['policies']}
    assert [x['ea_count'] for x in d['profiles']]==[4,14,9]
    assert set(profiles['hybrid9']['keys'])==set(profiles['orbs4']['keys'])|{
        'xau-rsi-vwap','gold-overnight-value-area','xau-trend-progression','3-way-gold','nasdaq-5m-candle-momentum'}
    for p,h in d['source_hashes'].items(): assert sha(p)==h, p
    pure=ROOT.parent/'FTMO Pure ORB Swing Portfolio 2026-10-08'; old=read(pure/'Results.json')
    oldhist={x['name']:x for x in old['historical']}
    for name,key in [('orbs4','orb_qualified_4'),('current14','current_ftmo_14')]:
        assert next(x for x in d['historical'] if x['profile']==name and x['policy']=='original_50')['portfolio']==oldhist[key]['portfolio']
    budgets=entries=0
    for x in d['historical']:
        m=x['portfolio']; log=x['log']; pol=policies[x['policy']]; entries+=len(log)
        assert len(log)==m['trades']==sum(z['trades'] for z in m['months'].values())
        assert set(m['contributions'])<=set(profiles[x['profile']]['keys'])
        assert m['cash_reconciled'] and m['open_at_end']==0
        eq(sum(z['net_profit'] for z in log),m['return_pct']*100)
        eq(sum(z['net'] for z in m['months'].values()),m['return_pct']*100)
        eq(sum(z['net'] for z in m['contributions'].values()),m['return_pct']*100)
        eq(m['balance_curve'][-1][1]-10000,m['return_pct']*100)
        eq(x['trades_per_weekday'],m['trades']/261)
        assert x['max_open_risk']<=225+1e-7
        for z in log+x['challenge']['log']:
            eq(z['planned_budget'],pol['risk'])
            assert 0<z['initial_risk']<=pol['risk']+1e-7
            assert z['lots']>=.01
            eq(z['lots']/.01,round(z['lots']/.01))
            assert z['prior_open_risk']+z['initial_risk']<=225+1e-7
            eq(z['admission_reserve'],1.25*z['initial_risk']+5.)
            assert z['day_anchor']-z['balance_before_entry']+z['prior_reserve']+z['admission_reserve']-z['entry_fee']<=pol['daily']+1e-7
            assert z['balance_before_entry']-z['prior_reserve']-z['admission_reserve']+z['entry_fee']>=9200-1e-7
            budgets+=1
        assert all(z['trading_days']>=4 for z in x['challenge']['passes'])
    checked=funnels=paired=0; timing=[]; baseline_paths={}
    for c in d['random_cases']:
        suffix='-stress' if c['stress'] else '-cooldown' if c['cooldown'] else ''
        prefix='PATHS-'+str(c['seed'])+'-'+str(c['block_weeks'])+'-'
        paths=read(ROOT/(prefix+c['profile']+'-'+c['policy']+suffix+'.json'))
        assert len(paths)==n; checked+=n
        refkey=(c['protocol'],c['profile'])
        if c['policy']=='original_50':
            baseline_paths[refkey]=paths
            if c['profile']!='hybrid9':
                key='orb_qualified_4' if c['profile']=='orbs4' else 'current_ftmo_14'
                assert paths==read(pure/(prefix+key+suffix+'.json'))
        before=lambda v,cut:v is not None and stamp(v)<cut
        for r in paths:
            assert len(r['passes'])<=2 and all(z['trading_days']>=4 for z in r['passes'])
            assert [z['phase'] for z in r['passes']]==list(range(1,len(r['passes'])+1))
            if len(r['passes'])==2: assert stamp(r['passes'][1]['time'])>stamp(r['passes'][0]['time'])
            if r['funded_at']: assert len(r['passes'])==2 and stamp(r['funded_at'])>stamp(r['passes'][1]['time'])
            if r['receipt_at']: assert stamp(r['receipt_at'])>stamp(r['request_at'])>stamp(r['funded_at'])
        for z in c['summary']:
            cut=syn+z['days']*DAY
            p1=sum(bool(r['passes']) and before(r['passes'][0]['time'],cut) for r in paths)
            both=sum(len(r['passes'])==2 and before(r['passes'][1]['time'],cut) for r in paths)
            funded=sum(before(r['funded_at'],cut) for r in paths)
            paid=sum(before(r['receipt_at'],cut) for r in paths)
            assert paid<=funded<=both<=p1<=n
            for count,key in ((p1,'phase1_pass_pct'),(both,'both_pass_pct'),(funded,'funded_pct'),(paid,'first_reward_received_pct')): eq(count*100/n,z[key])
            times=sorted((stamp(r['passes'][1]['time'])-syn)/DAY for r in paths if len(r['passes'])==2 and before(r['passes'][1]['time'],cut))
            assert len(times)==z['days_to_pass_both']['n']
            if times:
                eq(statistics.median(times),z['days_to_pass_both']['median'])
                eq(statistics.mean(times),z['days_to_pass_both']['mean'])
            reward=statistics.mean(r['reward'] if before(r['receipt_at'],cut) else 0. for r in paths)
            eq(reward,z['expected_first_reward_usd'])
            for f in z['expected_net_cash_and_fee_roi']:
                net=reward+paid/n*f['fee_usd']-f['fee_usd']
                eq(net,f['expected_net_cash']); eq(net/f['fee_usd']*100,f['expected_fee_roi_pct'])
            timing.append(dict(protocol=c['protocol'],profile=c['profile'],policy=c['policy'],horizon_days=z['days'],
                conditional_successful_median_days=statistics.median(times) if times else None,
                half_of_all_paths_completed_by_days=times[(n+1)//2-1] if len(times)>=(n+1)//2 else None,
                interpretation='Null means fewer than half of ALL starts completed within this horizon; conditional successful-run median is not an overall median.'))
            funnels+=1
        for z in c['paired_vs_original']:
            cut=syn+z['days']*DAY
            passed=lambda r:len(r['passes'])==2 and before(r['passes'][1]['time'],cut)
            new=sum(passed(r) and not passed(b) for r,b in zip(paths,baseline_paths[refkey]))
            lost=sum(passed(b) and not passed(r) for r,b in zip(paths,baseline_paths[refkey]))
            assert new==z['new_passes'] and lost==z['lost_passes']
            eq((new-lost)*100/n,z['net_change_pct']); paired+=1
        draws=read(ROOT/('DRAWS-'+str(c['seed'])+'-'+str(c['block_weeks'])+'.json'))['draws']
        assert draws==read(pure/('DRAWS-'+str(c['seed'])+'-'+str(c['block_weeks'])+'.json'))['draws']
    assert checked==45000 and funnels==180 and paired==90
    assert len(d['starts'])==603
    starts=Counter((x['profile'],x['policy'],x['horizon_days']) for x in d['starts'])
    for x in d['starts']:
        begin=datetime.fromisoformat(x['start']); end=datetime.fromisoformat(x['end_exclusive'])
        assert begin.weekday()==0 and begin+timedelta(days=x['horizon_days'])==end
        assert end<=datetime(2026,10,6)
        assert all(z['trading_days']>=4 for z in x['passes'])
    assert set(starts.values())=={40,27}
    plan=read(ROOT.parent/'ORB and Range Breakout RR05 Comparison 2026-10-08/PLAN.json')
    production={p:h for x in plan['setups'] for p,h in x['production_hashes'].items()}
    for p,h in production.items(): assert sha(p)==h,p
    (ROOT/'AGGREGATE_TIMING.json').write_text(json.dumps(timing,indent=2),encoding='utf-8')
    import report
    report.main()
    parser=Parser(); parser.feed((ROOT/'Results.html').read_text(encoding='utf-8'))
    assert not parser.stack and parser.counts['table']==14
    result=dict(paths_checked=checked,deadline_probability_funnels_checked=funnels,paired_comparisons_checked=paired,
        historical_cash_ledgers_checked=9,continuous_entries_checked=entries,entry_budgets_and_reserves_checked=budgets,
        source_hashes_checked=len(d['source_hashes']),production_files_unchanged=len(production),
        current_launcher_membership=14,requested_combined_membership=9,real_historical_start_windows_checked=603,
        baseline_history_and_paths_match=True,draws_matched=True,html_balanced=True,tables=14,
        tests=d['checks'],not_a_hard_floating_equity_stop=True,live_changes=False)
    (ROOT/'VERIFICATION.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
