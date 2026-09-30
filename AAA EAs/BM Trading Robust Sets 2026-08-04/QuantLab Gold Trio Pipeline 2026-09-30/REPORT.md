# QuantLab Gold Trio — full optimisation pipeline results (2026-09-30)

Research only. Rules and gates frozen in `PROTOCOL.md` before any search. Isolated tester, XAUUSD Exness-MT5Trial16,
$10,000, 1% risk per module, 150 ms delay, broker costs. Real ticks begin 2026-01-01; earlier ticks are generated.
Nothing installed, published or pushed. The live MT5 terminal was not touched.

- **Parity:** before searching, the search EA reproduced the raw 3y native runs exactly: A 432, B 266 and C 35 trades, with cash identical to the cent.
- **Trials:** 1,770 native passes in total (1,553 unique settings plus single runs), all counted for the deflated Sharpe.
- **Override:** A and C had failed the raw gate. They were optimised because the user asked for it (exploratory override); their raw rejection stays on record.

**Metric definitions:**
- Trades/month = trades ÷ (days ÷ 30.44). Trades/day = trades ÷ weekdays.
- Consistency = share of months with a positive result.
- Sharpe = daily closed-trade returns, every calendar day counted, × √365.
- Balance DD = drawdown of the closed-trade balance. Equity DD = the native MT5 relative equity DD.
- Trades are counted per position; a partial close is part of its position.
- Streaks are shown as average win / average loss (longest win / longest loss).

## The two versions the user asked for

| Version | Contents |
|---|---|
| **BEST trio** (best PF/√n/DD score per module) | A-best + B-best + C-best |
| **PROP trio** (best mean rank of win rate, Sharpe, longest win streak per module) | A-prop + B-prop + C-prop |

Frozen settings:
- **A (best = prop, same setting):** H4 · limit entry 0.5 ATR · stop 3 ATR · no target · 50% partial at +1R · ATR trail 1 ATR from +0.5R · all hours · long+short · EMA200 bias · no Monday · lookback 24, threshold 0.5 ATR, EMA50.
- **B-best:** M15 · limit 0.5 ATR · stop 4 ATR · target 2.5R · 50% at +1R · ATR trail 1.5 ATR from +1R · London–NY overlap 12–16 UTC · spread ≤ 0.1 ATR · range **960**, breakout 60, edge 10%, volatility window 50.
- **B-prop:** identical to B-best but range **480** (the raw value).
- **C-best:** long at session open on the last trading day (Day −1) · stop 2 D1-ATR · target 2.5R · breakeven at +0.5R · no Monday entries · exit near the end of trading day +2.
- **C-prop:** long at session open on Day −2 · stop 2 D1-ATR · target **0.5R** · breakeven at +0.5R · exit near the end of trading day +2.

## Website periods (ending 2026-09-29) — native Model 4

The 5y and 3y windows contain the development data, so they are in-sample. 1y and 6m were seen by the raw test only.

| Case | Trades | /month | /day | Return | PF | Win | Consist. | Streaks W/L avg (max) | Sharpe | Bal DD | Eq DD |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|
| **BEST trio 6m** | 41 | 6.8 | 0.31 | +3.6% | 1.18 | 58.5% | 43% | 2.7/1.9 (8/6) | 0.73 | 7.5% | 8.8% |
| **BEST trio 1y** | 77 | 6.4 | 0.30 | +14.5% | 1.38 | 58.4% | 46% | 2.7/1.9 (8/6) | 1.27 | 8.0% | 8.5% |
| **BEST trio 3y** | 263 | 7.3 | 0.34 | +52.0% | 1.37 | 61.2% | 51% | 2.6/1.6 (16/6) | 1.38 | 7.6% | 9.4% |
| **BEST trio 5y** | 439 | 7.3 | 0.34 | **+114.4%** | **1.44** | 62.4% | 62% | 2.9/1.7 (16/6) | **1.61** | 6.8% | **7.9%** |
| PROP trio 6m | 50 | 8.3 | 0.38 | −4.9% | 0.84 | 52.0% | 43% | 2.4/2.2 (7/6) | −0.74 | 9.5% | 10.9% |
| PROP trio 1y | 90 | 7.5 | 0.35 | +5.8% | 1.11 | 55.6% | 38% | 2.6/2.1 (7/6) | 0.50 | 10.1% | 11.3% |
| PROP trio 3y | 300 | 8.3 | 0.38 | +30.2% | 1.18 | 59.0% | 51% | 2.6/1.8 (16/6) | 0.84 | 10.2% | 11.5% |
| PROP trio 5y | 503 | 8.4 | 0.39 | +96.1% | 1.30 | 62.8% | 61% | 2.9/1.7 (17/6) | 1.36 | 10.0% | 11.5% |
| C-prop alone (only qualified module) 6m | 6 | 1.0 | 0.05 | +0.5% | 1.19 | 50.0% | 43% | 1.5/1.5 (2/2) | — | 1.8% | 2.2% |
| C-prop alone 1y | 12 | 1.0 | 0.05 | +0.9% | 1.17 | 50.0% | 38% | 1.5/1.5 (2/2) | 0.24 | 2.6% | 3.4% |
| C-prop alone 3y | 35 | 1.0 | 0.05 | +3.1% | 1.27 | 57.1% | 41% | 2.2/1.5 (5/3) | 0.35 | 2.5% | 3.3% |
| C-prop alone 5y | 60 | 1.0 | 0.05 | +8.7% | 1.51 | 65.0% | 44% | 2.8/1.5 (10/3) | 0.64 | 2.4% | 3.2% |

**5y split by module** (return / PF / win):
- **BEST trio:** A +20.1% / 1.23 / 72%, B +72.8% / 1.47 / 59%, C +21.5% / 2.38 / 47%.
- **PROP trio:** A +21.5% / 1.24 / 72%, B +65.0% / 1.31 / 57%, C +9.7% / 1.40 / 65%.

## Out-of-sample checks (the evidence that decides)

| Case | Validation 2024-03→2025-09 | Recent 2025-09→2026-09 | **Older holdout 2019-09→2021-09 (untouched)** |
|---|---|---|---|
| BEST trio | 141 tr, +9.9%, PF 1.15, DD 7.9% | 77 tr, +14.5%, PF 1.38, DD 8.5% | **153 tr, −20.3%, PF 0.74, DD 22.5%** |
| PROP trio | 160 tr, +12.3%, PF 1.16, DD 10.9% | 90 tr, +5.8%, PF 1.11, DD 11.3% | **181 tr, −24.2%, PF 0.74, DD 29.2%** |
| C-prop alone | 17 tr, +0.9%, PF 1.17 | 12 tr, +0.9%, PF 1.17 | 23 tr, +1.3%, PF 1.21 |

## Per-module verdicts

| Module / objective | Dev (Model 1) | Validation | Recent | Older holdout | 5y vs 5y control (mean R) | Verdict |
|---|---|---|---|---|---|---|
| A best = prop | 80 tr, +22.4%, PF 2.03, win 79% | −0.7%, PF 0.97 | −2.7%, PF 0.85 | −12.0%, PF 0.65 | +0.120 vs **+0.116 random side** | REJECTED (validation) |
| B best (range 960) | 113 tr, +28.5%, PF 1.57 | +5.4%, PF 1.13 | +15.6%, PF 1.89 | −12.4%, PF 0.71 | +0.182 vs −0.001 | REJECTED (validation) |
| B prop (range 480) | 140 tr, +32.5%, PF 1.47 | +10.9%, PF 1.22 | +5.9%, PF 1.19 | **−13.2%, PF 0.77** | +0.147 vs −0.048 | REJECTED (older holdout) |
| C best (Day −1, 2.5R) | 26 tr, +11.1%, PF 4.10 | +4.9%, PF 2.39 | −1.4%, PF 0.68 | +2.9%, PF 1.70 | +0.224 vs +0.021 mid-month | REJECTED (recent) |
| C prop (Day −2, 0.5R) | 30 tr, +6.3%, PF 2.03, win 73% | +0.9%, PF 1.17 | +0.9%, PF 1.17 | +1.3%, PF 1.21 | +0.111 vs −0.008 mid-month | **QUALIFIED** (thin: ~1 trade/month) |

Plateau checks passed for every finalist (100% of ±20% neighbours positive in development).

**Duplicate finalists:**
- In each module the three finalists usually had identical ledgers: "max 2/3 per day" never fires, and EMA50 vs EMA200 gives the same trades.
- So each objective effectively had one real candidate per module.
- For A, the best and prop objectives chose the same setting.

## Robustness (5y native Model 4, `robustness/`)

| | BEST trio | PROP trio |
|---|---|---|
| calyx verdict | WATCH_ONLY | WATCH_ONLY |
| Bootstrap (10,000 paths, block 5): P(profit) | 99.9% | 99.8% |
| Return p05 / p50 / p95 | +47.6% / +113.2% / +212.1% | +32.3% / +95.2% / +191.8% |
| PF p05 / p50 | 1.20 / 1.44 | 1.09 / 1.29 |
| Closed-P/L max DD p50 / p95 | 9.8% / 16.2% | 11.8% / 19.5% |
| 5% daily / 10% total loss-limit breach (closed P/L) | 0.0% / 3.0% | 0.0% / 7.1% (fails the < 5% gate) |
| Trade-order reshuffle: max DD p50 / p95; loss streak p95 | 10.9% / 18.5%; 8 | 14.2% / 23.5%; 8 |
| Random removal 10% / 20%: return p05, PF p05 | +86.2% / 1.36; +68.0% / 1.31 | +68.1% / 1.23; +52.9% / 1.20 |
| **Deflated Sharpe (1,770 trials)** | **63.0%** (needs ≥ 95%) | **38.4%** (needs ≥ 95%) |
| Cost stress (measured tester slippage, $0.03–0.04/trade) | PF 1.44 | PF 1.29 |

The calyx tool counts MT5 deals, so partial closes appear as separate trades there: 616 and 708 deals, and a 73% deal win rate.
The tester's measured slippage is almost zero, so the cost stress is weak evidence; live slippage will be larger.

## Findings

1. **The best version is the BEST trio.**
   - 5y: +114.4%, PF 1.44, equity DD 7.9%, Sharpe 1.61, 62% win, 16-trade longest win streak, 7.3 trades/month.
   - It is positive in validation and in the recent year.
   - **It lost 20.3% on the untouched 2019–2021 holdout**, and its deflated Sharpe (63%) is below the 95% bar.
   - Most of the 5y profit comes from years the search was run on. It is not qualified.
2. **The PROP-objective trio did not beat the BEST trio on the user's prop measures.**
   - Out of sample, win rate, Sharpe and win streak are about equal or lower: 5y win 62.8% vs 62.4%, Sharpe 1.36 vs 1.61, streak 17 vs 16.
   - Drawdown is higher (11.5% vs 7.9%), and it fails the closed-P/L 10% total-loss breach gate (7.1%).
   - **For a prop account the BEST trio is the better of the two**, but neither passed the older holdout.
3. **Breakout is the only module with a real directional edge.**
   - It beats its random-direction control by a wide margin over 5y.
   - But both breakout picks lost about 12–13% in 2019–2021, so the edge looks regime-dependent (it only worked in the 2022–2026 gold trend).
4. **Momentum's optimised profit is a management effect, not a signal.**
   - Random direction with the same management earns the same.
   - It is rejected.
5. **Turn of month Prop is the only fully qualified piece**, and it is small: +8.7% over 5y, about 1 trade a month, PF 1.51, 3.2% DD.
   - It passed every out-of-sample window and beat the mid-month control.
6. **What the search changed most:** limit entries 0.5 ATR back, 50% partial profit at +1R with a tight ATR trail (this is what raises win rate to 60–70%), and breakout trades only in the London–NY overlap.

Not a deployment recommendation. The frozen settings are in `FROZEN PICKS.json`. Promotion to production or the website needs the user's decision.

## Files

| File | Contents |
|---|---|
| `PROTOCOL.md` | frozen rules |
| `PARITY.json` | raw parity check |
| `STAGES-*.json`, `FINALISTS-*.json` | search stages and finalists |
| `PLATEAUS-*.json`, `PICKS-*.json` | plateau checks and picks |
| `FROZEN PICKS.json` | settings and all periods |
| `COMBINATIONS.json` | trio runs |
| `ROBUSTNESS.json`, `robustness/` | calyx reports |
| `TRIAL ACCOUNTING.json` | trial counts |
| `balance-5y.png` | balance graph |
| `native/<batch>/` | case tables, EX5, compile log, SETs, tester.ini, gzipped reports, journals, per-pass trade ledgers |
