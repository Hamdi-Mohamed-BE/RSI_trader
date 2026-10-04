# VIX confirmed reversal / SVXY — raw daily screen

Raw screen failed: insufficient trades and no confirmed edge over matched random timing.

5y: return +3.18%, PF 2.271, WR 78.6%, close equity DD 1.45%, trades 14, max W/L 11/2.

3y: return +1.16%, PF 1.796, WR 75.0%, close equity DD 1.43%, trades 8, max W/L 6/2.

1y: return -1.00%, PF 0.297, WR 50.0%, close equity DD 1.42%, trades 4, max W/L 2/2.

6m: return +0.00%, PF —, WR —%, close equity DD 0.00%, trades 0, max W/L 0/0.

- One frozen daily interpretation, not a published rule set or proof that every volatility mean-reversion strategy fails. All thresholds are ours; no optimisation.
- VIX >=25 and >=1.25x its PREVIOUS 20-session average arms a five-session window. Confirm a close below the prior low and close; buy SVXY at next session open.
- SVXY stop is 2x prior Wilder ATR(14), target 2R; VIX return to the frozen mean or 10 held bars requests next-open exit. One trade at a time; no trailing, pyramiding or short borrowing.
- Whole-share sizing floors to 1% closed-balance risk and caps by available cash. Gap losses can exceed the budget. No minimum-lot override; no leverage.
- SVXY tracks -0.5x daily short-term VIX FUTURES, not spot VIX. Its roll and fund economics are embedded in ETF prices; do not map these returns to an Exness VIX CFD or futures contract.
- Headlines are BEFORE broker commission, spread and slippage. 5/10bps each side are illustrative sensitivity assumptions, not measured costs. No measured-cost gate is passed.
- Daily OHLC bars cannot supply 150ms fill simulation, native tick equity DD, order-book liquidity, historical bid/ask costs, or FTMO pass/payout estimates. Exact intraday order is unknown; both-touch bars take SL first.
- Close equity DD includes marked open P&L at session closes. OHLC assumed-path DD follows a low-before-high convention and is not exact native equity DD.
- Official Cboe VIX replaces connector VIX as predeclared. Three overlapping closes differ by more than 0.02; largest is 2.61 on 6 Feb 2026. Their differences are saved; official observations on non-ETF sessions are omitted from joint-session signals.
- The test history has been seen in earlier research. Windows overlap; independent annual resets do not sum or compound to the continuous five-year run. No pristine prospective holdout.
- Matched random schedules match count, weekday mix and maximum observed holding-session horizons, with the same stops, targets and risk. VIX-mean exits are replaced with matched time exits in controls. This is a timing diagnostic, not an exact strategy twin.
- 10,000 circular block-5 risk-unit resamples are historical diagnostics, not forecasts; small sample undermines inference. No future pass or payout probabilities are implied.
- Independent reconstruction verified 92 overlapping closed trades across 17 runs, plus daily equity and prefix-causal signals. Eleven unit tests passed.
- No active EA, broker account, MT5 installation, website, portfolio, or FTMO settings changed for this research. Gold-only BAT policy was committed and pushed separately as 582175546.
