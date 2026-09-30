# Gold Overnight Value Area: loss-escalation comparison

Research date: 20 September 2026. No live settings, installers, website defaults or production EA sources changed.

## What was tested

Scope: **raw Gold Overnight Value Area only**, based on the current page and pending scope clarification. This is not the combined FTMO portfolio. Each window starts independently at **$10,000**, with **$50 fixed-dollar base stop risk**. It is not the website's existing 1%-of-equity sizing.

Main interpretation: after each consecutive net loss, multiply the next requested risk by 1.5: $50, $75, $112.50, $168.75, $253.125, $379.6875. After any net win, reset to $50. Net breakeven leaves the current state unchanged. A win need not recover earlier losses before the reset.

Because "1.5x the original risk" could also mean a fixed $75 after every loss until a win, that alternative was tested too. No cap, daily stop, additional signal filter or parameter optimization was added.

## Primary results: recorded broker lot constraints

The recorded 0.01-lot minimum and step are applied, rounding up as in the existing approved EA. Commissions and swaps are included proportionally from the original native trades. The drawdowns below are **closed-balance drawdowns**, not observed floating-equity drawdowns.

| Window | Trades | Win rate | Flat $50 net | 1.5x net | Flat / 1.5x PF | Flat / 1.5x closed DD |
|---|---:|---:|---:|---:|---:|---:|
| 6 months | 100 | 71.00% | +$505.77 (+5.06%) | +$558.44 (+5.58%) | 1.51 / 1.48 | 1.68% / 2.10% |
| 1 year | 200 | 74.00% | +$1,119.72 (+11.20%) | +$1,348.28 (+13.48%) | 1.53 / 1.56 | 1.92% / 1.96% |
| 3 years | 601 | 69.22% | +$932.15 (+9.32%) | +$1,512.30 (+15.12%) | 1.13 / 1.18 | 5.76% / 5.63% |
| 5 years | 1,027 | 68.35% | +$518.27 (+5.18%) | +$1,651.62 (+16.52%) | 1.04 / 1.11 | 15.80% / 12.91% |

The signal sequence is unchanged: win rates and trade counts do not improve. Only how much money is assigned to each outcome changes. Historical closed drawdown improves on the longer windows but worsens on the shorter windows. This is not evidence that increasing risk after losses generally reduces risk.

All windows end 19 September 2026 exclusive (through 18 September). Independent starts and reported native history quality:

| Window | Start | Native real-tick share |
|---|---|---:|
| 6 months | 19 March 2026 | 100% |
| 1 year | 19 September 2025 | 71% |
| 3 years | 19 September 2023 | 23% |
| 5 years | 19 September 2021 | 14% |

Older periods rely heavily on generated ticks, not full real-tick coverage. Existing evidence also has a missing June 2025 session and some delayed exits, including weekend holds. They were preserved, not silently repaired.

## Risk increases and minimum-lot limitation

- Longest historical losing sequence: 3 in 6m/1y; 5 in 3y/5y.
- Highest next requested risk: $168.75 in 6m/1y; $379.69 in 3y/5y, **7.59 times** the $50 base.
- Highest actual planned initial-stop risk after lot rounding: $383.80 in the five-year escalation replay. This excludes fees and possible gap losses.
- Even the flat-$50 replay sometimes needed **$280.63** of initial-stop risk because 0.01 lot exceeded the target on a very wide stop. It exceeded the target due to the minimum lot on 84 of 1,027 five-year trades (70 with escalation).
- Consequently, this is a **$50 target**, not a hard $50 maximum. Exact fractional-lot comparisons are saved separately, but fractional sizes below the broker minimum are not executable there.
- A longer future streak can exceed the observed maximum: after seven consecutive losses, next requested risk is $854.30; after ten it is $2,883.25. This uncapped rule does not protect account capital.

Actual example in the five-year replay: trades 435–439 lost $55.89, $11.83, $114.06, $177.11 and $66.06, totaling **$424.95**. Trade 440 then requested $379.69 of risk but won only **$74.96**. It reset to $50 while the six-trade sequence remained **-$349.99**. High win rate and increasing size do not guarantee recovery, particularly with small reward-to-risk winners.

## Additional-cost stress

Stress adds a total $0.25-per-ounce execution penalty per round trip and increases negative commission by 50%. This is a transparent sensitivity assumption, not a forecast or measured broker latency model. Risk state updates use the stressed net result, so the stress path can differ from the reference path.

| Window | Flat net | 1.5x net | Flat / 1.5x closed DD |
|---|---:|---:|---:|
| 6 months | +$456.92 | +$505.86 | 1.72% / 2.16% |
| 1 year | +$1,015.80 | +$1,231.53 | 2.09% / 2.02% |
| 3 years | +$309.77 | +$842.51 | 10.31% / 8.77% |
| 5 years | -$844.59 | -$102.31 | 25.24% / 23.70% |

The five-year escalation version loses its positive expectancy under this stress: PF 0.9935. Neither rule exhausts closed balance on these particular replays, but that **does not establish no liquidation, no intratrade breach or FTMO compliance**. Historical leverage/margin schedules and synchronized floating equity were not replayed.

## Alternative: always $75 after a loss

If the intended rule was $50, then $75 repeatedly until a win (rather than continued multiplication):

| Window | Net | PF | Closed DD |
|---|---:|---:|---:|
| 6 months | +$476.07 | 1.42 | 2.24% |
| 1 year | +$1,270.43 | 1.54 | 2.08% |
| 3 years | +$1,184.74 | 1.15 | 6.07% |
| 5 years | +$1,077.15 | 1.08 | 14.80% |

## Method and verification

This is an **offline chronological position-sizing replay of saved native MT5 trades**, not a fresh native MT5 test of a modified EA. Original entries, exits, spreads, gap effects and the 150 ms native test-delay assumptions are inherited from recorded fills. Larger size is assumed not to change those fills. Original cash flows are scaled by volume; broker fee rounding and size-dependent execution are approximations. Recorded swap is zero for this source; swap was not newly assumed away.

Original stop risks are used, not later trailed stop levels. One open position at a time is checked explicitly; overlapping trades would stop the replay rather than use future outcomes. Source counts and cash totals reconcile; original native report hashes are verified and all source hashes are saved. Nine deterministic regression tests cover escalation, reset, break-even handling, sizing, costs, overlap rejection and no look-ahead.

`results.json` indexes all 48 ledgers: four periods, two lot-sizing methods, two cost scenarios and three risk rules. Each ledger includes requested and actual risk, position size, cash costs, outcome and balance; each summary contains monthly totals. No new data collection or MT5 trading was performed.

## Conclusion

The geometric rule improved recorded net profit in all four windows, but did not improve trade quality. The weak five-year stress result, broker minimum-lot oversizing and uncapped streak exposure make this **research-only**, not a recommendation to activate it uncapped or a claim of better FTMO passing probability. A capped progression, hard account-level loss controls and a genuine execution/equity replay would be separate tests requiring a defined profile.

FTMO also requires consistent risk management and identifies substantially larger position sizing/repeatedly increased risk as potentially problematic; its public rules do not establish this exact progression as approved. See [FTMO forbidden trading practices and risk-management rules](https://ftmo.com/en/forbidden-trading-practices/).
