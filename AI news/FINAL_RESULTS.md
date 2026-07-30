# Gold News AI - Initial Validation

This is a prediction-only XAUUSD research result. It does not place, modify, or
manage trades.

## Data and target

- Calendar releases: 716
- Usable releases: 699
- Supported events: NFP, GDP, CPI, PPI, and FOMC statements
- Price data: XAUUSD M1 bid/ask, 2011-07-30 through 2026-07-29
- Training: chronological expanding-window validation
- Final holdout: the latest two years, 61 clear-direction releases
- Target: direction from the final pre-release midpoint to the release M1 close
- Unclear release minutes excluded: 209

M1 history cannot establish the true first 30-second tick impulse. The included
release monitor records that information prospectively from MT5 ticks.

## Final holdout results

| Lead | Model | Threshold | Directional accuracy when called | Coverage | Calls |
|---|---|---:|---:|---:|---:|
| 15 minutes | Extra Trees | 0.55 | 55.56% | 44.26% | 27 |
| 30 minutes | Extra Trees | 0.60 | 65.38% | 42.62% | 26 |

The 30-minute model is the stronger initial default. It made a directional call
on 26 of 61 clear releases and returned `NO TRADE` on the rest.

The event-majority baseline scored 62.30% at full coverage. The 30-minute model
improved called-direction accuracy modestly by abstaining on lower-confidence
cases; it has not demonstrated a large universal edge.

## 30-minute model by event

| Event | Samples | Calls | Coverage | Directional accuracy |
|---|---:|---:|---:|---:|
| NFP | 16 | 8 | 50.00% | 62.50% |
| GDP | 3 | 0 | 0.00% | Not measurable |
| CPI | 15 | 4 | 26.67% | 50.00% |
| PPI | 14 | 8 | 57.14% | 62.50% |
| FOMC | 13 | 6 | 46.15% | 83.33% |

GDP has too few holdout samples for a useful conclusion. FOMC is promising but
still based on only six called predictions.

## Historical release-minute movement

These are USD price ranges, not broker points or guaranteed future movement.

| Event | Median | 75th percentile | Samples |
|---|---:|---:|---:|
| NFP | $6.081 | $9.384 | 150 |
| GDP | $2.771 | $4.733 | 51 |
| CPI | $2.739 | $5.271 | 149 |
| PPI | $1.534 | $3.132 | 156 |
| FOMC | $4.961 | $7.440 | 101 |

## Missing information

The archive does not contain point-in-time consensus, actual values, revisions,
DXY, Treasury yields, positioning, or complete historical ticks. The system
reports these inputs as missing instead of fabricating them. A licensed
point-in-time economic calendar feed is the most important next data upgrade.
