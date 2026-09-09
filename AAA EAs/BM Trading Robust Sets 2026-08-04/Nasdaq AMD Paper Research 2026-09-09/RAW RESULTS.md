# Step 9 — Nasdaq AMD raw reproduction

## Decision

**Research-only; do not add this raw strategy to the portfolio.** The full result is
positive, but it comes from only eight accepted trades in four and a half years. The
more relevant three-year result becomes negative after the paper's own transaction-cost
assumption, and the paper's attractive trend-regime split relies on the same day's 4 PM
close, which is unavailable at the morning decision time.

No optimizer was run. No EA, website, installer, BAT, recommended portfolio, or live MT5
terminal was changed.

## Source and faithful implementation

- Paper: *Evaluating the Predictive Validity of ICT's
  Accumulation-Manipulation-Distribution (AMD) Model*, Veer Taylor (2026).
- Paper URL: <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7150238>
- Author code: <https://github.com/veertaylor19/amd-backtest>, commit
  `811e37337a9b8cd02c686a99d4559088acd065dc`.
- Test market: Exness `USTEC` CFD, cached M15 OHLC and historical spread.
- Test clock: `America/New_York`, including DST.
- Full window: 2022-01-01 to 2026-07-01 (end exclusive), matching the paper. This is
  four and a half years, not a fabricated five-year result.

The independent implementation was cross-run through the author's source. It matched all
1,157 trading days, all eight accepted trade dates, directions, outcomes, and R-multiples.

## Locked raw rules

1. Asia accumulation range: prior calendar day, 19:00–00:00 ET.
2. London manipulation: 10-point unilateral breach of an Asia boundary between
   02:00–04:00 ET, followed by a close back inside before 05:00 ET.
3. Reject a bilateral breach.
4. Reject Asia ranges above the paper's published 106.38-point cutoff. The number stays
   fixed in the full, three-year, and one-year reports.
5. Reject if the opposite Asia boundary is swept between 05:00 and 09:40 ET.
6. Enter at the open of the first M15 candle from 09:40–10:30 ET that has reclaimed the
   relevant Asia boundary. On M15 data the first possible candle is 09:45.
7. Target the opposite Asia boundary; stop four points beyond the London extreme.
8. Reject planned reward/risk below 1.5.
9. Exclude the author's FOMC/NFP dates.
10. No time exit. A bar touching stop and target is conservatively scored as a loss.

## Strategy performance at 1% equity risk

### Gross raw track

| Window | Trades | Win rate | Return | PF | Max DD | Sharpe | Recovery | Total R | Expectancy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Full 4.5y | 8 | 50.00% | +5.03% | 2.19 | 1.99% | 0.47 | 2.53 | +5.03R | +0.629R |
| 3y | 5 | 40.00% | +0.59% | 1.19 | 1.99% | 0.12 | 0.30 | +0.64R | +0.127R |
| 1y | 2 | 50.00% | +0.71% | 1.70 | 1.00% | 0.37 | 0.71 | +0.73R | +0.366R |

### Paper cost track — six index points round trip

| Window | Trades | Win rate | Return | PF | Max DD | Sharpe | Recovery | Total R | Expectancy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Full 4.5y | 8 | 50.00% | +3.46% | 1.70 | 2.35% | 0.34 | 1.47 | +3.52R | +0.440R |
| 3y | 5 | 40.00% | -0.36% | 0.90 | 2.35% | -0.06 | -0.15 | -0.32R | -0.064R |
| 1y | 2 | 50.00% | +0.29% | 1.24 | 1.19% | 0.16 | 0.24 | +0.30R | +0.152R |

### Exness historical-spread track

| Window | Trades | Win rate | Return | PF | Max DD | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full 4.5y | 8 | 50.00% | +4.39% | 1.98 | 2.07% | 0.42 | 2.12 |
| 3y | 5 | 40.00% | +0.22% | 1.07 | 2.07% | 0.05 | 0.11 |
| 1y | 2 | 50.00% | +0.71% | 1.69 | 1.00% | 0.36 | 0.71 |

The spread track uses the historical entry-bar spread. It does not invent commission,
swap, or execution delay. The paper-cost track is the safer decision column.

## Full-sample filter attrition

| Stage | Days remaining | Share of starting days |
|---|---:|---:|
| Trading days | 1,157 | 100.00% |
| Asia range passes | 877 | 75.80% |
| Timely breach exists | 655 | 56.61% |
| Breach is unilateral | 633 | 54.71% |
| Close-back confirmed | 387 | 33.45% |
| Opposite target remains intact | 169 | 14.61% |
| Valid New York entry | 60 | 5.19% |
| Planned RR at least 1.5 | 8 | 0.69% |
| Macro filter passes | 8 | 0.69% |

The result is therefore driven by fewer than two trades per year. PF, Sharpe, recovery,
and win rate are descriptive only; they are not statistically dependable at this sample
size.

## Paper comparison and regime audit

| Test | Paper NQ | Exness USTEC CFD |
|---|---:|---:|
| Accepted trades | 6 | 8 |
| Accepted-trade win rate | 50.0% | 50.0% |
| Gross expectancy | +0.683R | +0.629R |
| Bullish signal accuracy | 46.9% of 226 | 46.9% of 224 |
| Bearish signal accuracy | 39.9% of 258 | 40.1% of 257 |

The close match confirms that the transfer is behaving like the published model. It also
confirms the paper's main finding: the unconditioned AMD direction is not predictive.

The paper reports 60.9% bullish accuracy in an uptrend and 68.5% bearish accuracy in a
downtrend on this CFD replication. However, that regime label uses the same day's 4 PM
close, after the morning setup. With the regime shifted to the prior completed day:

| Causal trend-aligned cell | Signals | Accuracy |
|---|---:|---:|
| Bullish signal after prior-day uptrend | 122 | 45.08% |
| Bearish signal after prior-day downtrend | 79 | 45.57% |

The apparent trend-conditioned advantage disappears without lookahead. That is the main
reason not to promote or optimize this strategy yet.

## Reproduce

Run `python run_raw_test.py` from this folder. Outputs are:

- `raw-trades.csv` — every accepted trade and all three cost tracks.
- `raw-results.csv` — complete metrics by window and cost track.
- `directional-signals.csv` — signal-by-signal 4 PM prediction audit.
- `regime-audit.csv` — same-day and prior-day regime results.
- `raw-paper-audit.json` — exact source hashes, rules, dates, attrition, and parity check.
