# Market-style bots — raw rules frozen before outcomes

Source: user-supplied clip about trend/Nasdaq, mean reversion/Bitcoin, volatility clustering/gold, and ranges/forex. The clip names four market families despite saying five, and omits exact rules, costs, dates and the meaning of +180R. We do NOT claim replication of its percentages. All concrete rules below are our research implementations. User authorizes building and comparing raw bots, not parameter optimization, production, deployment or account actions.

## Universe and common execution

Six independent bots: Nasdaq USTEC trend (mode 0); BTCUSD shock reversal (mode 1); XAUUSD volatility regime momentum (mode 2); EURUSD, GBPUSD and USDJPY range fade (mode 3). Exness research CFDs, not exchange futures or crypto spot. Do not infer one universally best asset or compare untested model/asset pairings.

Completed H1 bars only. Evaluate at the next H1's first quote within five minutes. Up to one attempted qualifying trade per UTC calendar date; one position; entries 07:00 through 16:00 UTC inclusive. Weekdays only except BTC includes weekends. Close after eight elapsed hours for trend/gold, six for BTC/FX, or 20:00 UTC, or five minutes before a known current broker session end, whichever comes first and is executable. No overnight intended. No future bar-completeness filtering. Current broker sessions may not reproduce old holiday schedules; delayed exits/fees are audited and invalidate unqualified execution claims.

Target 1% current equity at entry, volume rounded UP to broker step/minimum (user's normal policy); record actual initial-stop dollar risk after fill, overshoot, skipped constraints and all costs. Stop distance = 1.5 x SMA of the most recent 14 completed true ranges. Respect tick, stops and margin constraints. Fixed initial stop and target, no trailing, break-even, averaging, pyramiding, martingale or re-entry. Simulated 150ms order delay. $10,000 deposit, USD. Native fees are retained, not silently removed.

Indicators use 400 completed H1 bars, oldest to newest. EMAs seed at the oldest close (finite 400-bar EMA definition). ATR means simple average true range, not Wilder ATR. Rates are requested from shift 1, never the active bar. Reject signal if last H1 did not end at this hour; no stale-gap entry. Missing bars are not forward-filled. EMA20/50/200; standard deviation is population SD.

## Models (all defaults ours, not tuned)

0. **Nasdaq trend pullback:** EMA50 > EMA200 and EMA50 rising over five bars; penultimate bar low touches/breaches EMA20; last close exceeds both penultimate high and EMA20. Buy. Mirror for shorts. TP 3R; initial stop 1.5 ATR14; max 8h.

1. **Bitcoin shock mean reversion:** penultimate candle body magnitude >= 2 x ATR14 measured BEFORE that candle. Last candle body reverses the shock's sign, while its close remains on the stretched side of EMA20 (above for a positive shock, below for a negative one). Trade opposite the shock. TP 1.5R; initial stop 1.5 ATR14; max 6h. This does not assume every large move reverses.

2. **Gold volatility-state momentum:** volatility ratio ATR14 / ATR100 labels Calm (<0.8), Normal (0.8–1.2), Hot (>1.2). Fit a three-state transition matrix from the preceding 252 completed transitions, excluding the latest transition, with Laplace +1 per cell. Require current state Hot, >=20 observed outgoing Hot transitions, and P(next Hot | current Hot)>=0.55. Direction still needs evidence: buy when close > EMA50, EMA50 slope positive over five bars and last close > previous high; mirrored short. TP 2R; stop 1.5 ATR14; max 8h. Clustering predicts volatility, not direction; the directional trigger is an explicit extra hypothesis.

The regime skill's advertised runner is absent locally. This is a transparent fallback adapted to volatility states, NOT the missing Roan Bull/Bear/Sideways implementation, NOT GARCH and NOT HMM. Its causal state/transition concept informs the implementation; the transition matrix is recalculated using only completed past bars and checked independently.

3. **Forex range fade:** use the 20 closes BEFORE the penultimate bar for mean and +/-2 SD bands. Penultimate close must be outside a band; last close returns inside it. Require efficiency ratio over the last 20 changes <0.30 and absolute five-bar EMA50 change <0.25 ATR14. Buy lower-band re-entry / sell upper-band re-entry. Target the fixed pre-excursion mean. Stop 1.5 ATR14. Skip if remaining mean-target distance is outside 0.5–2R at the actual quote. Max 6h. Same unchanged parameters on EURUSD, GBPUSD and USDJPY.

## Matched control and statistical limits

Control uses the SAME qualifying signals/date, clock, stop distance, TP distance, sizing rule and timed exit, but assigns direction by fixed seed 290929 and a deterministic integer hash of the UTC date. This is a matched random-DIRECTION entry control, not random clock times and not the clip's unspecified random-level experiment. When direction reverses, reflect both stop and TP distances. At most one trade/day and intraday flattening aim to maintain matched samples; verify rather than assume timestamp/size parity. One native random seed is a noisy benchmark, not a full randomization distribution. Compare mean net R per position, not differently compounded dollar profits alone.

## Windows, selection and gates

Windows all end 2026-09-27 exclusive: 6m from 2026-03-27, 1y from 2025-09-27, 3y from 2023-09-27, 5y from 2021-09-27. Warmup 90 calendar days. Smoke 2026-08-01 to 2026-09-01. Three-/five-year initial screens Model 1; recent 6m/1y Model 4 with 150ms. Only candidates passing three-/five-year gates advance to long-window Model 4 confirmation. Real/generated coverage explicitly reported. No full optimization in this request.

Raw gate: both 3y and 5y positive, PF>=1.15, at least 30 trades, beat matched control mean net R and valid execution/cost evidence. Require recent 1y positive for a current shortlist. A failed raw gate stops advancement. Empty-signal result is insufficient sample, never success. No changing thresholds after seeing returns.

Best among these implementations: first rank eligible passes by lower 3y/5y PF, then lower equity drawdown, then recent-year PF. If none passes, report no qualified winner; the same ranking can identify the least-bad research candidate clearly labeled as such. 5y/3y/1y/6m overlap and are not independent out-of-sample tests. This is a frozen-rule historical raw comparison; the dates have been seen in unrelated prior research, so do not call them globally untouched holdouts or validated future performance.

Archive all source/build/SET/report/deal/signal/trace evidence and failed attempts. Native equity DD, balance DD, R, trade frequency, costs, streaks and yearly/subperiod results must be distinguishable. Any resampling diagnostic is separate from native evidence and cannot rescue a failed gate. No live terminal or Ava connection, installers, website edits, Git push or production changes.
