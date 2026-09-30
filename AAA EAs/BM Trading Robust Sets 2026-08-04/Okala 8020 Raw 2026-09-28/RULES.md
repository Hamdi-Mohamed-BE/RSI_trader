# Okala 80/20 — frozen mechanical adaptation, 28 September 2026

## Scope and attribution

The user's Chart Fanatics transcript is the strategy source. Its payout and 70%-win-rate claims are not independently verified and are not test inputs. The trader uses discretionary futures price action, not a complete deterministic system. This research creates an explicitly **mechanical US100 CFD adaptation**, not an exact replication of his skill or futures results. NQ futures and a cash-index CFD can trade at different price levels. Original futures tick size is 0.25 index points; on CFDs use the actual symbol tick size. Ten index points means a price distance of 10.00, not 10 broker points.

Research only. Isolated native tester, no live account actions or deployment. Account comparison means the previously planned FTMO $10K 2-Step Swing and FundedNext $5K Stellar Instant, not FNL futures. Standalone first; no mixing a failed raw strategy into the existing portfolio. Preserve the existing bots and exits.

## Explicit transcript rules

- Nasdaq prices ending in 20 or 80, potentially used either direction, combined with price structure.
- 10-minute context and 200-second execution bars. True 200-second bars must be aggregated from ticks, never silently replaced with M3/M5 bars.
- Fork: impulsive move, rejection wick, following candle tests but cannot break the extreme, then reverses.
- H: impulse down, weak rebound/lower high, continuation; cross-section retest is an entry mechanism. Mirrored upside allowed in this research.
- Cross-section: retest of the junction of two continuation candle bodies, with a 20/80-level confluence.
- Repair: an untouched wickless candle boundary as a possible target/confluence, not a guaranteed resting-order location. Price candles do not prove unfilled orders exist.
- Initial 10-index-point stop, first profit around +15, move remaining position to entry after first profit, optional later +30 / +60 or discretionary runner.
- Prefer liquid New York trading and avoid lunch. No numerical time windows or daily trade cap are specified by the speaker. No verified risk-per-trade, filters or entry tolerance is supplied.

## Frozen automation choices — ours, not claims about the trader

Session: 09:30–11:30 and 13:30–15:30 America/New_York, DST-aware. Force flat at 15:55 or after 20 minutes. No overnight carry. One trade idea at a time, no pyramiding, at most 7 ideas/day. No sizing up after wins or losses. Reuse of the same level in either direction blocked for 10 minutes (documentation corrected to match the original code; no entry behavior changed). Spread above 2.0 index points blocks entries. These choices can materially alter performance.

Bars: 200-second buckets aligned to broker/UTC midnight (three per 600 seconds); 10-minute context likewise. Source Exness server is UTC. Ignore the first incomplete bar and stale/gapped sequences. Closed bars only create setups. Current tick may trigger a pre-existing setup. Synthetic ticks in older history must be labelled, not called genuine 200-second historical observations.

Levels: 100*k+20 and 100*k+80, nearest level within 2.0 points of fork extreme or candle-body junction. Control is the same system shifted by 50 points: levels ending 30/70, with identical 40/60 spacing. No tuning of the phase after results.

Fork: the latest closed 200-second bar has range >=4 points, rejection wick >=50% of range, body <=35% of range; the preceding three bars moved at least 20 points toward its extreme. Extreme lies within 2 points of a level. During the next 200-second bar only, price retests within 2 points without penetrating by more than one symbol tick, then breaks the rejection bar's opposite extreme. Enter at market only if the 10-point stop lies beyond that rejection extreme. Both directions; no higher-timeframe trend filter for this mean-reversion setup.

Cross: two successive closed 200-second candles of the same direction, each body >=4 points, body junction gap <=2 points. Junction = mean(first close, second open), within 2 points of an eligible level. Wait up to 600 seconds for a pullback from the continuation side to within 2 points of the junction and then a 2-point bounce. Cancel if price penetrates junction by more than 3 points. Market entry; no future-bar hindsight. H-cross additionally requires the last two closed 10-minute bars to have directional closes and matching higher highs/lows (long) or lower highs/lows (short), and those bars' close-to-close movement >=20 points. This is a simplified H-context proxy, not visual pattern recognition.

Combined: fork has priority, then H-cross, then unfiltered cross, never overlapping ideas. Standalone fork, cross and H-cross diagnostics use the same exits. Repair is a target component, not an independently invented blind-entry bot.

Staged exit: 50% at +15 points; move remaining stop to actual entry after this partial succeeds. 25% at +30. Final 25% at the nearest valid repair target 30–60 points away, otherwise +60. A long repair target is the high/open of a prior bearish no-upper-wick candle; short is low/open of a bullish no-lower-wick candle. Wick <=one symbol tick, no subsequent touch, lookback 36 execution bars. No discretionary runner. Single-TP sensitivity closes 100% at +15, same entries and 10-point initial stop. Broker latency/slippage can make actual risk and targets differ from intended distances.

Native raw sizing: fixed $100 stop-risk budget on $10K initial equity, no compounding; round down to 4 volume steps so 50/25/25 partials are representable. This intentionally replaces the generic pipeline's round-up helper: never exceed requested risk simply to fit a minimum lot. Native hedging account required. Server-side SL; partial targets managed on ticks with 150ms execution delay, which is less optimistic than guaranteed ideal limit fills.

## Test plan, gates and prop simulation

Compile clean; smoke test; six frozen variants on the last year. Combined and shifted-level control also receive 6m/3y/5y native checks, with Model1 older-history screening distinguished from Model4 confirmation. Do not optimize a loser. Gate requires positive results and PF>=1.15 on 3y/5y, >=30 ideas and superiority to control. Report every tried configuration, not just winners. No production promotion in this request.

Use native deal events plus sampled sub-minute floating-equity extrema for prop replay. Group partials into one idea for win rate and streaks; separately audit each position's partial profits held <=30 seconds for FundedNext. Count one risk budget per whole idea, never per partial. Initial margin cap30%, available-loss-headroom caps, max7 ideas/day, stop admitting after3 losing ideas/day. Size down for margin before rounding down; report actual achieved risk, not just the configured maximum. No fabricated target-broker execution or guaranteed payout probabilities.

FTMO: 10%/5%, four opening days per phase, 5% Prague-midnight daily and10% static total limit, 80% funded reward after14days and flat. Assumed administration delays2/5 business days. Instant: no challenge,6% balance-trailing floor, initial70% split,14day/+1% orEOD/+5% eligibility, retain3% initial capital above floor. Conservative post-withdrawal ratchet. Target commissions, full news calendar and account-specific lot specifications are not fully verified; base/stress scenarios must be labelled assumptions.

Instant Quick Strike is a serious compatibility gate, not a suggestion to hold losing trades longer: official rule measures profitable trades closed within30seconds, at30% of cycle profits a violation. Test original durations. Never alter timestamps, force a minimum holding period, or split trades to evade rules. If the scalping profits concentrate there, report the incompatibility; conservative simulation withholds such a cycle's payout and counts a compliance failure, separately from drawdown failure. Exact firm evaluation of partial exits remains a confirmation requirement.

Sources checked 28 September 2026: [CME NQ](https://www.cmegroup.com/markets/equities/nasdaq/e-mini-nasdaq-100.contractSpecs.html), [MQL5 timeframes](https://www.mql5.com/en/docs/constants/chartconstants/enum_timeframes), [FTMO objectives](https://ftmo.com/en/trading-objectives/), [FTMO Swing](https://ftmo.com/faq/ftmo-swing-account-type/), [Instant loss rules](https://help.fundednext.com/en/articles/11641163-what-are-the-daily-loss-limit-and-the-maximum-loss-limit-for-the-stellar-instant-accounts), [Quick Strike](https://help.fundednext.com/en/articles/14702484-understanding-the-quick-strike-parameter-on-fundednext).

## Audit revision 1.01

Repair targets must also be untouched by the current, partly formed 200-second candle as observed at entry. Initial code checked subsequent closed candles only; the audit adds the current candle check, without changing numerical thresholds. Initial build and all its results are preserved in `audit-initial-build`; all frozen native cases are rerun. Both revisions count in the research ledger. This is a correctness repair, not selection of a favorable parameter set.

Native floating snapshots can carry a quote timestamp up to 150ms older than the synchronous fill that already changed account cash. The offline analyzer aligns such cash states forward to their matching native deal timestamp; it never backdates a fill or changes profit, price, duration, or the native trade log. Breach replay remains approximately one-second sampled and conservatively combines interval lows with partial-profit floor increases.
