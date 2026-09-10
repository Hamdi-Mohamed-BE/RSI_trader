# LTA Volume Profile — FTMO vs Exness

## Controlled test

- EA: current compiled `LTA_Concepts_EA.ex5`
- Mode: recommended Safe mode (completed-D1 Markov gate enabled)
- Symbol/timeframe: XAUUSD M15
- Period: 2023-09-05 through 2026-09-05
- Starting balance: USD 10,000
- Risk: 1% dynamic equity risk per trade
- Target: 3R
- Profile: M15, 64 bins, 70% value area
- Model: MT5 Every Tick with random execution delay
- FTMO leverage: 1:100
- FTMO account/feed: FTMO-Demo, $200k Free Trial 2-Step login

## Results

| Metric | Exness Safe | FTMO Safe | FTMO minus Exness |
|---|---:|---:|---:|
| Final balance | $26,331.16 | $20,292.54 | -$6,038.62 |
| Net profit | $16,331.16 | $10,292.54 | -$6,038.62 |
| Return | +163.31% | +102.93% | -60.38 pp |
| Profit factor | 1.33 | 1.23 | -0.10 |
| Win rate | 31.35% | 29.98% | -1.37 pp |
| Maximum equity drawdown | 20.57% | 12.62% | -7.95 pp |
| Total trades | 437 | 437 | 0 |
| Sharpe ratio | 4.01 | 2.84 | -1.17 |
| Recovery factor | 5.43 | 3.59 | -1.84 |
| Maximum win streak | 5 | 4 | -1 |
| Maximum losing streak | 15 | 13 | -2 |
| History quality | 98% | 99% | +1 pp |

## Trade-path comparison

- Raw report timestamps use different broker clocks. After normalizing FTMO's observed EET/EEST server clock to UTC, 150 of 437 entries matched Exness at the exact timestamp and direction (34.32%).
- With a 15-minute tolerance after clock normalization, 169 entries matched (38.67%); 96.45% of those matched trades agreed on win versus loss.
- FTMO produced 131 winning and 306 losing trades; Exness produced 137 winning and 300 losing trades.
- FTMO average winning trade: $416.92; average losing trade: -$144.85.
- Exness average winning trade: $474.36; average losing trade: -$162.19.
- The identical total trade count hides a substantially different sequence of signals: roughly two-thirds of entries still do not align exactly after broker-clock normalization. This is consistent with LTA's dependence on broker tick volume, bar construction, prior-day/week profiles, and volume-qualified expansion/confirmation.

## Decision

FTMO remains profitable in this native test, but its edge is weaker than Exness: return, PF, win rate, Sharpe and recovery all declined. Drawdown improved materially. Because exact clock-normalized entry overlap is only 34.32%, the EA is broker-sensitive and should not be assumed portable from Exness to FTMO without separate FTMO validation.

No recommended-system, BAT, EA, cache, or website setting was changed by this comparison.
