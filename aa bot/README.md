# HamaForex LTA + Coinbase MBO Terminal

A real-time analysis platform that keeps the LTA framework in control and uses Coinbase order-book data only as execution confirmation.

## Included

- Coinbase Exchange Level-3 snapshot plus `full` WebSocket reconstruction by `order_id`
- Separate connection per configured product
- Sequence-gap detection, automatic snapshot rebuild and exponential reconnect backoff
- Automatic Level-2 fallback when Level 3 repeatedly fails
- Live order-book ladder, aggressive trade delta and top-book imbalance
- Bid/ask refresh, absorption, stacked-liquidity and spoof/pull heuristics
- Rolling 70% value-area profile from trades collected since connection
- Manual HTF bias, structure and POC/VAH/VAL/supply/demand planning
- Deterministic A/A+ setup ranking that refuses to trade MBO without LTA location
- Spot position sizing and R-multiple calculator
- Dedicated Playbook page with EM1–EM4 and live A+ qualification gates
- Dedicated Risk command center with sizing policy and guardrails
- Historical LTA backtester with Coinbase candle pagination, rolling value-area approximation, conservative fills, equity curve, drawdown and trade log
- Live execution locked by default

## Start

```powershell
Copy-Item .env.example .env
npm.cmd install
npm.cmd run dev
```

Open `http://localhost:5173`.

Production-style local run:

```powershell
npm.cmd run build
npm.cmd start
```

Open `http://localhost:8787`.

## How to use

1. Choose BTC-USD or ETH-USD.
2. Enter the H4/H1 bias and M30/M15 structure.
3. Add completed TradingView POC, VAH, VAL and fresh supply/demand zones.
4. Save the plan.
5. The platform observes MBO only when price is at a planned zone.
6. A+ requires aligned location, HTF bias, structure and MBO confirmation without spoof/spread warnings.

The live internal volume profile begins when the server connects. It is an execution aid; it does not replace completed session profiles from TradingView.

## Backtesting scope

The Backtest page simulates value-area reclaims and rejections from Coinbase OHLCV history. Candle volume is distributed across each candle range to approximate a rolling 70% value area. Same-candle stop/target collisions assume the stop is hit first.

Backtests may model 0.01–10% risk for research. Values above 1% are clearly marked research-only; the live trading plan and execution guardrail remain capped at 1%.

Historical Level-3 events are not available from the standard Coinbase candle endpoint. The backtester therefore tests the LTA location/structure model, not historical MBO confirmation. Live MBO can be replayed only after a recorder has accumulated a local event dataset.

## Safety

- `ENABLE_LIVE_EXECUTION=false` by default.
- `/api/orders` refuses every request in this version.
- Spot shorting is not enabled.
- Maximum plan risk is validated at 1%.
- API credentials are never sent to the browser.

See [ENVIRONMENT.md](./docs/ENVIRONMENT.md) for keys and [ARCHITECTURE.md](./docs/ARCHITECTURE.md) for the data flow.
