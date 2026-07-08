# LTA A+ Trading Bot

Focused implementation of the original LTA Concepts strategy, plus one isolated research worker for the relative-volume U.S. equity ORB described below. LTA remains the primary bot; the new strategy has its own launcher, state, magic number, live switches, and backtester.

## Start

- `run_lta_bot.bat` starts the visible LTA automation worker.
- `stop_lta_bot.bat` stops that worker and clears its runtime lock.
- `run.bat` starts the LTA backtesting and scan page at `http://127.0.0.1:8000`.

## Lot Sizing

Select one execution mode in `.env`:

```env
# Fixed volume, normalized to the broker's min/max/step constraints.
LOT_SIZING_MODE=STATIC_LOT
STATIC_LOT=0.08

# Or size from the current MT5 balance and stop-loss distance.
# LOT_SIZING_MODE=RISK_PERCENT
MAX_LOT_RISK_PCT=5.0
```

The selected mode applies to both confirmed market entries and pre-placed pending orders. Static mode records estimated money risk when MT5 can calculate it. Risk-percent mode uses the current account balance and can use the broker minimum lot when the calculated volume is too small.

## Live Execution

Live market and pending orders require all three switches:

```env
LIVE_TRADING=true
AUTO_PLACE_TRADES=true
AUTO_PREPLACE_ORDERS=true
```

The current live `.env` uses static `0.01` lots and scans every five minutes. `.env.example` keeps live execution disabled and retains `0.08` as the default static-lot example.

`python -m app.watch_cycle` performs one lock-protected cycle and prints a compact status for thread monitoring. Optional `WATCH_REFERENCE_LEVELS` values provide screenshot context only; they never bypass the live `92+` pending-order gate.

## Retained LTA Behavior

- Completed-candle confirmation only.
- Market and pending retest entries.
- Pending orders require an A+ or PRE-A+ setup score of at least `92`.
- Spread-versus-stop validation.
- Direction-aware duplicate protection.
- Daily trade and loss circuit breakers.
- Weekend entry block.
- TP1 moves SL to break-even; later R milestones trail SL to the previous milestone.
- Persistent state under `reports/automation/` prevents duplicate entries after restart.

The browser page still supports LTA scans, historical backtests, cached MT5 candles, and report export. Legacy ORB, 20 Pip, BPR, Sniper, grid, trend, mean-reversion, DCA, arbitrage, news, and Telegram signaler workers do not remain in this folder. The paper-based relative-volume ORB worker documented below is the only separate strategy worker.

## Relative-Volume U.S. Equity ORB

`run_relvol_orb_bot.bat` starts the separate strategy from the Concretum Research paper *A Profitable Day Trading Strategy For The U.S. Equity Market*. It uses the direction of the first New York opening-range candle, a stop entry at that range's high or low, first-range relative volume versus the previous 14 sessions, a daily-ATR stop, and an end-of-day exit. `stop_relvol_orb_bot.bat` stops it.

The paper uses consolidated share volume. This MT5 broker exposes tick volume for its stock CFDs, so relative volume remains usable as an activity ratio but is explicitly a proxy. The paper's one-million-share filter is disabled because tick counts are not shares. Live switches are separate and disabled by default.

`RELVOL_ORB_DATA_TIMEZONE` must match the timestamps returned by the active MT5 terminal. It converts that feed to the 09:30-16:00 New York session without changing the main LTA data clock.

For the currently connected Exness account, the live `.env` uses UTC candle timestamps and separate optimized profiles: US100 (`60m`, `0.15` ATR, `0.75` RVOL), BTCUSD (`5m`, `0.15`, `0.75`), and ETHUSD (`15m`, `0.20`, `1.0`). The format is `SYMBOL:RANGE_MINUTES:ATR_STOP_FRACTION:MIN_RVOL`, separated by semicolons. The example file keeps the paper's stock defaults. Live switches remain disabled.

ORB sizing is independent from the main LTA sizing mode. Set `RELVOL_ORB_LOT_SIZING_MODE=RISK_PERCENT` to size from the stop and account balance, or use `STATIC_LOT` with `RELVOL_ORB_SYMBOL_LOTS=US100:0.01;BTCUSD:0.01;ETHUSD:0.10`. Static values are normalized to each broker symbol's minimum, maximum, and step, and their estimated risk is logged. The current live `.env` uses these static lots.

Run the 60-day walk-forward optimizer with:

```powershell
.\.venv\Scripts\python.exe -m app.relvol_orb_backtest --days 60 --balance 300
```
