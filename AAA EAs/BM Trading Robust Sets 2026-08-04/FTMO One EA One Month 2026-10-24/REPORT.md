# One EA, one month on FTMO $100k 2-step — REPORT (2026-10-24)

**Question (owner):** is it possible to pass in one month with one EA? Choose the best options and show the data.

## Method
- **Engine:** Python/numba replay of the Full EA ledger stream (36 EAs).
- **Sizing:** fixed 1–4% risk per trade, fractional lots, recorded costs.
- **FTMO rules:**
  - Phase 1 +10%, then phase 2 +5% on a fresh balance from the next Prague midnight.
  - At least 4 trading days per phase.
  - 5% daily and 10% max loss, with every open position marked at its full stop.
- **Selection:** ranked on 2021-10 → 2023-10 (development) only. Validation 2023-10 → 2024-10 and OOS 2024-10 → 2026-10
  are shown afterwards. Tables are in `RESULTS.md`; raw output is in `RESULTS.json`.

## Answer: possible, but only as a lottery ticket. The best single-EA odds are about 1 in 7 to 1 in 9.

| Option | Risk | Pass both phases ≤30 d (all MC / history) | Breach ≤30 d | By window (dev / val / OOS) | Phase 1 ≤30 d | Median days when it passes | Trades / month |
|---|---:|---:|---:|---|---:|---:|---:|
| **LTA Volume Profile** (most consistent across windows) | 2% | 13.5% / 13.3% | 57–59% | 9.1% / 13.1% / 19.1% | 35% | 24 | 19.2 |
| **Nasdaq 5M Candle Momentum** (dev #1) | 2% | 11.1% / 13.7% | 32–36% | 14.1% / **0.0%** / 15.3% | 33% | 33 | 15.3 |
| Nasdaq 5M Candle Momentum | 3% | 11.0% / 13.7% | 78–80% | 13.4% / 2.2% / 17.1% | 30% | 22 | 15.3 |
| XAU Slow Trend | 2% | 8.2% / 8.2% | 23% | – | – | – | 17.0 |
| LTA Volume Profile, safer | 1% | 5.0% / 5.5% | ~10% | 5.6% / 7.6% / 4.6% | 19% | 42 | 19.2 |

## Reading it
- **Why it is so hard:** +15% in 30 days needs about 15–20 trades with a real edge at 2–3% risk. Only EAs trading 15+
  times a month can even try. Every ORB and every low-frequency EA scored 0%.
- **Higher risk does not raise the odds; it raises the breaches.** At 3–4% the pass rate stays around 11% or falls,
  while breaches go to 80–98%.
- **Cost per success:** at an 11–14% pass rate, one FTMO-fee attempt per month means about 7–9 fees per funded account
  on average. The multi-EA guarded portfolios need about 1.3–1.8 fees, but take 3–6 months.
- **Regime risk:** Nasdaq 5M at 2% passed 0% in the 2023–24 validation year. LTA Volume Profile held up in every window
  but breaches more than half the time.

## Limits
- **Production builds:** the production Nasdaq 5M EA caps risk at 1%, so 2–3% needs a separate research build (none was
  built). Other EAs' caps should be checked before any attempt.
- **In-sample:** the EAs were chosen on this history. Ticks before 2026 are generated. Closed-ledger replay, not a native
  account test. Breaches are checked on stop-marked equity, not real floating equity.
- **Not a forecast and not advice.** Check the current FTMO rules.
