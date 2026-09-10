# USDJPY Volatility-Adaptive ATR Exits - raw paper-grid results

This is a raw reproduction of the paper's daily MACD/ATR framework on Exness USDJPY data. No Calyx session, direction, regime, trailing, breakeven or risk filters were added.

## Chronological selection

The candidate is selected using only 2022-2023. Its 2024-2025 statistics are untouched out-of-sample results. Returns below include the Exness spread proxy and 0.7 bp round-trip commission at 1x notional.

| Selection | Configuration | IS return | IS PF | IS win | IS DD | IS trades | OOS return | OOS PF | OOS win | OOS DD | OOS trades |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Best baseline chosen IS | MACD(17,22,23) no ATR exits | +31.39% | 2.34 | 44.83% | 4.51% | 29 | +10.94% | 1.55 | 38.46% | 6.80% | 26 |
| Best ATR chosen IS | MACD(15,26,16) ATR14 SL 1.5 / TP 3.0 | +21.01% | 2.05 | 48.28% | 6.15% | 29 | +5.57% | 1.29 | 39.29% | 10.19% | 28 |
| Same MACD without ATR | MACD(15,26,16) no ATR exits | +20.28% | 1.78 | 34.48% | 7.15% | 29 | +6.21% | 1.30 | 39.29% | 13.65% | 28 |

The ATR version cuts matched-model OOS drawdown from 13.65% to 10.19%, but return falls from 6.21% to 5.57% and PF falls from 1.30 to 1.29.
Only 21 of 16,920 ATR cases improved profit in-sample, and 0 of those remained profit enhancements out of sample.

## Verdict

RAW REJECT AS A NEW EDGE: the selected ATR version stays profitable, but it does not improve out-of-sample return or profit factor versus the identical MACD without ATR exits. Its only useful result is lower drawdown, so keep it as a possible risk-control experiment rather than add it to Calyx.

## Aggregate reproduction versus the paper

| Measure | Paper 2022-23 | Exness 2022-23 | Paper 2024-25 | Exness 2024-25 |
|---|---:|---:|---:|---:|
| Mean baseline log return | 0.1820 | 0.1974 | 0.0720 | 0.0938 |
| Mean ATR log return | 0.0524 | 0.0346 | 0.0127 | 0.0454 |
| Profit-enhancement cases | 107 | 21 | 801 | 1608 |

## Raw rules

- Daily USDJPY closes; MACD fast 15-20, slow 20-27 and signal 16-25, requiring fast < slow.
- Long on bullish MACD crossover and short on bearish crossover; execute at the next trading-day close.
- ATR(14) is fixed at entry. Stop and target grids both use 1.0-3.5 ATR in 0.5 steps.
- Exit at the first ATR threshold, or reverse at the next close after an opposite MACD crossover.
- After an ATR exit, remain flat until a new MACD crossover.
- Primary same-day ambiguity assumption is stop-first; target-first sensitivity is stored in the JSON audit.

## Important paper limitations

- The paper does not include transaction costs and does not publish one recommended configuration.
- The 470-model parameter range was itself derived from 2022-2023, so only the 2024-2025 test is genuinely out of sample.
- Daily bars cannot identify first-hit ordering when both stop and target are crossed in one session.
- Exness short Sunday bars were merged into Monday to create conventional five-session FX daily bars.

No website, installer, BAT, recommended system, live EA or active terminal was changed.
