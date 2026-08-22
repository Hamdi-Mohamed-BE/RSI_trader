# Prop-Safe News Strategy Candidate — 2026-08-16

## Conclusion

The only news family worth developing is a **post-release macro-surprise continuation with pullback entry** on EURUSD. Do not use a pre-release buy-stop/sell-stop straddle. Do not assume this strategy can complete two prop phases and produce a reward inside four months until it passes a historical-consensus backtest and a forward trial.

## Research basis

- NBER evidence shows that the difference between the released number and market expectation produces systematic conditional-mean jumps in USD exchange rates.
- New York Fed research identifies nonfarm payrolls among the small subset of releases producing economically significant and measurably persistent responses. Stronger-than-expected growth and inflation generally raise the dollar and bond yields.
- Federal Reserve research finds price incorporation is generally completed within minutes, while trading volume and volatility can remain elevated longer. This argues against slow entries and against blindly chasing the first tick.
- Research on FOMC currency returns finds later reversals can offset much of the pre-announcement move, so FOMC continuation requires a separate rule and should not be mixed blindly with CPI/NFP logic.

Sources:

- https://www.nber.org/papers/w8959
- https://www.newyorkfed.org/research/current_issues/ci14-6.html
- https://www.federalreserve.gov/pubs/ifdp/2004/823/ifdp823.htm
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4386170

## Candidate rules

### Markets and events

- Primary market: EURUSD.
- Events: U.S. CPI and Employment Situation/NFP.
- Optional after separate validation: advance GDP and ISM Manufacturing.
- FOMC is excluded from version 1 because the 2:00 statement and 2:30 press conference can create conflicting moves.

### Before the event

- Pull the official event timestamp and convert America/New_York time to server time using a timezone database, not a fixed offset.
- Record the 30-minute pre-event high/low, M1 ATR(20), M15 ATR(14), median spread, and last valid quote.
- No orders or positions are created solely for the event before release.
- No new order from two minutes before through five minutes after release.

### Fundamental qualification

Use the original contemporaneous consensus, not revised data.

- CPI USD-positive: headline and core monthly CPI surprises are both positive and neither conflicts materially with year-over-year readings.
- CPI USD-negative: headline and core monthly surprises are both negative.
- NFP USD-positive: payroll surprise positive, unemployment not materially worse, and average hourly earnings not materially weaker.
- NFP USD-negative: payroll surprise negative, unemployment not materially better, and earnings not materially stronger.
- Normalize each surprise by its trailing 24-release forecast-error standard deviation. Require a composite absolute z-score of at least 0.75.
- Skip mixed releases.

### Price and execution qualification

At five minutes after release:

- The five-minute impulse must agree with the fundamental direction.
- Its close must be outside the pre-event 30-minute range.
- Impulse size must be between 0.50 and 1.50 times M15 ATR(14): smaller moves lack confirmation; larger moves are too extended to chase.
- Candle body at least 60% of its range.
- Current spread no greater than two times the pre-event median and no greater than the broker-specific absolute cap.
- Quote age no more than two seconds.

### Entry and exit

- Place one limit order at the 40–60% retracement of the five-minute impulse.
- Cancel if not filled within ten minutes.
- Stop beyond the impulse origin plus 0.10 M15 ATR, subject to a one-ATR minimum and spread buffer.
- Initial target: 1.8R.
- Move stop to entry only after 1R.
- Exit at 45 minutes after release if neither stop nor target has been reached.
- One trade per event; no second leg, recovery trade, averaging, or opposite pending order.

### Risk

- Research and demo: 0.25% per event.
- Maximum after validation: 0.35% per event.
- Daily portfolio loss stop: 1.50%.
- Maximum total open risk across every EA: 1.00% evaluation and 0.70% funded.
- Two consecutive news losses trigger a pause until the next calendar month.

## Prop-firm fit

### The5ers Classic High Stakes

- Phase targets: 8% and 5%.
- Static/absolute maximum loss: 10%.
- Daily loss: 5%.
- Three profitable days in each phase; a profitable day requires at least 0.5% of initial balance.
- No new orders two minutes before through two minutes after high-impact news.
- Pre-release bracketing is prohibited.
- Custom EA use requires source-code ownership and written approval under the current terms.
- Funded withdrawals are available every 14 days under the programme rules.

Official pages:

- https://the5ers.com/faqs/what-are-the-general-rules-for-the-high-stakes-program/
- https://www.the5ers.com/high-stakes/
- https://the5ers.com/faqs/prohibited-trading-practices/
- https://the5ers.com/terms-and-conditions/

### FTMO 2-Step Swing

- Phase targets: 10% and 5%.
- Static maximum loss: 10%.
- Daily loss: 5%.
- Custom legitimate EAs are permitted without the written-preapproval clause found in The5ers' current terms.
- Swing permits news and overnight holding, subject to forbidden-practice rules.

## Four-month feasibility

Completing an 8% phase, a 5% phase, then earning a 2% funded profit requires approximately 15% sequential gross performance. FTMO requires approximately 17% because its first target is 10%.

For a news-only system trading roughly 12 CPI/NFP events in four months:

- At 0.25% risk, 15% requires 60 net R, or 5R per event: impossible as a base expectation.
- At 0.50% risk, 15% requires 30 net R, or 2.5R per event: not credible.
- At 1.00% risk, 15% requires 15 net R, or 1.25R per event while also surviving slippage and loss streaks: still implausible and too risky.

The news strategy can therefore be an additive diversifier, not the main four-month challenge engine.

## Acceptance gate before deployment

- Minimum ten years of event timestamps, original consensus, actual releases, and tick/minute execution data.
- Development, validation, and locked recent holdout with no parameter selection on the holdout.
- At least 150 completed events across the tested release set.
- Net PF at least 1.35 after spread, commission, and event-specific slippage.
- Slippage-stress PF at least 1.15.
- Maximum equity drawdown no more than 6% at 0.50% risk.
- Positive results in at least four of the last five complete years.
- No single event contributing more than 15% of total profit.
- Eight to twelve weeks of forward demo execution with zero clock or rule violations.

