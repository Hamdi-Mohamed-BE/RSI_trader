# LTA A+ Trading Bot

Focused implementation of the original LTA Concepts strategy. The project contains one strategy only: LTA volume-profile levels, market-structure confirmation, A+ scoring, pending retest entries, live MT5 execution, and progressive stop protection.

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

The current live `.env` uses static `0.08` lots. `.env.example` keeps live execution disabled.

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

The browser page still supports LTA scans, historical backtests, cached MT5 candles, and report export. No ORB, 20 Pip, BPR, Sniper, grid, trend, mean-reversion, DCA, arbitrage, news, or Telegram signaler workers remain in this folder.
