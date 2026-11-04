# Edge scan of every bot (2026-11-04)

**Owner request:** "scan all the bots we have and tell what you think is real edge not just luck".
`scan.py` → `SCAN.md` / `SCAN.json`. The rules were declared in the script before computing.

**Data:**
- **Trades:** 5-year native Model 4 streams, 2021-10 → 2026-10, recorded costs. The ORB rows are identical in the Full EA and FTMO17 streams
  (both 0.5R).
- **Not scored (no usable stream):**
  - the 5 news bots: tester news-spike artefacts, about +7R per trade;
  - US30 / US100 hourly: no stop loss;
  - BTC FVG, BTC POC, ETH FVG: no engine specs for crypto.

**Rules:** n ≥ 100; positive in dev / val / OOS; PF ≥ 1.15; best-day PASS; three-way MC (resample ≤ 5%, randomize ≤ 10%); break-even extra
cost ≥ 0.10R.

**Earlier evidence that overrides the in-sample scan:**
- **3 Way Gold:**
  - All three modules were fitted on 2021-26 and lost on the untouched 2019-21 holdout.
  - Module A (930930100, momentum) = a management effect: the random-direction control was equal.
  - Module B (930930101, breakout) beat its random control (3y raw gate PASS).
  - Module C (930930102, turn of month) was the only qualified module, but trades about once a month.
- **XAU Weakness:** native 2019-23 development −28.5% PF 0.75 (`XAU Weakness Market Fill 2026-11-03`), so it is not robust.
- **USDJPY London:** confirmed by today's native 2019-26 split (`USDJPY London MC OOS 2026-11-04`); Monday / Tuesday correctly off.
- **Nasdaq 5M ATR6:** 2019-26 pipeline development PF 1.10, below the 1.15 gate (`Nasdaq 5M Wide Stop Pipeline 2026-11-02`).

**Limit:** everything here is in-sample. Most settings were chosen on this history, so passing is necessary, not sufficient.
