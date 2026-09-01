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
