# EMA trailing + ORB 0.50R — combined-account follow-up

Research date: 27 September 2026. No live EA, BAT, website, terminal or account configuration changed.

## What was tested

The current six already include EMA3 Safe and ORB Volume Profile 0.75R. Both interpretations of “add” were tested: replace those two versions (six EAs total), or retain all six and add the modified versions as separate instances (eight total). Two single-change controls isolate the effect of each modification.

The unchanged four are raw Gold Overnight Value Area, Nasdaq Overnight, event-specific News Pulse XAU and event-specific News Pulse XAG. Nasdaq 5M DI and RSI/VWAP are not included.

EMA ATR means the existing frozen M15 test: remove TP, disable original trailing, activate after a completed M15 close reaches +1R, trail the best completed close by 2×ATR(14), never widen the stop. It is not EMA3 at a fixed 0.75R target. ORB uses a fixed 0.50R TP with initial stop and entry rules unchanged, original trailing disabled and original time exits retained.

No new native tick reruns were necessary: all eight required individual EA/exit ledgers already exist from the 24-run MT5 study and were revalidated before these new combined-account simulations. Native source: Exness real ticks, 150 ms fixed delay, 2 March–30 August 2026. These results are **new portfolio ledger replays and Monte Carlo**, not a fresh integrated FTMO tick backtest.

Chronological period: 2026-03-04 through 2026-08-30. 1,000 matched 180-day paths per configuration/cost case, ten cases in total, using the same 26 joint source weeks and seed 20260926. Baseline parity with the preceding study is checked exactly.

## Versions

| ID | Configuration |
|---|---|
| A | Current six EAs |
| I | Replace EMA with ATR and ORB with 0.50R |
| J | Keep six and add EMA ATR plus ORB 0.50R |
| K | Only replace EMA with ATR |
| L | Only replace ORB with 0.50R |

## Shared-account chronological results

Starting balance $10,000. Dollar profit is continuous-account trading P&L, not payout income. Drawdown reserve is a stop-reserve model, not actual combined bid/ask equity. Frequency per weekday includes weekday holidays and zero-trade days.

### Reference costs

| ID | Trades | Per 30 days | Per weekday | Net USD | Return | Win rate | PF | Closed DD | Reserve DD | Max W/L streak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 208 | 34.7 | 1.62 | +$4,673.65 | 46.74% | 70.67% | 3.31 | 1.77% | 2.26% | 9/3 |
| I | 212 | 35.3 | 1.66 | +$4,600.24 | 46.00% | 71.70% | 3.26 | 1.64% | 2.57% | 9/3 |
| J | 239 | 39.8 | 1.87 | +$4,954.71 | 49.55% | 70.29% | 3.00 | 2.06% | 3.02% | 12/3 |
| K | 212 | 35.3 | 1.66 | +$4,611.71 | 46.12% | 70.28% | 3.14 | 1.78% | 2.59% | 9/3 |
| L | 209 | 34.8 | 1.63 | +$4,624.58 | 46.25% | 71.29% | 3.40 | 1.64% | 2.13% | 9/3 |

### Stressed execution costs

| ID | Trades | Per 30 days | Per weekday | Net USD | Return | Win rate | PF | Closed DD | Reserve DD | Max W/L streak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 207 | 34.5 | 1.62 | +$3,229.57 | 32.30% | 69.57% | 2.32 | 2.32% | 2.98% | 9/3 |
| I | 211 | 35.2 | 1.65 | +$3,164.61 | 31.65% | 70.62% | 2.29 | 2.38% | 3.24% | 9/3 |
| J | 237 | 39.5 | 1.85 | +$3,411.28 | 34.11% | 70.04% | 2.17 | 3.11% | 4.51% | 12/3 |
| K | 211 | 35.2 | 1.65 | +$3,150.96 | 31.51% | 69.19% | 2.22 | 2.34% | 3.66% | 9/3 |
| L | 207 | 34.5 | 1.62 | +$3,243.23 | 32.43% | 71.01% | 2.40 | 2.19% | 2.85% | 9/3 |

## Trade frequency — stressed costs

| ID | Calendar days | Weekdays | Active entry days | Per calendar day | Per weekday | Per active day | Per week | Most on one day |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 180 | 128 | 116 | 1.15 | 1.62 | 1.78 | 8.05 | 5 |
| I | 180 | 128 | 116 | 1.17 | 1.65 | 1.82 | 8.21 | 5 |
| J | 180 | 128 | 116 | 1.32 | 1.85 | 2.04 | 9.22 | 6 |
| K | 180 | 128 | 116 | 1.17 | 1.65 | 1.82 | 8.21 | 5 |
| L | 180 | 128 | 116 | 1.15 | 1.62 | 1.78 | 8.05 | 5 |

A trade means an admitted filled position, not a signal, news event or pending order. Each filled news side and each duplicate EA position counts separately. An average does not imply a trade every weekday. Evaluation review pauses can reduce actual challenge activity.

## Conditional FTMO outcomes

These are fitted-history scenario frequencies, not calibrated probabilities for a real account. Timing medians are conditional on reaching that milestone by day 180; separate milestone medians need not add.

### Reference costs

| ID | Funded 60d | Paid 60d | Funded 120d | Paid 120d | Funded 180d | Paid 180d | Breached before first reward | Median funded / paid days |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 27.5% | 6.8% | 87.9% | 71.0% | 98.8% | 98.2% | 0.0% | 79.8 / 100.6 |
| I | 26.6% | 6.7% | 85.9% | 69.8% | 99.0% | 97.8% | 0.0% | 79.8 / 100.8 |
| J | 32.9% | 8.0% | 91.2% | 77.9% | 99.6% | 99.5% | 0.0% | 73.3 / 94.0 |
| K | 27.4% | 7.1% | 86.3% | 69.0% | 98.8% | 98.0% | 0.0% | 79.8 / 100.9 |
| L | 26.1% | 6.4% | 87.0% | 72.3% | 99.3% | 98.3% | 0.0% | 79.8 / 100.7 |

### Stressed execution costs

| ID | Funded 60d | Paid 60d | Funded 120d | Paid 120d | Funded 180d | Paid 180d | Breached before first reward | Median funded / paid days |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 13.9% | 3.0% | 59.8% | 41.3% | 90.7% | 82.7% | 0.0% | 100.8 / 120.6 |
| I | 14.7% | 3.2% | 59.6% | 41.3% | 90.7% | 81.4% | 0.0% | 100.8 / 119.9 |
| J | 16.4% | 3.4% | 68.0% | 48.3% | 94.0% | 88.1% | 0.0% | 94.6 / 114.6 |
| K | 14.7% | 3.2% | 59.0% | 40.0% | 89.6% | 79.0% | 0.0% | 100.8 / 120.0 |
| L | 13.9% | 2.8% | 60.7% | 41.4% | 92.3% | 84.7% | 0.0% | 101.6 / 121.0 |

## Paired payout differences vs current — stressed costs

| ID | 120-day change, percentage points | MC-only interval | 180-day change, percentage points | MC-only interval |
|---|---:|---|---:|---|
| A | 0.0 | 0.0 to 0.0 | 0.0 | 0.0 to 0.0 |
| I | 0.0 | -1.6 to 1.6 | -1.3 | -2.8 to 0.2 |
| J | 7.0 | 5.2 to 8.8 | 5.4 | 3.8 to 7.0 |
| K | -1.3 | -2.6 to -0.0 | -3.7 | -5.1 to -2.3 |
| L | 0.1 | -1.3 to 1.5 | 2.0 | 0.6 to 3.4 |

These intervals measure Monte Carlo sampling error on this fixed source pool only. They do not cover model misspecification, overfitting, broker changes or future market regimes.

## Per-EA contributions — stressed costs

| ID | EA | Trades | Per 30 days | Per weekday | Win rate | PF | Net USD | Max W/L streak |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| A | Gold Value Area raw | 85 | 14.2 | 0.66 | 78.82% | 1.88 | +$541.01 | 18/2 |
| A | News Pulse XAG | 16 | 2.7 | 0.12 | 43.75% | 4.19 | +$1,444.89 | 2/4 |
| A | Nasdaq Overnight | 57 | 9.5 | 0.45 | 61.40% | 1.16 | +$116.68 | 10/3 |
| A | ORB Volume Profile | 35 | 5.8 | 0.27 | 65.71% | 1.36 | +$203.74 | 6/3 |
| A | EMA3 Safe | 4 | 0.7 | 0.03 | 75.00% | 2.52 | +$72.95 | 3/1 |
| A | News Pulse XAU | 10 | 1.7 | 0.08 | 90.00% | 48.36 | +$850.29 | 9/1 |
| I | Gold Value Area raw | 85 | 14.2 | 0.66 | 78.82% | 1.88 | +$541.01 | 18/2 |
| I | News Pulse XAG | 16 | 2.7 | 0.12 | 43.75% | 4.19 | +$1,444.89 | 2/4 |
| I | Nasdaq Overnight | 57 | 9.5 | 0.45 | 61.40% | 1.16 | +$116.68 | 10/3 |
| I | ORB Volume Profile 0.50R | 35 | 5.8 | 0.27 | 74.29% | 1.50 | +$217.40 | 9/2 |
| I | EMA3 Safe ATR trail | 8 | 1.3 | 0.06 | 62.50% | 0.97 | −$5.67 | 3/2 |
| I | News Pulse XAU | 10 | 1.7 | 0.08 | 90.00% | 48.36 | +$850.29 | 9/1 |
| J | Gold Value Area raw | 82 | 13.7 | 0.64 | 79.27% | 2.11 | +$599.52 | 18/2 |
| J | News Pulse XAG | 16 | 2.7 | 0.12 | 43.75% | 4.19 | +$1,444.89 | 2/4 |
| J | Nasdaq Overnight | 56 | 9.3 | 0.44 | 62.50% | 1.17 | +$126.31 | 10/3 |
| J | ORB Volume Profile | 35 | 5.8 | 0.27 | 65.71% | 1.36 | +$203.74 | 6/3 |
| J | ORB Volume Profile 0.50R (added copy) | 26 | 4.3 | 0.20 | 73.08% | 1.32 | +$119.24 | 6/1 |
| J | EMA3 Safe | 4 | 0.7 | 0.03 | 75.00% | 2.52 | +$72.95 | 3/1 |
| J | EMA3 Safe ATR trail (added copy) | 8 | 1.3 | 0.06 | 62.50% | 0.97 | −$5.67 | 3/2 |
| J | News Pulse XAU | 10 | 1.7 | 0.08 | 90.00% | 48.36 | +$850.29 | 9/1 |
| K | Gold Value Area raw | 85 | 14.2 | 0.66 | 78.82% | 1.88 | +$541.01 | 18/2 |
| K | News Pulse XAG | 16 | 2.7 | 0.12 | 43.75% | 4.19 | +$1,444.89 | 2/4 |
| K | Nasdaq Overnight | 57 | 9.5 | 0.45 | 61.40% | 1.16 | +$116.68 | 10/3 |
| K | ORB Volume Profile | 35 | 5.8 | 0.27 | 65.71% | 1.36 | +$203.74 | 6/3 |
| K | EMA3 Safe ATR trail | 8 | 1.3 | 0.06 | 62.50% | 0.97 | −$5.67 | 3/2 |
| K | News Pulse XAU | 10 | 1.7 | 0.08 | 90.00% | 48.36 | +$850.29 | 9/1 |
| L | Gold Value Area raw | 85 | 14.2 | 0.66 | 78.82% | 1.88 | +$541.01 | 18/2 |
| L | News Pulse XAG | 16 | 2.7 | 0.12 | 43.75% | 4.19 | +$1,444.89 | 2/4 |
| L | Nasdaq Overnight | 57 | 9.5 | 0.45 | 61.40% | 1.16 | +$116.68 | 10/3 |
| L | ORB Volume Profile 0.50R | 35 | 5.8 | 0.27 | 74.29% | 1.50 | +$217.40 | 9/2 |
| L | EMA3 Safe | 4 | 0.7 | 0.03 | 75.00% | 2.52 | +$72.95 | 3/1 |
| L | News Pulse XAU | 10 | 1.7 | 0.08 | 90.00% | 48.36 | +$850.29 | 9/1 |

Per-EA figures above reflect admitted trades after shared portfolio gates. Individual contributions are not causal estimates because changing exits alters risk availability and which later trades can be accepted.

## Historical monthly cash — stressed costs

| ID | Month | Closed trades | Net USD |
|---|---|---:|---:|
| A | 2026-03 | 33 | +$150.41 |
| A | 2026-04 | 26 | +$203.90 |
| A | 2026-05 | 31 | +$344.59 |
| A | 2026-06 | 37 | +$728.30 |
| A | 2026-07 | 46 | +$1,545.01 |
| A | 2026-08 | 34 | +$257.37 |
| I | 2026-03 | 33 | +$225.99 |
| I | 2026-04 | 28 | +$144.95 |
| I | 2026-05 | 32 | +$146.10 |
| I | 2026-06 | 38 | +$728.35 |
| I | 2026-07 | 46 | +$1,596.68 |
| I | 2026-08 | 34 | +$322.55 |
| J | 2026-03 | 38 | +$213.99 |
| J | 2026-04 | 30 | +$264.54 |
| J | 2026-05 | 38 | +$323.18 |
| J | 2026-06 | 42 | +$805.78 |
| J | 2026-07 | 51 | +$1,500.99 |
| J | 2026-08 | 38 | +$302.80 |
| K | 2026-03 | 33 | +$150.41 |
| K | 2026-04 | 28 | +$120.75 |
| K | 2026-05 | 32 | +$291.37 |
| K | 2026-06 | 38 | +$740.81 |
| K | 2026-07 | 46 | +$1,590.26 |
| K | 2026-08 | 34 | +$257.37 |
| L | 2026-03 | 33 | +$225.99 |
| L | 2026-04 | 26 | +$228.10 |
| L | 2026-05 | 31 | +$199.32 |
| L | 2026-06 | 37 | +$715.84 |
| L | 2026-07 | 46 | +$1,551.44 |
| L | 2026-08 | 34 | +$322.55 |

## Controls and limitations

- Same $71.43 maximum ordinary risk and $10 per news side; strict 0.01-lot rounding down, minimum-lot overshoots skipped. Both news sides remain available, subject to shared gates.
- Internal $300 daily admission budget, $225 aggregate initial risk, $150 correlated-metals/per-symbol risk, projected $9,200 buffer, seven entries/day and no new ordinary entries after three closed losses. Planned limits do not cap gap losses.
- FTMO model: $10K 2-Step Swing, +10% then +5%, four entry days per phase, 5% daily and 10% static loss limits, Prague reset. Instrument margin assumptions remain 1:15 metals/Nasdaq and an 80% margin ceiling, not a fresh FTMO server verification.
- Reference and stress are unchanged from the preceding study: native fills/commission floors; stress applies 10% adverse gross-P&L changes, extra adverse price costs, doubled negative swaps and carry reserves. Native spread is included, but this is not a measured FTMO slippage calibration.
- Same timing assumptions: two business days between phases, five until funded activation, first reward at least 14 calendar days after the first funded trade while flat and at least $25 profitable, four business days until payment, 80% share.
- For J, the extra versions are separate strategy identities, allowing independent concurrent positions. Original instances have priority when simultaneous signals compete for capacity. Shared metal and account caps still apply; adding copies is not independent diversification.
- Only 26 source weeks; previously fitted news presets and known-period exit experiments. Repeated joint-week resampling does not remove selection bias or establish future success probabilities.
- Native strategy ledgers are replayed independently and resized/gated on one modeled account. Skipped entries can change later signal availability. This is not a fully integrated native FTMO portfolio test.
- DD is a stop-reserve approximation, not actual combined floating equity. Breach counts stop at first reward request or day 180, not lifetime funded-account survival. Unfinished challenges are not treated as blown accounts.
- Swing news permission does not override forbidden gap-trading practices. The exact pre-news straddle implementation still needs FTMO clarification before deployment. Disqualification risk is not modeled.

## Evidence

FROZEN.json records all five configurations and source evidence hashes before results. RESULTS.json contains chronological trade ledgers, daily entry counts, milestone distributions and all 10,000 compact path records. CHECKS.json records validation and exact control reproduction. Original reports and production source files remain unchanged.

- [FTMO comparison](https://ftmo.com/en/comparison-table/)
- [FTMO forbidden practices](https://ftmo.com/en/forbidden-trading-practices/)
