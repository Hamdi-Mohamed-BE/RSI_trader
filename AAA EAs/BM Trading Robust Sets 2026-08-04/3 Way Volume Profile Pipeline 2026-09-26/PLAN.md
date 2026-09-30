# 3 Way Volume Profile: optimization qualification

Frozen 2026-09-26 before new results. Research only; no live terminal, website, installer, BAT or Git changes.

## Authorized sequence

1. BTC value-area reversal; XAU value-area breakout; USDJPY combined, with USDJPY breakout as comparator.
2. Reproduce the XAU breakout one-year native result with all new switches off.
3. Run unchanged raw settings on 2023-09-26 and 2021-09-26 through 2026-09-26 (exclusive).
4. Qualify only positive raw versions with PF >= 1.15 and >= 30 trades in BOTH windows, beating a predeclared no-signal reference.
5. Only qualifying versions proceed to the full staged parameter search in the parent PIPELINE.md. A failed or near-miss gate is reported, not silently bypassed.

## Fixed test assumptions

Original raw entry and exit rules, M15, 1% equity risk, 2R target, no adaptive sizing, one position at a time. Broker lot rounding remains as in the raw EA: upward, so actual risk can exceed 1%. Broker binding is inherited from the original study's saved isolated-tester config, never the live account. No account credentials are copied into this plan.

Fast screen: native MT5 Model 1 (M1 OHLC). Confirmation: Model 4, 150 ms execution delay, using the broker's stored spreads and trading conditions. Older periods are NOT guaranteed real ticks: the earlier study reports real ticks only from January 2026. Every run must preserve the journal, coverage warnings, report, inputs and hashes. A five-year requested date range is not by itself proof of five-year coverage.

## No-signal reference (ours, not the video's strategy)

Fixed independent random entry opportunities at completed M15 bars, random 50/50 direction, 2 ATR stop, 2R target and the same risk/session/one-position sizing rules. Skip the first bar of each day. Entry probability per eligible bar: BTC reversal 0.008; XAU breakout 0.004; USDJPY combined 0.009; USDJPY breakout 0.004. These rough rates reflect the already-observed one-year trade frequencies and are not fitted on the new periods. Seeds 101, 202, 303; compare the median return and median PF, never cherry-pick a seed. Rates are opportunity rates, not guaranteed matched executed trade counts. Stops differ from structure-based raw stops; this is a no-signal sanity reference, not a causal isolation of the profile effect.

Run controls only for raw versions meeting the absolute PF/return/count gate. If none meets it, stop without spending tests on controls or optimization. Model 4 confirmation of raw failures is allowed to distinguish a coarse OHLC screening artifact from a genuine failure, but cannot be used to select different parameters.

## Optimization, conditional on qualification

Fixed 1% risk, record every configuration; staged timeframe, entry, stop, trailing, 0.5-6R/exits, session, direction, filters and management search, top three per stage and joint neighbor stability checks. Development: 2021-09-26 to 2024-09-26; validation: 2024-09-26 to 2025-09-26. The last year has already been inspected and is NOT an untouched holdout. Reserve earlier unused 2019-09-26 to 2021-09-26 only if adequate data exists; otherwise label holdout unavailable and require prospective validation. No invented holdout or pass probability. Monte Carlo only after a final version is frozen.

## Safety and completion

One isolated portable tester at a time; empty research chart profile, live trading disabled, local agents only. A study lock prevents duplicate instances. Zero compile errors/warnings and strict report-input identity required. Report failed order types explicitly. Nothing is promoted or pushed by this task.
