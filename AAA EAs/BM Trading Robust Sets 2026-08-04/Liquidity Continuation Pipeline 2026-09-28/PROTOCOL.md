# Liquidity continuation: exploratory full search, frozen 2026-09-28

Requested: XAU first-touch + retest combined as ONE EA, BTC first-touch, US30
first-touch. All three failed the original raw 3y/5y gate. The user's explicit
request authorizes an exploratory search exception, not a changed raw verdict or
live promotion. Original raw artifacts stay immutable; no website/BAT changes.

## Data and execution

Development: 2021-09-27 through 2024-03-27 exclusive, Model 1 fast screening.
Validation: 2024-03-27 through 2025-09-27, Model 4, 150 ms.
Recent retrospective confirmation: 2025-09-27 through 2026-09-27, Model 4.
The recent year and old overlapping raw windows have ALREADY been seen; none is
called untouched. Earlier transfer holdout, one final choice only:
2019-09-27 through 2021-09-27, if native history actually covers it. Missing
history blocks validation rather than silently shortening the window. Even a
pass on that older window is not future-forward evidence.

All tests: isolated portable research MT5 only, empty profile, Experts disabled,
local tester agents only, $10,000 USD, research leverage 1:2000 (not FTMO).
Broker spread/commission/swap and 150 ms delay in confirmations. Real ticks begin
January 2026; older ticks are generated. 300-day no-trade warmup; no future bars.
Private source T812/order-flow rules remain unavailable: this is our price-only
recreation, not the original author's claimed futures strategy.

## Combined Gold and sizing

Raw first-touch and retest signals share causally formed level data but retain
separate position magic numbers and independent eligibility. A first-touch entry
must not erase the subsequent retest. One position per engine by default, each
with 0.5% planned equity risk; together 1% planned, not two separate 1% budgets.
Retest remains eligible while the touch engine is busy. Pyramiding alternatives
divide each engine's allocation by its position cap. Native lot rounding UP is
preserved, so broker minimum/steps, costs and gaps can exceed planned risk.
Single-engine parity uses the original 1% risk, 1 ATR SL/TP, M5 ATR14 and 60-minute
exit. Defaults must reproduce original entries/exits before any search.

## Search design (all trials retained)

Staged beam search, keep top 3 distinct settings at each stage:
timeframe -> entry -> stop -> trailing -> RR/exit -> session -> direction ->
filters -> trade management -> level/ATR/retest parameters -> joint neighbourhood.
Because this is explicitly exploratory, negative development leaders can survive
intermediate stages; final eligibility is still positive, PF >= 1.15, >=60 trades.
Custom native score uses position-grouped net P/L including commission/swap,
trade count and return/equity drawdown, never return alone. All searched cases
are counted, including duplicates across stages (unique settings counted too).

- TF M1/M3/M5/M15/M30/H1/H4/D1. Touch stays tick-based; TF controls closed ATR,
  retest/confirmation bars. Retest expiry defaults to 6 signal bars (30 min at M5).
- Entry: original tick touch/closed retest, completed-bar confirmation, ATR/fixed
  limit retrace, stop continuation. Market-on-close and next-bar-open are the
  same executable first tick and counted as one, not duplicate evidence.
- Stops: ATR .5/.75/1/1.5/2/3/4; price .05/.1/.2%; fixed XAU 5/10/20,
  BTC 100/250/500, US30 25/50/100; signal extreme, 5-bar swing, structure +.1ATR.
- Management: none; BE .5/1/1.5R; ATR trail starts .5/1/1.5/2R at 1/1.5/2ATR;
  price-percent .05/.1/.2%; EMA20; swing5; chandelier1.5/2/3ATR;
  completed-M15 step lock (50% trigger, 20% lock, reference initial target or1R).
- RR .5/.75/1/1.25/1.5/2/2.5/3/4/5/6; no TP + ATR trail; next known level;
  session-end exit; partial50% at1R + ATR trail (if lot minimum permits).
- All hours/Asia00-08UTC/London07-16UTC/NY09:30-16 local/overlap12-16UTC/
  NYopen09:30-11 local, NY DST explicitly calculated.
- Both/long/short; none/Mon/Fri/Mon+Fri exclusions; no filter/EMA50 slope/H1EMA50
  bias/ADX14>=20/DI14 agreement/ATR20-80 percentile over100 prior bars/spread<=.1ATR.
  News blackout NOT tested: no complete point-in-time calendar for all old years.
- Max daily entries unlimited/1/2/3; cap1/2 positions per engine; repeat touches
  after stop vs first only; max hold15/30/60/120/240min/unlimited; Friday flat vs
  weekend hold; day flat vs overnight. Level masks all/prior day/Asia/London/week;
  ATR7/14/28; retest3/6/12 bars. Level formation/warmup controls remain causal.
- Neighbourhood: up to three genuinely active numeric parameters, prioritizing
  stop size, target/trail distance, pending offset, trail activation, hold time,
  retest expiry and ATR period. Perturb each by -20%/0/+20%; never count an
  inactive target, inactive retest expiry or inactive ATR period as robustness.
  Require >=2/3 positive neighbours and median PF>1, not a lone best result.

Native Model4 validation ranks eligible plateau finalists; freeze best before
recent/older checks. If validation or older holdout fails, reject, no holdout
retuning. Baseline vs final and synthetic donor control on matching windows.
Only surviving candidates continue to 10,000 block-bootstrap paths (block5),
reshuffle, missed10/20% trades, measured execution-cost stress where data exists,
and FTMO/portfolio overlays with floating-equity limitations. Missing cost or
equity data blocks claims of readiness. Never present rejected candidates as
approved deployment, and never call the search a Cartesian exhaustive optimum.

## Pre-search review correction

The initial four parity runs matched original entries, exits and volumes. Before
any search result was produced, review found that forced-flat options did not
prevent new entries after their cutoff. Version 2 uses one shared close/entry
boundary, including weekend exclusion for the Friday-flat option. Raw defaults
are unchanged. Chandelier extremes are tracked per position after entry, avoiding
the pre-entry portion of its signal candle. The initial evidence remains in native/; all authoritative runs
are repeated in native-v2/. No research result was used to choose this correction.
