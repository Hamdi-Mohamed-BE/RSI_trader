# LTA Safe Micro Gold — QuantConnect

This project ports the locked **LTA baseline-safe XAU configuration** to
QuantConnect's continuous Micro Gold future (`MGC`). It is a fidelity port,
not a new optimization.

## Locked configuration

- Signal instrument: continuous Micro Gold future
- Execution instrument: currently mapped front contract
- Signal timeframe: 15 minutes
- Structure timeframe: 1 hour
- Supply/demand timeframe: 4 hours
- Macro timeframe: daily
- Volume profiles: previous day and previous week
- Profile construction: 64 price bins and 70% value area
- Entries: EM1 Double Wick and EM4 Continuation
- Direction: momentum only, long and short
- Safe mode: completed-daily-bar, no-lookahead Markov gate
- Reward/risk target: 3R
- Maximum risk: 1% of current portfolio equity per trade
- Daily consecutive-loss gate: 2
- Sessions: all day

## MT5-to-QuantConnect mapping

MT5's XAUUSD CFD does not publish centralized exchange volume and therefore
the EA falls back to broker tick volume. This QuantConnect version uses actual
traded volume from CME Micro Gold bars. The POC/VAH/VAL construction remains
the same bar-volume approximation: each bar's volume is distributed evenly
over every price bin touched by that bar.

The continuous contract supplies stable research signals. Orders are sent to
the mapped tradable contract. Open LTA positions are closed at a contract
rollover rather than carried across it.

## Validation status

- Python syntax validation: passed
- Locked safe-mode constants checked against the MT5 `.set`: passed
- Warm-up covers the full 220-bar H4 zone lookback
- Protective stop and target are created from the actual entry fill
- QuantConnect cloud compilation: passed on LEAN 2.5.0.0.18057
- First cloud backtest: completed over the available 7 Sep 2025–10 Jun 2026
  MGC history (5,960,206 data points)
- First-run result: -0.945% net, 0.900% drawdown, one completed losing trade,
  $9.12 fees, and $99,054.88 ending equity from $100,000
- This is a migration smoke test, not optimization evidence. The single-trade
  sample is too small to approve this port for live or demo deployment.
- Local Docker backtesting is intentionally unavailable because Docker/WSL
  was removed from this computer
