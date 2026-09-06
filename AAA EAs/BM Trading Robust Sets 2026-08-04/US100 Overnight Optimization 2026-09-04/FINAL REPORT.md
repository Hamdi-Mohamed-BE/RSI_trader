# Step 10 — Nasdaq Overnight Full Re-optimization

## Goal

Compare the current negative-day close-to-open implementation with the video's futures-reopen/calendar alternatives, then select timing, stop, reward/risk, trailing and Friday handling on development data only. The audit also validates Standard and Safe modes natively. Risk stayed at 1% in every test.

## Untouched locked-year results

| Configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| current-negative-close-open | +8.67% | 1.84 | 63.89% | 2.36% | 72 | 4.66 | 3.36 |
| video-negative-reopen-eu3 | -0.22% | 0.91 | 48.39% | 1.52% | 31 | -0.60 | -0.14 |
| video-go-long-reopen-eu3 | -1.99% | 0.71 | 44.29% | 2.25% | 70 | -2.86 | -0.89 |
| high-win Standard | +4.14% | 3.36 | 76.92% | 0.88% | 26 | 7.62 | 4.62 |
| current Safe | +3.50% | 1.89 | 66.67% | 1.98% | 30 | 4.90 | 1.70 |
| high-win Safe | +2.61% | 9.66 | 90.00% | 0.66% | 10 | 2.33 | 3.91 |

## Selected development configuration

`{"definition": 0, "dynamic": true, "entry_hour": 16, "entry_minute": 0, "exit_hour": 9, "exit_minute": 29, "friday": true, "require_negative": true, "rr": 0.75, "stop_pct": 3.0, "threshold": 1.0}`

## Three-year result

Current Standard: +7.81% return, PF 1.29, 55.93% wins, 4.86% max DD, 177 trades, Sharpe 1.94, recovery 1.56.

High-win Standard: +7.00% return, PF 2.35, 69.01% wins, 2.12% max DD, 71 trades, Sharpe 5.10, recovery 3.21.

Current Safe: +4.14% return, PF 1.57, 57.81% wins, 2.03% max DD, 64 trades, Sharpe 3.21, recovery 1.95.

High-win Safe: +3.60% return, PF 10.03, 85.00% wins, 0.65% max DD, 20 trades, Sharpe 8.58, recovery 5.40. The tiny sample makes the inflated PF unsuitable for promotion.

## Monte Carlo

Current Standard, 10,000 paths: profitable 99.22%, return P5 +2.97%, median +8.74%, P95 +14.47%, max-DD P95 3.50%, ruin 0.00%.

High-win Standard, 10,000 paths: profitable 99.96%, return P5 +2.21%, median +4.15%, P95 +6.02%, max-DD P95 0.95%, ruin 0.00%.

## Integrity notes

- The selected rules were chosen only on 2023-09-01 through 2025-08-31. The final year was not used for selection.
- Final comparisons use native MT5 Every Tick data, broker spread, commission, swap and random execution delay.
- The older Go Long binary is input-audited only and was not used for rule selection. The unconditional Go Long idea was implemented in the readable Overnight source so the timing and risk logic could be verified.
- A fixed-R target is optional; calendar exit remains in force if the target is not reached.
- The current Standard setup remains selected because it has the highest untouched-year return, strongest Monte Carlo return floor and a materially larger sample.
- The native Safe filter reduced the active locked-year sample from 72 to 30 trades and produced a negative Monte Carlo P5 return. Full Safe therefore preserves Standard behavior for this EA.
- The optional Safe regime calculation was moved behind the once-per-day time, calendar and signal gates, eliminating an every-tick history-copy bottleneck without changing Standard trades.
