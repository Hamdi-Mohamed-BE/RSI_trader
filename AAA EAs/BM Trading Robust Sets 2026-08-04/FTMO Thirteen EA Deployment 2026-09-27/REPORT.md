# FTMO $10K Swing — 13 EAs, News OFF

Prepared 27 September 2026. No active account was accessed, restarted, armed or traded. The isolated research tester ran mock-only guard tests; that is not a live forward test.

## What changed

- All eight maintained normal MT5 launchers now select Nasdaq 5M DI(14) agreement + EMA12, 4 ATR initial stop, fixed 2.5R target; no ATR trail, break-even, or added D1 Markov gate. Existing normal risk policies remain unchanged, including the Recommended Adaptive 0.25x Nasdaq multiplier.
- Ava and archived/research launchers were not changed.
- A separate FTMO launcher installs ONLY the 13 builds listed below. News Pulse XAU and Gold News V9 are omitted; no news service is started. The ordinary launchers' news settings are unchanged.
- FTMO copies are isolated; the original EA sources/binaries were not rewritten. Do not substitute ordinary EAs into this profile: they do not have this guard.

## Launcher

File in the parent folder: **FTMO 10K SWING - 13 EAS - NEWS OFF.bat**.

1. Open the intended FTMO terminal and log in yourself. Turn Algo Trading OFF.
2. The account must have no positions or pending orders. The launcher will not close them.
3. Run the BAT, select Challenge / Verification / Funded, and review the detected account and symbols.
4. Confirm that it really is a USD $10,000 **2-Step Swing** product. The API cannot verify your purchase type.
5. It installs an isolated profile and restarts only that selected terminal. Algo Trading stays OFF.
6. Inspect the 13 charts, inputs and Experts tab. Forward-test on FTMO Free Trial/demo first. Enable Algo Trading yourself only after this review.

Use one terminal/VPS for this account, with no other EAs or manual trading. Account/server/symbol changes block these EAs. A new phase/account needs a new installation binding. There is no automated purchase, phase switching, reward request, or payout.

## Portfolio and settings

| EA | Asset | Chart |
|---|---|---|
| XAU RSI VWAP | XAUUSD (resolved dynamically) | H1 |
| Gold Overnight Value Area | XAUUSD (resolved dynamically) | M5 |
| XAU Squeeze Momentum Standard | XAUUSD (resolved dynamically) | H1 |
| DMC Fresh Reaction US100 | USTEC (resolved dynamically) | H1 |
| EMA3 | XAUUSD (resolved dynamically) | H4 |
| XAU Trend Progression | XAUUSD (resolved dynamically) | H4 |
| XAU ORB London NY Overlap M30 | XAUUSD (resolved dynamically) | M30 |
| Nasdaq Overnight | USTEC (resolved dynamically) | M1 |
| US100 H1 ORB 13UTC | USTEC (resolved dynamically) | M15 |
| USDJPY London Open Momentum | USDJPY (resolved dynamically) | M15 |
| US100 Month End Flow | USTEC (resolved dynamically) | M30 |
| DMC Current XAU | XAUUSD (resolved dynamically) | H1 |
| Nasdaq 5M Candle Momentum | USTEC (resolved dynamically) | M5 |

All entries/exits use the frozen fourteen-EA study settings, except News is excluded. Exact inputs, source fingerprints and compiled-file fingerprints are in PACKAGE.json.

## Risk controls

| Control | Setting |
|---|---|
| Planned stop risk | Fixed maximum $50 per entry, not compounding |
| Lot policy | Broker step rounded DOWN; skip if minimum lot exceeds budget |
| Aggregate initial open risk | $225 |
| Per-symbol initial open risk | $150; all gold EAs share this budget |
| Daily admission budget | $300 using Prague day and floating/reserved losses |
| Projected equity floor | $9,200 |
| Margin | At most 80% of conservative projected equity, with actual broker margin calculation |
| Entries per Prague day | At most 7, counted across the account |
| Loss stop | No new entries after 3 net losing closed positions that day |
| Escalation | No martingale; no adaptive taper; no Nasdaq 0.25x factor in this FTMO profile |
| Target pause | New entries stop after phase target + 4 opening days; wait for flat/review |

$50 excludes commission, swap, gaps and adverse execution. Actual loss can exceed it. The guard observes floating equity on ticks/timers but does not forcibly liquidate trades. Existing broker stops remain essential. It rejects missing SLs, new pending orders, removed/widened stops, unprotected exposure, missing history, wrong funding size, and uncertain execution.

The guard retains initial risk when a stop moves to profit. It reserves 1.25x stop risk plus $5 per position and negative accrued swap, and uses actual floating equity when lower. Daily/total breaches latch entries off; an uncertain execution also requires manual reconciliation. Do not delete guard state to bypass a loss stop.

Request pacing: failed market-closed management retries wait 15 minutes, other failed management 60 seconds. New entries stop at 1,400 EA requests/day; protective modifications at 1,700; absolute ceiling 1,900 for all guarded requests. At the absolute ceiling automated exits also pause: the Experts log flags this and operator review is required. Existing server stops/targets remain. This does not count external/manual requests, another PC, or other software, and is not a guarantee of contract compliance.

## News-off simulation

**These are fitted-history scenario results, not calibrated probabilities or an exact live-package backtest.** Source signals: 27 September 2025 through 27 September 2026 exclusive; Exness native histories, not FTMO-native execution. 51 complete joint weeks, 1,000 paired resampled paths per case, seed 20260927. Native tick coverage was mixed (approximately 73% real ticks across the year); broker transfer remains unvalidated.

The replay preserves the prior study's stops, reserve model, costs and guard assumptions with News removed. It cannot reconstruct shared-account tick equity. The deployment adds stricter real-time floating-equity checks, $5 reserves, execution reconciliation and request throttles, so live admissions and results can differ. This is a useful planning estimate, not a promise that the new wrapper reproduces these exact trades.

Reference costs include native fills and commission floors. The stress case reduces gross winners 10%, enlarges gross losers 10%, adds adverse movement ($0.20 gold, two US100 points, 0.02 USDJPY), doubles negative native swaps, and adds carry reserves. Full inherited assumptions: ../FTMO Fourteen EA Study 2026-09-27/PROTOCOL.md.

### One-year continuous account (no phase resets)

| Risk | Costs | Trades | Return | Win rate | PF | Balance DD | Stop-reserve DD* | Trades/weekday |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| $50 | Reference | 797 | +61.89% | 50.82% | 1.43 | 5.24% | 6.97% | 3.07 |
| $50 | Stressed | 796 | +17.86% | 49.87% | 1.11 | 7.43% | 9.69% | 3.06 |
| $70 | Reference | 793 | +93.94% | 52.84% | 1.48 | 5.48% | 6.34% | 3.05 |
| $70 | Stressed | 763 | +34.01% | 52.16% | 1.16 | 9.12% | 10.31% | 2.93 |

*Stop-reserve DD is NOT measured tick-equity drawdown. $70 is a sensitivity only; the BAT uses $50.

### Phase timing — $50 profile, news OFF

Calendar-day medians below are **conditional on achieving each milestone within 180 days**. Unfinished paths are not included in these medians. Separate medians do not add up to total funding time.

| Milestone | Reference costs | Stressed costs |
|---|---:|---:|
| Challenge, from purchase | 51.8 days | 80.7 days |
| Verification, from its availability | 24.3 days | 29.6 days |
| Funded activation, from purchase | 88.7 days | 119.9 days |
| First reward receipt, from purchase | 112.8 days | 134.3 days |

Review delays assumed: two business days between phases, five to funding activation, four to first reward receipt after request eligibility (14 calendar days from the first funded trade, flat and at least $25 closed profit). These administrative times are assumptions, not FTMO promises.

### Deadline frequencies — $50, stressed costs

| Deadline | Challenge passed | Both phases passed | Funded | First reward received | Still in evaluation |
|---|---:|---:|---:|---:|---:|
| 30 days | 5.6% | 0.3% | 0.1% | 0.0% | 99.7% |
| 60 days | 20.2% | 3.6% | 2.8% | 0.6% | 96.4% |
| 120 days | 45.1% | 19.4% | 17.0% | 9.0% | 80.6% |
| 180 days | 60.1% | 35.0% | 33.6% | 24.2% | 65.0% |

**A one-month pass is not the base expectation here.** Under stressed costs, only 33.6% of modeled paths activate funding by six months; the ~120-day funding median is only among that successful subset. 41.9% of paths touch the internal total-loss admission buffer. Zero modeled rule breaches is NOT zero real failure risk: gaps, equity paths, regime changes, operational failures and provider decisions are not fully modeled.

### Official rules

Designed for FTMO 2-Step Swing: 10% Challenge target, 5% Verification target, four minimum trading days per phase, 5% daily and 10% static total loss limits; Prague midnight accounting. Not the 1-Step product.

- [FTMO trading objectives](https://ftmo.com/en/trading-objectives/)
- [FTMO 2-Step](https://ftmo.com/en/2-step-challenge/)
- [Swing account](https://ftmo.com/en/faq/ftmo-swing-account-type/)
- [Forbidden practices](https://ftmo.com/en/forbidden-trading-practices/)

### Verification

- 13 isolated EA copies compile with 0 errors and 0 warnings.
- Native mock-broker MQL assertions: see GUARD_TESTS.json and compressed journal. No real order requests.
- Eight normal launcher modes, exact Nasdaq inputs, risk-policy preservation, 13 generated charts and file hashes checked.
- Frozen history cash ledgers reconciled; no News rows/placements allowed in any replay.
- Active account has NOT been accessed, installed, restarted or armed. Full forward validation is still required.
