# US100 New York Session Strategy Specification

All session rules use `America/New_York`; conversion to UTC/MT5 time is DST-aware.
Only closed candles are used. One strategy pip defaults to **1.0 US100 index price unit**.

## Strategy A

At the first tradable tick from 09:30:00 through 09:30:59 New York time, submit two
SELL positions. Their combined initial loss at the shared 50-pip stop equals the
configured strategy risk.

- `A_FIXED`: 50-pip stop and 100-pip target.
- `A_RUNNER`: 50-pip initial stop, no target. At each new M15 bar, the stop may
  move to the high of the M15 bar that just closed, plus the configured buffer.
  The stop only tightens. The unfinished candle is never read.

The baseline forced exit is 15:55 New York time.

## Strategy B

The reference candle is 09:15-09:30. The decision candle is 09:45-10:00.
Evaluation occurs only after 10:00.

- `B1`: if the decision candle closes green, SELL at the first valid post-10:00
  price. Baseline stop is the London-session high through 10:00 plus a buffer;
  target is 2R.
- `B2`: if it closes red, place a SELL LIMIT 50 strategy pips above that close.
  Baseline stop is 100 pips and target is 2R. It expires at 12:00 or is
  invalidated if price reaches the stop before entry.
- A body smaller than `DOJI_BODY_PIPS` produces no trade.

## Execution and safety

The bot persists daily execution state, filters non-trading/shortened sessions,
validates spreads and stop distances, sizes from broker tick value, and tries the
broker-supported filling modes. Live trading requires both `ENABLE_TRADING=true`
and `DRY_RUN=false`; default is safe signal-only mode.

## Backtest model

Broker M1 bid OHLC and each bar's historical spread are used. Short exits are
tested against reconstructed ask prices. Same-minute ambiguity is resolved
pessimistically (stop before target). M1 data cannot prove tick ordering or
1/2/5/10-second delay sensitivity; the report states this limitation.

