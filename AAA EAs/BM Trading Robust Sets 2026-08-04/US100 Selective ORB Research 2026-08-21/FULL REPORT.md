# US100 Selective ORB — research and native MT5 validation

> **Update:** V3 now supersedes the configuration documented below. See `V3 IMPROVEMENT REPORT.md` and `Sets/BEST V3 - US100 USTEC M5 - TIME DIRECTION OR30 - 1pct.set`. The original V1 report is preserved here as an audit trail.

## Decision

**Research PASS; paper-trade first; not added to the active BAT.**

This is the strongest robust configuration found in the bounded search. It remained profitable in training, validation, and the later chronological check, but its latest-year sample contains only six trades. That is not enough evidence for unattended live deployment or for a claim that the future return will match the backtest.

## Final native MT5 results

Account assumptions: USD 10,000 initial deposit, 1% equity risk per trade, Exness `USTEC`, M5 chart, MT5 Every Tick model, broker history, recorded spread, random execution delay, commission and swap included. History quality was 98% on the older segments and 100% on the recent segments.

| Segment | Period | Final balance | Net return | PF | Win rate | Max equity DD | Trades |
|---|---:|---:|---:|---:|---:|---:|---:|
| Training | 2020-01-01 to 2023-12-31 | $10,999.57 | +10.00% | 1.52 | 55.36% | 4.02% | 56 |
| Validation | 2024-01-01 to 2025-06-30 | $10,329.13 | +3.29% | 2.46 | 55.56% | 2.57% | 18 |
| Later chronological check | 2025-07-01 to 2026-08-20 | $10,172.49 | +1.72% | 1.50 | 57.14% | 3.23% | 7 |
| Exact latest year | 2025-08-21 to 2026-08-20 | $10,104.92 | +1.05% | 1.31 | 50.00% | 3.20% | 6 |
| Full continuous test | 2020-01-01 to 2026-08-20 | **$11,559.45** | **+15.59%** | **1.61** | **55.56%** | **4.02%** | **81** |

The full-period CAGR is approximately 2.21%. This EA is designed to reject most days; low trade frequency is part of the result, not a tester error.

### Full-period detail

| Metric | Result |
|---|---:|
| Initial balance | $10,000.00 |
| Final balance | $11,559.45 |
| Net profit | $1,559.45 |
| Gross profit | $4,125.63 |
| Gross loss | -$2,566.18 |
| Profit factor | 1.61 |
| Max equity drawdown | $413.82 / 4.02% |
| Max balance drawdown | 3.20% |
| Wins / losses | 45 / 36 |
| Long trades | 36; 66.67% won |
| Short trades | 45; 46.67% won |
| Largest win / loss | $223.61 / -$217.83 |
| Average win / loss | $91.68 / -$69.70 |
| Explicit commission | -$56.97 |
| Swap | -$32.93 |
| Recovery factor | 3.77 |

Spread and random-delay effects are embedded in the deal results. The MT5 Sharpe figure is available in the source report, but it is not emphasized because sparse intraday trading can make terminal-specific Sharpe calculations look misleadingly high.

## Final logic implemented in the EA

1. The EA converts broker time to New York time with US daylight-saving rules and builds the opening range from **09:30 through 10:00 New York time**.
2. It calculates a 20-session median baseline for the same opening-window tick volume and a 20-session median regular-session true range.
3. It rejects the day unless the opening range is between 5% and 35% of the daily range baseline and opening relative tick volume is at least 0.60.
4. From 10:00 through 11:30, it looks for an M5 close outside the range. The breakout candle must have at least a 75% body, at least 0.90 same-clock relative tick volume, a 1.5%-of-daily-range breakout buffer, and the correct relationship to session VWAP.
5. The EA does not chase the first breakout. It waits up to three closed M5 bars for a retest that holds the broken boundary. Excessive pre-retest excursion invalidates the setup.
6. The stop goes beyond the opposite opening-range boundary plus a 5% range buffer. A trade is skipped if the stop exceeds 80% of the daily range baseline or the spread exceeds 10% of the opening range.
7. The target is 2R. After a closed M5 bar reaches 1R, the stop moves to entry. Any remaining position is closed at 15:55 New York time.
8. Position size is calculated with `OrderCalcProfit`, current equity, broker tick value, and broker lot steps. The final preset risks 1% and allows at most one trade per New York session.

## Why these filters were retained

- Nasdaq's regular cash session begins at 09:30 ET, so the logic anchors to the actual US open rather than a fixed broker hour.
- The QQQ opening-range/retest study found that opening-range size, retest timing, and pre-retest excursion were associated with continuation outcomes, while explicitly warning that the evidence was exploratory.
- Recent large-sample intraday papers on Nasdaq futures found that many OHLCV/ORB rules failed strict out-of-sample and cost-aware validation. This is why the EA uses chronological splits, same-clock activity normalization, and a selective retest rather than presenting raw in-sample optimization as proof.
- Exness warns that USTEC spreads can widen around the market open and news. The EA therefore includes spread rejection, random-delay testing, and broker-aware risk sizing.

## Optimization discipline

- Stage 1 tested opening windows, direction, and target size.
- Stage 2 tested 243 combinations of opening activity, breakout activity, candle body, retest timing, and retest tolerance on 2020–2023 only.
- Eight neighboring parameter sets were then checked on 2024 through June 2025. The selected region was profitable across multiple nearby settings, rather than being a single isolated top row.
- Stage 3 tested 144 exit variants. Larger targets increased headline return but reduced validation PF and increased drawdown, so the original 2R / 1R-break-even exit was retained.
- The later period was used as a chronological check. However, an earlier baseline result from that period had already been observed during development, so it should not be described as a pristine scientific holdout.

## Data limitations

- `USTEC` is an Exness CFD. Its `tick_volume` measures broker quote activity, not centralized Nasdaq exchange volume or full order-book volume.
- Exness's available real-tick archive in the isolated tester began in January 2026. A requested real-tick rerun stalled before its tester agent launched and produced no report. The complete results above therefore use MT5 Every Tick generated from the broker's M1 history, with recorded spread and random execution delay.
- The latest-year result has only six trades. A forward demo period of at least 20–30 trades is recommended before considering live use.

## Files

- `EA/US100 Selective ORB Retest EA.mq5` — source code
- `EA/US100 Selective ORB Retest EA.ex5` — compiled EA
- `Sets/BEST CANDIDATE - US100 USTEC M5 - OR30 RV Retest - 1pct.set` — final preset
- `Backtest Reports/selected/` — native MT5 HTML reports and terminal graphs
- `native-selected-results.json` and `.csv` — parsed statistics and chronological balance data
- `US100 Selective ORB - Full Equity and Drawdown.png` — readable combined graph

## Research references

- Nasdaq official market schedule: https://www.nasdaq.com/market-activity/stock-market-holiday-schedule
- Exness USTEC contract page: https://www.exness.com/indices/us-tech-100/
- Exploratory QQQ opening-range/retest paper: https://papers.ssrn.com/sol3/Delivery.cfm/6745958.pdf?abstractid=6745958&mirid=1
- Strict MNQ OHLCV strategy validation: https://arxiv.org/abs/2605.04004
- Nasdaq volatility/volume/gap regime study: https://arxiv.org/abs/2605.11423
