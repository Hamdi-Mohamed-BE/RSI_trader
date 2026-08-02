# Asian Session Breakout

An MT5 research and execution project for the Asian-range breakout. It uses
UTC throughout and sizes each live order from its exact stop distance so the
planned loss is the configured percentage of the current MT5 balance.

## Deterministic rules

1. Build the Asian box from all M1 highs and lows between 00:00 and 08:00 UTC.
2. Compare its height with the prior 14-day Average Daily Range (ADR) and skip
   ranges outside the configured quality filter.
3. Test one of three entry models:
   - `mechanical_oco`: stops above and below the completed box.
   - `confirmed_close`: first completed M15 close beyond the buffered box.
   - `close_retest`: breakout close followed by a retest that closes back
     outside the boundary.
4. Use either the box midpoint or the opposite edge as the stop.
5. Test target distances from 0.5R through 6R.
6. Compare a fixed target with a bar-confirmed trailing stop. The trailing
   stop is activated only after a completed M1 bar reaches its start level,
   then becomes effective from the following bar to avoid look-ahead.
7. Allow one trade per symbol per day, cancel entries at 13:00 UTC, and close
anything still open at 17:00 UTC.

The live safety layer also blocks new strategy exposure once the configured
`MAX_BASKET_RISK_PCT` would be exceeded. For example, a 9% cap permits at
most three simultaneous 3% ideas.

The backtester includes recorded spread, assumes the stop was hit first if
both stop and target occur inside the same M1 candle, and compounds risk at 3%
of the current simulated balance. It does not use future candles to form the
box or entry.

## Run

```powershell
uv sync --extra dev
uv run pytest -q
uv run asia-breakout optimize --start 2026-05-29 --end 2026-07-29
uv run asia-breakout portfolio --start 2026-05-29 --end 2026-07-29 --scenarios 3:9,1:6,1:9
```

Reports are written under `reports/`. Cached MT5 M1 history is under `data/`.
The `portfolio` command replays the frozen per-symbol trades through one
shared, compounding account and rejects entries that would exceed each
scenario's exposure cap. It writes `reports/exposure_scenarios.csv` plus one
accepted/skipped-trade audit per scenario. Realized drawdown uses closed
portfolio equity; committed-risk drawdown is a conservative stress measure
that marks every open trade at its full planned loss simultaneously.
The deployable research choices are written to `configs/best_symbols.json`.
`configs/pf3_basket.json` contains only symbols whose selected in-sample
profit factor is at least 3.0. Set `SYMBOL_CONFIG_PATH` to that file and the
regular `backtest` command will apply each symbol's own entry, stop, target,
and trailing configuration.

The active high-risk deployment uses `configs/core4_basket.json`: BTCUSD,
EURJPY, GBPJPY, and XAUUSD at 3% risk per idea with a 6% basket cap. The broader
six-symbol `pf3_basket.json` and previous `core3_basket.json` remain available
for research and comparison.

Configuration files use canonical names such as `XAUUSD` and `BTCUSD`.
By default the bot attaches to the open, already logged-in MT5 terminal; no
account credentials are required in `.env`. After connecting, it reads the
broker's complete symbol catalogue and resolves canonical names to the
account's exact prefix/suffix convention.
`SYMBOLS` is optional and, when supplied, also uses canonical names.

`run_backtest.bat` runs the full optimization. `run_live.bat` starts one dry
run cycle. Live trading remains locked unless `DRY_RUN=false` and
`ENABLE_TRADING=true` are both set.

`run_forward_test.bat` starts the frozen one-month forward-test profile in
`.env.forward`. That profile uses the active core-three configuration at 3%
risk per idea with a 6% basket cap, writes separate records under
`logs/forward/`, and refuses to run unless the connected MT5 account is a demo
account. Keep the same configuration unchanged for the full test period so
the result remains genuinely out-of-sample.

## Logging and signal display

The live runner first prints the connected MT5 account type, server, currency,
leverage, balance, equity, free margin, floating P/L, and trading permission.
It then prints a strategy board showing the canonical
instrument, discovered broker symbol, entry model, actual execution method,
exit rule, risk, and whether the setup is automated or display-only.
Mechanical OCO signals also print an order board with the pending order type,
volume, entry, stop, target, cash risk, and order status.
Confirmed-close and close-retest models are rescanned once per completed M15
slot between the Asian close and entry cutoff. A signal is eligible only on
the immediately completed M15 bar; stale signals are ignored after restarts.
The runner checks the one-trade-per-symbol daily limit and basket exposure cap,
then sizes and sends the market order when live execution is enabled.

Trailing configurations keep their optimized fixed target as a hard cap. Once
a completed M1 candle reaches the configured activation distance, the live
manager advances the stop using the configured R distance. Stops only tighten.

Logs rotate daily and are retained for 90 days, which preserves a complete
one-month forward-test audit:

- `logs/asia-breakout.log`: readable operational log.
- `logs/events.jsonl`: structured events for later analysis.

Important events include MT5 connection state, symbol discovery, signal
generation, order validation, dry-run/placement results, basket-risk blocks,
OCO cancellation, exceptions, and a one-minute monitor heartbeat.

## Important live limitations

For mechanical OCO, the sibling order is cancelled as soon as a position is
detected, but a very fast two-sided spike can fill both legs before
cancellation. The two pending legs must therefore not be treated as risk-free.

The optimized basket is a research result, not a live guarantee. Most selected
symbols were selected on a recent two-month sample. The longer one-year report
shows substantial regime instability and must be reviewed before live use.
