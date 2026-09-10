# BTC Turn-of-the-Candle - raw MT5 results

This is an unoptimized transfer of the published one-minute timing rule to the Exness BTCUSD CFD. It adds no Calyx filters and has not been installed into the website, BAT files or recommended portfolio.

| Window | Net P/L | Return | PF | Win rate | Max DD | Trades | Avg/trade | Commission |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| paper-era-available | $-9,541.88 | -95.42% | 0.25 | 28.81% | 95.43% | 5,532 | $-1.72 | $-1,388.75 |
| latest-1y | $-8,754.62 | -87.55% | 0.78 | 49.22% | 87.59% | 35,035 | $-0.25 | $-7,367.00 |
| recent-3y | $-9,607.94 | -96.08% | 0.16 | 24.33% | 96.09% | 9,508 | $-1.01 | $-3,631.15 |
| full-5y | $-9,843.47 | -98.43% | 0.26 | 31.10% | 98.44% | 7,319 | $-1.34 | $-1,460.23 |

## Raw verdict

RAW FAIL. The published exchange anomaly does not survive current Exness BTCUSD CFD execution sufficiently to justify pipeline optimization.

The latest one-year test completed essentially the full 96-signals-per-day schedule and is the cleanest current measurement. Even if its $7,367 commission were removed, the result after spread would still be approximately -$1,387.62. The older and longer simulations depleted capital until the broker's 0.01-lot minimum prevented further entries; their lower trade counts are therefore part of the raw deployability failure, not missing history.

## Raw rules

- BTCUSD long only.
- Enter at the first available tick of minutes 00, 15, 30 and 45 of every hour.
- Exit at the first tick of the following minute, giving one M1 bar of exposure.
- Reinvest 100% of current balance as unlevered notional exposure.
- No stop, target, trend filter, volatility filter, weekday filter or session restriction.
- Native Exness spread/commission and random execution delay are included.

No production EA, website page, installer, BAT or active terminal was changed.
