# Nasdaq Overnight Negative Day EA — Exness USTEC

## Final strategy

- Chart: USTEC M1
- Entry: buy just after 16:00 New York time when today's regular-session close is below the prior trading day's regular-session close
- Exit: 09:29 New York time before the next cash open
- Risk: 1% of current equity at a 2% emergency stop
- Friday: enabled; Friday positions are held to Monday pre-open
- Initial test balance: USD 10,000
- Leverage: 1:2000
- Execution: random delay
- Model: every tick from Exness history

## Honest results

| Period | Quality | Net profit | Return | Max equity DD | PF | Win rate | Trades |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2025-08-05 to 2026-08-04 | 100% | +$792.56 | +7.93% | 2.39% ($260.91) | 1.86 | 59.15% | 71 |
| 2023-08-05 to 2026-08-04 | 98% | +$729.94 | +7.30% total | 4.86% ($500.60) | 1.28 | 56.07% | 173 |

The recent year was materially stronger than the full three-year sample. This
is a positive backtest, not proof of a permanent edge or a profit guarantee.
Overnight gaps may exceed the emergency stop and the intended 1% loss.

The EA is installed separately for research. It is not enabled by the strict
portfolio BAT because its return is below the previously agreed +20% inclusion
gate.
