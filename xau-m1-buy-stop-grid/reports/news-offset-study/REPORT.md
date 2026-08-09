# XAU news-event stop-offset study

Study range: **2021-08-07 through 2026-08-07**. Main-move horizon: **30 minutes**.

## Method

- Anchor: last available bid/ask close immediately before the official release.
- Direction: sign of the bid/ask midpoint at the end of the horizon versus the anchor midpoint.
- Correct move: maximum executable stop-trigger excursion in that final direction.
- Fakeout: maximum opposite executable stop-trigger excursion before or during the M1 bar containing the correct extreme.
- Same-bar ordering is conservative: the wrong side is assumed to occur first.
- Best robust offset: first $0.50 increment strictly above the historical 95th-percentile fakeout.
- Sample-safe offset: first $0.50 increment strictly above the largest fakeout in this sample; not a future guarantee.

## Results

| Event | N | Fake min | Fake avg | Fake p95 | Fake max | Correct min | Correct avg | Correct max | Robust offset | Capture | False-first | Sample-safe | Safe capture |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| NFP | 57 | $0.00 | $2.93 | $13.41 | $16.74 | $2.49 | $18.20 | $74.27 | $13.50 | 52.63% | 5.26% | $17.00 | 40.35% |
| CPI | 59 | $0.00 | $3.63 | $11.12 | $19.99 | $2.66 | $16.66 | $76.02 | $11.50 | 61.02% | 5.08% | $20.00 | 28.81% |
| PPI | 59 | $0.00 | $2.88 | $7.83 | $19.00 | $1.54 | $8.74 | $34.03 | $8.00 | 38.98% | 5.08% | $19.50 | 6.78% |
| GDP | 19 | $0.00 | $2.97 | $7.35 | $10.59 | $3.99 | $10.74 | $20.11 | $7.50 | 73.68% | 5.26% | $11.00 | 42.11% |
| FOMC | 40 | $0.00 | $3.22 | $10.68 | $12.59 | $3.68 | $15.21 | $102.68 | $11.00 | 55.00% | 5.00% | $13.00 | 42.50% |
| ALL | 234 | $0.00 | $3.15 | $10.74 | $19.99 | $1.54 | $14.31 | $102.68 | $11.00 | 49.15% | 4.70% | $20.00 | 20.51% |

Skipped events: 2

- 2023-04-07T12:30:00+00:00 NFP: insufficient bars
- 2026-04-03T12:30:00+00:00 NFP: insufficient bars

## Interpretation

The robust offset is the practical research choice, not a promise of safety. The sample-safe offset avoids every measured pre-main-move fakeout in this dataset but can miss many correct moves. Gaps, slippage, spread expansion, and sub-minute path ordering remain live risks.
