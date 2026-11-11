# Best 1-Step (BEST1STEP-20261111)

Owner 2026-11-11. Core 9 + Overnight Bias ORB + Gold Band Wave = 11 EAs (Nasdaq 5M REPLACE DI OFF, USDJPY London DI ON, 3 Way Gold breakout only,
Sell Nasdaq 15min, EMA3, ORB VP Volume Confirmed, XAU Squeeze, US100 Selective ORB V3 0.5R, XAU RSI VWAP, Overnight Bias ORB, Gold Band Wave).

- `Best 1-Step - FTMO 1-Step guard.bat` -> `1-Step/` (ftmo 1_step guard, state key B1O, default 0.5% risk = tested best).
- `Best 1-Step - no guard.bat` -> `../Packages/Best1Step` (no guard; the already compiled Core 9 / P4 no-guard EX5s).
- `build.py` regenerates both (`python build.py installer` = installer only).

Evidence: `../../Best 1-Step Search 2026-11-11/REPORT.md`. FTMO 1-Step $100k MC: guard 0.5% pass within 60 / 90 / 180 days 35 / 57 / 78%, 0% breach;
no guard 0.5% 46 / 68 / 90%, 7.4% breach. 60% within 60 days is NOT reached. In-sample, selection-biased.

Checks 2026-11-11: 11 guarded wrappers 0 errors / 0 warnings; both BATs -ValidateOnly PASS; source packages unchanged (asserted).
Not done: native parity of the new guarded wrappers (guard refuses the tester; members are the same sources as Core 9 / P4, whose parity passed), any install, push.
Sell Nasdaq (guarded) holds its stop in the EA and sells at market. Gold Band Wave / EMA3 use H4 bars: non-UTC brokers (FTMO UTC+2/+3) give different bars.

## 2026-11-11 changes
- Sell Nasdaq 15min removed (owner). UK100 Monday dip added (owner): FTSE Three Setup Raw 2026-10-27 S2, unchanged rules, UK100 H1; asserted edits only for the live broker
  clock, the unused governor input and (no guard) RiskSupport sizing. Installers map UK100 / UK100.cash / FTSE100 / UKX / GBR100. 11 EAs in both BATs, -ValidateOnly PASS.
- Parity: no-guard UK100 wrapper = raw EA, 183 / 183 identical trades (native Model 4, 2019-08 -> 2026-09-28; UK100 Monday Dip QuantLab Check 2026-11-11/PARITY_B1.json).
  The guarded wrapper has no native run (the guard refuses the tester).
- FTMO simulation with the Monday dip (Best 1-Step UK100 Monday 2026-11-11): 1-Step guard 0.5% pass <=60/90/180 d 30/53/81%, median 74 d; funded guard $2,669/month.
- LATER 2026-11-11 (owner: "update the profile now with the new approved EAs"): Best 1-Step = 7 EAs: Nasdaq 5M (REPLACE, DI OFF), Overnight Bias ORB, EMA3, Gold Band Wave,
  ORB VP Volume Confirmed, XAU RSI VWAP, UK100 Monday dip. Removed USDJPY London, 3 Way Gold, XAU Squeeze, US100 Selective ORB V3. Chosen on the last two months
  (hindsight selection); over all years 2021-26 the 7 made +258R PF 1.22 vs the 11's +419R PF 1.29 (Best 1-Step Seven 2026-11-11). Both BATs pass -UsdJpyDIFilter OFF; -ValidateOnly PASS.
- FINAL 2026-11-11 (owner: "keep all 11 ... just remove sell nasdaq" + "make the bat ask me one by one"): the package holds all 11 EAs (Core 9 without Sell Nasdaq = 8,
  + Overnight Bias ORB, Gold Band Wave, UK100 Monday dip). Both installers ask for EACH EA (Enter = install; Select-CalyxEntries, `_00 Live profiles/Calyx-SelectEAs.ps1`,
  dot-sourced via Calyx-InstallChoices.ps1, inline in the no-guard installer); `-SkipEAs slug1,slug2` skips without asking. Integrity checks cover all 11; symbols, charts and
  load checks only the chosen ones (a broker without UK100 works if UK100 is skipped). The 7-EA builder is kept as build.seven.py (not used). A smaller set is untested.

