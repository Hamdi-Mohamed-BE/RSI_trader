# Noise Band raw study: QuantLab's assets (Nasdaq 100, S&P 500, DAX 40), 2026-11-24

**Rules:** RULES.md, frozen 2026-11-11, plus Addendum 1 (assets and DAX clock) and Addendum 2 (flat at 15:55 NY / 17:25 Frankfurt).

**The strategy:**
- Reference price = the cash-open price (09:30 NY; 09:00 Frankfurt for the DAX).
- On every closed 30-minute candle, the EA checks whether price has moved more than k × √K × ATR14(M30) away from the open. K = the number of half-hours since the open.
- If it has, the EA trades in the direction of the move at the next candle's open: one trade a day.
- Exits: initial stop at s × ATR, a 2 × ATR trailing stop once the trade is +1R, and flat before the close.
- **WIDE** (QuantLab's pick): k 1.4, stop 2 ATR. **PAPER:** k 0.6, stop 1.5 ATR.

**Test setup:**
- Exness CFDs USTEC, US500 and DE30, native MT5 Model 4, M30, $10k, 1% of balance per trade, 150 ms.
- Period: 2019-07-16 → 2026-11-21.
- Older ticks are generated; real ticks start 2026-01-01.

**Checks:**
- Parity: v1.10 = v1.00 trade for trade on USTEC (77 / 77).
- QuantLab's example trade (short 2023-01-18, held ~4 h) is found on USTEC and US500: 11:30 → 15:55 NY.
- The first USTEC run held 12% of its trades overnight; the broker's 2020-24 quotes end at 16:00 NY. It was rerun with a 15:55 flat. The invalid run is kept in `native-INVALID-flat1600/`.
- Trades still held past the flat time: USTEC 9, US500 6, DE30 0 (US half-day holidays).

## Main table (all years; R = net / 1% of balance at entry)

| Case | Trades | /month | /day | Return (native) | PF | Win % | Avg R | Consistency | Sharpe | Equity DD | Win / loss streak (avg) | Max loss streak |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **USTEC WIDE** | 1,166 | 13.2 | 0.61 | **+172.3%** | **1.22** | 53.7 | +0.093 | 57% | 0.99 | 16.7% | 2.1 / 1.8 | 10 |
| **US500 WIDE** | 1,014 | 11.5 | 0.53 | **+162.5%** | **1.25** | 52.9 | +0.102 | 57% | 0.99 | 28.5% | 2.1 / 1.9 | 7 |
| DE30 WIDE | 1,075 | 12.2 | 0.56 | +14.4% | 1.02 | 49.0 | +0.020 | 57% | 0.19 | 47.4% | 1.9 / 2.0 | 9 |
| USTEC PAPER | 1,830 | 20.7 | 0.95 | +24.0% | 1.02 | 40.5 | +0.021 | 55% | 0.24 | 31.4% | 1.6 / 2.4 | 11 |
| US500 PAPER | 1,815 | 20.6 | 0.95 | −45.5% | 0.92 | 38.1 | −0.024 | 40% | −0.24 | 70.9% | 1.6 / 2.5 | 12 |
| DE30 PAPER | 1,829 | 20.7 | 0.95 | −75.4% | 0.89 | 36.2 | −0.067 | 44% | −0.75 | 86.2% | 1.6 / 2.7 | 19 |
| US2 WIDE (USTEC + US500, 1 R each) | 2,180 | 24.7 | 1.14 | +211.7R | 1.22 | 53.3 | +0.097 | 63% | 1.12 | closed 42.7R | 2.7 / 2.3 | 13 |
| ALL3 WIDE (+ DE30) | 3,255 | 36.9 | 1.70 | +233.2R | 1.16 | 51.9 | +0.072 | 61% | 1.06 | closed 81.3R | 2.4 / 2.3 | 10 |

Notes on the columns:
- Consistency = share of profitable months.
- Sharpe = annualised daily R.
- Equity DD = MT5 relative equity drawdown.
- Trades / day = per weekday.

## Windows (data_split; OOS = last two years, previously viewed by QuantLab's choice of k, NOT untouched) and years, in R

| Case | Dev 2019-07 → 2023-11 | Val 2023-11 → 2024-11 | OOS 2024-11 → 2026-11 | Last 12 m | 2019* | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026* |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| USTEC WIDE | +44.6 | +22.3 | +41.1 | +23.5 (PF 1.40, 152 trades) | −2.9 | +2.6 | +25.5 | +20.6 | −0.9 | +33.4 | +10.1 | +19.6 |
| US500 WIDE | +33.8 | +18.6 | +51.4 | +27.6 (PF 1.49, 145 trades) | −3.3 | +5.7 | +16.4 | +23.7 | −13.2 | +27.7 | +23.4 | +23.3 |
| DE30 WIDE | +13.2 | −19.2 | +27.5 | +2.0 (PF 1.03) | +17.2 | +21.9 | −12.6 | +7.9 | −27.8 | −13.0 | +19.8 | +8.2 |
| US2 WIDE | +78.3 (PF 1.13) | +40.8 (PF 1.33) | +92.6 (PF 1.40) | +51.0 (PF 1.45) | −6.1 | +8.4 | +41.8 | +44.4 | −14.2 | +61.0 | +33.5 | +42.9 |

\* partial year

## Robustness (pipeline stages 4/6)

| Case | Random direction (5 seeds, R) | Random-entry control (200 copies) | MC resample / randomize red | Clumped losses | 2× cost | Best-day dependence |
|---|---|---|---|---|---|---|
| USTEC WIDE | +10.9 / −44.2 / −56.6 / −92.8 / +11.0 vs +107.9 | p 0.02 PASS | 0.5% / 0.0% PASS | no (15.9%) | +95.9R PASS (breakeven 10×) | PASS (without 5 best days +85.7R) |
| US500 WIDE | −26.9 … −100.0 vs +103.8 | p 0.02 PASS | 0.2% / 0.0% PASS | **YES (95.3%)** | +85.4R PASS (6.6×) | PASS (+79.8R) |
| DE30 WIDE | −30.7 … −106.1 vs +21.5 | **p 0.20 FAIL** | **29.8% / 98.8% FAIL** | YES | +9.0R (2.7×) | **top-5-days sign flip** |
| PAPER (all three) | – | – | 26-98% / 99-100% FAIL | – | US500 / DE30 FAIL | – |

## Buy and hold, same window

| Asset | Buy & hold | Max DD | Noise Band WIDE |
|---|---|---|---|
| USTEC | +19.0% (price +218%; CFD financing eats it) | 72.6% | +172.3%, DD 16.7% |
| US500 | −2.9% (price +132%) | 52.4% | +162.5%, DD 28.5% |
| DE30 | price only +98.6% (EA benchmark refuses EUR symbols) | 42.4% | +14.4%, DD 47.4% |

## QuantLab claim vs ours

| | Return | PF | Max DD | Win rate |
|---|---|---|---|---|
| QuantLab (3 indices, start and sizing not shown) | +420.0% | 1.28 | 19.5% | 48.6% |
| Ours, USTEC / US500 WIDE | +172% / +162% | 1.22 / 1.25 | 16.7% / 28.5% | 53.7 / 52.9 |

Ours is a broadly similar edge, but the claim was not reproduced on DAX.

## Verdict (raw gate: all and last 3 years positive, PF ≥ 1.15, ≥ 100 trades, beats random, MC resample ≤ 5% / randomize ≤ 10%)

- **USTEC WIDE: PASS.** The cleanest result:
  - It is positive in dev, val and OOS.
  - 2023 −0.9R and partial 2019 are its only losing years.
  - It beats every control, and the 2× cost check passes.
- **US500 WIDE: PASS with a CLUMPED-losses flag.** The real DD is worse than 95% of shuffles; 2023 −13.2R.
  - Size from the worse DD, not from the average.
- **US2 (USTEC + US500 together):** the two signals trade the same day on 836 days and move together, so this is not real diversification. The combined DD is 42.7R.
- **DE30 WIDE: FAIL.** PF 1.04, random-entry p 0.20, MC fail, negative without its 5 best days. Our DAX times (09:00 open, 17:25 flat) are an assumption; QuantLab's are not published.
- **PAPER (k 0.6): FAIL on all three.**
- **Survivors for stage 5 (optimisation, owner approval needed):** USTEC WIDE and US500 WIDE.
  - The OOS window is not untouched: QuantLab chose k 1.4 after seeing these years. Earlier ticks are generated.
  - `/bear-review` has not been run yet.

Files:
- `RESULTS.json`, `CONTROLS.json`, `BALANCE.png`, `PARITY.json`
- `native/`, and `native-INVALID-flat1600/` (invalid first run)
- `study.py`, `controls.py`
- EA v1.10: `EA/Noise Band Research EA.mq5`, research only
