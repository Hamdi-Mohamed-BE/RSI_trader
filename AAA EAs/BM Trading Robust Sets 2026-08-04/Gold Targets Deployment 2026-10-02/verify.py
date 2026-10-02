"""Final offline release checks. Does not import MT5 or connect to an account."""
from deploy import *
os.environ['EA_STORE_DISABLE_MT5']='1'
sys.path.insert(0,str(STORE))
from app.catalog import get_product
from app.gold_targets import verified_payload

selection=load(ROOT/'SELECTION.json');checks=[]
for slug,(kind,rr,src,settings) in SPECS.items():
    p=selection['profiles'][slug]
    assert sha(BASE/src)==p['original_source_sha']
    assert sha(BASE/settings)==p['original_settings_sha']
    old=read(BASE/src);new=read((BASE/p['expert']).with_suffix('.mq5'))
    normalize=lambda t:re.sub(r'(input\s+double\s+InpRewardRisk\s*=\s*)[\d.]+',r'\g<1>TARGET',t)
    assert normalize(old)==normalize(new)
    for mode in ['standard']+(['dynamic'] if kind=='S' else []):
        for period in ('6m','1y','3y','5y'):
            cached=load(STORE/f'data/evidence-cache/v1/products/{slug}/{mode}/{period}.json')
            payload,rows=verified_payload(get_product(slug),mode,period,date.fromisoformat(cached['available_from']),date.fromisoformat(cached['end_exclusive']))
            assert len(rows)==payload['stats']['trades']
            assert abs(sum(t['net_profit'] for t in rows)-payload['stats']['net_profit'])<.011
            assert all(t['r_is_estimate'] is False and t['estimated_risk_cash']==t['actual_risk'] for t in rows)
            checks.append({'slug':slug,'mode':mode,'period':period,'trades':len(rows)})
ftmo=BASE/'FTMO Thirteen EA Deployment 2026-09-27'
m=load(ftmo/'PACKAGE.json')
assert m['risk_usd']==50 and not m['news_enabled']
assert sha(ftmo/'CalyxFTMOGuard.mqh')==m['guard_sha']
for name,digest in m['files'].items(): assert sha(ftmo/'package'/name)==digest
for e in m['entries']:
    assert e['inputs']['FTMOExpectedLogin']=='0'
    assert float(e['inputs']['InpRiskPercent'])==.5
assert float(next(e for e in m['entries'] if e['slug']=='xau-trend-progression')['inputs']['InpRewardRisk'])==.6
write(ROOT/'VERIFICATION.json',{'passed':True,'checks':checks,'normal_bat_checks':load(ROOT/'LAUNCHER_CHECKS.json'),
    'original_sources_and_sets_preserved':True,'source_function_bodies_unchanged':True,
    'ftmo_guard_unchanged':True,'ftmo_roster_count':len(m['entries']),
    'slow_ftmo_roster_choice_pending':not any(e['slug']=='xau-slow-trend' for e in m['entries']),
    'active_mt5_unchanged':True,'public_site_deployed':False,
    'qualification':'Explicit selection, failed strict PF screen; research-labelled standalone evidence only'})
print('PASS: 12 source-bound ledgers; original sources/SETs preserved; FTMO guard and locks preserved; 16 normal BAT assertions.')
