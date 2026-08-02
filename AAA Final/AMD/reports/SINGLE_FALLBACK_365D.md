# Single Cancel-and-Replace Validation

Configuration:

- `NY_ENTRY_MODE=single_fallback`
- Limit target: `5R`
- Limit active from 13:30 through 14:15 UTC
- If unfilled, cancel the limit and replace it with a breakout stop
- Breakout-stop target: `4R`
- Stop buffer: `5%` of the Asia range
- At `+0.50R`, protect at `+0.15R`
- Risk: `3%`, one active leg

| Period | Trades | Win rate | PF | Net R | Return | Realized DD | Ending balance |
|---|---:|---:|---:|---:|---:|---:|---:|
| Latest 60 days | 5 | 80.00% | 9.61 | +8.30R | +26.06% | 3.00% | $1,260.63 |
| Latest 365 days | 34 | 38.24% | 0.68 | -4.56R | -15.79% | 38.79% | $842.06 |

The PF 9.61 result is reproduced, but it comes from only five recent trades.
It does not generalize to the full year. The annual validation contains 13
wins and 21 losses; the large recent result is concentrated in July 2026.
