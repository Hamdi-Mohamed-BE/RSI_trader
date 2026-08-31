# Statistical Triple Print EA — one-year MT5 audit

This is a mechanical reconstruction of the supplied transcript, not the speaker's undisclosed proprietary model.
Tests use Exness MT5 Every Tick modelling, broker spread, random execution delay, commission and swaps where charged.

| Symbol | Profile | Return | PF | Win rate | Max equity DD | Trades |
|---|---:|---:|---:|---:|---:|---:|
| BTCUSD | normal | +20.15% | 1.18 | 44.03% | 9.01% | 243 |
| BTCUSD | prop | +5.58% | 1.24 | 45.95% | 2.46% | 185 |
| US30 | normal | -1.62% | 0.99 | 40.07% | 23.33% | 307 |
| US30 | prop | +1.33% | 1.04 | 42.58% | 7.03% | 209 |
| USTEC | normal | +1.90% | 1.01 | 42.36% | 12.73% | 288 |
| USTEC | prop | +2.99% | 1.08 | 44.55% | 5.04% | 211 |
| XAUUSD | normal | +11.93% | 1.14 | 44.13% | 11.16% | 213 |
| XAUUSD | prop | +3.10% | 1.23 | 48.72% | 5.07% | 117 |

## Profile rules

- Normal: 1% equity risk, 2 trades/day, 2R target.
- Prop: 0.35% equity risk, 1 trade/day, 1.5R target, 1% daily equity-loss lock, 5% overall equity guard, flat after the trading window and before the weekend.
- Both: M15 body-close structure breakout, three valid countertrend candles, ATR displacement and wick-gap filters, spread guard, fixed stop and no martingale/grid.

Combined chart: `EQUITY CURVES - NORMAL VS PROP.png`
