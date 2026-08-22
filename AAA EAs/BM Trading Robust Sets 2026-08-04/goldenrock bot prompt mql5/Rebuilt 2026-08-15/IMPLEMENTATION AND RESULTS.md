# GoldenRock EA rebuild — implementation and baseline results

Date: 2026-08-15

## Scope found on disk

The source folder contains nine real prompt files: 01–04 and 06–10. Prompt 05 and prompts 11–18 referenced by the old index/QA document are not present anywhere in the repository, so no strategy rules were invented for those missing IDs.

The old `.mq5` files were scaffolds: they depended on a missing shared include, several had duplicate inputs, and the strategy conditions were placeholders. The rebuilt library contains nine strategy wrappers plus one audited shared execution/risk engine. Every wrapper compiled with 0 errors and 0 warnings in MetaEditor build 6090.

## Deterministic interpretation of each prompt

| ID | Strategy | Exact automated interpretation | Chart |
|---|---|---|---|
| 01 | Trend Following Starter | H1 EMA 20/50 direction and slope plus ADX regime; M15 two-bar pullback into EMA; completed directional confirmation candle; stop beyond five-bar pullback swing. | M15 |
| 02 | Breakout Confirmation | Completed M15 close beyond the previous 20-bar range by 0.10 ATR; state machine waits up to six bars for a directional retest/acceptance; stop beyond the three-bar retest structure. | M15 |
| 03 | Liquidity Sweep Reversal | Sweep of the previous 20-bar extreme by 0.05 ATR, close back inside, rejection wick at least 35% of candle range, then completed opposite displacement/structure close. | M15 |
| 04 | MTF Institutional | H4 EMA/ADX bias; H1 20-bar premium/discount range; M15 local liquidity sweep plus displacement/reclaim in the HTF direction; H1 range extreme is the structural target. | M15 |
| 06 | SMC BOS OB | H1 close breaks the prior 20-bar structure; last opposing H1 candle defines the order block; M15 must retest and close away from that block before entry. | M15 |
| 07 | ICT Killzone | UTC Asia range 00:00–06:00 defines liquidity; London/NY window must sweep/reclaim it; completed displacement plus a three-candle FVG confirms entry; opposite Asia extreme is the structural target. | M15 |
| 08 | Candle Range Theory | Previous completed H1 candle is the reference and must span at least one ATR; next H1 candle manipulates beyond one extreme, reclaims it, closes directionally, and targets the opposite extreme. | H1 |
| 09 | SNR + ICT | Recent confirmed H1 swing defines support/resistance; M15 sweeps/reclaims it; displacement plus three-candle FVG confirms; opposing H1 level is the target. | M15 |
| 10 | SMC + Liquidity Sweep | M15 external sweep/reclaim, then displacement/BOS, then return to the preceding order-block zone; target is the opposing H1 20-bar liquidity extreme. | M15 |

All signals use completed candles. The engine uses broker-aware `OrderCalcProfit` sizing, price/tick/lot normalization, hard stop validation, one position per EA/symbol, no duplicate same-bar processing, setup expiry, spread protection, maximum two entries per UTC day, breakeven at 1R, ATR trailing after 1.5R, and a time exit after 96 entry bars.

## Test protocol

- Broker/data: Exness-MT5Trial16, XAUUSD
- Period: 2021-08-15 through 2026-08-14 (five years)
- Starting deposit: USD 10,000
- Leverage: 1:2000
- Risk sizing: 1% of current equity at the original stop
- Modelling: MT5 Every Tick generated from broker M1 history (Model 0)
- History quality: 98% on all nine reports
- Costs: broker commission, spread and swap were retained; no cost was added back
- Optimization: none; these are frozen prompt-to-code baselines, avoiding in-sample parameter mining

The Exness trial server available here does not expose a usable historical real-tick archive. Model 4 produces no-history/zero-bar tests, so Model 0 is the highest valid common protocol available from this terminal. These results are research estimates, not live-performance promises.

## Results

| Verdict | EA | Final | Net | Return | Max equity DD | PF | Win rate | W/L | Trades | Commission + swap |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Best baseline; forward-test only | GR 06 SMC BOS OB | $11,553.14 | +$1,553.14 | +15.53% | 12.37% | 1.10 | 38.59% | 115 / 183 | 298 | -$658.56 |
| Positive but fragile/outlier-driven | GR 09 SNR ICT | $10,707.21 | +$707.21 | +7.07% | 39.92% | 1.02 | 34.32% | 139 / 266 | 405 | -$1,368.49 |
| Breakeven, rejected | GR 02 Breakout Confirmation | $10,068.55 | +$68.55 | +0.69% | 33.91% | 1.00 | 34.69% | 427 / 804 | 1,231 | -$1,881.36 |
| Rejected | GR 04 MTF Institutional | $9,471.68 | -$528.32 | -5.28% | 16.40% | 0.84 | 32.76% | 19 / 39 | 58 | -$109.26 |
| Rejected | GR 01 Trend Following Starter | $6,775.77 | -$3,224.23 | -32.24% | 45.88% | 0.95 | 33.75% | 488 / 958 | 1,446 | -$2,188.80 |
| Rejected | GR 10 SMC Liquidity Sweep | $5,622.49 | -$4,377.51 | -43.78% | 77.48% | 0.90 | 32.31% | 243 / 509 | 752 | -$4,557.15 |
| Rejected | GR 07 ICT Killzone | $4,981.61 | -$5,018.39 | -50.18% | 52.79% | 0.73 | 32.40% | 150 / 313 | 463 | -$752.36 |
| Rejected | GR 08 Candle Range Theory | $3,338.74 | -$6,661.26 | -66.61% | 68.52% | 0.80 | 31.88% | 352 / 752 | 1,104 | -$1,498.46 |
| Rejected | GR 03 Liquidity Sweep Reversal | $646.49 | -$9,353.51 | -93.54% | 93.67% | 0.57 | 26.93% | 304 / 825 | 1,129 | -$2,078.81 |

GR 09's largest winner was $6,469.09, far larger than its normal trade outcome. Removing or degrading that one fill would erase the total five-year profit, so PF 1.02 is not evidence of a robust edge. GR 06 is the only baseline worth a separate walk-forward/forward-test round, and even it has only PF 1.10 and should not be installed live yet.

## Deliverables

- `Source`: all `.mq5`, shared `.mqh`, and compiled `.ex5` files
- `Presets`: the exact 1% XAUUSD baseline used by the reports
- `Packages`: one self-contained folder per EA with original prompt, source, shared engine, compiled EA, set, compile log, MT5 report and equity image
- `Reports/MT5 Exness XAUUSD 2021-08-15 to 2026-08-14`: native MT5 HTML reports, equity PNGs, CSV/JSON summaries and manifest
- `Run-GoldenRock-Backtests.ps1`: reproducible isolated MT5 runner
- `Analyze-GoldenRock.py`: reproducible report parser, including commission and swap totals

## Important limitations

- The prompts are high-level discretionary descriptions. The table above records the objective choices used to turn ambiguous terms such as BOS, order block, sweep, FVG and premium/discount into deterministic code.
- The optional MT5 economic-calendar/news filter and partial exits were not enabled in this frozen comparison because the available historical tester feed does not provide a complete reproducible five-year economic-calendar series. The engine instead uses hard sessions, spread filtering, initial stops, breakeven, trailing and time exits.
- This batch is a baseline comparison, not an optimization. Any future optimization must use a separated development window and untouched validation window; selecting the best full-period parameter set would overfit these results.
- No EA from this folder was added to the active installer/BAT portfolio.
