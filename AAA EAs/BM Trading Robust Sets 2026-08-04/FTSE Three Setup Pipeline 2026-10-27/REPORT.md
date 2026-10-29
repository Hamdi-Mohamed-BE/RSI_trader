# FTSE 100 three-setup bot — full pipeline (EXPLORATORY OVERRIDE) — REJECTED_AT_VALIDATION

**Owner request (2026-10-27):** "optimize all three together and run through unseen data and Monte Carlo simulation".

- **Rules and changes:** `PLAN.md` was frozen before any search result. Addenda 1–3 cover the diagnostic carry, the
  parity method and a transfer bug fix.
- **Engine:** a case-table EA swept by the native MT5 optimizer. Exact parity with the raw ALL 5y Model-4 ledger:
  1,273 / 1,273 entries match the raw EA journal; exits, volumes and money match (net $−2,076.65 on both).
- **Account:** UK100 H1 chart; each setup uses its own M30 / H1 / H4. $10,000, 0.75% risk, 150 ms.
- **Tests:** 915 unique configurations screened on development (Model 1), 989 native records in total.

## Data
| Window | Dates | Status |
|---|---|---|
| Development | 2019-08-01 → 2023-10-27 | all searching |
| Validation | 2023-10-27 → 2024-10-27 | viewed in the raw study |
| OOS | 2024-10-27 → 2026-10-27 | viewed in the raw study: retrospective, not pristine |
| Transfer (genuinely unseen) | DE30, US500, 2021-10-27 → 2026-10-27 | never run with these rules |

## What the search found (development, Model 1)
| Setup | Raw dev result | Best after the search | Main changes |
|---|---|---|---|
| S1 panic drop | losing (PF ≈ 0.9) | PF 1.43, +17.2%, 87 trades | Bollinger 2.5σ, RSI < 30, 5R target, break-even at 1R, no time exit, London 07–21, only against the D1 trend |
| S2 Monday dip | PF ≈ 1.4 | PF 1.44, +5.7%, 69 trades | H4, SMA 10 h, RSI < 35, Monday–Tuesday, 1R target, 24 h, ATR trail |
| S3 trend pullback | losing (PF 0.87) | PF 1.33, +24.4%, 112 trades | **shorts only**, 2 ATR from SMA 60 h, RSI 35 / 65, 4R target, ADX ≥ 20 |

- **Combination:** all three together ranked first. Development: +54.6%, PF 1.38, 268 trades (5.3 / month, 0.24 / day),
  equity DD 15.5%.
- **Plateau:** passed. 20 / 20 neighbours were profitable, median PF 1.32.
- **Duplicate finalists:** the three finalists produce identical ledgers (S2's carried versions behave the same), so
  they are not three independent edges.

## Validation and OOS (Model 4) — the edge does not survive
| Window | Trades | / month | / day | Return | PF | Win % | Equity DD | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Development (M4) | 268 | 5.3 | 0.24 | +54.5% | 1.37 | 34% | 15.7% | — |
| **Validation** | 52 | 4.3 | 0.20 | **−6.3%** | **0.77** | — | 9.4% | **REJECTED** |
| OOS (diagnostic) | 77 | 3.2 | 0.15 | −1.0% | 0.97 | 35% | 13.7% | FAIL (net, PF, best day) |

- **Validation by setup:** S1 +$350, S2 −$266, S3 −$712.
- **OOS by setup:** S1 −$542, S2 +$591, S3 −$150.
- **Raw S2 does better recently:** the unoptimised raw S2 made +1.3% / +5.6% / +14.0% in 2024 / 2025 / 2026 (raw
  study). The tuned S2 did worse there.

## Monte Carlo (DIAGNOSTIC: full period 2019-08 → 2026-10, Model 4, mostly in-sample)
- **Full run:** +43.3%, PF 1.18, 397 trades (4.6 / month, 0.21 / day), equity DD 18.4%, mean +0.13R.
  - By year: 2021 +$2,616 and 2022 +$1,753 (development), then 2024 −$1,067 and 2025 −$690.
- **Day-block bootstrap** (10,000 one-year paths):
  - Median year +5.1%; 5th percentile −9.8%.
  - **Probability of a losing year 29%.**
  - Max DD median 9.8R (≈ 7%), 95th percentile 20.2R (≈ 15%), 99th percentile 25.6R (≈ 19%).
  - Losing streak median 7, 95th percentile 14.
- **Trade-order reshuffle:** max DD 95th percentile 38R (≈ 29%).
- **Random 20% trade removal:** total stays positive in 99.5% of draws.
- **Cost stress** (1 index point per trade): total 53.1R falls to 44.9R.
- **Deflated Sharpe = 0.00.** With 915 configurations tried, the expected best Sharpe from luck alone is higher than
  this version's 0.70 annualised.

## Unseen transfer test (frozen version, unchanged, 5y Model 4)
| Symbol | Trades | / month | / day | Return | PF | Equity DD |
|---|---:|---:|---:|---:|---:|---:|
| DE30 (DAX) | 250 | 4.2 | 0.19 | −9.6% | 0.91 | 21.6% |
| US500 | 282 | 4.7 | 0.22 | +19.8% | 1.14 | 12.2% |

The result is mixed: it loses on the closest index (DAX) and makes a below-gate profit on US500.

## Verdict
**REJECTED_AT_VALIDATION.**
- The optimisation found a strong development fit (PF 1.38), but it lost in validation and was flat to negative on the
  later years.
- The deflated Sharpe is 0, and the unseen DAX test lost.
- There is no stage 6 promotion, no Turbo/FTMO use and no deployment.
- The only part with consistent recent evidence is the **unoptimised raw S2 Monday dip**, which passed the raw gate.
  Its profit is concentrated in 2024–26 and it trades about 2 times a month.

Nothing installed, deployed or pushed. Older UK100 ticks are generated (real from 2026-01-02); the DE30/US500 windows
are also mostly generated ticks.
