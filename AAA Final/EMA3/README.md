# EMA3 H4 Pivot Reversal

This project trades the Buy/Sell labels produced by the supplied TradingView
indicator without look-ahead. A pivot is known only after the right-side H4
candles close, so execution occurs at the following H4 open.

## Safe optimized default

- XAUUSD H4, discovered automatically from the connected MT5 broker.
- Five candles on each side of the pivot.
- Buy only while EMA200 is rising over six completed H4 bars; Sell only while
  EMA200 is falling.
- One position maximum; no doubling down.
- Stop at the confirmed pivot extreme.
- Start trailing after an H4 close reaches +1R; keep the stop 1R behind that
  completed close.
- Close and reverse when an opposite qualified pivot confirms.
- Risk 1% of current equity per position.

The EMA8, EMA20 and Bollinger plots from the original indicator are visual.
The EMA200 slope is the only added trade-quality filter.

## H1 versus H4 cross-market test

Run the walk-forward comparator with:

```powershell
uv run ema3-compare-timeframes
```

It tests XAUUSD, the broker's available US100 proxy, US30, BTCUSD, EURUSD and
GBPJPY. The first 75% of each available history selects the configuration and
the final 25% validates it without resetting open strategy state at the split.
The current report is saved in `reports/timeframe_comparison/REPORT.md`.

The latest standard-confidence validation ranked XAUUSD H4 first: 14 trades,
57.1% win rate, 1.80 profit factor, +4.82R and 2.97% drawdown. H1 did not improve
Gold. US100 H4 was mildly positive, but the connected broker exposed only about
47 days for its current Nasdaq contract, so that result is provisional.

## Corrected one-year result

Test period: 1 August 2025 through 1 August 2026. Historical broker spread is
included and same-bar stop handling is conservative.

| Metric | Result |
|---|---:|
| Trades | 37 |
| Wins / losses | 23 / 14 |
| Win rate | 62.16% |
| Profit factor | 3.39 |
| Net result | +33.51R |
| Expectancy | +0.91R/trade |
| $1,000 ending balance at 1% risk | $1,385.87 |
| Return | +38.59% |
| Maximum realized drawdown | 5.29% |

The last quarter was held out from selection: 14 trades, 64.29% win rate,
PF 2.09, +5.44R and 2.97% drawdown. This is encouraging, although 14 trades
is still a small validation sample.

| Recent sample | Trades | Win rate | PF | Net R | Max DD |
|---|---:|---:|---:|---:|---:|
| Last 60 days | 8 | 75.00% | 2.54 | +3.08R | 1.00% |
| Last 30 days | 4 | 75.00% | 2.58 | +1.58R | 1.00% |

## Why the old drawdown exceeded 400%

The legacy test used a fixed 0.10 lot on a $1,000 account without a protective
stop or an account-solvency check. It allowed equity to become negative and
then recover on later trades. That is not executable and made the drawdown
statistic meaningless. The default test now uses a structural stop, compounds
percentage risk, includes adverse gaps, and stops the simulation at zero
equity. Negative-balance recovery is impossible.

## Risk sensitivity

| Risk per trade | Ending balance | Return | Max realized DD |
|---:|---:|---:|---:|
| 0.5% | $1,179.78 | +17.98% | 2.67% |
| 1.0% (default) | $1,385.87 | +38.59% | 5.29% |
| 2.0% | $1,888.83 | +88.88% | 10.38% |
| 3.0% | $2,534.55 | +153.45% | 15.27% |

The strategy is configured at 1%. Higher rows are sensitivity tests, not a
recommendation. Historical performance does not guarantee live results.

## Run

Backtest and save the current report to `reports/risk_sized_default`:

```powershell
uv sync
uv run ema3-backtest
```

Run the MT5 worker:

```powershell
uv run ema3-live
```

The worker uses whichever MT5 account is already open. `.env` currently has
`LIVE_TRADING=true`, so starting it can place, trail, close and reverse its own
positions. Set it to `false` for observation-only mode. It manages only trades
with its own magic number.

The live worker mirrors the tested logic: completed H4 pivots, EMA200 slope
filter, structural stop, one leg, 0.5% base equity risk, and configurable
completed-H4 trailing. No order was placed while producing this report.

## 0.5% loss-streak research controls

The risk engine supports the optional sequence `0.5%, 0.8%, 1.28%, ...`:

- `RISK_PROGRESSION_ENABLED=false` keeps flat 0.5% risk and is the live default.
- `RISK_PROGRESSION_MULTIPLIER=1.6` controls the consecutive-loss multiplier.
- `RISK_PROGRESSION_MAX_PCT=3.2` is the live safety ceiling.
- `TARGET_R=1.7` and `MAX_TARGET_R=1.7` enforce the 1.7R target ceiling.
- `TRAILING_ENABLED=true/false` explicitly switches trailing on or off. With it
  disabled, an `EXIT_MODE=trail` configuration uses the fixed capped target.

Only a closed losing trade increments the streak. A closed winning trade resets
it to zero; a flat trade leaves the streak unchanged. The research study is
deliberately uncapped so it tests the exact requested formula, while live trading
remains flat-risk unless progression is manually enabled.

Run the four-way comparison with `run_risk_study.bat`. Machine-readable results,
scenario journals, and the report are written to
`reports/risk_progression_1_7r`.
