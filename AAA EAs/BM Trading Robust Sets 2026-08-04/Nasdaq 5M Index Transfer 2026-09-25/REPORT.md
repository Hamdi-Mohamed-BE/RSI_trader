# Nasdaq 5M candle momentum — transfer to US500 and US30 (2026-09-25)

User request: run the same 5M momentum on the S&P 500 (US500) and compare side by side. US30 added (same 09:30 NY
open). Unchanged production DI EX5 + claude_eas SET, DI on and off; isolated tester, Exness-MT5Trial16, $10,000,
1% risk, M5, Model 4 (real ticks from 2026-01), 150 ms delay; windows 6m/1y/3y/5y ending 2026-09-25. 24 runs.
Full tables with streaks and costs: `RESULTS.md`.

## 5-year result (trades, per month, per trading day)

| Symbol | Version | Trades | /mo | /day | Return | PF | Win | Max DD |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| USTEC | DI (current) | 968 | 16.1 | 0.74 | +180.2% | 1.22 | 41% | 10.9% |
| USTEC | no DI | 1,272 | 21.2 | 0.98 | +133.8% | 1.14 | 39% | 12.9% |
| US500 | DI | 973 | 16.2 | 0.75 | +1.9% | 1.00 | 37% | 36.1% |
| US500 | no DI | 1,269 | 21.2 | 0.97 | −24.5% | 0.96 | 36% | 53.5% |
| US30 | DI | 956 | 15.9 | 0.73 | −60.0% | 0.85 | 35% | 62.5% |
| US30 | no DI | 1,268 | 21.1 | 0.97 | −56.4% | 0.89 | 35% | 58.6% |

## Conclusions

1. The edge is Nasdaq-specific. US500 is flat-to-negative over 3y/5y (1y: DI +13.9%, no-DI +20.2% — consistent with the
   earlier `SP500 Existing Strategies Retest 2026-09-19` +21.7% one-year result), US30 loses in every window.
2. USTEC DI reproduces `Nasdaq 5M QuantLab Style Research 2026-09-25` CURRENT exactly (+180.24%, 968 trades) — consistency check.
3. Recommendation: keep the bot on USTEC only; do not add US500/US30 versions.
