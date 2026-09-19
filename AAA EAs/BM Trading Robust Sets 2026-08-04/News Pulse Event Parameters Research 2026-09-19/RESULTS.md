# News Pulse XAU — event-family parameter research

Research period: 2025-09-19 inclusive to 2026-09-19 exclusive. USD 10,000 starting balance. Native MT5 Model 4, Exness-MT5Trial16 XAUUSD, leverage 1:2000. Not an FTMO simulation.

## Decision

Do not replace the installed preset based on the full-year fitted result. Chronological validation and execution sensitivity must drive the decision, not the maximum hindsight return. Both pending directions remain eligible; no OCO cancellation was introduced. No production EA, BAT, website or live account settings changed.

## Baseline identity

Local installer set: `12A News Pulse XAU Two Sided - HARD 1.5 TOTAL.set`. Lead 30 seconds; current Ask/Bid anchors; $6 price offset; $6 stop; no TP; trail starts 1.5R with $15 distance; close at event +60 seconds. Source defaults differ from this saved set. The comparison is against this verified local installer, not an unverified newer deployment.

Risk is 0.75% equity per pending side, with source lot-round-up/minimum-lot behavior. Both sides can fill. Commission and gaps can make realized risk exceed the nominal 1.5% combined budget. Risk percentage was not optimized.

## Native MT5 results

| Run | Return | Final USD | Net PF | Net win rate | Trades | Max equity DD | Commission | Swap |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Current, full year | +35.92% | $13,591.91 | 4.18 | 57.58% | 33 | 3.62% | $-27.68 | $0.00 |
| Full-year fitted combination | +262.10% | $36,210.11 | 10.97 | 65.79% | 38 | 6.60% | $-133.94 | $0.00 |
| Earlier-period-selected combination, full year | +74.99% | $17,499.27 | 2.86 | 61.54% | 39 | 11.72% | $-121.44 | $0.00 |
| Current, later-period validation | +19.34% | $11,933.73 | 3.84 | 62.50% | 16 | 3.38% | $-12.76 | $0.00 |
| Earlier-selected, later-period validation | +5.70% | $10,569.98 | 1.30 | 46.67% | 15 | 9.61% | $-31.76 | $0.00 |
| Current, native 250ms | +36.00% | $13,600.46 | 4.17 | 54.55% | 33 | 3.34% | $-27.58 | $0.00 |
| Full-year fitted, native 250ms | +331.07% | $43,106.88 | 11.75 | 66.67% | 39 | 6.79% | $-156.55 | $0.00 |

Full-year results contain 71% real ticks; MT5 generated the remainder. Later-period validation (2026-05-19 to 2026-09-19 exclusive) reports 100% real ticks and restarts each alternative with $10,000. It is one chronological split, not an unbiased repeated walk-forward or a live passing probability. The full-year fitted combination uses the validation releases in its selection and is NOT out of sample.

## Parameters by event family

Price distances are XAUUSD price dollars per ounce, NOT cash risk. The prior closed M1 high is adjusted by current spread for buy-stop anchoring; the low anchors the sell stop. These are separate rules per NFP/CPI/FOMC family, not per historical release date.

| Selection | Event | Before release | Anchor | Entry offset | SL | TP | Trailing | Close after release |
|---|---|---:|---|---:|---:|---|---|---:|
| full | NFP | 10s | Previous closed M1 high/low | $2 | $2 | None | Off | 60s |
| full | CPI | 5s | Previous closed M1 high/low | $1 | $2 | None | Start 1R; distance $10 | 300s |
| full | FOMC | 60s | Current quote | $1 | $2 | 5.5R | Start 0.5R; distance $4 | 120s |
| train | NFP | 120s | Current quote | $8 | $2 | 7.5R | Start 1.5R; distance $6 | 300s |
| train | CPI | 30s | Previous closed M1 high/low | $1 | $2 | 8R | Off | 600s |
| train | FOMC | 5s | Active M1 high/low | $2 | $2 | 8R | Start 2R; distance $2 | 120s |

## Event-family contributions in the combined account

These cash contributions use each combined account’s changing equity. They are not independent standalone strategy returns.

| Event | Current trades | Current net USD | Fitted trades | Fitted net USD | Fitted net win rate |
|---|---:|---:|---:|---:|---:|
| NFP | 11 | $1,481.56 | 11 | $13,762.71 | 63.64% |
| CPI | 13 | $1,561.78 | 13 | $8,150.13 | 61.54% |
| FOMC | 9 | $548.57 | 14 | $4,297.27 | 71.43% |

## Monthly realized breakdown

| Month | Current trades | Current net USD | Fitted trades | Fitted net USD |
|---|---:|---:|---:|---:|
| 2025-10 | 2 | $296.09 | 3 | $1,151.17 |
| 2025-11 | 1 | $-28.57 | 1 | $35.41 |
| 2025-12 | 3 | $161.19 | 4 | $638.25 |
| 2026-01 | 3 | $59.57 | 4 | $568.51 |
| 2026-02 | 2 | $1,024.47 | 1 | $951.19 |
| 2026-03 | 3 | $-45.09 | 5 | $1,186.53 |
| 2026-04 | 2 | $53.42 | 3 | $658.44 |
| 2026-05 | 1 | $-114.62 | 4 | $-788.61 |
| 2026-06 | 4 | $528.38 | 3 | $2,381.98 |
| 2026-07 | 3 | $920.87 | 3 | $7,459.32 |
| 2026-08 | 4 | $543.74 | 2 | $4,884.33 |
| 2026-09 | 5 | $192.46 | 5 | $7,083.59 |

## Screening stress — not native tester results

Historical bid/ask spread was used. Moderate stress adds $0.25 spread, $0.25 adverse entry/stop/market-exit fills, and 100ms placement delay. Severe adds $0.50 spread, $0.75 adverse fills, and 250ms placement delay. TP fills remain at target. This is a simplified sensitivity model, not a complete live latency/queue/liquidity simulation.

| Modelled scenario | Current return | Fitted return | Fitted estimated DD |
|---|---:|---:|---:|
| stress | +32.15% | +229.66% | 7.98% |
| severe | +24.64% | +133.75% | 11.90% |

Native 250ms execution delay produced a different trade path and can increase, not merely reduce, backtest profit. This is sensitivity evidence, not proof that slower execution improves the strategy. Do not interpret the 1ms run as realistic guaranteed news execution.

## Coverage and checks

- 30 scheduled releases: 11 NFP, 11 CPI, 8 FOMC. The 2026-04-03 NFP has no executable gold quotes; zero trades are retained rather than fabricated.
- Official BLS/Fed calendar receipt archive extended with FXMacroData records. Connector receipts do not establish point-in-time historical-vintage safety; this limitation is preserved in the saved data.
- Final bounded search: 5,066 configurations per event family; lead 5–120s, three anchors, offset $1–20, SL $2–20, TP disabled or 0.5–8R in 0.5R steps, trailing on/off, close 60–600s. Not an exhaustive global optimum.
- Selection ranks return minus twice estimated equity DD; the top 100 first-pass candidates per family are reranked under moderate cost stress. Training uses only releases before 2026-05-19 (7 NFP, 7 CPI, 5 FOMC). This is a very small sample for many parameters.
- A first-pass 30-second close candidate failed native specified-expiration validation and was excluded. First-pass files were archived. Final selections were rerun natively.
- The fitted closed-M1-anchor setup also had four single-side invalid-price placement rejections when price was already beyond the proposed stop entry. Native results include those rejections; successfully placed events can have only one valid pending side. Retaining the opposite side is not a promise that both orders are accepted.
- A quote-only native export removed three missing callback quotes seen when exporting alongside synchronous trading. The revised export passed full running-candle high/low checks, baseline trade-count/net-win reconciliation, and baseline cash reconciliation within $1.
- Main final results are parsed from native deals; net PF and net win rate include recorded commission and swap. Equity DD is MT5 relative equity DD, not balance-only drawdown.
- Tester fills include the historical bid/ask path and native gap behavior, but cannot certify live news slippage, rejection rates, historical liquidity, or future profitability.

Saved native HTML reports, trade-level JSON, logs, full calendar receipts, parameter candidates and screening results are in this research directory. No active system changes were made.
