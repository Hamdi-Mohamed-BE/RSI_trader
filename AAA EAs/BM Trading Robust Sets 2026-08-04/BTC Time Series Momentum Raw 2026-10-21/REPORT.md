# BTC time-series momentum + volatility targeting — RAW REPORT (2026-10-21)

**Verdict: BOTH main versions PASS the raw gate (LF spot long/flat and LS perps long/short). Not optimised, not deployed.**
Rules frozen before testing: RULES.md (incl. the pre-run Model 1 screen revision). Generated tables: RESULTS.md / RESULTS.json.
Chart: equity.png. Native MT5, BTCUSD CFD (Exness Trial16), $100,000, end 2026-10-20 exclusive; 25 runs, 0 failed orders.
Real ticks only from 2026-01-01. Model 1 and Model 4 agree on 5y (LF +60.66% vs +60.67%, LS +78.7% vs +78.9%).

## Gate runs (Model 4)
| Version | Window | Return | CAGR | Sharpe | Equity DD | Closed DD | Exposure | Avg size | Positions | / month | / day | Episode PF / win | Episode win/loss streak avg (max) | Consistency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LF | 6m | +14.4% | 31.0% | 1.49 | 10.4% | — | 69% | 0.55× | 16 | 2.66 | 0.09 | 4.43 / 17% | | 43% |
| LF | 1y | +1.9% | 1.9% | 0.19 | 19.6% | — | 51% | 0.55× | 31 | 2.59 | 0.09 | 1.10 / 25% | | 23% |
| LF | 3y | +60.5% | 17.1% | 0.97 | 22.0% | 16.6% | 60% | 0.50× | 96 | 2.67 | 0.09 | 1.77 / 35% | 1.6 (4) / 3.2 (7) | 43% |
| LF | 5y | +60.9% | 10.0% | 0.65 | 26.1% | 23.4% | 53% | 0.48× | 148 | 2.47 | 0.08 | 1.56 / 33% | 1.7 (4) / 3.4 (10) | 38% |
| LS | 6m | +21.8% | 48.6% | 1.80 | 13.8% | — | 100% | 0.57× | 26 | 4.32 | 0.14 | 3.11 / 27% | | 71% |
| LS | 1y | +15.2% | 15.3% | 0.73 | 18.3% | — | 100% | 0.51× | 63 | 5.25 | 0.17 | 1.40 / 30% | | 54% |
| LS | 3y | +37.7% | 11.3% | 0.58 | 33.0% | 22.7% | 100% | 0.48× | 184 | 5.11 | 0.17 | 1.27 / 33% | 1.4 (3) / 2.9 (8) | 57% |
| LS | 5y | +79.2% | 12.4% | 0.63 | 33.0% | 22.8% | 100% | 0.46× | 296 | 4.93 | 0.16 | 1.33 / 34% | 1.4 (5) / 2.7 (8) | 57% |
Equity DD = native MT5 floating-equity drawdown, "relative" (largest % from a peak); closed DD from closed positions. An episode
is one signal period (flip to flip). **Correction 2026-10-22:** LF 5y equity DD was first reported as 22.1%. That is MT5's
"maximal" figure, the % at the largest $ drawdown. The true largest % is 26.1% (in 2022). All other rows match both measures.
Positions include weekly rebalance legs.

## Raw gate
| Version | Positive 3y & 5y | Episode PF ≥ 1.15 3y & 5y | ≥ 30 positions | 5y Sharpe > always-long vol-target | > random mean | Best day / best trade | Verdict |
|---|---|---|---|---|---|---|---|
| LF | yes | yes (1.77 / 1.56) | yes | yes (0.65 vs 0.15) | yes (vs 0.09) | yes (5y without best day +$42,151) | **PASS** |
| LS | yes | yes (1.27 / 1.33) | yes | yes (0.62 vs 0.15) | yes | yes (5y without best day +$55,036) | **PASS** |
Diagnostic: without the 5 best days, every version turns negative (LF 5y −$8,397; LS 5y −$6,210). That is typical of trend
following ("wins big on a few trends"), but the edge is concentrated.

## Controls and benchmark (Model 1, 5y, like for like)
| Version | Return | CAGR | Sharpe | Max DD | Positions | / month | Costs |
|---|---|---|---|---|---|---|---|
| LF (both rules) | +60.9% | 10.0% | 0.65 | 25.0% | 148 | 2.47 | −$22,296 |
| VTL: vol targeting only, always long (Rule 1 removed) | +3.6% | 0.7% | 0.15 | 45.9% | 161 | 2.68 | −$28,771 |
| FIX: signal only, fixed 1× (Rule 2 removed) | +44.8% | 7.7% | 0.39 | 51.3% | 82 | 1.37 | −$39,527 |
| Random signal, LF flip rate (mean of 3) | +1.0% | | 0.09 | 30.9% | ~153 | ~2.55 | ~−$16,400 |
| BH: buy and hold 1× | −25.2% | −5.7% | 0.29 | 87.8% | 1 | — | −$52,947 |
Both rules contribute: the signal turns flat vol-targeting into +61%, and vol targeting raises Sharpe from 0.39 to 0.65 while
halving drawdown.

**Swap is the dominant cost on this CFD.** Buy and hold gained +$27,391 gross but paid −$52,941 in swap. LF paid −$21,839 in
swap and −$456 in commission; LS paid −$25,254 and −$1,055. On spot BTC (no financing), LF gross would be about +83% over 5y.
Perpetual futures charge funding instead, which varies over time.

## Per year (Model 1)
| Version | 2021 (from Oct 20) | 2022 | 2023 | 2024 | 2025 | 2026 (to Oct 20) |
|---|---|---|---|---|---|---|
| LF | −2.1% | −21.6% | +61.7% | +26.1% | −0.4% | +3.0% |
| LS | +5.0% | −10.9% | +70.2% | +3.3% | +0.6% | +6.9% |
| BH | −28.9% | −81.5% | +229.7% | +160.8% | −16.5% | −18.6% |
| VTL | −9.8% | −38.2% | +42.4% | +46.5% | −5.0% | −5.4% |
| FIX | −7.4% | −44.9% | +121.6% | +33.4% | −1.2% | −3.3% |
Most of the gain came from the late-2023 / early-2024 trend; equity has been roughly flat since early 2024 (LF last 12 months
+1.9%). It lost 21.6% in 2022 despite going flat in down-trends: the chop and whipsaws the clip warns about.

## Sensitivities (Model 1, 5y; declared before testing, not used to pick)
| Version | Return | Sharpe | Max DD | Positions | Episode PF |
|---|---|---|---|---|---|
| Lookback 20 / 60 / 90 days | +48.8% / +31.3% / +6.2% | 0.57 / 0.40 / 0.15 | 28.7% / 31.3% / 34.0% | 168 / 119 / 123 | 1.46 / 1.40 / 1.09 |
| Target vol 10% / 30% | +29.4% / +73.0% | 0.66 / 0.58 | 13.3% / 35.7% | 150 / 141 | 1.59 / 1.43 |
| 60-day vol window | +53.8% | 0.65 | 20.8% | 127 | 1.55 |
| Leverage cap 2× | identical to LF (BTC vol never fell below 20%, so the cap never bound) | | | | |
| Daily rebalance | +45.3% | 0.55 | 25.3% | 252 | 1.43 |
| Signal checked weekly only | +61.0% | 0.66 | 22.3% | 95 | 2.16 |
Stable in the 20–60-day lookback range, fading at 90. Weekly rebalancing beats daily (costs). A weekly-only signal performs the
same as daily with fewer trades.

## Recommendation (pipeline stage 4 → 5)
Survivors for optimisation: **LF** (better risk-adjusted: Sharpe 0.65, equity DD 26%) and **LS** (higher return, DD 31–33%).
Open points to answer before stage 5 (self-review; the fresh-context /bear-review was not run):
1. The edge is concentrated in one trend (2023–24) and has been flat for about 2.5 years.
2. The 5-best-days falsifier goes negative.
3. CFD swap costs are about 22% of capital over 5y; on another venue the cost profile differs (funding).
4. One asset only; trend following is usually run across many markets, so an ETH/XAU/US100 transfer is untested.
5. Real ticks only from 2026.
6. The OOS 2024-10-20 → 2026-10-20 window has now been viewed (labelled retrospective for any stage-5 split).
Nothing installed, no SET/BAT/live change, no push.
