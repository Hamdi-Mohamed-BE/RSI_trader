# Raw 15-minute opening-range breakout results

Stopped for review. No optimisation or live EA changes. Last completed data day: 1 October 2026.

| Asset | Window | Return | Net PF | Win rate | Native equity DD | Trades | Daily closed Sharpe | Win/loss streak |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| USTEC | 1y | -9.61% | 0.93 | 43.2% | 31.70% | 257 | -0.47 | 5/6 |
| USTEC | 3y | +13.62% | 1.03 | 44.0% | 31.76% | 772 | 0.31 | 6/8 |
| USTEC | 5y | +63.06% | 1.06 | 44.3% | 31.77% | 1285 | 0.59 | 7/9 |
| US500 | 1y | -1.89% | 0.99 | 40.9% | 19.56% | 257 | 0.02 | 5/9 |
| US500 | 3y | -22.85% | 0.93 | 39.2% | 47.89% | 770 | -0.29 | 6/15 |
| US500 | 5y | +4.10% | 1.01 | 40.2% | 49.55% | 1283 | 0.15 | 7/15 |

## Limitations

- One strategy configuration, two asset candidates, six overlapping performance runs plus a five-day implementation smoke check. No best-set selection or optimisation. Two asset candidates are conservatively counted for deflated Sharpe.
- NY 09:30–09:45 range; first subsequent completed M5 close outside range; stop opposite range boundary; no take-profit; close requested 15:55 NY. $10,000 per independent account, 1% current-balance risk target, rounded down; skip below minimum.
- Broker CFD adaptation, not broad stocks-in-play research and not exchange-volume ORB replication. Native model 4, 150ms delay, native costs; historic tick coverage is mixed as recorded below. History quality is a tester field, not proof of real ticks for the whole window.
- Daily closed-balance Sharpe annualises calendar-day realised returns at sqrt(365); not native MT5 Sharpe, floating-equity Sharpe or a forecast. Trade-net PF/win rate include entry and exit commission/swap; native floating-equity drawdown is shown separately.
- Closed-balance graphs are not floating-equity graphs. The symbols ran separately: no shared portfolio, FTMO limits, position overlap admission or payout simulation.
- The signal audit checks timestamps, NY DST, one entry/date, reported range-boundary stops, quoted risk and filled side/volume. It does not independently reconstruct every range from a second OHLC dataset.
- Five-year raw audits used 10,000 circular block-bootstrap paths, block length 5, plus deflated Sharpe with 2 asset candidates. These are resampling diagnostics, not forecasts. No separate broker-calibrated extra-cost stress or forward demo was run; missing costs were not invented. Both raw statistical screens failed.
- Timed exits can be unavailable around broker market closures. Latest-year carryovers: USTEC 15, US500 14. These trades and their costs are included, not deleted; this realised CFD implementation is not strictly flat every day. A session-aware pre-close version would be a separately frozen test after review.

## USTEC: RAW FAIL

- bootstrap_return_p05_positive
- bootstrap_pf_p05_above_1
- deflated_sharpe_95pct
- closed_pnl_total_breach_below_5pct

5y statistical screen: DSR 79.5% (gate 95%); bootstrap PF 5th percentile 0.956; bootstrap return 5th percentile -18.32%. Neither candidate meets the user's preferred PF >=1.2.

1y: 75% real ticks; costs $-304.09; carryovers 15; late exits 17; native Sharpe -1.42; flags {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "entry_fail": 0, "close_fail": 0, "stopout": 0, "start_changed": 0}.
CS	0	10:07:59.682	Ticks	USTEC : real ticks begin from 2026.01.01 00:00:00
PD	0	10:08:05.573	Core 01	USTEC : real ticks begin from 2026.01.01 00:00:00
RAWORB_SPEC symbol=USTEC digits=2 ticksize=0.01000000 tickvalue=0.01000000 lots_min=0.05000000 lots_step=0.01000000 lots_max=500.00000000 stops=0 point=0.01000000

3y: 25% real ticks; costs $-1213.64; carryovers 41; late exits 55; native Sharpe 0.81; flags {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "entry_fail": 0, "close_fail": 0, "stopout": 0, "start_changed": 0}.
CS	0	10:08:45.024	Ticks	USTEC : real ticks begin from 2026.01.01 00:00:00
DS	0	10:08:49.159	Core 01	USTEC : real ticks begin from 2026.01.01 00:00:00
RAWORB_SPEC symbol=USTEC digits=2 ticksize=0.01000000 tickvalue=0.01000000 lots_min=0.05000000 lots_step=0.01000000 lots_max=500.00000000 stops=0 point=0.01000000

5y: 15% real ticks; costs $-2729.86; carryovers 69; late exits 93; native Sharpe 2.1; flags {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "entry_fail": 0, "close_fail": 0, "stopout": 0, "start_changed": 0}.
CS	0	10:09:50.411	Ticks	USTEC : real ticks begin from 2026.01.01 00:00:00
LF	0	10:09:53.834	Core 01	USTEC : real ticks begin from 2026.01.01 00:00:00
RAWORB_SPEC symbol=USTEC digits=2 ticksize=0.01000000 tickvalue=0.01000000 lots_min=0.05000000 lots_step=0.01000000 lots_max=500.00000000 stops=0 point=0.01000000

## US500: RAW FAIL

- 3y net return is not positive
- 3y trade-net PF is not above 1
- bootstrap_return_p05_positive
- bootstrap_pf_p05_above_1
- deflated_sharpe_95pct
- closed_pnl_total_breach_below_5pct

5y statistical screen: DSR 42.5% (gate 95%); bootstrap PF 5th percentile 0.899; bootstrap return 5th percentile -52.81%. Neither candidate meets the user's preferred PF >=1.2.

1y: 75% real ticks; costs $-496.25; carryovers 14; late exits 17; native Sharpe -0.25; flags {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "entry_fail": 0, "close_fail": 0, "stopout": 0, "start_changed": 0}.
CS	0	10:11:01.127	Ticks	US500 : real ticks begin from 2026.01.01 00:00:00
PN	0	10:11:04.928	Core 01	US500 : real ticks begin from 2026.01.01 00:00:00
RAWORB_SPEC symbol=US500 digits=2 ticksize=0.01000000 tickvalue=0.01000000 lots_min=0.14000000 lots_step=0.01000000 lots_max=1000.00000000 stops=0 point=0.01000000

3y: 25% real ticks; costs $-1499.20; carryovers 35; late exits 48; native Sharpe -1.54; flags {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "entry_fail": 0, "close_fail": 0, "stopout": 0, "start_changed": 0}.
CS	0	10:11:24.824	Ticks	US500 : real ticks begin from 2026.01.01 00:00:00
QO	0	10:11:27.667	Core 01	US500 : real ticks begin from 2026.01.01 00:00:00
RAWORB_SPEC symbol=US500 digits=2 ticksize=0.01000000 tickvalue=0.01000000 lots_min=0.14000000 lots_step=0.01000000 lots_max=1000.00000000 stops=0 point=0.01000000

5y: 15% real ticks; costs $-3218.50; carryovers 49; late exits 71; native Sharpe 0.16; flags {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "entry_fail": 0, "close_fail": 0, "stopout": 0, "start_changed": 0}.
CS	0	10:12:01.498	Ticks	US500 : real ticks begin from 2026.01.01 00:00:00
RQ	0	10:12:03.902	Core 01	US500 : real ticks begin from 2026.01.01 00:00:00
RAWORB_SPEC symbol=US500 digits=2 ticksize=0.01000000 tickvalue=0.01000000 lots_min=0.14000000 lots_step=0.01000000 lots_max=1000.00000000 stops=0 point=0.01000000
