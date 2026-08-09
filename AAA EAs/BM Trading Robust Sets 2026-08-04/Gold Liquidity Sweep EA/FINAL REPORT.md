# Gold Liquidity Sweep EA — honest validation report

## Verdict: REJECTED

The mechanical version of the supplied video strategy is not valid for the synchronized live EA portfolio. It failed both the Jan-Aug 2025 selection slice and the locked last year, and the continuous 2022-2026 test was also negative. The BAT installer and active portfolio were not changed.

## Test protocol

- Broker/history: Exness `Exness-MT5Trial16`, XAUUSD
- Initial balance: USD 10,000 per independent test
- Risk: 1.00% of current equity per trade
- Engine: MT5 Every Tick with random execution delay
- Chart: M5; H1 and M15 confirmed swing-structure alignment
- Permanent hard stop; maximum two entries per UTC day; three-hour time exit
- Acceptance gate: positive locked-final return, PF at least 1.15, equity DD no more than 12%, and at least 20 final trades

## Development variants, 2022-01-03 through 2024-12-31

| Variant | Return | Max equity DD | PF | Win rate | Trades |
|---|---:|---:|---:|---:|---:|
| aggressive-core | +1.48% | 4.81% | 1.14 | 42.11% | 19 |
| aggressive-core-loose | -3.07% | 7.07% | 0.84 | 33.33% | 30 |
| aggressive-all | -4.02% | 14.31% | 0.84 | 34.15% | 41 |
| aggressive-ny | -4.12% | 5.48% | 0.43 | 27.27% | 11 |
| aggressive-all-loose | -6.97% | 15.28% | 0.81 | 31.58% | 57 |

Only `aggressive-core` was positive in development, but +1.48% from only 19 trades over three years was already insufficient evidence. It was nevertheless locked before the later tests and carried forward without retuning.

## Locked checks

Cells show return / max equity DD / PF / trades.

| Period | Result | Decision |
|---|---:|---|
| Jan-Aug 2025 selection | -1.08% / 4.09% / 0.79 / 7 | Fail |
| 2025-08-07 to 2026-08-06 final | -2.93% / 5.37% / 0.58 / 9 | Fail |
| Continuous 2022-01-03 to 2026-08-06 | -2.53% / 5.42% / 0.89 / 35 | Fail |

## Continuous-test trade statistics

- Final balance: $9,747.42; net: $-252.58
- Gross profit / loss: $2,021.65 / $-2,274.23
- Wins / losses: 12 / 23 (34.29% win rate)
- Largest win / loss: $273.58 / $-102.41
- Average win / loss: $168.47 / $-94.89
- Balance max DD: $513.29 (5.00%)
- Recovery / Sharpe: -0.45 / -5.00
- History quality: 98%

## Transcript fidelity and limitation

The EA mechanizes H1/M15 trend alignment, M15 displacement-created supply/demand zones, M5 sweep-and-reclaim entries, nearest M15 swing targets, and protected-candle stops. The video does not give objective formulas for drawing zones or market structure, and one showcased trade removes its stop based on gut feeling. That discretionary stop removal was deliberately excluded. The claimed USD 566,000 from two trades is not evidence of repeatable percentage performance because the account size, exposure and complete trade population are not supplied.

## Files

- `Gold Liquidity Sweep EA.mq5/.ex5`: compiled research EA
- `Best Settings/REJECTED - XAUUSD M5 - Gold Liquidity Sweep - 1pct.set`: disabled rejected preset for audit only
- `Reports`: native MT5 reports and equity graphs
- `STRATEGY TRANSLATION.md`: exact mechanical translation and limitations
