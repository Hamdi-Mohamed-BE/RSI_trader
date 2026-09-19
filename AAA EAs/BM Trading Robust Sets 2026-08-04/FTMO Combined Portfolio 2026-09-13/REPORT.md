# FTMO Swing: 10-EA shared-account simulation

Research only; no live EA, BAT, MT5 account, or website data changed.

## Scope and interpretation

- $100,000 USD; 5 September 2023 through 31 August 2026 (36 calendar rows; September 2023 is partial).
- One shared balance, simultaneous positions, gross reserved margin, lot-step round-up and common risk controls. BTC News excluded.
- Provisional safer proposal: 0.35% normal risk AND 0.35% news risk. This requires changing the locked news setting only if approved later. Current-news 0.75% is shown as a separate control.
- Normal entries: stop at -$1,000 daily closed P/L; $3,000 total planned open-risk gate; 4%/7% drawdown and 3/5 loss-streak tapers. News bypasses those gates/tapers but not broker margin availability.
- Modelled Swing leverage: FX 1:30, indices 1:15, metals 1:9, from FTMO published asset-class guidance. This is not a verified current contract specification for the connected account. 20% equity margin reserve. No cross-position hedge margin credit.
- FTMO 2-Step: 10% then 5% targets; four entry days each; $5,000 daily loss from midnight CE(S)T balance; static $90,000 floor. No 1-Step consistency/trailing-loss rules applied.
- Payout is a possible gross USD trader claim at 80%, not guaranteed income or cash received. Month-end claim, deferred until flat and at least 14 days after first funded trade/previous claim. Leave $2,000 above initial capital; losses must be recovered first. Evaluation profits are never paid out.
- Each phase starts at $100,000; 2 business days assumed between phases. Withdrawal profit, including firm share, leaves the account. Withdrawals/reset adjustments are not trading losses.

## Evidence limits — important

- This replays existing cached native MT5 deals, not a new all-EA FTMO Strategy Tester run. Feed differences, signal changes and actual FTMO execution are not reproduced.
- CRITICAL: both News Pulse source backtests report only 13% real ticks. Do not treat their news fills, projected payouts or resulting challenge pass frequencies as verified FTMO evidence.
- No continuous bid/ask equity, original stop history or complete pending-order ledger. A no-breach closed-deal result cannot certify FTMO compliance. Stops and original risk are reconstructed estimates, not guaranteed loss bounds.
- Stop-envelope scenario subtracts all open planned stop losses simultaneously, with stress multipliers. It can overstate risk after trailing stops, and can understate gap/unknown-stop risk. A warning is a hypothetical vulnerability, not evidence the real account breached.
- Source recorded commission/swap are retained; zero recorded swap is not proof the target account is swap-free. Source spreads/fill effects are embedded, not separately measured. No claim of exact historical FTMO costs.
- Stress assumptions: news gross winners x0.65, losers x1.25, extra 0.15R per trade; other winners x0.90, losers x1.10, extra 0.02R. Commission floor $7/lot round-trip on metals/FX; double negative swaps and remove credits. These are sensitivity assumptions, NOT an FTMO fee quote or calibrated slippage model.
- Source timestamps treated as UTC (cached Exness schedules), converted to Prague for resets/months. Same-second round trips close one microsecond after entry to preserve event ordering. Commission split equally between entry and exit; swaps booked at exit.
- Sizing scales from each source trade reconstructed entry balance, not from fixed $10k, avoiding double compounding. 0.01 lot step rounded UP; actual planned risk can exceed the nominal percentage.
- All ten EAs were selected with knowledge of historical results. This is retrospective, not independent out-of-sample proof. The news sample/MT5 modelling quality vary; audit lists source file hashes and quality labels.
- No automatic account restart after failure. Open positions at a model halt are not liquidated at invented prices; ending balance then excludes their unresolved floating P/L.

## Included EAs

| EA | Mode | Role | Source 5Y trades | Source PF | Source win rate |
|---|---|---|---:|---:|---:|
| News Pulse XAU | standard | Retained | 133 | 2.77 | 56.39% |
| News Pulse XAG | standard | Retained | 152 | 3.43 | 53.95% |
| ORB Volume Profile Confirmed | standard | Retained | 120 | 1.69 | 43.33% |
| XAU Trend Progression | standard | Retained | 138 | 2.27 | 58.7% |
| USDJPY London Open Momentum | standard | Retained | 693 | 1.46 | 53.97% |
| US100 ORB New York M30 | standard | Retained | 96 | 1.78 | 48.96% |
| US100 H1 ORB 13UTC | standard | Retained | 289 | 1.57 | 48.79% |
| EMA3 Safe | safe | Added | 102 | 1.86 | 60.78% |
| XAU Squeeze Momentum Standard | standard | Added | 128 | 1.83 | 45.31% |
| XAU RSI VWAP | standard | Added | 260 | 1.37 | 73.46% |

## Three-year system scenarios

| Scenario | Trades closed | Net trading P/L | Possible trader payouts | Closed PF | Closed DD | Model status |
|---|---:|---:|---:|---:|---:|---|
| funded-source | 1224 | $183,373 | $145,098 | 2.21 | 4.78% | No closed or stop-envelope breach |
| funded-stressed | 1218 | $70,401 | $54,721 | 1.41 | 7.33% | No closed breach; stop warning |
| funded-stop-envelope | 203 | $4,708 | $3,821 | 1.15 | 4.02% | Halted: daily stop envelope |
| funded-lower-news | 1275 | $69,461 | $53,969 | 1.43 | 6.14% | No closed or stop-envelope breach |
| challenge-source | 1219 | $183,336 | $131,896 | 2.21 | 4.78% | No closed or stop-envelope breach |
| challenge-stressed | 1216 | $70,184 | $40,855 | 1.41 | 7.33% | No closed breach; stop warning |
| challenge-stop-envelope | 203 | $4,651 | $0 | 1.14 | 4.02% | Halted: daily stop envelope |
| challenge-lower-news | 1271 | $70,305 | $38,811 | 1.44 | 6.14% | No closed or stop-envelope breach |

## 1,000 paired resamples per scenario

Joint four-week blocks sampled from the common 2021-09-05 to 2026-09-01 source window. Both evaluation phases follow the SAME continuing sampled timeline. Horizon = 730 calendar days TOTAL across phases, not per phase. FTMO itself has no time limit. Seed 20260913. Whole trade durations preserved across block joins; joins may create artificial overlaps. No within-EA independent reshuffle.

Pass rates are conditional model frequencies, not verified real-world probabilities. Wilson intervals reflect sampling error only. Funded survival is assessed on the historical path, not by these challenge-only trials.

| Scenario | Passed | Breached | Unfinished | Median days to pass, successes only | 95% sampling interval |
|---|---:|---:|---:|---:|---|
| source | 1000 | 0 | 0 | 143.0 | 99.6–100.0% |
| stressed | 553 | 237 | 210 | 319 | 52.2–58.4% |
| stop_envelope | 434 | 476 | 90 | 280.0 | 40.4–46.5% |
| lower_news_source | 1000 | 0 | 0 | 158.0 | 99.6–100.0% |
| lower_news_stressed | 700 | 52 | 248 | 330.5 | 67.1–72.8% |
| lower_news_stop_envelope | 696 | 70 | 234 | 329.5 | 66.7–72.4% |

## Proposed 0.35% news: monthly system breakdown

Main columns assume funded from the first day. Challenge payout column instead starts in evaluation; its own trades/phase accounting are in the separate scenario CSV/interactive selector. A payout can appear in a negative month after a deferred earlier claim; positive months can pay zero while recovering losses or waiting to be flat.

| Month | Closed trades | Net USD | Return on initial $100k | Commission | Swap | Trader claim USD | End balance | Worst closed day loss | Stop-envelope day loss | Breach | Challenge-start claim |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
| 2023-09 | 25 | $578 | +0.58% | -$238 | $0 | $0 | $100,578 | $1,097 | $1,448 | None modelled | $0 |
| 2023-10 | 31 | -$803 | -0.80% | -$253 | -$213 | $0 | $99,775 | $495 | $1,306 | None modelled | $0 |
| 2023-11 | 35 | $141 | +0.14% | -$267 | -$70 | $0 | $99,916 | $794 | $1,953 | None modelled | $0 |
| 2023-12 | 39 | $2,645 | +2.65% | -$302 | -$47 | $449 | $102,000 | $927 | $1,846 | None modelled | $0 |
| 2024-01 | 34 | $4,273 | +4.27% | -$276 | $0 | $3,419 | $102,000 | $786 | $2,081 | None modelled | $0 |
| 2024-02 | 30 | $1,441 | +1.44% | -$260 | -$25 | $1,153 | $102,000 | $1,260 | $1,875 | None modelled | $0 |
| 2024-03 | 36 | -$1,104 | -1.10% | -$304 | -$61 | $0 | $100,896 | $1,198 | $3,079 | None modelled | $0 |
| 2024-04 | 35 | $7,262 | +7.26% | -$246 | -$45 | $4,926 | $102,000 | $439 | $1,990 | None modelled | $0 |
| 2024-05 | 34 | $4,262 | +4.26% | -$302 | -$252 | $3,410 | $102,000 | $807 | $1,840 | None modelled | $0 |
| 2024-06 | 30 | $4,981 | +4.98% | -$290 | -$20 | $3,985 | $102,000 | $496 | $1,509 | None modelled | $2,283 |
| 2024-07 | 29 | $7,628 | +7.63% | -$245 | $0 | $6,102 | $102,000 | $444 | $1,902 | None modelled | $6,102 |
| 2024-08 | 32 | -$135 | -0.14% | -$170 | -$208 | $0 | $101,865 | $1,761 | $2,366 | None modelled | $0 |
| 2024-09 | 41 | -$772 | -0.77% | -$296 | -$36 | $0 | $101,093 | $1,137 | $2,564 | None modelled | $0 |
| 2024-10 | 37 | $4,031 | +4.03% | -$255 | -$80 | $2,714 | $101,731 | $1,753 | $3,492 | None modelled | $2,614 |
| 2024-11 | 34 | $1,845 | +1.84% | -$182 | -$38 | $922 | $102,423 | $625 | $1,321 | None modelled | $922 |
| 2024-12 | 29 | $565 | +0.57% | -$184 | -$358 | $1,740 | $100,814 | $1,006 | $1,884 | None modelled | $1,740 |
| 2025-01 | 43 | $617 | +0.62% | -$221 | -$30 | $632 | $100,641 | $794 | $2,055 | None modelled | $632 |
| 2025-02 | 35 | $881 | +0.88% | -$190 | -$24 | $0 | $101,522 | $1,510 | $1,748 | None modelled | $0 |
| 2025-03 | 39 | $1,389 | +1.39% | -$181 | -$75 | $40 | $102,861 | $941 | $2,313 | None modelled | $40 |
| 2025-04 | 40 | -$497 | -0.50% | -$147 | -$52 | $291 | $102,000 | $1,567 | $1,707 | None modelled | $291 |
| 2025-05 | 44 | -$3,906 | -3.91% | -$158 | -$90 | $0 | $98,094 | $1,664 | $1,702 | None modelled | $0 |
| 2025-06 | 31 | -$986 | -0.99% | -$132 | -$10 | $0 | $97,108 | $1,126 | $1,734 | None modelled | $0 |
| 2025-07 | 35 | $786 | +0.79% | -$143 | -$17 | $0 | $97,894 | $223 | $1,206 | None modelled | $0 |
| 2025-08 | 30 | $2,465 | +2.46% | -$198 | -$51 | $0 | $100,359 | $413 | $1,260 | None modelled | $0 |
| 2025-09 | 41 | $1,598 | +1.60% | -$308 | -$60 | $447 | $101,398 | $1,635 | $2,215 | None modelled | $447 |
| 2025-10 | 41 | $7,235 | +7.23% | -$157 | -$26 | $5,306 | $102,000 | $418 | $1,785 | None modelled | $5,306 |
| 2025-11 | 28 | -$944 | -0.94% | -$191 | -$19 | $0 | $101,056 | $1,460 | $2,052 | None modelled | $0 |
| 2025-12 | 31 | $3,286 | +3.29% | -$241 | -$9 | $2,279 | $101,493 | $408 | $2,430 | None modelled | $2,279 |
| 2026-01 | 38 | $1,809 | +1.81% | -$318 | -$3 | $21 | $103,276 | $3,119 | $4,380 | None modelled | $21 |
| 2026-02 | 33 | $6,464 | +6.46% | -$191 | -$82 | $3,632 | $105,199 | $1,139 | $1,876 | None modelled | $3,632 |
| 2026-03 | 40 | $2,224 | +2.22% | -$276 | -$2 | $4,339 | $102,000 | $1,775 | $1,980 | None modelled | $4,339 |
| 2026-04 | 37 | $1,490 | +1.49% | -$227 | -$10 | $1,192 | $102,000 | $709 | $1,856 | None modelled | $1,192 |
| 2026-05 | 40 | -$1,725 | -1.73% | -$289 | $0 | $0 | $100,275 | $1,596 | $1,835 | None modelled | $0 |
| 2026-06 | 38 | $1,269 | +1.27% | -$217 | -$3 | $397 | $101,047 | $1,316 | $1,907 | None modelled | $397 |
| 2026-07 | 40 | $6,234 | +6.23% | -$297 | -$2 | $4,225 | $102,000 | $435 | $1,929 | None modelled | $4,225 |
| 2026-08 | 40 | $2,935 | +2.94% | -$342 | $0 | $2,348 | $102,000 | $1,608 | $3,046 | None modelled | $2,348 |

Total proposed funded-start net: $69,461; total trader claims: $53,969; mean per calendar month: $1,499; median monthly claim: $448; zero-claim months: 13/36.

Challenge-start funded activation estimate: 2024-05-21T14:46:39+00:00; trader claims over the same overall window: $38,811. Evaluation fee/refund, tax, FX conversion and transfer delays are excluded.

## Per-EA contribution to the concurrent safer portfolio

| EA | Trades closed | Net contribution | Win rate | PF | Commission | Swap | Extra stress deduction |
|---|---:|---:|---:|---:|---:|---:|---:|
| News Pulse XAU | 88 | -$584 | 47.7% | 0.96 | -$384 | $0 | $15,466 |
| News Pulse XAG | 97 | $9,635 | 49.5% | 1.45 | -$4,196 | $0 | $27,984 |
| ORB Volume Profile Confirmed | 65 | $3,481 | 44.6% | 1.42 | -$159 | $0 | $2,448 |
| XAU Trend Progression | 88 | $14,607 | 61.4% | 2.16 | -$111 | $0 | $4,816 |
| USDJPY London Open Momentum | 411 | $6,747 | 46.0% | 1.16 | -$2,771 | $0 | $11,943 |
| US100 ORB New York M30 | 60 | $5,025 | 50.0% | 1.50 | -$158 | -$79 | $2,997 |
| US100 H1 ORB 13UTC | 176 | $14,692 | 53.4% | 1.57 | -$367 | -$803 | $8,117 |
| EMA3 Safe | 73 | $8,001 | 65.8% | 1.92 | -$34 | $0 | $3,224 |
| XAU Squeeze Momentum Standard | 86 | $3,859 | 44.2% | 1.45 | -$77 | -$1,134 | $2,756 |
| XAU RSI VWAP | 131 | $3,998 | 77.9% | 1.41 | -$238 | $0 | $3,383 |

Payout belongs to the account, not an individual EA: per-EA profit is attribution, not a separately withdrawable reward.

## Sources

- [FTMO 2-Step objectives](https://ftmo.com/en/trading-objectives/)
- [FTMO rewards: timing, 80% share and rollover](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/)
- [FTMO Swing leverage by asset class](https://ftmo.com/en/blog/a-few-answers-to-your-questions/)
- [Current symbol specification page](https://ftmo.com/en/symbols/)

Eight deterministic tests cover chronology, conservation, deficit recovery, terminal failure, shared margin, minimum entry days, news exemption and Prague DST. Full runs also assert monthly accounting identities, closed-trade ordering and no orphan positions.
