"""Offline paired shared-risk replay. No MT5 connection or deployment changes."""
from pathlib import Path
import csv,gzip,io,json,sys,random,statistics,hashlib
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
sys.path.insert(0,str(BASE/'FTMO Fourteen EA Study 2026-09-27'))
import study as s
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def epoch(x):return datetime.fromisoformat(x).replace(tzinfo=timezone.utc).timestamp()
def save(name,v):(ROOT/name).write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
begin=epoch('2025-09-29');end=epoch('2026-09-26')
src=BASE/'Daily Equity Controls Audit 2026-09-29/recent-ROWS.json'
ordinary=[r for r in read(src) if begin<=r['op']<end and r['cl']<end]
assert len({r['key'] for r in ordinary})==13
goldsrc=BASE/'QuantLab Gold Trio Pipeline 2026-09-30/native/ftmo-market-variant-1y/0-trades.csv.gz'
gold=[]
for raw in csv.DictReader(io.StringIO(gzip.decompress(goldsrc.read_bytes()).decode())):
    f=lambda k:float(raw[k])
    if not begin<=f('open_epoch')<end or f('close_epoch')>=end:continue
    vol=f('volume');risk=abs(f('open_price')-f('initial_sl'))*100
    assert vol>0 and risk>0
    assert abs(f('gross_profit')+f('commission')+f('swap')+f('fee')-f('net_profit'))<.03
    gold.append(dict(key='3-way-gold/'+raw['module'],symbol='XAUUSD',news=False,
        op=f('open_epoch'),cl=f('close_epoch'),open_price=f('open_price'),close_price=f('close_price'),
        side='Long' if f('side')>0 else 'Short',unit_risk=risk,
        unit_gross=f('gross_profit')/vol,unit_comm=(f('commission')+f('fee'))/vol,unit_swap=f('swap')/vol))
data=dict(rows={},placements=[])
for r in ordinary+gold:data['rows'].setdefault(r['key'],[]).append(r)
basekeys=sorted({r['key'] for r in ordinary});allkeys=sorted(data['rows'])
start=epoch('2026-10-05');poolstart=begin;nweeks=51
s.c.START=start;s.c.END=end;s.ph.HORIZONS=[30,60,90,120,180]
weeks=s.c.pool(data,poolstart,nweeks)
rng=random.Random(20261001);samples=[[rng.randrange(nweeks) for _ in range(26)] for i in range(1000)]
checks=s.unit_tests()
save('PROVENANCE.json',dict(source_files={str(p):sha(p) for p in [src,goldsrc,BASE/'FTMO Fourteen EA Study 2026-09-27/study.py',BASE/'FTMO Combination Study 2026-09-19/simulate.py']},
    start=s.iso(begin),end_exclusive=s.iso(end),baseline_keys=basekeys,added_keys=sorted(set(allkeys)-set(basekeys)),
    risk=50,paths=1000,seed=20261001,weeks=nweeks,checks=checks,
    model='Initial-stop reserve proxy, NOT M1/tick equity; final aggregated position cash for partial exits',
    guards='225 total,150 symbol,300 daily,9200 floor,7/day,3 losing closes; not daily -2/+4 liquidation',
    source_counts={k:len(v) for k,v in data['rows'].items()}))
out=[]
for name,keys in [('Current13 without new gold',basekeys),('Current14 with market gold',allkeys)]:
    for stress in [False,True]:
        ns=s.engine(50)
        rr=[dict(r) for k in keys for r in data['rows'][k]]
        hist=ns['replay'](rr,[],begin,end,stress=stress,guards=True,challenge=False,detail=True)
        hist['risk']=50;s.reconcile(hist)
        paths=[]
        for sample in samples:
            r,p=s.c.sample_rows(data,keys,poolstart,weeks,sample,start,start+180*s.DAY)
            paths.append(ns['replay'](r,[],start,start+180*s.DAY,stress=stress,guards=True))
        summary=s.ph.summarize(paths,ns)
        paid=[r['reward'] for r in paths if r['payout']]
        summary['median_first_reward_if_received']=statistics.median(paid) if paid else None
        summary['mean_first_reward_all_paths']=statistics.mean(r['reward'] if r['payout'] else 0 for r in paths)
        summary['both_pass_days']=s.ph.distribution([(s.ph.epoch(r['passes'][1]['time'])-start)/s.DAY for r in paths if len(r['passes'])==2])
        summary['request_days']=s.ph.distribution([(s.ph.epoch(r['request_at'])-start)/s.DAY for r in paths if r['eligible']])
        cell=dict(portfolio=name,stress=stress,historical=hist,summary=summary,
            trades_per_month=hist['trades']/((end-begin)/s.DAY/30.4375),trades_per_weekday=hist['trades']/260,
            added_trades=sum(v['trades'] for k,v in hist['by_ea'].items() if k.startswith('3-way-gold/')),
            added_net=sum(v['net'] for k,v in hist['by_ea'].items() if k.startswith('3-way-gold/')))
        out.append(cell);save('RESULTS.json',out)
        print(json.dumps(dict(portfolio=name,stress=stress,trades=hist['trades'],return_pct=(hist['balance']-10000)/100,pf=hist['pf'],win=hist['win_rate'],closed_dd=hist['closed_dd_pct'],added=cell['added_trades'],h180=summary['horizons'][-1],timing=summary['timing'])),flush=True)
save('CHECKS.json',dict(cash_reconciled=True,source_hashes_unchanged=all(sha(Path(p))==h for p,h in read(ROOT/'PROVENANCE.json')['source_files'].items()),paired_paths=4000))
