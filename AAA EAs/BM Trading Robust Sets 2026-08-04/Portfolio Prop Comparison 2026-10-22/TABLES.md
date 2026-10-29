# Five portfolios under FTMO 2-step rules · $100k · recorded Exness costs (generated from RESULT-*.json)

Challenge: phase 1 +10%, phase 2 +5%, min 4 trading days, 5% daily / 10% max loss, 180-day horizon from purchase.
Funded: $100k, 80% split, reward every 14 days (min $20), balance re-baselined after each reward, until breach or freeze.
MC = 2,000 block-bootstrap paths (4-week blocks) from the 2021-10-07 → 2026-10-06 signal pool; History = every weekday start.

## Challenge · Monte Carlo

| Portfolio | Risk / trade | Pass both ≤180 d | Funded ≤90 d | Breach | Stuck at buffer | Median days to pass both | Median days to funded | Median challenge trades |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| FTMO guarded · Current 14 + ORB (17 EAs) | 0.50% | 62% | 15% | 0% | 13% | 110 | 117 | 271.5 |
| FTMO guarded · Current 14 + ORB (17 EAs) | 0.75% | 69% | 28% | 0% | 36% | 94 | 101 | 156 |
| FTMO guarded · Current 14 + ORB (17 EAs) | 1.00% | 58% | 29% | 0% | 51% | 82 | 89 | 90.5 |
| Current 14 + ORB 0.5R (17 EAs, no guard) | 0.50% | 76% | 29% | 4% | 0% | 97.5 | 104.5 | 294 |
| Current 14 + ORB 0.5R (17 EAs, no guard) | 0.75% | 81% | 48% | 13% | 0% | 74.0 | 81.0 | 191 |
| Current 14 + ORB 0.5R (17 EAs, no guard) | 1.00% | 64% | 51% | 35% | 0% | 53 | 60 | 118.5 |
| ORB-only (5 ORBs, no guard) | 0.50% | 0% | 0% | 0% | 0% | - | - | 57 |
| ORB-only (5 ORBs, no guard) | 0.75% | 0% | 0% | 0% | 0% | 164 | 171 | 57 |
| ORB-only (5 ORBs, no guard) | 1.00% | 2% | 0% | 0% | 0% | 163 | 170 | 57 |
| Prop ready (9 EAs, Nasdaq DI ON) | 0.50% | 53% | 9% | 0% | 8% | 123 | 130 | 206 |
| Prop ready (9 EAs, Nasdaq DI ON) | 0.75% | 70% | 31% | 0% | 26% | 89.0 | 96.0 | 118 |
| Prop ready (9 EAs, Nasdaq DI ON) | 1.00% | 62% | 42% | 0% | 45% | 67 | 74 | 71 |
| Best Prop (9 EAs, Nasdaq DI OFF) | 0.50% | 49% | 11% | 0% | 12% | 122 | 129 | 232 |
| Best Prop (9 EAs, Nasdaq DI OFF) | 0.75% | 63% | 30% | 0% | 35% | 87.0 | 94.0 | 120 |
| Best Prop (9 EAs, Nasdaq DI OFF) | 1.00% | 54% | 40% | 0% | 54% | 60.0 | 67.0 | 64 |

## Challenge · History, every weekday start

| Portfolio | Risk / trade | Pass both ≤180 d | Funded ≤90 d | Breach | Stuck at buffer | Median days to pass both | Median days to funded | Median challenge trades |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| FTMO guarded · Current 14 + ORB (17 EAs) | 0.50% | 67% | 20% | 0% | 13% | 113.0 | 120.0 | 259 |
| FTMO guarded · Current 14 + ORB (17 EAs) | 0.75% | 74% | 37% | 0% | 32% | 84.0 | 91.0 | 136 |
| FTMO guarded · Current 14 + ORB (17 EAs) | 1.00% | 62% | 38% | 0% | 52% | 74.0 | 81.0 | 82 |
| Current 14 + ORB 0.5R (17 EAs, no guard) | 0.50% | 66% | 35% | 4% | 0% | 77.0 | 84.0 | 303 |
| Current 14 + ORB 0.5R (17 EAs, no guard) | 0.75% | 71% | 50% | 17% | 0% | 59 | 66 | 162 |
| Current 14 + ORB 0.5R (17 EAs, no guard) | 1.00% | 60% | 52% | 40% | 0% | 46 | 53 | 105 |
| ORB-only (5 ORBs, no guard) | 0.50% | 0% | 0% | 0% | 0% | - | - | 59 |
| ORB-only (5 ORBs, no guard) | 0.75% | 0% | 0% | 0% | 0% | - | - | 59 |
| ORB-only (5 ORBs, no guard) | 1.00% | 2% | 0% | 0% | 0% | 163 | 170 | 59 |
| Prop ready (9 EAs, Nasdaq DI ON) | 0.50% | 57% | 9% | 0% | 9% | 108 | 115 | 181.5 |
| Prop ready (9 EAs, Nasdaq DI ON) | 0.75% | 71% | 37% | 0% | 30% | 81 | 88 | 97 |
| Prop ready (9 EAs, Nasdaq DI ON) | 1.00% | 67% | 46% | 0% | 38% | 64.0 | 71.0 | 66 |
| Best Prop (9 EAs, Nasdaq DI OFF) | 0.50% | 57% | 11% | 0% | 17% | 110.0 | 117.0 | 188.5 |
| Best Prop (9 EAs, Nasdaq DI OFF) | 0.75% | 66% | 36% | 0% | 36% | 78.0 | 85.0 | 105 |
| Best Prop (9 EAs, Nasdaq DI OFF) | 1.00% | 59% | 44% | 0% | 50% | 61.0 | 68.0 | 65 |

## Funded $100k · Monte Carlo 36 months

| Portfolio | Risk / trade | Avg monthly income while trading | Median days until the account ends | Breach / frozen | Still trading at horizon | Total income until end (median / mean) | First reward (share / median $) | Trades / month | / weekday |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| FTMO guarded · Current 14 + ORB (17 EAs) | 0.50% | $2,634 | 1060.6 | 0% / 50% | 50% | $76,797 / $68,938 | 97% / $2,417 | 60.94 | 2.803 |
| FTMO guarded · Current 14 + ORB (17 EAs) | 0.75% | $3,613 | 357.6 | 0% / 89% | 11% | $41,103 / $53,221 | 94% / $2,816 | 47.73 | 2.195 |
| FTMO guarded · Current 14 + ORB (17 EAs) | 1.00% | $3,725 | 169.7 | 0% / 100% | 0% | $18,549 / $27,949 | 88% / $2,377 | 33.49 | 1.54 |
| Current 14 + ORB 0.5R (17 EAs, no guard) | 0.50% | $3,618 | > 1092 | 45% / 0% | 55% | $110,148 / $99,084 | 98% / $3,603 | 84.99 | 3.909 |
| Current 14 + ORB 0.5R (17 EAs, no guard) | 0.75% | $5,736 | 357.7 | 89% / 0% | 11% | $64,641 / $85,063 | 94% / $5,538 | 85.05 | 3.912 |
| Current 14 + ORB 0.5R (17 EAs, no guard) | 1.00% | $7,319 | 85.8 | 100% / 0% | 0% | $16,926 / $28,518 | 79% / $7,384 | 85.06 | 3.912 |
| ORB-only (5 ORBs, no guard) | 0.50% | $310 | > 1092 | 0% / 0% | 100% | $11,081 / $11,108 | 100% / $203 | 9.56 | 0.44 |
| ORB-only (5 ORBs, no guard) | 0.75% | $469 | > 1092 | 5% / 0% | 95% | $16,495 / $16,501 | 100% / $302 | 9.56 | 0.44 |
| ORB-only (5 ORBs, no guard) | 1.00% | $642 | > 1092 | 18% / 0% | 82% | $21,508 / $21,244 | 99% / $401 | 9.59 | 0.441 |
| Prop ready (9 EAs, Nasdaq DI ON) | 0.50% | $2,257 | 847.2 | 0% / 59% | 41% | $58,227 / $54,117 | 98% / $1,184 | 38.97 | 1.792 |
| Prop ready (9 EAs, Nasdaq DI ON) | 0.75% | $3,701 | 231.7 | 0% / 97% | 3% | $25,309 / $37,904 | 94% / $1,879 | 38.25 | 1.759 |
| Prop ready (9 EAs, Nasdaq DI ON) | 1.00% | $4,841 | 105.2 | 0% / 100% | 0% | $14,652 / $23,621 | 86% / $2,283 | 34.88 | 1.604 |
| Best Prop (9 EAs, Nasdaq DI OFF) | 0.50% | $2,192 | 529.4 | 0% / 77% | 23% | $36,840 / $42,196 | 97% / $1,151 | 43.4 | 1.996 |
| Best Prop (9 EAs, Nasdaq DI OFF) | 0.75% | $3,625 | 147.7 | 0% / 99% | 1% | $15,784 / $25,768 | 91% / $1,787 | 42.4 | 1.95 |
| Best Prop (9 EAs, Nasdaq DI OFF) | 1.00% | $5,109 | 78.6 | 0% / 100% | 0% | $11,031 / $18,718 | 84% / $2,381 | 38.42 | 1.767 |

## Funded $100k · History 12-month horizon, every weekday start

| Portfolio | Risk / trade | Avg monthly income while trading | Median days until the account ends | Breach / frozen | Still trading at horizon | Total income until end (median / mean) | First reward (share / median $) | Trades / month | / weekday |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| FTMO guarded · Current 14 + ORB (17 EAs) | 0.50% | $2,928 | > 365 | 0% / 21% | 79% | $32,915 / $31,461 | 95% / $2,715 | 59.62 | 2.742 |
| FTMO guarded · Current 14 + ORB (17 EAs) | 0.75% | $3,806 | > 365 | 0% / 45% | 55% | $33,613 / $34,853 | 92% / $3,433 | 46.62 | 2.144 |
| FTMO guarded · Current 14 + ORB (17 EAs) | 1.00% | $3,067 | 168.6 | 0% / 86% | 14% | $15,411 / $18,326 | 86% / $2,394 | 32.89 | 1.513 |
| Current 14 + ORB 0.5R (17 EAs, no guard) | 0.50% | $3,481 | > 365 | 28% / 0% | 72% | $25,679 / $35,761 | 97% / $3,460 | 83.22 | 3.828 |
| Current 14 + ORB 0.5R (17 EAs, no guard) | 0.75% | $5,591 | 167.7 | 84% / 0% | 16% | $23,247 / $33,999 | 87% / $5,929 | 83.99 | 3.863 |
| Current 14 + ORB 0.5R (17 EAs, no guard) | 1.00% | $7,147 | 73 | 100% / 0% | 0% | $9,589 / $19,929 | 72% / $8,508 | 82.72 | 3.805 |
| ORB-only (5 ORBs, no guard) | 0.50% | $353 | > 365 | 0% / 0% | 100% | $3,627 / $4,227 | 95% / $195 | 10.17 | 0.468 |
| ORB-only (5 ORBs, no guard) | 0.75% | $527 | > 365 | 0% / 0% | 100% | $5,418 / $6,324 | 95% / $288 | 10.17 | 0.468 |
| ORB-only (5 ORBs, no guard) | 1.00% | $701 | > 365 | 0% / 0% | 100% | $7,192 / $8,406 | 95% / $391 | 10.17 | 0.468 |
| Prop ready (9 EAs, Nasdaq DI ON) | 0.50% | $2,474 | > 365 | 0% / 40% | 60% | $22,387 / $23,986 | 97% / $1,067 | 39.28 | 1.807 |
| Prop ready (9 EAs, Nasdaq DI ON) | 0.75% | $4,110 | 169.7 | 0% / 64% | 36% | $18,246 / $28,119 | 90% / $1,819 | 38.36 | 1.764 |
| Prop ready (9 EAs, Nasdaq DI ON) | 1.00% | $5,201 | 112.4 | 0% / 73% | 27% | $17,659 / $28,641 | 83% / $2,426 | 34.86 | 1.603 |
| Best Prop (9 EAs, Nasdaq DI OFF) | 0.50% | $2,237 | > 365 | 0% / 38% | 62% | $19,717 / $21,415 | 94% / $1,128 | 42.92 | 1.974 |
| Best Prop (9 EAs, Nasdaq DI OFF) | 0.75% | $4,134 | 141.7 | 0% / 72% | 28% | $14,786 / $24,346 | 88% / $1,818 | 41.7 | 1.918 |
| Best Prop (9 EAs, Nasdaq DI OFF) | 1.00% | $4,893 | 90.7 | 0% / 93% | 7% | $13,310 / $19,542 | 82% / $2,373 | 37.78 | 1.738 |

