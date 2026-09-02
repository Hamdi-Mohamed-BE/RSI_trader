# BTC spot–CME futures reopen-basis research

This is a standalone Python/uv research project. It does not place trades and is not connected to the main MT5 portfolio.

## Important market-structure change

The original idea assumes CME Bitcoin futures close for the weekend while spot BTC trades continuously. CME launched 24/7 cryptocurrency futures trading on 29 May 2026. The old approximately 49-hour weekend gap therefore no longer exists. Today, CME cryptocurrency products only have a weekly Saturday maintenance window plus a one-minute business-date switch.

The study consequently separates:

1. **Legacy weekend reopen:** historical gaps of at least 30 hours before 29 May 2026.
2. **Current maintenance reopen:** short post-launch pauses, reported separately and never mixed with the legacy test.

## Data and limitations

- Research proxy: Yahoo Finance `BTC-USD` spot and continuous `BTC=F` futures, hourly bars.
- The continuous futures series may switch contracts near expiry. Reopens in the last seven calendar days of a month are excluded to reduce roll contamination.
- Yahoo is adequate for falsifying or screening an idea, but not for production. A deployable version needs individual CME BTC/MBT contracts and a licensed spot benchmark from Databento/CME/CF Benchmarks or another institutional feed.
- All signals use data available before the entry timestamp. Parameter selection uses only the chronological development segment; the validation segment stays locked.
- Costs are deducted from every round trip: 12 bps for the futures-only version and 32 bps for the market-neutral futures/spot version.

## Strategy variants

- **Directional reconstruction:** after a qualifying legacy futures closure, short futures when spot rose and the reopened futures basis is unusually high; long futures when spot fell and basis is unusually low.
- **Market-neutral basis:** trade the same basis signal using opposing futures and spot legs to isolate convergence more directly.
- Exit when basis normalizes, a basis/price stop is hit, or the maximum holding time expires.

## Run

Double-click `RUN BTC BASIS STUDY.bat`, or run:

```text
uv sync --dev
uv run pytest
uv run python scripts/run_study.py
```

Outputs are written to `Results` and downloaded proxy data to `Data`.

## MT5 live status

`RUN LIVE MT5 PREFLIGHT - 1 PERCENT.bat` is a guarded readiness check, not an active order sender. It connects to MT5 and verifies the account, a tradable BTC spot/CFD leg, a separate tradable CME BTC/MBT futures leg, a Databento key and an exact 1% account-equity risk cap.

The currently connected Exness account has a tradable `BTCUSD` CFD but does not expose a tradable CME BTC or MBT futures contract. Its `MBTUSD` symbol is a disabled indicator, so this account cannot execute the tested two-leg basis strategy. The preflight deliberately refuses to substitute the CFD for both legs or place a directional approximation.

Even on a compatible futures broker, live order sending must remain disabled until the post-29-May-2026 maintenance-window variant is validated on contract-level data. The attractive historical result belongs to the retired Friday-to-Sunday closure.

## Official market references

- CME production notice for the 29 May 2026 expansion to continuous trading: https://www.cmegroup.com/notices/electronic-trading/2026/05/20260525.html
- CME clearing guide showing the Saturday 02:00–03:45 CT maintenance pause: https://www.cmegroup.com/clearing/files/cryptocurrency-guidelines.pdf
- CME explanation of futures-versus-cash basis and front-month changes: https://www.cmegroup.com/articles/faqs/faq-spot-quoted-futures.html
