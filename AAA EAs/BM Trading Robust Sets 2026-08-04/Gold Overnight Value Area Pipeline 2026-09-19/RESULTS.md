# Gold Overnight Value Area — full research pipeline

**Review only: nothing deployed. S&P 500 pipelines have not been started.**

**NO PROMOTION. None of the three native finalists passed all predeclared training/validation gates. Do not add this version to the active system on this evidence.**

## Native MT5 comparison

Independent $10,000 starts, 1% requested equity stop-risk, same Exness Zero XAUUSD contract, 150 ms simulated execution delay. Commissions and swaps are the actual values recorded in each tester Deals ledger. Native equity drawdown includes floating P/L. Ends 2026-09-19 exclusive; six months starts 2026-03-19, one year 2025-09-19, three years 2023-09-19, five years 2021-09-19.

| Period | Version | Return | Net USD | Trades | Win rate | PF | Equity DD | Commission | Swap | Real tick quality |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 6m | Raw | +9.39% | $+938.77 | 100 | 71.00% | 1.52 | 3.97% | $-18.15 | $0.00 | 100% real ticks |
| 6m | Research candidate | +10.95% | $+1,095.18 | 30 | 60.00% | 2.58 | 3.43% | $-10.93 | $0.00 | 100% real ticks |
| 1y | Raw | +22.26% | $+2,225.75 | 200 | 74.00% | 1.56 | 4.00% | $-39.99 | $0.00 | 71% real ticks |
| 1y | Research candidate | +17.71% | $+1,771.05 | 72 | 48.61% | 1.94 | 5.67% | $-30.84 | $0.00 | 71% real ticks |
| 3y | Raw | +18.37% | $+1,836.52 | 601 | 69.22% | 1.15 | 11.84% | $-225.72 | $0.00 | 23% real ticks |
| 3y | Research candidate | +47.24% | $+4,723.94 | 208 | 43.27% | 1.78 | 5.91% | $-215.73 | $0.00 | 23% real ticks |
| 5y | Raw | +9.09% | $+908.83 | 1027 | 68.35% | 1.04 | 28.90% | $-501.67 | $0.00 | 14% real ticks |
| 5y | Research candidate | +52.92% | $+5,292.35 | 381 | 43.31% | 1.44 | 9.78% | $-519.73 | $0.00 | 14% real ticks |

## Frozen candidate settings

- 96 histogram bins; 80% contiguous value area; profile NY 18:00 previous calendar day to 09:30 today.
- First completed M5 close above VAH buys, below VAL sells; market execution on the next tick. One signal attempt per NY day; invalid price geometry consumes it.
- Stop: POC plus one broker tick beyond it. Minimum initial reward/risk: 0.50R.
- TP: overnight high for buys / low for sells.
- Breakeven trigger: 0.5R (0=off); trailing distance: 0.0R (0=off, otherwise activates after 1R using completed M5 closes).
- Last entry before 15:00 NY; time exit 15:30 NY, clamped to known broker session end; retries if market closed.
- Requested risk 1% equity, rounded UP to broker lot step with 0.01-lot floor. This is not a strict 1% cap. Native 0.5% sensitivity is reported below.

## Selection, not a latest-year winner search

Tested 162 Stage-A configurations plus 33 additional management/target configurations, with the unchanged raw baseline separately. Discovery used an explicitly approximate M1/M5 bid/ask bar engine. Native MT5 checked three diverse finalists.

Training: 2021-09-19–2024-09-19. Validation: 2024-09-19–2025-09-19. Candidate selection was frozen before evaluating its latest year. The latest-year **raw** result had already been seen, so this is not a virgin holdout.

| Candidate | Train return / trades / PF / DD | Validation return / trades / PF / DD | Gate |
|---|---|---|---|
| 80% VA / 96 bins / POC stop / overnight TP / BE 0.5R | +21.37% / 249 / 1.29 / 9.78% | +8.95% / 60 / 1.53 / 4.48% | training: fewer than 300 trades |
| 70% VA / 96 bins / opposite VA stop / 1.5R TP | +34.64% / 703 / 1.12 / 23.82% | +20.74% / 213 / 1.30 / 9.07% | training: equity DD over 20% |
| 70% VA / 64 bins / POC stop / overnight TP / BE 0.5R | +16.90% / 331 / 1.16 / 10.18% | -1.67% / 106 / 0.95 / 12.29% | validation: net loss; validation: PF below 1.10 |

Gates: at least 300 training and 60 validation trades; both periods net-positive, PF ≥1.10 and equity DD ≤20%. The gates were not relaxed after seeing results. The displayed research candidate is the best eligible candidate, or the least-bad training/validation score if none qualifies. These thresholds are research safeguards, not statistical proof that 300 trades are sufficient or 249 are worthless.

The fixed-R target finalist can accept first signals that the overnight-extreme TP would reject because its target is already behind the entry price. Its changed trade count therefore reflects changed entry eligibility as well as exit behavior; it is not a pure exit-only comparison. The selected configuration is specified explicitly above.

## Chronological walk-forward diagnostic — bar approximation

For each origin, select from the same 162 Stage-A family using only the preceding two years, then evaluate the following six months. Stage B is excluded because its parent choice used later training data. Each fold starts with $10,000; these returns must not be added as one live portfolio.

| Test start | Test end (exclusive) | Return | Trades | WR | PF | Approx. DD |
|---|---|---:|---:|---:|---:|---:|
| 2023.09.19 | 2024.03.19 | -7.01% | 54 | 40.74% | 0.75 | 10.34% |
| 2024.03.19 | 2024.09.19 | +4.11% | 40 | 52.50% | 1.20 | 6.59% |
| 2024.09.19 | 2025.03.19 | -5.38% | 44 | 45.45% | 0.77 | 8.92% |
| 2025.03.19 | 2025.09.19 | +12.07% | 60 | 55.00% | 1.44 | 7.21% |

## Native execution / sizing stress

| Scenario | Period | Return | Trades | WR | PF | Equity DD | Max actual initial risk |
|---|---|---:|---:|---:|---:|---:|---:|
| 500 ms, 1% requested | 1y | +17.35% | 72 | 48.61% | 1.92 | 5.71% | 1.58% |
| 1000 ms, 1% requested | 1y | +19.37% | 72 | 50.00% | 2.07 | 5.78% | 1.58% |
| 150 ms, 0.5% requested | 5y | +25.18% | 381 | 43.31% | 1.43 | 5.21% | 1.12% |

These delay runs use MT5 fixed delay and its recorded spreads. They do not model every live rejection, queue position, spread burst, disconnection or historical liquidity change.

## Extra-cost overlay on fixed five-year native ledgers

Add the stated dollar price cost per ounce per round trip, plus 50% extra commission. Existing spreads and recorded fees are already present. **This is a fixed-trade cash overlay, not a re-execution or a re-compounded native test. DD below is closed-balance only.**

| Version | Added $/oz | Return | PF | Closed-balance DD |
|---|---:|---:|---:|---:|
| raw | 0.10 | -2.50% | 0.99 | 36.33% |
| raw | 0.25 | -16.11% | 0.93 | 45.83% |
| raw | 0.50 | -38.81% | 0.84 | 62.82% |
| selected | 0.10 | +40.89% | 1.32 | 11.34% |
| selected | 0.25 | +26.74% | 1.20 | 14.84% |
| selected | 0.50 | +3.16% | 1.02 | 30.38% |

## Sizing and operational audit (five years)

| Version | Median / max initial risk | Minimum-lot trades | Exits >1 minute late | Held into another NY day | Average initial RR | Gross breakeven but net loss |
|---|---|---:|---:|---:|---:|---:|
| raw | 1.065% / 2.815% | 15 | 78 | 5 | 0.418R | 0 |
| selected | 1.024% / 1.917% | 0 | 4 | 0 | 1.137R | 6 |

| Version | Average win / loss | Win / loss streak maximum | Long trades / net USD | Short trades / net USD | Net profit without best five winners |
|---|---|---|---|---|---:|
| raw | $33.31 / $-69.16 | 12 / 5 | 499 / $+167.74 | 528 / $+741.09 | $-30.65 |
| selected | $104.41 / $-55.25 | 7 / 7 | 155 / $+1,438.89 | 226 / $+3,853.46 | $+3,232.29 |

Gross breakeven trades still pay costs and are correctly counted as net losses. Moving the time exit earlier is not a guarantee of same-day execution on every historical holiday.

## Monte Carlo sensitivity, not a promise

5,000 paths, each 52 randomly sampled historical week blocks (including empty weeks), seed 9192026. Uses realized percentage returns and ignores intratrade floating DD and longer regime dependence. It does not estimate FTMO passing probabilities and does not remove parameter-selection bias.

| Ledger | Negative sampled year | Return p05 / median / p95 | Closed-balance DD p95 |
|---|---:|---|---:|
| raw | 42.2% | -11.04% / +1.49% / +15.98% | 15.07% |
| selected | 11.8% | -2.78% / +8.35% / +22.45% | 9.11% |

Missed-winner tests remove 5% or 10% of winners at random from the fixed ledger, 1,000 draws. No replacement trades or compounding changes are invented.

| Ledger | Missing winners | Five-year return p05 / median / p95 |
|---|---:|---|
| raw | 5% | -5.77% / -2.77% / -0.20% |
| raw | 10% | -18.56% / -14.44% / -10.96% |
| selected | 5% | +39.24% / +44.03% / +46.45% |
| selected | 10% | +29.62% / +35.48% / +39.22% |

## Local parameter stability

Neighbor settings are sensitivity checks, not replacements selected after looking at the latest year. Full bar-based training/validation neighbors are in neighbor-screen.json. Two nearest geometry neighbors were checked in native MT5 on validation.

| Neighbor change | Validation return | Trades | PF | Equity DD |
|---|---:|---:|---:|---:|
| bins=64 | +11.58% | 68 | 1.61 | 5.51% |
| va=70 | -0.94% | 97 | 0.97 | 12.62% |

## Annual and monthly breakdown — five-year continuous runs

These are cash flows from each continuous five-year run, not independent restarts. First and last months/years are partial. Return is on that period’s opening balance.

| Year | Raw USD | Raw trades | Candidate USD | Candidate trades |
|---|---:|---:|---:|---:|
| 2021 | +87.55 | 56 | -333.62 | 22 |
| 2022 | +345.53 | 218 | +763.60 | 82 |
| 2023 | -1,690.05 | 207 | +450.30 | 92 |
| 2024 | +38.31 | 198 | +1,565.42 | 69 |
| 2025 | +272.48 | 200 | +811.58 | 64 |
| 2026 | +1,855.01 | 148 | +2,035.07 | 52 |

| Month | Raw USD | Raw trades | Candidate USD | Candidate trades | Candidate return |
|---|---:|---:|---:|---:|---:|
| 2021-09 | -2.50 | 6 | +57.28 | 1 | +0.57% |
| 2021-10 | -270.64 | 18 | -64.59 | 4 | -0.64% |
| 2021-11 | +285.75 | 15 | -20.66 | 10 | -0.21% |
| 2021-12 | +74.94 | 17 | -305.65 | 7 | -3.07% |
| 2022-01 | +249.39 | 19 | +189.08 | 8 | +1.96% |
| 2022-02 | +286.78 | 17 | +468.79 | 11 | +4.76% |
| 2022-03 | +6.99 | 15 | -128.16 | 5 | -1.24% |
| 2022-04 | +201.59 | 18 | +284.67 | 7 | +2.79% |
| 2022-05 | +312.32 | 20 | +61.56 | 6 | +0.59% |
| 2022-06 | -20.46 | 18 | -107.70 | 8 | -1.02% |
| 2022-07 | -59.45 | 18 | +146.29 | 7 | +1.40% |
| 2022-08 | -290.85 | 21 | -78.49 | 8 | -0.74% |
| 2022-09 | -129.86 | 19 | -138.74 | 6 | -1.32% |
| 2022-10 | +279.41 | 19 | +129.59 | 6 | +1.25% |
| 2022-11 | -211.65 | 18 | -106.60 | 6 | -1.02% |
| 2022-12 | -278.68 | 16 | +43.31 | 4 | +0.42% |
| 2023-01 | -138.22 | 17 | +56.19 | 8 | +0.54% |
| 2023-02 | -240.00 | 17 | +292.71 | 9 | +2.79% |
| 2023-03 | -7.17 | 20 | +293.55 | 10 | +2.72% |
| 2023-04 | -150.16 | 15 | +86.51 | 4 | +0.78% |
| 2023-05 | -78.43 | 22 | -309.51 | 11 | -2.77% |
| 2023-06 | +283.54 | 17 | +371.92 | 4 | +3.43% |
| 2023-07 | +202.85 | 15 | -145.03 | 8 | -1.29% |
| 2023-08 | -711.97 | 19 | -444.54 | 9 | -4.01% |
| 2023-09 | -564.11 | 17 | -208.21 | 8 | -1.96% |
| 2023-10 | -225.82 | 18 | +34.76 | 12 | +0.33% |
| 2023-11 | -44.50 | 18 | -36.53 | 6 | -0.35% |
| 2023-12 | -16.06 | 12 | +458.48 | 3 | +4.40% |
| 2024-01 | +25.65 | 18 | -41.94 | 8 | -0.39% |
| 2024-02 | +141.09 | 15 | -11.96 | 9 | -0.11% |
| 2024-03 | -84.86 | 16 | +203.74 | 7 | +1.88% |
| 2024-04 | -69.46 | 21 | +252.29 | 4 | +2.29% |
| 2024-05 | +49.39 | 17 | +463.27 | 7 | +4.11% |
| 2024-06 | +19.59 | 16 | -123.23 | 3 | -1.05% |
| 2024-07 | +197.49 | 19 | +597.74 | 6 | +5.14% |
| 2024-08 | -181.01 | 16 | -59.72 | 4 | -0.49% |
| 2024-09 | -119.21 | 17 | +168.52 | 9 | +1.39% |
| 2024-10 | +125.09 | 18 | +56.04 | 6 | +0.45% |
| 2024-11 | -199.69 | 10 | -16.29 | 4 | -0.13% |
| 2024-12 | +134.24 | 15 | +76.96 | 2 | +0.62% |
| 2025-01 | -274.78 | 18 | -197.63 | 3 | -1.59% |
| 2025-02 | -198.85 | 16 | -46.89 | 6 | -0.38% |
| 2025-03 | +64.49 | 20 | +2.91 | 5 | +0.02% |
| 2025-04 | -18.60 | 17 | +208.04 | 7 | +1.70% |
| 2025-05 | -3.85 | 18 | -192.16 | 3 | -1.55% |
| 2025-06 | -115.86 | 14 | +499.96 | 4 | +4.09% |
| 2025-07 | +177.25 | 18 | +8.77 | 5 | +0.07% |
| 2025-08 | +183.33 | 17 | +104.11 | 8 | +0.82% |
| 2025-09 | +332.89 | 15 | +468.92 | 5 | +3.65% |
| 2025-10 | +12.19 | 17 | +160.99 | 6 | +1.21% |
| 2025-11 | -180.06 | 14 | -283.03 | 5 | -2.10% |
| 2025-12 | +294.33 | 16 | +77.59 | 7 | +0.59% |
| 2026-01 | +366.08 | 20 | +151.28 | 9 | +1.14% |
| 2026-02 | +273.90 | 16 | +214.33 | 7 | +1.60% |
| 2026-03 | +227.41 | 18 | +82.93 | 7 | +0.61% |
| 2026-04 | +236.52 | 18 | +239.72 | 8 | +1.75% |
| 2026-05 | +463.14 | 14 | +747.21 | 6 | +5.36% |
| 2026-06 | +310.28 | 15 | +74.21 | 8 | +0.51% |
| 2026-07 | +140.03 | 20 | +90.65 | 1 | +0.61% |
| 2026-08 | -149.33 | 16 | +335.44 | 5 | +2.26% |
| 2026-09 | -13.02 | 11 | +99.30 | 1 | +0.65% |

## Verification and limits

- 21 native reports independently reconciled to their trade/fee ledgers; 3869 distinct day/parameter profiles checked against M1 history. All completed M5 signal, initial SL/TP, cash-total, source-hash and profile checks passed.
- Ten unit tests cover DST, Monday boundaries, profile geometry, tester-only/account guard, raw ledger parity, minimum lot rounding, conservative intraminute stop-first ordering, invalid-signal consumption and short ask-side exits.
- The modified source exactly reproduces all 200 prior one-year raw trades with default parameters, including timestamps, prices, size, net costs and initial levels.
- Broker real ticks begin 2026-01-01. Older data uses generated ticks even in real-tick tester mode. Tick volume is broker activity, not centralized traded gold volume.
- Holiday/closure candidates and monthly bar counts are saved; no missing bars were synthesized by the research scripts. The MT5 tester itself generates ticks for missing real-tick history.
- A specific coverage gap remains: repeated broker M1/M5 API re-queries match the frozen cache, but on 2025-06-20 the M1 history ends at 07:17 UTC, before NY open. No trade is invented for the absent NY session. These are five-year available-history results, not a claim of complete market coverage.
- During the work an external Git operation left website catalog conflict markers. The research report parser was mechanically isolated from website imports and checked against all then-completed native ledgers with identical outputs; the website conflicts were not modified.
- Fee snapshots, 1:2000 leverage and native account conditions are Exness demo assumptions, not FTMO Swing conditions. This is not an FTMO pass simulation.
- No second broker or forward demo validation was manufactured. Actual live execution remains unverified.

**Stop here for user review. Do not deploy Gold or start the five S&P 500 optimization pipelines automatically.**
