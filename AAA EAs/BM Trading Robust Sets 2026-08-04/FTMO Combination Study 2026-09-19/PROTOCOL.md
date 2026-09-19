# FTMO combination study — fixed protocol

Research only. The user approved raw Gold Overnight Value Area integration and requested risk = FTMO's 5% daily allowance / 7. On $10,000 this is $71.428571 per entry, based on initial capital, not compounded equity. This study does not change live risk settings or submit orders.

## Evidence and selection

- Audit every available standalone 5-year EA/mode cache, including archived alternatives. Reconstruct original stops from entry orders where possible; do not use a modified final position stop. Report missing/proxy risk separately.
- Screen non-news modes on data before 2024-09-19. Pick one mode per strategy, requiring at least 50 training trades and positive stressed expectancy. Rank high-win candidates separately from expectancy candidates.
- Evaluate frozen small combinations, the new raw Gold EA, and Gold/Silver news additions. Do not select a portfolio simply to print 70%.
- Existing EA parameters were researched retrospectively. News parameters explicitly fitted 2025-09-19 to 2026-09-19. None of these results establish an independently calibrated future payout probability.
- Broad comparison ends at the earliest cached evidence boundary, 2026-08-31 exclusive (Month End Flow ends first). Windows begin 2026-06-30, 2026-04-30 and 2026-02-28. The joint bootstrap uses 26 complete weeks, March 2–August 30. Most existing histories do not run to September 19. Show exact dates, not 'today'.

## Account model

- Single $10K FTMO 2-Step Swing attempt. 10% first phase, 5% verification, four Prague entry dates per phase. Static $9,000 equity floor; daily Prague-midnight balance minus $500.
- Two business days review after phase 1; five after verification. Both are explicit assumptions. First funded trade starts 14-calendar-day reward wait; request only flat with no pending orders and >=$25 gross profit. 80% reward; assumed four business days to receipt. Stop at first request, not repeated monthly withdrawals. No evaluation profit withdrawal, fee refund, tax or repurchase.
- Margin model: gold/silver 1:15, main US index 1:15, FX 1:30, crypto conservatively 1:1. EURUSD contract100K, gold100oz, silver5000oz, US1001, BTC1, ETH10. Crypto per-side fee0.0325% notional per FTMO July2025 update. Source unit quantities are converted to target contracts. Actual regional/account specs require confirmation before deployment.
- Both news directions reserve margin before any fills; no perfect hedged-margin relief or hindsight admission. Do not assume quoted tiny-stop risk implies affordable margin. Compare literal $71.43 per order against lower news risk/margin-compatible sizing.
- Round upward to broker .01 lots/minimum in the study (the existing user policy), then check actual planned cash risk and margin. Portfolio safety gates can reject unaffordable/over-budget trades. Never silently treat the requested amount as a guaranteed loss cap.
- Reference uses observed spread/gap fills plus source commissions/swaps, with fee floors. Stress adds explicit spread/slippage and adverse cash-flow haircuts/carry reserves. These are scenario assumptions, not measured FTMO slippage.
- Broad portfolio equity uses a conservative simultaneous initial-stop envelope for open trades, not synchronized FTMO ticks. It can reject trades that would survive live, and cannot bound all gap losses. Call breaches 'model breaches', not proven account liquidation.

## Dependence and reporting

- Historical shared-cash chronological replay, not a sum of independently compounded EA returns. Preserve entry costs, concurrent exposure and resets between phases.
- Joint weekly resampling keeps all included EAs/news on each sampled week's timestamps, including carried exits. Repeated weeks get unique trade IDs. Entry/exit timing is shifted together; pending reservation precedes fill. One EA's open position blocks duplicate synthetic entries for that EA.
- Use the same full-week source pool and seed for every 2/4/6-month horizon; additional block-length sensitivity for shortlisted plans. Report sample size, selection bias and source length. Resampling cannot create independent market regimes.
- Report funding, first payout receipt, model breach, remaining unfinished, trade counts, win/loss streaks, modeled drawdown and conditional payout size. 70% is a goal to assess, not a guaranteed result.

Official references (checked 2026-09-19):
- https://ftmo.com/en/trading-objectives/
- https://ftmo.com/en/faq/ftmo-swing-account-type/
- https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/
- https://ftmo.com/en/forbidden-trading-practices/
- https://ftmo.com/en/blog/trading-updates/trading-update-2-feb-2026/
- https://ftmo.com/en/blog/trading-updates/trading-update-7-may-2026/
- https://ftmo.com/en/blog/ftmo-enhances-crypto-trading-new-instruments-and-better-spreads/

Swing news permission does not automatically approve news-gap exploitation. Written FTMO clarification of the precise straddle design is a prerequisite to calling a modeled news payout eligible in practice.
