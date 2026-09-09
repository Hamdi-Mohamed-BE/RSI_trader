# DMC Playlist Strategy Review

## Executive conclusion

The playlist contains one current DMC overview, several older videos that explain pieces of the same discretionary framework, and many unrelated mindset, account-growth, indicator, news, or third-party-strategy videos. The consistent strategy thread is not a single fully specified algorithm. It is a hierarchy of important levels, a preference for fresh first reactions, a liquidity sweep or failed break, a regain or lower-timeframe reversal, and a target at the next meaningful level.

The current retained Calyx DMC should **not** be replaced by a full playlist clone. That experiment has already been performed. The earlier video-faithful EA damaged XAU performance and its only promising USTEC variant lost money in the untouched validation window. The best next research candidate is an incremental **DMC Fresh-Reaction Filter** added to the existing profitable XAU logic, with every feature tested one at a time against the unchanged baseline.

No DMC source, SET file, website, installer, BAT, or recommended-portfolio file was changed during this review.

## Playlist classification

| # | Video | Classification | Use in this review |
|---:|---|---|---|
| 1 | Easiest Trading Strategy (80-90% Win Rate) - DMC | Core | Primary current explanation of DMC levels, rejection/regain, entries, stops and targets.^1 |
| 2 | Easiest Way to Fix your BAD Trading Habits | Excluded | Psychology and habits; no strategy rule. |
| 3 | Testing Tori Trades Strategy | Excluded | Review of another trader's strategy, not DMC. |
| 4 | 2026 LAST Chance to Get Rich! | Excluded | General/account content; no reproducible DMC rule. |
| 5 | How to Turn $100 into $10,000 | Excluded | Account-growth content; no DMC level rule. |
| 6 | Private video | Unavailable | Cannot be reviewed. |
| 7 | 90% WINRATE Trend Trading Strategy | Supporting | Higher-timeframe direction, broken-level retests, fresh zones and lower-timeframe entries.^2 |
| 8 | 0 - Full Time Trader In 5 Steps | Excluded | Career/process content. |
| 9 | FREE FUNDED TRADER PROGRAM + MY COURSE FREE!! | Excluded | Promotional; no usable captions or DMC rule. |
| 10 | Trading Flat Markets | Supporting with limitation | Strategy-adjacent regime discussion. Captions are unavailable; visual review confirms chart analysis but no deterministic rule was taken from it.^3 |
| 11 | Predict The Market With 100% Accuracy | Supporting | Live examples of higher-timeframe bias, sweep, pullback, breaker/inefficiency context and lower-timeframe execution.^4 |
| 12 | Improve Your Mindset | Excluded | Mindset content. |
| 13 | Forex Indicator Tier List | Excluded | Indicator commentary, not DMC mechanics. |
| 14 | How BANKS Trade | Supporting | Observable liquidity-sweep, rejection and retest sequence. The causal story about banks is not treated as evidence.^5 |
| 15 | Simple BEGINNER RSI Trading Strategy | Excluded | Separate RSI strategy. |
| 16 | How To Stop Getting Wicked Out | Supporting | Waiting for the sweep, confirmation, stop buffer and structural invalidation.^6 |
| 17 | How To Improve Your Trading | Excluded | General improvement content. |
| 18 | Grow A Small Account (Strategy To Quick Profits) | Supporting | H1 direction, London/New York behavior, untested levels, M5 confirmation and prior-day targets.^7 |
| 19 | How To Grow A Small Forex Account | Excluded | Account/risk content, not level logic. |
| 20 | Unavailable video | Unavailable | Cannot be reviewed. |
| 21 | How To Trade NFP | Excluded from DMC | Separate event strategy that overlaps News Pulse; not a DMC improvement.^8 |
| 22 | How To Take Profits Like A Pro | Supporting | Structural partial-profit idea and stop-to-break-even concept.^9 |
| 23 | How To Grow A Forex Account Faster | Excluded | Account-growth content. |
| 24 | When To Place Blind Limit Orders | Supporting | First flip-retest rule, repeated-test rejection, confirmation requirement and pending-order cancellation.^10 |
| 25 | How To Trade A Small Trading Account | Excluded | Account-growth/risk content. |
| 26 | How To Become A Profitable Forex Trader | Excluded | Learning/discipline content. |

## Strategy logic reconstructed from the relevant videos

### Level hierarchy

The current DMC overview gives highest importance to untouched monthly and weekly candle-body levels, followed by daily levels and recently crossed levels. Older videos broaden the map with prior daily highs/lows, supply/demand or breaker areas, important pivot highs/lows, equal highs/lows that may contain clustered stops, and session highs/lows.

The repeatable principle is stronger than the labels: a level matters when it is visible on a higher timeframe, has not already absorbed several reactions, and leaves a plausible route to another meaningful level.

### Freshness and first touch

The clearest recurring rule is that the first interaction is materially different from later interactions. An untouched level or the first retest after a genuine support/resistance flip may support a direct entry. Once a level has already reacted, a later touch is weaker and should require confirmation. Repeated support-as-support or resistance-as-resistance tests are specifically treated as vulnerable to a sweep.

### Three distinct signal types

The videos describe three patterns that should not be merged into one condition:

1. **Failed break / rejection:** price trades through a level but the candle closes back on the original side.
2. **Quick regain:** a candle closes beyond the level, but a following candle rapidly closes back through it.
3. **Flip retest:** price closes decisively through a level and later returns for the first test from the opposite side.

Each pattern implies a different trade direction and invalidation. The present EA implements only a simple form of the first pattern.

### Direction and route

The creator's higher-timeframe direction is the expected move from the current level toward the next important level. Older videos also use H4/H1 structure breaks and pullbacks as a practical trend filter. London is described as frequently establishing the day's move; New York may continue it or reverse it after a sweep and close back through an important level.

This is a route-based bias, not a moving-average trend definition. It is also partly discretionary, so it must be translated into explicit rules before testing.

### Confirmation and entry

The common confirmed entry sequence is:

1. price reaches or sweeps an important level;
2. a candle rejects or regains it;
3. lower-timeframe structure turns in the expected direction;
4. the first pullback/retest supplies the entry.

A blind limit is reserved for the first retest of a clean flip. The videos do not support blind entries on repeated same-side tests. DCA appears only as an optional discretionary technique and is not required by DMC.

### Stops and invalidation

Stops are generally described as structural: beyond the failed-break extreme, beyond the next level behind the setup, or beyond the confirmation range with a small buffer. The stop should not sit exactly where a second liquidity sweep is obvious. When a distant structural extreme produces an unusably wide stop, the creator sometimes waits for a lower-timeframe reversal and then uses that smaller structure for invalidation.

### Targets and management

Targets include the next higher-timeframe level, the opposite side of a zone, a prior-day high/low, or the next swing. The entry and target should remain consistent with the timeframe of the setup. Early exit is suggested when price fails to produce the expected new high/low and instead confirms an opposite move.

The partial-profit video proposes reducing exposure at an important opposing level based on the reward still available versus the open profit at risk. Its verbal formula is not defined precisely enough to implement verbatim. A simpler structural partial-exit experiment would be more auditable.

## Current retained DMC versus playlist logic

| Component | Current retained DMC | Playlist framework | Material gap |
|---|---|---|---|
| Entry levels | Previous completed D1 candle body high/low | D1/W1/MN1 bodies plus pivots, session liquidity and structural zones | Current scope is much narrower. |
| Freshness | No touch-count or used-level state | Untouched/first test preferred; repeated tests weaker | High-value missing filter. |
| Rejection | H1 touches/crosses D1 body edge and closes back with directional candle | Failed break is one distinct setup type | Current implementation is a valid simplified subset. |
| Quick regain | Not tracked across two closed candles | Close outside followed by rapid close back inside | Missing distinct setup. |
| Flip retest | Not implemented | First retest after a decisive close through the level | Missing distinct setup. |
| Direction | Optional D1 Markov gate; otherwise reaction direction | Expected route to next HTF level plus H4/H1 structure | Current bias does not measure route or nearby opposition. |
| Confirmation | One closed H1 candle | Optional M15/M5 structure reversal and first retest | Current entry may be early. |
| Session | Wrapper supports all/Asia/London/NY/overlap; selected XAU is Asia | London may set direction; NY continuation or reversal | Infrastructure exists, but no session-transition logic. |
| Stop | Selected XAU uses fixed $22.50 price distance; ATR/signal-candle variants exist | Failed-break extreme or next structure behind, with buffer | Structural stop is not selected and portable ATR tests failed. |
| Target | Fixed RR; selected XAU uses 3R | Next meaningful structural level or prior high/low | Current target ignores available room. |
| Stale-order handling | Market entry only; no level cancellation state | Cancel a missed limit after price crosses another level | Relevant only to a future flip-retest pending mode. |
| Exposure | One trade/day, one exposure, 1% risk | Discretionary blind/confirmation/DCA choices | Current risk control is safer and should remain. |

## Why a full playlist rewrite is not recommended

The broad rewrite was already tested in `DMC Video Update 2026-08-11`. It included D1/W1/MN1 candle-body levels, untested-level tracking, failed loss/gain, quick regain, immediate or retest entries, structural stops and structural targets.

### Matched one-year comparison

| Asset | Existing DMC | Video-faithful baseline | Interpretation |
|---|---:|---:|---|
| XAUUSD | +20.87%, PF 1.15, WR 41.20%, DD 9.82%, 233 trades | -8.74%, PF 0.92, WR 32.80%, DD 24.83%, 186 trades | Full rewrite was a clear regression. |
| USTEC | -40.84%, PF 0.73, WR 31.41%, DD 45.11%, 277 trades | +2.79%, PF 1.02, WR 39.06%, DD 25.02%, 192 trades | Less bad, but PF 1.02 is not a deployable edge. |
| US30 | -3.54%, PF 0.98, WR 37.99%, DD 29.02%, 279 trades | +4.50%, PF 1.04, WR 37.88%, DD 23.09%, 198 trades | Improvement remained too weak. |

The selected USTEC daily-level variant then lost **3.16%** in the untouched final four months with PF **0.92**, win rate **31.03%**, DD **11.16%**, and 58 trades. This failure is decisive: adding all discretionary concepts at once neither preserved the XAU edge nor created a robust index edge.

The later full DMC pipeline also showed that the portable ATR-stop form did not transfer robustly to XAG, US30, US100, BTC or GBPJPY. The current evidence supports keeping DMC confined to XAU until a genuinely new frozen variant passes independent validation.

## Recommended improvement for approval

### DMC Fresh-Reaction Filter

Keep the existing XAU DMC signal, session, risk and management as the baseline. Add only the following research switches:

1. **Previous-day body freshness gate.** Count completed M15/H1 touches of the selected D1 body edge after that daily candle closes. Permit the signal only when the current event is the first touch, with a separate test allowing one prior touch.
2. **Separate rejection and regain modes.** Preserve the current one-candle rejection exactly. Add a two-candle regain mode where the first candle closes outside and the next closes back inside within one or two H1 bars. Never combine their results invisibly.
3. **Room-to-target gate.** Map the nearest opposing previous-day high/low and fresh D1/W1 candle-body level. Skip the trade if the nearest obstacle provides less than the configured minimum R. Initially keep the actual 3R TP unchanged so this tests selection quality rather than changing entries and exits simultaneously.
4. **Optional M15 confirmation.** After the H1 rejection/regain, require M15 to break the most recent micro swing in the trade direction and enter only on its first retest. Compare this with the unchanged immediate H1 entry.
5. **Level consumption.** Once an edge produces a trade or a confirmed reaction, mark it used for that day. Do not permit another trade from the same edge.

This is the best balance between fidelity and evidence. It extracts the playlist's most objective ideas without replacing the daily-body core that currently works on XAU.

### Settings that must remain unchanged in the first experiment

- Asset: XAUUSD only for feature selection.
- Signal timeframe: H1.
- Entry session: Asia, matching the selected three-year configuration.
- Stop: existing fixed $22.50 price-distance baseline.
- Target: 3R baseline.
- Management: Dynamic 50/20 baseline.
- Risk: user-selected dynamic percentage, default 1%; never more than 1% in this research.
- Exposure: one open DMC position and one DMC trade per day.

Freezing these controls ensures that any performance difference comes from the playlist-derived signal filters rather than a simultaneous stop, target, session or risk change.

## Features not recommended

- **Do not add DCA or martingale.** They are discretionary and conflict with the fixed 1% risk ceiling.
- **Do not add no-stop trading.** It is inappropriate for an automated system and prop-style loss limits.
- **Do not make monthly/weekly levels independent entry generators yet.** The previous full rewrite already tested this broad approach and failed.
- **Do not enable blind limit orders by default.** If studied later, restrict them to the first clean flip-retest and run them as a separate research arm.
- **Do not encode the “banks must do this” narrative.** Only observable price events—sweep, close, regain, retest and next level—are testable.
- **Do not use the advertised 80–90% or 100% win-rate claims as a target or prior.** The videos do not publish a reproducible audit, and Calyx's native tests did not reproduce those claims.
- **Do not alter live/recommended DMC before an untouched test.** The current XAU version remains the benchmark.

## Future pipeline after approval

| Stage | Test | Purpose | Promotion gate |
|---:|---|---|---|
| 0 | Re-run unchanged XAU Asia 3R baseline on identical windows | Control | Must reproduce cached/native evidence. |
| 1 | First-touch gate: strict first touch vs at most one prior touch | Test level freshness only | Better development PF/recovery without collapsing trade count. |
| 2 | Rejection vs 1-bar/2-bar regain | Separate event types | One mode must survive the locked window independently. |
| 3 | Room gate at 1.7R, 2R and 3R | Remove trades blocked by nearby structure | Locked PF/DD improve, not just return. |
| 4 | Immediate H1 vs H1 plus M15 break/retest | Test confirmation delay | Locked result positive with an adequate sample. |
| 5 | W1/MN1 proximity as confluence only | Test higher-timeframe context without new entries | Incremental locked benefit and stable neighbors. |
| 6 | Structural stop and structural partial exit as separate arms | Improve portability/management | Must beat fixed-stop control after costs. |
| 7 | Freeze winner, run Every-Tick locked/latest/full history and Monte Carlo | Final XAU decision | Positive locked and latest windows, acceptable DD and MC tail. |
| 8 | Transfer the frozen logic to USTEC, US30 and BTC | Cross-asset research only | Each asset must pass independently; no pooled rescue. |

For USTEC and US30, any later transfer should be New-York-session research with an asset-scaled structural or ATR stop, because a fixed XAU price distance is meaningless. BTC should be evaluated separately with weekday/weekend splits. These are test instructions, not recommended live configurations.

## Decision

**Recommended for the next approved experiment:** DMC Fresh-Reaction Filter on the current XAU Asia 3R baseline.

**Not approved or performed in this review:** source changes, compilation, optimization, cross-asset backtests, website changes, BAT changes, installer changes, or portfolio changes.

## Sources

1. Dumb Money Hunter. [“Easiest Trading Strategy (80-90% Win Rate) - DMC.”](https://www.youtube.com/watch?v=MzZ0b_ZVeQw) February 23, 2026.
2. Dumb Money Hunter. [“90% WINRATE Trend Trading Strategy.”](https://www.youtube.com/watch?v=KbpNGzvsd7E) February 20, 2022.
3. Dumb Money Hunter. [“Trading Flat Markets.”](https://www.youtube.com/watch?v=IAB0Kn6tU7A) June 23, 2021.
4. Dumb Money Hunter. [“Predict The Market With 100% Accuracy.”](https://www.youtube.com/watch?v=eseD8Y0sjKk) June 15, 2021.
5. Dumb Money Hunter. [“How BANKS Trade.”](https://www.youtube.com/watch?v=4eZdVYkkh1I) March 30, 2021.
6. Dumb Money Hunter. [“How To Stop Getting Wicked Out.”](https://www.youtube.com/watch?v=yGJmxFByqeI) October 28, 2020.
7. Dumb Money Hunter. [“Grow A Small Account (Strategy To Quick Profits).”](https://www.youtube.com/watch?v=k593DVFIQkE) September 16, 2020.
8. Dumb Money Hunter. [“How To Trade NFP.”](https://www.youtube.com/watch?v=PbAzhwy9vG0) May 7, 2020.
9. Dumb Money Hunter. [“How To Take Profits Like A Pro.”](https://www.youtube.com/watch?v=RUFBtm4vpyU) April 1, 2020.
10. Dumb Money Hunter. [“When To Place Blind Limit Orders.”](https://www.youtube.com/watch?v=0GQaWMi2PAM) March 23, 2020.
11. Calyx local source: `AAA Final EAs/AAA Final DmC EA/AAA_Final_Strategy_Engine.mqh`, `AAA_RunDmC`.
12. Calyx local evidence: `DMC Video Update 2026-08-11/FULL COMPARISON REPORT.md` and `Active Portfolio Full Pipeline 2026-09-05/07 DmC/STEP 6 - DMC XAU FULL OPTIMIZATION.md`.

