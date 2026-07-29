# EMA3 Pivot Reversal Backtest

This project reproduces the trade-producing portion of the supplied
TradingView indicator on XAUUSD H4.

The EMA 8/20/200 and Bollinger Band plots are visual only. Buy labels come
from a six-left/six-right pivot low and Sell labels from an equivalent pivot
high. Because a pivot is unknowable until its six right-hand candles close,
the backtest recognizes it on the sixth later close and executes at the next
H4 open. An opposite signal closes and reverses the position.

The default report uses the most recent 30 days, a $1,000 starting balance,
and a fixed 0.10 lot. Historical spread is included. The final open trade is
closed at the final completed H4 candle solely to calculate the test result.

```powershell
uv sync
uv run ema3-backtest
```

Outputs are saved under `reports/`.

## Live MT5 bot

The live worker follows the single-leg version shown in the 30-day report:

- automatically finds the connected broker's tradable gold symbol;
- reads H4 candles and confirms a six-left/six-right pivot without look-ahead;
- enters only near the next H4 open after confirmation;
- sizes one position so its structural-stop loss is at most 3% of live equity;
- places the stop at the confirmed pivot low for Buy or pivot high for Sell;
- closes and reverses it when the opposite pivot is confirmed;
- manages only positions carrying its own magic number.

It uses the MT5 terminal and account that are already open and connected. No
login, password, server, or terminal path is stored in `.env`.

The supplied `.env` is configured with `LIVE_TRADING=true`. Starting the
worker can therefore place and close orders. To observe without execution,
change it to `false`.

```powershell
uv run ema3-live
```

or double-click `run_live_bot.bat`.

The screenshot's PF 3.18 result used one leg. Setting
`MAX_SAME_DIRECTION_LEGS=2` enables the requested consecutive-signal add-on,
but it is not the safe default because the one-year double-down test failed.

## Exit and multi-symbol optimization

`.env` defines the broker-independent symbol universe and research settings.
The optimizer tests fixed targets from 1R through 5R plus bar-confirmed
trailing stops. The structural stop is the confirmed pivot low for buys and
pivot high for sells.

Consecutive signals in the same direction pyramid up to
`MAX_SAME_DIRECTION_LEGS`. The default is two: a second Sell opens a separate
second short leg, and a second Buy does the same for longs. Each leg keeps its
own entry, pivot stop, target, and trailing state.

The first 75% of the one-year history selects one exit configuration per
symbol. That frozen selection is then measured on the final, unseen 25%.
Only positive validation configurations with PF of at least 1.20 enter the
normalized 1%-risk, 3%-exposure portfolio comparison.

```powershell
uv run ema3-optimize
```
