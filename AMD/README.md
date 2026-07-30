# AMD Session Bot

An XAUUSD MT5 implementation of two mechanical
Accumulation-Manipulation-Distribution models.

## Recommendation

The article-aligned model at 3% risk is the protected default in `.env`.
Execution remains disabled and dry-run protected while it is forward tested.
XAUUSD remains the only default symbol because the cross-asset validation did
not justify adding another market.

The selective legacy model remains the stronger historical reference because
it produced better return, profit factor, and drawdown in the same one-year
broker sample.

| Model at 10% risk | Trades | Win rate | PF | Net R | Return | Realized DD |
|---|---:|---:|---:|---:|---:|---:|
| Selective legacy reference | 12 | 91.67% | 9.87 | +13.95R | +226.16% | 10.00% |
| Article-aligned higher frequency | 67 | 85.07% | 1.76 | +10.70R | +150.66% | 21.47% |

The higher-frequency model generated 5.6 times as many trades, but its edge was
weaker. At the more balanced 3% risk, it produced PF 1.97, +35.94% return, and
6.66% realized drawdown.

Past results are not a guarantee. The article provides testable behavior, not
proof of a profitable edge.

## Selective live model

Selected by setting `STRATEGY_MODEL=legacy`:

1. Build the full-wick Asia range from 00:00-08:00 UTC.
2. Require the 08:00-09:00 London H1 candle to close outside the range.
3. Trade only the opposite-side New York expansion after its first 45 minutes.
4. Apply the recent-volatility and Asia-range regime filter.
5. Target 4R; at +0.30R, move the stop to +0.15R.
6. Expire unfilled orders at 16:00 UTC and close remaining positions at 21:00.

## Higher-frequency article model

Selected by `STRATEGY_MODEL=article` in `.env`:

1. Accumulation is the full-wick Asia range from 00:00-08:00 UTC.
2. Scan completed M5 candles during the first four hours of London.
3. A manipulation fade requires a wick beyond the range and a close back
   inside. The sweep must be 2%-60% of the Asia-range height.
4. A distribution continuation requires an M5 close outside the range,
   pullback to its edge, and directional M5 close that holds the edge.
5. Enter on the next minute, never inside the confirmation candle.
6. Target 1.5R; at +0.30R, move the stop to +0.15R.
7. Keep the regime filter and take at most one setup per day.

The one-year research was separated chronologically into 60% train, 20%
validation, and 20% final test. The chosen active candidate was stable across
the segments, including 27 trades, PF 1.91, +5.05R, and 4.20% realized
drawdown in the final segment at 3% risk. That segment has now been reviewed,
so the next meaningful evidence must come from forward testing.

The 85.07% full-year win rate includes 48 small +0.15R protected-stop exits,
9 full +1.5R targets, and 10 full -1R stops.

## Run

Backtest the protected default:

```powershell
cd "C:\Users\hama101\Desktop\geek\ai trader\AMD"
uv sync
uv run amd-bot backtest --days 365
```

Backtest the separate article forward-test profile:

```powershell
uv run amd-bot backtest --env .env.article --days 365
```

Forward-test the article model without placing orders by double-clicking
`run_article_forward.bat`. Its profile has `ENABLE_TRADING=false` and
`DRY_RUN=true`.

`run_live.bat` uses `.env`, which now selects Expanded AMD at 3% risk with
`ENABLE_TRADING=false` and `DRY_RUN=true`.

## Live safeguards

- auto-connects to the account already open in MT5;
- dynamically discovers the broker's XAU symbol;
- tries broker-compatible RETURN, IOC, and FOK filling modes;
- sizes volume down to the broker step without exceeding configured risk;
- article signals use completed M5 candles and expire after 120 seconds;
- permits at most one bot trade per day;
- advances stops using the same R rule as the backtest;
- force-closes remaining bot positions at 21:00 UTC;
- never modifies manual trades or orders with another magic number.

## Reports

- `reports/REPORT.md`: current selective-model backtest.
- `reports/ARTICLE_REPORT.md`: higher-frequency article-model backtest.
- `reports/CROSS_ASSET_VALIDATION.md`: exact and normalized basket comparison.
- `reports/article_research/robust_search.csv`: parameter comparison.
- `reports/article_research/robust_winner.json`: chronological selection audit.
