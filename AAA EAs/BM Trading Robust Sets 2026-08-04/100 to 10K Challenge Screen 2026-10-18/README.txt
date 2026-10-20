$100 TO $10,000 CHALLENGE SCREEN — RESEARCH ONLY

Purpose
Compare the fastest existing single EA and combinations within a finite frozen
historical search. The $100-to-$10,000 goal is a 100x capital target. This study
cannot identify a guaranteed or universally best way to achieve it.

Read Results.html for the locked development choices, later evaluation, all
tested development configurations, every evaluation start and detailed saved
paths. The report reads saved evidence only; it does not search, simulate, trade
or change the live website.

Selection / evaluation
Development: 2021-10-06 through 2024-10-06 exclusive.
Evaluation:  2024-10-06 through 2026-10-06 exclusive.
Fresh starts each Monday with 365 full calendar days within the partition.
The selected EA/configurations and risk are locked before evaluation outcomes.
Historical starts overlap and are dependent. These dates/strategies had already
been researched; the later split is not genuinely untouched out-of-sample data.

Important interpretation
- Historical target hit fraction is NOT a future success probability.
- Median completion time among hits excludes failures and timeouts. All-start
  median is unavailable unless at least half the starts reach the target.
- Fastest-observed paths are retrospective lottery diagnostics, not deployment
  recommendations or typical experience.
- Sizing compounds only owned CLOSED cash. Respect broker minimum/step/maximum
  lots, skip below minimum, reserve original stop risk and conservative margin.
- $20 is an 80% initial-capital-loss RESEARCH floor, not a measured broker
  stopout, guaranteed maximum loss or protection against total loss.
- DD is closed-cash drawdown, not floating equity drawdown. Margin is admission
  bookkeeping using snapshots, not historical HMR or a liquidation engine.
- Recorded native fills, fees, swaps and genuine partial exits are preserved.
  Larger resized fills assume linear execution. Stress is only a sensitivity.
- Native tests report 15% real ticks; earlier history uses generated/mixed ticks.
- ETH has no current quote/margin receipt: cached margin and a September 2026
  bar-spread proxy are used. Nasdaq overnight lacks entries before June 2023.
- Seven of the 37 current EAs are excluded (two no-stop hourly EAs and five news
  EAs). The eligible universe includes 30 current EAs plus Nasdaq DI-OFF variant;
  DI ON/OFF cannot coexist within one basket.
- Native invalid-stop log diagnostics are preserved and are not converted into
  filled trades. Log-hit counts are not unique rejected-order counts.
- A publisher 1ms ordering epsilon is a sorting convention, not measured latency.

Verification
report.py can show independent PASS only if VERIFICATION.json has status PASS
and matching results_sha256, selection_sha256 and frozen_sha256 bindings.
Missing/stale receipts display PENDING or NOT VERIFIED. The renderer also rejects
missing evaluation costs/starts, stale frozen files and inconsistent selections.

Supplemental retrospective scoreboard
After the original locked single/pair failed the later evaluation, the same 720
configurations were ranked descriptively on that later period. RECENT-PLAN.json
explicitly declares this later-period ranking AFTER original outcomes were seen.
No search-space/guard/risk expansion is allowed. This is NOT new validation:
its winning configurations are selected using the same outcomes being reported.
Do not replace the original failure with a new "out-of-sample winner" claim.
RECENT.json keeps the base-scoreboard ranking, primary/fastest-observed roles,
same-period cost stress, all starts and illustrative paths separately. Original
SELECTION.json, RESULTS.json and FROZEN.json are not modified by that supplement.
The report gives the supplement its own receipt status; PASS requires matching
recent_sha256, recent_frozen_sha256 and original_results_sha256 bindings in
RECENT-VERIFICATION.json. Arithmetic PASS does not remove data-mining bias.

Final same-period risk sensitivity
RISK-SENSITIVITY.json shows every originally declared risk percentage for the
two retrospectively selected primary EA families, base and stress. This is not
a new independent validation sample. Its family choice uses those same dates;
selecting a risk from the table would add another retrospective selection step.
Low-risk zero-trade outcomes caused by the broker minimum lot are not evidence
of a profitable low-risk strategy. RISK-VERIFICATION.json is separately bound to
risk_sha256, protocol_sha256 and recent_sha256 before displaying PASS.

No live trades, EA/BAT/preset changes, portfolio deployment, website changes,
automatic commit or push are part of this research.
