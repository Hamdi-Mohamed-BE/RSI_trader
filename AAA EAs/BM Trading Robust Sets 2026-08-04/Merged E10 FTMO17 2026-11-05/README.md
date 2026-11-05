# Merged E10 + FTMO17 (M22), 2026-11-05

**Owner request:** merge E10 and FTMO17, show results with and without guard, full results and Monte Carlo for all the years; add buy and hold to the pipeline.

**M22** = FTMO17's 17 EAs + 5 E10-only bots (ORB VP Volume Confirmed, ORB VP, Sell Nasdaq 15min, XAU Regime Switch, XAU Elliott Wave). 22 EAs; overlapping bots run once; 3 Way Gold keeps all modules.

**Files:** `TABLES_ALL_YEARS.md` (`native.py`, `analyze.py`), `TABLES_PROP.md` (`merged.py`, `prop_tables.py`).

**Two evidence types:**
- **All years:** 22 standalone native Model 4 runs, 2019-01 → 2026-11, replayed together in Python. USTEC data starts 2019-07-16; ticks before 2026 are generated. Guards replayed from closed balance. All native runs OK.
- **FTMO simulations:** frozen engines on the 2021-10 → 2026-10 streams with intratrade marks, $100k, 2,000-path MC.

## All years, per trade, no guard, fixed risk (no compounding)
| Portfolio | Trades (/month) | PF | Mean R | Total R | Real DD R | Shuffle p95 DD R | At 0.5%: return / DD |
|---|---:|---:|---:|---:|---:|---:|---|
| FTMO17 | 8,118 (86.4) | 1.13 | +0.049 | +400 | 109.7 | 61.7 | +200% / 54.8% |
| E10 | 4,989 (53.1) | 1.24 | +0.116 | +576 | 65.4 | 49.6 | +288% / 32.7% |
| M22 | 9,718 (103.4) | 1.16 | +0.065 | +630 | 162.3 | 67.1 | +315% / 81.1% |

Three-way MC gates, all years:
- **Resample ≤ 5%:** all PASS (0%).
- **Randomize ≤ 10%:** FTMO17 FAIL (55.9%), E10 PASS (0%), M22 PASS (0%).
- **CLUMPED LOSSES flag:** all three (real DD worse than 99.3-100% of shuffles). The 5-year stream showed 52% for FTMO17: the damage is in 2019-21, which the streams do not include.
- **One year, randomize red:** FTMO17 50%, E10 13%, M22 36%.
- **Break-even extra cost:** FTMO17 0.049R, E10 0.116R, M22 0.065R.

## Verdict
- **Best quality: E10.** Best per-trade edge, smallest drawdown, most cost-robust, only portfolio positive in the 2019-23 development window (+43.6% vs -24.9% and -36.3% at 0.5%).
- **Merging raises income and risk together.** On the 2021-26 funded simulation, M22 no guard at 0.5% earns the most ($4,978/month, $150k median over 36 months) but 50% of accounts breach, against E10's $3,580, $120k and 33%. Over all years M22 has by far the largest drawdown (162R vs 65R), and the funded simulation does not include the 2019-21 years that caused it.
- **Challenges:** no clear gain. No guard at 0.5%: 2-step M22 78% (E10 69%, FTMO17 73%); 1-Step M22 78% with 21% breach (E10 87% with 8%). With guard, 1-Step 0.5%: FTMO17 79%, M22 78%, E10 74%; 2021-23 starts 64%, 36%, 28%.
- **Buy and hold:** all three beat XAUUSD and USTEC on return and return/DD at fixed 0.5%. Financing cost hold: gold +207.6% price, -144.2% swap; USTEC +257.8%, -207.1%.
- **FTMO17 fails the randomize gate over all years**, and DMC Current XAU, Gold Overnight and Nasdaq Overnight lost money over 2019-26.

**Limits:** in-sample; E10 was picked on 2021-26 data, though 2019-21 was not used to pick it. Continuous guards freeze at their buffer within months in 2019, so guarded yearly figures are fresh-start each year.

## Since 2024 (`equity_2024.py`, `funded_2024.py`, `chart_2024.py`; EQUITY_2024.md, FUNDED_2024.md, EQUITY_2024.png)
Correction 2026-11-05: a trade opening and closing in the same second (1 of 9,718, Gold Overnight) had stayed open forever in the guarded replays. Fixed; only FTMO17 and M22 guarded rows from 2026-07 moved (1-Step 0.5% 2026: FTMO17 +26.7% -> +30.7%, M22 +26.3% -> +17.4%).
