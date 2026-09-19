# Raw H4 fair-value-gap swing — XAUUSD and US100

**Raw research only. No optimization, deployment, website/BAT modification or Git push.** One frozen mechanical rule set was applied unchanged to both markets.

## Mechanical interpretation

- Completed H4 candles only. Bullish FVG: candle 3 low above candle 1 high. Bearish: candle 3 high below candle 1 low.
- Keep the newest untraded gap per direction. Enter at the first later executable tick inside it; invalidate if price crosses the far edge first.
- Stop one tradable tick beyond candle 1 extreme; fixed 2R target. One position per symbol; both directions.
- No displacement threshold, trend, volume, lower-timeframe, news, session, expiry, break-even or trailing filter.
- The transcript defines only the visual H4 gap and retrace. Stop, target, symmetry and zone lifecycle are necessary explicit assumptions, frozen before results. This is not an exact clone of a discretionary/private strategy. See [RULES.md](RULES.md).

## Account and evidence

- Native MT5 Strategy Tester on Exness-MT5Trial16 Zero demo, XAUUSD and USTEC, H4, independent $10,000 starts, leverage 1:2000.
- Planned risk is 1% of current equity; volume rounds up to the broker step/minimum, so it is not a hard cap. Spread, tester-booked commission and swap are included.
- Real-tick mode requested with 1ms delay. Journal evidence says real ticks begin 2026-01-01; older missing ticks are generated. All windows end 2026-09-05 exclusive.
- Overlapping periods restart balance and setup state; they are not independent experiments. Returns are total-period, not annualized.

## Raw results

| Market | Window | Trades | Return | Net USD | Final balance | Win rate | PF | Max equity DD | Real-tick coverage |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| XAUUSD | 6m | 50 | -10.01% | -$1,000.67 | $8,999.33 | 28.00% | 0.79 | 14.50% | 100% real ticks |
| XAUUSD | 1y | 93 | -21.51% | -$2,151.47 | $7,848.53 | 27.96% | 0.74 | 25.33% | 67% real ticks |
| XAUUSD | 3y | 264 | -1.97% | -$197.08 | $9,802.92 | 34.47% | 0.99 | 25.40% | 22% real ticks |
| XAUUSD | 5y | 394 | -31.92% | -$3,192.45 | $6,807.55 | 32.74% | 0.89 | 36.29% | 13% real ticks |
| US100 (USTEC) | 6m | 48 | +17.59% | $1,759.40 | $11,759.40 | 45.83% | 1.61 | 7.48% | 100% real ticks |
| US100 (USTEC) | 1y | 110 | -1.18% | -$117.76 | $9,882.24 | 34.55% | 0.98 | 23.69% | 67% real ticks |
| US100 (USTEC) | 3y | 253 | -18.09% | -$1,809.35 | $8,190.65 | 32.41% | 0.88 | 32.89% | 22% real ticks |
| US100 (USTEC) | 5y | 437 | -53.91% | -$5,390.91 | $4,609.09 | 29.06% | 0.72 | 61.94% | 13% real ticks |

## Costs, direction and holding

| Market | Window | Commission | Swap | Winners / losers | Long trades / net | Short trades / net | Overnight | Avg holding | Worst loss streak |
|---|---|---:|---:|---|---|---|---:|---:|---:|
| XAUUSD | 6m | -$6.98 | -$69.97 | 14 / 36 | 23 / -$1,200.19 | 27 / $199.52 | 36 | 66.0h | 6 |
| XAUUSD | 1y | -$13.77 | -$106.23 | 26 / 67 | 52 / -$894.42 | 41 / -$1,257.05 | 59 | 67.5h | 7 |
| XAUUSD | 3y | -$97.10 | -$848.44 | 91 / 173 | 149 / $2,350.78 | 115 / -$2,547.86 | 175 | 72.0h | 11 |
| XAUUSD | 5y | -$142.22 | -$1,313.50 | 129 / 265 | 219 / -$95.41 | 175 / -$3,097.04 | 254 | 82.3h | 12 |
| US100 (USTEC) | 6m | -$14.84 | -$149.73 | 22 / 26 | 32 / $1,231.11 | 16 / $528.29 | 33 | 67.4h | 5 |
| US100 (USTEC) | 1y | -$41.61 | -$317.42 | 38 / 72 | 66 / $710.89 | 44 / -$828.65 | 72 | 54.3h | 14 |
| US100 (USTEC) | 3y | -$107.60 | -$775.99 | 82 / 171 | 143 / -$186.47 | 110 / -$1,622.88 | 143 | 74.6h | 14 |
| US100 (USTEC) | 5y | -$143.01 | -$846.79 | 127 / 310 | 232 / -$2,748.22 | 205 / -$2,642.69 | 257 | 71.8h | 20 |

## Signal and execution audit

| Market | Window | H4 gaps | Invalidated | Attempts | Fills | Rejected | Errors | Actual filled stop risk | Boundary exits |
|---|---|---:|---:|---:|---:|---:|---:|---|---:|
| XAUUSD | 6m | 185 | 54 | 50 | 50 | 0 | 0 | 1.031%–2.038% | 0 |
| XAUUSD | 1y | 362 | 100 | 93 | 93 | 0 | 0 | 1.001%–2.365% | 0 |
| XAUUSD | 3y | 1097 | 341 | 268 | 264 | 0 | 4 | 0.999%–1.911% | 0 |
| XAUUSD | 5y | 1777 | 602 | 398 | 394 | 0 | 4 | 1.001%–2.546% | 0 |
| US100 (USTEC) | 6m | 201 | 56 | 48 | 48 | 0 | 0 | 0.941%–1.075% | 0 |
| US100 (USTEC) | 1y | 411 | 111 | 111 | 110 | 0 | 1 | 0.942%–1.084% | 0 |
| US100 (USTEC) | 3y | 1155 | 348 | 257 | 253 | 0 | 4 | 0.936%–1.392% | 0 |
| US100 (USTEC) | 5y | 1950 | 585 | 441 | 437 | 0 | 4 | 0.950%–2.508% | 0 |

## Five-year calendar breakdown

Partial 2021 and 2026. These partition each continuous five-year run.

| Market | Year | Trades | Net USD | Win rate | PF | Commission | Swap |
|---|---:|---:|---:|---:|---:|---:|---:|
| XAUUSD | 2021 | 17 | -$305.48 | 29.41% | 0.78 | -$14.29 | -$47.58 |
| XAUUSD | 2022 | 73 | -$1,202.34 | 30.14% | 0.78 | -$34.37 | -$363.55 |
| XAUUSD | 2023 | 64 | $290.93 | 37.50% | 1.08 | -$32.49 | -$364.17 |
| XAUUSD | 2024 | 81 | -$567.74 | 32.10% | 0.89 | -$31.83 | -$248.01 |
| XAUUSD | 2025 | 92 | -$14.41 | 34.78% | 1.00 | -$21.76 | -$226.17 |
| XAUUSD | 2026 | 67 | -$1,393.41 | 29.85% | 0.75 | -$7.48 | -$64.02 |
| USTEC | 2021 | 40 | -$1,636.37 | 20.00% | 0.46 | -$29.82 | -$71.05 |
| USTEC | 2022 | 83 | -$1,525.41 | 26.51% | 0.69 | -$30.31 | -$136.48 |
| USTEC | 2023 | 103 | -$1,863.85 | 25.24% | 0.59 | -$38.78 | -$265.70 |
| USTEC | 2024 | 66 | -$238.46 | 33.33% | 0.90 | -$16.21 | -$170.67 |
| USTEC | 2025 | 77 | $126.07 | 35.06% | 1.05 | -$19.14 | -$127.23 |
| USTEC | 2026 | 68 | -$252.89 | 32.35% | 0.88 | -$8.75 | -$75.66 |

## Verification

- EA compilation completed with zero errors and zero warnings, and it refuses non-tester initialization.
- Ten deterministic rule tests passed. Every native H4 gap was independently recomputed from exported candles; completed-bar chronology, exact zone/stop construction, first-use uniqueness, 2R arithmetic, risk rounding and mirrored invalidation were checked.
- Every trade count and its profit, commission and swap reconcile to the native report. No overlapping strategy positions occurred. All eight runs use the same source hash.
- Four XAU and four US100 attempts in the overlapping longer windows were rejected as market closed. They were not filled or counted as trades; the EA did not retry them later.
- Source SHA-256: `ad1df1cd4c6349214bb01195e3122af179cc4ed696836f695a0a47a23b4e45f7`.

## Recommendation

- XAUUSD: skip full optimization of this raw interpretation. Five-year result -31.92%, PF 0.89, equity DD 36.29%, 394 trades.
- US100 (USTEC): skip full optimization of this raw interpretation. Five-year result -53.91%, PF 0.72, equity DD 61.94%, 437 trades.
- No profitability is guaranteed. If the raw version fails, optimization could mostly fit assumptions the transcript never supplied. A better next step would be obtaining the creator's exact stop, target, invalidation and multi-gap rules.

## Native reports

- XAUUSD 6m: [MT5 report](<Backtest Reports/xauusd-h4-fvg-raw-6m-model4.htm>), [trades](<Audit/xauusd-h4-fvg-raw-6m-model4-trades.json>), [signal audit](<Audit/xauusd-h4-fvg-raw-6m-model4.csv>).
- XAUUSD 1y: [MT5 report](<Backtest Reports/xauusd-h4-fvg-raw-1y-model4.htm>), [trades](<Audit/xauusd-h4-fvg-raw-1y-model4-trades.json>), [signal audit](<Audit/xauusd-h4-fvg-raw-1y-model4.csv>).
- XAUUSD 3y: [MT5 report](<Backtest Reports/xauusd-h4-fvg-raw-3y-model4.htm>), [trades](<Audit/xauusd-h4-fvg-raw-3y-model4-trades.json>), [signal audit](<Audit/xauusd-h4-fvg-raw-3y-model4.csv>).
- XAUUSD 5y: [MT5 report](<Backtest Reports/xauusd-h4-fvg-raw-5y-model4.htm>), [trades](<Audit/xauusd-h4-fvg-raw-5y-model4-trades.json>), [signal audit](<Audit/xauusd-h4-fvg-raw-5y-model4.csv>).
- US100 (USTEC) 6m: [MT5 report](<Backtest Reports/ustec-h4-fvg-raw-6m-model4.htm>), [trades](<Audit/ustec-h4-fvg-raw-6m-model4-trades.json>), [signal audit](<Audit/ustec-h4-fvg-raw-6m-model4.csv>).
- US100 (USTEC) 1y: [MT5 report](<Backtest Reports/ustec-h4-fvg-raw-1y-model4.htm>), [trades](<Audit/ustec-h4-fvg-raw-1y-model4-trades.json>), [signal audit](<Audit/ustec-h4-fvg-raw-1y-model4.csv>).
- US100 (USTEC) 3y: [MT5 report](<Backtest Reports/ustec-h4-fvg-raw-3y-model4.htm>), [trades](<Audit/ustec-h4-fvg-raw-3y-model4-trades.json>), [signal audit](<Audit/ustec-h4-fvg-raw-3y-model4.csv>).
- US100 (USTEC) 5y: [MT5 report](<Backtest Reports/ustec-h4-fvg-raw-5y-model4.htm>), [trades](<Audit/ustec-h4-fvg-raw-5y-model4-trades.json>), [signal audit](<Audit/ustec-h4-fvg-raw-5y-model4.csv>).
