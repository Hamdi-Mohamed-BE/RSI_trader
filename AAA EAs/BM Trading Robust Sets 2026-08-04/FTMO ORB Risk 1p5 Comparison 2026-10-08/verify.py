"""Independent reconciliation of saved risk budgets, cash and path summaries."""
from pathlib import Path
from datetime import datetime
from html.parser import HTMLParser
from collections import Counter
import hashlib,json,math,statistics
ROOT=Path(__file__).resolve().parent
DAY=86400
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def eq(a,b):assert math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-7),(a,b)
class Parser(HTMLParser):
    def __init__(self):super().__init__();self.stack=[];self.counts=Counter()
    def handle_starttag(self,tag,attrs):
        self.counts[tag]+=1
        if tag not in {'meta','link','img','input','br','hr','wbr'}:self.stack.append(tag)
    def handle_endtag(self,tag):assert self.stack and self.stack.pop()==tag,tag
def main():
    d=read(ROOT/'Results.json');n=d['paths_per_case'];syn=datetime.fromisoformat(d['synthetic_start']).timestamp()
    assert len(d['historical'])==3 and len(d['random_cases'])==15 and n==1000
    for p,h in d['sources'].items():assert sha(p)==h,p
    pure=ROOT.parent/'FTMO Pure ORB Swing Portfolio 2026-10-08'
    prior=read(pure/'Results.json')
    old=next(x for x in prior['historical'] if x['name']=='orb_qualified_4')
    assert d['historical'][0]['portfolio']==old['portfolio']
    assert d['shared_guard']==prior['profile']['shared_guard']
    allowed={x['slug'] for x in d['original_profile']}
    assert len(allowed)==4
    entries=0
    for x in d['historical']:
        m=x['portfolio'];log=x['log'];entries+=len(log)
        assert len(log)==m['trades']==sum(z['trades'] for z in m['months'].values())
        assert set(m['contributions'])<=allowed and m['cash_reconciled'] and m['open_at_end']==0
        eq(sum(z['net_profit'] for z in log),m['return_pct']*100)
        eq(sum(z['net'] for z in m['months'].values()),m['return_pct']*100)
        eq(sum(z['net'] for z in m['contributions'].values()),m['return_pct']*100)
        eq(m['balance_curve'][-1][1]-10000,m['return_pct']*100)
        eq(x['trades_per_weekday'],m['trades']/261)
        assert x['max_open_risk']<=225+1e-7
        for z in log+x['challenge']['log']:
            expected=.015*z['balance_before_entry'] if x['mode']=='balance_1p5' else 150. if x['mode']=='fixed_150' else 50.
            eq(expected,z['planned_risk_budget'])
            assert 0<z['initial_risk']<=min(expected,150.)+1e-7
            eq(z['lots']/.01,round(z['lots']/.01))
            assert z['lots']>=.01
        assert all(z['trading_days']>=4 for z in x['challenge']['passes'])
    checked=funnels=0
    for c in d['random_cases']:
        suffix='-stress' if c['stress'] else '-cooldown' if c['cooldown'] else ''
        paths=read(ROOT/('PATHS-'+str(c['seed'])+'-'+str(c['block_weeks'])+'-'+c['mode']+suffix+'.json'))
        assert len(paths)==n;checked+=n
        if c['mode']=='fixed_50':
            before=read(pure/('PATHS-'+str(c['seed'])+'-'+str(c['block_weeks'])+'-orb_qualified_4'+suffix+'.json'))
            assert paths==before
        for r in paths:
            assert len(r['passes'])<=2
            assert all(z['trading_days']>=4 for z in r['passes'])
            if r['funded_at']:
                assert len(r['passes'])==2 and datetime.fromisoformat(r['funded_at'])>datetime.fromisoformat(r['passes'][1]['time'])
            if r['receipt_at']:
                assert r['funded_at'] and r['request_at']
                assert datetime.fromisoformat(r['receipt_at'])>datetime.fromisoformat(r['request_at'])>datetime.fromisoformat(r['funded_at'])
        for z in c['summary']:
            cut=syn+z['days']*DAY
            before=lambda v:v is not None and datetime.fromisoformat(v).timestamp()<cut
            p1=sum(bool(r['passes']) and before(r['passes'][0]['time']) for r in paths)
            both=sum(len(r['passes'])==2 and before(r['passes'][1]['time']) for r in paths)
            funded=sum(before(r['funded_at']) for r in paths);paid=sum(before(r['receipt_at']) for r in paths)
            assert paid<=funded<=both<=p1<=n
            for count,key in ((p1,'phase1_pass_pct'),(both,'both_pass_pct'),(funded,'funded_pct'),(paid,'first_reward_received_pct')):eq(count*100/n,z[key])
            times=[(datetime.fromisoformat(r['passes'][1]['time']).timestamp()-syn)/DAY for r in paths if len(r['passes'])==2 and before(r['passes'][1]['time'])]
            assert len(times)==z['days_to_pass_both']['n']
            if times:eq(statistics.median(times),z['days_to_pass_both']['median']);eq(statistics.mean(times),z['days_to_pass_both']['mean'])
            reward=statistics.mean(r['reward'] if before(r['receipt_at']) else 0. for r in paths)
            eq(reward,z['expected_first_reward_usd'])
            for f in z['expected_net_cash_and_fee_roi']:
                net=reward+paid/n*f['fee_usd']-f['fee_usd']
                eq(net,f['expected_net_cash']);eq(net/f['fee_usd']*100,f['expected_fee_roi_pct'])
            funnels+=1
    assert checked==15000 and funnels==60
    plan=read(ROOT.parent/'ORB and Range Breakout RR05 Comparison 2026-10-08/PLAN.json')
    production={p:h for x in plan['setups'] for p,h in x['production_hashes'].items()}
    for p,h in production.items():assert sha(p)==h,p
    parser=Parser();parser.feed((ROOT/'Results.html').read_text(encoding='utf-8'))
    assert not parser.stack and parser.counts['table']==10
    result=dict(paths_checked=checked,deadline_probability_funnels_checked=funnels,
                historical_cash_ledgers_checked=3,historical_entry_budgets_checked=entries,
                planned_dynamic_balances_and_broker_rounding_checked=True,all_guards_unchanged=True,
                baseline_matches_previous_results=True,source_hashes_unchanged=True,
                production_files_unchanged=len(production),html_balanced=True,table_count=10,
                live_changes=False,tests=d['checks'])
    (ROOT/'VERIFICATION.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
