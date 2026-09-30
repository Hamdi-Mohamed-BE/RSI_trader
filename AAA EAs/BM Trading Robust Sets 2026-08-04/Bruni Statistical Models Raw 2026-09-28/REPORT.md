# Bruni statistical models — FTMO / FundedNext research

28 September 2026 · Research only · **No live changes**

## Decision

**Do not advance this batch to optimization or deployment.** The M15 entry approximations fail the frozen three-year gate. The risk overlays do not demonstrate a reliable improvement over fixed risk. This is a rejection of these explicit implementations on these data—not proof that Bruni’s undisclosed system cannot work.

- Nasdaq triple-print: last year +5.44%, PF 1.20, but latest six months −1.17%, and three-year screen PF 1.04. The wick filter does not fix it.
- USDJPY: neither triple-print candidate passes the three-year screen; both lose over the latest year and six months.
- Existing portfolio: 972 native opportunities across 13 EAs. No statistically convincing win/loss clustering after multiplicity adjustment; only 222 opportunities have enough prior data for our conditional-Kelly estimate.
- The evidence-gated seven-loss boost never activates: the largest available historical state sample is 7, against the required 30. “Another win is due” is not a substitute.
- No tested risk overlay clears the predeclared paired-return confidence gate. Some reduce drawdown; that is not evidence for the video’s extreme risk increases.

## What was built, and what was not

Built a tester-only M15 EA with actual/peripheral zone approximations, triple-print validation, a wick-gap filter, a simpler one-print control, 2R target, fixed price-risk and a 48-hour/Friday time exit. Tested Nasdaq CFD (USTEC) and USDJPY; no metals. **The entry trigger, pivot definition, zone segmentation and index wick threshold are ours.** The transcript does not specify enough to reproduce the speaker’s exact system. The full frozen definitions are in [RULES.md](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/Bruni Statistical Models Raw 2026-09-28/RULES.md>).

Separately built six offline sizing policies: fixed, half risk after a loss, capped conditional quarter-Kelly, GARCH volatility cap, combined cap, and evidence-gated VAM. These use earlier closed trades of the same EA only. Unexecuted original opportunities remain a virtual “shadow” ledger, which a live implementation would also need to maintain. Maximum standalone increase is 1.25×; no 0.5%→3% jump.

Not implemented as a claimed trading edge: the missing exact Asia-session entry schematics; volume-profile hierarchy; a fitted Hamilton Markov-switching model; GARCH calm-regime direction reversal; a new target optimization; or automatic rotation/replacement of prop accounts. The supplied material does not establish their parameters or efficacy. Reversal needs its own opposite-order execution test, not negating existing P&L. There is no stage-5 parameter search because the raw gate failed.

## Native M15 results

All variants were frozen before tests. Each starts with $10,000 and targets $100 initial price-risk per position, before commission/slippage; lots round down. This is not compounded 1% risk. Six-month/year tests use native Model 4 real-tick mode with 150 ms delay and source broker costs. Three/five-year results below are **Model 1 screens**, not real-tick confirmation. PF uses complete net trade cash, including costs. Equity DD here is the native report’s peak-relative equity drawdown. /weekday includes all weekdays in the window, including no-trade days. W/L means maximum consecutive winning/losing trades.

**Tick-quality limitation:** both symbols have real ticks only from 1 January 2026. The 6-month tests report 100% real ticks; the 1-year runs report 63% real ticks over the full tester window including warm-up, with generated ticks earlier. November 2025 smoke tests use generated ticks (0% real). Thus one-year results and their prop replays are MIXED-tick evidence, not fully real-tick validation.

### 6m — 100% real-tick report quality


Model | Trades | /month | /weekday | Return | PF | Win % | Equity DD | W/L streak
--- | --- | --- | --- | --- | --- | --- | --- | ---
USDJPY single-print-control | 96 | 15.88 | 0.73 | 12.53% | 1.20 | 39.6% | 11.23% | 4/5
USDJPY triple-print | 28 | 4.63 | 0.21 | -3.79% | 0.81 | 32.1% | 11.30% | 2/6
USDJPY triple-wick | 19 | 3.14 | 0.15 | -3.45% | 0.75 | 31.6% | 7.12% | 2/5
USTEC single-print-control | 95 | 15.72 | 0.73 | 0.29% | 1.00 | 34.7% | 12.27% | 4/6
USTEC triple-print | 20 | 3.31 | 0.15 | -1.17% | 0.91 | 35.0% | 5.47% | 2/5
USTEC triple-wick | 16 | 2.65 | 0.12 | -3.16% | 0.72 | 31.2% | 4.67% | 1/4

### 1y — mixed real/generated ticks


Model | Trades | /month | /weekday | Return | PF | Win % | Equity DD | W/L streak
--- | --- | --- | --- | --- | --- | --- | --- | ---
USDJPY single-print-control | 191 | 15.93 | 0.73 | 9.25% | 1.07 | 36.6% | 17.65% | 4/6
USDJPY triple-print | 40 | 3.34 | 0.15 | -3.98% | 0.86 | 32.5% | 14.12% | 3/9
USDJPY triple-wick | 29 | 2.42 | 0.11 | -4.58% | 0.78 | 31.0% | 10.17% | 2/7
USTEC single-print-control | 192 | 16.01 | 0.74 | -9.58% | 0.93 | 32.8% | 17.63% | 4/8
USTEC triple-print | 45 | 3.75 | 0.17 | 5.44% | 1.20 | 40.0% | 5.25% | 3/5
USTEC triple-wick | 39 | 3.25 | 0.15 | 3.65% | 1.15 | 38.5% | 7.38% | 3/6

### 3y — fast historical screen


Model | Trades | /month | /weekday | Return | PF | Win % | Equity DD | W/L streak
--- | --- | --- | --- | --- | --- | --- | --- | ---
USDJPY single-print-control | 557 | 15.47 | 0.71 | -37.84% | 0.90 | 32.5% | 60.34% | 6/13
USDJPY triple-print | 102 | 2.83 | 0.13 | -12.13% | 0.83 | 31.4% | 20.47% | 3/9
USDJPY triple-wick | 76 | 2.11 | 0.10 | -4.57% | 0.91 | 32.9% | 14.85% | 2/7
USTEC single-print-control | 606 | 16.83 | 0.77 | -86.63% | 0.80 | 29.7% | 92.13% | 4/14
USTEC triple-print | 124 | 3.44 | 0.16 | 3.08% | 1.04 | 35.5% | 13.36% | 3/8
USTEC triple-wick | 103 | 2.86 | 0.13 | 4.62% | 1.07 | 35.9% | 8.66% | 3/7

### 5y — fast historical screen


Model | Trades | /month | /weekday | Return | PF | Win % | Equity DD | W/L streak
--- | --- | --- | --- | --- | --- | --- | --- | ---
USDJPY single-print-control | 963 | 16.05 | 0.74 | -1.12% | 1.00 | 34.8% | 45.44% | 7/13
USDJPY triple-print | 172 | 2.87 | 0.13 | 9.03% | 1.08 | 37.2% | 17.05% | 10/9
USDJPY triple-wick | 130 | 2.17 | 0.10 | 15.27% | 1.19 | 39.2% | 12.54% | 9/7
USTEC single-print-control † | 605 | 10.08 | 0.46 | -100.10% | 0.77 | 29.1% | 100.13% | 5/16
USTEC triple-print | 196 | 3.27 | 0.15 | 28.22% | 1.24 | 39.3% | 10.91% | 3/8
USTEC triple-wick | 161 | 2.68 | 0.12 | 23.00% | 1.24 | 39.1% | 7.34% | 3/7

† The five-year Nasdaq control exhausts its test capital and stops taking all later opportunities. Its −100.10% is a failed, capital-limited path—not a valid complete five-year opportunity benchmark. Do not use it to claim that the candidate’s five-year excess return is robust. Candidate rejection already follows from PF below 1.15 on the three-year screen. All four non-control candidates fail; none was sent for long-window Model 4 confirmation.

## Prop-account results for the new entry approximations

Replay uses the **one-year native trades**, rescaled through the conservative shared-equity account model. It does not reproduce target-server fills. Price paths use sampled native equity and conservative interval lows; low estimates retain some source fee/financing effects, so the envelope is deliberately conservative. Exness lot minima are USTEC 0.05 and USDJPY 0.01; target-firm symbol specifications still need verification.

FTMO: $10,000 Swing two-step, 0.50% maximum base price-risk. FundedNext: $5,000 Stellar Instant, 0.25% maximum base risk, further capped by remaining loss headroom. Firm rules and our tighter guards are described below. “Stress” is a hypothetical adverse-cost scenario, not measured FTMO/FundedNext slippage.

### FTMO — full-year account replay, no withdrawals


Model | Trades | /month | /weekday | Return | PF | Win % | Equity DD | W/L streak
--- | --- | --- | --- | --- | --- | --- | --- | ---
USDJPY-single-print-control base | 78 | 6.50 | 0.30 | -7.59% | 0.75 | 30.8% | 9.55% | 3/9
USDJPY-single-print-control stress | 32 | 2.67 | 0.12 | -7.40% | 0.50 | 31.2% | 8.12% | 2/8
USDJPY-triple-print base | 36 | 3.00 | 0.14 | -2.35% | 0.82 | 33.3% | 7.04% | 5/9
USDJPY-triple-print stress | 25 | 2.08 | 0.10 | -7.69% | 0.38 | 24.0% | 8.49% | 3/9
USDJPY-triple-wick base | 26 | 2.17 | 0.10 | -2.92% | 0.70 | 30.8% | 5.37% | 3/7
USDJPY-triple-wick stress | 26 | 2.17 | 0.10 | -6.23% | 0.47 | 30.8% | 7.49% | 3/7
USTEC-single-print-control base | 129 | 10.76 | 0.49 | -3.73% | 0.92 | 32.6% | 8.46% | 3/11
USTEC-single-print-control stress | 60 | 5.00 | 0.23 | -7.48% | 0.69 | 31.7% | 10.66% | 3/9
USTEC-triple-print base | 44 | 3.67 | 0.17 | 3.23% | 1.25 | 40.9% | 2.89% | 3/4
USTEC-triple-print stress | 44 | 3.67 | 0.17 | -0.33% | 0.98 | 40.9% | 4.10% | 3/4
USTEC-triple-wick base | 38 | 3.17 | 0.15 | 2.33% | 1.20 | 39.5% | 3.93% | 3/6
USTEC-triple-wick stress | 38 | 3.17 | 0.15 | -0.75% | 0.94 | 39.5% | 5.01% | 3/6

### Instant — full-year account replay, no withdrawals


Model | Trades | /month | /weekday | Return | PF | Win % | Equity DD | W/L streak
--- | --- | --- | --- | --- | --- | --- | --- | ---
USDJPY-single-print-control base | 191 | 15.93 | 0.73 | -2.90% | 0.85 | 36.6% | 4.95% | 4/6
USDJPY-single-print-control stress | 117 | 9.76 | 0.45 | -5.17% | 0.42 | 31.6% | 5.51% | 3/6
USDJPY-triple-print base | 40 | 3.34 | 0.15 | -1.75% | 0.70 | 32.5% | 3.20% | 3/9
USDJPY-triple-print stress | 40 | 3.34 | 0.15 | -3.54% | 0.43 | 32.5% | 3.94% | 3/9
USDJPY-triple-wick base | 29 | 2.42 | 0.11 | -1.79% | 0.62 | 31.0% | 2.56% | 2/7
USDJPY-triple-wick stress | 29 | 2.42 | 0.11 | -3.22% | 0.38 | 31.0% | 3.45% | 2/7
USTEC-single-print-control base | 102 | 8.51 | 0.39 | -1.35% | 0.91 | 33.3% | 2.85% | 3/8
USTEC-single-print-control stress | 127 | 10.59 | 0.49 | -4.06% | 0.65 | 33.9% | 5.10% | 4/9
USTEC-triple-print base | 38 | 3.17 | 0.15 | 0.89% | 1.15 | 36.8% | 1.59% | 3/6
USTEC-triple-print stress | 39 | 3.25 | 0.15 | -0.84% | 0.87 | 38.5% | 2.20% | 3/4
USTEC-triple-wick base | 34 | 2.84 | 0.13 | 0.99% | 1.20 | 38.2% | 1.85% | 3/6
USTEC-triple-wick stress | 34 | 2.84 | 0.13 | -0.77% | 0.86 | 38.2% | 2.26% | 3/6

These returns include risk/margin rejection of entries and profit-policy deductions, and are not the native EA returns above. No-withdrawal balances are not payouts. All these replay paths stayed inside the modeled breach barriers; risk guards can stop further trading before a formal breach. A low breach count is not proof of profitable or payout-ready trading.

### Payout lifecycle — new candidates

Weekly historical restarts yield 48 matured 30-day starts, 44 matured 60-day starts, 35 matured 120-day starts, 27 matured 180-day starts. These windows overlap heavily. Counts are **historical conditional eligibility frequencies, not forecast probabilities or independent trials**. Cash assumes approval and excludes acquisition, EA-addon, withdrawal and other paid fees.

- USDJPY-triple-print / FTMO / base: at 180 days 0/27 starts reach an eligible payout; mean modeled cash $0.00; 0 drawdown breaches; 0 QuickStrike blocks.

- USDJPY-triple-print / FTMO / stress: at 180 days 0/27 starts reach an eligible payout; mean modeled cash $0.00; 0 drawdown breaches; 0 QuickStrike blocks.

- USDJPY-triple-print / Instant / base: at 180 days 3/27 starts reach an eligible payout; mean modeled cash $4.89; 0 drawdown breaches; 0 QuickStrike blocks.

- USDJPY-triple-print / Instant / stress: at 180 days 0/27 starts reach an eligible payout; mean modeled cash $0.00; 0 drawdown breaches; 0 QuickStrike blocks.

- USDJPY-triple-wick / FTMO / base: at 180 days 0/27 starts reach an eligible payout; mean modeled cash $0.00; 0 drawdown breaches; 0 QuickStrike blocks.

- USDJPY-triple-wick / FTMO / stress: at 180 days 0/27 starts reach an eligible payout; mean modeled cash $0.00; 0 drawdown breaches; 0 QuickStrike blocks.

- USDJPY-triple-wick / Instant / base: at 180 days 0/27 starts reach an eligible payout; mean modeled cash $0.00; 0 drawdown breaches; 0 QuickStrike blocks.

- USDJPY-triple-wick / Instant / stress: at 180 days 0/27 starts reach an eligible payout; mean modeled cash $0.00; 0 drawdown breaches; 0 QuickStrike blocks.

- USTEC-triple-print / FTMO / base: at 180 days 0/27 starts reach an eligible payout; mean modeled cash $0.00; 0 drawdown breaches; 0 QuickStrike blocks.

- USTEC-triple-print / FTMO / stress: at 180 days 0/27 starts reach an eligible payout; mean modeled cash $0.00; 0 drawdown breaches; 0 QuickStrike blocks.

- USTEC-triple-print / Instant / base: at 180 days 20/27 starts reach an eligible payout; mean modeled cash $33.08; 0 drawdown breaches; 0 QuickStrike blocks.

- USTEC-triple-print / Instant / stress: at 180 days 8/27 starts reach an eligible payout; mean modeled cash $12.65; 0 drawdown breaches; 0 QuickStrike blocks.

- USTEC-triple-wick / FTMO / base: at 180 days 0/27 starts reach an eligible payout; mean modeled cash $0.00; 0 drawdown breaches; 0 QuickStrike blocks.

- USTEC-triple-wick / FTMO / stress: at 180 days 0/27 starts reach an eligible payout; mean modeled cash $0.00; 0 drawdown breaches; 0 QuickStrike blocks.

- USTEC-triple-wick / Instant / base: at 180 days 17/27 starts reach an eligible payout; mean modeled cash $28.60; 0 drawdown breaches; 0 QuickStrike blocks.

- USTEC-triple-wick / Instant / stress: at 180 days 8/27 starts reach an eligible payout; mean modeled cash $12.65; 0 drawdown breaches; 0 QuickStrike blocks.

For Nasdaq triple-print this is only about $33 mean cash over 180 days under the Instant base assumptions, falling to about $13 under stress, before paid fees. No new candidate reaches an FTMO payout in the tested 180-day restarts. This does not justify buying an account for these models.

## Risk overlays on the existing 13-EA portfolio

Common source: 27 September 2025–25 September 2026 (exclusive end). Validation replay: 27 March–25 September 2026. Source EAs/settings were already selected using historical evidence, so this is **not an untouched out-of-sample test**. Multipliers themselves are causal: no trade’s result is usable until it closed strictly before the next entry minute. Broader price correlation and overlapping trades remain relevant even when binary outcome clustering is weak.

Below is second-half account replay without withdrawals. Same source prices, guards and fee policy for every overlay. DD is conservative peak-to-trough equity decline divided by initial capital, **not** the firms’ loss threshold or native peak-relative DD. A funded-style static FTMO loss barrier can survive a peak-to-trough DD larger than 10% of initial capital when earlier profits provide buffer. This should not be mistaken for passing evaluation phases.

### FTMO — chronological validation


Model | Trades | /month | /weekday | Return | PF | Win % | Equity DD | W/L streak
--- | --- | --- | --- | --- | --- | --- | --- | ---
fixed base | 283 | 47.33 | 2.18 | 8.59% | 1.16 | 46.6% | 10.78% | 7/10
fixed stress | 253 | 42.31 | 1.95 | -7.87% | 0.85 | 45.8% | 19.00% | 6/10
after-loss-half base | 329 | 55.02 | 2.53 | 15.17% | 1.34 | 48.0% | 4.98% | 6/13
after-loss-half stress | 325 | 54.35 | 2.50 | 3.14% | 1.06 | 47.7% | 9.92% | 6/13
conditional-kelly-capped base | 285 | 47.66 | 2.19 | 11.32% | 1.21 | 50.2% | 8.42% | 7/6
conditional-kelly-capped stress | 283 | 47.33 | 2.18 | -3.64% | 0.94 | 48.8% | 16.22% | 6/7
garch-vol-cap base | 298 | 49.84 | 2.29 | 8.65% | 1.18 | 46.6% | 8.39% | 5/7
garch-vol-cap stress | 256 | 42.81 | 1.97 | -7.87% | 0.83 | 44.9% | 17.13% | 5/7
combined-capped base | 294 | 49.17 | 2.26 | 6.63% | 1.13 | 49.0% | 9.43% | 7/9
combined-capped stress | 255 | 42.65 | 1.96 | -7.77% | 0.84 | 47.1% | 16.55% | 6/7
vam-evidence-gated base | 283 | 47.33 | 2.18 | 8.59% | 1.16 | 46.6% | 10.78% | 7/10
vam-evidence-gated stress | 253 | 42.31 | 1.95 | -7.87% | 0.85 | 45.8% | 19.00% | 6/10

### Instant — chronological validation


Model | Trades | /month | /weekday | Return | PF | Win % | Equity DD | W/L streak
--- | --- | --- | --- | --- | --- | --- | --- | ---
fixed base | 180 | 30.10 | 1.38 | 7.10% | 1.42 | 45.6% | 2.22% | 8/7
fixed stress | 169 | 28.26 | 1.30 | 0.14% | 1.01 | 43.2% | 3.14% | 8/7
after-loss-half base | 138 | 23.08 | 1.06 | 5.61% | 1.56 | 45.7% | 2.05% | 7/10
after-loss-half stress | 131 | 21.91 | 1.01 | 0.94% | 1.09 | 42.7% | 2.72% | 7/9
conditional-kelly-capped base | 166 | 27.76 | 1.28 | 8.23% | 1.51 | 47.0% | 2.52% | 6/6
conditional-kelly-capped stress | 169 | 28.26 | 1.30 | -0.05% | 1.00 | 43.2% | 3.29% | 8/7
garch-vol-cap base | 163 | 27.26 | 1.25 | 5.82% | 1.42 | 45.4% | 1.94% | 8/8
garch-vol-cap stress | 156 | 26.09 | 1.20 | -0.65% | 0.96 | 43.6% | 3.11% | 8/8
combined-capped base | 163 | 27.26 | 1.25 | 6.21% | 1.42 | 45.4% | 2.25% | 6/6
combined-capped stress | 163 | 27.26 | 1.25 | -0.85% | 0.95 | 43.6% | 2.93% | 8/7
vam-evidence-gated base | 180 | 30.10 | 1.38 | 7.10% | 1.42 | 45.6% | 2.22% | 8/7
vam-evidence-gated stress | 169 | 28.26 | 1.30 | 0.14% | 1.01 | 43.2% | 3.14% | 8/7

FTMO half-risk-after-loss improves this guarded replay’s drawdown and return, but takes more trades because smaller orders pass margin/exposure guards. In the equal-opportunity shadow ledger it actually removes 15.17R of return. That distinction matters: it is not evidence of a dependable “next trade after a loss” advantage. Conditional Kelly’s apparent benefit is also not robust enough to promote.

### Rolling payout check for the existing portfolio

Second-half Monday starts mature into 22 30-day, 18 60-day and 9 120-day observations. There are **no matured 180-day starts** after 30 March in this data. FTMO has no payout within the tested 120-day horizons for any policy, though some paths pass an earlier evaluation stage. Instant 120-day results follow; cash is before fees and all provider discretion.

- fixed (base): 9/9 eligible; mean cash $83.79; drawdown breaches 0; compliance blocks 0.

- fixed (stress): 5/9 eligible; mean cash $21.93; drawdown breaches 0; compliance blocks 0.

- after-loss-half (base): 9/9 eligible; mean cash $59.14; drawdown breaches 0; compliance blocks 0.

- after-loss-half (stress): 5/9 eligible; mean cash $27.69; drawdown breaches 0; compliance blocks 0.

- conditional-kelly-capped (base): 9/9 eligible; mean cash $81.31; drawdown breaches 0; compliance blocks 0.

- conditional-kelly-capped (stress): 5/9 eligible; mean cash $27.71; drawdown breaches 0; compliance blocks 0.

- garch-vol-cap (base): 9/9 eligible; mean cash $90.43; drawdown breaches 0; compliance blocks 0.

- garch-vol-cap (stress): 4/9 eligible; mean cash $18.97; drawdown breaches 0; compliance blocks 0.

- combined-capped (base): 9/9 eligible; mean cash $85.05; drawdown breaches 0; compliance blocks 0.

- combined-capped (stress): 6/9 eligible; mean cash $28.12; drawdown breaches 0; compliance blocks 0.

- vam-evidence-gated (base): 9/9 eligible; mean cash $83.79; drawdown breaches 0; compliance blocks 0.

- vam-evidence-gated (stress): 5/9 eligible; mean cash $21.93; drawdown breaches 0; compliance blocks 0.

### Statistical validation and the 10,000-path check

All 13 per-EA Fisher transition tests have raw p-values above 0.16; Holm-adjusted p-values are 1.00. This is insufficient evidence of serial win/loss predictability, not proof of exact independence. Samples range from 11 to199 trades per EA, so combining them into “972 trades” cannot solve a per-strategy sample shortage. Conditional Kelly qualifies on222/972 opportunities; VAM qualifies onnone. Full estimates, Wilson intervals, chronological chunks, expectancy and profit factor with the best winner removed are in [DIAGNOSTICS.json](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/Bruni Statistical Models Raw 2026-09-28/DIAGNOSTICS.json>).

The paired block bootstrap resamples 28-day blocks of the **realized second-half shadow-ledger differences**, 10,000 paths. It retains zero-trade days. The following are net-R differences versus fixed risk, with fifth/ninety-fifth percentile sampling bounds. This is a diagnostic distribution, **not** a new simulation of adaptively re-estimated Kelly/GARCH states on each synthetic path, and not a future prop pass probability.

- fixed: observed +0.00R; bootstrap range [+0.00, +0.00]R.

- after-loss-half: observed -15.17R; bootstrap range [-24.96, -4.91]R.

- conditional-kelly-capped: observed +1.79R; bootstrap range [-2.82, +6.47]R.

- garch-vol-cap: observed -8.13R; bootstrap range [-17.76, -0.25]R.

- combined-capped: observed -6.46R; bootstrap range [-16.88, +3.20]R.

- vam-evidence-gated: observed +0.00R; bootstrap range [+0.00, +0.00]R.

No non-control model has a positive lower bound. Risk reductions naturally can reduce both gains and drawdown; these difference tests do not by themselves rank utility or prove volatility sizing is useless. No full stage-6 promotion Monte Carlo was warranted after the earlier gates failed.

### GARCH findings and skill fallback

The regime-analysis skill influenced the past-data-only design and prefix-invariance tests. Its referenced Markov helper was absent locally. The study therefore directly implemented the interview’s GARCH(1,1) volatility forecast using constrained estimation, not an undisclosed substitute Markov classifier. GARCH forecasts conditional variance—not the next direction or a guaranteed calm session. [Model/forecast reference](https://arch.readthedocs.io/en/latest/univariate/forecasting.html).

The isolated collector supplied 540–542 daily bars per instrument, starting 1January2025, not the requested 2021 history. This still supports the frozen 252-return minimum; first forecasts start 23–24October2025. Of972 opportunities,232 lack enough forecast history to assign a bucket and use the default sizing. Source daily bars include short Sunday sessions, so volatility buckets mix session lengths. All 36 monthly fits converged, but calibration was imperfect: e.g. Nasdaq extreme-bucket predicted variance averages 3.83 percentage-points-squared against 2.37 realized. No tuning or reverse-direction rule was added after seeing this. See [GARCH_AUDIT.json](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/Bruni Statistical Models Raw 2026-09-28/GARCH_AUDIT.json>).

## Drawdown shield: cash, exposure and account constraints

In the transcript’s simple noncompounded example (weekly−7%, +3%,−4%, +4%), four $50k accounts traded one at a time generate−$2,000 combined simulated trading P&L. Withdrawing the two winning slices gives $3,500 gross and $2,800 cash at an assumed 80% split, leaving $194,500 combined simulated balance. Two accounts retain a combined $5,500 drawdown.

At the same percentage risk, one $200k account instead takes four times the active dollar exposure and loses $8,000. Reducing that single account’s percentage risk to one-quarter gives the same−$2,000 gross result as the rotation. Thus the comparison combines less dollar risk with segregated payout accounting; it does not create a market edge.

**Simulated balances are not trader-owned cash.** Adding residual account balances to payouts is not a valid measure of personal wealth. In this toy example actual trader cash is$2,800 minus all account/EA/reset/other paid fees; it is not automatically a$2,700 personal loss. Future earning capacity and probability of losing accounts still matter. The transcript’s80% split is not our Stellar Instant Tier 1 assumption. We did not buy, cycle, sacrifice or replace accounts.

FTMO explicitly prohibits account rolling and substantially inconsistent position sizing. FundedNext also restricts account rolling; its example concerns acquiring multiple evaluations and deliberately sacrificing some. Ordinary ownership of multiple accounts is not automatically the same thing, but an operational “lose this account, move on” plan is not treated as approved. Small payouts do not excuse breaches. [FTMO practices](https://ftmo.com/en/forbidden-trading-practices/), [FundedNext practices](https://help.fundednext.com/en/articles/8020351-what-are-the-restricted-prohibited-trading-strategies).

## Rules and assumptions checked on28 September 2026

- FTMO **two-step**, not one-step:10% then 5% targets, four entry days per phase,5% daily equity-loss amount resetting at Prague midnight and 10% static overall loss amount. These differ from one-step rules on the same page. Our simulation uses two/five business days for review/handover and 14-day funded payout timing; timing is an assumption, not a service guarantee. [Trading objectives](https://ftmo.com/en/trading-objectives/).

- Stellar Instant: no formal daily-loss limit;6% balance-trailing maximum loss, capped at initial balance, not reset down by withdrawals. We retain an additional 3% initial-capital cushion when withdrawing. Our tighter 0.75% internal daily stop is **ours**, not a FundedNext rule. [Loss-limit policy](https://help.fundednext.com/en/articles/11641163-what-are-the-daily-loss-limit-and-the-maximum-loss-limit-for-the-stellar-instant-accounts).

- Instant cash timing: at least 1% growth after 14 days or5% growth confirmed at end-of-day. Tier 1 cash split modeled 70%; no scaling-tier uplift modeled. [Eligibility](https://help.fundednext.com/en/articles/11641693-what-is-the-eligibility-criteria-for-my-performance-reward-in-the-stellar-instant-account).

- Instant requires stops and ordinarily limits cumulative open risk to3%, or1% after reclassification. Its news attribution credits 40% of positive flagged profit while retaining full losses; any execution within±5 minutes can qualify. QuickStrike concerns profitable trades closed within 30 seconds reaching 30% of recorded positive profit. [Clarity Cards](https://help.fundednext.com/en/articles/15644011-what-are-the-clarity-cards-and-how-do-they-affect-my-account).

- Official QuickStrike descriptions conflict: the Clarity page describes deduction/termination on a second violation; the general prohibited-strategies page describes termination at the breached cycle. The simulator conservatively blocks cash at the first qualifying request and records a **compliance block separately from drawdown breach**. This is not an assertion that the firm always terminates on the first violation. No modeled case here reached that block.

- Instant’s dedicated EA page requires its paid addon, customized/distinct strategies and compliance with its allocation/copying restrictions; it also restricts EAs integrated with third-party tools such as Telegram/WhatsApp. Any planned production adaptation needs a separate eligibility check. Leverage uses the stricter help-page value: indices 5, gold 7.5, forex 30; marketing material may differ. These pages were accessible earlier in this session but later returned 403 on recheck. [EA policy](https://help.fundednext.com/en/articles/11641338-can-i-use-ea-in-stellar-instant), [Leverage](https://help.fundednext.com/en/articles/11641369-what-is-the-leverage-provided-in-the-stellar-instant-accounts).

## Important corrections to the interview

1. Two wins out of six is33.33%, not 23%. Comparing unconditional win rate with win rate after a loss gives a percentage-point difference, not an autocorrelation coefficient and not a90% next-win probability.
2. The Lo–MacKinlay paper studied weekly historical stock returns. It does not validate serial predictability in these EA trades or show that seven losses imply an imminent win. [Author’s abstract](https://www.mit.edu/~alo/Papers/lo-mackinlay-88.html).
3. Binary Kelly is f=p−(1−p)/b for fixed+ b/−1 payoffs. It maximizes a particular long-run log-growth objective under its assumptions; it does not enforce prop drawdown survival. Our real trades have variable payoffs, gaps and costs, so even fractional Kelly is an approximation.
4. Zero serial outcome correlation does not rule out useful sizing based on volatility, expected payoff, spread, exposure or other independently validated predictors.
5. Reversing a75%-losing strategy does not guarantee 75% wins: both sides pay costs, their barriers can differ, fills and holding times change, and both directions can lose net.
6. More trades reduce sampling error only under appropriate dependence assumptions. A thousand observations, stable chunks or a published paper do not prove a live edge. Target selection and repeated testing still create overfitting risk.
7. Profit factor and expectancy both depend on the same underlying cash outcomes; removing the largest winner is a sensitivity check, not a universal edge certificate. Sharpe requires a specified return frequency and volatility denominator.

## Evidence limitations and audit

This study uses exactly 972 existing portfolio opportunities, not thousands of independent Bruni trades, with only 29 locally known news events in the source calendar. Target-firm bid/ask ticks, full news coverage, financing schedules, payout discretion, plan availability and actual paid fees remain unverified. CFDs are not NQ futures; index levels and contract values are not interchangeable. Source spread records contain zeros, so native costs alone can be optimistic.

Hypothetical stress reduces positive gross profits 10%, worsens negative gross profits 10%, adds spread/slippage allowances ($20/lot gold,$2/lot Nasdaq or0.02 JPY converted per FX lot), and stresses carry. It is not a measured broker cost forecast. No paid-fee ROI or guarantee is reported. Equal percentage risk is not equal dollar risk across $10k and $5k accounts.

Checks: 20 automated tests passed; 30 native runs (6 smoke, 12 recent/year Model-4 runs, 12 long-window screens); 857,009 native trace/cash items checked; maximum cash reconciliation error below $0.01. All six overlapping 6m/1y comparisons match trade-for-trade after the initial boundary week (261 matched trades).

Tests cover causality, same-minute/pending trade exclusion, per-EA training, GARCH prefix invariance, sizing caps, stop-loss breaches before profitable closes, FTMO phases, Prague daylight saving, Instant floor retention, minimum lots, QuickStrike block classification and fixed-policy parity with the prior simulator. Source hashes and frozen rules remain unchanged. The live MT5 process retained the same PID and creation time; no production tracked files changed.

## Artifacts and next decision

Research implementation: [BruniProxy.mq5](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/Bruni Statistical Models Raw 2026-09-28/BruniProxy.mq5>); frozen configuration: [run-config.json](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/Bruni Statistical Models Raw 2026-09-28/run-config.json>); raw evidence: [RAW_RESULTS.json](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/Bruni Statistical Models Raw 2026-09-28/RAW_RESULTS.json>); account results: [NATIVE_PROP.json](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/Bruni Statistical Models Raw 2026-09-28/NATIVE_PROP.json>) and [OVERLAYS.json](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/Bruni Statistical Models Raw 2026-09-28/OVERLAYS.json>); verification: [VERIFICATION.json](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/Bruni Statistical Models Raw 2026-09-28/VERIFICATION.json>). Full native reports, deal ledgers, settings, tick traces and journals are retained under the native folder. Reproduction commands are in [README.md](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/Bruni Statistical Models Raw 2026-09-28/README.md>).

**Next useful input is the exact video/chart entry examples or a complete mechanical rule sheet**, especially how an impulse/retracement becomes a valid breakout and the Asia-session entry trigger. That would permit a new frozen exact-specification test. It would not justify tuning this failed approximation on the same recent outcomes. No EA, risk policy or account-rotation plan is approved for deployment from this study.
