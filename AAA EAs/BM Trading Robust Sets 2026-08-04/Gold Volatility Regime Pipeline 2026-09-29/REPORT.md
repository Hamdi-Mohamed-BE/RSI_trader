# Gold volatility-regime bot — review

## Decision

**No improved version survived. Keep the original as the benchmark; do not replace it with the optimized candidate.** This is not approval to trade the original live. Gold alone was tested; Nasdaq, Bitcoin and GBPUSD have not been started.

The selected candidate passed development, the parameter-neighbourhood check and the 18-month validation. It then lost money and had worse drawdown than the original over the reserved latest year. The pipeline correctly stops at **REJECTED_RECENT_CONFIRMATION**. No attempt was made to rescue it by tuning that year.

## Like-for-like native results

Each run starts with $10,000 USD; target risk is 1% equity, rounded UP to the broker's lot step. Model 4 uses recorded ticks where available and generated ticks otherwise. Return is cumulative, not annualized; DD is native floating-equity drawdown. PF and win rate use net position P&L including fees and swap, so may differ from the platform's gross-trade win count. Frequency per weekday uses Monday–Friday calendar days, including holidays; it is not trades per active trading day.

| Version / period | Return | Net PF | Equity DD | Trades | / month | / weekday | Net win% | Max W / L streak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Original — validation | +9.42% | 1.37 | 6.90% | 65 | 3.60 | 0.165 | 50.77% | 5 / 7 |
| Selected A — validation | +3.56% | 1.37 | 5.05% | 38 | 2.11 | 0.097 | 28.95% | 3 / 9 |
| Original — reserved year | +4.36% | 1.17 | 7.00% | 44 | 3.67 | 0.169 | 45.45% | 3 / 4 |
| Selected A — reserved year | -2.44% | 0.80 | 9.39% | 35 | 2.92 | 0.135 | 11.43% | 2 / 18 |

Validation: **2024-03-27 to 2025-09-27 exclusive**. Reserved year: **2025-09-27 to 2026-09-27 exclusive**. The candidate underperformed the original's cash return even in validation; its slight PF advantage was not an improvement that held up afterward.

![Gold comparison](C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/Gold Volatility Regime Pipeline 2026-09-29/comparison.png)

The chart samples the recorded equity trace hourly for legibility. Table drawdowns come from the full native tester, not the downsampled chart.

## Three finalists, not three proven edges

Development: 2021-09-27 to 2024-03-27 exclusive. These are **Model 1 one-minute OHLC screening results**, selected after searching, not comparable evidence quality to the Model 4 validation above.

| Version / period | Return | Net PF | Equity DD | Trades | / month | / weekday | Net win% | Max W / L streak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Candidate A — development | +18.75% | 4.01 | 2.76% | 61 | 2.04 | 0.094 | 52.46% | 4 / 4 |
| Candidate B — development | +19.00% | 4.01 | 2.74% | 60 | 2.00 | 0.092 | 53.33% | 4 / 4 |
| Candidate C — development | +19.00% | 4.01 | 2.74% | 60 | 2.00 | 0.092 | 53.33% | 4 / 4 |

Native Model 4 validation of all three, with the same threshold fixed in advance: at least30 positions, positive return, PF>=1.15 and clean execution.

| Version / period | Return | Net PF | Equity DD | Trades | / month | / weekday | Net win% | Max W / L streak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Candidate A — validation | +3.56% | 1.37 | 5.05% | 38 | 2.11 | 0.097 | 28.95% | 3 / 9 |
| Candidate B — validation | +0.60% | 1.06 | 5.53% | 35 | 1.94 | 0.089 | 25.71% | 2 / 9 |
| Candidate C — validation | +0.60% | 1.06 | 5.53% | 35 | 1.94 | 0.089 | 25.71% | 2 / 9 |

- A passed validation and was frozen before the latest-year test. Latest year: PF0.80, negative return, and one rejected stop modification. It fails on performance independently of that execution flag.
- B and C failed validation (PF1.06). They were not tried on the reserved year. Their no-elapsed-time and16-hour holds produced identical development/validation results because the daily flat rule dominated here; they are not independent corroboration.
- All three neighbourhoods passed the coarse plateau screen; that did **not** imply they would generalize. A's27 neighbours were100% profitable in development, medianPF2.17, yet A still failed later.

## Selected candidate A — exact interpretation

- H1 completed candles; ATR14/ATR100 Hot threshold1.2;252-transition history,20 Hot observations minimum, Laplace smoothing, persistence threshold0.65; the newest transition is excluded.
- EMA50 direction/slope over5 bars and previous-bar breakout, with completed-H4 EMA50 direction agreement.
- Buy/sell stop0.5ATR beyond the observed executable quote; pending lifetime4 signal bars, bounded by the daily flat time. Both directions, weekday entry07:00–16:59 UTC.
- Fixed **$10 price-distance stop** (not $10 account risk), target2.5R. Move the stop to entry at0.5R favorable movement. A breakeven stop does not guarantee zero net P&L because of execution and costs.
- One position, normally one attempt/day, one additional qualifying attempt after a losing-price SL;8-hour maximum holding or20:00UTC /5minutes before broker session close. The retry implementation checks negative DEAL_PROFIT on an SL; it is not a universal after-fees-loss trigger.
- 1% target risk; observed maximum initial fill-to-stop risk was1.123% in the reserved year. Original maximum on that year was1.801%. These are stop-distance estimates, not a guarantee on realized loss.

Execution exception: **2026-06-10 12:29:52**, one breakeven-stop modification returned `Invalid stops`. The rejected request is preserved in the native journal. No post-result code or parameter change was used to improve the reported return. Net-cost totals and small-loss counts are in `RECENT COST ACCOUNTING.json`; the18-loss maximum streak includes small negative trades, not18 full1R losses.

## Coverage and audit

- 590 native passes archived, including 582 development/plateau screen passes; 508 unique parameter vectors. Repeats and retired trials remain counted. Including the earlier64-run raw screen gives654 observed passes for any later multiplicity accounting. Counts are not independent experiments.
- Seven timeframes; market/confirmation/pending entries; ATR, percentage, fixed-price and structural stops; BE/trailing/partial/time/RR exits; sessions; direction; filters; trade management; regime parameters; joint neighbourhoods. Search is staged with a top-three beam, **not** an exhaustive global optimum.
- Every completed pass reconciles native report cash to its position ledger. Verified46,205 position rows across590 archived passes;7 passes had execution flags and were not treated as clean candidates.
- Zero-error, zero-warning final compilation. The initial warning-only build was corrected and archived before any test.
- Exact original/new-engine parity on44 baseline trades: times, side, prices, volume, SL/TP and net P&L. Independent numerical checks passed216 past-only/symmetry windows and44 native baseline signal checks.
- The regime skill informed the causal-state checks. Its packaged runner was unavailable; this uses the disclosed ATR-state Markov filter, **not GARCH**, an HMM or proof that volatility clustering predicts direction.

### Important repair and selection bias

The first management search allowed two position slots with only one daily attempt and split the risk between them. That inactive second slot only cut risk in half. Those versions were retired. The management/regime search was restarted with a structural capacity rule: at least two daily attempts and actual observed overlap for a two-slot candidate. The original runs remain in `repair1-audit` and the all-pass ledger.

This was found before inspecting those early validation returns, although two early validation runs had executed automatically. They were retained; validation is therefore not represented as pristine. The latest year was also already seen for the raw baseline. This is retrospective screening, not untouched future-forward evidence. It is enough to reject this candidate, not enough to certify a survivor.

Exness-MT5Trial16 XAUUSD CFD, USD,1:2000 research leverage,150ms delay. Recorded real ticks start **2026-01-01**. The earlier validation used generated ticks; Model4 does not make missing historical ticks real. The recent report's49% real-tick coverage includes the180-day no-trade warmup. This is not an FTMO-native feed or proof of live fills.

## Where the pipeline stopped

Raw eligibility: passed earlier. Baseline parity: passed. Broad search: completed. Neighbourhoods: passed. Validation: onlyA passed. Reserved recent year: **failed**.

**Not advanced:** older2019–2021 holdout; new6m/3y/5y candidate confirmations; direction control on the selected candidate;10,000-path Monte Carlo; deflated Sharpe; additional-cost stress; FTMO scenarios; portfolio integration; forward/live deployment. Those gates cannot turn a failed reserved-period result into a validated strategy, and no readiness or probability claim is made. `finish.py` is a prepared, guarded continuation utility, not evidence that those tests ran.

Your original +33.11%/PF1.33/7.48% five-year result was the faster Model1 screen. Its prior Model4 confirmation was +33.06%/PF1.33/7.38%,209 trades. No five-year result is claimed for the selected optimized version because it failed earlier.

## Files and next action

`PROTOCOL.md` records dates, rules and the repair. `ALL NATIVE RESULTS.json` includes every completed pass, including retired ones. `DEVELOPMENT FINALISTS.json`, `PLATEAUS.json`, `FROZEN FINAL.json`, `PARITY.json`, `VERIFICATION.json` and `VERDICT.json` provide machine-readable evidence. Native source, binaries, inputs, compressed ledgers/reports and journals remain in the local native folders. The review ZIP excludes private tester connection files and raw account-identifying reports.

The original bot was not modified; no website, installer, portfolio or live account was changed. The candidate has a tester-only guard and remains rejected. **Stop here for the user's Gold review before any other asset.** The list still has four assets despite the wording “three”; confirm the remaining scope when continuing.

## Method references

MetaTrader documents that [missing real ticks are replaced by generated ticks](https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation), and defines the [native testing modes](https://www.mql5.com/en/docs/runtime/testing). The reason to count all trials is the [Bailey–Lopez de Prado Deflated Sharpe research](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551); that statistic was not run after this candidate failed its earlier gate.
