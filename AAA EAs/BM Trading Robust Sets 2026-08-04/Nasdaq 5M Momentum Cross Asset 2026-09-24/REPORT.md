# Nasdaq 5M Candle Momentum on other symbols — native MT5, last year (2026-09-24)

Research only. The production EA and SET were not modified; nothing deployed.

## What was run

- **Unchanged production EX5** `Active Portfolio Full Pipeline 2026-09-05/11 Nasdaq 5M Candle Momentum/EA/Nasdaq 5M
  Candle Momentum Audit EA.ex5` (not recompiled; SHA-256 in `native/build.json`) with the **installed SET**
  `Selected Portfolio Settings 2026-09-01/11 Nasdaq 5M Candle Momentum - OPTIMIZED 2P5R - HARD 1PCT.set`.
  Tester overrides: tester UTC offset 0, adaptive controls off, 1% risk.
- Same logic on every symbol: the 09:30 New York M5 candle's close vs EMA(12) sets direction; stop 4 ATR(14);
  target 2.5R; flat 15:55 New York. UK 100 therefore trades its mid-afternoon London session (not its own open).
- Native MT5 Strategy Tester, isolated terminal `_Backtests/MT5-DMC-20260811`, profile "Calyx Research Empty",
  `[Experts] Enabled=0`, Exness-MT5Trial16 demo, $10,000, 1:2000, Model=4, 150 ms delay, M5,
  **2025-09-24 → 2026-09-24**. History quality 72% real ticks for every symbol (real ticks from 2026-01).
  All five runs exit 0 with fresh reports matching EA, symbol, dates and inputs. `run_native.py`, `summarize.py`,
  `RESULTS.json`.

## Results side by side ($10,000, 1% risk)

| | US100 (baseline) | Gold (XAUUSD) | Bitcoin (BTCUSD) | UK 100 | Silver (XAGUSD) |
|---|---:|---:|---:|---:|---:|
| Net return | **+39.6%** | −20.4% | +12.8% | −15.1% | +8.1% |
| Net profit | +$3,964 | −$2,039 | +$1,279 | −$1,514 | +$811 |
| Trades | 256 | 258 | 261 | 248 | 258 |
| Win rate | 41.4% | 38.8% | 39.5% | 41.5% | 46.9% |
| Profit factor | 1.22 | 0.86 | 1.07 | 0.88 | 1.05 |
| Avg win / avg loss | $205 / −$119 | $120 / −$89 | $180 / −$109 | $102 / −$83 | $136 / −$114 |
| Equity drawdown | 12.9% | 31.2% | 17.7% | 24.4% | 25.2% |
| Balance drawdown | 11.9% | 30.1% | 17.4% | 24.0% | 23.6% |
| Best win / worst loss streak | 11 / 11 | 5 / 8 | 4 / 9 | 4 / 9 | 6 / 6 |
| Long trades (won %) | 127 (40.9%) | 123 (36.6%) | 116 (40.5%) | 147 (42.9%) | 124 (48.4%) |
| Short trades (won %) | 129 (42.6%) | 135 (40.7%) | 145 (39.3%) | 101 (39.6%) | 134 (45.5%) |
| Exits: target / stop / time | 49 / 136 / 71 | 19 / 107 / 132 | 44 / 140 / 77 | 15 / 112 / 121 | 19 / 94 / 145 |
| Commission / swap | −$180 / −$213 | −$56 / −$3 | −$218 / $0 | −$430 / −$86 | −$382 / −$2 |
| Held past the close (trades, net) | 11 (−$92) | 3 (+$50) | 0 | 7 (−$317) | 3 (+$87) |
| Profit factor, same-day trades only | 1.24 | 0.85 | 1.07 | 0.89 | 1.05 |

## Findings

1. **The edge is specific to US100.** Gold and UK 100 lose; Bitcoin (+12.8%, PF 1.07) and silver (+8.1%, PF 1.05)
   are marginal and have deeper drawdowns than US100 for a fraction of its return.
2. On gold, UK 100 and silver the 2.5R target is rarely reached (15–19 targets vs 44–49 on US100/BTC); most trades
   end at the 15:55 time exit — the 09:30 NY move does not carry through the session on those markets.
3. Session-close defect seen again: on US100 (Friday) and UK 100 (session ends before 15:55 NY on some days) the time
   exit is rejected with "market closed" and positions are held overnight/over weekends. Effect this year is small
   (US100 −$92 on 11 trades; UK 100 −$317 on 7 trades) and does not change the conclusions.
4. One year only, 28% generated ticks; not validated on other years.

## Recommendation

Keep Nasdaq 5M Candle Momentum on US100 only. **SKIP** gold and UK 100 in this form; **WATCH ONLY** for BTC and
silver (too marginal to justify a pipeline without a symbol-specific session anchor, e.g. London open for UK 100
or the COMEX/crypto session for metals/BTC, tested on a period not used for choosing it).
Historical results are not a forecast.
