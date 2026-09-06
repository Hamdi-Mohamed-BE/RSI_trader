# Nasdaq Overnight Negative Day EA

Symbol: Exness `USTEC`  
Chart: `M1`  
Clock: official New York cash session with automatic US daylight-saving handling

Literal research rule:

1. Compare today's 16:00 Nasdaq close with the prior trading day's 16:00 close.
2. If that close-to-close day was negative, buy USTEC just after 16:00.
3. Close at 09:29 New York time before the next regular session opens.
4. Friday signals are held to Monday unless disabled.

Risk is fixed at 1% of current equity using a 2% emergency stop. The stop is
required for deterministic position sizing; the normal exit remains the next
pre-open. Overnight gaps can still exceed the intended 1% loss.

The EA deliberately skips short/holiday sessions when fewer than 300 M1 cash
session bars are available. This avoids pretending a partial day is a normal
09:30-16:00 session.

For research, `InpNegativeDayDefinition=1` changes the signal to today's cash
open-to-close return. The saved live baseline uses the standard close-to-close
definition (`0`).

## Active recommendation (2026-09-05)

The deployed portfolio SET explicitly locks the best larger-sample configuration:

- require a negative close-to-close New York day, with a 0% threshold;
- enter at 16:00 and exit at 09:29 New York;
- allow Friday entries;
- use a 2% emergency price stop, no fixed take profit and no Dynamic 50/20 exit;
- ask for deployment risk in every BAT, defaulting to the validated 1% value.

The untouched 2025-09-01 to 2026-09-01 MT5 Every Tick test returned +8.67%
with PF 1.84, a 63.89% win rate, 2.36% maximum drawdown and 72 trades.

`CONSERVATIVE 2026-09-04 - USTEC M1 - 1pct.set` is retained as an optional
research preset. It requires a -1% day, uses a 3% emergency stop, a 0.75R
target and Dynamic 50/20. Its locked-year PF was 3.36 with 0.88% drawdown,
but return was only +4.14% across 26 trades, so it is not the active default.

The embedded Markov Safe gate was also tested natively. On the active setup it
reduced the locked-year result to +3.50% across 30 trades and produced a
negative -0.24% Monte Carlo P5 return. It is therefore disabled for this EA in
both Standard and Full Safe portfolios. The optional gate's CPU path was fixed
so its history calculation runs only after the once-per-day signal gates rather
than on every tick; this does not change Standard trades.
