# US100 hourly raw test

Primary result: 11:00–12:00 New York is weakly profitable, not a validated edge.

Exness USTEC CFD; 2021-10-02 to 2026-10-02 exclusive. Fixed 1 lot, $10,000. No stop-loss. Native Model 4, 150ms. No live changes.

| Window | Return | PF | Win rate | Max equity DD | Trades | Daily Sharpe | Max W/L |
|---|---:|---:|---:|---:|---:|---:|---:|
|5y|11.87%|1.037|52.76%|15.28%|1287|0.20|12/13|
|first3y|1.85%|1.011|52.13%|15.28%|773|0.06|9/13|
|last2y|10.02%|1.067|53.70%|14.48%|514|0.35|12/6|
|1y|4.90%|1.055|53.49%|12.89%|258|0.29|5/6|
|6m|4.19%|1.090|53.08%|12.98%|130|0.50|5/5|
|3m|6.33%|1.302|50.00%|5.38%|66|1.65|4/5|

## Random comparison and hour search

The 11:00 bar-price edge over matched random is 3.36 points/hold. Its 95% five-date-block interval is [-0.30, 6.89]. Raw one-sided p=0.0309; adjusted max-T p=0.5271 across 22 hours. No hour survives the familywise 5% test. The descriptive leader is 13:00, not 11:00, with 1.81 points/hold and PF 1.088. These p-values are from the bar approximation, not native tick execution.

## Limits

Broker sessions and incomplete 60-minute windows leave 22 eligible hourly starts, not the video’s 23 NQ hours; 16:00 and 17:00 are unavailable under the frozen completeness rule. The random control uses the same date as each target trade, not freely selected dates. Overnight financing is omitted in the all-hour screen; UTC-midnight-crossing hours are flagged. Most older native data are generated ticks: only 15% real ticks across five years. Historical spread drops substantially in recent M1 data; native primary results include actual tester quotes, charged commission and execution delay. There is no SL, risk-% sizing, daily cap, portfolio simulation or live-account recommendation. Daily Sharpe is computed consistently from realised net daily cash changes including nontrade weekdays; it is not the MT5 report’s Sharpe calculation. Win rate and PF are recomputed from net closed deals; MT5’s gross Profit Trades count can differ when commission turns a flat or small positive trade into a loss.

## Execution reconciliation

- 5y: native commission $-810.81, swap $0.00; 21.45 trades/month, 0.987/weekday.
- first3y: native commission $-486.99, swap $0.00; 21.47 trades/month, 0.988/weekday.
- last2y: native commission $-323.82, swap $0.00; 21.43 trades/month, 0.985/weekday.
- 1y: native commission $-162.54, swap $0.00; 21.51 trades/month, 0.989/weekday.
- 6m: native commission $-81.90, swap $0.00; 21.62 trades/month, 0.992/weekday.
- 3m: native commission $-41.58, swap $0.00; 21.84 trades/month, 1.000/weekday.

## Decision

Stop for user review. No full pipeline, filter optimisation, production files, BATs or active account changed. ADX/DI scope next: shortlist only strategies for which trend strength, trend-direction agreement or low-trend regime has a testable rationale; preserve their current baseline and distinguish last 3/6/12 months from longer validation.