# FTMO ticket sizing — REPORT (2026-10-24)

**Owner request:** test the pasted clip's approach on our FTMO portfolios and give the rates. The clip says:
- treat the evaluation as a ticket;
- what it costs = fee × attempts × months;
- size up until passing gets fast, not tiny;
- beyond the right size you only add variance.

**Engine:** frozen Portfolio Prop Comparison 2026-10-22, FTMO 2-step $100k, 180-day attempts, 2,000 MC attempts plus
every weekday history start. Python only. Full table: `RESULTS.md`.

## Result: the clip is right for the unguarded portfolio, and the optimum is 1%. The guarded portfolios cannot size up.

| Portfolio | Best risk for cost and time | Pass rate MC / hist | Fees per funded MC / hist | Days to funded incl. retries MC / hist | Breach |
|---|---:|---:|---:|---:|---:|
| **Current 14 + ORB 0.5R, no guard** | **1.0%** | 64% / 60% | 1.55 / 1.68 | **86 / 85** | 35% |
| same | 0.5% (today's style) | 76% / 66% | 1.32 / 1.52 | 155 / 175 | 4% |
| same | 1.5% | 30% / 32% | 3.31 / 3.12 | 75 / 69 | 70% |
| same | 2% / 3% | 17% / 6% | 5.8 / 15.5 | 82 / 115 | 83% / 94% |
| Prop ready 9 (guard) | 1.0% | 62% / 67% | 1.62 / 1.50 | 187 / 160 | 0% (45% stuck) |
| FTMO guarded 17 | 0.5% (packaged) | 62% / 67% | 1.61 / 1.50 | 223 / 203 | 0% (13% stuck) |
| Best Prop 9 (guard) | 1.0% | 54% / 59% | 1.84 / 1.69 | 219 / 190 | 0% (54% stuck) |

## Reading it
- **Unguarded Current 14 + ORB matches the clip's shape.**
  - Going from 0.5% to 1% cuts the time to funded from 155 to 86 days, including retries, for only +0.23 fees per funded
    account.
  - At 1.5% it is slightly faster again (75 days) but costs 3.3 fees.
  - At 2–3% it is both slower and more expensive: variance only, as the clip says.
- **Guarded portfolios do not speed up above about 1%.** The guard's fixed $ reserve, total-exposure limits and 92%
  entry buffer bind, so results are identical from 1.5% to 3%. About half the attempts stall frozen near the buffer.
  - Stalled attempts are counted as the full 180 days. A trader who restarts a stalled attempt would do better, but
    that is not measurable from the saved trials.
- **The clip's "end-of-day drawdown" does not exist on FTMO.** FTMO measures daily and max loss on equity. EOD drawdown
  is a futures-firm option.

## Practical combination (follows from the data; not separately simulated end-to-end)
- **Challenge:** Current 14 + ORB 0.5R unguarded at 1% (about 86 days and 1.55 fees per funded account).
- **Funded:** switch to the guarded FTMO 17 package at 0.5%.
  - Funded at 1% unguarded ended within a median of 86 days (100% breach in the Prop Comparison study).
  - Guarded 0.5% lasted a median of 1,061 days at about $2,634 a month per $100k.
- **Switching** needs a reinstall with Algo off and a flat account; the installers support it.

## Limits
- **In-sample:** EAs chosen on this history; ticks before 2026 are generated.
- **Independent attempts:** treating MC attempts as independent is optimistic if a bad regime persists across retries.
- **Hypothetical guards:** guard levels above 0.5% are not what the installed packages do.
- **Not a forecast or advice.**
