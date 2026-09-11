# News Pulse BTC — official-calendar three-year replay

## Scope

- Test window: 2023-09-11 through 2026-09-10 UTC
- Official schedule: 94 releases (35 NFP, 35 CPI, 24 FOMC)
- Calendar execution audit: 94 expected, 94 attempted, 94 pending straddles placed, no coverage violation
- Triggered events: 92; two events placed orders but neither side triggered
- Market/tester: Exness-MT5Trial16 BTCUSD, M1, MT5 Every Tick (Model 0), random execution delay, USD 10,000, 1:2000
- Saved settings: 0.75% risk per enabled side, 75-unit entry offset, 75-unit stop, trailing starts at 1.5R with a 112.5-unit distance, 30-second lead, 60-second forced close

## Full result

| Metric | Result |
|---|---:|
| Final balance | $108,486.66 |
| Net profit | $98,486.66 |
| Return | +984.87% |
| Profit factor | 9.33 |
| Trades | 125 |
| Win rate | 76.80% (96 wins / 29 losses) |
| Equity max drawdown | 3.41% ($2,867.76) |
| Balance max drawdown | 2.88% ($2,404.46) |
| Commission | -$2,298.82 |
| Swap | $0.00 |
| Expected payoff | $787.89 |
| Recovery factor | 34.34 |
| Max win / loss streak | 16 / 3 |
| Average holding time | 28.3 seconds |
| History quality | 100% |

## Calendar-year path

The first and last rows are partial years because the requested window starts in September 2023 and ends in September 2026.

| Event year | Triggered events | Trades | Win rate | Net profit | Return on that year's starting balance | PF after recorded commission |
|---|---:|---:|---:|---:|---:|---:|
| 2023 partial | 8 | 8 | 87.50% | $256.20 | +2.56% | 5.36 |
| 2024 | 32 | 44 | 75.00% | $12,515.99 | +122.03% | 8.82 |
| 2025 | 30 | 44 | 72.73% | $50,808.59 | +223.12% | 9.81 |
| 2026 partial | 22 | 29 | 82.76% | $34,905.88 | +47.44% | 8.93 |

## Event-type breakdown

| Event | Events with trades | Trades | Win rate | Net profit | PF after recorded commission |
|---|---:|---:|---:|---:|---:|
| NFP | 35 | 50 | 80.00% | $33,728.20 | 9.89 |
| CPI | 34 | 46 | 71.74% | $42,699.26 | 8.56 |
| FOMC | 23 | 29 | 79.31% | $22,059.20 | 10.26 |

## Interpretation

This result supersedes neither live-forward validation nor a real-tick news test. Model 0 generates intra-minute ticks from broker M1 bars, so its 100% history-quality label does not mean every historical tick was recorded. For this seconds-sensitive straddle, treat +984.87% as the complete pipeline baseline, not a guaranteed live return. The next required validation is the same locked settings on Every Tick Based on Real Ticks plus adverse spread/slippage stress.
