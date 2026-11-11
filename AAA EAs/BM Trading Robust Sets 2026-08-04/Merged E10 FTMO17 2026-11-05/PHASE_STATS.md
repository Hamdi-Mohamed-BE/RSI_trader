# Per-phase FTMO stats, $100k, Monte Carlo 2,000 paths (2021-10 -> 2026-10 streams, in-sample)

Phase rows count only the paths that reached that phase (Phase 2 = paths that passed Phase 1). Days = calendar days from the phase start, inclusive. Trading days = days with at least one entry.
Worst closed day = biggest loss of trades CLOSED on one day in that phase (median / 95th percentile / worst path). Floating = worst intraday equity loss of the whole path, reported separately.

## FTMO 2-step

| Portfolio | Guard | Risk | Phase | Reached | Pass | Median days to pass | Breach | Median days to breach | Median trading days before breach | Worst closed day (median / p95 / max) | Breaches (paths) | Overall pass / breach | Floating worst day (median / p95 / max) |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|---:|---|---|
| Core 9 | guard | 0.50% | Phase 1 | 100% | 87% | 80 | 0% | - | - | $1,483 / $1,722 / $2,461 | 0 | 66% / 0% | $1,542 / $1,893 / $2,967 |
| Core 9 | guard | 0.50% | Phase 2 | 87% | 76% | 36 | 0% | - | - | $1,083 / $1,653 / $2,461 | 0 | 66% / 0% | $1,542 / $1,893 / $2,967 |
| Core 9 | guard | 0.75% | Phase 1 | 100% | 87% | 57 | 0% | - | - | $1,638 / $2,376 / $3,594 | 0 | 74% / 0% | $2,102 / $2,590 / $3,570 |
| Core 9 | guard | 0.75% | Phase 2 | 87% | 85% | 27 | 0% | - | - | $1,512 / $2,340 / $2,934 | 0 | 74% / 0% | $2,102 / $2,590 / $3,570 |
| Core 9 | guard | 1.00% | Phase 1 | 100% | 80% | 47 | 0% | - | - | $2,015 / $2,308 / $3,912 | 0 | 67% / 0% | $2,037 / $2,443 / $3,880 |
| Core 9 | guard | 1.00% | Phase 2 | 80% | 84% | 21 | 0% | - | - | $1,945 / $2,234 / $3,912 | 0 | 67% / 0% | $2,037 / $2,443 / $3,880 |
| Core 9 | no guard | 0.50% | Phase 1 | 100% | 90% | 74 | 1% | 89 | 59 | $1,544 / $1,984 / $2,402 | 17 | 72% / 1% | $1,739 / $2,176 / $3,106 |
| Core 9 | no guard | 0.50% | Phase 2 | 90% | 80% | 35 | 0% | 59 | 40 | $1,100 / $1,835 / $2,369 | 6 | 72% / 1% | $1,739 / $2,176 / $3,106 |
| Core 9 | no guard | 0.75% | Phase 1 | 100% | 93% | 52 | 4% | 55.5 | 36.5 | $1,971 / $2,870 / $3,623 | 86 | 84% / 7% | $2,446 / $3,074 / $4,780 |
| Core 9 | no guard | 0.75% | Phase 2 | 93% | 90% | 25 | 3% | 40.5 | 26 | $1,564 / $2,714 / $3,692 | 52 | 84% / 7% | $2,446 / $3,074 / $4,780 |
| Core 9 | no guard | 1.00% | Phase 1 | 100% | 90% | 39 | 9% | 43 | 28 | $2,310 / $3,770 / $5,113 | 179 | 84% / 14% | $3,088 / $3,969 / $6,126 |
| Core 9 | no guard | 1.00% | Phase 2 | 90% | 93% | 19 | 6% | 26.5 | 18 | $2,028 / $3,457 / $4,452 | 102 | 84% / 14% | $3,088 / $3,969 / $6,126 |
| E10 | guard | 0.50% | | missing |||||||||
| E10 | guard | 0.75% | | missing |||||||||
| E10 | guard | 1.00% | | missing |||||||||
| E10 | no guard | 0.50% | | missing |||||||||
| E10 | no guard | 0.75% | | missing |||||||||
| E10 | no guard | 1.00% | | missing |||||||||
| FTMO17 | guard | 0.50% | | missing |||||||||
| FTMO17 | guard | 0.75% | | missing |||||||||
| FTMO17 | guard | 1.00% | | missing |||||||||
| FTMO17 | no guard | 0.50% | | missing |||||||||
| FTMO17 | no guard | 0.75% | | missing |||||||||
| FTMO17 | no guard | 1.00% | Phase 1 | 100% | 75% | 30 | 25% | 30 | 21 | $3,088 / $5,329 / $7,021 | 497 | 65% / 34% | $3,822 / $5,927 / $7,013 |
| FTMO17 | no guard | 1.00% | Phase 2 | 75% | 87% | 16 | 12% | 23 | 17 | $2,419 / $4,880 / $6,319 | 184 | 65% / 34% | $3,822 / $5,927 / $7,013 |

## FTMO 1-Step

| Portfolio | Guard | Risk | Phase | Reached | Pass | Median days to pass | Breach | Median days to breach | Median trading days before breach | Worst closed day (median / p95 / max) | Breaches (paths) | Overall pass / breach | Floating worst day (median / p95 / max) |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|---:|---|---|
| Core 9 | guard | 0.50% | Challenge | 100% | 85% | 80 | 0% | - | - | $1,317 / $1,652 / $2,392 | 0 | 85% / 0% | $1,465 / $1,795 / $2,967 |
| Core 9 | guard | 0.75% | Challenge | 100% | 76% | 65 | 0% | - | - | $1,538 / $2,249 / $2,934 | 0 | 76% / 0% | $1,555 / $2,243 / $2,910 |
| Core 9 | guard | 1.00% | Challenge | 100% | 61% | 71 | 3% | 43 | 18 | $1,996 / $2,168 / $3,912 | 55 | 61% / 3% | $1,994 / $2,282 / $3,880 |
| Core 9 | no guard | 0.50% | Challenge | 100% | 89% | 74 | 3% | 93 | 60 | $1,545 / $1,984 / $2,402 | 59 | 89% / 3% | $1,674 / $2,111 / $3,106 |
| Core 9 | no guard | 0.75% | Challenge | 100% | 84% | 52 | 15% | 58 | 37.5 | $1,971 / $2,896 / $3,860 | 298 | 84% / 15% | $2,267 / $3,039 / $4,780 |
| Core 9 | no guard | 1.00% | Challenge | 100% | 48% | 30 | 52% | 22 | 14 | $2,310 / $3,725 / $5,090 | 1039 | 48% / 52% | $2,855 / $3,652 / $5,088 |
| E10 | guard | 0.50% | | missing |||||||||
| E10 | guard | 0.75% | | missing |||||||||
| E10 | guard | 1.00% | | missing |||||||||
| E10 | no guard | 0.50% | | missing |||||||||
| E10 | no guard | 0.75% | | missing |||||||||
| E10 | no guard | 1.00% | | missing |||||||||
| FTMO17 | guard | 0.50% | | missing |||||||||
| FTMO17 | guard | 0.75% | | missing |||||||||
| FTMO17 | guard | 1.00% | | missing |||||||||
| FTMO17 | no guard | 0.50% | | missing |||||||||
| FTMO17 | no guard | 0.75% | | missing |||||||||
| FTMO17 | no guard | 1.00% | | missing |||||||||

## Funded (FTMO standard funded rules, 36-month MC)

| Portfolio | Guard | Risk | Income / month while trading (median) | 36 m total median | Breach | Frozen | Still trading | Median days to breach | Median trading days before breach | Median days to freeze | Worst closed day (median / p95 / max) | Floating worst day (median / p95 / max) | Trades / month |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|
| Core 9 | guard | 0.50% | missing ||||||||||
| Core 9 | guard | 0.75% | missing ||||||||||
| Core 9 | guard | 1.00% | missing ||||||||||
| Core 9 | no guard | 0.50% | missing ||||||||||
| Core 9 | no guard | 0.75% | missing ||||||||||
| Core 9 | no guard | 1.00% | missing ||||||||||
| E10 | guard | 0.50% | missing ||||||||||
| E10 | guard | 0.75% | missing ||||||||||
| E10 | guard | 1.00% | missing ||||||||||
| E10 | no guard | 0.50% | missing ||||||||||
| E10 | no guard | 0.75% | missing ||||||||||
| E10 | no guard | 1.00% | missing ||||||||||
| FTMO17 | guard | 0.50% | missing ||||||||||
| FTMO17 | guard | 0.75% | missing ||||||||||
| FTMO17 | guard | 1.00% | missing ||||||||||
| FTMO17 | no guard | 0.50% | missing ||||||||||
| FTMO17 | no guard | 0.75% | missing ||||||||||
| FTMO17 | no guard | 1.00% | missing ||||||||||
