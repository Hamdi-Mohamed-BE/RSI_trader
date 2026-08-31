# CRT parent-range research notes

## Mechanical definition used

The online CRT references consistently define the model as:

1. A completed higher-timeframe candle defines a parent high and low.
2. A later candle takes one boundary with its wick.
3. That candle closes back inside the parent range.
4. Direction is toward the untouched opposite boundary.

Primary reference pages used:

- https://candlerangetheory.com/
- https://crtterminal.com/learn/candle-range-theory
- https://www.crttrading.com/

The EA uses completed candles only and excludes double-sided sweeps. The stop is buffered beyond the sweep extreme. The target is the opposite parent boundary. Trades below 0.5 reward-to-risk are skipped. The daily-bias version requires EMA(20) and EMA(50) alignment on D1.

## Test design

- Symbols: BTCUSD, XAUUSD, US500, USTEC, EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF and NZDUSD.
- Four development candidates: H1/H4 parent ranges, each with and without the D1 trend filter.
- One universal configuration selected from 2024-08-29 through 2025-08-28.
- Untouched locked test from 2025-08-29 through 2026-08-28.
- Exness MT5 Every Tick, random execution delay, spread, commission and swap included.
- $10,000 initial balance and 1% equity risk per trade.

## Result

The universal H4 daily-bias configuration was profitable on only 2 of 11 locked markets. Its mean locked return was -14.44%. US500 returned +5.47% with PF 1.08, which is too weak for deployment, and USTEC returned +1.08% with PF 1.01.

Gold H4 core and USDJPY H4 core looked positive during development but failed their separately locked tests. No CRT configuration qualifies for the active BAT portfolio.
