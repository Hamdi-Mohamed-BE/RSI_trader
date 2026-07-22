# Last 12 Months Account Simulation: $500 Start, 0.10 Lot

Strategy: XAU news straddle trailing runner.

- Events listed: `56`
- Events with no MT5 data: `1`
- Trades taken: `26`
- Wins: `14`
- Losses: `12`
- Win rate: `53.8%`
- Starting balance: `$500.00`
- Final balance: `$4,118.97`
- Net: `$3,618.97`
- Return: `723.8%`
- Max drawdown: `$628.85`
- Min balance: `$453.43`
- Account below zero: `False`

## Trade path

| event                      | type   | status                   | side   |           r |      best_r |   risk_usd_0_10 |   pnl_usd_0_10 |   balance_before |   balance_after |   drawdown_from_peak |
|:---------------------------|:-------|:-------------------------|:-------|------------:|------------:|----------------:|---------------:|-----------------:|----------------:|---------------------:|
| Jul 30 2025 FOMC Statement | FOMC   | no_trigger               |        |   0         |             |            0    |           0    |           500    |          500    |                 0    |
| Jul 31 2025 PCE            | PCE    | no_trigger               |        |   0         |             |            0    |           0    |           500    |          500    |                 0    |
| Aug 01 2025 NFP / Jobs     | NFP    | timeout                  | buy    |   2.00444   |   2.58121   |          182.55 |         365.91 |           500    |          865.91 |                 0    |
| Aug 12 2025 CPI            | CPI    | timeout                  | buy    |  -0.695618  |   0.55467   |          190.78 |        -132.71 |           865.91 |          733.2  |               132.71 |
| Aug 20 2025 FOMC Minutes   | FOMC   | no_trigger               |        |   0         |             |            0    |           0    |           733.2  |          733.2  |               132.71 |
| Aug 29 2025 PCE            | PCE    | no_trigger               |        |   0         |             |            0    |           0    |           733.2  |          733.2  |               132.71 |
| Sep 05 2025 NFP / Jobs     | NFP    | timeout                  | buy    |   1.19563   |   1.93978   |          193.78 |         231.69 |           733.2  |          964.89 |                 0    |
| Sep 11 2025 CPI            | CPI    | both_sides_same_bar_skip |        |   0         |             |            0    |           0    |           964.89 |          964.89 |                 0    |
| Sep 17 2025 FOMC Statement | FOMC   | both_sides_same_bar_skip |        |   0         |             |            0    |           0    |           964.89 |          964.89 |                 0    |
| Sep 26 2025 PCE            | PCE    | no_trigger               |        |   0         |             |            0    |           0    |           964.89 |          964.89 |                 0    |
| Oct 03 2025 NFP / Jobs     | NFP    | no_trigger               |        |   0         |             |            0    |           0    |           964.89 |          964.89 |                 0    |
| Oct 08 2025 FOMC Minutes   | FOMC   | no_trigger               |        |   0         |             |            0    |           0    |           964.89 |          964.89 |                 0    |
| Oct 15 2025 CPI            | CPI    | no_trigger               |        |   0         |             |            0    |           0    |           964.89 |          964.89 |                 0    |
| Oct 29 2025 FOMC Statement | FOMC   | loss                     | sell   |  -1         |   0.505417  |          181.83 |        -181.83 |           964.89 |          783.06 |               181.83 |
| Oct 31 2025 PCE            | PCE    | no_trigger               |        |   0         |             |            0    |           0    |           783.06 |          783.06 |               181.83 |
| Nov 07 2025 NFP / Jobs     | NFP    | no_trigger               |        |   0         |             |            0    |           0    |           783.06 |          783.06 |               181.83 |
| Nov 13 2025 CPI            | CPI    | no_trigger               |        |   0         |             |            0    |           0    |           783.06 |          783.06 |               181.83 |
| Nov 19 2025 FOMC Minutes   | FOMC   | timeout                  | sell   |   0.319655  |   0.620309  |          191.05 |          61.07 |           783.06 |          844.13 |               120.76 |
| Nov 26 2025 PCE            | PCE    | timeout                  | sell   |  -0.0530196 |   1.23008   |          184.46 |          -9.78 |           844.13 |          834.35 |               130.54 |
| Dec 05 2025 NFP / Jobs     | NFP    | no_trigger               |        |   0         |             |            0    |           0    |           834.35 |          834.35 |               130.54 |
| Dec 10 2025 CPI            | CPI    | no_trigger               |        |   0         |             |            0    |           0    |           834.35 |          834.35 |               130.54 |
| Dec 10 2025 FOMC Statement | FOMC   | loss                     | buy    |  -1         |   1.01347   |          178.23 |        -178.23 |           834.35 |          656.12 |               308.77 |
| Dec 23 2025 PCE            | PCE    | no_trigger               |        |   0         |             |            0    |           0    |           656.12 |          656.12 |               308.77 |
| Jan 07 2026 FOMC Minutes   | FOMC   | no_trigger               |        |   0         |             |            0    |           0    |           656.12 |          656.12 |               308.77 |
| Jan 09 2026 NFP / Jobs     | NFP    | loss                     | sell   |  -1         |   0.288618  |          202.69 |        -202.69 |           656.12 |          453.43 |               511.46 |
| Jan 13 2026 CPI            | CPI    | timeout                  | buy    |   0.0302873 |   1.32374   |          193.15 |           5.85 |           453.43 |          459.28 |               505.61 |
| Jan 28 2026 FOMC Statement | FOMC   | trail_exit               | buy    |   4.1844    |   5.1844    |          206.13 |         862.53 |           459.28 |         1321.81 |                 0    |
| Jan 30 2026 PCE / PPI      | PCE    | loss                     | sell   |  -1         |   0.329027  |          276.33 |        -276.33 |          1321.81 |         1045.48 |               276.33 |
| Feb 11 2026 NFP / Jobs     | NFP    | timeout                  | sell   |   1.31004   |   2.67978   |          220.1  |         288.34 |          1045.48 |         1333.82 |                 0    |
| Feb 13 2026 CPI            | CPI    | timeout                  | buy    |   1.90708   |   2.00487   |          186.82 |         356.28 |          1333.82 |         1690.1  |                 0    |
| Feb 18 2026 FOMC Minutes   | FOMC   | loss                     | buy    |  -1         |   0.249719  |          178    |        -178    |          1690.1  |         1512.1  |               178    |
| Feb 27 2026 PPI / PCE      | PCE    | timeout                  | sell   |  -0.274323  |   0.863974  |          229    |         -62.82 |          1512.1  |         1449.28 |               240.82 |
| Mar 11 2026 CPI            | CPI    | loss                     | buy    |  -1         |   0.0038355 |          187.72 |        -187.72 |          1449.28 |         1261.56 |               428.54 |
| Mar 18 2026 PPI / FOMC     | FOMC   | loss                     | buy    |  -1         |   0.0379774 |          186.69 |        -186.69 |          1261.56 |         1074.87 |               615.23 |
| Apr 03 2026 NFP / Jobs     | NFP    | no_data                  | nan    | nan         | nan         |          nan    |         nan    |           nan    |         1074.87 |               nan    |
| Apr 10 2026 CPI            | CPI    | timeout                  | buy    |   1.2902    |   1.31469   |          195.21 |         251.86 |          1074.87 |         1326.73 |               363.37 |
| Apr 29 2026 FOMC Statement | FOMC   | timeout                  | sell   |  -0.386452  |   1.03308   |          195.6  |         -75.59 |          1326.73 |         1251.14 |               438.96 |
| May 08 2026 NFP / Jobs     | NFP    | loss                     | sell   |  -1         |   0.0141661 |          189.89 |        -189.89 |          1251.14 |         1061.25 |               628.85 |
| May 12 2026 CPI            | CPI    | no_trigger               |        |   0         |             |            0    |           0    |          1061.25 |         1061.25 |               628.85 |
| May 20 2026 FOMC Minutes   | FOMC   | no_trigger               |        |   0         |             |            0    |           0    |          1061.25 |         1061.25 |               628.85 |
| May 29 2026 PCE            | PCE    | no_trigger               |        |   0         |             |            0    |           0    |          1061.25 |         1061.25 |               628.85 |
| Jun 05 2026 NFP / Jobs     | NFP    | timeout                  | sell   |   4.84235   |   5.30161   |          194.16 |         940.19 |          1061.25 |         2001.44 |                 0    |
| Jun 10 2026 CPI            | CPI    | timeout                  | buy    |   0.751859  |   1.87529   |          220.52 |         165.8  |          2001.44 |         2167.24 |                 0    |
| Jun 17 2026 FOMC Statement | FOMC   | trail_exit               | sell   |   3.60571   |   4.60571   |          183.75 |         662.55 |          2167.24 |         2829.79 |                 0    |
| Jun 25 2026 PCE            | PCE    | timeout                  | buy    |   1.48918   |   1.92748   |          224.5  |         334.32 |          2829.79 |         3164.11 |                 0    |
| Jul 02 2026 NFP / Jobs     | NFP    | trail_exit               | buy    |   2.49703   |   3.49703   |          195.52 |         488.22 |          3164.11 |         3652.33 |                 0    |
| Jul 08 2026 FOMC Minutes   | FOMC   | no_trigger               |        |   0         |             |            0    |           0    |          3652.33 |         3652.33 |                 0    |
| Jul 14 2026 CPI            | CPI    | trail_exit               | buy    |   2.38009   |   3.38009   |          196.06 |         466.64 |          3652.33 |         4118.97 |                 0    |