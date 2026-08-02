# AMD risk progression / 1.7R study

Period: 2025-08-02T06:11:00+00:00 to 2026-08-02T06:11:00+00:00  
Broker symbol: `XAUUSD..`  
Starting balance: $1,000; base risk: 0.5%; progression: 1.6x after loss and reset after win; research progression uncapped.

| scenario | trades | win_rate_pct | profit_factor | ending_balance | return_pct | max_drawdown_pct | max_risk_used_pct |
|---|---|---|---|---|---|---|---|
| flat_fixed | 31 | 83.87096774193549 | 2.632518568397481 | 1041.5564065085393 | 4.155640650853942 | 1.4925124999999975 | 0.5 |
| flat_trailing | 31 | 83.87096774193549 | 2.7723134176066018 | 1045.207735857951 | 4.5207735857951015 | 1.4925124999999988 | 0.5 |
| progression_fixed | 31 | 83.87096774193549 | 2.039546366505014 | 1037.8884047157796 | 3.78884047157797 | 2.559411199999997 | 2.0480000000000005 |
| progression_trailing | 31 | 83.87096774193549 | 2.136976353547275 | 1041.5268753448038 | 4.15268753448037 | 2.5594112000000036 | 2.0480000000000005 |

Trailing starts at +1R, follows by 0.5R, and retains the 1.7R hard TP.
