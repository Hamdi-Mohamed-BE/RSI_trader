# News Pulse - XAG, BTC and EURUSD event-family optimization

Research window: **2025-09-19 inclusive to 2026-09-19 exclusive**. Independent USD 10,000 accounts, Exness-MT5Trial16, leverage 1:2000, M1, native MT5 Model 4. Not FTMO. Both pending directions remain enabled. Risk stays 0.75% equity planned per side; it is not a realized loss cap.

## Decision

No BAT, active EA, attached chart, website or portfolio settings were changed. EURUSD remains inactive. Do not deploy the maximum fitted return as if it were validated.

- **XAG:** WATCH ONLY: earlier-selected combination merits additional testing, but materially higher equity drawdown and very tight stops prevent recommending automatic replacement.
- **BTC:** KEEP CURRENT: earlier-selected combination underperformed current settings in the later period and increased risk; the giant full-year fit is not validation.
- **EURUSD:** WATCH ONLY / INACTIVE: earlier-selected combination merits further testing, but higher drawdown and a small sample do not justify adding it back automatically.

## One-year native MT5 comparison

The fitted combination was selected using the full year, including the later validation dates. Its performance is hindsight/in-sample, not an out-of-sample expectation. Earlier-selected uses only releases before 2026-05-19 for parameter selection; its full-year total still includes training data.

| Asset | Version | Return | Final USD | Trades | Net win rate | Net PF | Max equity DD | Commission | Swap |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| XAG | Current / archived EURUSD | +81.74% | $18,173.93 | 38 | 52.63% | 4.29 | 4.77% | $-464.67 | $0.00 |
| XAG | Full-year fitted | +2,523.64% | $262,364.48 | 33 | 51.52% | 9.59 | 11.45% | $-8,151.07 | $0.00 |
| XAG | Earlier-selected, whole-year replay | +1,059.28% | $115,928.04 | 28 | 60.71% | 8.95 | 10.21% | $-3,784.86 | $0.00 |
| BTC | Current / archived EURUSD | +68.28% | $16,828.22 | 43 | 65.12% | 6.33 | 3.35% | $-250.83 | $0.00 |
| BTC | Full-year fitted | +3,773.32% | $387,331.82 | 49 | 63.27% | 12.13 | 12.22% | $-13,191.19 | $0.00 |
| BTC | Earlier-selected, whole-year replay | +697.21% | $79,721.33 | 47 | 65.96% | 6.64 | 5.03% | $-5,129.32 | $0.00 |
| EURUSD | Current / archived EURUSD | +22.02% | $12,202.11 | 34 | 52.94% | 2.75 | 6.12% | $-115.28 | $0.00 |
| EURUSD | Full-year fitted | +751.20% | $85,119.70 | 45 | 53.33% | 10.71 | 21.11% | $-1,806.48 | $0.00 |
| EURUSD | Earlier-selected, whole-year replay | +443.24% | $54,323.56 | 42 | 57.14% | 5.67 | 13.74% | $-2,122.79 | $0.00 |

## Chronological later-period check

**2026-05-19 inclusive to 2026-09-19 exclusive**, each alternative restarts with $10,000. These runs report **100% real ticks**. Only the earlier-selected combination is compared here; the full-year fit is not eligible for an out-of-sample claim. There are only 11 release dates, so evidence is limited.

| Asset | Version | Return | Final USD | Trades | Net win rate | Net PF | Max equity DD |
|---|---|---:|---:|---:|---:|---:|---:|
| XAG | Current / archived EURUSD | +40.43% | $14,043.41 | 15 | 66.67% | 6.81 | 3.99% |
| XAG | Earlier-selected | +215.21% | $31,520.93 | 12 | 58.33% | 8.99 | 10.27% |
| BTC | Current / archived EURUSD | +25.47% | $12,546.96 | 16 | 75.00% | 9.34 | 2.13% |
| BTC | Earlier-selected | +5.17% | $10,517.29 | 19 | 42.11% | 1.43 | 5.03% |
| EURUSD | Current / archived EURUSD | +20.46% | $12,046.34 | 14 | 64.29% | 5.70 | 2.23% |
| EURUSD | Earlier-selected | +114.75% | $21,474.70 | 16 | 56.25% | 8.49 | 6.51% |

## Exact selected event settings

XAG/BTC dollar distances mean symbol price movement, not account cash risk. EURUSD distances are displayed in pips (0.0001). Candle high/low anchors use a current-spread adjustment for the buy side. No-TP and no-trailing are independent settings. Each family uses one reusable rule, not one setting for each historical release.

| Asset | Selection | Event | Place before | Anchor | Entry offset | SL distance | TP | Trailing | Close after event |
|---|---|---|---:|---|---:|---:|---|---|---:|
| XAG | Full-year fitted | NFP | 15s | Bid/Ask | $0.12 | $0.02 | None | Off | 60s |
| XAG | Full-year fitted | CPI | 10s | Previous closed M1 high/low | $0.02 | $0.02 | None | Off | 60s |
| XAG | Full-year fitted | FOMC | 120s | Previous closed M1 high/low | $0.12 | $0.02 | None | 0.5R trigger / $0.4 distance | 60s |
| XAG | Earlier-selected | NFP | 60s | Bid/Ask | $0.3 | $0.04 | None | 1.5R trigger / $0.4 distance | 120s |
| XAG | Earlier-selected | CPI | 10s | Previous closed M1 high/low | $0.02 | $0.02 | None | Off | 60s |
| XAG | Earlier-selected | FOMC | 120s | Previous closed M1 high/low | $0.12 | $0.02 | None | 0.5R trigger / $0.4 distance | 60s |
| BTC | Full-year fitted | NFP | 90s | Bid/Ask | $75 | $12.5 | None | 1.5R trigger / $50 distance | 600s |
| BTC | Full-year fitted | CPI | 5s | Active M1 high/low | $6.25 | $12.5 | None | 0.5R trigger / $187.5 distance | 180s |
| BTC | Full-year fitted | FOMC | 45s | Bid/Ask | $12.5 | $12.5 | None | 1.5R trigger / $100 distance | 600s |
| BTC | Earlier-selected | NFP | 15s | Bid/Ask | $25 | $37.5 | 7.5R | 2R trigger / $125 distance | 600s |
| BTC | Earlier-selected | CPI | 45s | Previous closed M1 high/low | $37.5 | $12.5 | None | 1.5R trigger / $25 distance | 60s |
| BTC | Earlier-selected | FOMC | 90s | Previous closed M1 high/low | $6.25 | $12.5 | None | 1R trigger / $37.5 distance | 300s |
| EURUSD | Full-year fitted | NFP | 90s | Previous closed M1 high/low | 2 pips | 1 pips | None | Off | 300s |
| EURUSD | Full-year fitted | CPI | 60s | Bid/Ask | 1 pips | 2 pips | None | 3R trigger / 4 pips distance | 60s |
| EURUSD | Full-year fitted | FOMC | 10s | Previous closed M1 high/low | 1 pips | 1 pips | None | Off | 60s |
| EURUSD | Earlier-selected | NFP | 90s | Active M1 high/low | 2 pips | 1 pips | None | 1.5R trigger / 8 pips distance | 600s |
| EURUSD | Earlier-selected | CPI | 30s | Active M1 high/low | 6 pips | 1 pips | None | 1R trigger / 6 pips distance | 60s |
| EURUSD | Earlier-selected | FOMC | 120s | Active M1 high/low | 2 pips | 1 pips | 7R | Off | 180s |

## Current baseline settings

| Asset | Place before | Entry offset | SL | TP | Trail trigger | Trail distance | Close after |
|---|---:|---:|---:|---|---:|---:|---:|
| XAG | 30s | $0.08 | $0.08 | None | 1.5R | $0.2 | 60s |
| BTC | 30s | $75 | $75 | None | 1.5R | $112.5 | 60s |
| EURUSD | 30s | 6 pips | 6 pips | None | 1.5R | 15 pips | 60s |

## Native execution-delay sensitivity

Fixed 250ms tester execution delay changes placement and subsequent paths; it may increase or decrease returns. This is not a guaranteed live-news latency/slippage model.

| Asset | Version, 250ms | Return | Trades | Net win rate | PF | Max equity DD |
|---|---|---:|---:|---:|---:|---:|
| XAG | Current | +86.00% | 38 | 52.63% | 4.46 | 5.10% |
| XAG | Full-year fitted | +2,655.34% | 32 | 53.12% | 9.91 | 10.81% |
| BTC | Current | +65.09% | 43 | 65.12% | 6.01 | 3.36% |
| BTC | Full-year fitted | +2,903.18% | 45 | 64.44% | 11.48 | 10.21% |
| EURUSD | Current | +22.29% | 34 | 52.94% | 2.74 | 5.51% |
| EURUSD | Full-year fitted | +729.79% | 45 | 53.33% | 10.51 | 21.06% |

## Screening cost stress - estimates, not native headline results

Historical bid/ask spread is already in the paths. Extra spread and adverse entry/SL/forced-close slippage are added below; TP fills remain at the target. Screening does not fully model margin, order rejection or liquidity. Consequently it can materially diverge from native results, especially when small stops imply large BTC positions. Approximate screening DD is not MT5 equity DD.

| Asset | Scenario | Extra spread | Adverse slippage | Placement delay | Current return | Fitted return | Earlier-selected return |
|---|---|---:|---:|---:|---:|---:|---:|
| XAG | stress | $0.005 | $0.005 | 100ms | +51.52% | +2,023.50% | +836.63% |
| XAG | severe | $0.01 | $0.015 | 250ms | +41.72% | +1,332.22% | +607.69% |
| BTC | stress | $3.125 | $3.125 | 100ms | +57.80% | +2,396.66% | +550.80% |
| BTC | severe | $6.25 | $9.375 | 250ms | +47.44% | +962.61% | +313.22% |
| EURUSD | stress | 0.25 pips | 0.25 pips | 100ms | +18.24% | +618.29% | +348.50% |
| EURUSD | severe | 0.5 pips | 0.75 pips | 250ms | +12.55% | +437.87% | +180.36% |

## Later-period cost stress and local parameter stability

These are supplementary Python sensitivity estimates, not additional native MT5 runs. They did not change the previously frozen selections. The native later-period comparison above remains the execution reference.

| Asset | Current moderate | Earlier-selected moderate | Current severe | Earlier-selected severe |
|---|---:|---:|---:|---:|
| XAG | +36.18% | +184.24% | +33.50% | +162.98% |
| BTC | +21.31% | -2.46% | +17.92% | -12.96% |
| EURUSD | +18.99% | +97.41% | +16.59% | +63.50% |

BTC earlier-selected turns negative with the additional cost assumptions while current BTC remains positive. This reinforces keeping current BTC.

Local neighbor diagnostics vary one selected timing/distance by -20% or +20%, rounding to broker precision and clipping to the tested timing limits. The saved results are diagnostics, not a new optimization or probability estimate. Earlier-selected EURUSD FOMC has a negative-return neighbor; the strongest headline alone is not a stable-parameter guarantee.

## Realized risk and coverage audit

Per-trade and per-event loss percentages below use the event-start closed balance, not exact floating equity at each entry. They demonstrate why the planned 0.75% per side / 1.50% per event does not cap realized loss. Dollar profits also compound; event-family contributions are not independent portfolio returns.

| Asset | Version | Real ticks | Expected / attempted / placed releases | Worst single net loss / event-start balance | Worst net losing event |
|---|---|---|---|---:|---:|
| XAG | Baseline | 71% real ticks | 30 / 29 / 29 | 2.38% | 4.19% |
| XAG | Fitted | 71% real ticks | 30 / 29 / 29 | 9.37% | 8.00% |
| XAG | Train | 71% real ticks | 30 / 29 / 29 | 3.81% | 4.31% |
| BTC | Baseline | 71% real ticks | 30 / 30 / 30 | 0.85% | 1.67% |
| BTC | Fitted | 71% real ticks | 30 / 30 / 30 | 2.62% | 2.63% |
| BTC | Train | 71% real ticks | 30 / 30 / 30 | 1.82% | 2.36% |
| EURUSD | Baseline | 71% real ticks | 30 / 30 / 30 | 1.60% | 1.67% |
| EURUSD | Fitted | 71% real ticks | 30 / 30 / 30 | 8.37% | 9.53% |
| EURUSD | Train | 71% real ticks | 30 / 30 / 30 | 6.79% | 6.79% |

## Event-family contributions: native combined account

| Asset | Event | Current trades | Current net USD | Fitted trades | Fitted net USD | Fitted net win rate |
|---|---|---:|---:|---:|---:|---:|
| XAG | NFP | 14 | $3,717.78 | 13 | $129,681.38 | 46.15% |
| XAG | CPI | 15 | $3,446.91 | 13 | $90,222.50 | 46.15% |
| XAG | FOMC | 9 | $1,009.24 | 7 | $32,460.60 | 71.43% |
| BTC | NFP | 18 | $1,100.92 | 19 | $99,581.21 | 63.16% |
| BTC | CPI | 15 | $4,175.63 | 15 | $200,743.87 | 66.67% |
| BTC | FOMC | 10 | $1,551.67 | 15 | $77,006.74 | 60.00% |
| EURUSD | NFP | 12 | $894.37 | 16 | $44,740.86 | 50.00% |
| EURUSD | CPI | 11 | $768.46 | 18 | $13,734.14 | 55.56% |
| EURUSD | FOMC | 11 | $539.28 | 11 | $16,644.70 | 54.55% |

## XAG monthly realized cashflow

| Month | Current trades | Current net USD | Fitted trades | Fitted net USD | Earlier-selected trades | Earlier-selected net USD |
|---|---:|---:|---:|---:|---:|---:|
| 2025-10 | 1 | $350.07 | 1 | $1,355.62 | 1 | $1,355.62 |
| 2025-11 | 2 | $-131.00 | 1 | $-161.25 | 0 | $0.00 |
| 2025-12 | 3 | $803.27 | 3 | $3,312.97 | 3 | $2,863.40 |
| 2026-01 | 5 | $-252.12 | 4 | $1,798.93 | 3 | $3,620.85 |
| 2026-02 | 2 | $2,237.17 | 3 | $26,598.97 | 3 | $12,366.82 |
| 2026-03 | 4 | $207.59 | 3 | $184.30 | 3 | $6,523.89 |
| 2026-04 | 2 | $-60.01 | 1 | $1,854.90 | 1 | $1,580.10 |
| 2026-05 | 4 | $-205.02 | 4 | $-2,825.50 | 2 | $-1,368.00 |
| 2026-06 | 3 | $668.11 | 2 | $13,280.92 | 2 | $13,943.92 |
| 2026-07 | 3 | $2,428.80 | 4 | $76,544.96 | 4 | $23,874.09 |
| 2026-08 | 4 | $1,561.54 | 3 | $16,210.30 | 2 | $2,188.62 |
| 2026-09 | 5 | $565.53 | 4 | $114,209.36 | 4 | $38,978.73 |

## BTC monthly realized cashflow

| Month | Current trades | Current net USD | Fitted trades | Fitted net USD | Earlier-selected trades | Earlier-selected net USD |
|---|---:|---:|---:|---:|---:|---:|
| 2025-10 | 4 | $905.59 | 4 | $6,991.64 | 3 | $9,067.54 |
| 2025-11 | 2 | $-182.17 | 1 | $2,041.58 | 2 | $1,254.19 |
| 2025-12 | 4 | $1,362.14 | 5 | $32,535.36 | 4 | $19,842.87 |
| 2026-01 | 4 | $298.60 | 5 | $13,009.81 | 4 | $5,467.38 |
| 2026-02 | 2 | $438.74 | 2 | $4,039.26 | 2 | $3,019.43 |
| 2026-03 | 3 | $392.92 | 6 | $11,464.70 | 4 | $14,485.90 |
| 2026-04 | 4 | $188.71 | 5 | $17,010.68 | 5 | $12,753.94 |
| 2026-05 | 4 | $5.49 | 4 | $2,097.42 | 4 | $-81.25 |
| 2026-06 | 4 | $1,077.33 | 5 | $25,763.42 | 5 | $-554.36 |
| 2026-07 | 3 | $1,228.31 | 3 | $80,678.73 | 5 | $3,243.81 |
| 2026-08 | 4 | $-163.49 | 4 | $16,154.48 | 4 | $438.49 |
| 2026-09 | 5 | $1,276.05 | 5 | $165,544.74 | 5 | $783.39 |

## EURUSD monthly realized cashflow

| Month | Current trades | Current net USD | Fitted trades | Fitted net USD | Earlier-selected trades | Earlier-selected net USD |
|---|---:|---:|---:|---:|---:|---:|
| 2025-10 | 2 | $265.33 | 3 | $1,662.77 | 3 | $2,594.07 |
| 2025-11 | 2 | $5.15 | 2 | $629.99 | 2 | $973.34 |
| 2025-12 | 4 | $237.12 | 6 | $689.60 | 5 | $2,917.30 |
| 2026-01 | 3 | $2.47 | 4 | $-951.82 | 5 | $1,920.53 |
| 2026-02 | 2 | $76.56 | 3 | $4,550.92 | 2 | $5,609.47 |
| 2026-03 | 3 | $-100.39 | 5 | $2,749.98 | 3 | $4,085.67 |
| 2026-04 | 3 | $-238.49 | 3 | $581.63 | 4 | $-1,520.87 |
| 2026-05 | 1 | $-120.62 | 3 | $-942.24 | 2 | $-1,276.16 |
| 2026-06 | 3 | $635.52 | 3 | $10,480.94 | 3 | $4,926.21 |
| 2026-07 | 4 | $850.69 | 5 | $21,773.51 | 4 | $7,390.82 |
| 2026-08 | 3 | $207.26 | 4 | $17,212.78 | 4 | $6,873.60 |
| 2026-09 | 4 | $381.51 | 4 | $16,681.64 | 5 | $9,829.58 |

## Limitations and next decision

- Full-year results report 71% real ticks; the remaining ticks were generated by MT5. Do not describe them as a fully real-tick year.
- The huge fitted returns are not forecasts. The search favors very tight stops and has only 7/7/5 earlier-period NFP/CPI/FOMC releases for selection, respectively.
- Baseline replay matches native trade counts and net wins, with final balance differences below $0.10. This does not prove candidate execution or equity-drawdown fidelity.
- The equity path, contract, fees, margin checks and accepted orders in native reports take precedence over Python screening.
- Calendar source/vintage caveats from the XAU study remain. No post-release actual value is used in the trading rule. Fee calibration uses the asset baseline reports and is an empirical cost assumption, not a reconstructed point-in-time commission tariff.
- The chronological split enforces earlier-only parameter selection in code, but these dates have already been researched elsewhere. It is not a pristine prospective blind experiment.
- Nominal 0.75% stop sizing did not cap realized single-trade loss: the fitted XAG and EURUSD tests include losses above 8% of event-start balance. Gaps and original SL geometry are material risks; do not use these as prop-safe settings.
- Keeping both sides means both are eligible, not that a broker must accept or fill both. Rejected orders and unavailable quotes stay in the audit.
- No independent cross-broker validation, live liquidity proof, long-window reoptimization or prop-firm pass simulation was performed.
- These are separate per-asset accounts, not a combined portfolio on shared capital.
- Prefer further forward validation and a separate approved risk study before promoting XAG/EURUSD. Keep current BTC based on the later-period comparison.

## Artifacts

Each native run retains MQ5/EX5, compile log, exact SET, tester configuration, report/images, journal, parsed stats and individual trades. Asset directories retain raw quotes, causal data-quality checks, cost calibration, full candidate arrays, top-100 rankings and selected settings. `SUMMARY.json` contains all native metrics and monthly/event detail.

Production EAs/BATs and the website have intentionally not been updated by this research.
