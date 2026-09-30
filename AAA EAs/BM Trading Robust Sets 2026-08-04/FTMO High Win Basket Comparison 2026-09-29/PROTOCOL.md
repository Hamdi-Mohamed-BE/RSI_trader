# FTMO high-win basket comparison — frozen before replay

Research only. Do not modify active EAs, presets, MT5, orders, account settings, or prior reports.

User additions: XAU RSI VWAP is retained despite its newer PF1.18; Nasdaq 5M uses DI14/EMA12, initial stop0.60% of price, ATR6 trail after1R, no fixed target. Among completed comparable saved recent-year Nasdaq modes examined, this has the highest win rate while maintaining PF>=1.2. The old0.75R two-month test has PF0.85 and is excluded; no cancelled research is resumed.

Interpret the previous shortlist as six distinct EAs, not both EMA3 versions at once. Compare:

1. Current13: unchanged source basket from the existing FTMO audit.
2. CurrentCore5: Gold Overnight raw, EMA3 current audited inputs, Nasdaq Overnight, XAU RSI VWAP, Nasdaq 5M DI/ATR. All five already belong to Current13. This isolates removing EAs without substituting older builds.
3. HighWin8: Gold Overnight raw, ORB Volume Profile0.75R, EMA3 Safe, US100 H1 ORB1R + ADX25, XAU Squeeze Safe, Nasdaq Overnight, XAU RSI VWAP, Nasdaq 5M DI/ATR. No duplicate EMA3. The four changed/additional high-win modes are retained old/research evidence, not current-build validation.

No new optimization. ADX25 is the highest saved win rate; ADX20 is essentially tied and is not searched again. Main portfolio comparison uses the common supported interval: 27September2025 through31August2026. The older Squeeze Safe evidence ends1September2026, so do not label this a full trailing year. Start flat for all baskets; same entry window, broker-path data, risk, costs, and account rules. Reproduce the earlier full-period Current13 reference separately as a regression check, not as an unequal-date competitor.

$10,000 shared FTMO2-Step Swing account; fixed maximum$50 initial-stop risk per accepted trade, rounding down. No risk increase to compensate for fewer trades. A: -$200 daily equity close / +$400 daily equity close, then stop entries for that Prague day. B sensitivity: $250 combined original open-risk cap replaces the internal daily-loss stop; same+$400 profit close. FTMO's separate $500 daily equity-loss amount and $9,000 static total floor remain. Policies replace rather than stack with the original package governors, exactly as in the earlier audit.

Reuse the audited offline minute-marked source-trade replay. Reference, higher costs, costs plus10% weaker gross outcomes, and five-minute forced-liquidation delay are tested for A; reference/higher costs for B. No terminal access. Reuse existing phase/reward lifecycle: +10%/+5% flat targets, four opening days per phase, two/five assumed business days between stages, earliest funded request14calendar days after first trade, minimum$50 gross profit,80% share, two-business-day pause after each request. Requests are not guaranteed approvals or cash received.

Weekly Monday starts with at least30days of follow-up; report horizon-complete cohorts only, paired dates across portfolios. Compare120/180-day completion/request frequencies and conditional median timing, plus unconditional mean six-month reward shares including zero outcomes. These overlapping historical starts are not independent trials or forecasts of pass/payout probabilities. Selection used some of the same history.

Audit new ledgers against native original stops and net/gross/commission/swap identities; reject missing/ambiguous stop records rather than invent risk. Preserve sources/hashes, source counts, exclusions, simulation logs and accounting checks. Minute sampling, source-signal reuse after forced exits, Exness-to-FTMO translation, swap timing, old-build history and possible non-simultaneous intrabar extrema limit the conclusion. No tick-level compliance or completed validation claim.
