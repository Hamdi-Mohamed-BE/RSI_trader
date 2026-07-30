# AMD Session Bot

An MT5 research implementation of the requested
Accumulation-Manipulation-Distribution routine.

## Rules implemented

1. Accumulation: Asia range is the full wick high/low from 00:00-08:00 UTC.
2. London directional reference:
   - Aggregate the 08:00-09:00 UTC candle.
   - A close above the Asia high establishes a London-up reference.
   - A close below the Asia low establishes a London-down reference.
   - No London trade is placed.
3. New York distribution/reversal:
   - Direction must be opposite the London reference.
   - Rest a liquidity-limit order during the first 45 minutes from 13:30 UTC.
   - If the limit does not fill, cancel it and replace it with a buy stop
     above or sell stop below that 45-minute range.
   - The limit target is 5R and the replacement stop target is 4R.
   - The stop buffer is 5% of the Asia range, subject to the minimum
     spread-based protection.
   - The pending order expires at 16:00 UTC.
4. The single active leg risks 3% of current balance.
5. At +0.50R, its stop advances to +0.15R.
6. Remaining trades close at 21:00 UTC.
7. Backtests use M1 broker history and historical spread. Ambiguous candles are
   evaluated pessimistically: stop first.

## Run

```powershell
cd "C:\Users\hama101\Desktop\geek\ai trader\AMD"
uv sync
uv run amd-bot backtest --days 60
```

Or double-click `run_backtest.bat`.

`run_live.bat` currently starts a dry-run scanner. Real order submission is
intentionally locked until the strategy passes forward validation.

## Chart overlay

Paste `tradingview/AMD_Asia_Range.pine` into TradingView's Pine Editor. It:

- shades the 00:00-08:00 UTC Asia accumulation range;
- extends the full-wick Asia high and low;
- shades the London confirmation and New York execution windows;
- labels the London H1 close-above/close-below conditions;
- exposes TradingView alert conditions for both London setups.
