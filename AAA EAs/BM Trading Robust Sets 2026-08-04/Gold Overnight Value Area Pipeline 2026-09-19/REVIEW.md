# Adversarial review before handoff

This is a second-pass review by the same research agent, using separately implemented profile calculations, exact native ledger replays and synthetic engine tests—not a claim of an external auditor or live validation.

## Findings that change the interpretation

1. **Recent raw profitability was not representative.** The raw last year returned +22.26%, but the training period lost 13.51%. Its five-year net return was only +9.09% with 28.90% equity drawdown. Small extra trading costs erase that edge.
2. **No finalist passes every frozen gate.** The selected 96-bin / 80% VA / POC-stop / minimum 0.5R / breakeven-at-0.5R candidate is profitable in training and validation, but has only 249 training trades against the predeclared minimum of 300. The alternate 1.5R target candidate breaches the training drawdown gate. Gates were not revised after results.
3. **A lower win rate can coexist with better performance.** The selected five-year candidate returns +52.92%, PF 1.44, DD 9.78%, but net wins are only 43.31%. Net loss counts include tiny cost/slippage losses near breakeven. They must not be relabeled as wins to improve marketing statistics.
4. **Tick evidence is incomplete.** The native six-month report has 100% real ticks, the year 71%, three years 23%, five years 14%. Real ticks start 2026-01-01; earlier execution is generated. The latest year's raw result was already inspected before the research, so it is not an untouched holdout.
5. **Specific historical coverage gap.** June 20, 2025 M1 history ends at 07:17 UTC, before NY open. Repeated broker API queries return the same M1/M5 data as the frozen cache. This is recorded as unresolved missing-session/closure evidence, not silently filled or claimed complete.
6. **Risk percentages are targets, not caps.** Upward lot-step and minimum-lot sizing is retained from the existing raw specification. The 1% native study reaches 1.917% actual initial stop risk; the 0.5% version reaches 1.120%. Slippage and market gaps can add further realized loss. Calling the half-risk setting a strict safe mode would be incorrect.
7. **Time exit is not guaranteed.** The candidate's 15:30 NY exit lowers five-year late exits from 78 to 4 and overnight holdings from 5 to 0. It still has a maximum 151-minute exit delay. Broker historical holidays are not fully represented by today's weekly session schedule.
8. **Stress outputs have different meanings.** Native 500/1000 ms delay tests replay execution; added dollar/ounce and commission stresses are fixed-ledger cash overlays. Bootstrap drawdowns are closed-balance only and cannot be compared as if they were native floating-equity drawdowns or live prop-firm passing odds.
9. **The stronger cost stress nearly removes the candidate's edge.** With an additional $0.50 per ounce round trip plus 50% extra commission, its fixed-ledger five-year return falls to +3.16% and closed-balance drawdown rises to 30.38%. It is not insensitive to execution costs.
10. **Several promising-looking results remain selection-biased.** The family was defined after prior raw inspection; Stage-A/Stage-B training search tests 195 unique candidates and validation chooses among three finalists. The separate chronological walk-forward bar test is mixed. A forward demo interval is still required before a live claim.
11. **Value-area sensitivity is not a broad plateau.** Changing only the selected 80% value area to 70% gives -0.94%, PF 0.97 and DD 12.62% in native validation, versus +8.95%, PF 1.53 and DD 4.48% at 80%. Changing 96 bins to 64 bins remains positive (+11.58%, PF 1.61), but that does not remove the value-area threshold sensitivity. These checks are not used to select another winner after evaluation.

## Defects avoided or corrected during the work

- Exact raw default replay agrees with all 200 prior native trades, including fees and initial levels.
- A synthetic ambiguous-minute case confirms the bar screen checks stop loss before TP; an invalid first signal consumes the day; short exits use ask prices.
- Weekly resampling uses the same 261-week calendar grid for both ledgers, including the candidate's initially empty weeks, rather than inflating its sparse trade frequency.
- A concurrent external Git operation introduced website conflict markers. The research parser was isolated by copying only unchanged pure parsing functions, with exact native ledger replay proof. No website conflicts were edited and no live installation was attempted.
- Fixed-R target finalists are disclosed as changing entry eligibility, not just exit behavior: a fixed target can accept signals already beyond the overnight extreme.

## Review gate

Keep the candidate as a research version. The 0.5% requested-risk test is a useful forward-demo candidate, not a passed or guaranteed-safe deployment. Before live use, review the evidence gaps, lot sizing policy and historical/forward holiday handling. Do not silently install it based on headline return.

S&P 500 pipelines remain unstarted pending user review: Nasdaq 5M Momentum, H1 ORB 13UTC, Month End Flow, Sell Nasdaq Dynamic, Nasdaq Overnight. No live BAT, portfolio or website update is authorized by this completed research stage.
