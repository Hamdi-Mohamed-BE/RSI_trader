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
