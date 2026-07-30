# Gold Direction Results

The production output is information only:

- `POSITIVE`: the immediate release-minute effect on XAUUSD is expected to be up.
- `NEGATIVE`: the immediate release-minute effect on XAUUSD is expected to be down.

There are no trade calls, entries, stops, targets, lots, or `NO TRADE` outputs.

## Honest frozen validation

The final T-15 model and feature choice used chronological validation ending
before 2024-07-30. The broad holdout then covered 84 releases from 2024-07-30
through 2026-05-30:

- Correct: **49 / 84**
- Accuracy: **58.33%**
- 95% Wilson interval: **47.65% to 68.29%**
- Simple event-history baseline: **58.33%**
- Pre-release momentum baseline: **48.81%**

The untouched recent window from 2026-05-30 onward contained eight releases:

- Correct: **6 / 8**
- Accuracy: **75.00%**
- 95% Wilson interval: **40.93% to 92.85%**

Recent event accuracy was CPI 2/2, PPI 2/2, NFP 1/2, and FOMC 1/2. The sample
is too small to treat 75% as a stable future rate.

## What actually improved

Changing the target from selective trade calls to a binary gold-impact forecast
removed misleading coverage statistics and scored every release. Market-only ML
did not beat the event-history anchor on the broad holdout, so the final T-15
forecast conservatively uses the historical event profile. This is simpler and
better supported by the evidence.

The T-30 research model adds prior-day broad USD, 2-year and 10-year Treasury
yields, VIX, inflation breakevens, and the effective fed funds rate. It improved
pre-holdout validation, but should not replace the final T-15 historical anchor
until a larger forward sample confirms the gain.

Complete tables are in `GOLD_DIRECTION_RESULTS.md` and
`gold_direction_backtest.json`.
