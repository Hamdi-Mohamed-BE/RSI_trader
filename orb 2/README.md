# ORB Playbook Bot

This project implements the four setups in **The ORB Playbook — Mind Over
Markets**:

- Straight Break
- Break and Retest
- Liquidity Sweep
- Rejection Inside the Opening Range

The New York opening range is the first 15 minutes from 09:30 to 09:45 in
`America/New_York`. Entries use completed M5 candles. The optimizer compares
the four models, volume/body filters, H1 bias, retest windows, FVG confluence,
and 2R/3R exits. It selects settings using a 70% training / 30% later validation
split instead of choosing solely from the full sample.

## Start

1. Open MetaTrader 5 and log in to the intended account.
2. Run `backtest.bat` once. This writes `optimized_configs.json` and detailed
   files under `reports`.
3. Run `run.bat` to start the visible live scanner.

Live trading is disabled by default. To permit real or demo orders, set both:

```dotenv
ORB2_LIVE_TRADING=true
ORB2_PLACE_TRADES=true
```

The worker will only use symbols marked `enabled` by the latest optimization.
It limits each symbol to one idea per New York day, stops new entries after two
closed losses, moves the stop to break even at 1R, and exits remaining positions
at 16:00 New York time.

## Risk

`ORB2_RISK_PERCENT` is capped at 1% to follow the playbook. A positive
`ORB2_FIXED_LOT` acts as a lot ceiling; the worker reduces it when necessary to
stay inside the risk cap. When dynamic sizing produces less than the broker
minimum lot, the trade is skipped rather than exceeding the risk cap.

## Backtest Notes

- Historical broker spread and configured slippage are included.
- Commission and swap are not included.
- MT5 tick volume is a broker activity proxy, not centralized exchange volume.
- A same-candle stop/target conflict is counted as a stop.
- Results are research estimates, not a promise of future returns.
