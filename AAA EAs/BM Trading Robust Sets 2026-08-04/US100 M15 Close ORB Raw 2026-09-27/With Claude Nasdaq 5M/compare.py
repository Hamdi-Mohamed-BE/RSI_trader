"""Offline portfolio addition only. No terminal/API connection or deployment."""
from pathlib import Path
import hashlib, importlib.util, random

ROOT = Path(__file__).resolve().parent
ORB = ROOT.parent
BASE = ORB.parent
DIROOT = BASE / 'FTMO Exit Management Research 2026-09-27' / 'Claude Nasdaq and Gold News Followup'
spec = importlib.util.spec_from_file_location('di_followup', DIROOT / 'compare_additions.py')
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
f, a, c = d.f, d.a, d.c
N, SEED, HS = 1000, 20260926, d.HS
CONFIGS = [
    dict(id='M', control='J', name='Eight + Nasdaq 5M DI', target=None),
    dict(id='M50', control='O50', name='Eight + ORB 0.50R + Nasdaq 5M DI', target='half'),
    dict(id='M33', control='O33', name='Eight + ORB 1/3R + Nasdaq 5M DI', target='third'),
]

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name, obj): c.save(ROOT / name, obj)
def num(v, places=2): return '—' if v is None else f'{v:,.{places}f}'
def cash(v): return ('−' if v < 0 else '+') + '$' + num(abs(v))

def orb_rows(target):
    folder = ORB / 'native' / ('aligned-' + target)
    meta, trades = c.read(folder/'run.json'), c.read(folder/'trades.json')
    assert meta['ok'] and meta['delay_ms'] == 150
    assert meta['metrics']['history_quality'] == '100% real ticks'
    audit = c.read(folder/'AUDIT.json')
    assert audit['no_lookahead_bar_checks'] and audit['verified_signal_entries'] == len(trades)
    orders = a.orders(a.report_text(folder/'report.htm.gz'))
    rows = []
    for t in trades:
        op, cl = a.epoch(t['open_time']), a.epoch(t['close_time'])
        oo = orders[op, t['symbol'], t['side']]
        assert len(oo) == 1 and cl > op
        stop = oo[0]['stop']; sign = 1 if t['side'] == 'Long' else -1
        assert sign * (t['open_price'] - stop) > 0
        assert abs(sign*(t['close_price']-t['open_price'])*t['volume']-t['gross_profit']) < .03
        rows.append(dict(t, key='us100-m15-close-orb/'+target, news=False, op=op, cl=cl,
            stop=stop, target=oo[0]['target'], unit_risk=abs(t['open_price']-stop),
            risk_quality='native_initial_order', unit_gross=t['gross_profit']/t['volume'],
            unit_comm=t['commission']/t['volume'], unit_swap=t['swap']/t['volume']))
    assert abs(sum(t['net_profit'] for t in trades)-meta['metrics']['net_profit']) < .1
    return rows

def report(out):
    lines = ['# Nasdaq 5M DI added to the US100 ORB comparison', '',
        'Research only — 27 September 2026. No live setup, EA, BAT, website or account changed.', '',
        '## Scope and frozen method', '',
        'M adds Claude\'s verified Nasdaq 5M Momentum DI version to the previous eight-EA research basket. M50/M33 also add one of the new US100 M15 ORBs; the two new ORB targets are alternatives, never traded together.', '',
        'Claude version: DI agreement ON, period 14; EMA12; 09:30 New York M5 signal; fixed 2.5R target; ATR trailing, breakeven and dynamic trailing OFF. This is not the experimental wider-stop/ATR version. Nasdaq Overnight remains a separate EA.', '',
        'Historical comparison: 4 March–30 August 2026, $10,000 start, 180 calendar days / 128 weekdays. This is the existing matched portfolio window, NOT the newer March–September standalone ORB window.', '',
        'Evidence: saved native Exness real-tick MT5 ledgers with 150 ms delay, revalidated and replayed under one shared controller. No new MT5 run, optimization, live trading, or native FTMO combined-account test. New work is the shared-account replay and 6,000 matched Monte Carlo paths (three portfolios, two cost cases, 1,000 each).', '',
        'Ordinary risk ceiling $71.43 per trade; news $10 per pending side. Both news sides remain reserved. Daily admission $300, aggregate initial risk $225, correlated-metal/per-symbol risk $150, projected buffer $9,200, max seven entries/day, admission stop after three closed losses, strict 0.01-lot rounding down, 80% margin ceiling and modeled 1:15 instrument leverage. Existing strategies retain priority on simultaneous admissions.', '',
        'Reference costs retain native fills and commission floors. Stress is the same hypothetical sensitivity: gross wins −10%, gross losses +10%, extra Nasdaq cost 2 points, ordinary gold $0.20, gold news $1, silver $0.04, doubled negative swap/carry. These are NOT measured FTMO execution costs.', '',
        '## Continuous shared-account results', '',
        'Cash figures are trading P&L, not payouts. Closed DD uses realized balance; reserve DD includes a modeled open-stop reserve and is NOT actual combined intratrade equity DD.', '']
    names = {'J':'Eight EAs','O50':'Eight + ORB 0.50R','O33':'Eight + ORB 1/3R', **{v['id']:v['name'] for v in CONFIGS}}
    allcases = {(x['id'], x['stress']):x for x in out['controls']+out['cases']}
    for stress in (True, False):
        lines += ['### '+('Stressed costs' if stress else 'Reference costs'), '',
            '| Portfolio | Trades | /30 days | /weekday | Net USD | Return | Win rate | PF | Closed DD | Reserve DD proxy | Max W/L |',
            '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
        for ident in ('J','M','O50','M50','O33','M33'):
            z=allcases.get((ident,stress))
            if not z: continue
            h,q=z['historical'],z['frequency']; profit=h['balance']-10000
            lines.append(f"| {names[ident]} | {h['trades']} | {num(q['trades_per_30_days'])} | {num(q['trades_per_weekday'])} | {cash(profit)} | {num(profit/100)}% | {num(h['win_rate'])}% | {num(h['pf'])} | {num(h['closed_dd_pct'])}% | {num(h['model_dd_pct'])}% | {h['max_win_streak']}/{h['max_loss_streak']} |")
        lines += ['']
    lines += ['## Conditional FTMO milestones — stressed costs', '',
        '1,000 matched paths per case. These frequencies are conditional on resampling 26 selected historical weeks, not calibrated future probabilities. Existing news and DI selection overlap this history.', '',
        '| Portfolio | Funded 30d | Paid 60d | Paid 120d | Funded 180d | Paid 180d | Breached before reward | Internal buffer touched | Median paid days* |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for ident in ('J','M','O50','M50','O33','M33'):
        z=allcases.get((ident,True))
        if not z: continue
        s=z['summary']; hz={h['days']:h for h in s['horizons']}
        vals=[hz[30]['funded_pct'],hz[60]['payout_pct'],hz[120]['payout_pct'],hz[180]['funded_pct'],hz[180]['payout_pct'],hz[180]['breach_before_first_reward_pct']]
        lines.append('| '+names[ident]+' | '+' | '.join(num(v,1)+'%' for v in vals)+f" | {s['paths_touching_internal_total_buffer']}/{N} | {num(s['timing']['payout_days_from_purchase']['median'],1)} |")
    lines += ['', '*Median only among paths receiving a reward within 180 days. Unfinished/risk-blocked paths are not counted as blown. Zero modeled breaches is not zero real risk.', '',
        '## Nasdaq 5M contribution and full-basket change — stress', '',
        '| Portfolio | DI trades | DI win rate | DI PF | DI net | Whole-basket profit change | 180d payout change |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for z in out['cases']:
        if not z['stress']: continue
        h=z['historical']; v=h['by_ea'].get(d.DI); old=allcases[z['control'],True]
        assert v
        p=z['summary']['horizons'][-1]['payout_pct']-old['summary']['horizons'][-1]['payout_pct']
        lines.append(f"| {names[z['id']]} | {v['trades']} | {num(100*v['wins']/v['trades'])}% | {num(v['positive']/v['negative'] if v['negative'] else None)} | {cash(v['net'])} | {cash(h['balance']-old['historical']['balance'])} | {p:+.1f} pp |")
    lines += ['', 'Marginal portfolio effects differ from the DI EA\'s own P&L because shared limits may block or displace other trades.', '',
        '## Monthly cash P&L — stress', '', '| Month | Eight | +DI | +ORB 0.50R | +ORB 0.50R +DI | +ORB 1/3R | +ORB 1/3R +DI |', '|---|---:|---:|---:|---:|---:|---:|']
    for month in range(3,9):
        stamp=f'2026-{month:02d}'; vals=[]
        for ident in ('J','M','O50','M50','O33','M33'):
            z=allcases.get((ident,True))
            vals.append(cash(sum(t['net_profit'] for t in z['historical']['log'] if t['close'].startswith(stamp))) if z else '—')
        lines.append('| '+stamp+' | '+' | '.join(vals)+' |')
    lines += ['', 'March and August are partial months. No withdrawals modeled in continuous-account figures.', '',
        '## Limits', '',
        '- Same FTMO research model: 10%/5% phase targets, four trading days per phase, 5% daily and 10% static loss; Prague reset. Review delays two business days between phases and five to funded; reward eligibility after 14 days, flat and $25 profit, receipt four business days later, 80% share. Administrative delays are assumptions.',
        '- Stop-reserve DD cannot establish actual daily-equity compliance. Gaps, outages, margin rules and stop slippage can exceed assumptions. No disqualification probability is modeled.',
        '- The unmodified DI build retried failed session closes on 6 March and carried a trade to 8 March. Those outcomes remain in the ledger. Its broker-session exit handling needs review before deployment.',
        '- New ORB 0.50R also has a retained July market-closure hold. Fixed-time exit requests cannot execute during closed markets.',
        '- Selected/fitted history is not out-of-sample validation. Weekly resampling does not preserve future macro-release calendars. Outcomes stop at first reward request or 180 days, not lifetime account survival.',
        '- Shared-controller skipped trades may change subsequent EA state; the saved-ledger overlay does not recreate this feedback. Pending news gross-margin reservations are conservative model rules, not verified FTMO order checks.',
        '- News-straddle permission needs clarification under prohibited gap-trading practices. Nothing deployed or promoted.', '',
        '## Evidence', '',
        'FROZEN.json stores versions, settings and input hashes before replay. RESULTS.json retains controls, new historical ledgers and all 6,000 compact paths. CHECKS.json verifies old controls, exact nine-EA reproduction, cash/risk/funnel consistency and unchanged source hashes.', '',
        '- [FTMO objectives](https://ftmo.com/en/comparison-table/)',
        '- [FTMO prohibited practices](https://ftmo.com/en/forbidden-trading-practices/)', '']
    (ROOT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')

def main():
    c.verify_sources()
    evidence={}
    for frozen,field in ((ORB/'PORTFOLIO_FROZEN.json','hashes'),(DIROOT/'FROZEN.json','evidence_hashes')):
        for p,digest in c.read(frozen)[field].items():
            assert sha(Path(p))==digest,p
            evidence[p]=digest
        evidence[str(frozen)]=sha(frozen)
    for p in (ROOT/'compare.py',ORB/'RESULTS.json',DIROOT/'RESULTS.json'):
        evidence[str(p)]=sha(p)
    for target in ('half','third'):
        p=ORB/'native'/('aligned-'+target)/'AUDIT.json';evidence[str(p)]=sha(p)
    frozen=dict(configs=CONFIGS,paths_per_case=N,seed=SEED,historical_start=c.iso(HS),end_exclusive=c.iso(c.END),
        native_di=c.read(DIROOT/'NATIVE_FROZEN.json'),ordinary_risk=500/7,news_risk=10.,new_native_runs=0,evidence_hashes=evidence)
    save('FROZEN.json',frozen)
    old=c.read(ORB/'RESULTS.json');old_di=c.read(DIROOT/'RESULTS.json')
    out=dict(frozen=frozen,controls=old['cases'],cases=[])
    needed=list(dict.fromkeys((n,v) for n,v,_ in d.J['members']))
    native={(n,v):a.load_case(n,v) for n,v in needed}
    di,di_meta=d.load_di();out['native_di']=di_meta
    orb={t:orb_rows(t) for t in ('half','third')}
    checks=dict(inherited=a.six.checks(c.read(c.SOURCE/'prepared.json')),historical_control_parity=[],nine_ea_exact_parity=[])
    rng=random.Random(SEED);samples=[[rng.randrange(26) for _ in range(26)] for _ in range(N)]
    for cfg in CONFIGS:
        data,labels=f.body_data(d.J,native)
        if cfg['target']:
            key='us100-m15-close-orb/'+cfg['target'];data['rows'][key]=orb[cfg['target']];labels[key]='US100 M15 ORB '+cfg['target']
        pp=[dict(p) for p in data['placements'] if HS<=p['op']<c.END]
        rr=[dict(t) for rows in data['rows'].values() for t in rows if HS<=t['op']<c.END and t['cl']<c.END]
        for stress in (False,True):
            ns=a.six.make_engine('strict_round_down')
            control=next(z for z in old['cases'] if z['id']==cfg['control'] and z['stress']==stress)
            assert ns['replay'](rr,pp,HS,c.END,stress=stress,news_risk=10.,challenge=False,detail=True)==control['historical']
            checks['historical_control_parity'].append(dict(control=cfg['control'],stress=stress,full_ledger=True))
        data['rows'][d.DI]=di;labels[d.DI]='Claude Nasdaq 5M Momentum DI, 2.5R'
        keys=list(data['rows']);weeks=c.pool(data,a.ph.POOL_START,26)
        for stress in (False,True):
            ns=a.six.make_engine('strict_round_down');sims=[]
            for index,sample in enumerate(samples):
                rr,pp=c.sample_rows(data,keys,a.ph.POOL_START,weeks,sample,c.START,c.START+180*c.DAY)
                sims.append(ns['replay'](rr,pp,c.START,c.START+180*c.DAY,stress=stress,news_risk=10.))
                if (index+1)%250==0: print('PROGRESS',cfg['id'],stress,index+1,flush=True)
            rr=[dict(t) for rows in data['rows'].values() for t in rows if HS<=t['op']<c.END and t['cl']<c.END]
            pp=[dict(p) for p in data['placements'] if HS<=p['op']<c.END]
            hist=ns['replay'](rr,pp,HS,c.END,stress=stress,news_risk=10.,challenge=False,detail=True)
            hc=ns['replay'](rr,pp,HS,c.END,stress=stress,news_risk=10.,detail=True)
            summary=a.ph.summarize(sims,ns);paths=a.a.compact_paths(sims)
            if cfg['id']=='M':
                prev=next(x for x in old_di['cases'] if x['id']=='M' and x['stress']==stress)
                assert hist==prev['historical'] and summary==prev['summary'] and paths==prev['paths']
                checks['nine_ea_exact_parity'].append(dict(stress=stress,historical=True,summary=True,paths=N))
            case=dict(**cfg,stress=stress,labels=labels,historical=hist,historical_challenge=hc,frequency=f.freq(hist),summary=summary,aggregate180=c.summarize(sims,180),paths=paths)
            f.verify_run(case,ns);out['cases'].append(case);save('RESULTS.json',out);report(out)
            print('COMPLETE CASE',cfg['id'],stress,'net',round(hist['balance']-10000,2),'trades',hist['trades'],'paid180',summary['horizons'][-1]['payout_pct'],flush=True)
    for p,digest in evidence.items(): assert sha(Path(p))==digest,p
    for p,info in a.CFG['source_files'].items(): assert sha(Path(p))==info['sha256'],p
    checks.update(cases_validated=len(out['cases']),paths_checked=6000,unchanged_evidence_files=len(evidence),unchanged_production_sources=len(a.CFG['source_files']))
    assert len(out['cases'])==6
    save('CHECKS.json',checks)
    print('COMPLETE: 6000 new paths, source hashes, historical controls and exact nine-EA parity verified.',flush=True)

if __name__=='__main__':main()
