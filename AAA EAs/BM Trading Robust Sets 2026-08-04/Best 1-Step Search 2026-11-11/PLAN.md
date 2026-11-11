# Best 1-Step Search 2026-11-11 (PLAN, frozen before any result of this study)

Owner request (2026-11-11): "nasdaq 5m and overnight bias orb and gold band wave and EMA3 are must have so what is the best
portfolio for 1 step for now? ... create guard and no guard bat files ... aim for 60%+ pass rate within 2 months".

Method = `Merge 1Step 60d Search 2026-11-10/search.py` unchanged (frozen engines from Prop Portfolio Selection 2026-11-03,
FTMO 1-Step $100k, weekday starts, 180-day horizon, streams 2021-10-07 -> 2026-10-06, 13-EA pool, Nasdaq 5M = REPLACE DI OFF).
Only change: FORCED = Nasdaq 5M, Overnight Bias ORB, Gold Band Wave, EMA3 (never dropped).

- Models: GUARD = the ftmo 1_step guard (f1_profile.Profile); NOGUARD = FTMO 1-Step firm rules only.
- Objective: development (2021-10-07 -> 2023-10-06) pass within 60 days; feasibility dev breach <= 5%.
- Backward elimination from all 13 at 0.5 / 0.75 / 1.0 / 1.25 % (Addenda 1-2 of the source study apply), one add-back pass.
- Pick: best validation (2023-10-06 -> 2024-10-06) pass_60 among the per-risk forced winners with val breach <= 5%, per model.
- OOS 2024-10 -> 2026-10 (previously viewed, retrospective) and MC 2,000 paths reported once for the picks + references
  (Core 9, P4, Core 9 + P4, all 13; unforced winners copied from the source study).
- Dev results already computed by the source study for identical (members, risk) keys are reused from its cache (copied).
- 60% within 60 days is the owner's aim, not a selection rule: if no pick reaches it, report the gap; do not tune further.

Known limits: in-sample selection (the pool EAs were themselves chosen on these years); guards have no native tester run;
Vault Break is in the pool although it failed its own Monte Carlo and validation year (owner-approved research EA).

## Addendum A (2026-11-11, after the dev search, BEFORE any validation / OOS / MC result)
NOGUARD forced winners at 0.75 / 1.0 / 1.25 % stayed infeasible in development (dev breach > 5%: best dev scores -0.50, -0.70, -0.73 = -breach).
The source study's final() only checked validation breach. The pick now also requires dev breach <= 5% (the declared feasibility rule).
Dev winners (pass within 60 d, dev): GUARD 0.5% 10 EAs 21.1%; 0.75% 11 EAs 26.5%; 1.0% 12 EAs 24.0%; 1.25% 12 EAs 24.4%; NOGUARD 0.5% 10 EAs 25.7%.
