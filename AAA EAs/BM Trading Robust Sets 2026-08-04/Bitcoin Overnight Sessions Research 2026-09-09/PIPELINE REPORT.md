# Bitcoin Overnight MAX(10) - full Calyx pipeline

Decision: **REJECT — the untouched post-selection window failed.**

All pipeline configurations use a defined stop and dynamic 1% equity risk. Screening used only the development window; the locked window was opened after every setting was frozen.

## Selected settings

- stop: `percent-100`
- nights: `friday-monday`
- lookback: `max-10-paper`
- direction: `long-paper`
- exit-time: `ny-1600`
- target: `time-exit`
- management: `none`
- regime: `none`
- volatility: `none`

## Final native MT5 results

| Version | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline-locked | -4.40% | 0.78 | 41.46% | 7.32% | 82 | -1.23 | -0.59 |
| optimized-locked | -18.32% | 0.53 | 22.41% | 19.17% | 58 | -3.49 | -0.96 |
| optimized-latest-1y | -1.59% | 0.88 | 31.58% | 7.82% | 19 | -0.53 | -0.19 |
| optimized-full-5y | +29.43% | 1.27 | 29.09% | 21.71% | 110 | 1.74 | 0.83 |

## Locked-window Monte Carlo

- Probability profitable: 0.52%
- Return P5 / median / P95: -29.45% / -18.48% / -7.04%
- Max DD median / P95: 20.46% / 30.41%

No website, BAT, installer, recommended-system or active-portfolio file was changed. The selected SET remains research-only pending user review.
