# News Pulse XAG — review complete, 5 October 2026

Research-only next-EA step. No production EA/EX5/SET, BAT, website or live chart/account changed; no Git stage/commit/push. Stop for user review before the next EA. No replacement or future-BAT keep was selected.

Six successful native replays, one unchanged v2.21 trading configuration, zero optimisation configurations. Shipped EX5 versus instrumented August copy passed exact four-position parity. Whole cash and all exported native deal rows reconcile; actual-risk conversion is measured with OrderCalcProfit and matches every exit cash amount. Original/helper/SET fingerprints unchanged. Current normal installer risk is 0.75% equity per side, both sides armed, not OCO.

| Window (UTC start inclusive, end exclusive) | Delay | Positions | Net win rate | Net position PF | Return | Native floating equity DD | Daily equity Sharpe | Max W/L |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025-10-05 → 2026-10-05 | 150ms | 39 | 46.15% | 8.368 | +2622.82% | 11.28% | 2.924 | 3/6 |
| 2026-04-05 → 2026-10-05 | 150ms | 22 | 40.91% | 8.611 | +543.57% | 9.32% | 3.277 | 2/6 |
| 2026-07-05 → 2026-10-05 | 150ms | 13 | 46.15% | 8.067 | +213.19% | 8.31% | 4.093 | 2/2 |
| 2026-07-05 → 2026-10-05 | 3000ms | 13 | 46.15% | 7.913 | +196.84% | 8.75% | 4.068 | 2/2 |

These are descriptive, overlapping, separate USD10k starts, not return forecasts or an independent validation pass. The existing event settings were hindsight fitted on 2025-09-19 → 2026-09-19. The year reports 75% real ticks with real ticks beginning 2026-01-01. The shorter windows report 100% real ticks but most accepted recent request quotes have zero spread (14/16 in the baseline quarter; 20/32 in six months). Credible historical spread/stop liquidity remains unproven. Request delay is not extra pending-trigger server latency.

Year actual initial stop exposure reached 30.159× its pre-send risk budget; max realised net loss 12.479×. Those are position measurements, not guaranteed future caps and not identical to account-level drawdown. July14 CPI buy: intended budget $654.808575, actual fill 58.635, original SL58.032, volume6.55, measured initial exposure $19,748.25. January9 NFP sell: budget$107.962875, net loss$1,347.30. Every cash conversion uses the native 5,000-ounce XAG contract size, independently reconciled. Do not reuse Gold's100 multiplier.

Year setup30/31; the unplaced April3 NFP lies in a quote-clock gap April2 evening→April5 evening. Consistent with a missing broker session, not independently proven historical schedule or a placement bug. Missing event retained in prospective setup denominator. No duplicated accepted sides, uncertain sends or close/delete/trailing errors observed. Five accepted market entries in the year; journal market-fallback print count10 is duplicate occurrences, not ten unique filled positions. Original fault-check evidence is separate from performance.

Three-/five-year tests NOT RUN at the prospectively defined input gate. No optimisation, Monte Carlo promotion, FTMO/pass/payout simulation, or credible new winner. Primary future research hypothesis: verified costs/fills → spread-aware stops and budget-aware sizing → OCO/anchor/exit comparisons on separate dates. None implemented. A skip/rejection guard would conflict with force-entry preference and requires an explicit deployment decision.

Results.html contains curves, every year trade, event attribution, basket statistics, risk/spread/coverage audits, exact native reports and source/calendar receipts. The previous review/Trend1.5R future keep log is untouched.
