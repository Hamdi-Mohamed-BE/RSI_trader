# Two new papers: frozen raw standalone screen

Frozen before examining strategy returns, 2026-09-19. Research only; no BAT, live account, portfolio, website or deployment changes. MT5 is authorized only as a market-data source. Its connection currently fails authentication. These are proxy-data screens, NOT native MT5/FTMO backtests and NOT an estimate guaranteed to transfer to FTMO.

## Sources and necessary interpretations

- Gold: Caporale and Plastun (2021), https://doi.org/10.1007/s11408-021-00380-w . The tables specify positive-abnormal entry 19:00 and negative-abnormal entry 17:00 GMT+3. The prose reverses those clocks. The primary test follows the TABLES; the prose clock is a separately disclosed sensitivity, never an optimized selection. The negative threshold printed with a plus sign is interpreted as mean MINUS two standard deviations. The paper's full-day abnormal label cannot be known intraday: only the return already observed at the entry is used here. A 60-completed-day rolling threshold is an explicit implementation assumption, not an author-specified lookback.
- Japan: Iwanaga (2026), https://doi.org/10.1016/j.finr.2026.100108 . Opposite sign of the previous completed US cash-session S&P 500 close-to-close return. Enter at 08:45 Tokyo, exit 09:15 Tokyo (first 30 minutes of futures daytime session). JPX confirms 08:45 opening: https://www.jpx.co.jp/english/derivatives/products/domestic/225futures/01.html . Japanese holidays without regular cash trading are conservatively excluded; US-holiday stale signals are not repeated. The paper studies futures; a Japan-index CFD proxy may not reproduce the same effect.

## Gold deterministic rules

1. Fixed GMT+3 paper days; open is first available bid quote after 21:00 UTC the preceding day. Need at least 1,000 M1 bars for a prior day to enter the rolling sample. Use previous 60 such completed days, sample standard deviation.
2. At 14:00 UTC short if the available return from the day's open is negative and below prior mean minus 2 SD. At 16:00 UTC long if it is positive and above mean plus 2 SD. Maximum one trade per paper day. Use only entry-minute OPEN; no current candle high/low/close to decide entry.
3. Close at the first quote at or after 20:50 UTC. This deliberate CFD adaptation exits before the maintenance/rollover gap; the paper says end of day. Do not invent a 21:00 tradable quote. Missing exit quotes are audited.
4. The prose-clock sensitivity swaps long/short entry clocks, all other rules unchanged.

## Common raw prop-compatible wrapper

- Hard stop 2 x ATR(14) from completed H1 bars (Wilder smoothing). No TP, trailing, breakeven, parameter search or loss recovery. This stop and position sizing are OUR adaptations, not paper rules. A separate time-exit-only diagnostic can quantify the stop's effect, with no assertion that its nominal budget caps losses.
- Fixed initial-account risk budget $50 (0.5% of $10,000); predeclared $25/$75/$100 risk sensitivities only. Lots round DOWN, skip if minimum lot exceeds budget. No martingale or minimum-lot override. No production policy change.
- At most one position/day. Leverage 1:15 on both instruments, 50% maximum balance committed as margin. Current contract specifications projected through history, not historical accounts.
- Gold contract 100 oz, assumed lot step/min 0.01. Japan contract 10 JPY/point, assumed lot step/min 0.1, max 200 lots. Lot constraints await terminal verification. Japan P/L converted using cached contemporaneous USDJPY quotes; old FX quotes are flagged.
- Gold baseline: cached Exness M1 bid bars, per-minute recorded spread with $0.30 minimum; $0.10 adverse slippage per fill; FTMO public metals commission 0.0007% of notional PER SIDE (0.0014% round trip). Japan baseline: Dukascopy M1 bid/ask, at least 10 index points spread, 2 points adverse slippage per fill, zero index commission per public FTMO specification.
- Stress: spread doubled (gold minimum $0.60, Japan minimum 20 points), gold slippage $0.25 per fill / Japan 5 points per fill; same public commission. Slippage and spread floors are conservative assumptions, NOT measured FTMO execution.
- Flat before rollover: zero swap by design; any unexpectedly delayed exit crossing rollover invalidates this assumption and must be reported, not silently assigned zero.
- M1 adverse extremes test floating-equity breaches; stop gaps fill adversely at next available open. Intraminute high/low order and variable within-minute spreads are unknown. Peak-to-trough equity DD is an adverse-order M1 approximation, not tick-exact.

## Evaluation

- Common frozen end: 2026-09-01 exclusive. Report 6m, 1y, 3y, 5y with available warm-up. Signals before 2025 overlap the Japan paper's sample; the full five years are NOT independent out-of-sample evidence. Report 2025 onward separately.
- Chronological rolling Monday challenge starts, no shuffled individual trades, one attempt, no retry/rebuy. Both phases must pass sequentially: +$1,000 then fresh $10K +$500, four entry dates per phase. Two business days administrative handover assumption. Outcomes at 30/60/180 calendar days; full follow-up only. Report pending distinctly from breach, and phase 1 distinctly from both phases.
- Official risk limits: static $9,000 equity floor, $500 maximum daily equity loss anchored to each Prague midnight balance (including fees/floating). No 2-Step best-day rule. Planned daily exposure is naturally one $25-$100 risk trade; gaps can exceed it. Stop the attempt on a rule breach. Track 30 calendar days without a trade separately as inactivity risk, not a proven official account cancellation. Payout/KYC review and actual funding are NOT simulated.
- Rules reference: https://ftmo.com/en/trading-objectives/ ; https://ftmo.com/en/faq/ftmo-swing-account-type/ ; public specs https://ftmo.com/wp-json/ftmo/symbols . Prospective terms must be reconfirmed before purchase.
- No optimization or approval to trade based on this screen. Preserve failures, missing-data counts, provenance and unit tests.
