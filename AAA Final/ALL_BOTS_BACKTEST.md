# AAA Final — seven-bot validation report

Generated 2026-08-03. Historical results are simulations, not guarantees. The five existing workers use their latest frozen broker-data validations; the two new workers were rebuilt and rerun for this delivery. Periods differ, so the rows are not a portfolio backtest and must not be added together.

## Final worker list

| # | Worker | Market | Current role | Execution state |
|---:|---|---|---|---|
| 1 | AMD | XAUUSD | Existing forward-test worker | Live-enabled by existing suite configuration |
| 2 | Asia Breakout | XAUUSD | Existing confirmed-close/retest worker | Live-enabled by existing suite configuration |
| 3 | DmC | US100 | Existing daily/H4 pullback worker | Live-enabled by existing suite configuration |
| 4 | EMA3 | XAUUSD | Existing pivot-reversal worker | Live-enabled by existing suite configuration |
| 5 | US100 Weakness | US100 | Existing Nasdaq weakness worker | Live-enabled by existing suite configuration |
| 6 | XAU News Pulse | XAUUSD | New PPI news OCO research worker | Live-enabled; current calendar refreshes automatically |
| 7 | XAU Weekend Direction | XAUUSD | New validation-gated weekend worker | Live-enabled process; rejected model still forces `NO_TRADE` |

## Existing workers — latest frozen 60-day comparison

These rows use the MT5 account's broker history and the assumptions already frozen in each project.

| Worker | Actual UTC data range | Trades | Win rate | Profit factor | Maximum drawdown | Interpretation |
|---|---|---:|---:|---:|---:|---|
| AMD | 2026-06-02 — 2026-07-31 | 11 | 90.91% | 4.71 | 3.00% | Strongest small-sample result; still only 11 trades |
| Asia Breakout — XAU | 2026-06-02 — 2026-08-01 | 18 | 72.22% | 3.27 | 5.30% | Positive but small sample |
| DmC — US100 | 2026-06-15 — 2026-07-31 | 9 | 55.56% | 1.07 | 3.96% realized / 4.21% intratrade | Marginal edge; forward-test only |
| EMA3 — XAU | 2026-06-02 — 2026-08-01 | 23 | 43.48% | 1.00 | 403.26% realized / 394.97% intratrade | Rejected unsafe historical baseline; account-ruin drawdown |
| US100 Weakness | 2026-06-15 — 2026-07-31 | 8 | 50.00% | 3.28 | 3.96% | Promising but only eight trades |

Asia Breakout's previously researched multi-symbol rows were BTCUSD: 29 trades, 75.86% win rate, 1.93 PF, 6.08% DD; EURJPY: 9 trades, 44.44% win rate, 1.99 PF, 6.45% DD. They are context, not additional independent portfolio returns.

## New worker 1 — XAU News Pulse

Test design: 93 scheduled high-impact USD events from 2024-07-31 through 2026-07-31. Development ended 2026-01-31; the following six months were untouched until final evaluation. Bid/ask M1 candles, historical spread, order buffers, pending expiry, slippage rules and pessimistic same-bar sequencing are included. The development-selected filter is PPI only, OCO, 5R and one re-entry.

| Sample | Trades | Win rate | Profit factor | Net R | Maximum DD | 1%-risk compounded return |
|---|---:|---:|---:|---:|---:|---:|
| Development | 20 | 45.00% | 3.07 | +16.05R | 3.09% | +16.87% |
| Untouched holdout | 4 | 50.00% | 2.89 | +3.78R | 1.22% | +3.72% |
| Full selected sample | 24 | 45.83% | 3.03 | +19.83R | 3.09% | +21.21% |
| Full unfiltered event set | 106 | 23.58% | 1.03 | +1.91R | 12.89% | +0.06% |

Verdict: **provisionally validated, but sample-constrained**. The untouched holdout is positive, yet it contains only four trades. The working deployment is now live-enabled at the user's direction, with a PPI-only gate, automatic calendar refresh, and the existing spread, margin, daily-loss, ownership, expiry and sizing guards. The source prediction models retain `execution_capability=false`; the separate deterministic worker never changes that flag.

## New worker 2 — XAU Weekend Direction

Nested model predictions cover 2024-06-10 through 2026-08-03. Strategy selection used the first 70 prediction weeks and the final 41 weeks as holdout. Weekend gaps use the first executable reopening price; same-minute ambiguity is pessimistic.

### Selected ML model — rejected

| Sample | Trades | Win rate | Profit factor | Net R | Maximum DD |
|---|---:|---:|---:|---:|---:|
| Development | 38 | 34.21% | 1.71 | +17.51R | 5.00R |
| Holdout | 13 | 15.38% | 0.25 | -13.46R | 13.90R |
| Full nested sample | 51 | 29.41% | 1.10 | +4.05R | 16.75R |

Verdict: **rejected**. `validated=false` is enforced at runtime and the worker returns `NO_TRADE`.

### Provisional momentum research — not live-authorized

The best observed alternative follows strong Friday 24-hour momentum, enters four minutes before the inferred close, uses a $30 emergency stop and 3R target, then exits at the first weekly reopening tick.

| Sample | Trades | Win rate | Profit factor | Net R | Maximum DD |
|---|---:|---:|---:|---:|---:|
| Development | 24 | 41.67% | 1.41 | +0.54R | 0.61R |
| Holdout | 21 | 80.95% | 5.78 | +8.69R | 1.52R |
| Full nested sample | 45 | 60.00% | 3.94 | +9.23R | 1.52R |

Verdict: **selection-biased/provisional** because this candidate was chosen after comparing multiple RR families on the same holdout. It is disabled by default and can run only on a demo account after explicitly setting `ALLOW_PROVISIONAL_MOMENTUM_MODE=true`.

## Delivery checks

- New worker tests: 8/8 passed.
- Master launcher PowerShell syntax: passed.
- Master `-CheckOnly`: all seven environments and the connected MT5 account passed.
- MT5 `order_check` preflight: all seven workers passed; no order was sent.
- Dynamic broker resolution: `XAUUSD -> XAUUSD..`, `US100 -> NAS100U6` on the connected demo account.
- Magic numbers are unique: News Pulse `860301`, Weekend Direction `860302`.
- Paper commands forcibly disable sending even though the working deployment environments are live-enabled.
- Weekend Direction still returns `NO_TRADE` because the selected model is rejected; live switches do not bypass validation.

## Commands

From each new project folder:

```text
uv sync --extra dev
uv run pytest -q
run_backtest.bat
run.bat
run_live.bat
```

From `AAA Final`:

```text
run_all_preflight.bat
run_all_live.bat
stop_all_bots.bat
```

`run_all_live.bat` starts all seven live-ready processes. News Pulse can execute only its selected PPI setup. Weekend Direction remains hard validation-gated and cannot execute while its model metadata is rejected.
