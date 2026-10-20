# FTMO risk-approach search: funded within 90 days at 70% (2026-10-20)

Owner request: find, from all our EAs, the best risk management and trading approach to get funded within 3 months, with a pass rate of 70% or more for both phases.

**Result: no configuration reaches 70%.** The best development rate for funded within 90 days was 47.2%.

Validation (starts from 2023-10 to 2024-04):
- All five finalists fell to 2-22%.
- The rule chose **CORE4_PLUS_FIVE_ORBS_05R · $150 / $150 · latch $450 · buffer $9100**, which did not meet the target (21.8%).

Out-of-sample (2024-10 to 2026-04 starts, previously inspected):
- The choice reached **67.8%** funded within 90 days, 75.1% passed within 180 days, median 47.5 days.
- The best finalist reached 68.9%.

So even the best risk setting only gets near 70% in favourable regimes.
- **What speeds it up:** larger risk, a lower $9,100 entry buffer and a $450 daily stop all make passes faster.
- **What they cost:** the worst drawdown from the peak grows to about $2,000. The pass rate in bad regimes (2023-24) is not rescued.

Method:
- **Configurations:** 168 risk configurations = 7 baskets × phase-1 cap ($100 / $150 / $200) × phase-2 risk (same or half) × daily latch/reserve ($300 / $450) × entry buffer ($9,200 / $9,100).
- **Data and engine:** the same frozen data and engine as the Fastest Funded Search. Parity check: 14 standard-guard configurations reproduced that search exactly.
- **Split:** development / validation / out-of-sample, pre-declared in `PLAN.json` and hash-frozen in `FROZEN.json`.
- **Funded:** both phases passed plus 5 business days.

## Development (top 20 of 168)

| Configuration | Funded ≤ 90 d (avg; recorded / stress) | Passed ≤ 180 d (avg) | Median days to funded | Breach share | Hit buffer | Worst equity DD $ | Worst day $ | Trades /month / weekday |
|---|---|---:|---:|---:|---:|---:|---:|---|
| ALL12 · $200 / $200 · latch $300 · buffer $9100 | 47.2% (51.8% / 42.6%) | 69.5% | 70.5 | 0.0% | 51.7% | 1,946 | 387 | 14.19 / 0.653 |
| CORE4_PLUS_H1_ORB_05R · $150 / $150 · latch $450 · buffer $9100 | 43.8% (47.7% / 39.8%) | 49.9% | 58.8 | 0.0% | 62.2% | 1,937 | 370 | 28.54 / 1.312 |
| ALL12 · $200 / $200 · latch $300 · buffer $9200 | 42.3% (47.7% / 37.0%) | 61.4% | 70.0 | 0.0% | 64.2% | 1,842 | 387 | 12.48 / 0.574 |
| CORE4_PLUS_FIVE_ORBS_05R · $150 / $150 · latch $450 · buffer $9100 | 41.2% (43.6% / 38.8%) | 47.7% | 56.5 | 0.0% | 69.4% | 2,107 | 362 | 22.54 / 1.037 |
| ALL12 · $200 / $200 · latch $450 · buffer $9100 | 40.9% (45.4% / 36.5%) | 49.6% | 59.5 | 0.0% | 64.5% | 1,870 | 418 | 12.46 / 0.573 |
| CORE4 · $150 / $150 · latch $450 · buffer $9100 | 39.4% (45.1% / 33.7%) | 46.7% | 59.8 | 0.0% | 60.3% | 2,116 | 362 | 21.52 / 0.99 |
| ALL12 · $200 / $100 · latch $300 · buffer $9100 | 39.3% (44.9% / 33.7%) | 65.2% | 80.8 | 0.0% | 45.7% | 1,946 | 387 | 23.99 / 1.104 |
| CORE4_PLUS_EMA3 · $200 / $200 · latch $450 · buffer $9100 | 38.9% (46.9% / 30.9%) | 49.4% | 59.2 | 0.0% | 75.5% | 2,201 | 408 | 10.75 / 0.495 |
| CORE4_PLUS_H1_ORB_05R · $150 / $150 · latch $450 · buffer $9200 | 38.6% (42.1% / 35.2%) | 42.9% | 57.5 | 0.0% | 74.1% | 1,720 | 370 | 10.65 / 0.49 |
| CORE4_PLUS_EMA3 · $150 / $150 · latch $450 · buffer $9100 | 38.0% (45.1% / 30.9%) | 53.8% | 64.5 | 0.0% | 65.6% | 2,027 | 376 | 19.34 / 0.889 |
| CORE4_PLUS_EMA3 · $150 / $150 · latch $450 · buffer $9200 | 37.1% (47.4% / 26.8%) | 48.0% | 60.0 | 0.0% | 74.1% | 1,885 | 376 | 18.26 / 0.84 |
| ALL12 · $200 / $200 · latch $450 · buffer $9200 | 37.1% (41.1% / 33.2%) | 47.6% | 61.5 | 0.0% | 78.4% | 1,870 | 418 | 11.19 / 0.515 |
| CORE4_PLUS_EMA3 · $150 / $150 · latch $300 · buffer $9100 | 36.5% (43.9% / 29.1%) | 67.9% | 87.0 | 0.0% | 40.8% | 1,738 | 290 | 13.2 / 0.607 |
| ALL12 · $200 / $100 · latch $300 · buffer $9200 | 36.4% (41.8% / 30.9%) | 60.7% | 80.8 | 0.0% | 60.3% | 1,842 | 387 | 23.16 / 1.065 |
| CORE4_PLUS_FIVE_ORBS_05R · $200 / $100 · latch $450 · buffer $9100 | 36.0% (43.1% / 28.8%) | 43.4% | 68.8 | 0.0% | 70.9% | 2,013 | 412 | 13.02 / 0.599 |
| ALL12 · $150 / $150 · latch $300 · buffer $9100 | 35.8% (39.0% / 32.6%) | 59.6% | 76.2 | 0.0% | 44.5% | 1,928 | 290 | 15.73 / 0.723 |
| ALL12 · $150 / $150 · latch $300 · buffer $9200 | 35.6% (38.8% / 32.4%) | 55.6% | 72.8 | 0.0% | 51.0% | 1,778 | 290 | 14.88 / 0.684 |
| CORE4_PLUS_EMA3 · $150 / $150 · latch $300 · buffer $9200 | 35.6% (42.9% / 28.3%) | 63.9% | 84.8 | 0.0% | 50.8% | 1,738 | 290 | 12.77 / 0.587 |
| CORE4_PLUS_H1_ORB_05R · $200 / $100 · latch $450 · buffer $9100 | 35.6% (40.1% / 31.1%) | 42.9% | 67.0 | 0.0% | 66.3% | 1,940 | 412 | 13.19 / 0.607 |
| CORE4_PLUS_GOLD_VA_H1_ORB · $150 / $150 · latch $450 · buffer $9100 | 34.9% (41.6% / 28.3%) | 42.1% | 59.0 | 0.0% | 77.2% | 2,071 | 367 | 37.2 / 1.711 |

## Validation (finalists)

| Configuration | Funded ≤ 90 d (avg; recorded / stress) | Passed ≤ 180 d (avg) | Median days to funded | Breach share | Hit buffer | Worst equity DD $ | Worst day $ | Trades /month / weekday |
|---|---|---:|---:|---:|---:|---:|---:|---|
| ALL12 · $200 / $200 · latch $300 · buffer $9100 | 1.9% (3.0% / 0.8%) | 9.8% | 147.0 | 0.0% | 98.1% | 1,741 | 286 | 5.24 / 0.241 |
| CORE4_PLUS_H1_ORB_05R · $150 / $150 · latch $450 · buffer $9100 | 20.3% (22.6% / 18.1%) | 22.9% | 69.5 | 0.0% | 86.5% | 1,898 | 354 | 7.61 / 0.35 |
| ALL12 · $200 / $200 · latch $300 · buffer $9200 | 2.3% (3.8% / 0.8%) | 5.6% | 92.5 | 0.0% | 99.2% | 1,704 | 286 | 3.89 / 0.179 |
| CORE4_PLUS_FIVE_ORBS_05R · $150 / $150 · latch $450 · buffer $9100 | 21.8% (24.8% / 18.8%) | 27.1% | 63.5 | 0.0% | 82.0% | 1,925 | 356 | 8.29 / 0.381 |
| ALL12 · $200 / $200 · latch $450 · buffer $9100 | 21.1% (28.6% / 13.5%) | 27.4% | 57.2 | 0.0% | 82.3% | 1,911 | 413 | 9.64 / 0.443 |

## Out-of-sample, previously inspected (finalists, evaluated once)

| Configuration | Funded ≤ 90 d (avg; recorded / stress) | Passed ≤ 180 d (avg) | Median days to funded | Breach share | Hit buffer | Worst equity DD $ | Worst day $ | Trades /month / weekday |
|---|---|---:|---:|---:|---:|---:|---:|---|
| ALL12 · $200 / $200 · latch $300 · buffer $9100 | 62.9% (66.0% / 59.9%) | 83.0% | 68.0 | 0.0% | 29.7% | 1,886 | 404 | 18.49 / 0.851 |
| CORE4_PLUS_H1_ORB_05R · $150 / $150 · latch $450 · buffer $9100 | 68.9% (74.6% / 63.2%) | 78.7% | 49.5 | 0.0% | 38.2% | 1,750 | 404 | 30.79 / 1.416 |
| ALL12 · $200 / $200 · latch $300 · buffer $9200 | 62.4% (65.5% / 59.4%) | 80.1% | 67.0 | 0.0% | 48.9% | 1,880 | 404 | 18.37 / 0.845 |
| CORE4_PLUS_FIVE_ORBS_05R · $150 / $150 · latch $450 · buffer $9100 | 67.8% (72.3% / 63.2%) | 75.1% | 47.5 | 0.0% | 42.6% | 1,721 | 404 | 33.5 / 1.541 |
| ALL12 · $200 / $200 · latch $450 · buffer $9100 | 49.1% (53.3% / 44.9%) | 62.8% | 63.0 | 0.0% | 74.9% | 2,069 | 405 | 23.75 / 1.092 |

## What this does NOT prove

- **Previously inspected.** All windows were inspected before.
- **Simulated execution.** Prices are generated-tick Exness proxies before 2026, equity is sampled every 5 minutes, and the guard's behaviour is modelled rather than run in a terminal.
- **Breach risk is understated.** Lowering the buffer and raising the daily stop moves the account closer to FTMO's real limits. A zero breach share in replay is not zero risk, especially with gaps.
- **Retrospective out-of-sample.** The out-of-sample 68% is not a forecast.

## Files

- [PLAN.json](PLAN.json), [FROZEN.json](FROZEN.json), [run.py](run.py).
- [DEV.json](DEV.json), [VAL.json](VAL.json), [OOS.json](OOS.json).
