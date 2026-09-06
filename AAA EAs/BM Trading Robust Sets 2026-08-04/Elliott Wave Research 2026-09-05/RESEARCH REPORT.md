# Elliott Wave 1-2-3 EA research report

## Scope and test discipline

- Markets: XAUUSD, XAGUSD, USTEC (US100), US30, BTCUSD, GBPJPY and EURUSD.
- Starting balance: USD 10,000.
- Risk: 1% of current equity per trade.
- Development period: 2023-09-01 through 2025-08-31.
- Untouched validation period: 2025-09-01 through 2026-09-01.
- Full chart period: 2023-09-01 through 2026-09-01.
- Development screens used MT5 bar modelling for speed. Locked and full audits used MT5 Every Tick history with broker spread, commission, swap and random execution delay.
- Settings were chosen only from the development period. The locked year was run after settings were frozen.

## Mechanical, non-repainting interpretation

The EA does not attempt subjective full Elliott-wave labeling. It trades a confirmed Wave 1 / Wave 2 / Wave 3 continuation proxy:

1. Confirm alternating pivots using three closed bars on both sides.
2. Require Wave 1 to measure 1.5 to 10 ATR.
3. Require Wave 2 to retrace 38.2% to 78.6% without crossing the Wave 1 origin.
4. Require a completed breakout candle through the Wave 1 extreme by 0.05 ATR, with a body of at least 0.15 ATR.
5. Apply the selected trend, stop, target, management and session rules.

## Development-selected configurations

| Market | TF | Trend confirmation | Stop | Target | Management | Session |
|---|---:|---|---|---:|---|---|
| XAUUSD | H4 | EMA50 direction and slope | Signal candle | 3R | None | All day |
| XAGUSD | H1 | Wave structure only | Wave 2 invalidation | 3R | None | All day |
| USTEC | H4 | Wave structure only | 2 ATR | 0.75R | M15 close at +0.5R moves SL to +0.2R | All day |
| US30 | M15 | H4 EMA50 direction and slope | Wave 2 invalidation | 4R | None | All day |
| BTCUSD | H1 | EMA20/EMA50 stack and slope | Signal candle | 4R | M15 close at +0.5R moves SL to +0.2R | All day |
| GBPJPY | H4 | Wave structure only | 2 ATR | 4R | None | All day |
| EURUSD | H1 | EMA20/EMA50 stack and slope | Wave 2 invalidation | 3R | M15 close at +0.5R moves SL to +0.2R | New York (12:00-21:00 broker time) |

## Untouched last-year result

| Market | Optimized return | PF | Win rate | Max DD | Trades | Sharpe | Recovery | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| XAUUSD | +23.82% | 3.15 | 54.17% | 3.77% | 24 | 5.86 | 4.91 | Best result; demo candidate, still a small sample |
| XAGUSD | +3.18% | 1.11 | 27.66% | 6.51% | 47 | 0.62 | 0.48 | Reject optimized version; worse than baseline |
| USTEC | -4.55% | 0.64 | 51.85% | 4.68% | 27 | -2.90 | -0.97 | Reject |
| US30 | -28.14% | 0.73 | 15.75% | 32.42% | 127 | -2.76 | -0.82 | Reject |
| BTCUSD | -16.82% | 0.62 | 52.83% | 24.28% | 106 | -4.32 | -0.68 | Reject |
| GBPJPY | -3.81% | 0.74 | 16.67% | 9.83% | 18 | -0.55 | -0.38 | Reject |
| EURUSD | +3.36% | 1.36 | 70.97% | 5.62% | 31 | 1.20 | 0.55 | Research/demo watch only |

## Monte Carlo interpretation

The bootstrap resampled each optimized locked-year trade list 10,000 times. This measures trade-order luck under the historical trade distribution; it does not model future regime change, worse liquidity or strategy decay.

| Market | Positive paths | Return P5 | Median return | DD P95 |
|---|---:|---:|---:|---:|
| XAUUSD | 99.6% | +8.47% | +23.84% | 6.03% |
| XAGUSD | 61.2% | -12.91% | +2.98% | 17.20% |
| USTEC | 14.0% | -11.34% | -4.52% | 12.18% |
| US30 | 7.3% | -58.96% | -28.62% | 61.86% |
| BTCUSD | 5.2% | -32.72% | -17.08% | 34.11% |
| GBPJPY | 35.8% | -13.45% | -3.85% | 15.97% |
| EURUSD | 69.4% | -6.02% | +3.15% | 8.38% |

## Verdict

The objective Elliott proxy is not a universal portfolio edge. XAUUSD is the only result strong enough for cautious demo forward testing. EURUSD is a secondary watch candidate but its negative Monte Carlo P5 and 31 locked trades are not strong enough for live deployment. BTCUSD and GBPJPY fail the untouched year despite good-looking development results, which is direct evidence of overfitting/instability. USTEC and US30 fail decisively. Do not add this EA to the production BAT portfolio from this audit.

Historical backtests and bootstrap simulations are research evidence, not a guarantee of future profit.
