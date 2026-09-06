# Step 2 — LTA Hybrid Sub-Condition Report

## Goal

Keep the current LTA Volume Profile signal engine intact, add the completed-profile POC / heavy-zone first-retest idea as an optional confirmation, optimize it without look-ahead, and decide whether it should replace the active BAT configuration.

## Implementation

The production `LTA_Concepts_EA` now calculates the contiguous heavy-volume zone around the completed profile POC and can require a qualified departure followed by the first retest. The new logic is an entry gate after the existing LTA direction, level-touch and EM1/EM4 confirmation logic; it is not a replacement strategy.

New inputs:

| Input | Active BAT value | Research best |
| --- | ---: | ---: |
| `InpUsePOCFirstRetestConfirmation` | false | true |
| `InpPOCHeavyZoneVolumeFraction` | 0.50 | 0.50 |
| `InpPOCMinimumDepartureATR` | 0.50 | 0.50 |
| `InpPOCRetestSignalBars` | 3 | 3 |

## Development selection — 2024-08-29 to 2025-08-28

Nineteen native MT5 Every Tick tests were run: the unchanged baseline plus eighteen combinations covering heavy-zone fraction 0.50/0.65/0.80, departure 0.50/1.00/1.50 ATR, and retest windows of 3/8 bars.

| Configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | -3.85% | 0.98 | — | 20.54% | 241 | — | — |
| H0.65 / D0.50 / 3 bars | +7.29% | 1.38 | 32.14% | 8.64% | 28 | 5.52 | 0.82 |
| H0.50 / D0.50 / 3 bars | +5.84% | 1.31 | 32.14% | 7.61% | 28 | 3.65 | 0.75 |
| H0.50 / D1.00 / 3 bars | +3.04% | 1.16 | — | 5.68% | 27 | — | — |

## Locked year — 2025-08-29 to 2026-08-28

| Configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | +107.28% | 1.44 | 33.33% | 15.25% | 249 | 5.12 | 4.83 |
| H0.50 / D1.00 / 3 bars | +7.64% | 1.43 | 33.33% | 9.16% | 27 | 5.64 | 0.78 |
| H0.50 / D0.50 / 3 bars | +7.10% | 1.55 | 35.00% | 6.39% | 20 | 7.19 | 1.04 |
| H0.65 / D1.00 / 3 bars | +5.84% | 1.36 | 32.00% | 5.97% | 25 | — | — |
| H0.80 / D1.50 / 8 bars | +3.20% | 1.12 | 28.95% | 8.09% | 38 | — | — |
| H0.65 / D0.50 / 3 bars | +0.46% | 1.03 | 26.32% | 7.50% | 19 | — | — |

## Full two-year comparison

| Configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Current LTA baseline | +96.16% | 1.22 | 29.51% | 20.54% | 488 | 2.59 | 3.93 |
| POC first-retest H0.50 / D0.50 / 3 bars | +14.55% | 1.45 | 33.33% | 7.61% | 48 | 5.83 | 1.86 |

## Decision

Keep the current LTA behavior in the active, recommended, dynamic and Safe BAT flows. The hybrid gate improves PF, win rate, Sharpe and drawdown, but removes about 90% of trades and most of the realized return. It is therefore saved as an optional selective/safe research mode, with the active BAT explicitly setting the gate to `false`.

This is a historical MT5 result, not a guarantee of future profitability.

