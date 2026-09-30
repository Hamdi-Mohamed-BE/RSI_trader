# FTMO Swing versus Stellar Instant — frozen research protocol

Research only, 28 September 2026. No purchase, live terminal/API connection, installer changes, website updates, or Git push. Existing live terminal must not be restarted. Any native operation uses the established isolated portable tester with live trading disabled.

## Question and evidence

Compare a single $10,000 FTMO 2-Step Swing with a single $5,000 FundedNext Stellar Instant. Current 13-EA basket, News OFF, replacing the old Nasdaq fixed-target ledger with the exact DI14/EMA12/0.60% initial stop/ATR6-from-1R/no-TP ledger whose binary and settings hashes match the approved user-selected release. This release is retrospective, not pipeline-approved.

Use the common available period 2025-09-27 to 2026-09-25 exclusive (not invent the missing last two days of the newer Nasdaq ledger). Audit initial stops against native order records, per-lot P&L, duplicate/partial positions and exact source hashes. Save all tried variants, including poor results.

Extract M1 bars from the isolated Exness research terminal for XAUUSD, USTEC and USDJPY. Reconstruct per-position open P&L with M1 bid/ask-spread estimates, native entries and native exits. Evaluate shared floating equity and within-minute adverse envelopes. OHLC extremes lack simultaneous tick ordering; label conservative envelopes separately from sampled minute equity. This is not FTMO/FundedNext native execution and not an exact multi-EA native backtest. No guarantee that signal availability is identical after a rejected or early-closed position. Do not invent broker quotes, swap histories, tick coverage or exact live probabilities.

If M1 extraction fails or has material gaps, publish a bounded ledger/reserve sensitivity only and explicitly withhold floating-equity-validated pass rates.

## Frozen portfolios and policies

- Full13: all current package EAs, News OFF; no ranking on this year.
- Core4: raw Gold Overnight Value Area, current Nasdaq 5M DI wider stop ATR, Nasdaq Overnight, USDJPY London Open Momentum. Structural comparison: three underlying markets, fewer competing gold EAs; not a data-selected best subset.
- FTMO full13 risk 0.25% and 0.50% of initial capital per trade. Include a separate existing-package 0.50% guard reference if its settings differ.
- Stellar full13 risk 0.15% and 0.25%; core4 risk 0.25%. Size down to min(risk cap, 5% available drawdown headroom) on Instant. Never round lots up or use a minimum-lot over-budget fallback.
- Proposed common static-plan limits: total planned stop risk 1.5%, same-symbol 0.75%, daily admission loss budget 1.5%, maximum 7 entries/day, stop admitting after 3 net losing closed positions/day, no martingale. Keep tested exits unchanged; do not invent a profitable early exit.
- Instant aggregate reserve risk <=20% available headroom; same-symbol <=10%; internal daily admission budget 0.75%. Daily rules are ours, not an official Instant DLL. Include protective cost reserves and retain 3% initial-capital equity headroom after withdrawal. Compare withdrawing all eligible profit as an explicitly unsafe sensitivity.
- Margin conservative cap 30% equity for proposed policies (ours); leverage FTMO XAU/USTEC 15, USDJPY30; Instant XAU7.5, USTEC5, USDJPY30. Contract/lot units harmonized to Exness research lots; actual target platform minimums need confirmation.

## Costs and compliance uncertainty

Native bid/ask fills already embed source spreads. Model commission using published target schedules plus native-cost floors where conservative. Reference retains source native swaps; stress doubles negative swaps and imposes an additional disclosed carry floor. Stress also worsens positive gross outcomes 10%, negative outcomes 10%, and adds round-trip adverse movement of $0.20 XAU, 2 USTEC points, 0.02 USDJPY. These are hypothetical sensitivity shocks, NOT measured target-broker costs. Avoid double-counting original commission.

Instant: news-profit deductions must be exposed; known NFP/CPI/FOMC times can be checked from saved event evidence, but this is not the complete firm's high-impact calendar. Include additional profit-haircut sensitivity if complete calendar unavailable, do not label baseline fully compliant. Audit <30-second trades and Telegram integration. Paid EA add-on, country eligibility, venue terms and payout approval cannot be simulated. No use of FNL50K (EAs prohibited).

## Lifecycle and reporting

FTMO: 10% then5% targets, >=4 opening days/phase, flat before passage, static10% total floor, Prague-midnight balance minus5% initial daily floor. New balance each phase. Assumed admin delays:2 business days between phases,5 to funded; distinguish these assumptions from rules. First funded payout eligible after14 calendar days and flat with >=$25 closed profit;80% share. Model request eligibility, not cash receipt or guaranteed approval. Fee €89 reported separately, never silently converted to USD.

Instant: no evaluation;6% balance-trailing floor capped at initial capital, equity checks continuously at model resolution. Request after14 days with >=1% growth or after EOD >=5%;70% share; flat before modeled payout. Withdraw gross amount from account, pay70% cash; floor never moves down. Test conservative post-withdraw high-water treatment and disclose ambiguity in official repeated-withdrawal examples. Minimum partial gross request assumed1% initial capital (sensitivity assumption, not verified contractual minimum). Price$104.99 plus unknown nonrefundable EA add-on; also show regular$149.99 cost sensitivity. No scaling benefit assumed.

Use actual rolling calendar starts first, common markets/dates for both products. Windows30/60/120/180 days; only fully observed historical windows enter each denominator. Report those overlapping samples as historical scenario frequencies, NOT independent trials or calibrated future probabilities. Where feasible use paired moving multiweek block bootstrap, fixed seed20260928; preserve cross-EA timing and whole trade duration, report boundary distortions and multiweek overlap. Bootstrap is not new market evidence. No new optimization or deployment promotion.

Report phase1/phase2/first-payout eligibility, median and p10-p90 milestone days CONDITIONAL on completion, modeled loss-limit failures before first payout and after withdrawals, unresolved share, gross/net reward cash, fee recovery, strategy-level admissions/min-lot/margin rejections, trades/day, winrate/PF/streaks, and sampled/envelope equity DD. Never replace failure/incomplete paths with successful-path average time.

## Rules sources checked 28 September 2026

- https://ftmo.com/en/trading-objectives/
- https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/
- https://help.fundednext.com/en/articles/11641163-what-are-the-daily-loss-limit-and-the-maximum-loss-limit-for-the-stellar-instant-accounts
- https://help.fundednext.com/en/articles/11641693-what-is-the-eligibility-criteria-for-my-performance-reward-in-the-stellar-instant-account
- https://help.fundednext.com/en/articles/12439744-what-will-happen-to-the-maximum-loss-limit-after-a-trader-withdraws-from-a-stellar-instant-account
- https://help.fundednext.com/en/articles/11641300-what-are-the-commission-charges-for-the-stellar-instant-account
- https://help.fundednext.com/en/articles/11641369-what-is-the-leverage-provided-in-the-stellar-instant-accounts
- https://help.fundednext.com/en/articles/11641410-is-news-trading-allowed-in-the-stellar-instant-accounts
- https://help.fundednext.com/en/articles/8020763-is-ea-allowed-in-fundednext

Any material method change after the freeze must be noted as an amendment with reason; do not choose a changed rule based on the preferred firm's result.
