# DmC pullback bot

This project converts the supplied DmC video descriptions into explicit rules that can be audited and backtested.

1. Aggregate the previous completed New York calendar day and determine its candle direction.
2. Build the four-hour candle ending at 09:30 New York time.
3. Require the daily and four-hour candle to agree and pass the configured body-quality filters.
4. Compare the final two closed H1 candles into the New York open. A body close through the prior body is a gain; a wick through it followed by a close back inside is a failure.
5. Only keep an H1 gain/failure that agrees with the D1/H4 direction, then place a limit order at the body level for the retest.
6. Use the instrument profile for the initial stop: 45 index points on US100 or $22.50 on gold. When enabled, start trailing after +1R with a 0.5R distance.
7. Close any remainder after 24 hours.
8. Allow at most three filled trades per ISO week.

The code also contains disabled research variants for reactions at completed daily/weekly/monthly candle-body levels, structural H1 stops, and targets at the next body level. They are not the default because this broker's available Nasdaq contract history produced too few qualifying trades to validate them.

Latest broker-history comparison (NAS100U6, 15 June to 31 July 2026, historical spread included, 2% risk):

| Version | Trades | Win rate | PF | Net R | Realized DD | Intratrade DD |
|---|---:|---:|---:|---:|---:|---:|
| Original fixed pullback | 9 | 55.56% | 1.07 | +0.24R | 3.96% | 4.21% |
| H1 gain/failure body retest | 8 | 50.00% | 2.49 | +5.96R | 3.96% | 5.67% |

Both chronological halves of the improved sample were positive (+2.99R and +2.97R). This is encouraging but still only eight trades from a short futures-contract history, so it must be forward-tested and is not proof of a durable edge.

The generic `US100` symbol is automatically resolved to the connected broker's tradeable Nasdaq-100 alias. The live worker uses the account already connected in the open MetaTrader 5 terminal; no login or password is stored.

Gold is enabled through the same D1/H4 plus H1 body-retest logic. `XAUUSD` is automatically resolved to the connected broker's gold alias. The current base risk is 0.5%; the portfolio ceiling remains controlled by `MAX_TOTAL_RISK_PCT`.

Latest gold broker-history result (XAUUSD.., 3 February to 31 July 2026, historical spread included, 2% compounded risk):

| Trades | Win rate | PF | Net R | Return | Realized DD | Intratrade DD |
|---:|---:|---:|---:|---:|---:|---:|
| 21 | 61.90% | 3.55 | +20.49R | +47.52% | 4.00% | 5.62% |

The final two-month validation segment produced 10 trades, +5.20R and PF 2.03. July alone was -0.60R, so this is not a claim that every month will be profitable. See `reports/GOLD_APPLICATION.md` for the monthly breakdown and limitations.

`run_backtest.bat` runs a 60-day research test. `run_live.bat` starts the live-enabled worker and may place orders because `.env` contains the explicit live unlock.

## Risk progression and the 1.7R ceiling

- `RISK_PCT=0.5` is the base risk.
- `RISK_PROGRESSION_ENABLED=false` keeps live trading flat-risk by default.
- When enabled, each closed loss changes the next risk to `base * 1.6 ^ loss_streak`; a closed win resets it. Flat results preserve the existing streak.
- `LIVE_MAX_RISK_PCT` is the required live safety cap. The research comparison intentionally applies the exact uncapped formula.
- `TARGET_RR` and `MAXIMUM_TARGET_R` cannot exceed `1.7`.
- `TRAILING_ENABLED=true|false` controls trailing independently in live management and backtests.

Run all four scenarios with `uv run dmc-bot risk-study --days 60 --balance 1000`. The command saves a summary, full JSON metrics, and four trade journals under `reports/risk_progression_1_7r/`.

This is a mechanical interpretation of an incomplete social-media description, not proof of the claimed profitability. Use the generated reports and forward testing before relying on it.
