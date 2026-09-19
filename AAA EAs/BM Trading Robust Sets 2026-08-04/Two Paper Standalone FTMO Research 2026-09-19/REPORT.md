# Two new strategies: standalone FTMO Swing investigation

**Verdict:** This raw gold adaptation does not support a one-month standalone challenge plan. Japan opening reversal remains untested because usable full history could not be obtained. Do not treat either as approved for a purchased challenge.

## Evidence and scope

- Window: 1 September 2021 through 31 August 2026. Initial capital $10,000; fixed $50 nominal all-in stop-risk budget, down-rounded lots; one position per day, no compounding of risk. Five signals exceed the gold minimum-lot risk budget and are skipped.
- Python event replay on cached Exness Zero M1 gold prices, not a native MT5 or FTMO tester run. Floating drawdown uses conservative M1 extrema; it is not tick-exact.
- Both variants use a 2 x completed-H1 ATR(14) stop and timed exit, no TP/trail. These and the rolling 60-day abnormal-return threshold are explicit adaptations, not rules fully specified by the paper.
- Gold baseline spread is max(recorded spread, $0.30), adverse slippage $0.10 each fill; commission 0.0007% of notional per side from FTMO published update. Stress doubles spread and uses $0.25 adverse slippage each fill. No rollover, thus no swap. Current terminal-specific fees/lot constraints remain unverified.
- Gold and Japan Swing leverage 1:15 and current contract sizes are taken from FTMO public specifications. A 50% margin-use cap applies. These public specifications are projected through history to screen a current hypothetical account.
- No production settings, website, BAT, trading account or orders were changed.

## Gold raw results ($50 budget)

| Variant / period | Trades | Net USD | Return | Win rate | PF | M1 equity DD | Excluded unknown signals | Size skips |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Paper table clocks (primary) / 6m | 2 | $37.42 | 0.37% | 100.00% | n/a (no losses) | 0.46% | 0 | 0 |
| Paper table clocks (primary) / 1y | 5 | $-8.94 | -0.09% | 60.00% | 0.83 | 0.84% | 0 | 5 |
| Paper table clocks (primary) / 3y | 18 | $-0.20 | -0.00% | 66.67% | 1.00 | 1.98% | 1 | 5 |
| Paper table clocks (primary) / 5y | 34 | $13.78 | 0.14% | 58.82% | 1.04 | 1.98% | 1 | 5 |
| Paper table clocks (primary) / 2025+ | 13 | $-107.54 | -1.08% | 53.85% | 0.48 | 1.76% | 1 | 5 |
| Paper prose clocks (sensitivity) / 6m | 1 | $37.93 | 0.38% | 100.00% | n/a (no losses) | 0.40% | 0 | 2 |
| Paper prose clocks (sensitivity) / 1y | 2 | $41.61 | 0.42% | 100.00% | n/a (no losses) | 0.40% | 0 | 10 |
| Paper prose clocks (sensitivity) / 3y | 20 | $55.09 | 0.55% | 55.00% | 1.31 | 1.06% | 1 | 10 |
| Paper prose clocks (sensitivity) / 5y | 32 | $82.24 | 0.82% | 53.12% | 1.30 | 1.06% | 1 | 10 |
| Paper prose clocks (sensitivity) / 2025+ | 10 | $-10.49 | -0.10% | 50.00% | 0.88 | 1.07% | 1 | 10 |

The 6-month win rates are based on only one or two trades and have no credible standalone predictive value. Alternate-clock results are disclosed because the source contradicts itself; they were not selected by optimization.

## Cost / stop sensitivity over five years

| Variant | Execution / stop | Trades | Net USD | Return | Win rate | PF | M1 equity DD |
|---|---|---:|---:|---:|---:|---:|---:|
| Paper table clocks (primary) | base | 34 | $13.78 | 0.14% | 58.82% | 1.04 | 1.98% |
| Paper table clocks (primary) | stress | 34 | $-38.99 | -0.39% | 52.94% | 0.90 | 1.91% |
| Paper table clocks (primary) | time_exit_only | 34 | $111.22 | 1.11% | 61.76% | 1.39 | 1.62% |
| Paper prose clocks (sensitivity) | base | 32 | $82.24 | 0.82% | 53.12% | 1.30 | 1.06% |
| Paper prose clocks (sensitivity) | stress | 32 | $45.95 | 0.46% | 53.12% | 1.16 | 1.16% |
| Paper prose clocks (sensitivity) | time_exit_only | 32 | $-3.75 | -0.04% | 53.12% | 0.99 | 1.94% |

The no-stop diagnostic uses the same position size but does NOT cap risk at $50. It is not the prop recommendation.

## Standalone challenge replay

Both phases: +10% then fresh-account +5%, four separate entry dates in each phase; 5% daily loss including floating equity/fees, 10% static total loss. Prague daily reset; no 2-Step best-day rule. Two business days between phases are an assumption. This models objectives, not actual funding, KYC, contract approval or payout.

All horizons use the same 235 Monday starts with 180-day available follow-up. They overlap and are NOT 235 statistically independent trials. Unknown-data windows are inconclusive, not passes or breaches. A low breach rate is not success: most windows have very few trades.

| Variant | Risk budget | Horizon days | Usable / 235 | Both phases passed | Phase 1 passed | Breached | Pending | Inconclusive | 30-day inactivity flags |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Paper table clocks (primary) | $25 | 30 | 231 | 0 | 0 | 0 | 231 | 4 | 170 |
| Paper table clocks (primary) | $25 | 60 | 227 | 0 | 0 | 0 | 227 | 8 | 227 |
| Paper table clocks (primary) | $25 | 180 | 209 | 0 | 0 | 0 | 209 | 26 | 231 |
| Paper table clocks (primary) | $50 | 30 | 231 | 0 | 0 | 0 | 231 | 4 | 154 |
| Paper table clocks (primary) | $50 | 60 | 227 | 0 | 0 | 0 | 227 | 8 | 220 |
| Paper table clocks (primary) | $50 | 180 | 209 | 0 | 0 | 0 | 209 | 26 | 231 |
| Paper table clocks (primary) | $75 | 30 | 226 | 0 | 0 | 0 | 226 | 9 | 149 |
| Paper table clocks (primary) | $75 | 60 | 218 | 0 | 0 | 0 | 218 | 17 | 214 |
| Paper table clocks (primary) | $75 | 180 | 191 | 0 | 0 | 0 | 191 | 44 | 224 |
| Paper table clocks (primary) | $100 | 30 | 226 | 0 | 0 | 0 | 226 | 9 | 149 |
| Paper table clocks (primary) | $100 | 60 | 218 | 0 | 0 | 0 | 218 | 17 | 214 |
| Paper table clocks (primary) | $100 | 180 | 191 | 0 | 0 | 0 | 191 | 44 | 224 |
| Paper prose clocks (sensitivity) | $25 | 30 | 231 | 0 | 0 | 0 | 231 | 4 | 157 |
| Paper prose clocks (sensitivity) | $25 | 60 | 227 | 0 | 0 | 0 | 227 | 8 | 217 |
| Paper prose clocks (sensitivity) | $25 | 180 | 209 | 0 | 0 | 0 | 209 | 26 | 231 |
| Paper prose clocks (sensitivity) | $50 | 30 | 231 | 0 | 0 | 0 | 231 | 4 | 140 |
| Paper prose clocks (sensitivity) | $50 | 60 | 227 | 0 | 0 | 0 | 227 | 8 | 209 |
| Paper prose clocks (sensitivity) | $50 | 180 | 209 | 0 | 0 | 0 | 209 | 26 | 231 |
| Paper prose clocks (sensitivity) | $75 | 30 | 226 | 0 | 0 | 0 | 226 | 9 | 134 |
| Paper prose clocks (sensitivity) | $75 | 60 | 218 | 0 | 0 | 0 | 218 | 17 | 204 |
| Paper prose clocks (sensitivity) | $75 | 180 | 191 | 0 | 0 | 0 | 191 | 44 | 226 |
| Paper prose clocks (sensitivity) | $100 | 30 | 226 | 0 | 0 | 0 | 226 | 9 | 134 |
| Paper prose clocks (sensitivity) | $100 | 60 | 218 | 0 | 0 | 0 | 218 | 17 | 204 |
| Paper prose clocks (sensitivity) | $100 | 180 | 191 | 0 | 0 | 0 | 191 | 44 | 226 |

No completed, usable window passed even phase 1 at any tested budget ($25, $50, $75, $100) or horizon (30, 60, 180 days). This is an observed historical result under frozen assumptions, not a statement that the true future probability is mathematically zero.

## Japan opening reversal: blocked, not rejected on performance

- Source: Iwanaga (2026), prior S&P 500 return predicts opposite-direction Nikkei futures opening return. Raw rule: sell after a positive prior US session, buy after a negative session, enter 08:45 Tokyo, exit 09:15. Skip missing US-session signals. No optimization.
- A first-30-minute futures effect is not automatically the same effect in a cash-index CFD. The instrument and execution must be validated before using it on FTMO JP225.cash.
- FTMO public Japan specifications: 10 JPY per index point per lot, profit and margin currencies JPY, Swing leverage 1:15, index commission zero. Terminal min/step size and actual bid/ask costs still require validation.
- Read-only MT5 initialization failed with (-6, Terminal: Authorization failed). No credentials, account balance or trade history were requested or read.
- Public Dukascopy Japan M1 download returned HTTP 429 after partial acquisition; stopped the downloader. Partial files are NOT a three/five-year backtest and no Japan profit, pass probability or breach rate is reported.
- The next required input is an authenticated FTMO terminal usable for market-data calls, including Japan history, or a complete export of Nikkei/Japan index bid/ask data. The terminal will continue to be treated only as a price-data source.
- Most of a 2021-2026 Japan test would overlap the paper's 2001-2024 research sample. A successful replay would still need separate 2025+ evidence and forward validation.

## Verification and reproducibility

- 12 focused tests check directional bid/ask, commission, slippage, gap stops, timed exits excluding future candle extremes, down-rounding/minimum lot, margin cap, both sequential phases, minimum entry days, administrative delay, floating-equity breaches and missing-data handling.
- Prefix-invariance test checks gold signals still exist when all future prices and the remainder of that day are removed.
- Source hashes, full unrounded per-lot paths, ledgers, monthly results and individual challenge outcomes are retained beside this report.
- The unexplained gold quote absence on 20 June 2025 censors affected challenge starts. The 21 October 2025 path gap affects higher-risk variants; at $50 its minimum permissible lot already exceeds the budget, so no trade is attempted.

## Sources

- [Gold abnormal-return paper](https://doi.org/10.1007/s11408-021-00380-w)
- [Nikkei opening-reversal paper](https://doi.org/10.1016/j.finr.2026.100108)
- [JPX futures hours](https://www.jpx.co.jp/english/derivatives/products/domestic/225futures/01.html)
- [FTMO trading objectives](https://ftmo.com/en/trading-objectives/)
- [FTMO instrument specifications](https://ftmo.com/en/symbols/)
- [FTMO published commission update](https://ftmo.com/en/blog/trading-updates/trading-update-25-sep-2025/)
