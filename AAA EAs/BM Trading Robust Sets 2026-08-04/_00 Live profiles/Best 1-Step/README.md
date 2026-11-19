# Best 1-Step (BEST1STEP-20261118)

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


## 2026-11-17 change (owner: "keep EMA3 and RSI VWAP, remove Gold Band Wave and XAU Squeeze Momentum")
- Package = 9 EAs: Nasdaq 5M (REPLACE, DI OFF), USDJPY London (DI ON), 3 Way Gold breakout, EMA3, US100 Selective ORB V3 (0.5R), XAU RSI VWAP,
  ORB VP Volume Confirmed, Overnight Bias ORB, UK100 Monday dip. Version BEST1STEP-20261117. Builder backup: build.before-nine.py.
- Rebuilt with build.py (9 guarded wrappers 0/0 compiled, no-guard package copied + UK100 wrapper compiled), weekend-flat helper re-added
  (Calyx Weekend Flat/wire_weekendflat.py patch_b), both BATs -ValidateOnly PASS. Still asks for each EA. Not installed on any terminal; not pushed.
- The no-opposite-trade rule (needed at FundingPips) is NOT in these EAs.
- Evidence: Multi Firm Funded 2026-11-17 (Addendum 3). Gold EAs picked on the last 12 months (hindsight).

## 2026-11-17 no-opposite rule (owner: "build the no opposite trade rule into the EAs and add to profile along side with weekend hold")
- Both installers ask: "No opposite trades on the same symbol? ON or OFF [OFF]" (-NoOpposite ON|OFF), next to the weekend-flat question.
  ON = no new entry / pending order against an open opposite position on the same symbol (FundingPips hedging rule); OFF = tested behaviour.
- No guard: all 9 wrappers recompiled from their package sources with the Calyx No Opposite shim (`../Calyx No Opposite/`). They are now named
  `Calyx Best1Step - <ea>.ex5`, and Package.json keeps the tested EX5 name + sha per entry. Guarded: the check runs inside the FTMO 1-Step guard lock.
- Every set has InpCalyxNoOpposite=false. 18 EAs compiled 0/0; weekend-flat helper re-added; both BATs -ValidateOnly PASS.
  The native harness passed 11/11 checks with the rule ON and 11/11 with it OFF. Wrapper parity: `../Calyx No Opposite/parity/PARITY.json`.
- Builder backup before this change: build.before-noopposite.py.

## 2026-11-18 "best perfect profile" (owner: "update the best profile to respect this and respect all the trading rules check inbox responses")
- 10 EAs: the 9 above + **Asia Breakout** (AAA Final engine, XAUUSD H1, market entries only, Full EA inputs, magic 290729). Builder backup: build.before-ten.py.
- **Nasdaq 5M at 0.75x** the chosen risk (`-NasdaqRiskFactor`, default 0.75, range (0, 1]). Guarded: new guard input `FTMOEntryRiskFactor` (Nasdaq chart only) scales the
  per-entry cap; total / symbol caps unchanged. No guard: InpPortfolioPercent (or the fixed USD) x0.75 on the Nasdaq chart.
- **News guard** (`../Calyx News Guard/`): question `OFF / 2 / 5` (`-NewsGuard`); guarded default Funded = 2, Challenge = OFF; no guard default 5. ON adds the helper
  chart, downloads the calendar and sets `InpCalyxNewsBlock=true` on every EA (entries refused while the guard blocks the symbol).
- Firm rules behind it (email replies): FTMO funded Standard 2 min news + flat before weekends (weekend-flat ON), challenges exempt; The5ers 2 min; FundingPips 5 min
  soft breach + no hedging (no-opposite ON); FTMO $400k per client AND per strategy; no copying the same trades into opposite directions across accounts.
- Checks: 20 wrappers compiled 0/0; weekend flat re-added; both BATs -ValidateOnly PASS; installer sandbox test 25/25 (news question, Nasdaq 0.375% / $75 at
  0.5% / $100, Asia inputs, chart writer, calendar download to a redirected APPDATA, guarded per-chart inputs, guard text). Native parity: `parity/PARITY.json`.
- Evidence for the list (Best 1-Step Add Gold 2026-11-18/FINAL_PICK.json, no-guard multi-firm engine, in-sample, hindsight-selected): FTMO 1-Step 0.75% first-try 93.1%,
  median 59 d; FTMO 2-Step / The5ers 0.75% 95.4%, 89 d; FundingPips Standard 0.75% 96.2%, 79 d. Weekend / holiday flat was applied;
  news closes were NOT simulated, so the real effect of the news guard is not measured. Not installed; not pushed.

## 2026-11-18 all-in-one setup (owner: "one script file that will apply all these extra stuff")
`Setup Best 1-Step (all in one).bat` (-> Setup-Best1Step.ps1): pick the account type 1-7 (FTMO 1-Step challenge / funded, FTMO 2-Step challenge / funded,
The5ers, FundingPips, custom). It downloads the news calendar, creates / refreshes the daily task "Calyx News Calendar" (06:00, asked), then runs the right
installer with risk / weekend flat / no-opposite / news guard / Nasdaq / DI / caps answers filled in. Still asked: each EA (Enter = install) and the installer's
typed confirmation. `-Type N -ValidateOnly` PASS for types 1-6. Not run on a terminal.

## 2026-11-19 Nasdaq 5M factor is now ASKED (owner: "make it ask me what to use for it")
Both installers ask: 1 = 0.75x (recommended, Enter), 2 = 1.00x (full), 3 = 0.50x, or a typed factor 0.05-1. `-NasdaqRiskFactor <f>` skips the question;
-ValidateOnly / no-prompt runs use 0.75. The all-in-one setup no longer forces 0.75 (the installer asks). Builder backup build.before-nasdaqask.py,
setup backup Setup-Best1Step.before-nasdaqask.ps1. Rebuilt (20 wrappers 0/0), weekend flat re-added, both BATs + setup types 1-6 -ValidateOnly PASS,
question tested with typed answers on both installers (Enter/1/2/3/0.6/invalid/no-prompt/param) PASS. Not installed; not pushed.

## 2026-11-20 `Ready for FTMO.bat` (owner: one file, 0.75% risk, DI off, all FTMO rules, "just run it on the account")
`Ready for FTMO.bat` -> `Ready-For-FTMO.ps1` -> the FTMO 1-Step guarded installer, non-interactive, all 10 EAs. Fixed: risk 0.75% (challenge), Nasdaq 5M x0.75,
Nasdaq DI OFF, USDJPY DI ON (tested), Nasdaq stop ATR6, caps 4.5x / 3x, weekend flat ON, no-opposite OFF, news guard Challenge OFF / Funded +-2 min, news
calendar now + daily task "Calyx News Calendar" (refreshed silently; a funded install stops if the calendar download fails). Asks: Challenge or Funded;
on Funded also the risk per trade (Enter = 0.5%, 0.1-1.5; `-FundedRisk x` skips it); then the installer's typed confirmation. -ValidateOnly PASS for
Challenge / Funded / -FundedRisk 0.6; risk question tested (Enter, 0.75, 0.3, rejects 2 / abc, param skip, challenge no question). Not installed; not pushed.
