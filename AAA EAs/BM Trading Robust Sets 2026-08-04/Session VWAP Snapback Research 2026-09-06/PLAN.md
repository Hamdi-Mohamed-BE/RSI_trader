# Step 4 — Session VWAP Liquidity Snapback

Research only until the locked evidence passes. No installer, active MT5 profile, website catalogue, or production portfolio is changed by this package.

## Fixed protocol

- Markets: XAUUSD, XAGUSD, USTEC, US30, GBPJPY.
- Source: isolated Exness demo research terminal, broker M5 bid OHLC, tick activity and recorded spread.
- Development: 2023-09-01 through 2025-09-01.
- Locked validation: 2025-09-01 through 2026-09-01. The locked year is not read while selecting parameters.
- Risk: exactly 1% of current equity per trade. At most one position per symbol and session.
- Signal: session-anchored tick-volume VWAP and causal volume-weighted deviation bands. A completed candle must reject an outer band; entry occurs at the following bar open.
- Regime gates: no gate, causal ADX ceiling, normalized EMA-slope ceiling, or a causal 20-day three-state return regime. These are veto layers; they do not create trades.
- Timeframes: M5, M15, M30, H1.
- Sessions: Asia, London, New York, London–New York overlap, and UTC all-day.
- Stops: confirmation candle, recent swing, session extreme, and ATR.
- Exits: central VWAP or fixed 0.5R, 0.75R, 1R, 1.5R, 2R, 2.5R, 3R, 4R and 6R.
- Management: none, breakeven, ATR trail, M15 50%-to-20% dynamic stop, and session close.
- Directions: both, long-only and short-only.
- Cost treatment: ask-side entries/exits include recorded spread with a causal fallback for unavailable zero-spread bars; conservative stop-first resolution; extra execution friction is tested separately.
- Robustness: rolling walk-forward folds, parameter-neighbourhood check, 10,000 five-trade block-bootstrap Monte Carlo paths, and cost stress.

## Acceptance gate

A market is not recommended from development performance. The frozen locked-year result should be positive with PF at least 1.10, at least 30 trades, drawdown below 15%, positive Sharpe and no single-trade dependency. Any passing candidate must then survive native MT5 execution validation before production deployment is considered.

## Known data limitation

These Exness CFDs expose broker tick activity rather than centralized exchange volume. VWAP is therefore a broker activity proxy. A true NQ/YM futures implementation should be revalidated on centralized exchange volume before claiming institutional-volume evidence.
