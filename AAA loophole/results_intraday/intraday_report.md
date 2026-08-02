# Intraday Nasdaq Research — Sealed Test

## Result that matters: January 2026 through 2026-07-31

| Metric | Result |
|---|---:|
| Profit factor | 1.41 |
| Win rate on active days | 57.78% |
| Maximum daily-close drawdown | 4.16% |
| Trades | 45 |
| Active session days | 31.25% |
| Profitable days out of all sessions | 18.06% |
| Return at 0.5% risk/trade | 2.84% |
| Average trade | 0.126R |

## Locked rule

`opening_momentum_long_E12-48_S1.5_T2_HR11-11_MOVE0.5`

{
  "family": "opening_momentum",
  "direction": "long",
  "fast_ema": 12,
  "slow_ema": 48,
  "atr_stop": 1.5,
  "target_r": 2.0,
  "entry_start_hour": 11,
  "entry_end_hour": 11,
  "max_hold": 5,
  "rsi_period": 0,
  "rsi_threshold": 0,
  "breakout_lookback": 0,
  "opening_move_atr": 0.5
}

Only one trade is allowed per New York session. All positions are closed by the end of the regular U.S. session. Signals use a completed hourly bar and enter at the next hourly open.

## Experiment design

- 1404 predeclared intraday candidates.
- Development folds: April 2024–June 2025.
- Validation and final selection: July–December 2025.
- Sealed test: January 2026 onward.
- Costs: 1 NQ point of slippage per side plus 0.62 point round-trip commission equivalent.
- Same-bar stop/target ambiguity is resolved against the strategy: stop first.
- Risk normalization: 0.5% of current equity per initial stop.

| Segment | Trades | PF | Win rate | Max DD | Return |
|---|---:|---:|---:|---:|---:|
| Development | 93 | 1.57 | 59.14% | 1.92% | 9.22% |
| Validation | 29 | 1.91 | 62.07% | 1.02% | 3.72% |
| Sealed test | 45 | 1.41 | 57.78% | 4.16% | 2.84% |

At five times the modeled execution costs, sealed-test PF is 1.17.

The 5,000-sample trade bootstrap gives a 95% PF interval of 0.70–2.95; estimated probability PF > 1 is 81.96%.

## Interpretation

“Profitable every day” is not a valid promise. The useful figure is profitable days out of all available sessions, which includes no-trade days. Hourly Yahoo continuous futures data is suitable for a prototype, not live deployment: it cannot reproduce your broker's US100 spread, tick sequence, latency, financing, or order rejection. Paper-test the frozen rule on the exact execution feed before risking capital.
