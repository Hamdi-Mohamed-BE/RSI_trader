# Edge portfolio E10 vs FTMO17 (2026-11-04)

**What E10 is:** the Edge Scan 2026-11-04 list plus Nasdaq 5M (ATR6, DI ON) and XAU RSI VWAP.
- **Bots:** USDJPY London, EMA3, ORB VP Volume Confirmed, ORB VP, Sell Nasdaq 15min, XAU Regime Switch, XAU Elliott Wave 1-2-3,
  3 Way Gold breakout module (930930101, market variant), Nasdaq 5M, XAU RSI VWAP.
- **Trades:** 3,098 (51.6 per month), from the same 5-year native streams as FTMO17.
- **Engines:** the same frozen engines, seeds and Prop Ready guard as FTMO17 (`compare_e10.py`).

Full tables: `TABLES.md` (`python table.py`). G5 is shown in the tables for reference.

**Results:**
- **FTMO 2-step:** FTMO17 is slightly better at 0.5% (61% vs 55%); about equal at 1% (58% vs 58%, 95 vs 96 days).
- **FTMO 1-Step (built guard):**
  - At 0.5%, FTMO17 is better: 79% vs 74% pass, the same 85 vs 86 days.
  - FTMO17 is steadier: 2021-23 starts pass 64% vs 28%.
  - At 0.75%, the two are equal (67% vs 66%).
- **Funded 0.5%:** E10 earns more per month while alive ($2,641 vs $2,446) but lives shorter (736 vs 1,036 days); total median $63k vs $72k.
- **Edge quality:** E10 is clearly better.
  - Mean +0.174R vs +0.092R per trade; PF 1.38 vs 1.26.
  - One-year randomize red at +0.10R extra cost: 10% vs 61%, so E10 survives worse broker costs.

**Verdict:**
- **For passing FTMO with recorded costs:** FTMO17 is narrowly better and more consistent across start years.
- **E10's edge** is twice as large per trade and far more cost-robust, but it relies more on 2023-26.

**Limits:** in-sample; the E10 list was chosen after seeing this history (selection bias). No installer exists for E10: five of its bots have no
guarded wrapper yet.

## Funded income (FTMO standard funded rules, $100k, 36-month MC) — `INCOME.md` (`income.py`, `funded_u.py`)
| Portfolio | Risk | Income / month while trading | 36 m total (median) | Accounts after 36 months |
|---|---|---:|---:|---|
| FTMO17 guarded | 0.5% | $2,446 | $72k | 51% stopped by the guard, 0% breach |
| E10 guarded | 0.5% | $2,641 | $63k | 66% stopped, 0% breach |
| FTMO17 no guard | 0.5% | $3,214 | $101k | 45% breach |
| E10 no guard (Edge 10 package) | 0.5% | $3,580 | $120k | 33% breach |
| FTMO17 no guard | 1% | $5,762 | $21k | 100% breach (median 107 d) |
| E10 no guard | 1% | $6,503 | $33k | 100% breach (median 155 d) |

- **0.75%:** still running at the time of this commit.
- **Rules modelled:** FTMO standard funded rules (10% static max loss, 5% daily). FTMO 1-Step funded accounts use a 3% daily loss and a trailing
  max loss, so unguarded breaches would be higher there.
- **Package parity:** `parity.py` → `PARITY.json` (10/10 identical).
