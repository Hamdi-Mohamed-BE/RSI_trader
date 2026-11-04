# FTMO17 vs the 5-EA portfolio (2026-11-04)

**Owner request:** compare the picked FTMO17 with EMA3 + Nasdaq 5M (best version) + Gold Overnight VA + XAU RSI VWAP + 3 Way Gold.

**Setup:**
- **G5** = the FTMO17 trade stream filtered to those 5 EAs (2,934 trades, 48.9 per month), so trades, costs and the 3 Way Gold market
  variant are identical to FTMO17's. Nasdaq 5M = deployed ATR6 stop, DI ON.
- **T5** = the earlier Turbo 5 stream (same roster, Nasdaq DI OFF, 3 Way Gold pending variant) for reference.
- **Engines:** the frozen Prop Portfolio Selection engines, seeds and MC pools (`compare5.py`), Prop Ready guard at the chosen risk,
  $100k:
  - FTMO 2-step (`CH-*`);
  - FTMO 1-Step with the built ftmo 1_step guard (`F1P-*`);
  - funded income (`FU-*`);
  - the three-way Monte Carlo (`MC3.json`).

Tables: `TABLES.md` (`python table.py`).

**Verdict: FTMO17 is better on every prop measure.**
- 2-step 0.5%: 61% vs 20% pass.
- 2-step 1%: 58% vs 49%, 95 vs 108 days.
- 1-Step 0.5%: 79% vs 51%, 85 vs 108 days.
- Funded 1%: $3,034 vs $2,364 per month.
- G5 is far weaker in 2021–24 (2-step 0.5% dev / val pass 10% / 12%). Only the 2024–26 starts are close.
- G5 has the higher win rate (60%) but lower expectancy: +0.074R vs +0.092R per trade. It is more cost-sensitive (one-year randomize
  red 32% vs 8% at +0.05R).

**Limits:** Python replay, in-sample; OOS previously viewed. All runs complete (see TABLES.md for funded 0.5%).
