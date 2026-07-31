# High-Impact USD News Source Pipeline

## Source roles

| Source | Use | Authority | Automation note |
|---|---|---:|---|
| BLS | NFP, CPI, PPI schedules and released values | Primary | Use the official calendar and API. The API can lag the release, so the release page/RSS remains important at T0. |
| BEA | Advance GDP, PCE, and related releases | Primary | Use the official release schedule and API metadata. |
| Federal Reserve | FOMC schedule, statement, minutes, and press releases | Primary | Use the monetary-policy RSS feed and official statement URL. |
| Forex Factory | High-impact label, consensus, previous value, and convenient weekly schedule | Secondary | Cache the weekly JSON/export, normalize its timezone to UTC, then cross-check the official publisher. |
| Investing.com | Consensus and calendar redundancy | Secondary | Use only an approved API/feed or permitted access method; do not build a brittle page scraper. |
| Reuters / Bloomberg | Timestamped macro narrative and rapid interpretation | Licensed secondary | Use a licensed feed or user-accessible page. Store headline timestamp and URL for audit. |
| TradingView | Price reaction, spread proxy, cross-asset confirmation, and chart context | Market context | It is not the authority for the economic release. The desktop MCP must be connected before it can be queried. |
| CNN / Al Jazeera | Geopolitical and regime context | Context only | Do not let a general headline directly override a numeric release without a deterministic rule. |

## Live sequence

1. At T-24h, build the watchlist from Forex Factory/Investing and verify the event time against BLS, BEA, or the Federal Reserve.
2. At T-30m, freeze the consensus, previous/revised value, official URL, source timestamps, prediction inputs, and the completed T-60 to T-31 price range.
3. Between T-30m and T-1m, move pending-order buffers only farther from price when spread widens. Never move an order closer to force a fill.
4. At T0, ingest the official actual value or statement. Numeric surprise drives NFP/CPI/PPI/GDP; statement-diff and rate-path context drive FOMC.
5. Keep article sentiment as a confidence modifier, not the sole direction. Reject articles published after the release from pre-release backtests.
6. Cancel unfilled pending orders at T+15m. Preserve the full audit record even when no order triggers.

## Prediction safeguards

- Every feature needs an `available_at` timestamp earlier than the prediction cutoff.
- Consensus revisions are versioned; the latest value must not overwrite the historical T-30 snapshot.
- Source disagreement produces `NO TRADE`, not an average invented from incompatible values.
- Official release facts outrank aggregators and media interpretations.
- Backtests use bid/ask prices and pessimistic same-minute ordering.
- Model and strategy results are reported separately. A correct direction forecast does not imply executable profit after spread and slippage.

## Current practical limitation

The current TradingView desktop connection is unavailable, and no callable TradingView news/calendar tool is exposed in this session. The pipeline can use TradingView price tools after the desktop CDP connection is restored, while official publishers remain the release authority.
