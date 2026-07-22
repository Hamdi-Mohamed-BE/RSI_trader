# News Impulse Straddle Bot

Demo-first MT5 bot for scheduled high-impact news moves on gold.

Core idea:

1. Just before a news release, read the last closed 1-minute candle.
2. Place a buy stop above that candle high and a sell stop below that candle low.
3. If one side triggers, cancel the other side.
4. Let the triggered side breathe; no early breakeven by default.
5. Trail only after a large runner move, then close after max hold time.
6. Cancel unfilled orders after a short timeout.

This is designed for CPI / NFP / FOMC-style impulse candles. It is not meant to run on every small news release.

## Files

- `news_straddle_bot.py` — live/demo MT5 execution bot. Dry-run unless `--execute` is passed.
- `backtest_news_straddle.py` — backtests and optimizes parameter combinations.
- `news_events.py` — scheduled event list used for backtesting.
- `config.best.json` — generated best config after optimization.
- `backtest_results.csv` — generated ranked backtest results.
- `BACKTEST_REPORT.md` — generated readable report.

## Run backtest

```powershell
cd "C:\Users\hama101\Desktop\geek\ai trader\news-impulse-straddle"
python .\backtest_news_straddle.py
```

## Dry run the bot

Example using New York news time:

```powershell
python .\news_straddle_bot.py --news-time "2026-07-15 08:30" --dry-run
```

## Live/demo execution

Only use this on demo first:

```powershell
python .\news_straddle_bot.py --news-time "2026-07-15 08:30" --execute
```

The bot will not trade without `--execute`.

The bot expects New York time by default, converts it to UTC internally, waits until the last closed M1 setup candle is available, then places the two pending orders.

## Current optimized demo profile

Loaded from `.env`, with `config.best.json` as fallback:

- XAU only: `XAUUSDm`
- News timezone: `America/New_York`
- Fixed lot: `0.10`
- Entry buffer: `$12` above/below the last closed M1 candle
- SL room: opposite side of candle + `$20`
- Max setup candle range: `$8`
- No fixed TP
- No early breakeven
- Trail starts at `+7R`
- Trail distance: `1R`
- Max hold: `120` minutes

This is aggressive. On a `$500` account, fixed `0.10` lot can risk a large part of the account per trade.

To change the live defaults, edit `.env`.
