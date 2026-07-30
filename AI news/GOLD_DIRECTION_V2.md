# Gold Direction Model V2

This predicts information only: **POSITIVE** or **NEGATIVE** immediate impact on gold. It does not generate trades.

## Validated result

- V2: **143/234 (61.11%)**
- Previous event-history baseline: **132/234 (56.41%)**
- V2 95% interval: **54.73% to 67.13%**
- Broad guard 2021-2024: **59.15%**
- Untouched recent test 2024-2026: **64.13%**
- Last two months: **75.00%**

## Production policy

| Event | Rule | Events | Correct | Accuracy |
|---|---|---:|---:|---:|
| NFP | inverse_last | 57 | 35 | 61.40% |
| GDP | event_history | 19 | 12 | 63.16% |
| CPI | event_history | 59 | 38 | 64.41% |
| PPI | event_history | 59 | 32 | 54.24% |
| FOMC | inverse_majority_5 | 40 | 26 | 65.00% |

## Interpretation

NFP uses the opposite of its previous release-minute direction. FOMC uses the opposite of the majority of its last five releases. GDP, CPI, and PPI retain their expanding event-history bias.

The five-minute follow-through score is reported separately and does not alter the immediate-direction target.
