# UK100 Monday dip: our rules vs QuantLab rules on our broker data (2026-11-11)

Native Model 4, Exness UK100 H1, 2019-08-01 -> 2026-09-28 (QuantLab data end), 0.75% risk, R = net / 0.75% of balance. Research copy of the FTSE raw EA with three switches (defaults = raw).

| Version | Trades | Days | Win % | Total R | R/trade | PF | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Ours (raw): one trade per London Monday | 183 | 183 | 50.3 | 22.0 | 0.12 | 1.27 | -3.2 | 7.7 | -1.7 | -0.6 | -8.4 | 1.9 | 7.8 | 18.6 |
| + re-entry after a close | 261 | 184 | 49.4 | 23.7 | 0.091 | 1.19 | -8.6 | 4.5 | 2.5 | -0.3 | -0.8 | -1.2 | 9.7 | 18.1 |
| + Monday on UTC+2/+3 server clock | 183 | 183 | 50.3 | 18.9 | 0.103 | 1.23 | -3.2 | 8.3 | -2.6 | -0.5 | -8.1 | 2.1 | 4.3 | 18.7 |
| + 0.3 sd below the 20h mean | 183 | 183 | 50.3 | 22.0 | 0.12 | 1.27 | -3.2 | 7.7 | -1.7 | -0.6 | -8.4 | 1.9 | 7.8 | 18.6 |
| QuantLab rules (all three) | 262 | 184 | 50.0 | 25.2 | 0.096 | 1.21 | -8.6 | 7.3 | 1.6 | 0.8 | -0.6 | -1.0 | 7.5 | 18.1 |

QuantLab (their broker, 2018-01 -> 2026-09-28, Python on H1 bars, hour-based spread + 0.5 pt): 285 trades, 53.3% win, +0.175R/trade, PF 1.4, positive every calendar year.

Findings: (1) trade count matches once re-entries are allowed (262 here vs 285 incl. 2018); (2) the 0.3-sd condition changes nothing (same ledger as raw);
(3) on the UTC+2/+3 clock about 45 Sunday 23:00 UTC entries are rejected by our broker (UK100 closed) - their broker trades that hour; (4) per-trade edge on our data
is +0.10-0.12R, not +0.175R, and 2019/2023/2024 are negative or flat. Remaining gap: different broker prices and trading hours, cost model, and QuantLab chose the
settings on its own 2018-2026 data (they state no untouched period). Our raw one-per-Monday version is the better of the two on our data (+0.12R, PF 1.27).
