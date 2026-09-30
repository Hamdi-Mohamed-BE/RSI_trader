# FTMO $10K Swing: phase-by-phase simulation

Offline extension, 26 September 2026. No new EA optimization and no account or live settings changed.

## Interpretation

**Fitted-history simulation, not a calibrated forecast.** 1,000 matched paths per portfolio/cost case. Source pool: 26 joint weeks, 2 March–30 August 2026. These news presets were selected using this same history, containing only 20 gold and 17 silver news trades. No genuine out-of-sample claim is made.

Account: $10,000 FTMO 2-Step Swing. Phase 1 +$1,000; Phase 2 +$500; four trading days per phase; $500 daily and $1,000 static total loss limits; Prague midnight reset. No evaluation time limit. Reporting stops at 180 days or first reward request, whichever occurs first, with subsequent first-payment receipt scheduled.

Ordinary risk $71.43/entry, news $10/side, with lot rounding and both news sides reserved. Shared internal gates: $300 daily admission budget, $225 aggregate initial risk, $150 correlated-metal/per-symbol risk, $9,200 internal buffer, seven entries/day maximum, no new entries after three closed losses. Full assumptions and costs remain in PROTOCOL.md.

Two business days assumed between Phase 1 and Phase 2, five between Phase 2 completion and funded activation, four for first-reward review/payment after eligibility. These are modeling assumptions, not guaranteed FTMO turnaround. Eligibility starts 14 calendar days after the first funded trade while flat.

## Phase probabilities by deadline

### Raw Gold / $71.43 — reference costs

| Calendar days | Phase 1 passed | Both phases passed | Funded/activated | First reward received | Evaluation breached | Still evaluating |
|---|---:|---:|---:|---:|---:|---:|
| 30 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 100.0% |
| 60 | 0.6% | 0.0% | 0.0% | 0.0% | 0.0% | 100.0% |
| 90 | 8.4% | 0.1% | 0.0% | 0.0% | 0.0% | 99.9% |
| 120 | 29.3% | 1.0% | 0.7% | 0.1% | 0.0% | 99.0% |
| 180 | 73.4% | 21.4% | 17.1% | 7.6% | 0.0% | 78.6% |

Timing is conditional on finishing the relevant milestone by day 180; unfinished accounts are censored, not assigned zero or labeled failed. Phase 2 time begins when its account becomes available, excluding the prior review wait. Separate medians do not add up to the median total.

| Milestone | Successful paths | Mean calendar days | Median | 10th–90th percentile |
|---|---:|---:|---:|---:|
| Phase 1, from purchase | 734 | 127.9 | 128.6 | 87.6–168.6 |
| Phase 2, from its availability | 214 | 52.4 | 50.2 | 32.0–78.6 |
| Funded, from purchase, including reviews | 171 | 157.4 | 161.6 | 130.7–178.6 |
| First payment, from purchase | 76 | 164.0 | 164.8 | 151.1–177.9 |

Phase 2 completion among paths that had become eligible to start it by day 180: 29.9%. This is deadline-censored, not eventual conditional success.

Internal $9,200 buffer gate encountered by 0 of 1,000 paths. This records a rejected admission, not necessarily permanent termination.

### Raw Gold / $71.43 — stressed costs

| Calendar days | Phase 1 passed | Both phases passed | Funded/activated | First reward received | Evaluation breached | Still evaluating |
|---|---:|---:|---:|---:|---:|---:|
| 30 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 100.0% |
| 60 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 100.0% |
| 90 | 2.0% | 0.0% | 0.0% | 0.0% | 0.0% | 100.0% |
| 120 | 9.0% | 0.0% | 0.0% | 0.0% | 0.0% | 100.0% |
| 180 | 38.8% | 4.1% | 3.4% | 1.2% | 0.0% | 95.9% |

Timing is conditional on finishing the relevant milestone by day 180; unfinished accounts are censored, not assigned zero or labeled failed. Phase 2 time begins when its account becomes available, excluding the prior review wait. Separate medians do not add up to the median total.

| Milestone | Successful paths | Mean calendar days | Median | 10th–90th percentile |
|---|---:|---:|---:|---:|
| Phase 1, from purchase | 388 | 140.6 | 143.6 | 102.6–172.6 |
| Phase 2, from its availability | 41 | 57.4 | 55.0 | 35.9–85.0 |
| Funded, from purchase, including reviews | 34 | 163.1 | 164.1 | 144.1–177.6 |
| First payment, from purchase | 12 | 169.0 | 170.0 | 157.2–177.9 |

Phase 2 completion among paths that had become eligible to start it by day 180: 11.2%. This is deadline-censored, not eventual conditional success.

Internal $9,200 buffer gate encountered by 0 of 1,000 paths. This records a rejected admission, not necessarily permanent termination.

### Raw Gold + news / $71.43 + $10 — reference costs

| Calendar days | Phase 1 passed | Both phases passed | Funded/activated | First reward received | Evaluation breached | Still evaluating |
|---|---:|---:|---:|---:|---:|---:|
| 30 | 26.8% | 4.1% | 1.7% | 0.0% | 0.0% | 95.9% |
| 60 | 70.4% | 29.5% | 22.6% | 6.2% | 0.0% | 70.5% |
| 90 | 91.5% | 62.5% | 54.6% | 30.2% | 0.0% | 37.5% |
| 120 | 97.8% | 84.2% | 80.8% | 61.4% | 0.0% | 15.8% |
| 180 | 99.8% | 98.6% | 98.3% | 95.9% | 0.0% | 1.4% |

Timing is conditional on finishing the relevant milestone by day 180; unfinished accounts are censored, not assigned zero or labeled failed. Phase 2 time begins when its account becomes available, excluding the prior review wait. Separate medians do not add up to the median total.

| Milestone | Successful paths | Mean calendar days | Median | 10th–90th percentile |
|---|---:|---:|---:|---:|
| Phase 1, from purchase | 998 | 49.3 | 45.6 | 15.5–87.6 |
| Phase 2, from its availability | 986 | 30.1 | 26.0 | 8.0–59.0 |
| Funded, from purchase, including reviews | 983 | 88.3 | 86.8 | 46.6–135.6 |
| First payment, from purchase | 959 | 108.4 | 107.7 | 67.7–151.2 |

Phase 2 completion among paths that had become eligible to start it by day 180: 98.8%. This is deadline-censored, not eventual conditional success.

Internal $9,200 buffer gate encountered by 0 of 1,000 paths. This records a rejected admission, not necessarily permanent termination.

### Raw Gold + news / $71.43 + $10 — stressed costs

| Calendar days | Phase 1 passed | Both phases passed | Funded/activated | First reward received | Evaluation breached | Still evaluating |
|---|---:|---:|---:|---:|---:|---:|
| 30 | 15.4% | 1.8% | 0.4% | 0.0% | 0.0% | 98.2% |
| 60 | 50.7% | 14.7% | 11.3% | 2.0% | 0.0% | 85.3% |
| 90 | 75.5% | 37.5% | 32.9% | 13.6% | 0.0% | 62.5% |
| 120 | 88.8% | 61.3% | 55.1% | 35.7% | 0.0% | 38.7% |
| 180 | 98.2% | 91.2% | 88.2% | 78.5% | 0.0% | 8.8% |

Timing is conditional on finishing the relevant milestone by day 180; unfinished accounts are censored, not assigned zero or labeled failed. Phase 2 time begins when its account becomes available, excluding the prior review wait. Separate medians do not add up to the median total.

| Milestone | Successful paths | Mean calendar days | Median | 10th–90th percentile |
|---|---:|---:|---:|---:|
| Phase 1, from purchase | 982 | 65.4 | 59.6 | 23.5–116.5 |
| Phase 2, from its availability | 912 | 36.8 | 31.0 | 10.0–72.3 |
| Funded, from purchase, including reviews | 882 | 105.8 | 106.1 | 58.8–156.8 |
| First payment, from purchase | 785 | 122.3 | 122.0 | 79.6–164.6 |

Phase 2 completion among paths that had become eligible to start it by day 180: 93.1%. This is deadline-censored, not eventual conditional success.

Internal $9,200 buffer gate encountered by 0 of 1,000 paths. This records a rejected admission, not necessarily permanent termination.

### High-win + news / $71.43 + $10 — reference costs

| Calendar days | Phase 1 passed | Both phases passed | Funded/activated | First reward received | Evaluation breached | Still evaluating |
|---|---:|---:|---:|---:|---:|---:|
| 30 | 30.9% | 5.4% | 2.7% | 0.0% | 0.0% | 94.6% |
| 60 | 76.4% | 34.7% | 26.7% | 7.8% | 0.0% | 65.3% |
| 90 | 94.0% | 69.9% | 62.0% | 35.7% | 0.0% | 30.1% |
| 120 | 98.8% | 90.5% | 86.4% | 70.9% | 0.0% | 9.5% |
| 180 | 99.9% | 99.3% | 99.0% | 97.1% | 0.0% | 0.7% |

Timing is conditional on finishing the relevant milestone by day 180; unfinished accounts are censored, not assigned zero or labeled failed. Phase 2 time begins when its account becomes available, excluding the prior review wait. Separate medians do not add up to the median total.

| Milestone | Successful paths | Mean calendar days | Median | 10th–90th percentile |
|---|---:|---:|---:|---:|
| Phase 1, from purchase | 999 | 44.8 | 39.6 | 15.6–79.8 |
| Phase 2, from its availability | 993 | 28.3 | 24.5 | 7.0–54.1 |
| Funded, from purchase, including reviews | 990 | 82.3 | 79.8 | 43.6–122.6 |
| First payment, from purchase | 971 | 102.0 | 100.6 | 64.9–142.0 |

Phase 2 completion among paths that had become eligible to start it by day 180: 99.4%. This is deadline-censored, not eventual conditional success.

Internal $9,200 buffer gate encountered by 0 of 1,000 paths. This records a rejected admission, not necessarily permanent termination.

### High-win + news / $71.43 + $10 — stressed costs

| Calendar days | Phase 1 passed | Both phases passed | Funded/activated | First reward received | Evaluation breached | Still evaluating |
|---|---:|---:|---:|---:|---:|---:|
| 30 | 20.5% | 3.0% | 1.7% | 0.0% | 0.0% | 97.0% |
| 60 | 54.9% | 20.1% | 15.3% | 3.5% | 0.0% | 79.9% |
| 90 | 77.4% | 42.0% | 36.8% | 19.2% | 0.0% | 58.0% |
| 120 | 89.3% | 64.4% | 59.2% | 39.6% | 0.0% | 35.6% |
| 180 | 98.1% | 90.9% | 88.8% | 80.4% | 0.0% | 9.1% |

Timing is conditional on finishing the relevant milestone by day 180; unfinished accounts are censored, not assigned zero or labeled failed. Phase 2 time begins when its account becomes available, excluding the prior review wait. Separate medians do not add up to the median total.

| Milestone | Successful paths | Mean calendar days | Median | 10th–90th percentile |
|---|---:|---:|---:|---:|
| Phase 1, from purchase | 981 | 61.6 | 56.5 | 17.6–115.6 |
| Phase 2, from its availability | 909 | 35.5 | 29.0 | 8.0–73.9 |
| Funded, from purchase, including reviews | 888 | 100.8 | 100.8 | 51.8–151.6 |
| First payment, from purchase | 804 | 118.6 | 120.9 | 72.7–163.9 |

Phase 2 completion among paths that had become eligible to start it by day 180: 92.8%. This is deadline-censored, not eventual conditional success.

Internal $9,200 buffer gate encountered by 8 of 1,000 paths. This records a rejected admission, not necessarily permanent termination.

## Breach-risk limitation

The simulated breach rate concerns the evaluation and, separately, funded trading only until the first reward request (or day 180). It is not the probability of losing a funded account over its full lifetime or after withdrawals. The zero breach outcome, if observed, is conditional on admission gates and stop-reserve equity assumptions. Stops do not cap gaps, and we did not replay FTMO bid/ask equity tick by tick. Real-world breach probability is not established by this study.

Do not equate 1 minus pass probability with blow-up probability: unfinished accounts and accounts waiting for administrative activation are distinct states. The state-count dictionaries in PHASE_RESULTS.json reconcile to 1,000 at every deadline.

## News eligibility

Swing permits news trading generally, but the exact pre-news two-sided stop strategy remains subject to FTMO forbidden gap-trading practices and contract review. No disqualification probability is modeled; written clarification is needed before deployment.

## Evidence and validation

All source hashes were verified. The prior nine engine tests, seven source-adapter assertions and eight historical parity fields pass again. Eleven new deadline/timing tests pass. All phase funnels reconcile, and the funded/first-payout percentages reproduce the previous results for every matching horizon.

- [FTMO objectives](https://ftmo.com/en/trading-objectives/)
- [FTMO comparison](https://ftmo.com/en/comparison-table/)
- [Reward rules](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/)
- [Swing account](https://ftmo.com/en/faq/ftmo-swing-account-type/)
- [Forbidden practices](https://ftmo.com/en/forbidden-trading-practices/)
