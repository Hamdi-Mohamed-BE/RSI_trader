# RSI + session-VWAP EA research

This standalone research package reconstructs the supplied Pine strategy as an MT5 Expert Advisor. It is not part of the active portfolio BAT or the EA website.

The source idea is long-only. It calculates a daily-reset VWAP from broker volume, calculates Wilder RSI over that VWAP series, buys when RSI crosses upward through the oversold level, and exits or scales out when RSI later crosses downward through the overbought level.

The original Pine strategy has no normal protective stop and can pyramid five times. The managed MT5 variants deliberately add a protective stop, 1% equity-risk sizing, optional reward/risk target, break-even, ATR trailing, session filtering and a maximum holding period. Original-like signal-only exits remain available for comparison, but still use an emergency stop so the 1% risk cap is meaningful.

## Validation conclusion

The development workflow screened 35 symbol/timeframe combinations, 182 stop/RR combinations, 42 trailing variants and 35 session variants. The selected configurations were then frozen and tested from 2025-09-01 through 2026-09-01 using native MT5 Every Tick modelling, Exness history, broker spread, commission, swap and random execution delay.

Only XAUUSD produced a usable locked-year result: +4.58%, PF 1.48, 72.73% wins, 3.53% max equity drawdown and 44 trades. Its 10,000-path trade-bootstrap Monte Carlo still has a negative 5th-percentile return, so it is a research candidate rather than a production recommendation. BTCUSD, ETHUSD and GBPJPY failed the locked year. XAGUSD, US30 and USTEC produced too few locked trades for a defensible conclusion.

Nothing in this package is installed into the active portfolio BAT or website. Exact locked `.set` files are in `Sets`, full MT5 reports are in `Backtest Reports`, charts are in `Charts`, and the consolidated evidence is in `FINAL AUDIT.md` and `final-audit.json`.
