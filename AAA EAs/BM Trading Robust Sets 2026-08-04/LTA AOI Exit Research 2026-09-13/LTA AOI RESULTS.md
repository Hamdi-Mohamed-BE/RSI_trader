# LTA XAUUSD — fixed 3R versus volume-profile exits

## Conclusion

**Keep the current 3R preset for now. Do not deploy the no-TP rolling trail on this evidence.**
The rolling no-TP exit preserved entry logic but reduced return and increased equity drawdown versus 3R over every tested period. Previous-week targets improved 6m and 3y returns but did not beat the 5y control and carried substantially higher 5y drawdown. Nearest-level exits increased win rate at the cost of much smaller average wins; higher hit rate was not an overall improvement.
Weekly AOI targets may merit a separately approved minimum-R / hybrid-exit experiment, but no such improvement was optimized or validated here. The frozen no-TP diagnostic is unsuitable as a deployment candidate because of sparse trades, large drawdowns and boundary-exit dependence.

Research comparison only. Nothing deployed and no website/BAT changes. Exness Zero demo feed, XAUUSD M15, $10,000 initial USD, 1% equity sizing using the current round-up/min-lot rule. Safe filter ON; account-wide adaptive overlay OFF for this standalone exit comparison. Original entries and initial stops preserved. All standard windows end 2026-09-05 exclusive.

Net P/L, win rate and profit factor include all recorded commissions, swap and fees. Drawdown below is the larger of native MT5 maximum relative equity drawdown and the independent every-tick observer. It is not closed-balance drawdown.

The user-confirmed no-TP candidate is **Rolling AOI trail**. Frozen AOI trail is an extra diagnostic, not the recommended implementation. Both keep the same original LTA entry logic. Fewer trades can result from the unchanged one-position-per-symbol rule while an earlier position remains open.

## Rules

- Current: fixed 3R target.
- Day/week/combined TP: nearest favorable POC, VAH or VAL from the specified completed profile(s). If none is ahead, use original 3R, with fallback counts disclosed. No minimum-R filter was optimized.
- Frozen trail: no TP; both profiles frozen at entry. A completed M15 close must cross beyond a favorable rung plus the fixed 0.05-entry-ATR buffer. SL moves one rung behind, buffered, and only tightens.
- Rolling trail: same, but loads newly completed day/week profiles for subsequent candles. It never applies a newly calculated profile retroactively.
- TP profile windows exclude the first bar of the current day/week; existing entry-profile boundary semantics are unchanged across every case. 64 bins / 70% value area. Broker tick volume when real volume is unavailable.

See [frozen protocol](RULES.md) for complete rules, scope, fallback behavior, date boundaries and limitations.

## 6m — 2026.03.05 to 2026.09.05

| Exit | Net P/L | Return | Final balance | Trades | Net win rate | Net PF | Max equity DD | Commission | Swap |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Current 3R | $2,910.58 | +29.11% | $12,910.58 | 108 | 31.48% | 1.304 | 9.86% | −$59.66 | −$12.82 |
| Previous-day TP | $665.20 | +6.65% | $10,665.20 | 146 | 45.21% | 1.071 | 16.21% | −$68.00 | −$14.43 |
| Previous-week TP | $3,539.99 | +35.40% | $13,539.99 | 123 | 41.46% | 1.370 | 9.77% | −$70.37 | −$10.16 |
| Nearest day/week TP | $1,113.95 | +11.14% | $11,113.95 | 177 | 53.67% | 1.117 | 10.82% | −$84.52 | −$11.76 |
| Frozen AOI trail | $1,269.54 | +12.70% | $11,269.54 | 22 | 13.64% | 1.811 | 31.91% | −$7.41 | −$1.07 |
| Rolling AOI trail | $1,523.58 | +15.24% | $11,523.58 | 88 | 27.27% | 1.249 | 14.65% | −$47.48 | −$35.84 |

## 1y — 2025.09.05 to 2026.09.05

| Exit | Net P/L | Return | Final balance | Trades | Net win rate | Net PF | Max equity DD | Commission | Swap |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Current 3R | $9,231.34 | +92.31% | $19,231.34 | 237 | 32.49% | 1.357 | 16.86% | −$170.36 | −$156.66 |
| Previous-day TP | $3,917.83 | +39.18% | $13,917.83 | 317 | 46.06% | 1.165 | 15.67% | −$194.84 | −$100.53 |
| Previous-week TP | $9,017.90 | +90.18% | $19,017.90 | 270 | 41.48% | 1.359 | 15.54% | −$191.36 | −$145.96 |
| Nearest day/week TP | $3,148.05 | +31.48% | $13,148.05 | 371 | 53.10% | 1.137 | 18.93% | −$220.23 | −$95.18 |
| Frozen AOI trail | $2,725.72 | +27.26% | $12,725.72 | 1 | 100.00% | N/A (no losses) | 38.84% | −$0.22 | −$778.96 |
| Rolling AOI trail | $6,456.44 | +64.56% | $16,456.44 | 203 | 25.12% | 1.332 | 25.39% | −$153.80 | −$419.83 |

## 3y — 2023.09.05 to 2026.09.05

| Exit | Net P/L | Return | Final balance | Trades | Net win rate | Net PF | Max equity DD | Commission | Swap |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Current 3R | $16,821.20 | +168.21% | $26,821.20 | 436 | 31.42% | 1.311 | 23.01% | −$582.56 | −$566.38 |
| Previous-day TP | $10,400.36 | +104.00% | $20,400.36 | 615 | 47.80% | 1.199 | 15.56% | −$791.12 | −$427.80 |
| Previous-week TP | $18,743.70 | +187.44% | $28,743.70 | 499 | 40.08% | 1.325 | 26.27% | −$726.96 | −$712.93 |
| Nearest day/week TP | $10,410.47 | +104.10% | $20,410.47 | 681 | 53.60% | 1.201 | 16.49% | −$875.92 | −$529.44 |
| Frozen AOI trail | $21,628.88 | +216.29% | $31,628.88 | 10 | 30.00% | 26.673 | 44.25% | −$24.11 | −$6,162.09 |
| Rolling AOI trail | $13,929.75 | +139.30% | $23,929.75 | 378 | 25.13% | 1.350 | 33.00% | −$517.30 | −$1,453.78 |

## 5y — 2021.09.05 to 2026.09.05

| Exit | Net P/L | Return | Final balance | Trades | Net win rate | Net PF | Max equity DD | Commission | Swap |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Current 3R | $12,816.93 | +128.17% | $22,816.93 | 608 | 29.28% | 1.215 | 23.27% | −$807.71 | −$654.11 |
| Previous-day TP | $5,623.20 | +56.23% | $15,623.20 | 851 | 46.77% | 1.107 | 31.24% | −$999.00 | −$480.21 |
| Previous-week TP | $9,110.12 | +91.10% | $19,110.12 | 686 | 36.88% | 1.179 | 39.28% | −$795.81 | −$624.53 |
| Nearest day/week TP | $3,094.94 | +30.95% | $13,094.94 | 939 | 51.65% | 1.068 | 42.37% | −$976.89 | −$460.93 |
| Frozen AOI trail | $5,142.06 | +51.42% | $15,142.06 | 123 | 11.38% | 1.744 | 64.12% | −$159.58 | −$3,490.07 |
| Rolling AOI trail | $2,737.46 | +27.37% | $12,737.46 | 540 | 23.70% | 1.089 | 54.47% | −$504.18 | −$1,008.09 |

## Exit usage and realized behavior — 3 years

| Exit | AOI targets | 3R fallbacks | Successful SL advances | Native modification failures | Initial target R range | Average win | Average loss | Worst loss streak |
|---|---:|---:|---:|---:|---|---:|---:|---:|
| Current 3R | 0 | 0 | 0 | 0 | 3.000R to 3.008R | $517.08 | −$180.66 | 15 |
| Previous-day TP | 373 | 242 | 0 | 0 | 0.001R to 10.941R | $212.78 | −$162.48 | 7 |
| Previous-week TP | 210 | 289 | 0 | 0 | 0.003R to 41.644R | $381.71 | −$192.64 | 10 |
| Nearest day/week TP | 513 | 168 | 0 | 0 | 0.001R to 16.233R | $170.12 | −$163.55 | 7 |
| Frozen AOI trail | 0 | 0 | 7 | 0 | No TP | $7,490.45 | −$120.35 | 7 |
| Rolling AOI trail | 0 | 0 | 315 | 0 | No TP | $566.14 | −$140.82 | 14 |

## Closed-trade monthly P/L — 3-year run

Month allocation uses exit time and includes each trade’s recorded fees. Floating profits/losses are not monthly realized P/L. First and last months are partial.

| Month | Current 3R | Previous-day TP | Previous-week TP | Nearest day/week TP | Frozen AOI trail | Rolling AOI trail |
|---|---:|---:|---:|---:|---:|---:|
| 2023.09 | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) |
| 2023.10 | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) |
| 2023.11 | $1,879.19 (14 trades) | $1,325.33 (20 trades) | $2,558.11 (18 trades) | $1,559.45 (24 trades) | $595.99 (5 trades) | $807.29 (12 trades) |
| 2023.12 | $210.55 (6 trades) | $426.91 (8 trades) | $220.72 (6 trades) | $439.87 (8 trades) | −$481.48 (3 trades) | −$264.82 (3 trades) |
| 2024.01 | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) |
| 2024.02 | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) |
| 2024.03 | $416.89 (8 trades) | $148.23 (13 trades) | $1,739.86 (24 trades) | $668.83 (22 trades) | −$105.26 (1 trades) | $555.62 (16 trades) |
| 2024.04 | $1,447.43 (28 trades) | $276.96 (52 trades) | $1,188.58 (31 trades) | $126.37 (53 trades) | $0.00 (0 trades) | $2,417.81 (18 trades) |
| 2024.05 | −$112.63 (16 trades) | $351.34 (21 trades) | −$143.78 (16 trades) | $330.82 (21 trades) | $0.00 (0 trades) | −$563.59 (12 trades) |
| 2024.06 | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) |
| 2024.07 | −$144.40 (1 trades) | $102.56 (2 trades) | −$160.44 (1 trades) | $103.56 (2 trades) | $0.00 (0 trades) | −$6.38 (1 trades) |
| 2024.08 | −$1,265.41 (17 trades) | −$928.82 (27 trades) | −$946.58 (19 trades) | −$815.65 (31 trades) | $0.00 (0 trades) | −$1,152.41 (17 trades) |
| 2024.09 | $1,178.80 (14 trades) | $728.26 (28 trades) | $780.24 (17 trades) | $789.30 (29 trades) | $0.00 (0 trades) | −$12.67 (18 trades) |
| 2024.10 | −$29.84 (27 trades) | $161.72 (43 trades) | −$1,060.31 (33 trades) | −$622.97 (43 trades) | $0.00 (0 trades) | $90.08 (27 trades) |
| 2024.11 | −$283.97 (2 trades) | −$47.88 (4 trades) | −$290.74 (2 trades) | −$47.88 (4 trades) | $0.00 (0 trades) | −$198.11 (4 trades) |
| 2024.12 | −$273.81 (2 trades) | −$259.76 (2 trades) | −$287.86 (2 trades) | −$259.76 (2 trades) | $0.00 (0 trades) | −$245.72 (2 trades) |
| 2025.01 | −$271.63 (2 trades) | −$255.69 (2 trades) | −$281.92 (2 trades) | −$255.69 (2 trades) | $0.00 (0 trades) | −$238.21 (2 trades) |
| 2025.02 | $276.35 (25 trades) | $411.67 (25 trades) | −$257.61 (26 trades) | $78.03 (26 trades) | $0.00 (0 trades) | −$48.59 (17 trades) |
| 2025.03 | −$604.97 (20 trades) | −$56.46 (35 trades) | $1,165.91 (16 trades) | $1,437.70 (25 trades) | $0.00 (0 trades) | −$559.07 (17 trades) |
| 2025.04 | $359.14 (29 trades) | $902.82 (30 trades) | $173.07 (30 trades) | $743.23 (34 trades) | $0.00 (0 trades) | $2,927.11 (18 trades) |
| 2025.05 | $331.87 (9 trades) | $571.42 (11 trades) | −$382.83 (11 trades) | −$193.07 (13 trades) | $0.00 (0 trades) | $406.96 (6 trades) |
| 2025.06 | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) |
| 2025.07 | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) |
| 2025.08 | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) | $0.00 (0 trades) |
| 2025.09 | $2,544.58 (14 trades) | $2,435.94 (20 trades) | $2,492.25 (14 trades) | $2,213.18 (20 trades) | $0.00 (0 trades) | $2,657.04 (18 trades) |
| 2025.10 | $1,674.80 (29 trades) | $2,366.66 (32 trades) | $1,519.31 (33 trades) | $1,677.79 (37 trades) | $0.00 (0 trades) | $2,150.01 (17 trades) |
| 2025.11 | −$622.76 (19 trades) | −$636.42 (22 trades) | −$179.54 (27 trades) | −$48.76 (31 trades) | $0.00 (0 trades) | $1,094.18 (18 trades) |
| 2025.12 | $1,291.55 (9 trades) | $914.69 (15 trades) | $1,282.58 (9 trades) | $914.69 (15 trades) | $0.00 (0 trades) | $308.96 (12 trades) |
| 2026.01 | $1,720.05 (15 trades) | $407.51 (22 trades) | $1,736.66 (15 trades) | $406.62 (22 trades) | $0.00 (0 trades) | $1,471.73 (15 trades) |
| 2026.02 | $641.38 (20 trades) | −$239.38 (33 trades) | −$83.92 (25 trades) | −$1,375.65 (40 trades) | $0.00 (0 trades) | −$937.96 (21 trades) |
| 2026.03 | −$366.28 (10 trades) | −$1,151.47 (17 trades) | $77.55 (11 trades) | −$540.36 (18 trades) | $0.00 (0 trades) | −$1,782.35 (10 trades) |
| 2026.04 | $3,075.51 (25 trades) | $1,820.03 (37 trades) | $4,050.59 (27 trades) | $1,486.05 (46 trades) | $0.00 (0 trades) | $1,729.05 (16 trades) |
| 2026.05 | $858.03 (12 trades) | −$326.38 (13 trades) | $265.39 (13 trades) | −$261.12 (14 trades) | $0.00 (0 trades) | $1,194.67 (9 trades) |
| 2026.06 | $3,522.26 (26 trades) | $2,794.61 (32 trades) | $4,235.33 (30 trades) | $2,880.67 (42 trades) | $0.00 (0 trades) | $2,382.71 (16 trades) |
| 2026.07 | −$981.29 (15 trades) | −$1,586.48 (24 trades) | −$81.07 (19 trades) | −$972.42 (27 trades) | $0.00 (0 trades) | −$274.92 (16 trades) |
| 2026.08 | $911.87 (20 trades) | $176.67 (23 trades) | $26.23 (20 trades) | $381.87 (28 trades) | $0.00 (0 trades) | $526.42 (18 trades) |
| 2026.09 | −$562.06 (2 trades) | −$434.23 (2 trades) | −$612.08 (2 trades) | −$434.23 (2 trades) | $21,619.63 (1 trades) | −$505.09 (2 trades) |

## An actual no-TP staircase example

Broker timestamp 2023.11.16 02:30:00: BUY at 1958.265, initial SL 1956.309, TP = none. These are historical broker prices, not current trade advice.

| Confirmed at | Broken AOI | Preceding AOI | Previous SL | New SL |
|---|---:|---:|---:|---:|
| 2023.11.16 05:00:00 | 1962.139 | 1957.328 | 1956.309 | 1957.265 |
| 2023.11.16 13:45:00 | 1969.743 | 1968.177 | 1957.265 | 1968.114 |
| 2023.11.16 14:00:00 | 1970.526 | 1969.743 | 1968.114 | 1969.680 |
| 2023.11.17 15:30:00 | 1981.575 | 1970.526 | 1969.680 | 1970.463 |

## Boundary-exit sensitivity

End-of-test liquidations are included in the main results, as in the native tester. These diagnostics separate their contribution; excluding them is NOT a replacement equity backtest.

| Period / exit | Boundary-closed positions | Their net P/L | Other closed-trade net P/L | Longest hold (days) |
|---|---:|---:|---:|---:|
| 6m / Frozen AOI trail | 1 | $2,093.15 | −$823.61 | 136.3 |
| 6m / Rolling AOI trail | 0 | $0.00 | $1,523.58 | 4.8 |
| 1y / Frozen AOI trail | 1 | $2,725.72 | −$0.00 | 364.7 |
| 1y / Rolling AOI trail | 0 | $0.00 | $6,456.44 | 6.7 |
| 3y / Frozen AOI trail | 1 | $21,619.63 | $9.25 | 912.3 |
| 3y / Rolling AOI trail | 0 | $0.00 | $13,929.75 | 6.7 |
| 5y / Frozen AOI trail | 1 | $10,809.82 | −$5,667.76 | 912.3 |
| 5y / Rolling AOI trail | 0 | $0.00 | $2,737.46 | 6.7 |

## Evidence and caveats

- Recorded entry rejections across retained runs: {'market closed': 10, 'invalid stops': 1}. These remain in the audit; rejected orders are not invented trades. Successful trailing SL changes are checked against broker return codes.
- These are six predeclared mechanical variants, not a full optimization pipeline. The overlapping periods are not independent out-of-sample tests. No deployment or guaranteed profitability is implied.
- Each is a complete independent EA run. Different exits change holding periods, which later entries are available, daily-loss locks and compounded position sizes. They are not identical-entry replay comparisons.
- The current round-up sizing policy can exceed 1% planned stop risk: maximum across these runs 1.95%. This policy was not altered by exit research.
- Model 4 was requested. Real-tick coverage must be read with the source journals; pre-2026 history can use generated ticks. Historical fee schedules, news high-margin requirements and all live slippage are not reconstructed.
- Closed trades at the end of a test can include forced boundary exits. A no-TP variant can hold one trade for a long period and block new entries; high profit factor with few trades is not strong evidence.
- Original active code/SET and shared includes were preserved. Source-fidelity/unit checks and per-trade profile-direction/candle/SL/ledger assertions accompany the evidence.
- Six prototype preflight passes are retained separately and excluded from the primary results; final results use resized per-entry arrays to prevent stale ladder levels when profiles contain duplicate levels.

## Native execution-delay sensitivity

| Period / exit | Delay | Return | Trades | Net PF | Max equity DD |
|---|---:|---:|---:|---:|---:|
| 6m / Current 3R | 1000 ms | +28.59% | 108 | 1.297 | 9.71% |
| 6m / Previous-week TP | 1000 ms | +35.06% | 122 | 1.364 | 10.08% |

Delay can change the full trade path. This is not a guarantee of execution during news or gaps.

## Native MT5 reports

- [1y-batch-d1-1789303690.xml](<Backtest Reports/1y-batch-d1-1789303690.xml>)
- [3y-batch-d1-1789303816.xml](<Backtest Reports/3y-batch-d1-1789303816.xml>)
- [3y-case0-d1-1789304361.htm](<Backtest Reports/3y-case0-d1-1789304361.htm>)
- [3y-case2-d1-1789304444.htm](<Backtest Reports/3y-case2-d1-1789304444.htm>)
- [5y-batch-d1-1789304036.xml](<Backtest Reports/5y-batch-d1-1789304036.xml>)
- [6m-batch-d1-1789303635.xml](<Backtest Reports/6m-batch-d1-1789303635.xml>)
- [6m-case0-d1000-1789304526.htm](<Backtest Reports/6m-case0-d1000-1789304526.htm>)
- [6m-case2-d1000-1789304553.htm](<Backtest Reports/6m-case2-d1000-1789304553.htm>)
