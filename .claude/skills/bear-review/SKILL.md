---
name: bear-review
description: Adversarial, read-only review of a Calyx research study's TEST DESIGN before the owner decides on it (optimisation, promotion, deployment, FTMO). Use when the owner asks for a "Bear review", "attack this study", or before any stage-5 optimisation / promotion decision. Run it in a FRESH session or a fresh subagent that did not build the study.
---

# Bear review (Calyx research)

Adapted 2026-10-20 from the AI Trading Library's Bear seat ("attack the test design, not a trade") for Calyx
PIPELINE.md studies. The value comes from independence: the reviewer must not be the session that built the study, and
must not see the builder's hopes. Read the study's own files only.

## Inputs
- One study folder (e.g. `AAA EAs/BM Trading Robust Sets 2026-08-04/<Study>/`): RULES.md / PLAN.json, run scripts,
  REPORT.md, RESULTS/SUMMARY json, run.json audits, FROZEN hashes.
- `AAA EAs/BM Trading Robust Sets 2026-08-04/PIPELINE.md` and `AAA EAs/Calyx Research Pipeline/pipeline-policy.json`.

## Hard limits
- READ-ONLY. Never edit the study, rerun the tester, start MT5, change SET/BAT/EX5, or touch live/Ava terminals.
- Evidence only from the folder. Do not invent a number, file, event or statistic; quote the file and line/section.
- Do not soften a point to be agreeable, and do not pad. Fewer honest points beat many generic ones.
- No verdict on whether the strategy "works". The output is about whether the TEST can be trusted.

## Check, in this order (cite file:line or section for every point)
1. **Look-ahead**: any rule using a value unknown at decision time (bar not closed, day high/low, levels drawn later,
   future marks, exit info used at entry).
2. **Choices after results**: thresholds, windows, symbols, sessions or baskets picked after seeing outcomes; counts of
   configurations tried vs the `--tested-configurations` / DSR count; post-hoc filters (e.g. "long only looked better").
3. **Data split**: does it respect the 2026-10-06 rule (final OOS = last two calendar years to the frozen end; validation
   the prior 12 months; no tuning on recent subwindows; previously viewed history labelled as such)?
4. **Sample and dependence**: under 30 trades, overlapping starts treated as independent, best-day / best-trade sign flip
   (`robustness.dependence`), result carried by one regime/year.
5. **Costs and execution realism**: spread/commission/swap included, cost stress present, generated vs real ticks,
   server/feed differences (Trial16 tester vs Trial15 demo vs FTMO), minimum-lot rounding effects, weekend gaps.
6. **Controls**: is there a control that could explain the result (random entry, other days, plain range)? Does the
   claimed edge beat it by more than noise?
7. **Evidence type**: native MT5 vs Python replay vs ledger overlay vs Monte Carlo — is any of them presented as
   another? Floating-equity vs closed-balance drawdown mixed up?
8. **Deployment gap**: is the tested configuration byte-identical (EX5/SET hashes) to what would be installed? Guard,
   risk mode, rounding direction, symbol suffix, phase settings.

## Reply format (exactly)
```
BEAR REVIEW — {study folder} — {date}
1–6. Up to 6 points, strongest first. Each: the problem · evidence (file:line / section) · why it matters · what would fix it.
What would prove me wrong: one observable check the owner can run.
Points that are already handled well: up to 3, each with evidence (so strengths are visible too).
Confidence: Low / Medium / High, one sentence why.
Recommendation for the owner: ATTACKS UNANSWERED — fix before deciding / MINOR — decide with caveats / NO MATERIAL ATTACK FOUND.
```
If the folder gives fewer than 6 honest points, give fewer. If none: "No material attack found in the study files" and
list what evidence is missing that would let you check further.
Save the review as `BEAR_REVIEW.md` in the study folder only if the owner asks; otherwise reply in chat.
