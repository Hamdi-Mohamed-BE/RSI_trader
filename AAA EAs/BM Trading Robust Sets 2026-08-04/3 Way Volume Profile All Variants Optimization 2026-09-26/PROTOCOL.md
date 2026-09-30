# All 32 variants: frozen research protocol

Requested 2026-09-26. Optimize every combination, including earlier screening failures.
This is a broad staged parameter search, not an exhaustive Cartesian search or proof of a global optimum.
No live EA, BAT, website, account, or deployment changes are authorized by this experiment.

## Universe and controls

USTEC, XAUUSD, XAGUSD, BTCUSD, ETHUSD, EURUSD, USDJPY, GBPJPY.
For each: POC bounce (1), value-area reversal (2), value-area breakout (4), combined (7).
Raw M15 reference: original 2026-09-26 study, same dates, $10,000 USD, 1% equity risk,
2R, 64-bin previous UTC trading-day tick-volume profile, 70% value area, ATR14.
Prior raw evidence is retained, with native parity checks on all 32 references.
Historical broker binding: existing isolated Exness demo research terminal, leverage 1:2000.
This is NOT a simulation of the currently connected account or of FTMO execution.
Configured execution delay 150 ms, historical tester spread, broker commission/swap.
Lot sizing rounds UP as in the original; 1% is a target, not a strict maximum.
Unverified news calendars are not added as a filter.

## Time separation and selection

1. Development: 2021-09-26 through 2024-09-25. Native MT5 M1 OHLC (Model 1).
2. Validation: 2024-09-26 through 2025-09-25. Native Model 4. Choose between two
   frozen development finalists for EACH asset/setup, using the whole-position objective.
3. Comparison: 2025-09-26 through 2026-09-25. Native Model 4, raw and selected candidate.
   Parameters are frozen before this comparison. All candidates are reported, even failures.

Last-year raw results and some earlier gold validation results have already been seen.
Therefore this is a chronological validation/comparison, NOT a pristine untouched holdout.
Real ticks only exist from January 2026 in the previously audited research cache.
Earlier Model 4 periods can use generated ticks. Do not label the entire year real-tick verified.
Model 1 ranking can especially mis-rank tight stops, trailing stops, and small targets.

## Search coverage

Top TWO parameter vectors per asset/setup survive each stage, even if both lose money.
All remaining stages are run for every pair; there is no early profitability gate.
Every stage includes the previous leaders. Duplicate parameter vectors are removed per batch.
Native optimization enumerates case indices, using local tester CPU agents only.

Stages: timeframe; entry; stop; trailing; reward/exit; session; direction; filter;
trade management; profile construction; local stability neighborhood.

- Timeframe: M1, M3, M5, M15, M30, H1, H4. D1 is structurally inapplicable: the original
  daily-reset engine only builds the profile on each D1 bar and cannot trigger a trade.
- Entry: market, next-bar confirmation, 0.25 ATR limit retest, asset-scaled fixed limit retest,
  stop beyond the closed signal candle. Pending orders expire after four signal bars.
- Stop: original structure, ATR (0.5/0.75/1/1.5/2/3/4), price percent (0.05/0.1/0.2),
  fixed price distance, signal extreme, or five-bar swing. Pending stops are anchored at signal time.
- Fixed stops in price units: USTEC 50/100/200; XAU 5/10/20; XAG .1/.25/.5;
  BTC 250/500/1000; ETH 10/25/50; EURUSD .001/.002/.004; USDJPY .1/.2/.4; GBPJPY .2/.4/.8.
- Trailing: none, break-even, ATR, percentage, EMA50, swing, chandelier, step-lock.
- Target: 0.5/0.75/1/1.25/1.5/2/2.5/3/4/5/6/8R; no TP plus ATR trail; next profile level;
  time exit; session exit; 50% partial at 1R then ATR trail where minimum lot permits.
- Sessions: full day; 00-08 UTC; 07-16 UTC; NY 09:30-16:00; 12-16 UTC; NY 09:30-11:00.
  New York daylight saving is calculated. UTC windows remain fixed UTC, not local London time.
- Direction: both, long-only, short-only.
- Filters: none, EMA slope, H1 EMA alignment, ADX20, directional-index alignment,
  ATR percentile 20-80, spread <=0.1 ATR. Missing indicators fail closed.
- Management: skip Monday/Friday/both; 1/2/3/unlimited entries per day; 1/2 positions;
  stop new entries after a negative exit deal that day; 16/32/no bar timeout; Friday flatten/hold.
  The negative-exit-deal filter is deliberately described as such, not a whole-position loss filter.
- Profile: 32/64/96 bins; 60/70/80% value area; ATR7/14/28; relevant strategy stop buffers,
  breakout displacement, retest proximity and invalidation depth. Inactive setup knobs are omitted.
- Stability: 3x3x3 local grid around each finalist, using active exit, stop and profile dimensions.
  Report median neighbor objective and profitability fraction, then validate both original
  finalists; do not cherry-pick individual neighborhood points.

## Objective, interpretation and audit

Aggregate every entry/exit fee, commission, swap and P/L by native MT5 DEAL_POSITION_ID.
Partial exits are NOT extra independent trades or wins. Optimization objective uses this count
and whole-position PF, profit and maximum RELATIVE equity drawdown.
Minimum count for a positive score: 60 development, 30 validation positions.
Positive score: min(PF,3)*sqrt(positions/100)*(profit/10000)/(0.05+relative equity DD/100).
Unprofitable or under-count candidates retain a negative score so all 32 can be searched.
Selected validation candidates require positive net P/L, PF>=1.15, >=30 whole positions and
maximum relative equity DD<=20% to be called validation-qualified. Failure does not hide results.
The largest cash drawdown's associated percentage is not substituted for maximum relative DD.

Native source, EX5 hashes, input manifest, XML/HTML reports and appended journals are preserved.
Whole-position ledgers for final confirmation reconcile to native net P/L. History-start shifts,
missing reports and initialization failures are blocking evidence errors, not zero-return results.
Market-closed retries, rejected stops/orders and insufficient-margin messages are disclosed.
Promotional return claims, future pass/payout probabilities and live deployment are out of scope.
Even validation-qualified results still need independent holdout, execution-cost stress,
Monte Carlo and forward observation before any deployment recommendation.
