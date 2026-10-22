# Turtle breakout portfolio (Revelio adaptation) — raw study report (2026-10-22)

**Verdict:**
- **HOLD (hold overnight) PASSES the raw gate.**
- **DAY (day-trading version) FAILS:** 5-year result +0.5%, PF 1.00, 58% drawdown.
- The video's claim that day-trading is better is **not reproduced**.
- HOLD is a raw survivor with large risk: 47% worst equity drawdown and −35% in 2022. Its profit came from gold, silver
  and Bitcoin trends; the two index legs lost after swap.
- Research only. Isolated tester `_Backtests/MT5-DMC-20260811` (Exness-MT5Trial16). Nothing installed, deployed or pushed.

**Files:**
- Rules: [RULES.md](RULES.md), frozen before testing, plus 4 recorded EA-fix revisions (see "Implementation fixes").
- Tables: [RESULTS.md](RESULTS.md) / `RESULTS.json`. Chart: `equity.png`.
- EA: `EA/Turtle Portfolio Research EA.mq5`.

## What was tested
- **Assets:** US500 (S&P 500), USTEC (Nasdaq 100), XAUUSD (gold), XAGUSD (silver), BTCUSD. One $100k account, long only.
- **Daily bars:** built from M30 data on the 17:00 → 17:00 New York trading day.
- **Rules (video + Pine code):**
  - Entry: price breaks above the 20-day high.
  - Fixed stop: 2 × ATR(20) below the entry level.
  - Trailing exit: 10-day low; the exit is the higher of the two. No take profit.
  - Risk: 2% of high-water-mark equity per trade, lots rounded up.
- **DAY:** close at 16:30 NY, re-enter from 18:00 NY while the trade is still valid, flat over weekends.
- **Test setup:**
  - Native MT5 **Model 4**, 150 ms, end 2026-10-22 exclusive.
  - Separate 6m / 1y / 3y / 5y windows; 6 random-entry controls and 3 sensitivities on 5y.
  - 0 failed or rejected orders in every valid run.
  - The tester's US500/USTEC history only starts in 2019, so the video's 11 years cannot be rebuilt.
- **Trade count:** a trade is one breakout signal; DAY re-entries belong to the same trade. Positions are counted separately.

## Main results (native MT5 Model 4)
| Version | Window | Return | CAGR | Sharpe | Equity DD (max %) | Trades | / month | / day | Positions | PF | Win % | Mean R | Swap $ | Return before swap |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **HOLD** | 6m | +8.31% | 17.3% | 0.80 | 11.83% | 15 | 2.49 | 0.082 | 15 | 1.72 | 46.7 | 0.28 | −3,935 | +12.2% |
| **HOLD** | 1y (last year) | +19.16% | 19.2% | 0.69 | 33.75% | 32 | 2.67 | 0.087 | 32 | 1.45 | 31.2 | 0.26 | −8,656 | +27.8% |
| **HOLD** | 3y | +153.31% | 36.3% | 1.17 | 34.68% | 107 | 2.97 | 0.097 | 107 | 1.84 | 45.8 | 0.43 | −69,024 | +222.3% |
| **HOLD** | 5y | +111.59% | 16.2% | 0.64 | **46.90%** | 177 | 2.95 | 0.096 | 177 | 1.47 | 38.4 | 0.21 | −89,399 | +201.0% |
| DAY | 6m | +2.45% | 5.0% | 0.32 | 14.40% | 15 | 2.49 | 0.082 | 245 | 1.18 | 40.0 | 0.11 | −2,477 | +4.9% |
| DAY | 1y (last year) | +6.97% | 7.0% | 0.38 | 32.38% | 32 | 2.67 | 0.087 | 475 | 1.17 | 28.1 | 0.08 | −4,927 | +11.9% |
| DAY | 3y | +53.44% | 15.3% | 0.61 | 34.99% | 107 | 2.97 | 0.097 | 1,857 | 1.36 | 37.4 | 0.19 | −36,371 | +89.8% |
| DAY | 5y | +0.53% | 0.1% | 0.19 | 57.94% | 177 | 2.95 | 0.096 | 2,865 | 1.00 | 31.6 | −0.00 | −48,542 | +49.1% |

- **Drawdown:** the largest % equity drop from a peak (MT5 "relative"). The HOLD 5y worst drop came in 2022. MT5's
  "maximal" figure (35.1%) is smaller because it is measured at the largest dollar loss, later in the run, after
  compounding.
- **Balance drawdowns** (closed trades) are in RESULTS.md: HOLD 5y 50.2%, DAY 5y 56.8%.
- **/ day** is per calendar day (Bitcoin trades 7 days a week).
- **Mean R** = trade net ÷ (2% × HWM at entry).
- **Return before swap** is a diagnostic only: swap added back, no re-compounding.

### Per year (5-year runs)
| Version | 2021 (from Oct 22) | 2022 | 2023 | 2024 | 2025 | 2026 (to Oct 22) |
|---|---|---|---|---|---|---|
| HOLD | −9.9% | **−35.1%** (DD 41%) | +69.1% | +32.6% | +38.0% | +16.9% (DD 31%) |
| DAY | −12.2% | **−48.3%** (DD 50%) | +50.1% | +12.0% | +18.7% | +11.0% |

### Per asset — 5 years
| Asset | HOLD trades | HOLD net $ | HOLD PF | HOLD swap $ | DAY net $ | DAY PF |
|---|---:|---:|---:|---:|---:|---:|
| US500 | 34 | −6,320 | 0.86 | −28,772 | −7,273 | 0.77 |
| USTEC | 37 | −1,955 | 0.96 | −23,939 | −6,084 | 0.83 |
| XAUUSD | 32 | +32,160 | 1.77 | −14,466 | +9,623 | 1.27 |
| XAGUSD | 34 | +27,841 | 1.56 | −8,470 | −26,396 | 0.51 |
| BTCUSD | 40 | +59,860 | 2.22 | −13,751 | +30,664 | 1.73 |

The two index legs lost money after swap; before swap they were about +$44k combined. The largest HOLD trades were:
- silver, Nov 2025 → Jan 2026: +$38.4k;
- gold, Aug → Oct 2025: +$21.5k;
- Bitcoin, Oct → Dec 2023: +$20.4k;
- Bitcoin, Aug → Sep 2026: +$20.1k;
- Nasdaq, Apr → Jun 2026: +$19.1k.

## Controls (5 years, same stops, sizing and schedule; random long entries at 18:00 NY, matched rate p = 0.0253 per symbol-day)
| Version | Return | Trades | / month | / day | PF | Mean R | Equity DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| **HOLD** | **+111.6%** | 177 | 2.95 | 0.096 | 1.47 | **0.208** | 46.9% |
| Random HOLD seed 1 / 2 / 3 | +57.1% / +23.3% / +27.1% | 131 / 145 / 136 | 2.2–2.4 | 0.07–0.08 | 1.46 / 1.18 / 1.22 | 0.176 / 0.080 / 0.087 (mean 0.114) | 27–32% |
| DAY | +0.5% | 177 | 2.95 | 0.096 | 1.00 | −0.003 | 57.9% |
| Random DAY seed 1 / 2 / 3 | +8.0% / −13.9% / −4.3% | 125 / 136 / 127 | 2.1–2.3 | 0.07 | 1.07 / 0.88 / 0.96 | 0.033 / −0.050 / −0.008 (mean −0.008) | 31–49% |

- **HOLD** beats every random seed on return and mean R. But random long entries with the same exits still made +23% to
  +57%: holding long through the 2023–2026 gold, silver and Bitcoin trends explains much of the result. The breakout
  entry adds about +0.09 R per trade over random. With only three seeds, this is a weak control.
- **DAY** is no better than random entries.

## Sensitivities (declared before testing on DAY; 5 years)
| Version | Return | Trades | / month | PF | Equity DD |
|---|---:|---:|---:|---:|---:|
| S55: 55-day entry / 20-day exit (Turtle System 2) | −3.8% | 80 | 1.33 | 0.97 | 51.9% |
| SATR3: 3 ATR fixed stop | −6.8% | 173 | 2.88 | 0.95 | 41.9% |
| SR1: 1% risk | −0.1% | 177 | 2.95 | 1.00 | 29.2% |

Every DAY variant is flat to negative. Sensitivities for HOLD were not declared and were not run.

## Raw gate
| Version | Positive 3y & 5y | PF ≥ 1.15 3y & 5y | ≥ 30 trades | Mean R > random mean | Best day / best trade | Verdict |
|---|---|---|---|---|---|---|
| HOLD | yes | yes (1.84 / 1.47) | yes (177) | yes (0.208 vs 0.114) | yes (5y without best day +$73,180) | **PASS** |
| DAY | yes (barely) | **no** (1.36 / 1.00) | yes | yes (−0.003 vs −0.008) | **no** (5y without best day −$6,721) | **FAIL** |

Diagnostic: without its 5 best days, HOLD turns negative (3y −$4,500; 5y −$22,012). A few big trends carry the result.

## Versus the video's claims
| | Video HOLD (~11 y) | Ours HOLD 5y | Ours HOLD 3y | Video DAY | Ours DAY 5y |
|---|---:|---:|---:|---:|---:|
| CAGR | 27.3% | 16.2% | 36.3% | 31.2% | 0.1% |
| Max drawdown | 37.6% | 46.9% | 34.7% | 37.9% | 57.9% |
| PF | 1.88 | 1.47 | 1.84 | 2.11 | 1.00 |
| Sharpe | 1.04 | 0.64 | 1.17 | 1.31 | 0.19 |
| Losing years | 2018, 2022 | 2021 (Q4), 2022 | — | — | 2021 (Q4), 2022 |

- **HOLD:** the 3-year numbers match the video's profile, and 2022 is a losing year in both. Over 5 years it is weaker,
  with a deeper drawdown.
- **DAY:** much worse here than in the video, for three reasons.
  1. **Swap:** this tester charges swap at 00:00 UTC, so DAY positions held from 18:00 to 16:30 NY still pay it
     ($48.5k over 5 years). The video's broker likely rolls over at 17:00 NY, during the flat window.
  2. **Missed overnight moves:** even before swap DAY made +49% against HOLD's +201%. Trend gains come largely
     overnight and over weekends, and closing every afternoon gives them up. Silver flips from +$27.8k (HOLD) to
     −$26.4k (DAY).
  3. **Early closes:** in US winter and in older index data, the tester cannot trade until 16:30 NY, so DAY closes at
     about 15:50–15:55 NY instead (see below).

## Implementation fixes during the study (all recorded in RULES.md before the final runs)
1. **v2 — stop raise:** the daily stop raise was rejected because indices and metals are closed at 17:00 NY. It is now
   applied at the first tradable tick. This affected HOLD; 3 runs were redone.
2. **v3 — winter close:** the tester's fixed-UTC summer session table blocks 16:00–17:00 NY in US winter. DAY now
   closes 5 minutes before the session ends.
3. **v4 — early quote end:** older index quotes stop before 16:30 NY (15:58 NY in 2022). DAY now closes 5 minutes before
   the previous day's last quote.
4. **v5 — per weekday:** Friday quotes end earlier than Monday to Thursday, so the quote-end time is learned per weekday
   and seeded from M1 bars before the start. There is no look-ahead.

- Each fix was checked with dedicated smoke tests, and HOLD was proven identical across v2→v5 (parity trades).
- **Builds behind the final runs:**
  - HOLD windows: v2 `a65596191b1e`.
  - RND_HOLD controls: v3.
  - All DAY runs, DAY controls and sensitivities: v5 `8b020cb9c17f`.
- Invalid runs are kept in the `native-INVALID-*` folders.
- **Remaining limitation:** 71 of 2,865 DAY positions (2.5%) were held over 23 h, all around US market holidays
  (Thanksgiving, Christmas, New Year, MLK, Presidents' Day, Good Friday, Memorial Day, Juneteenth, July 4, Labor Day).
  The EA has no holiday calendar.

## Limitations
- **Tick data:** older ticks are generated. The 5y reports show 16% real ticks; real ticks start in 2026.
- **Window:** 5 years, not the video's 11. 2023–2026 was a strong trend regime for gold, silver and Bitcoin.
- **Costs:** Exness CFD swaps are large (HOLD paid $89k over 5 years on a $100k start). Futures or another broker would
  have a different cost profile.
- **Winter hour:** in US winter, HOLD cannot trade 16:00–17:00 NY, because of the tester's fixed session table.
- **Leverage:** 1:2000 means margin never binds here. Five concurrent positions at 2% risk could hit margin limits at
  lower leverage.
- **Weak control:** the random control has only 3 seeds.
- **Not optimised:** no stage 5 (dev/val/OOS), plateau check, Monte Carlo or Bear review was done. The OOS window
  2024-10-22 → 2026-10-22 has now been viewed, so it is retrospective for any stage-5 split.

## Recommendation
- **DAY:** reject.
- **HOLD:** a raw survivor that may advance to stage 5 only with the owner's approval. Points to settle first:
  1. Is a 47% worst drawdown and a −35% year acceptable at 2% risk? A 1% HOLD version would roughly halve it.
  2. How much is trend-following edge, and how much is long exposure to assets that rose? A bigger random-entry control
     and a buy-and-hold benchmark per asset are needed.
  3. Should the two losing index legs be kept? Deciding now would be post-hoc selection; it should be tested inside a
     proper dev/val/OOS split.
  4. Swap is a cost of about 89% of starting capital over 5 years.
- Nothing installed, no SET/BAT/live change, no push.
