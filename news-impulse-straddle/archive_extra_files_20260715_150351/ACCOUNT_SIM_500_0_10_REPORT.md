# Account Simulation: $500 Start, 0.10 Lot

Strategy:

- XAUUSDm only
- Buffer: `$5` beyond last closed M1 high/low
- SL room: opposite side + `$10` extra
- Trailing starts at `+3R`
- Trail distance: `1R`
- Max hold: `120 minutes`
- Events: CPI / NFP / FOMC / PCE

## Result

- Starting balance: `$500.00`
- Final balance: `$3,292.24`
- Net profit: `$2,792.24`
- Return: `558.4%`
- Max drawdown: `$265.48`
- Ruined / balance <= 0: `False`

## Trade path

| event                 | type   | status     | side   |         r |   risk_usd_0_10 |   pnl_usd_0_10 |   balance_before |   balance_after |   drawdown_from_peak |
|:----------------------|:-------|:-----------|:-------|----------:|----------------:|---------------:|-----------------:|----------------:|---------------------:|
| Apr 29 FOMC Statement | FOMC   | timeout    | sell   | -0.386452 |          195.6  |         -75.59 |           500    |          424.41 |                75.59 |
| May 08 NFP / Jobs     | NFP    | loss       | sell   | -1        |          189.89 |        -189.89 |           424.41 |          234.52 |               265.48 |
| May 12 CPI            | CPI    | no_trigger |        |  0        |            0    |           0    |           234.52 |          234.52 |               265.48 |
| May 20 FOMC Minutes   | FOMC   | no_trigger |        |  0        |            0    |           0    |           234.52 |          234.52 |               265.48 |
| May 29 PCE            | PCE    | no_trigger |        |  0        |            0    |           0    |           234.52 |          234.52 |               265.48 |
| Jun 05 NFP / Jobs     | NFP    | timeout    | sell   |  4.84235  |          194.16 |         940.19 |           234.52 |         1174.71 |                 0    |
| Jun 10 CPI            | CPI    | timeout    | buy    |  0.751859 |          220.52 |         165.8  |          1174.71 |         1340.51 |                 0    |
| Jun 17 FOMC Statement | FOMC   | trail_exit | sell   |  3.60571  |          183.75 |         662.55 |          1340.51 |         2003.06 |                 0    |
| Jun 25 PCE            | PCE    | timeout    | buy    |  1.48918  |          224.5  |         334.32 |          2003.06 |         2337.38 |                 0    |
| Jul 02 NFP / Jobs     | NFP    | trail_exit | buy    |  2.49703  |          195.52 |         488.22 |          2337.38 |         2825.6  |                 0    |
| Jul 08 FOMC Minutes   | FOMC   | no_trigger |        |  0        |            0    |           0    |          2825.6  |         2825.6  |                 0    |
| Jul 14 CPI            | CPI    | trail_exit | buy    |  2.38009  |          196.06 |         466.64 |          2825.6  |         3292.24 |                 0    |