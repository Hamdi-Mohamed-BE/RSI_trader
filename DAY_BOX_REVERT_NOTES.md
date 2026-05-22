# Day Box Revert Notes

`day box` means the Signal Pro BUY/SELL strategy module added to `MASTER_PROMPT.md` on 2026-05-20.

Snapshot file:

- `MASTER_PROMPT.day-box-enabled.snapshot.md`

If the user says `revert day box`, remove only these Signal Pro additions from `MASTER_PROMPT.md`:

- In `Deep scan`, remove:
  - `Validate Signal Pro BUY/SELL logic from the latest closed candles when enough data is available.`
- Remove the whole section:
  - `## Signal Pro BUY/SELL Strategy Rule`
  - through the line before `## RSI Divergence Rule`
- In `Trade Reflection And Continuous Improvement`, remove:
  - `Did Signal Pro confirm, conflict, or arrive too late?`
- In `A-only pre-order rule`, remove:
  - `For A/A+ grading, run the Signal Pro module when candle data is available. A fresh aligned Signal Pro marker improves confidence; a fresh opposite marker or choppy BUY/SELL flip blocks the A grade.`

Do not remove RSI divergence, BreakAndBounce, TP protection, source labels, or any trading safety rules.
