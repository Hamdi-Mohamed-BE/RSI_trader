# Asian-breakout 0.5% progression / 1.7R study

Test window: **2026-06-02 through 2026-08-02 UTC**  
Starting balance: **$1,000**  
Basket: **BTCUSD, EURJPY, GBPJPY, XAUUSD**  
Aggregate exposure cap: **6%**  
Trailing rule: activate after a closed M1 bar reaches **+1R**, trail by **1R**,
with the fixed **+1.7R hard target** retained.

| Scenario | Signals | Taken | Skipped | Win rate | Cash PF | Ending | Return | Realized DD | Stress DD | Peak planned exposure |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Flat 0.5%, fixed 1.7R | 81 | 81 | 0 | 55.56% | 1.24 | $1,036.51 | +3.65% | 3.15% | 3.74% | 2.00% |
| Flat 0.5%, trailing + 1.7R cap | 81 | 81 | 0 | 60.49% | 1.32 | $1,043.44 | +4.34% | 1.93% | 3.17% | 2.00% |
| 1.6x progression, fixed 1.7R | 81 | 81 | 0 | 55.56% | 1.15 | $1,035.31 | +3.53% | 7.36% | 11.63% | 5.32% |
| 1.6x progression, trailing + 1.7R cap | 81 | 81 | 0 | 60.49% | 1.44 | $1,082.63 | +8.26% | 3.23% | 8.42% | 5.32% |

The table uses cash-weighted PF (the unweighted R-based PF remains in
`summary.csv`). Exact cash compounding is reflected in ending balance and
drawdown. The trailing progression produced the highest
return in this sample, but used 2.66x the peak planned exposure and had roughly
1.67x the realized drawdown of flat trailing. It is therefore not enabled live
by default.

Every entry was processed in timestamp order; exits at the same timestamp
release exposure before new entries, entry ties use the frozen basket order,
and only a **closed** result changes the global loss streak. Full chronological
audits are the four scenario CSV files in this directory.
