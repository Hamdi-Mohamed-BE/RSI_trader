# News Impulse Straddle Backtest Report

Symbol: `XAUUSDm`
Events loaded: `22`

## Best config

```json
{
  "symbol": "XAUUSDm",
  "event_filter": "tier1_pce",
  "setup_candle_minutes_before": 1,
  "buffer_points": 5.0,
  "sl_extra_points": 10.0,
  "tp_r": 3.0,
  "be_at_r": 1.0,
  "trigger_window_minutes": 1,
  "max_hold_minutes": 30,
  "max_setup_range_points": 12.0,
  "entry_slippage_points": 1.0,
  "exit_slippage_points": 1.0,
  "same_bar_policy": "skip"
}
```

## Best config stats

- Trades: `8`
- Total R: `3.42R`
- Average R/trade: `0.43R`
- Win rate: `37.5%`
- Profit factor: `4.42`
- Max drawdown: `1.00R`
- Objective score: `4.57`

## Trade-by-trade result

| event                 | event_type   | status     | side   |         r |   setup_range |
|:----------------------|:-------------|:-----------|:-------|----------:|--------------:|
| Apr 29 FOMC Statement | FOMC         | timeout    | sell   |  0.445603 |         2.56  |
| May 08 NFP / Jobs     | NFP          | loss       | sell   | -1        |         1.989 |
| May 12 CPI            | CPI          | no_trigger | nan    |  0        |         1.642 |
| May 20 FOMC Minutes   | FOMC         | no_trigger | nan    |  0        |         1.695 |
| May 29 PCE            | PCE          | no_trigger | nan    |  0        |         2.649 |
| Jun 05 NFP / Jobs     | NFP          | timeout    | sell   |  2.58771  |         2.416 |
| Jun 10 CPI            | CPI          | be         | buy    |  0        |         5.052 |
| Jun 17 FOMC Statement | FOMC         | be         | sell   |  0        |         1.375 |
| Jun 25 PCE            | PCE          | timeout    | buy    |  1.38267  |         5.45  |
| Jul 02 NFP / Jobs     | NFP          | be         | buy    |  0        |         2.552 |
| Jul 08 FOMC Minutes   | FOMC         | no_trigger | nan    |  0        |         2.103 |
| Jul 14 CPI            | CPI          | be         | buy    |  0        |         2.606 |

## Important notes

- This is a 1-minute OHLC simulation, not tick-perfect execution.
- News slippage is modeled with adverse entry and exit slippage.
- If both stop orders are touched in the same 1-minute candle, the default policy skips that event.
- Demo forward testing is required before risking real money.