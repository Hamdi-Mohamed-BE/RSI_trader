# NAW LTA Order Flow Lab

A fresh, self-contained FastAPI and Celery application for researching and monitoring an order-flow-aware LTA strategy on:

- `BTCUSD` via CME `BTC.v.0`
- `ETHUSD` via CME `ETH.v.0`
- `XAUUSD` via CME `GC.v.0`
- `XAGUSD` via CME `SI.v.0`
- `US30` via CME `YM.v.0`
- `US100` via CME `NQ.v.0`

The provider symbols are volume-based front continuous futures. They are configurable in the web interface.

## What It Does

- Builds volume profiles with POC, VAH, VAL, HVNs, and LVNs.
- Supports exact CME trade-size and MBP-10 confirmation when the account has live entitlement.
- In free mode, combines the cached CME composite profile with live MT5 candles.
- Scores profile location, trend, rejection, participation, and book pressure.
- Chooses a market entry near price or a resting limit at the profile level.
- Expands stop distance with volatility and participation while preserving percentage risk.
- Includes spread and slippage in backtests.
- Translates CME profile levels to the live broker chart using the overlapping CME/MT5 basis.
- Runs live scans, paper order management, and backtests in Celery.
- Supports 30-day and 183-day per-symbol tests from a `$300` default balance.
- Can optimize RR, A+ score, ATR stop width, and session per symbol, then save the winners as defaults.

## Market Data Key

Create a Databento account and obtain an API key from the portal. Add it to `.env`:

```dotenv
DATABENTO_API_KEY=db-your-key-here
```

Then restart `run.bat`. The key is read server-side and is never returned by the API or browser.

Official references:

- [Databento API keys](https://databento.com/docs/portal/api-keys)
- [CME GLBX.MDP3 schemas](https://databento.com/docs/venues-and-datasets/glbx-mdp3)
- [Continuous futures symbols](https://databento.com/docs/standards-and-conventions/symbology#continuous)

Historical MBP-10 over six months can be large and costly. The backtester deliberately uses CME `ohlcv-1m` traded volume for the full period. Exact live trade tape and MBP-10 are used only when the Databento account has the required live CME entitlement. This distinction is shown in each report and is not silently treated as full historical depth.

The default historical download cap is `$1.00`. Gold minute data is cached in completed daily files, plus a coverage manifest, so optimization passes reuse local history instead of purchasing it again.

## Run

Double-click:

```text
run.bat
```

It will:

1. Sync the locked Python environment with `uv`.
2. Install/build Tailwind CSS.
3. Open a visible Celery worker window.
4. Open a visible Celery scheduler window.
5. Run the web app at [http://127.0.0.1:8010](http://127.0.0.1:8010).

Repeated launches restart this app's existing worker and scheduler rather than creating duplicates, so code updates cannot leave an older Celery process running.

## Pages

- **Live desk:** worker state, candlesticks, profile/order levels, order ledger.
- **Scanner:** latest score and decision for all six markets.
- **Backtests:** queue fixed or optimized 1-month/6-month runs and inspect per-symbol monthly results.
- **Configuration:** all live/backtest rules in one place.

The Start/Stop button controls strategy decisions. It does not kill Celery, so the web interface and backtest queue stay responsive.

## Backtest Integrity

- Signals only see candles at or before the decision time.
- Pending entries require the market to trade through the limit.
- When stop and target are both touched inside one candle, the stop is assumed first.
- Spread and slippage are charged on entry.
- Weekend candles and sessions outside the configured windows are skipped.
- Each symbol result starts independently from the selected balance. Results are not a promise of future returns.

For optimization, use six months first. It has enough observations to avoid selecting a setting from a handful of trades. Then run a normal 30-day test with the saved defaults as a recent validation.

## Development

```powershell
uv sync
npm.cmd install
npm.cmd run build:css
uv run pytest
uv run ruff check .
```

The local task queue uses SQLite, so Redis is not required. Celery uses the `solo` worker pool for reliable Windows operation.

## MT5 Execution

Set `execution_mode` to `mt5` and enable **Allow MT5 orders** on the Configuration page. The adapter:

- Uses the balance of the account currently logged into the MT5 terminal.
- Risks the configured percentage through `order_calc_profit` and broker contract specifications.
- Uses the broker minimum lot when the calculated lot is smaller, and records that risk exception.
- Refuses an order when the CME/MT5 basis exceeds the configured limit.
- Blocks duplicate same-direction positions and orders.
- Applies the global three-order daily cap and configured session gate.
- Moves SL to break-even at `1R`, then locks `1R` at `2R`, and so on.

The locally detected account during setup is an Exness MT5 Trial account with symbol `XAUUSDm`. Re-check the account banner before changing terminals or logging into a funded account.
