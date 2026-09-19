# XAU News Pulse alone: $100 per order / $200 per event

Research only. $10,000 initial account; fixed 0.25 lot on each pending side, with a $4 initial gold stop and 100 oz/lot assumption. No compounding, adaptive taper or funded-stage size reduction. Both directions remain armed. Fees, slippage and gaps are ADDITIONAL to the $100 initial-stop risk, not included within it.

## Scope and limitations

- Same saved Exness v2.16 XAU deal evidence as the preceding comparisons. FTMO tick probe returned no data again. No fresh native FTMO tester run, no live orders, no BAT or production changes.
- Both source and stressed results use historical recorded fills, not newly simulated entry paths. Source fill prices contain the broker spread; commission and swap scale with lots. Source history reports 13% real ticks and 1 ms tester delay: historical news fills are especially uncertain.
- Source: unchanged recorded gross P/L, commission and swap. Stress: gross winners x0.65, losers x1.25, minus 0.15R additional execution cost, commission at least $7/lot round trip. Severe: winners x0.40, losers x2, minus 0.50R, same commission floor. These are hypothetical sensitivities, not measured FTMO slippage.
- No change to entry/exit geometry: T-15, live Ask/Bid +/− $4 offsets, $4 initial SL, no TP/trailing, cleanup T+60. All scheduled eligible CPI/NFP/FOMC releases can trade, including two releases on the same day. No old $100 metals cap, $150 portfolio cap, $200 daily safeguard or 60% margin cap is silently retained.
- Performance tables are fixed-size paper replays with no challenge loss halt, phase reset or margin rejection. They answer the trading idea, NOT whether a prop account survives the full period. Drawdown uses closed balance, not tick equity.
- Challenge replay has separate 10%/5% phases, four Prague-calendar entry days each, equity-rule proxies checked only at recorded cash endpoints, 30-day inactivity termination scenario, and 2/5 business-day transition assumptions. No retries. Funded size remains 0.25 lot as requested. First modeled reward requires $225 profit after costs, leaves $100, pays 80% remainder after >=14 days from first funded entry and 4 business days processing.
- Overlapping weekly-start windows and 1,000 whole-window resamples are descriptive historical frequencies, not independent observations or reliable future pass probabilities. Each horizon has a different eligible starting-date cohort: the 180/365-day percentages must not be read as a cumulative probability curve. Longer horizons exclude more of the newest, strongest starting dates. Numerical completion does not model KYC or discretionary acceptance.

## Fixed-risk performance

| Period | Costs | Trades | Win rate | PF | Net USD | Ending balance | Return | Closed-balance DD | Worst closed day |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 6 months | source | 20 | 55.00% | 5.70 | $+5,734.18 | $15,734.18 | +57.34% | 4.78% | $317.67 |
| 6 months | stress | 20 | 55.00% | 2.62 | $+2,685.82 | $12,685.82 | +26.86% | 9.38% | $412.12 |
| 6 months | severe | 20 | 50.00% | 0.77 | $-661.75 | $9,338.25 | -6.62% | 20.30% | $706.41 |
| 1 year | source | 37 | 59.46% | 6.40 | $+9,146.63 | $19,146.63 | +91.47% | 3.63% | $317.67 |
| 1 year | stress | 37 | 59.46% | 2.86 | $+4,354.09 | $14,354.09 | +43.54% | 8.09% | $412.12 |
| 1 year | severe | 37 | 48.65% | 0.78 | $-914.64 | $9,085.36 | -9.15% | 21.75% | $706.41 |
| 3 years | source | 105 | 62.86% | 5.08 | $+13,130.51 | $23,130.51 | +131.31% | 2.83% | $317.67 |
| 3 years | stress | 105 | 56.19% | 2.06 | $+4,970.00 | $14,970.00 | +49.70% | 7.69% | $412.12 |
| 3 years | severe | 105 | 33.33% | 0.44 | $-5,190.59 | $4,809.41 | -51.91% | 63.76% | $706.41 |
| ~5 years | source | 155 | 67.10% | 5.10 | $+16,014.53 | $26,014.53 | +160.15% | 2.44% | $317.67 |
| ~5 years | stress | 155 | 55.48% | 1.97 | $+5,647.70 | $15,647.70 | +56.48% | 7.30% | $412.12 |
| ~5 years | severe | 155 | 29.68% | 0.37 | $-7,674.74 | $2,325.26 | -76.75% | 88.60% | $706.41 |

All periods end 31 August 2026 exclusive. Starts: 1 March 2026, 1 September 2025, 1 September 2023, and 7 September 2021. The last interval is approximately five years, matching the preceding portfolio comparison.

## One-attempt challenge outcomes

| Days | Cost scenario | Margin scenario | Windows | Phase 1 by 30d | Funded by 30d | Funded by horizon | >=$100 payout by horizon | Recorded-close breach | Inactivity stop | Median closed trades |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 60 | source | paper | 251 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 5.2% | 5 |
| 60 | stress | paper | 251 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 5.2% | 5 |
| 60 | severe | paper | 251 | 0.0% | 0.0% | 0.0% | 0.0% | 6.8% | 5.2% | 5 |
| 180 | source | paper | 234 | 0.0% | 0.0% | 21.4% | 9.0% | 0.0% | 20.5% | 16 |
| 180 | stress | paper | 234 | 0.0% | 0.0% | 2.1% | 0.4% | 0.0% | 20.5% | 16 |
| 180 | severe | paper | 234 | 0.0% | 0.0% | 0.0% | 0.0% | 49.1% | 20.5% | 13 |
| 365 | source | paper | 207 | 0.0% | 0.0% | 42.0% | 32.9% | 0.0% | 34.3% | 23 |
| 365 | stress | paper | 207 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 34.3% | 32 |
| 365 | severe | paper | 207 | 0.0% | 0.0% | 0.0% | 0.0% | 70.5% | 22.7% | 14 |
| 60 | stress | gross_reservation | 251 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 100.0% | 0 |
| 60 | stress | on_fill | 251 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 5.2% | 5 |

The paper rows ignore broker margin eligibility. gross_reservation is OUR conservative policy requiring full funding of both sides before placement; its zero trades do NOT prove MT5 would reject all pending orders. on_fill instead tests gross margin at each cached fill, with exits processed before entries at equal second timestamps and no continuous floating-equity check. Actual server pending-order margin rates remain unverified. Endpoint breach rates are LOWER-INFORMATION proxies, not certified equity-rule failure rates.

## Margin and deadline checks

At assumed gold $4,348/oz, 100 oz/lot and 1:15: one side needs $7,246.67; both gross need $14,493.33. Full simultaneous gross exposure exceeds $10K. Even one side exceeds the previous 60% usage policy. FTMO's 22 August 2024 update states that OPEN hedged positions use the sum of both margins. Pending-stop placement/activation requirements still need verification on the actual Swing product.
There are 19 saved events with both directions filled: 0 strictly overlap in recorded open/close times, and 1 has a same-second handoff whose tick ordering is unknown. Both pending orders staying armed does not mean both positions remain open simultaneously. Therefore neither guaranteed rejection nor guaranteed execution is claimed.
The sampled calendar has at most 4 distinct eligible news days in a 30-day window and seven in a tested 60-day window. Each phase requires four separate entry dates. With OUR modeled two-business-day handover, these require eight distinct calendar dates across the two phases; this is not a separate FTMO eight-day rule. The assumed handover and sparse calendar create a structural 60-day completion bottleneck, independent of profit sizing.

## Calendar-year paper results

| Year | Costs | Trades | Net USD | Win rate | PF | Closed-balance DD |
|---|---|---:|---:|---:|---:|---:|
| 2021 | source | 7 | $+204.89 | 85.7% | 5.50 | 0.46% |
| 2021 | stress | 7 | $-4.28 | 42.9% | 0.96 | 0.86% |
| 2021 | severe | 7 | $-347.06 | 0.0% | 0.00 | 3.47% |
| 2022 | source | 22 | $+2,160.10 | 90.9% | 31.84 | 0.34% |
| 2022 | stress | 22 | $+1,014.87 | 63.6% | 7.12 | 0.75% |
| 2022 | severe | 22 | $-370.03 | 31.8% | 0.50 | 5.28% |
| 2023 | source | 33 | $+838.29 | 57.6% | 1.97 | 1.53% |
| 2023 | stress | 33 | $-486.77 | 45.5% | 0.63 | 6.59% |
| 2023 | severe | 33 | $-2,710.10 | 21.2% | 0.02 | 27.22% |
| 2024 | source | 36 | $+2,796.90 | 66.7% | 4.36 | 2.08% |
| 2024 | stress | 36 | $+757.87 | 55.6% | 1.60 | 3.89% |
| 2024 | severe | 36 | $-2,029.34 | 30.6% | 0.23 | 20.46% |
| 2025 | source | 32 | $+2,212.27 | 62.5% | 3.94 | 1.56% |
| 2025 | stress | 32 | $+489.60 | 59.4% | 1.43 | 2.76% |
| 2025 | severe | 32 | $-1,929.55 | 21.9% | 0.19 | 19.61% |
| 2026 | source | 25 | $+7,802.08 | 60.0% | 6.80 | 4.01% |
| 2026 | stress | 25 | $+3,876.41 | 60.0% | 3.12 | 8.42% |
| 2026 | severe | 25 | $-288.67 | 56.0% | 0.91 | 19.58% |

2021 and 2026 are partial years. Each yearly row starts from a fresh $10K for its drawdown calculation.

[FTMO gold Swing leverage](https://ftmo.com/en/blog/trading-updates/trading-update-2-feb-2026/) | [Hedged margin](https://ftmo.com/en/blog/trading-updates/trading-update-22-aug-2024/) | [Pending-order activation](https://www.metatrader5.com/en/terminal/help/trading/general_concept) | [2-Step objectives](https://ftmo.com/en/trading-objectives/) | [Swing rules](https://ftmo.com/en/faq/ftmo-swing-account-type/)
