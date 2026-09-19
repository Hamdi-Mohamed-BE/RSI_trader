# Raw D14 / H1 / M5 break-and-retest — XAUUSD and US100

Native MetaTrader 5 backtests, restarted after the user returned the active terminal to Exness. Frozen strategy v1; no optimization, live EA installation, BAT change or website publication.

## What was tested

- Daily: last 14 completed candles split into two seven-candle blocks. Both highs/lows higher = buy; both lower = sell; mixed/equal = no entry.
- H1: strict two-left/two-right confirmed swing break, following an opposite swing. The broken swing candle wick is the zone; only the latest zone is used.
- M5: zone retest, at least two full-body-outside rejection wicks in three completed candles, then a new confirmed high/low stair-step and a close beyond the swing. Mirror for sells.
- Stop one tick beyond the last M5 swing; 2R target; no break-even, trailing, partial closes, news/session filters or adaptive overlay.
- These are explicit interpretations of discretionary wording. In particular, the transcript does not define sideways, box width, pivot confirmation, freshness or the number of wicks. This is not a claim of exact replication. All definitions were frozen before evaluating performance.
- No same-day forced exit was specified. Positions can remain overnight. Details are in [RULES.md](RULES.md).

## Account, period and execution

- Exness-MT5Trial16 demo; current symbols listed under Zero. XAUUSD = gold, USTEC = US100/Nasdaq CFD. Not FTMO, not futures and not the Ava terminal.
- Independent $10,000 USD start for each instrument and each window. Target 1% of current equity per trade; lot step rounds UP with broker minimum lot. Actual initial stop risk can exceed 1%, before fees/gaps.
- Tester leverage 1:2000 (not a risk target). One open position per instrument; no portfolio compounding across XAUUSD and USTEC.
- End date 2026-09-05 exclusive (last full trading week available to the established research windows). The rows below list each exact start date. They do not cover 5–13 September 2026.
- Each window starts with fresh account/strategy state; overlapping windows are not independent samples and need not equal slices of the five-year run.
- Native real-tick mode requested. ACTUAL coverage is listed below. The tester journal says real ticks begin 2026-01-01 on this feed. Older dates use generated ticks where the real history is missing; do not label the long windows 100% real-tick evidence.
- Broker bid/ask prices and tester-booked commission/swap are included. Fixed 1 ms execution delay, not randomized or news-stressed execution. Stop fills may differ from requested SL. No additional invented slippage penalty was added.
- Recorded zero swap is not a promise of free overnight financing or proof of historically exact charges. Current contract/account settings and historical market data do not recreate every past account-specific fee change.
- Reported net win rate/PF are independently recomputed from closed trades after commission and swap; native headline PF can differ slightly. Drawdown is native maximum RELATIVE equity drawdown, including floating equity.

## Raw results — each row starts at $10,000

| Market | Window | Start | End exclusive | Closed trades | Net return | Net USD | Ending balance | Net win rate | Net PF | Max equity DD | Real-tick coverage |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| XAUUSD | 6m | 2026-03-05 | 2026-09-05 | 7 | -1.24% | -$124.04 | $9,875.96 | 28.57% | 0.76 | 5.20% | 100% real ticks |
| XAUUSD | 1y | 2025-09-05 | 2026-09-05 | 15 | +9.13% | $912.74 | $10,912.74 | 53.33% | 2.12 | 5.27% | 67% real ticks |
| XAUUSD | 3y | 2023-09-05 | 2026-09-05 | 41 | +10.80% | $1,080.26 | $11,080.26 | 43.90% | 1.41 | 7.56% | 22% real ticks |
| XAUUSD | 5y | 2021-09-05 | 2026-09-05 | 66 | +0.80% | $79.64 | $10,079.64 | 36.36% | 1.02 | 17.52% | 13% real ticks |
| US100 (USTEC) | 6m | 2026-03-05 | 2026-09-05 | 9 | -0.31% | -$30.94 | $9,969.06 | 33.33% | 0.95 | 3.90% | 100% real ticks |
| US100 (USTEC) | 1y | 2025-09-05 | 2026-09-05 | 15 | -0.61% | -$60.65 | $9,939.35 | 33.33% | 0.94 | 3.89% | 67% real ticks |
| US100 (USTEC) | 3y | 2023-09-05 | 2026-09-05 | 43 | -8.92% | -$892.47 | $9,107.53 | 27.91% | 0.71 | 14.25% | 22% real ticks |
| US100 (USTEC) | 5y | 2021-09-05 | 2026-09-05 | 60 | -17.06% | -$1,705.63 | $8,294.37 | 25.00% | 0.60 | 20.34% | 13% real ticks |

## Costs and trading detail

| Market | Window | Commission | Swap | Winners / losers | Avg winner | Avg loser | Worst losing streak | Long trades / net | Short trades / net | Overnight trades |
|---|---|---:|---:|---|---:|---:|---:|---|---|---:|
| XAUUSD | 6m | -$4.26 | $0.00 | 2 / 5 | $201.88 | -$105.56 | 4 | 3 / -$11.27 | 4 / -$112.77 | 3 |
| XAUUSD | 1y | -$11.41 | $0.00 | 8 / 7 | $215.71 | -$116.14 | 4 | 8 / $737.12 | 7 / $175.62 | 3 |
| XAUUSD | 3y | -$59.44 | -$193.10 | 18 / 23 | $205.79 | -$114.09 | 6 | 27 / $1,319.12 | 14 / -$238.86 | 10 |
| XAUUSD | 5y | -$124.04 | -$327.35 | 24 / 42 | $189.19 | -$106.21 | 6 | 41 / $836.45 | 25 / -$756.81 | 14 |
| US100 (USTEC) | 6m | -$11.42 | -$14.37 | 3 / 6 | $196.68 | -$103.50 | 3 | 7 / $176.30 | 2 / -$207.24 | 3 |
| US100 (USTEC) | 1y | -$23.80 | -$24.74 | 5 / 10 | $195.22 | -$103.68 | 3 | 10 / $157.25 | 5 / -$217.90 | 4 |
| US100 (USTEC) | 3y | -$88.55 | -$88.64 | 12 / 31 | $183.88 | -$99.97 | 6 | 30 / -$767.58 | 13 / -$124.89 | 9 |
| US100 (USTEC) | 5y | -$119.53 | -$129.85 | 15 / 45 | $167.92 | -$93.88 | 11 | 37 / -$883.40 | 23 / -$822.23 | 13 |

## Signal funnel and execution audit

| Market | Window | H1 zones | M5 holds | Entry signals | Fills | Rejections | Order errors | Planned risk min–max | End-of-test exits |
|---|---|---:|---:|---:|---:|---:|---:|---|---:|
| XAUUSD | 6m | 70 | 22 | 7 | 7 | 0 | 0 | 1.010%–1.095% | 0 |
| XAUUSD | 1y | 141 | 43 | 15 | 15 | 0 | 0 | 1.003%–1.114% | 0 |
| XAUUSD | 3y | 394 | 100 | 42 | 41 | 0 | 1 | 1.000%–1.097% | 0 |
| XAUUSD | 5y | 686 | 171 | 67 | 66 | 0 | 1 | 1.001%–1.104% | 0 |
| US100 (USTEC) | 6m | 83 | 22 | 9 | 9 | 0 | 0 | 1.001%–1.008% | 0 |
| US100 (USTEC) | 1y | 135 | 39 | 15 | 15 | 0 | 0 | 1.000%–1.005% | 0 |
| US100 (USTEC) | 3y | 400 | 98 | 43 | 43 | 0 | 0 | 1.000%–1.014% | 0 |
| US100 (USTEC) | 5y | 674 | 152 | 60 | 60 | 0 | 0 | 1.000%–1.009% | 0 |

## Five-year run, calendar-year breakdown

Partial 2021 and 2026; these calendar-year figures partition the continuous five-year run, not separate annual restarts.

| Market | Calendar year | Closed trades | Net USD | Commission | Swap | Win rate | Net PF |
|---|---:|---:|---:|---:|---:|---:|---:|
| XAUUSD | 2021 | 3 | -$15.89 | -$12.82 | $0.00 | 33.33% | 0.93 |
| XAUUSD | 2022 | 15 | -$498.04 | -$43.87 | -$152.44 | 26.67% | 0.61 |
| XAUUSD | 2023 | 8 | -$543.27 | -$14.87 | -$46.54 | 12.50% | 0.25 |
| XAUUSD | 2024 | 15 | -$63.79 | -$30.13 | -$19.25 | 33.33% | 0.93 |
| XAUUSD | 2025 | 15 | $1,022.23 | -$15.83 | -$109.12 | 60.00% | 2.56 |
| XAUUSD | 2026 | 10 | $178.40 | -$6.52 | $0.00 | 40.00% | 1.28 |
| USTEC | 2021 | 1 | -$114.16 | -$1.24 | -$11.66 | 0.00% | 0.00 |
| USTEC | 2022 | 11 | -$803.62 | -$23.25 | $0.00 | 9.09% | 0.19 |
| USTEC | 2023 | 8 | -$259.53 | -$22.27 | -$37.41 | 25.00% | 0.55 |
| USTEC | 2024 | 14 | -$20.64 | -$35.45 | -$60.10 | 35.71% | 0.98 |
| USTEC | 2025 | 16 | -$643.91 | -$25.65 | -$8.72 | 18.75% | 0.44 |
| USTEC | 2026 | 10 | $136.23 | -$11.67 | -$11.96 | 40.00% | 1.26 |

## Verification

- Research EA refuses to initialize outside the MT5 Strategy Tester. Compilation: zero errors and warnings. Embedded synthetic rule checks passed on initialization.
- Ten independent deterministic unit tests cover higher/lower/mixed/equal daily structure, strict pivots, unavailable right-hand candles and mirrored rejection rules.
- Every native zone, holding confirmation and entry was independently checked against the exported D1/H1/M5 OHLC history. Checks include completed-bar daily bias, delayed swing availability, H1 break chronology, no broken-zone resurrection, wick count, higher-low/lower-high ordering, stop placement and fixed 2R arithmetic.
- Trade counts, profit, commission and swap reconcile to the MT5 reports. No overlapping positions per instrument; unique trade numbers. All eight reports use the same final EA source hash.
- Source SHA-256: `98e400f29a2981040ace9bb7eeb57bd12a1dbccc26c6c5066754042523d38197`.
- A pre-final implementation review moved zone invalidation ahead of the open-position check and prohibited pre-test stale breaks. These are correctness fixes; no strategy parameters were selected using returns. All final tests were rerun with the corrected frozen source after the Exness restart.

## Native reports and full trades

- XAUUSD 6m: [native MT5 report](<Backtest Reports/xauusd-d14-raw-6m-model4.htm>), [closed trades with costs](<Audit/xauusd-d14-raw-6m-model4-trades.json>), [signal audit](<Audit/xauusd-d14-raw-6m-model4.csv>).
- XAUUSD 1y: [native MT5 report](<Backtest Reports/xauusd-d14-raw-1y-model4.htm>), [closed trades with costs](<Audit/xauusd-d14-raw-1y-model4-trades.json>), [signal audit](<Audit/xauusd-d14-raw-1y-model4.csv>).
- XAUUSD 3y: [native MT5 report](<Backtest Reports/xauusd-d14-raw-3y-model4.htm>), [closed trades with costs](<Audit/xauusd-d14-raw-3y-model4-trades.json>), [signal audit](<Audit/xauusd-d14-raw-3y-model4.csv>).
- XAUUSD 5y: [native MT5 report](<Backtest Reports/xauusd-d14-raw-5y-model4.htm>), [closed trades with costs](<Audit/xauusd-d14-raw-5y-model4-trades.json>), [signal audit](<Audit/xauusd-d14-raw-5y-model4.csv>).
- US100 (USTEC) 6m: [native MT5 report](<Backtest Reports/ustec-d14-raw-6m-model4.htm>), [closed trades with costs](<Audit/ustec-d14-raw-6m-model4-trades.json>), [signal audit](<Audit/ustec-d14-raw-6m-model4.csv>).
- US100 (USTEC) 1y: [native MT5 report](<Backtest Reports/ustec-d14-raw-1y-model4.htm>), [closed trades with costs](<Audit/ustec-d14-raw-1y-model4-trades.json>), [signal audit](<Audit/ustec-d14-raw-1y-model4.csv>).
- US100 (USTEC) 3y: [native MT5 report](<Backtest Reports/ustec-d14-raw-3y-model4.htm>), [closed trades with costs](<Audit/ustec-d14-raw-3y-model4-trades.json>), [signal audit](<Audit/ustec-d14-raw-3y-model4.csv>).
- US100 (USTEC) 5y: [native MT5 report](<Backtest Reports/ustec-d14-raw-5y-model4.htm>), [closed trades with costs](<Audit/ustec-d14-raw-5y-model4-trades.json>), [signal audit](<Audit/ustec-d14-raw-5y-model4.csv>).

## Recommendation before optimization

- XAUUSD: defer the full pipeline. The three-year result is positive, but the five-year account gains only $79.64 (+0.80%) with 17.52% equity drawdown and just 66 trades. The six-month fully real-tick sample also loses and has only seven trades. This is not a stable demonstrated edge.
- US100: skip this raw version. All four requested windows lose; five-year net is -$1,705.63 (-17.06%), PF 0.60 and 20.34% equity drawdown.
- If revisiting the concept, first clarify the creator’s exact daily-trend, H1-zone and M5-structure definitions. Any different interpretation must be labelled a new hypothesis, not silently called the same raw strategy. No optimization has been authorized or performed.
- One XAU order attempt was rejected as market closed on 2025-02-12 at 21:20 server time. The same event appears in both overlapping 3Y and 5Y reports. It was not filled, retried late or counted as a completed trade.

## Interpretation and limits

This raw test decides whether further research is justified; it is not a guarantee of an edge, proof of out-of-sample profitability, or authorization for optimization/deployment. A small trade count can produce misleading win rates. The transcript’s fixed 2R exit means the theoretical pre-cost break-even win rate is 33.33%; spread, commission, swap and adverse fills increase it.

## References

- User-supplied strategy transcript (primary strategy specification).
- [MetaTrader 5 testing modes, execution delay and historical testing](https://www.metatrader5.com/en/terminal/help/algotrading/testing).
- [MQL5 CopyRates ordering and current versus completed bars](https://www.mql5.com/en/docs/series/copyrates).
