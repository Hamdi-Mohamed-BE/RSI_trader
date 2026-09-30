# Conditional USDJPY survivor search

This branch may run only after the parent frozen numeric raw gate passes. It is not
a way to optimize the three failed strategies. It creates no production EA.

The original raw handler is preserved verbatim through an include. First confirm both
the default-off route and the extended engine with raw settings against the original
one-year native trades. Stop the search on parity failure.

Freeze development 2021-09-27 to 2024-03-27; validation 2024-03-27 to 2025-09-27.
The inspected last year is retrospective confirmation only. Historical holdout is
2020-09-27 to 2021-09-27: earlier history is unavailable for part of 2019, so this is
the reserved available full year, chosen before ANY optimization. Test this ONCE on
the final validation-selected candidate. A failed holdout is not a retuning opportunity.

Use Model 1 staged search and native Model 4 / 150 ms finalists. Do not tune risk:
all discovery uses raw 1% equity upward-rounded lots. Final risk assessment must use
downward rounding and target-broker margin separately.

Timeframes jointly seeded with candle entries: M1/M3/M5/M15/M30/H1/H4. A D1 signal
cannot complete after a same-day range and before its same-day exit, so D1 excluded.
The original pending-entry / structure-stop version has no signal-timeframe dependence;
do not treat identical timeframe-only results as independent evidence.

Search entries: pending breakout, completed-bar market entry (the next available tick,
so separate 'next bar' is a duplicate), two-close confirmation, fixed 10-point and
0.25 ATR retest limits. Search stops: opposite range, ATR .5/.75/1/1.5/2/3/4,
100/300/600 points, .05/.1/.2% price, signal candle, last five-bar swing.
Search management: none, BE .5/1/1.5R; ATR trailing 1/1.5/2 ATR starting .5/1/1.5/2R;
percentage .05/.1/.2; EMA50, five-bar swing, chandelier 1.5/2/3 ATR, step-lock .5/.2R.
Trailing updates once per completed signal-timeframe bar. Never loosen a stop.
Search fixed TP .5/.75/1/1.25/1.5/2/2.5/3/4/5/6R, no target + trail,
prior-day directional extreme, session-only, and 50% at 1R + trail (2R final TP).

Session candidates use the declared synthetic broker clock (NY+7): range/flat
00:00–03:00/11:00, 03:00–06:00/18:00 raw, 07:00–10:00/18:00,
10:00–13:00/20:00, 13:00–16:00/22:00, and 15:00–16:30/22:00.
These are shifted range hypotheses, not a claim to reproduce each exchange opening.
Both/long/short; no filter, EMA50 slope, H1 EMA50 bias, ADX>=20, DI alignment,
spread<=10% ATR; omit Monday/Friday/both; one/two/three entries with SL reentry;
12/24/48-bar max hold. Also test entry buffer 0/.1/.25 ATR and range durations
120/180/240 minutes where valid. No pyramiding: this hypothesis is OCO one-position
breakout, and overlapping baskets are a materially different strategy. No weekend
hold: intraday hypothesis. No point-in-time news/volatility-regime overlay because no
complete frozen matched history was supplied for those extra hypotheses.

Keep the best three development candidates per stage by the same frozen score:
min(net PF,3)*sqrt(position count/100)*(return fraction)/(.05+equity DD fraction).
Reject <60 positions, non-positive net or PF<=1. Count and preserve ALL trials,
including parity and diagnostic runs separately. Development score is based on net
position P&L including commissions/swaps; partial deals aggregate by position.

Joint neighborhood: shift range end ±30 minutes (same duration), exit ±30 minutes,
and active exit RR ±.25 or trailing distance ±20%. Require >=2/3 profitable neighbors
and median PF>1; a single peak is insufficient. Validate the best three plateau
candidates, rank using the same score with >=30 positions, then freeze one. If none
survives, stop. One-time historical holdout requires net>0, net PF>=1.0 and >=30 trades.
No survivor means no FTMO promotion, no optimization of rejected baselines, no claim
of a fully passed pipeline. Later Monte Carlo/cost/FTMO gates remain mandatory.
