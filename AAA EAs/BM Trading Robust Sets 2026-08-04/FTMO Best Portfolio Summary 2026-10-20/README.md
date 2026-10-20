# Best FTMO portfolio summary, after lowering the target to 65% (2026-10-20)

The owner lowered the target from 70% to 65% **after** the searches had run. The table below therefore ranks every configuration that was run on all three windows across **all history** (919 Prague-weekday starts, 2021-10 to 2026-04). It is a post-hoc, in-sample ranking, not a validated selection.

Definitions:
- **Pass:** both FTMO 2-step Swing phases completed within 180 days with no breach.
- **Funded:** pass plus 5 business days of review.
- **Rates:** the average of the recorded-cost and cost-stress scenarios.
- **Windows:** development is 2021-10 to 2023-04 starts (392), validation is 2023-10 to 2024-04 (133), and OOS is 2024-10 to 2026-04 (394).

| # | Configuration | Source | Pass ≤180 d: dev / val / OOS | **All-history pass ≤180 d** | Funded ≤90 d (all history) | Median days to funded (approx) | Breaches | Worst eq DD $ | Worst day $ | Trades /month (/weekday) |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | CORE4_PLUS_FIVE_ORBS_05R · $100 · standard guard | Fastest Funded Search | 58% / 28% / 97% | **70%** | — | 81.8 | 0 | 1,740 | 271 | 34.71 (1.596) |
| 2 | PR9_PLUS_NASDAQ_OVERNIGHT · $100 · standard guard | Fastest Funded Search | 58% / 27% / 95% | **69%** | — | 80.0 | 0 | 1,740 | 271 | 38.67 (1.779) |
| 3 | CORE4_PLUS_H1_ORB_05R · $100 · standard guard | Fastest Funded Search | 60% / 21% / 94% | **69%** | — | 83.0 | 0 | 1,796 | 271 | 31.65 (1.456) |
| 4 | CORE4 · $100 · standard guard | Fastest Funded Search | 57% / 24% / 94% | **68%** | — | 87.0 | 0 | 1,761 | 271 | 28.44 (1.308) |
| 5 | ALL12 · $200 / $200 · latch $300 · buffer $9100 | Risk Approach Search | 70% / 10% / 83% | **67%** | 47% | 80.5 | 0 | 1,946 | 404 | 18.49 (0.851) |
| 6 | ALL12 · $200 / $200 · latch $300 · buffer $9200 | Risk Approach Search | 61% / 6% / 80% | **61%** | 45% | 72.0 | 0 | 1,880 | 404 | 18.37 (0.845) |
| 7 | CORE4_PLUS_EMA3 · $150 · standard guard | Fastest Funded Search | 64% / 6% / 71% | **59%** | — | 96.6 | 0 | 1,839 | 303 | 13.74 (0.632) |
| 8 | CORE4_PLUS_H1_ORB_05R · $150 / $150 · latch $450 · buffer $9100 | Risk Approach Search | 50% / 23% / 79% | **58%** | 51% | 56.3 | 0 | 1,937 | 404 | 30.79 (1.416) |
| 9 | CORE4_PLUS_FIVE_ORBS_05R · $150 / $150 · latch $450 · buffer $9100 | Risk Approach Search | 48% / 27% / 75% | **56%** | 50% | 53.7 | 0 | 2,107 | 404 | 33.5 (1.541) |
| 10 | LLN_PF095 · $50 · standard guard | LLN test | 23% / 54% / 87% | **55%** | 31% | 83.7 | 0 | 2,005 | 255 | 55.24 (2.541) |
| 11 | LLN_ALL · $50 · standard guard | LLN test | 12% / 47% / 97% | **54%** | 29% | 84.6 | 0 | 1,982 | 252 | 71.52 (3.29) |
| 12 | ALL12 · $200 / $200 · latch $450 · buffer $9100 | Risk Approach Search | 50% / 27% / 63% | **52%** | 42% | 60.7 | 0 | 2,069 | 418 | 23.75 (1.092) |
| 13 | EDGE_PF110 · $100 · standard guard | LLN test | 49% / 94% / 40% | **51%** | 4% | 140.7 | 0 | 1,559 | 222 | 17.39 (0.8) |
| 14 | LLN_ALL · $100 · standard guard | LLN test | 14% / 62% / 73% | **46%** | 34% | 64.6 | 0 | 2,062 | 425 | 39.08 (1.797) |
| 15 | LLN_ALL · $25 · standard guard | LLN test | 3% / 11% / 99% | **45%** | 10% | 105.6 | 0 | 1,244 | 144 | 82.87 (3.812) |
| 16 | EDGE_PF110 · $150 · standard guard | LLN test | 23% / 30% / 57% | **39%** | 5% | 127.5 | 0 | 1,866 | 260 | 10.99 (0.506) |
| 17 | LLN_PF095 · $25 · standard guard | LLN test | 1% / 39% / 77% | **39%** | 4% | 147.9 | 0 | 1,305 | 140 | 61.57 (2.832) |
| 18 | LLN_PF095 · $100 · standard guard | LLN test | 17% / 10% / 67% | **37%** | 28% | 68.0 | 0 | 2,297 | 444 | 25.07 (1.153) |
| 19 | LLN_PF095 · $150 · standard guard | LLN test | 13% / 3% / 56% | **30%** | 24% | 72.7 | 0 | 2,302 | 461 | 14.89 (0.685) |
| 20 | LLN_ALL · $150 · standard guard | LLN test | 1% / 27% / 50% | **26%** | 22% | 52.6 | 0 | 2,305 | 461 | 14.35 (0.66) |
| 21 | EDGE_PF110 · $50 · standard guard | LLN test | 0% / 17% / 0% | **2%** | 0% | 172.0 | 0 | 609 | 151 | 16.83 (0.774) |
| 22 | EDGE_PF110 · $25 · standard guard | LLN test | 0% / 0% / 0% | **0%** | 0% | None | 0 | 281 | 67 | 13.87 (0.638) |

For the top four (each at $100 with the standard guard), the share completing both phases within 90 days is about **46–47%** across all history (31% / 16–22% / 69–72% across development, validation and OOS).

## Answer

1. **Best at 65%: Prop Ready 9 at $100 per trade with the standard guard.**
   - **70%** all-history pass within 180 days (58% / 28% / 97% by window).
   - Median about 82 days to funded, and about 46% done within 90 days.
   - 0 breaches, but the worst equity drawdown reached $1,740 and the worst day $271 (sampled).
2. **Funded within 3 months at 65%: not achieved by any configuration across all history.**
   - The fastest risk settings (Prop Ready 9 or CORE4 + H1 ORB at $150, with a $450 daily stop and a $9,100 buffer) reach 50–51% funded within 90 days, median about 54–56 days.
   - Their pass rate within 180 days is only 56–58%.
3. **The pass rate is driven by the market regime.** Every configuration scored 6–28% for 2023-24 starts and 71–97% for 2024-26 starts.
4. **Not deployed.** $100 needs both the EA risk request and the guard caps raised in a hashed Prop Ready build, plus the open items from the dial-study Bear review. Nothing was changed.

## Sources

- [FTMO Fastest Funded Search](../FTMO%20Fastest%20Funded%20Search%202026-10-20/REPORT.md)
- [FTMO Risk Approach Search](../FTMO%20Risk%20Approach%20Search%202026-10-20/REPORT.md)
- [Law of Large Numbers test](../FTMO%20Law%20Of%20Large%20Numbers%20Test%202026-10-20/REPORT.md)
- [Prop Ready older history](../FTMO%20Prop%20Ready%20Older%20History%202026-10-20/REPORT.md)
- [Dial study](../FTMO%20Dial%20Study%202026-10-20/REPORT.md)
