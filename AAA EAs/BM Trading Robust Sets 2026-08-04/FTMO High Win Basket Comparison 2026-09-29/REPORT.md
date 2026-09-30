# FTMO: proposed high-win basket versus the current portfolio

29 September 2026. **Analysis only: nothing deployed or changed on any trading account.** XAU RSI VWAP and Nasdaq 5M are included as requested.

## Verdict

**Better historical win rate and lower drawdown; worse historical profit, challenge speed and six-month reward totals.** The high-win basket is not a clear upgrade for FTMO. Keep the current 13-EA package as the comparison baseline; the proposed basket merits a separate demo test, not an automatic replacement.

The comparison uses **27 September 2025–31 August 2026, 339 calendar days**, the common supported period. It is not a full trailing year. The newer Current13 result for the longer original period was reproduced exactly before clipping all baskets to the same dates. Returns below are account equity changes, not withdrawals; all three have one open position at the common endpoint.

## Baskets and settings

**Proposed eight**, using one EMA3 version, not two:

1. Gold Overnight Value Area — raw.
2. ORB Volume Profile — retained 0.75R high-win version.
3. EMA3 — retained Safe version.
4. US100 H1 ORB — 1R + ADX14 ≥25.
5. XAU Squeeze Momentum — retained Safe version.
6. Nasdaq Overnight — newer audited inputs.
7. XAU RSI VWAP — newer audited inputs, included despite its standalone PF1.18.
8. Nasdaq 5M — DI14/EMA12 agreement, 0.60% price stop, ATR6 trailing from +1R, no TP.

Nasdaq's selected recent-year standalone result is 51.40% wins / PF1.48 / 179 trades. This is the best win rate among the completed comparable catalogue and recent management variants examined that satisfy PF≥1.2. It is already present in Current13: no duplicate is added. The older 0.75R Nasdaq test returned PF0.85 over its recent two-month window and is not used. The cancelled DI-toggle comparison was not resumed.

**Core5** is a cleaner subset check: Gold Overnight, current audited EMA3, Nasdaq Overnight, XAU RSI VWAP and Nasdaq 5M, all using the same source versions as Current13. It tests removing EAs without introducing older high-win versions.

Every basket shares a $10,000 account with a **fixed maximum $50 planned initial-stop risk per entry** (0.5% of initial capital), lots rounded down, News OFF. Same FTMO contract/margin/cost assumptions. Main policy A closes at daily net equity change of -$200 or +$400 from Prague-midnight balance and stops entries for that day; one-minute observation-to-execution delay. These policies replace the package's previous internal governors; this is not an exact replay of the unchanged launcher with every original guard stacked on top.

## Same-period continuous replay — main policy A

| Basket | Equity return | Net PF | Net win rate | Closed trades | Equity DD | Worst daily loss | Max winning / losing streak |
|---|---:|---:|---:|---:|---:|---:|---:|
| Current 13 EAs | +67.38% | 1.55 | 54.02% | 746 | 5.46% | 2.09% | 11 / 9 |
| Proposed high-win 8 EAs | +41.88% | 1.67 | 63.23% | 465 | 3.00% | 1.75% | 27 / 5 |
| Current-version core 5 EAs | +31.21% | 1.59 | 62.03% | 374 | 3.71% | 1.75% | 22 / 5 |

Streaks describe the combined chronological closed-trade sequence across bots, not a forecast or individual-EA streak. Simultaneous exits follow the engine's deterministic order. Higher win rate does not make smaller profits arrive more often: the proposed basket has materially fewer accepted trades.

No sampled FTMO daily/total breach or adverse M1-envelope flag occurred in these continuous reference runs. That does not prove tick-level compliance. Current13 hit the +4% daily goal five times and the -2% stop twice; the proposed eight hit neither. The +4% level is a stop-taking-profit threshold, **not an expected daily return**.

## Why the standalone shortlist does not translate directly to a $10K account

Under the modeled 0.01-lot gold minimum, many wide-stop gold signals cannot fit the $50 risk budget and are skipped. In the proposed basket, **126 entries were rejected for sizing**, with no margin rejections. EMA3 Safe supplied 34 common-window signals but only three were accepted; XAU Squeeze Safe supplied ten but only three were accepted. Their attractive standalone one-year win rates are therefore not the win rates of a fully tradable 0.5%-risk FTMO stream. Exact broker minimum lots remain an assumption requiring account-specification verification.

Closed-trade contribution in the proposed eight (floating P/L at the endpoint is excluded):

| EA | Closed trades | Net contribution | Wins |
|---|---:|---:|---:|
| nasdaq-5m-candle-momentum | 164 | $2,324.32 | 85 |
| orb-vp-075r | 43 | $282.32 | 29 |
| gold-overnight-value-area | 122 | $331.87 | 89 |
| nasdaq-overnight | 66 | $365.92 | 42 |
| us100-h1-orb-rr1-adx25 | 45 | $633.11 | 31 |
| xau-squeeze-safe | 3 | $31.10 | 1 |
| xau-rsi-vwap | 19 | $212.41 | 16 |
| ema3-safe | 3 | $-2.52 | 1 |

Nasdaq 5M generates more than half the proposed basket's closed profit. The eight names do not imply eight equally contributing or independent edges. Five are gold strategies and three trade Nasdaq; concentration remains.

## FTMO phase and first-reward scenarios

Same weekly start dates for all portfolios, from September 2025 onward. There are **23 starts with complete 180-day follow-up**. Median times are calendar days from the start of phase 1 and are conditional on reaching that milestone within 180 days. Unfinished cases are not discarded from success counts or average reward amounts. These are overlapping historical scenarios, **not estimated future pass/payout probabilities**.

| Basket | Both phases within 180d | First request within 180d | Median phase 1 days | Median both phases days | Median first-request days | Mean trader share requested in 180d, all starts |
|---|---:|---:|---:|---:|---:|---:|
| Current 13 EAs | 23/23 | 23/23 | 44 | 78 | 100 | $1,379 |
| Proposed high-win 8 EAs | 23/23 | 22/23 | 64 | 114 | 138 | $309 |
| Current-version core 5 EAs | 16/23 | 8/23 | 113 | 153 | 170 | $60 |

The 120-day view uses a larger, separately eligible cohort of 31 starts:

| Basket | Both phases within 120d | First request within 120d |
|---|---:|---:|
| Current 13 EAs | 31/31 | 29/31 |
| Proposed high-win 8 EAs | 14/31 | 5/31 |
| Current-version core 5 EAs | 3/31 | 0/31 |

Lifecycle assumptions: flat +10% Challenge and +5% Verification targets, four distinct Prague opening days per phase; two and five assumed business days between phases/funded access. First funded request after 14 full calendar days from the first funded trade, at least $50 gross closed profit, no open position. Withdraw all gross profit; modeled trader share is 80%, restart at $10K after two assumed business days. No challenge fees/refunds, tax, transfer charges or actual approval delay are included. These are modeled **request amounts, not cash received**. The six-month totals include time spent in the evaluation phases.

Official [FTMO 2-Step objectives](https://ftmo.com/en/trading-objectives/) confirm the 10%/5% targets, 5% daily equity loss, 10% static overall loss and four opening days. [Reward rules](https://ftmo.com/faq/how-do-i-withdraw-my-profits/) specify the 14th-day request eligibility and 80% base 2-Step share; the extra day-count/admin conventions above are modeling choices. [Swing rules](https://ftmo.com/en/faq/ftmo-swing-account-type/) allow overnight/weekend holding. Sources checked 29 September 2026.

## Sensitivity — not calibrated forecasts

Higher costs add the earlier audit's adverse per-round-trip execution allowance (gold $0.20/oz, Nasdaq 2 points, USDJPY0.02) and double negative source swaps. Weaker-edge sensitivity additionally cuts positive gross outcomes by10% and enlarges negative gross outcomes by10%. Reference native spreads and commissions were already present; these are extra costs.

| Basket / case | Return | PF | DD | Both phases /23 at180d | First request /23 at180d | Mean180d trader share |
|---|---:|---:|---:|---:|---:|---:|
| Current 13 EAs / Higher costs | +59.19% | 1.47 | 5.99% | 23 | 23 | $1,182 |
| Proposed high-win 8 EAs / Higher costs | +38.06% | 1.60 | 3.17% | 22 | 19 | $229 |
| Current-version core 5 EAs / Higher costs | +27.92% | 1.52 | 4.02% | 8 | 5 | $23 |
| Current 13 EAs / Costs + weaker edge | +28.88% | 1.21 | 7.25% | 21 | 14 | $153 |
| Proposed high-win 8 EAs / Costs + weaker edge | +21.35% | 1.31 | 4.50% | 3 | 2 | $8 |
| Current-version core 5 EAs / Costs + weaker edge | +14.21% | 1.24 | 5.38% | 0 | 0 | $0 |
| Current 13 EAs / 5-minute liquidation | +65.63% | 1.54 | 5.52% | 23 | 23 | $1,340 |
| Proposed high-win 8 EAs / 5-minute liquidation | +41.88% | 1.67 | 3.00% | 23 | 22 | $309 |
| Current-version core 5 EAs / 5-minute liquidation | +31.21% | 1.59 | 3.71% | 16 | 8 | $60 |

In the weaker-edge case, the proposed basket has lower DD but only 3/23 scenarios complete both phases within six months versus21/23 for Current13. Most non-completions are unfinished, not rule breaches. This illustrates why high win rate and comfortable drawdown are not the same as fast challenge completion.

## Approach B: open-risk cap instead of daily-loss stop

B limits original open-stop commitments to $250 and keeps the +$400 daily profit close, but removes the internal daily-loss close. FTMO's own equity rules still apply.

| Basket / cost case | Return | PF | DD | Worst daily loss |
|---|---:|---:|---:|---:|
| Current 13 EAs / Reference | +66.58% | 1.55 | 5.51% | 2.11% |
| Proposed high-win 8 EAs / Reference | +41.88% | 1.67 | 3.00% | 1.75% |
| Current-version core 5 EAs / Reference | +31.21% | 1.59 | 3.71% | 1.75% |
| Current 13 EAs / Higher costs | +58.36% | 1.46 | 6.05% | 2.16% |
| Proposed high-win 8 EAs / Higher costs | +38.06% | 1.60 | 3.17% | 1.77% |
| Current-version core 5 EAs / Higher costs | +27.92% | 1.52 | 4.02% | 1.77% |

The proposed eight have identical continuous results under A and B because neither its daily triggers nor its open-risk cap binds in this period. This is not evidence that a loss stop is unnecessary. Reusing risk capacity can accumulate daily losses even when open risk stays below a cap. Retain A as the comparison default; no settings were changed.

## Evidence limits and verification

- This is an offline source-trade / M1 marked-equity overlay, not a fresh native shared-account FTMO tick test. Signals are not regenerated after forced exits/skips. Source-total swap is accrued approximately over the observed trade duration. Exness history is translated using FTMO contract/cost/margin assumptions; actual historical FTMO fills and minimum lots are not verified.
- ORB0.75R, EMA3 Safe and Squeeze Safe are older retained versions with stale build evidence; H1 ORB ADX25 is a retrospective research selection. Combining them with newer current ledgers is a provisional candidate comparison, not a proven current-build alternative. Selection on overlapping history biases it favourably.
- The latest-year native histories use real ticks mainly from January2026, with generated earlier ticks; generic cached history-quality labels do not certify full real-tick coverage. M1 sampling can miss intraminute breaches; worst-symbol extremes need not coincide.
- Per-trade risk is held at a fixed $50 maximum before execution costs; it is not compounded or raised for the smaller basket. Stop gaps, costs and observation/fill delay can exceed intended losses.
- Original stop/cash identities and new cache-to-native ledgers were checked. Existing Current13 matrix reconstruction is identical after relabelling keys; the earlier full-period reference replay has zero metric difference. All source hashes remain unchanged. 56 synthetic test executions passed (including inherited duplicate tests).
- Verified 792 lifecycle paths, 2683 stages, 993 reward requests and 18 continuous runs. See VERIFICATION.json, SOURCE_AUDIT.json, RESULTS.json and LIFECYCLE.json for retained evidence.

## Practical decision

If the priority is **historical challenge speed and reward amount**, Current13 wins this comparison. If the priority is **higher win rate and a calmer historical equity path**, HighWin8 looks better—but its older/research builds and reduced trade frequency prevent calling it a superior FTMO system. Keep it as a separate demo candidate until those versions are retested under exact account constraints. Nothing was removed from or added to live trading.
