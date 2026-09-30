"""Read-only-source portfolio addition study. Never imports or connects to MT5."""
from __future__ import annotations
import ast
import hashlib
import html
import json
import math
import random
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path
import compare as c
import phase_breakdown as ph

BASE = c.ROOT.parent
CACHE = BASE.parent / 'EA store/data/evidence-cache/v1'
RSI = 'xau-rsi-vwap/standard'
DI = 'nasdaq-5m-candle-momentum/dynamic'
CORE = [c.RAW] + c.NEWS
CONFIGS = [dict(name=name, keys=keys, risk=500/7, news_risk=10.) for name, keys in [
    ('Core: Raw Gold + XAU/XAG news', CORE),
    ('Core + Gold RSI VWAP', CORE + [RSI]),
    ('Core + Nasdaq 5M DI', CORE + [DI]),
    ('Core + Gold RSI VWAP + Nasdaq 5M DI', CORE + [RSI, DI])]]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_di():
    # Reuse only pure parsing definitions. Do not import website/terminal modules.
    parser_path = CACHE.parents[2] / 'app/mt5_evidence_jobs.py'
    ns = dict(html=html, re=re, Path=Path, TAG_RE=re.compile(r'<[^>]+>'),
              defaultdict=defaultdict, datetime=c.datetime, timezone=c.timezone)
    for path, names in [(parser_path, {'_read_report', '_clean', '_number'}),
                        (c.SOURCE/'prepare.py', {'dt', 'orders'})]:
        tree = ast.parse(path.read_text(encoding='utf-8-sig'))
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
        assert {n.name for n in nodes} == names
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), ns)
    trades_path = CACHE/'products'/DI/'5y.trades.json'
    report_path = CACHE/'source-runs'/DI/'5y.htm'
    meta_path = report_path.with_suffix('.meta.json')
    set_path = BASE/'Selected Portfolio Settings 2026-09-01/11 Nasdaq 5M Candle Momentum - OPTIMIZED 2P5R + DI AGREE M5 - HARD 1PCT.set'
    expert = BASE/'Active Portfolio Full Pipeline 2026-09-05/11 Nasdaq 5M Candle Momentum/EA/Nasdaq 5M Candle Momentum DI EA.ex5'
    meta = c.read(meta_path)
    assert meta['expert_sha256'] == sha(expert) == '49c4f03622a8ec7fb8e70db990a2f19b3006b5641aeb915a5d7f2454f26bab35'
    assert meta['settings_sha256'] == sha(set_path)
    native = ns['orders'](report_path)
    raw_rows = c.read(trades_path)
    out = []
    for raw in raw_rows:
        op, cl = ns['dt'](raw['open_time']), ns['dt'](raw['close_time'])
        match = native.get((op, raw['symbol'], raw['side']), [])
        assert len(match) == 1, (raw['number'], match)
        stop = match[0]['stop']
        sign = 1 if raw['side'] == 'Long' else -1
        assert sign*(raw['open_price']-stop) > 0
        assert cl > op and raw['volume'] > 0
        assert abs(raw['gross_profit']+raw['commission']+raw['swap']-raw['net_profit']) < .04
        # USTEC contract cash value is $1/point/lot; verify native profit rounding.
        expected = sign*(raw['close_price']-raw['open_price'])*raw['volume']
        assert abs(expected-raw['gross_profit']) < .021, (raw['number'], expected)
        out.append(dict(raw, key=DI, news=False, symbol='USTEC', op=op, cl=cl,
                        stop=stop, target=match[0]['target'],
                        unit_risk=abs(raw['open_price']-stop),
                        risk_quality='native_entry_order',
                        unit_gross=raw['gross_profit']/raw['volume'],
                        unit_comm=raw['commission']/raw['volume'],
                        unit_swap=raw['swap']/raw['volume']))
    assert len(out) == 971
    evidence = dict(native_rows=len(out), accepted_before_cutoff=sum(r['op']<c.END for r in out),
                    missing_or_ambiguous_stops=0, report_metadata=meta,
                    files={str(p):sha(p) for p in (trades_path, report_path, meta_path, set_path, expert, parser_path)})
    return sorted([r for r in out if r['op'] < c.END], key=lambda r:r['cl']), evidence

def compact_paths(rr):
    fields = ('passes','funded_at','request_at','receipt_at','breach_at','phase','reward',
              'trades','counts','by_ea','model_dd_pct','closed_dd_pct','worst_daily_usd')
    return [dict(id=i, **{k:r[k] for k in fields}) for i,r in enumerate(rr)]

def paired(base, new, field, days):
    cutoff = c.START+days*c.DAY
    b = [ph.happened(ph.epoch(r[field]), cutoff) for r in base]
    a = [ph.happened(ph.epoch(r[field]), cutoff) for r in new]
    d = [int(x)-int(y) for x,y in zip(a,b)]
    diff = statistics.mean(d)*100
    se = statistics.stdev(d)/math.sqrt(len(d))*100
    return dict(delta_percentage_points=diff, new_only=sum(x and not y for x,y in zip(a,b)),
                core_only=sum(y and not x for x,y in zip(a,b)),
                paired_mc_only_interval=[diff-1.96*se,diff+1.96*se])

def report(out):
    lines = ['# FTMO $10K Swing: adding Gold RSI VWAP and Claude Nasdaq 5M DI', '',
        'Offline research, 26 September 2026. No live account, EA, launcher, website or trading settings changed.', '',
        '## Scope and method', '',
        'Core = raw Gold Overnight Value Area + News Pulse XAU + News Pulse XAG. RSI VWAP means the separate gold EA; it is not an extra indicator bolted onto Nasdaq. Nasdaq means Claude\'s promoted DI-filter build (DI period 14, EMA 12, 09:30 NY M5 signal, fixed 2.5R, ATR trailing OFF). It is NOT Nasdaq Overnight or the original no-DI bot.', '',
        'All four portfolios use the same $10,000 account, $71.43 nominal fixed-dollar risk per ordinary entry and $10 per news side. Broker lot rounding can increase actual risk. This study does not apply the production Recommended Adaptive 0.25x Nasdaq multiplier. Both news sides stay available, subject to shared gates.', '',
        'Shared gates: $300 daily admission budget, $225 simultaneous initial risk, $150 metals/per-symbol risk, $9,200 internal equity buffer, seven entries/day and no new entries after three closed losses; 80% maximum reserved margin. Ordinary stressed floating-loss reserve 1.25R; news 2R. Full assumptions: PROTOCOL.md.', '',
        '1,000 matched 180-day paths per portfolio and cost case, using joint weekly blocks from 2 March–30 August 2026; seed 20260926. Same draws and limits for every combination. Historical replay uses 4 March–30 August 2026. September is excluded to preserve comparability with the existing core study.', '',
        'This is a saved native-MT5-ledger portfolio simulation, NOT a fresh FTMO tick backtest. News presets were fitted on the same history; the DI rule was selected on Sep 2025–Apr 2026, partly overlapping this sample. No independent out-of-sample forecast is claimed. Small samples, regime change, weekly-resampling limitations and selection bias dominate Monte Carlo sampling error.', '',
        'FTMO modeling: 10% then 5% targets, four trading days per evaluation phase, $500 daily/$1,000 static loss limits, Prague midnight, no time limit. Administrative assumptions: two business days to Phase 2, five to funded, first reward after 14 calendar days of funded trading while flat, four business days to receipt; 80% profit share. Stops at first reward request or day 180; no lifetime survival estimate.', '',
        'Reference costs retain native spread/gaps with commission floors. Stress reduces gross wins 10%, enlarges gross losses 10%, adds slippage (2 USTEC points; $0.20 ordinary gold/$1 news gold; $0.04 silver), doubles negative swaps and adds overnight carry reserve.', '',
        '## Source availability', '', '| EA | Source trades in 26 weeks |', '|---|---:|']
    for k,n in out['source_entries'].items(): lines.append(f'| {k} | {n} |')
    for stress in (True, False):
        lines += ['', '## '+('Stressed execution' if stress else 'Reference execution'), '',
                  '| Portfolio | Funded 30d | Funded 60d | Funded 120d | Funded 180d | Paid 60d | Paid 120d | Paid 180d | Median days to funded* |',
                  '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
        cases = [r for r in out['cases'] if r['stress']==stress]
        for r in cases:
            h = {x['days']:x for x in r['summary']['horizons']}
            vals = [h[d]['funded_pct'] for d in (30,60,120,180)]+[h[d]['payout_pct'] for d in (60,120,180)]
            median = r['summary']['timing']['funded_days_from_purchase']['median']
            lines.append('| '+r['config']['name']+' | '+' | '.join(f'{v:.1f}%' for v in vals)+f' | {median:.1f} |')
        lines += ['', '*Timing is conditional on completion by day 180; unfinished paths are censored, not failed.', '',
                  '### Historical shared-account replay (no withdrawals or phase resets)', '',
                  '| Portfolio | Admitted trades | Net USD | Win rate | PF | Closed-balance DD | Stop-reserve DD proxy | Worst modeled day | Max win/loss streak | News baskets admitted |',
                  '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
        for r in cases:
            h=r['historical_continuous']
            lines.append(f"| {r['config']['name']} | {h['trades']} | ${h['balance']-10000:,.2f} | {h['win_rate']:.2f}% | {h['pf']:.2f} | {h['closed_dd_pct']:.2f}% | {h['model_dd_pct']:.2f}% | ${h['worst_daily_usd']:.2f} | {h['max_win_streak']}/{h['max_loss_streak']} | {h['counts'].get('news_baskets',0)} |")
        lines += ['', 'Historical P&L is hypothetical evaluation trading profit, NOT a payout. Stop-reserve DD is not tick-measured equity DD; neither stops nor reserves bound gap losses.', '',
                  '### Phase timing and safety', '',
                  '| Portfolio | P1 median days* | P2 median days* | Paid median days* | Breaches before first reward, 180d | Paths hitting $9,200 admission gate | 95th percentile reserve DD |',
                  '|---|---:|---:|---:|---:|---:|---:|']
        for r in cases:
            s=r['summary'];t=s['timing'];a=r['aggregate180']
            lines.append(f"| {r['config']['name']} | {t['phase1_days_among_phase1_passers']['median']:.1f} | {t['phase2_days_from_availability_among_phase2_passers']['median']:.1f} | {t['payout_days_from_purchase']['median']:.1f} | {s['horizons'][-1]['breach_before_first_reward_pct']:.1f}% | {s['paths_touching_internal_total_buffer']}/1000 | {a['p95_stop_envelope_dd_pct']:.2f}% |")
        lines += ['', 'Phase 2 timing starts at its account availability, excluding the prior review delay. Milestone timing cohorts differ; their medians should not be added.', '',
                  '### Matched-path changes versus core at 180 days', '',
                  '| Addition | Funding change (pp) | Payout change (pp) | Payout only with addition | Payout only with core | Payout paired MC-only 95% interval (pp) |',
                  '|---|---:|---:|---:|---:|---:|']
        for r in cases[1:]:
            p=r['paired180'];f=p['funded'];v=p['paid'];ci=v['paired_mc_only_interval']
            lines.append(f"| {r['config']['name']} | {f['delta_percentage_points']:+.1f} | {v['delta_percentage_points']:+.1f} | {v['new_only']} | {v['core_only']} | {ci[0]:+.1f} to {ci[1]:+.1f} |")
        lines += ['', 'These intervals measure random path sampling only, not real-world forecast accuracy.', '',
                  '### Historical per-EA attribution in the five-EA combination', '',
                  '| EA | Trades | Wins | Net USD |', '|---|---:|---:|---:|']
        for k,v in cases[-1]['historical_continuous']['by_ea'].items():
            lines.append(f"| {k} | {v['trades']} | {v['wins']} | ${v['net']:,.2f} |")
    lines += ['', '## Important limits', '',
        '- Zero breaches in these paths does not establish zero real breach probability. Intratrade FTMO bid/ask equity, abrupt gaps, outages, liquidity/rejections, changing margin and contractual disqualification are not fully modeled.',
        '- The model stops at the first reward request; continued funded-account survival and post-withdrawal drawdown are not tested.',
        '- Swing allows news trading generally, but this does not confirm that the exact pre-release two-sided stop strategy meets FTMO forbidden-practice conditions. Written eligibility clarification is still needed.',
        '- Existing news production builds hard-lock a different risk level. The $10/order and shared FTMO gates are research assumptions, not a deployable claim. No launcher has been created or changed.',
        '- More trades do not guarantee faster passing: losses, correlated exposure, margin competition and daily admission limits matter. No parameters were optimized for this comparison.', '',
        '## Interpretation of the actual historical sequence', '',
        'Under stressed execution the five-EA combination closed its final trade on 18 March 2026, after only 18 trades, at $9,227.46. It then could not admit another trade while reserving losses above the $9,200 internal buffer: 194 ordinary signals and 26 news baskets were rejected by that buffer. It did not breach the modeled FTMO hard limit, but it did not pass either phase or receive a payout. The reference-cost version also stalled ($9,212.27, 25 trades). These are sequence-dependent failures to progress, not successful low-drawdown outcomes.', '',
        'Adding only Nasdaq DI reduced historical admitted news baskets from 24 to 21 under stress, and gold news fills from 10 to 6. Margin-rejected news baskets increased from six to nine. Adding only RSI VWAP reduced admitted raw Gold trades from 97 to 85; its own 30 trades made a net loss of $283.28 despite winning 20 trades. These effects are specific to this period and sizing.', '',
        '**Sizing caveat:** $71.43 is a nominal target in this inherited simulation, not a strict cash-risk cap. It rounds UP to a 0.01-lot step; the largest admitted initial trade risk was $140.79 in the RSI addition historical case. A deployment requiring a hard $71.43 ceiling must round down (or skip the trade if the minimum lot is too large) and be retested. Do not interpret these results as testing a strict $71.43 maximum.', '',
        'At the tested nominal allocation, keep the core as the stronger six-month candidate; do not add both at full ordinary risk based on this evidence. Nasdaq improved early completion rates among modeled paths, but not overall six-month success. A reduced Nasdaq allocation would be a separate test, not a proven remedy. Neither this comparison nor the core itself has established reliable real-world pass or payout probabilities.', '',
        '## Verification', '',
        'DI cache EX5 hash matches the promoted production DI binary; 971 native trades have uniquely reconstructed initial stops and reconciled cash P&L. All original source hashes, nine engine tests, seven adapter checks, eight historical parity fields and eleven phase tests passed. Core funding/payout percentages match the prior phase study exactly at every horizon.', '',
        '[FTMO comparison](https://ftmo.com/en/comparison-table/) · [Reward rules](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/) · [Swing](https://ftmo.com/en/faq/ftmo-swing-account-type/) · [Forbidden practices](https://ftmo.com/en/forbidden-trading-practices/)', '']
    (c.ROOT/'ADDITIONS_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')

def main():
    c.verify_sources()
    data=c.read(c.SOURCE/'prepared.json')
    data['rows'][DI], evidence=load_di()
    ns=c.engine()
    validation=c.tests(data)
    validation['phase_checks']=ph.checks(ns)
    weeks=c.pool(data,ph.POOL_START,26)
    counts={k:sum(map(len,weeks[k])) for k in CORE+[RSI,DI]}
    print('AUDIT', json.dumps(dict(di=evidence,source_entries=counts,checks=validation)),flush=True)
    if '--audit-only' in sys.argv:return
    c.save(c.ROOT/'ADDITIONS_FROZEN.json',dict(configs=CONFIGS,paths=1000,seed=20260926,
        pool_start=c.iso(ph.POOL_START),pool_end=c.iso(c.END),di=evidence,source_entries=counts))
    rng=random.Random(20260926)
    samples=[[rng.randrange(26) for _ in range(26)] for _ in range(1000)]
    out=dict(configs=CONFIGS,paths=1000,seed=20260926,di=evidence,source_entries=counts,
             checks=validation,cases=[])
    prior=c.read(c.ROOT/'PHASE_RESULTS.json')['cases']
    controls={}
    for config in CONFIGS:
        for stress in (False,True):
            ns['RISK']=config['risk'];rr=[]
            for sample in samples:
                rows,places=c.sample_rows(data,config['keys'],ph.POOL_START,weeks,sample,c.START,c.START+180*c.DAY)
                rr.append(ns['replay'](rows,places,c.START,c.START+180*c.DAY,news_risk=10.,stress=stress))
            s=ph.summarize(rr,ns)
            if config==CONFIGS[0]:
                old=next(r for r in prior if r['config']['keys']==CORE and r['stress']==stress)
                for new,want in zip(s['horizons'],old['summary']['horizons']):
                    assert new==want,(new,want)
                controls[stress]=rr
            hs=c.END-180*c.DAY
            rows=[dict(r) for k in config['keys'] for r in data['rows'][k] if hs<=r['op']<c.END and r['cl']<c.END]
            places=[dict(p) for p in data['placements'] if p['key'] in config['keys'] and hs<=p['op']<c.END]
            hist=ns['replay'](rows,places,hs,c.END,news_risk=10.,stress=stress,challenge=False,detail=True)
            hc=ns['replay'](rows,places,hs,c.END,news_risk=10.,stress=stress,detail=True)
            pairs={label:paired(controls[stress],rr,field,180) for label,field in [('funded','funded_at'),('paid','receipt_at')]}
            out['cases'].append(dict(config=config,stress=stress,summary=s,
                aggregate180=c.summarize(rr,180),historical_continuous=hist,historical_challenge=hc,
                paired180=pairs,paths=compact_paths(rr)))
            c.save(c.ROOT/'ADDITIONS_RESULTS.json',out)
            print(config['name'],'stress' if stress else 'reference',
                  json.dumps(dict(funded=s['horizons'][-1]['funded_pct'],paid=s['horizons'][-1]['payout_pct'],
                  days=s['timing']['funded_days_from_purchase']['median'],historical_net=hist['balance']-10000,
                  trades=hist['trades'],wr=hist['win_rate'],dd=hist['model_dd_pct'])),flush=True)
    report(out)
    print('COMPLETE 8,000 paths; baseline parity verified.',flush=True)

if __name__=='__main__':main()
