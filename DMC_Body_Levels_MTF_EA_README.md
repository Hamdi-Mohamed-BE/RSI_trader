# DMC Body Levels MTF EA

File:

`DMC_Body_Levels_MTF_EA.mq5`

This EA is an MT5 implementation of the DMC body-level idea from the TradingView script.

## What It Builds

It scans completed candles from:

- Monthly
- Weekly
- Daily
- 4H
- 1H

For every candle it marks:

- body top: `max(open, close)`
- body bottom: `min(open, close)`

Each level is classified:

- `VIRGIN`: not touched yet
- `TESTED`: wick touched it, body did not pass through
- `PASSED`: body crossed through it or price gapped through it

Merged levels from multiple timeframes show confluence.

## Entries

Entries are evaluated only on closed `M15` candles by default.

Buy setups:

- `FAIL_LOW`: price touches the nearest virgin level below and rejects upward.
- `GAIN`: candle body closes through the nearest virgin level above.

Sell setups:

- `FAIL_HIGH`: price touches the nearest virgin level above and rejects downward.
- `LOSE`: candle body closes through the nearest virgin level below.

## Important Defaults

- `InpEnableTrading=false`
- Drawing is enabled.
- Fixed lot default is `0.01`.
- Entry timeframe default is `M15`.

Turn `InpEnableTrading=true` only after backtesting/demo testing.

## Target Logic

`TARGET_NEXT_LEVEL` tries to target the next virgin DMC level.

If no valid next level exists, it falls back to fixed RR using `InpRewardRisk`.

## Install

Copy `DMC_Body_Levels_MTF_EA.mq5` into:

`MQL5/Experts/`

Then compile in MetaEditor and attach it to the chart.
