# Opening-range breakout: frozen raw protocol

Frozen 2026-10-02 before these runs. First tier-list idea only. User requested stop and show raw results if the raw gate fails. No optimisation, website promotion, portfolio integration or active-terminal changes.

## Strategy

- Broker CFD proxies: Nasdaq 100 = USTEC; S&P 500 = US500, isolated Exness research terminal. This is not a replication of a broad stocks-in-play strategy or an exchange-volume study.
- New York session, US daylight-saving dates applied to UTC broker history. Build the range from the three completed M5 bars starting 09:30, 09:35 and 09:40 NY. All three must exist on that date.
- The first subsequent completed M5 candle closing strictly outside the range is the day's only entry attempt. The earliest signal bar opens 09:45 and completes 09:50. Market entry on the next available tick; never enter on an unfinished signal candle.
- Long stop at range low; short stop at range high. No take-profit, trailing, breakeven, trend/volume/news/range filter or re-entry. At most one position per symbol. Exit requested from 15:55 NY; missed closures retried on tradable ticks, no fictional fill when market is closed. No new entry at/after 15:55 NY. Holiday closures can cause carryover; count and disclose them.
- $10,000 USD per independent symbol run; target risk 1% of current BALANCE at entry, lots rounded DOWN. Skip if below minimum; never force minimum lot or widen stop. Costs and gaps can exceed planned stop risk. Leverage 1:2000 is the research broker setting, not FTMO.
- Windows end exclusively 2026-10-02: 1 year from 2025-10-02, 3 years from 2023-10-02, 5 years from 2021-10-02. Native tick model 4, 150ms execution delay, native broker spreads/commission/swaps. Older history may use generated ticks: disclose fresh tester journal coverage. No invented extra-cost stress.
- Exactly one strategy configuration, six symbol/window runs; overlapping periods are not independent confirmations. No data-driven parameter selection. Five-minute / thirty-minute opening ranges postponed pending review.

## Raw gate and evidence

Show both 3-year and 5-year results. Preliminary raw profitability gate requires both net return >0, trade-net PF >1 and at least 30 closed trades. Preferred PF >=1.2 is an additional user screen, not a promise. Passing a raw gate is NOT pipeline completion: deflated Sharpe, block bootstrap, chronology, adverse execution, untouched configuration holdout and forward demo would still be required. Failing the raw gate stops this idea for review; no exploratory optimisation is authorised.

Show full-year results, native floating-equity drawdown, closing-trade balance curves, trade-net win rate/PF/streaks, and daily closed-balance Sharpe (365-day annualisation, flat weekends included). Broker's native Sharpe is separate. This is historical research on already-used market history, not a pristine unseen dataset. Do not infer expected income or FTMO pass/payout rates.

## Safety and reproducibility

EA OnInit rejects non-tester attachment. Only the existing isolated portable research terminal is launched, with explicitly empty profile and live Expert flags disabled. Account-bound INI and raw journals remain local/ignored. Freeze source/settings hashes, verify native report inputs, reconcile report trades/net P&L, retain diagnostics and broker specs. No trading API connection or orders, Git push or install to a normal terminal.
