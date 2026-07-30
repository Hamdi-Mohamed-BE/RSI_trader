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
   - Observe the first 45 minutes from 13:30 UTC.
   - Place only a buy stop or sell stop 2.5 median spreads beyond that range.
   - The target is 4R.
   - The stop goes beyond the opposite side plus 7.5% of the Asia range,
     subject to the minimum spread-based protection.
   - The pending order expires at 16:00 UTC.
4. A pre-entry regime gate accepts trades only when:
   - prior five-session ATR is 1.5%-2.8% of the prior close; and
   - today's Asia range is 0.40-1.20 times its prior 20-session median.
   Both inputs use only information available before the New York entry.
5. The single active leg risks at most 3% of current equity. Lot size is
   rounded down to the broker step; the order is skipped if the minimum lot
   would exceed the risk cap.
6. At +0.30R, its stop advances to +0.15R.
7. Remaining trades close at 21:00 UTC.
8. Backtests use M1 broker history and historical spread. Ambiguous candles are
   evaluated pessimistically: stop first.

## Run

```powershell
cd "C:\Users\hama101\Desktop\geek\ai trader\AMD"
uv sync
uv run amd-bot backtest --days 60
```

Or double-click `run_backtest.bat`.

`run_live.bat` starts live execution when `.env` contains
`ENABLE_TRADING=true` and `DRY_RUN=false`.

Live safeguards:

- auto-connects to the MT5 account that is already open;
- discovers the broker's XAU symbol;
- tries broker-compatible RETURN, IOC, and FOK filling modes;
- never chases a stop trigger that was crossed while the bot was offline;
- loads sufficient prior history and applies the same regime gate as backtests;
- prevents another bot order after an order, position, or deal exists that day;
- cancels pending orders at 16:00 UTC;
- advances the stop according to the configured R rule;
- force-closes remaining bot positions at 21:00 UTC;
- never modifies manual trades or orders with a different magic number.

## Chart overlay

Paste `tradingview/AMD_Asia_Range.pine` into TradingView's Pine Editor. It:

- shades the 00:00-08:00 UTC Asia accumulation range;
- extends the full-wick Asia high and low;
- shades the London confirmation and New York execution windows;
- labels the London H1 close-above/close-below conditions;
- exposes TradingView alert conditions for both London setups.
