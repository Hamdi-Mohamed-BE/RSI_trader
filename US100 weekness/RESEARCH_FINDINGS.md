# Completed broker-history research

## Data

- Broker/account: MEXAtlantic-Demo, connected MT5 account.
- Detected instrument: `UT100`, described by the broker as **US Tech 100 Index**.
- Period: 2025-07-30 through 2026-07-29.
- Bars: 353,771 broker M1 bars.
- Model: bid OHLC plus each bar's historical spread; short exits use reconstructed
  ask prices. Same-minute ambiguity is pessimistic.
- Costs: one strategy pip of slippage on entry/exit; historical spread; commission
  configured as zero because no dependable per-lot commission schedule was exposed.
- One strategy pip = 1.0 index unit = 100 broker points = 100 ticks. At this broker,
  one strategy pip at one lot is approximately $1.

## Baseline, one year

| Component | Trades | Win rate | PF | Net | Max DD |
|---|---:|---:|---:|---:|---:|
| A fixed | 248 | 33.47% | 0.97 | -$115.97 | 4.25% |
| A runner | 248 | 21.77% | 0.46 | -$657.36 | 6.81% |
| B1 | 100 | 23.00% | 0.49 | -$1,868.11 | 21.73% |
| B2, baseline 2R | 54 | 48.15% | 1.72 | +$886.31 | 3.20% |
| Combined | 650 | 28.62% | 0.82 | -$1,755.13 | 25.38% |

The original combined rules are therefore **not suitable for live trading** on this
broker sample.

## Walk-forward unseen results

Two chronological folds used 180 training days followed by 90 unseen days. All
four components combined still lost money: 332 trades, 29.22% wins, PF 0.92,
-$470.28, and 16.33% maximum modeled drawdown.

`B2` was the only component that remained positive in both unseen folds. Both
training windows independently selected the original close-plus-50 pullback with
a 3R target:

| B2 unseen only | Trades | Win rate | PF | Net | Max DD |
|---|---:|---:|---:|---:|---:|
| Selected 3R variants | 33 | 42.42% | 1.71 | +$665.72 | 4.08% |

For context—not as out-of-sample proof—the full-year B2 3R replay produced 54
trades, 48.15% wins, PF 2.08, +$1,603.12, and 4.22% maximum modeled drawdown.

The safety-locked research profile is `.env.research_best`. It disables Strategy A
and B1, enables only B2, uses the close-plus-50 entry, 100-pip stop, and 3R target.
It remains dry-run and should undergo forward demo testing.

## Robustness and weaknesses

The full baseline remained unprofitable in every spread/slippage stress scenario.
Doubling spread reduced PF to 0.80; adding five pips of slippage reduced PF to
0.57.

The separate B2/3R stress replay was materially stronger:

| Scenario | PF | Net | Max DD |
|---|---:|---:|---:|
| Baseline | 2.08 | +$1,603.12 | 4.22% |
| Spread +100% | 2.07 | +$1,596.73 | 4.22% |
| Additional 2-pip slippage | 1.96 | +$1,479.20 | 4.44% |
| Additional 5-pip slippage | 1.80 | +$1,292.49 | 4.74% |

Ten thousand outcome-order permutations gave a 2.73% median maximum drawdown,
4.42% 95th-percentile drawdown, 5.44% 99th-percentile drawdown, and 8.33% worst
observed reshuffled drawdown. Removing the single best trade left +$1,433.26 and
PF 1.97.

The B2 sample is only 54 full-year trades and 33 unseen trades, so even its
positive and stress-resistant result is not statistically sufficient for
unattended live deployment.

Historical data is M1, not real ticks. The report therefore does not claim
1/2/5/10-second delay tests or exact tick-sequence fidelity. The news filter is
safe-off by default; if enabled without a trusted calendar adapter, live entries
are refused.
