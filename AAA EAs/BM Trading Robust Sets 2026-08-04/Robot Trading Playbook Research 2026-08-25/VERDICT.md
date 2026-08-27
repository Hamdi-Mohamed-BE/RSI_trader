# Robot Trading Playbook EA — validation verdict

## Decision

**Rejected for the active BAT portfolio.** The objective XAUUSD M30 translation did not reproduce the transcript's claimed 80%+ win rate and failed its locked final-year validation.

## Test design

- Broker/data: Exness MT5, XAUUSD.
- Account: USD 10,000, 1% equity risk per filled trade.
- Costs: broker spread, commission, swap and random execution delay included by MT5.
- Training: 2021-08-11 to 2025-08-10, one-minute OHLC screen.
- Locked validation: 2025-08-11 to 2026-08-10, MT5 every-tick modelling, 99% history quality.
- No locked-period result was used to select or change the preset.

## Training results

The complete transcript translation was essentially flat at **-0.67%**, PF **1.00**, win rate **43.47%**, max equity drawdown **35.42%**, across **1,102 trades**.

The only mildly positive isolated family was the higher-timeframe-aligned fakeout reclaim:

| Period | Return | PF | Win rate | Max equity DD | Trades |
|---|---:|---:|---:|---:|---:|
| Training, 2021-08-11 to 2025-08-10 | +6.49% | 1.05 | 44.44% | 9.33% | 216 |

## Locked one-year result

| Initial | Final | Net | Return | PF | Win rate | Max equity DD | Trades |
|---:|---:|---:|---:|---:|---:|---:|---:|
| $10,000.00 | $8,962.92 | -$1,037.08 | -10.37% | 0.50 | 28.57% | 14.28% | 35 |

Additional locked statistics: 10 wins / 25 losses, gross profit $1,054.79, gross loss -$2,091.87, commission -$13.24, swap -$23.05, largest win $144.98, largest loss -$105.32, average win $105.48 and average loss -$83.15.

## Interpretation

The general concepts—breakout, hold/retest and failed-break reclaim—can be automated only after defining structure and entries mathematically. Under fixed, non-look-ahead definitions, however, the strategy had no robust edge. The discretionary video may rely on unspoken chart selection and judgement that cannot be reproduced from the transcript alone.

The EA, source, reproducible scripts, SET file and native MT5 reports remain in this research folder, but nothing was added to the active installer or website.
