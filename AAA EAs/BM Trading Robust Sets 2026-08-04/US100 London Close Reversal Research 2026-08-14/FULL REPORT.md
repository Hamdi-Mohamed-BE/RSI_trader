# US100 London-Close Reversal — Research Report

Date completed: 2026-08-14  
Decision: **REJECT for active deployment**

## Strategy tested

- Instrument: MEXAtlantic `UT100` CFD (US100/Nasdaq 100)
- Signal chart: M15
- Observe the M15 candle ending at the selected London-clock close time.
- If its net body is bullish, enter short; if bearish, enter long.
- One entry at most per London trading day.
- Position size compounds at 1% of current equity per initial stop.
- Move the stop to entry after price reaches +1R.
- Exit any remaining position after the selected maximum holding time.

The phrase “50 pips” was implemented as **50.00 US100 index price points**. On this two-decimal broker symbol that is 5,000 quote ticks (`SYMBOL_POINT = 0.01`). Calling 50 quote ticks “50 pips” would mean only 0.50 index points and would be smaller than the typical spread, so that interpretation was rejected.

## Data and execution assumptions

- Broker history: MEXAtlantic-Demo `UT100` M1
- Period: 2022-01-02 through 2026-08-07
- Rows: 1,617,498 one-minute bars
- Quote precision: 0.01; median recorded spread: 1.70 index points
- London time is converted with Europe/London daylight-saving rules.
- Each market fill includes the recorded bid/ask spread plus 0.50 index point adverse slippage.
- If stop and target are both reachable inside the same M1 bar, the stop is assumed first.
- Starting balance: $10,000; risk: 1% of current equity per trade.
- This is a deterministic recorded-spread M1 research backtest, not a guarantee and not a native MT5 real-tick confirmation.

## Parameter search

11,664 combinations were evaluated across:

- London close: 16:00, 16:30, 17:00
- Candle lookback: 1, 2, 4 M15 candles
- Minimum net body: 0, 10, 25, 50 index points
- Stop: 25, 35, 50, 75, 100, 150 index points
- Reward:risk: 1.00, 1.25, 1.50, 2.00, 2.50, 3.00
- Maximum hold: 90, 180, 360 minutes
- Management: fixed exit, break-even at 1R, or trailing after 1.5R

Selection used only 2022–2025 calendar-year results. The chosen configuration had positive returns and PF at least 1.02 in every development year. It was then frozen and checked on 2026.

## Selected configuration

| Parameter | Selected value |
|---|---:|
| London candle close | 17:00 London time |
| M15 candles measured | 1 |
| Minimum candle body | 25 index points |
| Direction | Opposite the candle body |
| Stop distance | 50 index points |
| Target | 2R = 100 index points |
| Break-even | At +1R |
| Maximum hold | 90 minutes |
| Risk | 1% of current equity |

## Locked-period results

| Period | Trades | Wins / losses | Win rate | PF | Return | Max equity DD | Final balance |
|---|---:|---:|---:|---:|---:|---:|---:|
| Development 2022–2025 | 347 | 145 / 202 | 41.79% | 1.28 | +42.31% | 15.79% | $14,231.33 |
| Confirmation 2026-01-01–2026-08-07 | 71 | 19 / 52 | 26.76% | 0.77 | -9.30% | 17.77% | $9,070.16 |
| Full 2022–2026 | 418 | 164 / 254 | 39.23% | 1.16 | +29.08% | 17.77% | $12,908.04 |

## Development years

| Year | Trades | Win rate | PF | Return | Max DD |
|---|---:|---:|---:|---:|---:|
| 2022 | 84 | 39.29% | 1.35 | +11.31% | 6.84% |
| 2023 | 61 | 49.18% | 1.34 | +6.97% | 4.17% |
| 2024 | 90 | 44.44% | 1.20 | +6.96% | 9.13% |
| 2025 | 112 | 37.50% | 1.26 | +11.75% | 15.79% |

## Verdict

The original 50-point stop and 1:2 target were, in fact, the most stable development choice once a 25-point body filter, 17:00 London timing, break-even at 1R, and a 90-minute time exit were added. However, the edge did not survive the newest confirmation period: PF fell below 1.0, the strategy lost 9.30%, and drawdown reached 17.77% in only a little over seven months.

The EA is therefore saved with `InpEnableTrading=false`, is not copied into the active MT5 portfolio, and is not added to `INSTALL AND RUN ON ACTIVE MT5.bat`. Treat it as research only unless a new rule is developed on older data and passes a truly unseen forward period.

## Files

- `US100 London Close Reversal Research EA.mq5` — transparent source code
- `US100 London Close Reversal Research EA.ex5` — compiled EA (0 errors, 0 warnings)
- `REJECTED RESEARCH - US100 M15 London 1700 - 50 stop 2R - 1pct.set` — selected inputs, disabled
- `Results/walkforward-equity.png` — equity curve with 2026 boundary
- `Results/walkforward-confirmation.json` — exact aggregate statistics
- `Results/walkforward-selected-trades.csv` — all selected-config trades
- `Results/walkforward-screen-2022-2025.csv` — full parameter screen
- `backtest_london_close.py` — reproducible research backtest
