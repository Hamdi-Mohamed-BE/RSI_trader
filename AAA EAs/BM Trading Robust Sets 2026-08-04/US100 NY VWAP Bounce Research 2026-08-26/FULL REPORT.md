# US100 New York VWAP Bounce — native MT5 validation

Research date: 2026-08-26

## Verdict

**REJECT FOR THE ACTIVE BAT.** The literal transcript and the training-selected variant are shown separately below. Selection used training and validation only; the latest year was not used to tune the parameters.

## Native MT5 results

| Version | Segment / model | Return | PF | Win rate | Equity DD | Trades | Quality |
|---|---|---:|---:|---:|---:|---:|---:|
| Screen-selected | Training / 1-minute OHLC | -16.83% | 0.92 | 35.56% | 28.91% | 329 | 98% |
| Screen-selected | Validation / 1-minute OHLC | +35.53% | 1.50 | 47.20% | 13.99% | 125 | 98% |
| Screen-selected | Locked / Every Tick | +2.29% | 1.04 | 39.08% | 9.28% | 87 | 100% |
| Screen-selected | Latest year / Every Tick | +4.43% | 1.09 | 40.24% | 8.66% | 82 | 100% |
| Screen-selected | Full / 1-minute OHLC | +14.14% | 1.04 | 38.75% | 29.78% | 542 | 98% |
| Literal transcript | Training / 1-minute OHLC | -13.70% | 0.56 | 74.22% | 15.58% | 128 | 98% |
| Literal transcript | Validation / 1-minute OHLC | +3.92% | 1.32 | 81.97% | 3.94% | 61 | 98% |
| Literal transcript | Locked / Every Tick | -3.50% | 0.86 | 62.12% | 6.80% | 66 | 100% |
| Literal transcript | Latest year / Every Tick | -1.70% | 0.93 | 62.71% | 6.80% | 59 | 100% |

## Exact versions

- Literal transcript: 30-minute ORB; price must first extend beyond the ORB, then make its first VWAP pullback; directional rejection candle; rejection-candle stop; target the prior extension extreme.
- Screen-selected: 15-minute ORB; first VWAP pullback; open and close stay on the trend side of VWAP; EMA20/EMA50 trend filter; stop at 0.25 times the median prior 20 New York-session ranges; 2R target.
- Both: New York VWAP anchored at 09:30; 90-minute setup window; one trade per session; flat at 15:55 New York; automatic US DST; 1% equity risk.

## Test controls

- Exness USTEC, $10,000 initial balance, 1:2000 leverage.
- Native MT5 commission, swap and spread are included; random execution delay is enabled.
- Same-session signals are evaluated only after a candle closes; entries occur on the following tick.
- The Python screen charged an extra 2.0 US100 points round-trip and resolved ambiguous stop/target bars stop-first.

## Volume limitation

Exness USTEC exposes broker tick activity, not centralized Nasdaq futures exchange volume. Its anchored VWAP is therefore a CFD tick-activity proxy. True CME volume validation would require NQ futures data.

## Deployment decision

The active BAT, active presets and website were not changed by this research run.
