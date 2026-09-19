"""Render the saved research screen, preserving missing data and pending outcomes."""
from pathlib import Path
import json, hashlib
import pandas as pd
from research import ROOT, START, END, gold_data, stamp

def n(x): return 'n/a (no losses)' if x is None else f'{x:.2f}'

def main():
    r=json.loads((ROOT/'gold-results.json').read_text())
    lines=['# Two new strategies: standalone FTMO Swing investigation','',
        '**Verdict:** This raw gold adaptation does not support a one-month standalone challenge plan. Japan opening reversal remains untested because usable full history could not be obtained. Do not treat either as approved for a purchased challenge.','',
        '## Evidence and scope','',
        '- Window: 1 September 2021 through 31 August 2026. Initial capital $10,000; fixed $50 nominal all-in stop-risk budget, down-rounded lots; one position per day, no compounding of risk. Five signals exceed the gold minimum-lot risk budget and are skipped.',
        '- Python event replay on cached Exness Zero M1 gold prices, not a native MT5 or FTMO tester run. Floating drawdown uses conservative M1 extrema; it is not tick-exact.',
        '- Both variants use a 2 x completed-H1 ATR(14) stop and timed exit, no TP/trail. These and the rolling 60-day abnormal-return threshold are explicit adaptations, not rules fully specified by the paper.',
        '- Gold baseline spread is max(recorded spread, $0.30), adverse slippage $0.10 each fill; commission 0.0007% of notional per side from FTMO published update. Stress doubles spread and uses $0.25 adverse slippage each fill. No rollover, thus no swap. Current terminal-specific fees/lot constraints remain unverified.',
        '- Gold and Japan Swing leverage 1:15 and current contract sizes are taken from FTMO public specifications. A 50% margin-use cap applies. These public specifications are projected through history to screen a current hypothetical account.',
        '- No production settings, website, BAT, trading account or orders were changed.','',
        '## Gold raw results ($50 budget)','',
        '| Variant / period | Trades | Net USD | Return | Win rate | PF | M1 equity DD | Excluded unknown signals | Size skips |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    names={'gold_tables':'Paper table clocks (primary)','gold_prose':'Paper prose clocks (sensitivity)'}
    for name,x in r['strategies'].items():
        for p in ('6m','1y','3y','5y','2025+'):
            z=x['base']['periods'][p]
            lines.append(f"| {names[name]} / {p} | {z['trades']} | ${z['net_usd']:,.2f} | {z['return_pct']:.2f}% | {n(z['win_pct'])}% | {n(z['pf'])} | {z['equity_dd_pct']:.2f}% | {z['invalid_signals']} | {z['size_skips']} |")
    lines+=['','The 6-month win rates are based on only one or two trades and have no credible standalone predictive value. Alternate-clock results are disclosed because the source contradicts itself; they were not selected by optimization.','',
        '## Cost / stop sensitivity over five years','',
        '| Variant | Execution / stop | Trades | Net USD | Return | Win rate | PF | M1 equity DD |','|---|---|---:|---:|---:|---:|---:|---:|']
    for name,x in r['strategies'].items():
        for mode in ('base','stress','time_exit_only'):
            z=x[mode]['periods']['5y']
            lines.append(f"| {names[name]} | {mode} | {z['trades']} | ${z['net_usd']:,.2f} | {z['return_pct']:.2f}% | {n(z['win_pct'])}% | {n(z['pf'])} | {z['equity_dd_pct']:.2f}% |")
    lines+=['','The no-stop diagnostic uses the same position size but does NOT cap risk at $50. It is not the prop recommendation.','',
        '## Standalone challenge replay','',
        'Both phases: +10% then fresh-account +5%, four separate entry dates in each phase; 5% daily loss including floating equity/fees, 10% static total loss. Prague daily reset; no 2-Step best-day rule. Two business days between phases are an assumption. This models objectives, not actual funding, KYC, contract approval or payout.',
        '', 'All horizons use the same 235 Monday starts with 180-day available follow-up. They overlap and are NOT 235 statistically independent trials. Unknown-data windows are inconclusive, not passes or breaches. A low breach rate is not success: most windows have very few trades.', '',
        '| Variant | Risk budget | Horizon days | Usable / 235 | Both phases passed | Phase 1 passed | Breached | Pending | Inconclusive | 30-day inactivity flags |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for name,x in r['strategies'].items():
        for risk,c in x['base']['challenges'].items():
            for h,z in c.items():
                lines.append(f"| {names[name]} | ${risk} | {h} | {z['usable_starts']} | {z['both_passed']} | {z['phase1_passed']} | {z['breach']} | {z['pending']} | {z['data_inconclusive']} | {z['inactivity_flagged']} |")
    lines+=['','No completed, usable window passed even phase 1 at any tested budget ($25, $50, $75, $100) or horizon (30, 60, 180 days). This is an observed historical result under frozen assumptions, not a statement that the true future probability is mathematically zero.',
        '', '## Japan opening reversal: blocked, not rejected on performance','',
        '- Source: Iwanaga (2026), prior S&P 500 return predicts opposite-direction Nikkei futures opening return. Raw rule: sell after a positive prior US session, buy after a negative session, enter 08:45 Tokyo, exit 09:15. Skip missing US-session signals. No optimization.',
        '- A first-30-minute futures effect is not automatically the same effect in a cash-index CFD. The instrument and execution must be validated before using it on FTMO JP225.cash.',
        '- FTMO public Japan specifications: 10 JPY per index point per lot, profit and margin currencies JPY, Swing leverage 1:15, index commission zero. Terminal min/step size and actual bid/ask costs still require validation.',
        '- Read-only MT5 initialization failed with (-6, Terminal: Authorization failed). No credentials, account balance or trade history were requested or read.',
        '- Public Dukascopy Japan M1 download returned HTTP 429 after partial acquisition; stopped the downloader. Partial files are NOT a three/five-year backtest and no Japan profit, pass probability or breach rate is reported.',
        '- The next required input is an authenticated FTMO terminal usable for market-data calls, including Japan history, or a complete export of Nikkei/Japan index bid/ask data. The terminal will continue to be treated only as a price-data source.',
        '- Most of a 2021-2026 Japan test would overlap the paper\'s 2001-2024 research sample. A successful replay would still need separate 2025+ evidence and forward validation.','',
        '## Verification and reproducibility','',
        '- 12 focused tests check directional bid/ask, commission, slippage, gap stops, timed exits excluding future candle extremes, down-rounding/minimum lot, margin cap, both sequential phases, minimum entry days, administrative delay, floating-equity breaches and missing-data handling.',
        '- Prefix-invariance test checks gold signals still exist when all future prices and the remainder of that day are removed.',
        '- Source hashes, full unrounded per-lot paths, ledgers, monthly results and individual challenge outcomes are retained beside this report.',
        '- The unexplained gold quote absence on 20 June 2025 censors affected challenge starts. The 21 October 2025 path gap affects higher-risk variants; at $50 its minimum permissible lot already exceeds the budget, so no trade is attempted.',
        '', '## Sources','',
        '- [Gold abnormal-return paper](https://doi.org/10.1007/s11408-021-00380-w)',
        '- [Nikkei opening-reversal paper](https://doi.org/10.1016/j.finr.2026.100108)',
        '- [JPX futures hours](https://www.jpx.co.jp/english/derivatives/products/domestic/225futures/01.html)',
        '- [FTMO trading objectives](https://ftmo.com/en/trading-objectives/)',
        '- [FTMO instrument specifications](https://ftmo.com/en/symbols/)',
        '- [FTMO published commission update](https://ftmo.com/en/blog/trading-updates/trading-update-25-sep-2025/)']
    (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    files=list((ROOT/'Data/japan-bi5').glob('*.bi5'))
    audit={'mt5':'read-only initialization failed -6 Authorization failed','japan_complete':False,'japan_status':'stopped on HTTP 429','japan_partial_daily_files':len(files),'japan_files':[{'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
    m=gold_data();m=m[(m.time>=stamp(START))&(m.time<stamp(END))]
    audit['gold']={'rows':len(m),'first':str(m.index[0]),'last':str(m.index[-1]),'rows_by_year':m.groupby(m.index.year).size().to_dict(),'source':'cached Exness Zero bid M1; not FTMO'}
    (ROOT/'audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print('REPORT.md and audit.json saved')

if __name__=='__main__':main()
