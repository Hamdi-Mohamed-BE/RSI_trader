# Tables (generated from RESULTS.json)

Parity: {"continuous|DI_OFF|recorded_exness": {"trades": 908, "net": 17079.75, "ending_balance": 27079.42, "match": true}, "continuous|DI_OFF|fixed_cost_stress": {"trades": 19, "net": -766.19, "ending_balance": 9233.81, "match": true}, "oos_challenge|DI_OFF": {"n": 394, "pass_both_180": 0.8985, "match": true}, "continuous|DI_ON|recorded_exness": {"trades": 832, "net": 18365.98, "ending_balance": 28365.65, "match": true}, "continuous|DI_ON|fixed_cost_stress": {"trades": 831, "net": 16091.64, "ending_balance": 26090.78, "match": true}, "oos_challenge|DI_ON": {"n": 394, "pass_both_180": 0.9645, "match": true}}

## Funded only · DI_OFF · recorded_exness · request at first flat moment ≥ day 14 with ≥ $20 profit

| Window | Starts | Paid ≤30 d | ≤60 d | ≤90 d | ≤180 d | Median day (p25–p75) | Median payout (p25–p75) | Expected payout / account | Breach before payout | No payout, stuck at $9,200 | Trades / 180 d | / month | / day |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Dev 2021-23 | 392 | 79% | 81% | 82% | 86% | 15 (15–18) | $188 ($87–$408) | $234 | 0% | 14% | 235 | 39.74 | 1.828 |
| Val 2023-24 | 133 | 82% | 86% | 86% | 86% | 15 (15–19) | $228 ($76–$537) | $293 | 0% | 14% | 208 | 35.17 | 1.618 |
| OOS 2024-26 | 394 | 93% | 97% | 97% | 97% | 15 (15–16) | $276 ($116–$525) | $372 | 0% | 3% | 223 | 37.71 | 1.734 |
| All 5y | 1176 | 80% | 84% | 84% | 86% | 15 (15–17) | $232 ($88–$464) | $285 | 0% | 14% | 219 | 37.03 | 1.703 |
| Monte Carlo | 2000 | 78% | 82% | 83% | 83% | 15 (15–17) | $242 ($91–$461) | $277 | 0% | 16% | 223 | 37.71 | 1.734 |

## Funded only · DI_OFF · fixed_cost_stress · request at first flat moment ≥ day 14 with ≥ $20 profit

| Window | Starts | Paid ≤30 d | ≤60 d | ≤90 d | ≤180 d | Median day (p25–p75) | Median payout (p25–p75) | Expected payout / account | Breach before payout | No payout, stuck at $9,200 | Trades / 180 d | / month | / day |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Dev 2021-23 | 392 | 74% | 76% | 79% | 83% | 15 (15–19) | $154 ($62–$371) | $200 | 0% | 17% | 152 | 25.7 | 1.182 |
| Val 2023-24 | 133 | 78% | 80% | 80% | 80% | 15 (15–19) | $220 ($88–$496) | $257 | 0% | 20% | 202 | 34.16 | 1.571 |
| OOS 2024-26 | 394 | 90% | 94% | 94% | 95% | 15 (15–17) | $242 ($122–$484) | $347 | 0% | 5% | 222 | 37.54 | 1.727 |
| All 5y | 1176 | 76% | 79% | 80% | 83% | 15 (15–18) | $206 ($82–$430) | $256 | 0% | 17% | 214 | 36.19 | 1.664 |
| Monte Carlo | 2000 | 74% | 78% | 78% | 79% | 15 (15–17) | $218 ($94–$421) | $246 | 0% | 20% | 216 | 36.52 | 1.68 |

## Payout policy comparison · DI_OFF · recorded_exness

| Request when closed profit ≥ | Evidence | Paid ≤180 d | Median day | Median payout | Expected payout / account | Breach before payout | Trades / month | / day |
|---|---|---|---|---|---|---|---|---|
| $20 | All 5y | 86% | 15 | $232 | $285 | 0% | 37.03 | 1.703 |
| $20 | OOS 2024-26 | 97% | 15 | $276 | $372 | 0% | 37.71 | 1.734 |
| $20 | Monte Carlo | 83% | 15 | $242 | $277 | 0% | 37.71 | 1.734 |
| $250 | All 5y | 83% | 16 | $327 | $356 | 0% | 37.03 | 1.703 |
| $250 | OOS 2024-26 | 96% | 15 | $342 | $446 | 0% | 37.71 | 1.734 |
| $250 | Monte Carlo | 80% | 16 | $329 | $340 | 0% | 37.71 | 1.734 |
| $500 | All 5y | 80% | 21 | $508 | $469 | 0% | 37.03 | 1.703 |
| $500 | OOS 2024-26 | 96% | 19.5 | $524 | $593 | 0% | 37.71 | 1.734 |
| $500 | Monte Carlo | 77% | 22 | $518 | $458 | 0% | 37.71 | 1.734 |
| $1,000 | All 5y | 76% | 38 | $890 | $724 | 0% | 37.03 | 1.703 |
| $1,000 | OOS 2024-26 | 96% | 35.5 | $891 | $922 | 0% | 37.71 | 1.734 |
| $1,000 | Monte Carlo | 72% | 39 | $876 | $683 | 0% | 37.71 | 1.734 |

## End to end (challenge start → first request, $20 policy) · DI_OFF

| Scenario | Challenge starts | Funded | Paid ≤120 d | ≤180 d | ≤270 d | ≤365 d | Median days start → request (p25–p75) | Median payout | Expected payout / challenge bought | Median trades (chain) |
|---|---|---|---|---|---|---|---|---|---|---|
| base · Dev 2021-23 starts | 521 | 42% | 25% | 36% | 37% | 37% | 93 (72–127) | $145 | $127 | 100 |
| base · Val 2023-24 starts | 261 | 54% | 36% | 37% | 38% | 38% | 79 (66–92) | $446 | $171 | 98 |
| base · OOS 2024-26 starts | 255 | 86% | 78% | 86% | 86% | 86% | 79 (58–102) | $367 | $367 | 285 |
| base · All 5y starts | 1037 | 56% | 41% | 48% | 49% | 49% | 84 (66–107) | $367 | $197 | 162 |
| base · Monte Carlo | 2000 | 56% | 38% | 48% | 49% | 49% | 88 (68–116) | $245 | $164 | 163 |
| stress · Dev 2021-23 starts | 521 | 28% | 13% | 18% | 22% | 22% | 113 (87–171) | $97 | $55 | 81 |
| stress · Val 2023-24 starts | 261 | 38% | 27% | 28% | 28% | 28% | 87 (80–99) | $277 | $104 | 82 |
| stress · OOS 2024-26 starts | 255 | 87% | 68% | 85% | 85% | 85% | 85 (67–110) | $254 | $293 | 291 |
| stress · All 5y starts | 1037 | 45% | 30% | 37% | 39% | 39% | 90 (75–117) | $236 | $126 | 114 |
| stress · Monte Carlo | 2000 | 44% | 26% | 34% | 36% | 36% | 94 (72–123) | $236 | $114 | 104 |

## End to end ($500 policy) · DI_OFF

| Scenario | Challenge starts | Funded | Paid ≤120 d | ≤180 d | ≤270 d | ≤365 d | Median days start → request (p25–p75) | Median payout | Expected payout / challenge bought | Median trades (chain) |
|---|---|---|---|---|---|---|---|---|---|---|
| base · Dev 2021-23 starts | 521 | 42% | 18% | 33% | 35% | 36% | 122 (85–138) | $524 | $215 | 100 |
| base · Val 2023-24 starts | 261 | 54% | 31% | 32% | 32% | 32% | 80.5 (65–98) | $633 | $196 | 98 |
| base · OOS 2024-26 starts | 255 | 86% | 76% | 86% | 86% | 86% | 83 (69–104) | $464 | $484 | 285 |
| base · All 5y starts | 1037 | 56% | 35% | 46% | 47% | 47% | 89 (73–121) | $491 | $276 | 162 |
| base · Monte Carlo | 2000 | 56% | 31% | 43% | 45% | 45% | 101 (75–130) | $510 | $263 | 163 |
| stress · Dev 2021-23 starts | 521 | 28% | 5% | 7% | 9% | 9% | 119 (99–173) | $681 | $63 | 81 |
| stress · Val 2023-24 starts | 261 | 38% | 22% | 22% | 23% | 23% | 99 (85–108) | $657 | $153 | 82 |
| stress · OOS 2024-26 starts | 255 | 87% | 67% | 85% | 85% | 85% | 89 (77–110) | $467 | $435 | 291 |
| stress · All 5y starts | 1037 | 45% | 24% | 30% | 31% | 31% | 94 (80–116) | $508 | $177 | 114 |
| stress · Monte Carlo | 2000 | 44% | 20% | 29% | 31% | 31% | 106 (80–137) | $505 | $180 | 104 |

## Funded only · DI_ON · recorded_exness · request at first flat moment ≥ day 14 with ≥ $20 profit

| Window | Starts | Paid ≤30 d | ≤60 d | ≤90 d | ≤180 d | Median day (p25–p75) | Median payout (p25–p75) | Expected payout / account | Breach before payout | No payout, stuck at $9,200 | Trades / 180 d | / month | / day |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Dev 2021-23 | 392 | 80% | 83% | 84% | 88% | 15 (15–17) | $211 ($102–$401) | $241 | 0% | 11% | 217 | 36.69 | 1.688 |
| Val 2023-24 | 133 | 83% | 83% | 83% | 83% | 15 (15–18) | $222 ($77–$393) | $241 | 0% | 17% | 182 | 30.78 | 1.416 |
| OOS 2024-26 | 394 | 96% | 99% | 99% | 99% | 15 (15–16) | $283 ($128–$518) | $379 | 0% | 1% | 205 | 34.66 | 1.594 |
| All 5y | 1176 | 81% | 84% | 85% | 87% | 15 (15–17) | $237 ($106–$432) | $280 | 0% | 13% | 202 | 34.16 | 1.571 |
| Monte Carlo | 2000 | 81% | 87% | 87% | 88% | 15 (15–16) | $225 ($95–$432) | $273 | 0% | 12% | 205 | 34.66 | 1.594 |

## Funded only · DI_ON · fixed_cost_stress · request at first flat moment ≥ day 14 with ≥ $20 profit

| Window | Starts | Paid ≤30 d | ≤60 d | ≤90 d | ≤180 d | Median day (p25–p75) | Median payout (p25–p75) | Expected payout / account | Breach before payout | No payout, stuck at $9,200 | Trades / 180 d | / month | / day |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Dev 2021-23 | 392 | 76% | 80% | 80% | 80% | 15 (15–17) | $199 ($88–$374) | $210 | 0% | 19% | 215 | 36.36 | 1.672 |
| Val 2023-24 | 133 | 74% | 78% | 78% | 78% | 15 (15–22) | $187 ($73–$351) | $202 | 0% | 22% | 103 | 17.42 | 0.801 |
| OOS 2024-26 | 394 | 95% | 98% | 98% | 98% | 15 (15–17) | $248 ($109–$479) | $353 | 0% | 2% | 204 | 34.5 | 1.587 |
| All 5y | 1176 | 78% | 81% | 81% | 82% | 15 (15–17) | $215 ($99–$401) | $251 | 0% | 18% | 200 | 33.82 | 1.556 |
| Monte Carlo | 2000 | 75% | 81% | 82% | 82% | 15 (15–17) | $209 ($82–$417) | $246 | 0% | 17% | 201 | 33.99 | 1.563 |

## Payout policy comparison · DI_ON · recorded_exness

| Request when closed profit ≥ | Evidence | Paid ≤180 d | Median day | Median payout | Expected payout / account | Breach before payout | Trades / month | / day |
|---|---|---|---|---|---|---|---|---|
| $20 | All 5y | 87% | 15 | $237 | $280 | 0% | 34.16 | 1.571 |
| $20 | OOS 2024-26 | 99% | 15 | $283 | $379 | 0% | 34.66 | 1.594 |
| $20 | Monte Carlo | 88% | 15 | $225 | $273 | 0% | 34.66 | 1.594 |
| $250 | All 5y | 84% | 16 | $336 | $353 | 0% | 34.16 | 1.571 |
| $250 | OOS 2024-26 | 99% | 16 | $343 | $454 | 0% | 34.66 | 1.594 |
| $250 | Monte Carlo | 84% | 16 | $330 | $348 | 0% | 34.66 | 1.594 |
| $500 | All 5y | 80% | 22 | $496 | $459 | 0% | 34.16 | 1.571 |
| $500 | OOS 2024-26 | 99% | 20 | $511 | $591 | 0% | 34.66 | 1.594 |
| $500 | Monte Carlo | 82% | 23 | $490 | $458 | 0% | 34.66 | 1.594 |
| $1,000 | All 5y | 75% | 42 | $870 | $715 | 0% | 34.16 | 1.571 |
| $1,000 | OOS 2024-26 | 99% | 41 | $871 | $960 | 0% | 34.66 | 1.594 |
| $1,000 | Monte Carlo | 77% | 44 | $881 | $730 | 0% | 34.66 | 1.594 |

## End to end (challenge start → first request, $20 policy) · DI_ON

| Scenario | Challenge starts | Funded | Paid ≤120 d | ≤180 d | ≤270 d | ≤365 d | Median days start → request (p25–p75) | Median payout | Expected payout / challenge bought | Median trades (chain) |
|---|---|---|---|---|---|---|---|---|---|---|
| base · Dev 2021-23 starts | 521 | 51% | 28% | 46% | 46% | 46% | 105 (78–141) | $217 | $142 | 133 |
| base · Val 2023-24 starts | 261 | 57% | 34% | 36% | 43% | 43% | 87 (75–106) | $525 | $221 | 110 |
| base · OOS 2024-26 starts | 255 | 95% | 81% | 95% | 95% | 95% | 84 (64–111) | $371 | $350 | 269 |
| base · All 5y starts | 1037 | 63% | 43% | 55% | 57% | 57% | 90 (72–120) | $260 | $213 | 237 |
| base · Monte Carlo | 2000 | 65% | 41% | 55% | 58% | 58% | 96 (75–127) | $248 | $189 | 228.5 |
| stress · Dev 2021-23 starts | 521 | 38% | 20% | 31% | 34% | 34% | 105 (78–148) | $165 | $112 | 84 |
| stress · Val 2023-24 starts | 261 | 43% | 23% | 23% | 24% | 24% | 88 (78–103) | $362 | $118 | 86 |
| stress · OOS 2024-26 starts | 255 | 96% | 70% | 96% | 96% | 96% | 92 (76–125) | $551 | $424 | 278 |
| stress · All 5y starts | 1037 | 53% | 33% | 45% | 47% | 47% | 93 (77–128) | $362 | $190 | 136 |
| stress · Monte Carlo | 2000 | 51% | 30% | 42% | 44% | 44% | 99 (78–129) | $216 | $133 | 147 |

## End to end ($500 policy) · DI_ON

| Scenario | Challenge starts | Funded | Paid ≤120 d | ≤180 d | ≤270 d | ≤365 d | Median days start → request (p25–p75) | Median payout | Expected payout / challenge bought | Median trades (chain) |
|---|---|---|---|---|---|---|---|---|---|---|
| base · Dev 2021-23 starts | 521 | 51% | 24% | 43% | 45% | 45% | 114 (82–151) | $519 | $254 | 133 |
| base · Val 2023-24 starts | 261 | 57% | 33% | 33% | 41% | 41% | 88 (76–112) | $541 | $269 | 110 |
| base · OOS 2024-26 starts | 255 | 95% | 76% | 95% | 95% | 95% | 88 (72–116) | $522 | $512 | 269 |
| base · All 5y starts | 1037 | 63% | 39% | 53% | 56% | 56% | 94 (77–127) | $522 | $321 | 237 |
| base · Monte Carlo | 2000 | 65% | 34% | 50% | 54% | 54% | 108 (82–138) | $492 | $305 | 228.5 |
| stress · Dev 2021-23 starts | 521 | 38% | 18% | 30% | 34% | 34% | 119 (89–158) | $494 | $195 | 84 |
| stress · Val 2023-24 starts | 261 | 43% | 19% | 20% | 21% | 21% | 90 (83–107) | $707 | $139 | 86 |
| stress · OOS 2024-26 starts | 255 | 96% | 69% | 96% | 96% | 96% | 99 (81–125) | $575 | $542 | 278 |
| stress · All 5y starts | 1037 | 53% | 31% | 43% | 46% | 46% | 104 (84–132) | $551 | $266 | 136 |
| stress · Monte Carlo | 2000 | 51% | 22% | 35% | 39% | 39% | 113 (87–144) | $498 | $223 | 147 |

