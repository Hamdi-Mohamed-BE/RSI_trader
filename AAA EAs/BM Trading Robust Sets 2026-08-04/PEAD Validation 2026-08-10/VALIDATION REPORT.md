# PEAD Strategy Validation

**Date:** 2026-08-10  
**Source reviewed:** Mat Conti transcript supplied by the user  
**Decision:** The underlying anomaly is academically established for individual equities, but the transcript's performance figures are not independently reproducible from the information supplied. The exact strategy cannot be applied to XAU, BTC, EURUSD, GBPJPY, US30, or US100.

## 1. Strategy extracted from the transcript

The video describes **post-earnings-announcement drift (PEAD)**:

1. Compare a company's reported EPS with the analyst consensus available before the announcement.
2. Require the immediate stock-price reaction to agree with the surprise:
   - positive surprise and positive reaction: long;
   - negative surprise and negative reaction: short.
3. Enter at the next regular-session open after the reaction day.
4. Hold for 60 trading sessions.
5. Use no stop loss and no take profit.
6. Allocate 10% of portfolio capital to each position.
7. The transcript later reports a stronger long-only variation.

This is an event-driven **individual-stock** strategy. The earnings event and the point-in-time analyst forecast are indispensable signal inputs.

## 2. Applicability to the requested instruments

| Instrument | Reports corporate EPS? | Has its own analyst EPS consensus? | Exact PEAD test valid? |
|---|---:|---:|---:|
| XAUUSD | No | No | No |
| BTCUSD | No | No | No |
| EURUSD | No | No | No |
| GBPJPY | No | No | No |
| US30 index | No | No | No |
| US100 index | No | No | No |

US30 and US100 contain companies that report earnings, but the indices themselves do not. A constituent-level earnings model that aggregates positions across index members could be researched, but that is a different portfolio strategy. It needs historical constituent membership, corporate actions, every constituent's point-in-time consensus, actual EPS, and exact announcement timestamp.

## 3. Academic validation

- Ball and Brown (1968) established that accounting-income information is associated with stock-price behavior.
- Bernard and Thomas (1989) directly studied post-earnings-announcement drift.
- Livnat and Mendenhall (2006) found that drift is stronger when earnings surprise is constructed from analyst forecasts and reported earnings than from a simple time-series expectation model. This makes point-in-time consensus data particularly important.
- A 2021 review by Josef Fink describes PEAD as a long-studied stock-price drift in the direction of a firm's earnings surprise, while noting that the literature has no single complete explanation.

References:

- Ball, R. and Brown, P. (1968), *An Empirical Evaluation of Accounting Income Numbers*: https://doi.org/10.2307/2490232
- Bernard, V. L. and Thomas, J. K. (1989), *Post-Earnings-Announcement Drift: Delayed Price Response or Risk Premium?*: https://www.jstor.org/stable/2491062
- Livnat, J. and Mendenhall, R. R. (2006), *Comparing the Post-Earnings Announcement Drift for Surprises Calculated from Analyst and Time Series Forecasts*: https://doi.org/10.1111/j.1475-679X.2006.00196.x
- Fink, J. (2021), *A review of the post-earnings-announcement drift*: https://ideas.repec.org/a/eee/beexfi/v29y2021ics2214635020303750.html

## 4. Audit of the performance claims in the transcript

The transcript reports approximately:

| Variation | Period | Initial capital | Reported profit | Reported PF | Reported win rate | Reported max DD |
|---|---|---:|---:|---:|---:|---:|
| Concordant long/short | Jan 2018–Apr 2026 | $100,000 | $131,000 | 1.99 | 61% | 17.4% |
| Concordant long-only | Jan 2018–Apr 2026 | $100,000 | $146,000 | 2.68 | 63% | about 20% |

These are **claims from the video, not independently verified results**. Reproduction is impossible from the transcript because it omits the exact stock universe, event file, historical forecasts, code, trades, price source, cost model, and full portfolio accounting.

Important limitations:

1. The presenter acknowledges selection bias in the chosen companies.
2. Choosing today's recognizable large companies can create survivorship bias.
3. A current earnings webpage is not necessarily a point-in-time record of the consensus that was knowable immediately before each historical announcement.
4. A 60-session holding period causes overlapping positions. The transcript does not fully specify cash constraints, concurrent exposure, or what happens when more than ten signals are active at 10% each.
5. Short borrow availability, borrow fees, dividends, spread, commission, slippage, delistings, splits, and mergers are not fully specified.
6. Announcement timing must distinguish before-open, after-close, and intraday releases to avoid look-ahead errors.
7. Turning $100,000 into $231,000 between January 2018 and April 2026 implies a simple CAGR of roughly 10.6%, not exactly the stated 12%; the difference may reflect a different annualization calculation, but it cannot be checked without the underlying report.

## 5. Data required for an honest backtest

At minimum, each event needs:

- permanent security identifier and ticker valid on the event date;
- historical universe membership on every date;
- fiscal period and announcement timestamp in UTC;
- before-open/after-close/intraday classification;
- reported EPS exactly as initially released;
- analyst consensus snapshot timestamped before the release;
- adjusted and unadjusted OHLC prices and corporate actions;
- dividends, delistings and mergers;
- realistic commission, spread, slippage and short-borrow assumptions.

The portfolio engine must define signal ranking when capital is full, maximum gross and net exposure, handling of overlapping signals, quarterly re-entry, and whether position size is based on initial or current equity.

## 6. Reproducible validation design

1. Use a point-in-time universe, such as historical S&P 500 constituents—not today's constituents carried backward.
2. Freeze every consensus snapshot before the announcement.
3. Reserve the newest years as a final untouched out-of-sample test.
4. Test the transcript's original rules first, without optimization.
5. Separately test concordance, surprise thresholds, long-only, and holding periods; correct for multiple testing.
6. Include all trading and borrow costs.
7. Report CAGR, total return, max equity drawdown, PF, win rate, trade count, exposure, turnover, Sharpe/Sortino, and year-by-year results.
8. Run sensitivity and bootstrap tests so that the result does not depend on a few companies or events.

## 7. Final verdict

**Concept validity:** Valid and supported by the stock-market research literature.  
**Video backtest validity:** Plausible but unverified and insufficiently documented.  
**Validity on the six requested instruments:** Invalid as an exact implementation because none has company-level EPS and consensus inputs.  
**EA/system decision:** Do not add this as an XAU/BTC/FX/index EA or to the active MT5 BAT portfolio. A defensible implementation would be a separate equity-event portfolio system connected to historical and live earnings-consensus data.

