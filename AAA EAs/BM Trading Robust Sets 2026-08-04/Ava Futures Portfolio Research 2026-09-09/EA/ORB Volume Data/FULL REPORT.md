# ORB Volume + Data EA — final honest report

## Verdict

There is no perfect universal ORB preset in this test. XAUUSD passed cleanly and US30 passed with a small edge. BTCUSD, USTEC, and US500 failed the untouched final year and are not approved for live deployment.

## Untouched final-year results

- Window: 2025-08-07 through 2026-08-06
- Broker/history: Exness `Exness-MT5Trial16` CFDs
- Initial balance: USD 10,000 per independent test
- Risk: 1.00% of current equity per trade
- Engine: MT5 Every Tick from broker M1 history with random execution delay
- Chart: M5; maximum one position per market per session; forced intraday flat
- Pass gate: positive net profit, PF at least 1.15, equity DD no more than 12%, and at least 20 trades

| Status | Market | Symbol | Final | Net | Return | Equity DD | PF | Win rate | Wins / losses | Trades | History |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PASS | Gold | XAUUSD M5 | $10,818.92 | $818.92 | +8.19% | 6.40% | 1.53 | 40.00% | 20 / 30 | 50 | 99% |
| REJECT | Bitcoin | BTCUSD M5 | $8,840.74 | $-1,159.26 | -11.59% | 16.41% | 0.51 | 19.05% | 8 / 34 | 42 | 100% |
| PASS | Dow | US30 M5 | $10,268.63 | $268.63 | +2.69% | 4.92% | 1.23 | 34.78% | 8 / 15 | 23 | 100% |
| REJECT | Nasdaq | USTEC M5 | $9,648.15 | $-351.85 | -3.52% | 4.91% | 0.29 | 11.11% | 1 / 8 | 9 | 100% |
| REJECT | S&P 500 | US500 M5 | $9,768.42 | $-231.58 | -2.32% | 9.15% | 0.86 | 36.00% | 9 / 16 | 25 | 100% |

## Detailed trade statistics

| Symbol | Gross profit | Gross loss | Largest win | Largest loss | Average win | Average loss | Balance DD | Recovery | Sharpe |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| XAUUSD | $2,363.11 | $-1,544.19 | $257.57 | $-104.91 | $118.16 | $-50.89 | $547.82 (5.43%) | 1.26 | 6.71 |
| BTCUSD | $1,220.67 | $-2,379.93 | $287.91 | $-101.31 | $152.58 | $-68.90 | $1,626.85 (16.03%) | -0.69 | -5.00 |
| US30 | $1,415.55 | $-1,146.92 | $206.96 | $-105.83 | $176.94 | $-75.60 | $419.53 (3.96%) | 0.51 | 6.19 |
| USTEC | $142.71 | $-494.56 | $142.71 | $-99.51 | $142.71 | $-61.09 | $397.46 (3.97%) | -0.71 | -5.00 |
| US500 | $1,370.98 | $-1,602.56 | $156.34 | $-105.76 | $152.33 | $-96.07 | $857.90 (8.11%) | -0.24 | -5.00 |

## Locked presets

| Symbol | NY anchor | OR | Opening relative tick volume | Breakout relative tick volume | Range / ATR | Entry | Body minimum | Stop | Target | Result |
|---|---:|---:|---:|---:|---:|---|---:|---|---:|---|
| XAUUSD | 9:30 | 15 min | ≥ 0.6× | ≥ 0.8× | 0.2–1.2 | direct breakout | 55% | opposite OR | 2.5R | PASS |
| BTCUSD | 9:30 | 15 min | ≥ 0.6× | ≥ 0.8× | 0.4–2.0 | direct breakout | 40% | opposite OR | 3.0R | REJECT |
| US30 | 9:30 | 5 min | ≥ 0.6× | ≥ 1.2× | 0.4–1.2 | direct breakout | 70% | signal candle | 2.0R | PASS |
| USTEC | 9:30 | 15 min | ≥ 0.8× | ≥ 1.0× | 0.2–1.6 | direct breakout | 55% | signal candle | 1.5R | REJECT |
| US500 | 9:30 | 15 min | ≥ 0.6× | ≥ 0.8× | 0.2–1.2 | direct breakout | 70% | signal candle | 1.5R | REJECT |

## Validation design

1. Development/optimization: 2022-01-03 through 2024-12-31.
2. Candidate selection without optimization: 2025-01-01 through 2025-08-06.
3. Locked final test: 2025-08-07 through 2026-08-06. Final results were not used to choose another preset.

This avoids the dishonest practice of selecting the best settings on the same year being advertised. It does not remove market-regime risk or prove future profitability.

## Volume-data limitation

Exness CFD history exposes tick volume, not consolidated exchange volume. The EA therefore compares each opening window and breakout bar with its own recent tick-volume baseline. That is a useful activity proxy, but it is not CME, COMEX, NYSE, Nasdaq, or consolidated crypto volume.

## Research basis

- [NYSE auction schedule](https://www.nyse.com/trade/auctions): the core opening auction begins at 09:30 New York time.
- [Zarattini, Barbon, and Aziz — US equity ORB](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4729284): large-sample evidence emphasizes unusually active stocks and compares several opening-range lengths.
- [Wang and Gangwar — ORB robustness study](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5198458): volume thresholds and 5/15/30-minute variants are tested, but statistical significance remains inconclusive—an important warning against overclaiming.
- [Graczyk and Queirós — intraday volume nonstationarity](https://arxiv.org/abs/1810.12099): opening volume/volatility patterns exist but change across regimes.
- [Bitcoin intraday price discovery](https://doi.org/10.1016/j.ribaf.2022.101625): London–New York overlap dominates price discovery in the sample, although the 08:00 New York variant failed our later broker-data selection test.

Native MT5 HTML reports and equity graphs are under `Reports`. Settings are under `Best Settings`; rejected presets are labeled explicitly and should not be deployed.
