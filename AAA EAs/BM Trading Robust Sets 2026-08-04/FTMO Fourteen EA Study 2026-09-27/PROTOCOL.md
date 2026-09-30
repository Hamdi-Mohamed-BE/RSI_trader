# FTMO fourteen-EA study — frozen before results

Research only. No live terminal, orders, EA settings, launchers, website, or Git changes.

User basket, unchanged entries/exits: XAU RSI VWAP; raw Gold Overnight Value Area; XAU Squeeze Momentum Standard; event-specific News Pulse XAU; DMC Fresh Reaction US100; current EMA3 H4 pivot 1.7R / dynamic 60-20; XAU Trend Progression; XAU ORB London–NY overlap; Nasdaq Overnight; US100 H1 ORB 13UTC; USDJPY London Open Momentum; US100 Month End Flow; DMC Current XAU; Claude Nasdaq 5M DI (fixed 2.5R, ATR trail off).

## Evidence

- Refresh standalone native MT5 Model 4 ledgers, 150 ms simulated delay, 2025-09-27 through 2026-09-27 exclusive. Exness history in the isolated research tester only. These are NOT FTMO-native fills.
- Original compiled EAs and current catalogue presets, no strategy search. News gets a research-only calendar include covering the same window, with unchanged event parameters; no invented release times. Source hashes frozen. Original position sizing remains only for extracting signals and per-lot returns; the shared-account overlay sizes anew.
- News schedule retains saved official receipts through September 19; FXMacroData bounded checks and official September BLS/Fed calendars show no additional NFP/CPI/FOMC through September 27. Point-in-time calendar vintages are not fully verified.
- Older real ticks may be missing: disclose measured native coverage. Native report/ledger net cash and initial order stops must reconcile before simulation.

## Sizing and comparisons

- One USD 10,000 Swing 2-Step simulated account, all fourteen strategies together.
- Non-news planned initial stop risk: fixed $50 or $70 (0.5% or 0.7% of initial capital). This makes the comparison stable across phase resets; not equity compounding, martingale, or adaptive multipliers.
- News: fixed $30 per pending side, both sides retained. Lots round DOWN to 0.01; below minimum signals skipped. Additionally test the user's 0.02-lot fallback separately if it exceeds the $30 cap, never silently call this fixed-$30 risk.
- Compare no extra gates (shared modeled margin and FTMO hard limits only) against existing conservative portfolio gates: $300 daily reserved-loss budget, $225 simultaneous initial risk, $150 per symbol/correlated metals, $9,200 projected-equity admission buffer, max seven entries/day, stop new entries after three net losses, reserve no more than 80% margin. This is a sensitivity, not an optimized best policy.
- Margin: XAU/USTEC 1:15, USDJPY 1:30, confirmed against FTMO's public symbols API on September 27; assumed lot steps 0.01 still require platform confirmation. FTMO Swing is UP TO 1:30, not 1:30 on every asset. Reserve both news sides independently (conservative; no hedge relief).
- Reference costs: native price fills plus commission floors. Gold uses the greater cost of native commission, $7/lot round trip and the current published 0.0014% notional charged on each leg; USDJPY uses the greater of native and $10/lot round trip (published $5 conservatively applied per leg). USTEC keeps a $0.70/lot round-trip buffer despite the public commission field being zero. These are disclosed scenario floors, not reconstructed historical FTMO bills. Adverse sensitivity reduces gross winners 10%, increases gross losers 10%, adds $0.20 gold/$1 news-gold/two US100 points/0.02 USDJPY adverse movement, doubles negative native swaps and adds carry reserves on holds longer than a day. These are hypothetical stress assumptions, NOT measured FTMO fills.
- Floating equity is approximated with full-stop reserves, ordinary 1R/news 1.25R reference and 1.25R/2R stressed. This is NOT tick equity or a guaranteed gap-loss bound. Do not describe reserve-triggered failures as observed live breaches.

## Challenge model

- Targets +$1,000 then +$500, four separate Prague trading days per phase, all positions/pending orders flat at passage. Static total equity floor $9,000; daily equity floor Prague midnight balance minus $500. No 2-Step Best Day Rule and no evaluation expiry.
- Two business days between phases, five to funded activation (model assumptions), first payout request after fourteen calendar days from first funded entry while flat and with at least $25 closed profit, four business days to assumed receipt. 80% profit share. Report mathematical eligibility separately from actual receipt/approval.
- Last-year historical continuous account and challenge replay. Joint-week bootstrap using complete common-year weeks, 1,000 paired paths per case; report 60/120/180-calendar-day horizons (2/4/6-month approximations). Preserve within-week cross-EA dependencies; disclose distortion of multiweek holds/calendar regimes.
- Report phase passage, activation, first-reward eligibility/assumed receipt, modeled limit failures and unresolved paths separately. Conditional milestone days are not unconditional waiting-time promises.
- News event optimization and other EA selection overlap this history. Results are fitted-history scenario frequencies, NOT reliable out-of-sample pass probabilities. No actual payout guarantee or deployment approval.

## Official rules checked September 27, 2026

https://ftmo.com/en/trading-objectives/
https://ftmo.com/en/faq/ftmo-swing-account-type/
https://ftmo.com/en/faq/what-are-the-account-specifications/
https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/
https://ftmo.com/en/faq/do-you-have-any-consistency-rules/
https://ftmo.com/en/forbidden-trading-practices/

Swing news permission does not expressly approve this pre-release straddle. Gap trading, overexposure and unreasonable cumulative risk may violate contract rules. The simulation does not predict compliance decisions. Obtain written clarification before using News Pulse on a purchased account.
