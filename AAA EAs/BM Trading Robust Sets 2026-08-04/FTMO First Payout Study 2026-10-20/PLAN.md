# FTMO First Payout Study 2026-10-20 — plan (written before any result)

Question (owner): on a $10,000 account, what is a realistic first payout value and how many days does it take?

## Portfolio (unchanged, nothing tuned)
Built `_00 Live profiles/Best Prop Portfolio 2026-10-20` package model, exactly as in
`Best Prop Portfolio Retest 2026-10-20`: nine EAs, per-entry cap $100 (1%), total open risk $450, per symbol $300,
$300 daily reserve/latch, $9,200 equity entry buffer, 7 entries / 3 losses per Prague day, 80% margin cap.
Nasdaq 5M DI OFF = package default (primary). DI ON shown for comparison only.

## FTMO payout rules used (ftmo.com FAQ, checked 2026-10-20; store rules file checked 2026-09-29)
- First reward can be requested on/after the 14th day after the first trade on the FTMO Account.
  Model: first-trade Prague date + 14 calendar days, 00:00 Prague (conservative by up to one day).
- All positions and pending orders must be closed at the request. Model: request only at a moment the account is flat
  (after a close, or at a Prague midnight).
- Split 80% (2-Step). Challenge fee (EUR 155 for 10k, store rules file) refunded with the first reward.
- Minimum closed profit $20 (bank/card) — the "earliest" policy.
- Review 1–2 business days + payment 1–2 business days after approval: NOT modelled; add 2–4 business days.
- Funded account limits = same 5% daily ($500) and 10% maximum ($9,000) loss as the challenge.

## Payout policies (predeclared; reported side by side, none selected)
Request at the FIRST flat moment after eligibility when closed profit >= threshold:
$20 (earliest allowed), $250, $500, $1,000. Payout = 80% x closed profit. A breach before the request = $0 and the
account is lost. No request within 180 days = $0 for this horizon (reported separately: still trading vs stuck below
the $9,200 entry buffer with no entry for the final 30 days).

## Evidence (each labelled; different evidence types are not mixed)
A. Funded phase only, historical sequential replay: every weekday funded start, 180-day horizon inside the window.
   Windows from `Calyx Research Pipeline/data_split.py` on 2021-10-07 -> 2026-10-06:
   development 2021-10-07 -> 2023-10-06, validation -> 2024-10-06, OOS -> 2026-10-06, plus all history.
   The package was chosen after seeing all of this history (see FTMO Best Portfolio Summary) — nothing here is untouched.
B. Funded phase only, block-bootstrap Monte Carlo: same scheme and seed as the retest (4-week Monday-aligned blocks,
   7 blocks, 2,000 paths, seed 20261020) over the 5-year pool.
C. End to end (challenge start -> both phases -> FTMO access illustration -> funded -> first request):
   historical, every weekday challenge start whose 180-day challenge + 7-day access + 180-day funded chain fits in
   the data (starts through 2025-09-27), labelled by start window; plus Monte Carlo on 14-block (392-day) paths,
   2,000 paths, seed 20261021.
Costs: recorded Exness and fixed-cost stress. Handover (end to end): next Prague midnight (base) and two business days
(stress).

## Gates
- Parity: the funded model with payout tracking must reproduce the retest's continuous OOS results (trades, net,
  ending balance) exactly for all four DI x cost cases, and the base OOS challenge summary.
- Inputs/engines hashed and frozen before the run.

Every table shows trades, trades/month and trades/day. Backtest payouts are not a forecast; costs, execution,
FTMO review and the stall at the $9,200 buffer can differ live.

## Addendum (owner request, 2026-10-20, after the first 10k results were printed): account sizes
Sizes 20k (asked; FTMO does not sell 20k — no fee or official rules), 25k, 50k, 100k (FTMO sizes; fees EUR 250 / 345 /
540 from the store rules file), plus 10k re-run through the same scaled code as a parity gate (must reproduce the
10k RESULTS.json exactly). Every guard/FTMO limit scales with the reference balance exactly as CalyxFTMOGuard.mqh
does (1% entry cap, 4.5% total, 3% symbol, 3% daily reserve, 92% buffer, 0.05% per-position reserve, 5%/10% FTMO
limits, 10%/5% targets); the EA request stays 1% of equity. Only lot step / minimum / maximum stay fixed, which is the
real size effect. Payout policies: $20 absolute minimum (earliest) and 2.5% / 5% / 10% of the account (the 10k
$250/$500/$1,000 rows). DI OFF only (the installed default). Means are reported next to medians. Nothing tuned.

## Addendum 2 (owner question, 2026-10-20): long-run income on one funded 100k account, before it ends
Finding before any run: as built, CalyxFTMOGuard FTMOLedger fails closed on ANY balance operation after the frozen
start time ("Any funding/withdrawal/adjustment after deployment invalidates the frozen capital baseline"), so after the
first FTMO reward no new entry is admitted; reinstalling keeps the saved state file (same login) and stays blocked.
FTMO does not document 2-Step post-reward handling (same account reduced vs new account issued).
Model therefore ASSUMES the owner re-baselines the guard after every reward (new account: re-run installer; same
account: delete the Calyx-BestProp9 state file, then re-run) and the account restarts at the initial 100k.
Rules: first request >= 14 days after first trade, later requests >= 14 days after the previous request, at the first
flat moment with closed profit >= policy threshold; the full profit is withdrawn (balance back to 100k, withdrawal not
counted as a daily loss); trader receives 80%. Fee refund EUR 540 with the first reward, not added. Scaling plan
(90% split, larger account) not modelled. Policies: $20 minimum (default, every cycle) and 2% ($2,000) minimum.
End of account: FTMO breach (equity <= 90k or daily loss >= 5k) or FROZEN (no entry for 30 consecutive days with
the 92% entry buffer rejecting entries; end date = last entry). Frozen is not an FTMO breach; it is the end of bot
income without manual intervention. Evidence: historical 12-month horizon, every weekday start 2021-10-07 ->
2025-10-06 (in-sample, labelled by start window), and Monte Carlo 36 months (39 x 4-week blocks, 2,000 paths, seed
20261022). Costs: recorded and fixed-cost stress. DI OFF, size 100k (k = 10). Gates: payouts disabled at k = 1 must
reproduce the retest continuous OOS exactly; every run must satisfy withdrawn profit + (balance - 100k) = sum of trade
nets (+/- rounding). Nothing tuned.

## Addendum 3 (owner question, 2026-10-20): lower risk after getting funded — $100k income until it ends
Predeclared variants (all reported; none selected here):
- GUARD-EXACT sizing: CalyxFTMOGuard FTMOAllocationBudget = min(1% of reference, R% of CURRENT equity), volume =
  floor(min(EA request, budget / unit risk)). (Earlier model kept the EA's rounded-UP request when equity < reference,
  up to one lot step larger; shown as LEGACY 1.00 for parity with income.py.)
- SET 1.00 / 0.75 / 0.50 / 0.25: installer "risk per trade" input R in Funded phase; guard caps unchanged (1% entry
  cap, 4.5% total, 3% symbol, 3% daily reserve, 92% buffer). No code change needed.
- CAPS 0.50: guard code change — entry cap 0.5%, total 2.25%, symbol 1.5% (the Prop Ready guard levels), R = 0.5.
Same rules as addendum 2: $20 minimum reward every 14 days, full profit withdrawn, guard re-baselined after each
reward, end = breach or freeze (30 days without entry while the 92% buffer rejects). 100k, DI OFF, recorded + stress
costs, history 12-month horizon (windows by start) + Monte Carlo 36 months (same paths, seed 20261022).
Gate: LEGACY 1.00 must reproduce INCOME-<cost>-20.json exactly. Nothing tuned; choosing a level afterwards is an
owner decision on in-sample evidence, not validated selection.
