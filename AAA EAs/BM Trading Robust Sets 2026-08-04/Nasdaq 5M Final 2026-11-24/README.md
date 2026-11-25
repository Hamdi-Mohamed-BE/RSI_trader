# Nasdaq 5M: final code, build and SETs (2026-11-24)

These are copies only, made for reading. The originals stay where they are. Nothing was recompiled, and nothing was installed or changed on a terminal.

## Files

| File | SHA-256 (first 12) | What it is |
|---|---|---|
| `Nasdaq 5M DI Wide ATR EA.mq5` | 80aca5f5103f | The production strategy source, 571 lines, carry mode REPLACE. |
| `SafeRegimeFilter.mqh`, `DynamicTrailingSessionFilter.mqh` | 83e11a48b838, 54498db20170 | Includes. Both filters are OFF in every SET. |
| `Nasdaq 5M DI Wide ATR EA.ex5` | 2488443f62a8 | The production build. Compile log: 0 errors, 0 warnings. |
| `Nasdaq 5M - standalone production (DI ON, 1pct).set` | 35783fc7a48d | The canonical SET: ATR6 stop, ATR6 trail, no TP. |
| `Nasdaq 5M - Best 1-Step no guard.set` | 9341ca832b4c | The SET that `Best 1-Step - no guard.bat` installs. |
| `Nasdaq 5M - Best 1-Step FTMO guard (Ready for FTMO).set` | a5f57326d1b4 | The SET for the guarded build. The installer rewrites the FTMO* lines and the risk lines. |

**Compiling.** The `.mq5` includes `..\..\_Shared\CalyxAdaptivePortfolio.mqh`. Compile it from its original folder: `Nasdaq 5M Carry Replace Deployment 2026-11-09/EA/`.

## The builds that profiles install

The profiles do not install this strategy EX5 directly. They install a wrapper EX5 that includes a copy of the same strategy source. That copy is byte-identical to the production source except for the 4 `#include` lines.

- **No guard:** `_00 Live profiles/Packages/Best1Step/Experts/Calyx Best1Step - nasdaq-5m-candle-momentum.ex5` (29f9c7a1280a, 0/0).
  - It adds RiskSupport (% or fixed-USD sizing) and the Calyx No Opposite shim.
- **FTMO 1-Step guard (Ready for FTMO):** `_00 Live profiles/Best 1-Step/1-Step/EAs/B1O-nasdaq-5m-candle-momentum.ex5` (b5488ff42fe6, 0/0).
  - It adds the FTMO 1-Step guard: risk cap, daily and max loss, best-day rule, news block and no-opposite rule.

## Rules (from the code)

1. **Signal.**
   - It checks the M5 bar that closes at 09:35 New York, which is the 09:30 bar.
   - A close above EMA12 is a long; a close below is a short.
   - It takes one trade per New York day.
2. **DI filter (optional).**
   - It needs DI+ > DI- (period 14) for a long, and the reverse for a short.
   - ON in the standalone production SET. OFF in Best 1-Step (the installer asks).
3. **Stop.**
   - Initial stop = ATR(14) × 6 (`InpStopMode=0`).
   - The old 0.60% price stop is `InpStopMode=1` (the installer asks).
4. **No take-profit.**
   - The stop trails at ATR × 6 once the trade is +1R.
   - No break-even, no time exit, no session-end close.
   - It holds overnight. The weekend-flat helper closes it before weekends when that option is ON.
5. **Carry (REPLACE, `InpCarryMode=2`).**
   - If yesterday's trade is still open at 09:35 and today's signal passes, it closes the old trade and enters today's.
6. **Risk.**
   - Strategy risk % of equity, hard-capped at 1% in code (`MathMin(InpRiskPercent,1.00)`, line 113).
   - The no-guard wrapper sizes from `InpPortfolioPercent` or fixed USD.
   - The guarded wrapper cuts each entry to the guard's budget. On the Nasdaq chart that budget is × the Nasdaq factor (0.75 recommended).

## Evidence

- **Native parity**, deployed EX5 vs tested REPLACE: 1,882 / 1,882 trades identical with DI OFF, 1,449 / 1,449 with DI ON (`VERIFY_PRODUCTION.json`).
- **Pipeline status:** this is the owner's choice and is NOT pipeline-qualified.
  - ATR6 stop: development PF 1.10 is below the 1.15 gate.
  - Under the frozen rule, REPLACE did not qualify; the owner deployed it.
