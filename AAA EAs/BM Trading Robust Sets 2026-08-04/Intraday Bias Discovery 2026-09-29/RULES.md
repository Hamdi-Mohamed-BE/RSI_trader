# Intraday bias discovery — frozen protocol

Frozen before loading strategy returns, 29 September 2026. This is the user's bounded discovery request, not permission to optimize a production EA, place trades or change a live account.

## Instruments and data

Exness-MT5Trial16 CFD history only: US30, USTEC (US100), US500 (SP500), XAUUSD, BTCUSD, ETHUSD, EURUSD, GBPUSD, USDJPY, AUDUSD, NZDUSD, USDCAD, USDCHF. These are broker CFDs, not cash indices, exchange futures or exchange crypto. Collect five-minute bid OHLC and recorded spread through a no-trade EA in the isolated portable tester. Never initialize or modify live MT5. Confirm UTC timestamps against existing archives. Reject missing, duplicated or nonpositive price records. Never forward-fill.

Study: 2021-09-27 inclusive through 2026-09-27 exclusive. Development: before 2024-03-27. Validation: 2024-03-27 through 2025-09-26. Final holdout: 2025-09-27 through 2026-09-26. Holdout is unused by this search, not globally pristine: other historical research in this workspace used overlapping dates. Missing coverage is disclosed; no feed substitution to rescue a result.

## Fixed discovery grid

One entry per local calendar day at each half-hour (00:00 through 23:30); hold 30, 60 or 120 elapsed minutes; long or short; clocks UTC, America/New_York and Europe/London. DST handled by IANA zones. A maximum of 864 configurations per instrument, 11,232 across 13. Remove identical entry/exit timestamp sequences before ranking. Exclude windows with any missing five-minute bar, and positions spanning 17:00 New York (financing/rollover). Crypto includes weekends; other instruments use available weekday sessions. No weekday filters, indicators, stops, take-profits, parameter refinement or post-holdout replacement.

## Pricing, control and costs

Enter at the observed five-minute open; exit at the observed open after the holding period. Bid OHLC cannot establish actual executable fills. Long: exit bid minus entry bid minus entry spread. Short: entry bid minus exit bid minus exit spread. Spread points converted using native symbol point size. Recorded bar spread is an imperfect execution proxy. Use the larger of recorded spread and development-only positive-spread median for that New York half-hour; fall back to the instrument development positive-spread median. Report zero-spread prevalence. No pretend zero-cost fills.

Baseline is spread-only, no separate commission or slippage. Stress is twice the modeled spread plus two minimum price ticks per round trip, an explicitly hypothetical cushion, not measured slippage. Exclude rollover to avoid inventing historical financing. Results therefore cannot establish live net profitability for a different broker/account.

For time-specificity, subtract the same-day average return of all eligible UTC half-hour starts with the same holding period/direction. This matched daily control prevents broad asset drift from being mislabeled as a clock advantage. Use the same cost treatment for control trades.

## Selection and survival

Development needs at least 400 observations. Rank configurations by the lower of the net-return t-statistic and paired excess-over-control t-statistic. Select exactly one per instrument using development only; record all searches and freeze candidates before validation or holdout. No runner-up substitution.

Pass development and validation separately: positive net and excess mean; profit factor >=1.15; >=200 validation observations. Adjacent entry times (-30/+30 minutes, same clock/direction/horizon) must each have positive baseline mean in development and validation. Final holdout: >=150 trades, positive net and excess mean, PF>=1.15, positive stressed mean, and positive baseline mean in both chronological halves. If no configuration meets development minimum, mark insufficient data.

Final inference: 10,000 circular moving-block bootstrap paths, five consecutive trading days per block, fixed seeds. One-sided centered-null bootstrap p-values for net and paired excess return. Take their maximum, then apply Holm family-wise correction across all 13 selected instruments (missing instruments p=1). Require adjusted p<=0.05 and both one-sided 95% lower mean bounds >0. Bootstrap assumptions are approximate; volatility/regime changes remain possible. Also report stressed PF and effect sizes. No result may be called a survivor if an earlier gate failed.

## Reporting

Return and drawdown use fixed notional exposure, no leverage or risk-per-stop fiction. Record trades, trades/month, trades/trading day, cumulative net return, PF, win rate, entry-to-exit mark-to-market drawdown and win/loss streaks. No compounding. For zero net trades, classify as neither wins nor losses and reset streaks. Show each asset's selected candidate even if rejected. Native data export is not a native strategy backtest. Any statistical survivor remains a research candidate until native execution and independent feed/cost confirmation. Keep the full grid, selected rules, ledger, data hashes, source code and test results. Do not promote or deploy.
