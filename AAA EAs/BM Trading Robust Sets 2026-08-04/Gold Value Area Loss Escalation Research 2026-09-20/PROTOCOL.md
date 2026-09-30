# Gold Value Area: 1.5x loss escalation

Research-only chronological sizing replay. No EA, BAT, website default, or connected-account setting is changed.

Scope assumption pending user clarification: raw Gold Overnight Value Area, starting balance $10,000, base stop-risk target $50. Compare flat $50; $50 times 1.5 for each consecutive net losing trade; and the alternative interpretation of $75 after any loss until a win. A net win resets the next target to $50. A zero-net trade leaves the escalation state unchanged. Risk updates only after an actual close, never using a future outcome.

Use each independently recorded native MT5 period (6m/1y/3y/5y) and its original entry/exit sequence. Reset the account and risk state at each period start. Native fills already embed their spread/gap effects and the original 150 ms tester delay. Older history uses generated ticks; real ticks start January 2026. Preserve the source's known missing-session/late-close limitations.

Sizing comparisons:

- Ideal fractional volume: exact requested stop risk, to isolate the arithmetic rule.
- Broker-rounded volume: round up to the recorded 0.01-lot step/minimum, as in the approved raw EA. Use the recorded maximum lot limit. Actual planned stop loss can exceed requested risk. No silent risk cap or daily stop is added.

Scale recorded gross profit, commission and swap by new volume divided by original volume. Rounded-volume cash flows are rounded to account cents. This preserves observed costs proportionally, but does not rerun broker fee rounding, quote fills, liquidity, margin schedules or signal admission. Stress is separately labelled: add $0.25 per ounce in total execution cost and increase negative commission by 50%. Risk-state updates use the scenario's net result after costs.

Report closed-balance drawdown, not tick-equity drawdown. A separate initial-stop exposure envelope is a scenario bound at entry, not observed floating drawdown and not a guarantee against gaps. This is not an FTMO challenge/pass/payout simulation or a fresh MT5 risk-policy backtest. Existing production percent-risk website returns are context only; the fair rule comparison uses the same $50 base in every profile.

Preserve source JSON/report/run hashes, complete resized ledgers, monthly totals, full-window summaries and deterministic regression checks. No parameter optimization or selection by the best resulting return.
