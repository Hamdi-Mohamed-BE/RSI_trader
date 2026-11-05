# FTMO17 vs E10, October 2026, 1% risk (2026-11-04)

`oct_compare.py` → `RESULTS.md` / `RESULTS.json`. It is a Python replay of the native October member ledgers (Model 4, 100% real ticks), from a fresh $10,000.
Method and guard formulas are in the script docstring.

**Findings:**
- **No guard:** FTMO17 +6.95% (120 trades), E10 +16.49% (68 trades).
- **Prop Ready guard:** FTMO17 -3.16% (29 trades), E10 +5.81% (19 trades).
- **1-Step guard:** FTMO17 +2.86% (31 trades), E10 -1.01% (15 trades).
- **Every version was negative up to Oct 29** (-0.10% to -6.01%). All of the profit came on Oct 30, a sharp gold drop that hit open short targets.
- **End-of-test marks:** some Oct 30 profit is from trades still open when the data ended, closed by the tester at the last price: E10 no guard +6.72%,
  FTMO17 no guard +1.22%.
- **Firm limits on closed balance, no guard:**
  - FTMO17 hit -10.18% on Oct 16 (breaches the 10% max loss) and -3.66% in a day on Oct 2 (breaches the 1-Step 3% daily limit).
  - E10 lost 3.18% on Oct 20 (breaches the 1-Step daily limit) and reached -9.58% (just inside the 2-step max loss).
- **At 1% the guards leave few slots:** each open trade reserves about 1.3%, so the 3% (Prop) or 2.5% (1-Step) daily reserve usually allows only 1-2 open positions.
  Results then depend on which EA fires first, so the guarded numbers are noisy.

**Limits:**
- One month only.
- Guards replayed from closed balance: floating equity, margin and swap are not modelled.
- XAU Trend Progression had 0 October trades.
