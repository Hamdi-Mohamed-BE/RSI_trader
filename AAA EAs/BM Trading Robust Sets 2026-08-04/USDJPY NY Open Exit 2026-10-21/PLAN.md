# USDJPY NY Open Exit 2026-10-21 — plan (written before any result)

Owner question: close USDJPY London Open Momentum trades at the New York open instead of the current exit; show results
versus the current version.

Current version (Current14 ORB05 / Best Prop inputs): entry after the 08:00–08:30 London formation, ADX20 + DI ON, 5 ATR
stop, NO target (InpTargetMode=0 time exit), break-even at 0.75R, time exit InpExitLondonHour=16.0 (16:00 London, minus 30 s).
The EA keeps London local time with UK DST; it has no New York clock. "New York open" has two common meanings, both tested:
- NY FX open 08:00 New York  -> InpExitLondonHour = 13.0
- NY equity open 09:30 New York -> InpExitLondonHour = 14.5
Input-only changes (deployable without code). In the ~3 weeks a year when US and UK DST differ (March / late Oct–early
Nov), these London times are one hour AFTER the NY open; affected trades are counted and reported.

Evidence: native MT5 Model 4, 150 ms, $10k, 1% risk, 2021-10-06 -> 2026-10-06, isolated tester, same audited runner as
`Negative RR Study 2026-10-21`. Current = that study's fresh USDJPY baseline (same tester state, run 2026-10-21).
Windows (data_split.py): development 2021-10-06 -> 2023-10-06, validation -> 2024-10-06, OOS -> 2026-10-06, plus 5 years.
Metrics: trades, trades/month, trades/day, win rate, PF, average R, return, closed DD, native 5y equity DD, exit mix,
average holding time. Both variants reported; nothing selected or tuned. No SET/BAT/live change, no push.
