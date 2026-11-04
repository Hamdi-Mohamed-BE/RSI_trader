# XAU Weakness: enter at market when the breakout level is already passed (2026-11-03)

Owner request: "fix it to enter at market and backtest 5 years and october".

**The problem.** In October 2026 the bot made 0 trades. Both of its signals failed with "Invalid price": the bot places a stop order
just beyond the breakout level, but price was already past that level.

**The change.** Research copy `EA/XAU Weakness Market Fill Research.mq5` adds one input, `InpWeaknessMarketIfPast` (default false).
When it is true and price is already at or through the level (within the broker stop level), the bot enters at market. It keeps the
same structure stop and the same 4R target, and sizes the lots from the fill price. Production files are unchanged; their hashes are in
`PRODUCTION_SHA256.txt`.

**Runs.** Native MT5 Model 4, XAUUSD M30, $10k, 150 ms, Full EA preset, risk 1%, adaptive off (`run.py`, `native/`).
- Parity: OFF = PROD on all 248 trades (5y) and on October (0 trades, same rejections).

| Version | Window | Trades | Trades / month (/ weekday) | Return | PF | Win % | MT5 equity DD (maximal) |
|---|---|---:|---:|---:|---:|---:|---:|
| Production | 5y 2021-11-01 → 2026-11-01 | 248 | 4.1 (0.19) | +123.9% | 1.56 | 39.1 | 9.13% |
| **Market fill** | 5y | 248 | 4.1 (0.19) | +101.7% | 1.50 | 41.1 | 11.23% |
| Production | October 2026 | 0 | 0 | 0.0% | – | – | 0% |
| **Market fill** | October 2026 | 2 | 2 | −1.02% | 0.10 | 50 | 2.83% |

**Why there are not more trades.** The bot holds one position at a time.
- The 124 market entries made money: net +$5,970, PF 1.61; 116 of them were longs.
- But they took the slot from 127 production trades that were better: net +$7,567, PF 1.66.
- Net effect over 5 years: −$2,222.

**By period (net $, trades).**

| Period | Production | Market fill |
|---|---|---|
| Dev 2021-11 → 2023-10 | −407 (63), PF 0.92 | −1,231 (59), PF 0.72 |
| Validation 2023-11 → 2024-10 | +1,786 (67), PF 1.39 | +2,582 (73), PF 1.54 |
| OOS 2024-11 → 2026-10 | +11,015 (118), PF 1.88 | +8,821 (116), PF 1.81 |

**By year (net $, trades).**

| Year | Production | Market fill |
|---|---|---|
| 2021 | −165 (3) | −171 (3) |
| 2022 | +1,004 (31) | −286 (33) |
| 2023 | −175 (38) | +440 (34) |
| 2024 | +597 (59) | +1,249 (63) |
| 2025 | +6,933 (70) | +3,992 (75) |
| 2026 | +4,201 (47) | +4,947 (40) |

**Verdict: keep production; do not deploy market fill.** It is worse over 5 years, worse in development and in OOS, and better only in
validation. The missed signals are not lost edge: waiting for the next clean breakout earns more than chasing an already-passed level.

**Caveats.**
- Older ticks are generated; real ticks start 2026-01-01, which is 16% of the 5-year run.
- This preset's 5y trade count (248) differs from the 2026-10-08 long-history run (666), which used the RR 0.5 comparison inputs.
- Nothing installed or deployed.

## Addendum 1: out-of-sample windows and Monte Carlo (owner: "run monte carlo and out of sample data")
`run_split.py` → `SPLIT.json`; `mc.py` → `MC.json`.

**Windows.** From the shared `data_split.py`, history 2019-01-01 to 2026-11-01. Each window is a separate native run from a fresh $10k.
The OOS window was already seen in the 5y comparison above, so it is previously viewed, not untouched.

| Window | Version | Trades (/ month, / weekday) | Return | PF | Win % | MT5 equity DD (maximal) | Real ticks |
|---|---|---:|---:|---:|---:|---:|---:|
| Dev 2019-01 → 2023-11 | Production | 170 (2.9, 0.13) | −28.5% | 0.75 | 27.6 | 29.5% | 0% |
| Dev | Market fill | 182 (3.1, 0.14) | −42.3% | 0.62 | 26.9 | 44.6% | 0% |
| Val 2023-11 → 2024-11 | Production | 67 (5.6, 0.26) | +18.9% | 1.40 | 43.3 | 17.6% | 0% |
| Val | Market fill | 73 (6.1, 0.28) | +29.7% | 1.54 | 42.5 | 11.6% | 0% |
| OOS 2024-11 → 2026-11 | Production | 118 (4.9, 0.23) | +97.4% | 1.87 | 43.2 | 9.3% | 41% |
| OOS | Market fill | 117 (4.9, 0.22) | +68.4% | 1.70 | 45.3 | 11.4% | 41% |
| All 2019-01 → 2026-11 | Production | 355 (3.8, 0.17) | +70.6% | 1.29 | 35.8 | 30.3% | 10% |
| All | Market fill | 371 (3.9, 0.18) | +35.4% | 1.16 | 35.9 | 44.6% | 10% |

**Production by year** (net $, trades):

| 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| −954 (35) | −1,424 (56) | −268 (19) | +749 (31) | −160 (38) | +450 (59) | +5,361 (70) | +3,302 (47) |

**Monte Carlo.** Day-block bootstrap (5-weekday blocks, empty days kept), 10,000 paths, seed 20261103. Each trade is converted to
R = net / 1% of the closed balance before it. The sum of R is the % return at 1% risk, without compounding.

| Source | Version | Mean R / trade | 3 m p05 / median / p95 | 3 m P(loss) | 12 m p05 / median / p95 | 12 m P(loss) | 12 m DD median / p95 / p99 | Losing streak median / p95 |
|---|---|---:|---|---:|---|---:|---|---|
| 2019-26 | Production | 0.170 | −7.7 / +1.1 / +14.2% | 43% | −12.9 / +7.1 / +31.4% | 29% | 9.8 / 19.8 / 25.4% | 6 / 11 |
| 2019-26 | Market fill | 0.101 | −8.6 / +0.8 / +12.9% | 45% | −15.7 / +4.4 / +27.1% | 37% | 11.0 / 22.3 / 28.5% | 7 / 12 |
| 2024-26 only | Production | 0.603 | −2.8 / +8.1 / +22.9% | 13% | +10.3 / +34.5 / +62.5% | 1% | 6.7 / 11.9 / 15.4% | 5 / 8 |
| 2024-26 only | Market fill | 0.471 | −5.4 / +6.2 / +20.9% | 21% | +1.7 / +26.8 / +54.7% | 4% | 8.2 / 16.1 / 21.4% | 5 / 8 |

**Verdict.** Market fill is worse in dev, in OOS and in all-history MC, and better only in validation, so it stays REJECTED.

The production bot itself also FAILS the development window: −28.5%, PF 0.75, losing 2019, 2020 and 2021. Its 2019-26 MC gives
P(losing year) 29%. Nearly all of its profit comes from the 2024-26 gold bull market (2024-26 made +$9,113, more than the +$7,056 total; 2019-23 lost $2,057). The 2024-26-only MC
(P(losing year) 1%) describes that regime, not the whole history.

Caveats:
- Dev and val use generated ticks; real ticks start 2026-01-01.
- The preset's selection history is not documented here, so the OOS window cannot be called untouched.
