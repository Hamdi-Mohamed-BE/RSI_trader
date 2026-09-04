# Trend Progression — complete native MT5 audit

All configuration choices were selected on 2023-09-01 through 2025-08-31. The latest year, 2025-09-01 through 2026-09-01, was then run once without changing the rules. Tests use MT5 Every Tick modelling, broker spread, commission, swap, random execution delay and 1% equity risk per trade.

## Untouched latest-year decision

| Market | Selected return | PF | Win rate | Max DD | Trades | Sharpe | Recovery | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| XAUUSD | +16.10% | 2.74 | 48.00% | 3.07% | 25 | 5.35 | 4.43 | Pass; strongest candidate |
| USTEC | +6.04% | 1.29 | 33.33% | 10.03% | 27 | 1.10 | 0.55 | Cautious demo candidate; baseline was better |
| USDJPY | +1.66% | 1.24 | 72.00% | 3.29% | 25 | 1.52 | 0.50 | Cautious demo candidate; small sample |
| GBPJPY | +0.52% | 1.02 | 28.12% | 8.22% | 32 | 0.09 | 0.06 | Reject; no useful edge |
| XAGUSD | -1.06% | 0.76 | 12.50% | 5.02% | 8 | -0.11 | -0.21 | Reject optimized setup |
| EURUSD | -2.64% | 0.86 | 34.38% | 8.76% | 32 | -1.27 | -0.29 | Reject |
| ETHUSD | -2.97% | 0.87 | 31.25% | 10.69% | 32 | -0.94 | -0.26 | Reject |
| GBPUSD | -5.20% | 0.60 | 17.65% | 11.45% | 17 | -0.65 | -0.44 | Reject |
| BTCUSD | -9.04% | 0.56 | 38.46% | 14.10% | 39 | -2.11 | -0.61 | Reject |

## Selected configurations

| Market | Timeframe | Direction | Stop / target | Management | Session |
|---|---|---|---|---|---|
| XAUUSD | H4 | Long only | Swing stop / 3R | Break-even at +1R | All day |
| USTEC | H4 | Long only | Swing stop / 3R | None | All day |
| BTCUSD | H4 | Long only | Swing stop / 4R | Break-even at +1R | All day |
| XAGUSD | H4 | Long only | 2 ATR stop / 4R | Break-even at +1R | London–New York overlap |
| ETHUSD | H4 | Long only | Swing stop / 2R | None | All day |
| EURUSD | H4 | Long only | Signal-candle stop / 3R | Trail from +0.75R at 1.5 ATR | All day |
| GBPUSD | H4 | Long only | 2 ATR stop / 4R | None | All day |
| USDJPY | H4 | Long only | 2 ATR stop / 0.5R | Break-even at +0.75R | Asia |
| GBPJPY | H4 | Long only | Swing stop / 3R | None | All day |

## Three-year context and Monte Carlo

| Market | 3Y return | 3Y PF | 3Y DD | 3Y trades | MC profitable | MC return P5 | MC median | MC DD P95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| XAUUSD | +63.85% | 2.47 | 6.11% | 91 | 98.1% | +3.05% | +15.96% | 6.07% |
| USTEC | +37.07% | 1.58 | 10.06% | 77 | 73.3% | -10.39% | +6.06% | 14.97% |
| USDJPY | +10.44% | 1.60 | 6.11% | 66 | 75.2% | -4.15% | +1.70% | 5.93% |
| GBPJPY | +27.27% | 1.48 | 7.44% | 74 | 51.5% | -14.31% | +0.29% | 16.98% |
| EURUSD | +8.24% | 1.13 | 11.27% | 115 | 35.8% | -14.71% | -2.95% | 16.66% |
| GBPUSD | +8.02% | 1.19 | 14.98% | 52 | 18.5% | -14.30% | -5.36% | 14.46% |
| XAGUSD | +1.61% | 1.11 | 10.02% | 30 | 29.8% | -6.04% | -1.27% | 6.06% |
| ETHUSD | -1.18% | 0.98 | 10.69% | 106 | 35.1% | -15.12% | -3.02% | 17.85% |
| BTCUSD | +17.77% | 1.35 | 14.30% | 99 | 12.6% | -20.75% | -9.50% | 21.47% |

Monte Carlo uses 10,000 bootstrap paths of the untouched-year trade outcomes. A zero simulated ruin rate does not make a strategy safe: negative P5 and weak probability of profit still reject most candidates.

## Final recommendation

Use XAUUSD only as the production-quality Trend Progression candidate, beginning on demo. USTEC and USDJPY can be forward-tested at reduced risk (0.25%–0.50%) because both have only 25–27 untouched-year trades and negative Monte Carlo P5 outcomes. Do not deploy the BTC, ETH, XAG, EURUSD, GBPUSD, or GBPJPY optimized versions.

XAGUSD's untouched baseline made +14.42% with PF 1.91, but that result was observed only after the locked test. It is a new hypothesis—not permission to replace the failed selected setup—and requires a future unseen test.
