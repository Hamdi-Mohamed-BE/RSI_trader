"""Audit and publish local research artifacts, without touching trading or production."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json, hashlib, subprocess, sys
import numpy as np
import simulate as s

ROOT=s.ROOT
NAMES=['FTMO 0.25% tighter','FTMO 0.50% tighter','FTMO 0.50% existing guards',
       'Instant 0.15% full basket','Instant 0.25% full basket','Instant 0.25% core4','Instant core4 / withdraw all']
def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(map(str,r))+' |' for r in rows])+'\n'
def pct(x):return f'{x:.1f}%'
def money(x):return f'${x:,.2f}'
def timing(x):return 'Not reached' if x is None else f"{x['median']:.1f} ({x['p10']:.1f}–{x['p90']:.1f}); n={x['n']}"
def phase2_duration(xs):
    out=[];start=datetime(2026,9,28,tzinfo=timezone.utc)
    for row in xs:
        p1,p2=row[9],row[10]
        if p2<0:continue
        ready=start+timedelta(minutes=float(p1));n=2
        while n:
            ready+=timedelta(days=1)
            if ready.weekday()<5:n-=1
        out.append(p2/1440-(ready-start).total_seconds()/86400)
    return {'n':len(out),'median':float(np.median(out)),'p10':float(np.quantile(out,.1)),'p90':float(np.quantile(out,.9))} if out else None

def main():
    a=s.read(ROOT/'AUDIT.json');r=s.read(ROOT/'RESULTS.json');b=s.read(ROOT/'BOOTSTRAP.json')
    assert len(r['configs'])==len(b['configs'])==14
    checks=[]
    def check(name,ok,detail=None):
        checks.append(dict(name=name,passed=bool(ok),detail=detail));assert ok,(name,detail)
    for path,sha in a['source_hashes'].items():
        check('source hash unchanged: '+Path(path).name,hashlib.sha256(Path(path).read_bytes()).hexdigest()==sha)
    check('native cash reconciles',a['max_native_cash_error']<1e-7,a['max_native_cash_error'])
    z=np.load(ROOT/'prepared.npz');tr=z['trades'];pc=z['close'];pl=z['low']
    check('972 finite audited trades',len(tr)==972 and np.isfinite(tr).all())
    check('adverse paths <= sampled paths',bool(np.all(pl<=pc+.001)))
    check('prepared hash matches freeze',hashlib.sha256((ROOT/'prepared.npz').read_bytes()).hexdigest()==s.read(ROOT/'CONFIGS.json')['source_sha256'])
    for i,(rc,bc) in enumerate(zip(r['configs'],b['configs'])):
        check(f'case {i} metadata paired',rc['config']==bc['config'] and rc['stress']==bc['stress'])
        h=rc['historical'];v=h['snapshot'];logs=np.array(h['trades']);cfg=rc['config']
        check(f'case {i} historical ends flat',v['open_positions']==0)
        check(f'case {i} closed cash ledger',abs(cfg['capital']+logs[:,4].sum()-v['balance'])<1e-6)
        check(f'case {i} no oversize initial risk',bool(np.all(logs[:,5]<=cfg['risk']*cfg['capital']+1e-6)))
        check(f'case {i} lot increments',bool(np.allclose(logs[:,3]/.01,np.round(logs[:,3]/.01))))
        xs=np.load(ROOT/bc['artifact'])['snapshots']
        check(f'case {i} complete 500 x 4 snapshots',xs.shape==(500,4,len(s.FIELDS)) and np.isfinite(xs).all())
        check(f'case {i} monotone cash',bool(np.all(np.diff(xs[:,:,14],axis=1)>=-1e-6)))
        for hi,hz in enumerate(bc['summary']):
            check(f'case {i} horizon {hi} denominator',hz['payout']+hz['breach_before']+hz['unresolved']==500)
        if cfg['firm']=='FTMO':
            funded=xs[:,-1,11]>=0
            check(f'case {i} funded requires both phases',bool(np.all(xs[funded,-1,10]>=0)))
    unit=subprocess.run([sys.executable,'-m','unittest','test_simulate','-v'],cwd=ROOT,capture_output=True,text=True)
    check('13 synthetic accounting/rule tests',unit.returncode==0)
    s.save(ROOT/'CHECKS.json',dict(checks=checks,unit_output=unit.stdout+unit.stderr,passed=len(checks)))

    sections=['# FTMO Swing vs FundedNext Stellar Instant — current-EA simulation',
      'Research completed 28 September 2026. No purchases, production changes, live account actions or Git push. '
      'This is the approved two-account follow-up, not a new simulation of FundingPips, FNL or every product.',
      '## Decision',
      'Stellar Instant reaches a **small first reward request sooner** in this model. FTMO is the better structural fit for '
      'the current multi-EA system and offers larger modeled reward cash, but passage takes much longer. '
      'Neither is purchase-ready on this evidence alone: added costs sharply reduce results, target-broker lots and execution '
      'are not validated, and this year overlaps prior strategy selection. Do not treat the percentages below as calibrated live probabilities.',
      'The existing-guard FTMO case outperforms the tighter guard proposals on this history. This is not proof that more risk '
      'is safer: changed admission caps change which EAs trade. The seven configurations were fixed before this study’s results.',
      '## What was tested',
      f"{a['count']} audited source trades, 13 EAs, News OFF, common window **2025-09-27 through 2026-09-24** (363 calendar days). "
      'Nasdaq uses DI14 + EMA12, 0.60% initial price stop, ATR6 trailing from 1R, no fixed TP. '
      'Source orders and fills are from native Exness MT5 research reports; shared equity is reconstructed from M1 prices, '
      'not a target-broker native portfolio backtest.',
      '500 paired four-week-block samples per configuration per cost case; 7 configurations × 2 cases = **7,000 modeled paths**. '
      'They all reuse the same limited historical evidence. No bootstrap can remove overfitting or invent unseen crash regimes.',
      'Reference costs include published commission assumptions and source negative swaps. Stress worsens gross winners by 10% '
      'and losers by 10%, adds adverse fill movement and higher carrying costs, and applies an extra 10% haircut to other Instant '
      'winning trades for incomplete news-calendar coverage. This is a hypothetical joint sensitivity, not measured broker slippage.',
      '## First payout-request frequency: all starts in the denominator',
      'Every cell is **reference / stress**. Request eligibility is not approval or money received. Each side is 500 scenarios. '
      '30/60/120/180 mean calendar days, not exact calendar months.']
    rows=[]
    for ci in range(7):
        x,y=b['configs'][ci*2:ci*2+2]
        rows.append([NAMES[ci]]+[f"{pct(x['summary'][h]['payout_pct'])} / {pct(y['summary'][h]['payout_pct'])}" for h in range(4)])
    sections.append(table(['Configuration','30 days','60 days','120 days','180 days'],rows))
    sections +=['## FTMO stages and timing',
      'Times below are cumulative calendar days from starting the challenge, conditional on reaching the milestone within 180 days. '
      'Median (10th–90th percentile), with completing count n out of 500. Different milestones have different successful subsets. '
      'Model assumptions add two business days before Verification and five before funded activation; these are not firm promises.']
    rows=[];phase_durations=[]
    for i in range(6):
        c=b['configs'][i];h=c['summary'][-1];tm=h['timing']
        rows.append([NAMES[i//2]+' / '+('stress' if c['stress'] else 'reference')]+[timing(tm[k]) for k in ['phase1_minute','phase2_minute','funded_minute','first_request_minute']])
        xs=np.load(ROOT/c['artifact'])['snapshots'][:,-1,:];d=phase2_duration(xs);phase_durations.append(d)
    sections.append(table(['Case','Phase 1 passed','Phase 2 passed','Funded activation','First request'],rows))
    sections.append(table(['Case','Verification duration after assumed activation, days'],[[NAMES[i//2]+' / '+('stress' if i%2 else 'reference'),timing(d)] for i,d in enumerate(phase_durations)]))
    sections.append('No tested FTMO scenario reached a reward request within 30 days. A successful-path median is not an average waiting time for all buyers: many paths remain unfinished at day 180.')
    sections +=['## Cash rewards, fees and the Instant trap',
      'USD cash is after the modeled 80% FTMO / 70% Instant split, but before purchase fee, EA add-on, VPS, tax, payment charges and FX. '
      'Mean 180-day cash includes zero-reward paths. It excludes account balance gains not withdrawn and the FTMO fee refund.']
    rows=[]
    for i,c in enumerate(b['configs']):
        h=c['summary'][-1]
        rows.append([NAMES[i//2], 'Stress' if c['stress'] else 'Reference',timing(h['timing']['first_request_minute']),money(h['median_first_cash_if_paid']) if h['median_first_cash_if_paid'] is not None else '—',money(h['mean_cash']),h['unresolved']])
    sections.append(table(['Case','Costs','First-request day median (p10–p90); n','Median first cash if paid','Mean total cash by day 180','No request / still active'],rows))
    sections.append('Cost assumptions carried forward from the checked offers: FTMO $10K fee **€89**, refundable with the first qualifying reward; '
      'Instant $5K **$104.99 with INSTANT30**, otherwise $149.99, plus an **unverified paid EA add-on**. Reconfirm checkout; no purchase was made. '
      'The $25 and $50 add-on columns below are hypothetical sensitivity amounts, not advertised fee quotes. FTMO’s EUR fee is not silently converted into USD.')
    rows=[]
    for i in range(6,14):
        c=b['configs'][i];h=c['summary'][-1]
        rows.append([NAMES[i//2], 'Stress' if c['stress'] else 'Reference']+[f"{h[k]}/500 ({h[k]/5:.1f}%)" for k in ['base_fee_recovered','fee_plus25_recovered','fee_plus50_recovered','regular_fee_recovered']])
    sections.append(table(['Instant case','Costs','Cash ≥$104.99','Cash ≥$129.99','Cash ≥$154.99','Cash ≥$149.99'],rows))
    sections.append('A $5K Instant account starts with only $300 of formal loss headroom. The proposed policy withdraws only cash that leaves '
      'at least $150 above its non-decreasing loss floor. Risk then shrinks with available headroom. Once the floor reaches $5,000, '
      'withdrawing the entire profit can breach the account. The all-profit comparison is diagnostic, not recommended. '
      '[Official withdrawal examples](https://help.fundednext.com/en/articles/12439744-what-will-happen-to-the-maximum-loss-limit-after-a-trader-withdraws-from-a-stellar-instant-account).')
    sections +=['## Breach versus stalled progress',
      'No modeled loss-limit breaches occurred in these 7,000 source-history bootstrap runs or the rolling historical runs. '
      '**This does not establish a 0% live blow-up probability.** Admission controls can reject trades, the model cannot recreate '
      'all intraminute prices/gaps, and profitable in-sample source blocks do not represent all future market regimes. '
      'Synthetic tests deliberately create floating-loss and withdrawal breaches and confirm that the engine catches them.']
    rows=[]
    for i,c in enumerate(b['configs']):
        h=c['summary'][-1]
        rows.append([NAMES[i//2], 'Stress' if c['stress'] else 'Reference',h['breach_before'],h['breach_after'],h['no_entry_last30days'],money(h['median_ending_balance_headroom'])])
    sections.append(table(['Case','Costs','Breach before first request','Breach after request','No entry in last 30 days','Median ending balance minus floor'],rows))
    sections.append('Each count is out of 500. No-entry is an inactivity diagnostic, not necessarily permanent failure. Ending balance headroom excludes floating P&L; all modeled breach tests include reconstructed floating equity.')
    sections +=['## Historical continuous replay — no phase resets or withdrawals',
      'These are account-equity research returns, not cash payout returns. Maximum equity drawdown uses the within-minute adverse envelope, '
      'divided by initial capital. It can exceed 10% while still staying above FTMO’s static loss floor after prior gains. '
      'Trades/day uses every Monday–Friday in the common window, including holidays, not only days that traded.']
    weekdays=int(np.busday_count('2025-09-27','2026-09-25'));rows=[]
    for i,c in enumerate(r['configs']):
        v=c['historical']['snapshot'];cap=c['config']['capital'];nt=v['trades']
        rows.append([NAMES[i//2],'Stress' if c['stress'] else 'Reference',f"{(v['balance']/cap-1)*100:+.2f}%",int(nt),f'{nt/weekdays:.2f}',f"{100*v['wins']/nt:.2f}%",f"{v['positive']/v['negative']:.2f}",f"{v['envelope_dd_pct']:.2f}%",f"{int(v['max_win_streak'])}/{int(v['max_loss_streak'])}"])
    sections.append(table(['Case','Costs','Return','Trades','Per weekday','Win rate','PF','Equity DD','Max win/loss streak'],rows))
    sections +=['## What actually traded',
      'All 13 EAs were offered signals, but position sizing, minimum lots, margin and portfolio risk controls reject many. '
      'Lot minimum/step is assumed 0.01 in harmonized source contract units; the target-account values are not confirmed. '
      'In particular, do not interpret the Instant full-basket results as proof that its small account can run the complete gold package.']
    rows=[]
    for k,key in enumerate(a['keys']):
        rows.append([key,a['counts'][key]]+[r['configs'][i]['historical']['accepted'][k] for i in [4,2,8,10]])
    sections.append(table(['EA','Source trades','FTMO existing','FTMO tighter 0.50%','Instant full 0.25%','Instant core4'],rows))
    rows=[]
    for i in [4,2,8,10]:
        rej=np.array(r['configs'][i]['historical']['rejected']).sum(axis=0)
        rows.append([NAMES[i//2]]+rej.tolist())
    sections.append(table(['Case']+s.REJECT,rows))
    sections +=['## Actual rolling historical starts — separate from bootstrap',
      'Monday starts, fully observed windows only. There are 48 / 44 / 35 / 26 starts for 30 / 60 / 120 / 180 days. '
      'They overlap heavily and are not independent trials. This table reports reference / stress first-request counts.']
    rows=[]
    for ci in range(7):
        x,y=r['configs'][ci*2:ci*2+2]
        rows.append([NAMES[ci]]+[f"{x['rolling'][h]['payout']}/{x['rolling'][h]['starts']} / {y['rolling'][h]['payout']}/{y['rolling'][h]['starts']}" for h in range(4)])
    sections.append(table(['Case','30 days','60 days','120 days','180 days'],rows))
    sections +=['## Proposed risk settings and deployment status',
      table(['Setting','FTMO existing-guard reference','FTMO tighter proposal','Instant proposal'],[
       ['Per-entry stop risk cap','$50','$25 or $50','$7.50 or $12.50; also ≤5% available headroom'],
       ['Aggregate planned risk','$225','$150','Total 1.25R + cost reserves ≤20% available headroom'],
       ['Same-symbol risk','$150','$75','≤10% available headroom'],
       ['Internal daily admission budget','$300','$150','$37.50'],
       ['Margin admission cap','80%','30%','30%'],
       ['New entries/day','7','7','7'],
       ['Stop new entries after losing closes/day','3','3','3'],
       ['Withdrawal buffer','Static floor; modeled profit withdrawn','Static floor; modeled profit withdrawn','$150 above trailing floor retained'],
       ['News Pulse','OFF','OFF','OFF']]),
      'Available Instant headroom = min(balance, sampled equity) − current loss floor − $10. Initial trade risks are maxima, not promises '
      'of exact realized loss. Reserve adds 1.25× stop risk plus $5 on FTMO / $2.50 on Instant per position. No minimum-lot upsize. '
      'These are admission limits, not guaranteed daily maximum losses. Existing-guard exposure is more permissive and must not be called safer because its fitted-year result is better.',
      'Keep each strategy’s tested trade exit, including Nasdaq ATR trailing. Do not add an untested global trailing stop just to obtain an earlier payout. '
      'The account trailing-loss floor and an individual trade’s trailing stop are different mechanisms. No new strategy exits were invented here.',
      '## Compatibility and gates before buying',
      '- FTMO Swing supports the overnight/weekend style of this package. Use 2-Step Swing, not a different FTMO product with different rules. '
      '[Swing rules](https://ftmo.com/en/faq/ftmo-swing-account-type/).',
      '- Stellar Instant requires the paid EA permission on MT4/MT5 and compliant distinct strategies; Telegram/WhatsApp integrations are prohibited. '
      '[EA policy](https://help.fundednext.com/en/articles/11641338-can-i-use-ea-in-stellar-instant).',
      '- News Pulse OFF does not remove news exposure: other bots can open or close around releases. Only 29 saved timestamps were checked; '
      '17 source trades are close to those events. The complete firm calendar must be mapped before claiming compliance. '
      '[Instant news treatment](https://help.fundednext.com/en/articles/11641410-is-news-trading-allowed-in-the-stellar-instant-accounts).',
      '- Verify country/residency eligibility, exact checkout price and EA add-on, minimum lots/contract sizes, spread/swap schedules and account agreement. '
      'Do not assume the computer timezone proves residency.',
      '- Replay the unchanged package with actual target-account demo specifications, then forward-test. No purchase or live configuration change is justified by these fitted-history probabilities alone.',
      '## Evidence limits and validation',
      f"{sum(x['bars'] for x in a['rates'].values()):,} M1 bars; {a['paths_minutes']:,} per-position path minutes. "
      f"Max native cash reconciliation error {a['max_native_cash_error']:.2g}. Worst source path {a['minimum_r']:.2f}R, retained rather than clipped at the initial stop. "
      'The Nasdaq example is a weekend gap on an April 2026 trade.',
      f"{len(checks)} automated audit assertions passed, including 13 synthetic rule/accounting tests. All recorded source hashes remain unchanged. "
      'The lower-fidelity sampled-equity variant is saved beside the adverse-envelope rolling results in RESULTS.json. '
      'Source data, scripts, frozen parameters and all rejected configurations are retained locally.',
      'Read AMENDMENTS.md for timing, partial-minute gaps, absent spread values, swap approximation, conservative withdrawal ratchet, '
      'bootstrap boundary distortions and other limitations. Test success proves internal implementation checks, not trading profitability or firm approval.',
      '## Official rule references',
      '- [FTMO 2-Step objectives](https://ftmo.com/en/trading-objectives/): evaluation targets, daily/static loss limits and opening-day requirements.',
      '- [FTMO rewards](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/): request timing and reward share. Actual review and transfer add time after eligibility.',
      '- [Instant loss limits](https://help.fundednext.com/en/articles/11641163-what-are-the-daily-loss-limit-and-the-maximum-loss-limit-for-the-stellar-instant-accounts).',
      '- [Instant reward eligibility](https://help.fundednext.com/en/articles/11641693-what-is-the-eligibility-criteria-for-my-performance-reward-in-the-stellar-instant-account).',
      '- [Instant commissions](https://help.fundednext.com/en/articles/11641300-what-are-the-commission-charges-for-the-stellar-instant-account) and '
      '[leverage](https://help.fundednext.com/en/articles/11641369-what-is-the-leverage-provided-in-the-stellar-instant-accounts).',
      '## Bottom line',
      '**For fastest small reward eligibility: Instant. For this existing EA system and larger reward potential: FTMO Swing. '
      'For a purchase today based on a guaranteed quick return: neither.** The evidence supports target-broker validation, '
      'not a promise of funding next month or a risk-free instant payout.']
    (ROOT/'REPORT.md').write_text('\n\n'.join(sections)+'\n',encoding='utf-8')
    s.save(ROOT/'SUMMARY.json',dict(period=['2025-09-27','2026-09-25 exclusive'],source_trades=a['count'],bootstrap_paths_per_case=500,
      interpretation='historical-model scenario frequencies, not future probabilities',configs=[dict(name=NAMES[i//2],stress=c['stress'],summary=c['summary']) for i,c in enumerate(b['configs'])],checks=len(checks)))
    print(json.dumps(dict(report=str(ROOT/'REPORT.md'),audit_checks=len(checks),historical_weekdays=weekdays),indent=2))
if __name__=='__main__':main()
