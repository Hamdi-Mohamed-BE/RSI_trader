# P Continuation / Failed Auction — full validation

## Verdict

**REJECT. Do not add this EA to the active BAT or website.** The strategy failed on the preselected development history for every market. On the untouched last year, only Bitcoin was marginally positive (+0.71%, PF 1.08) and that came from just 13 trades. This is not sufficient evidence of a repeatable edge.

## Exact test design

- Starting balance: $10,000 per independent test
- Position risk: 1% of current equity per trade
- Broker/data: Exness MT5, broker-native history
- Locked period: 2025-08-28 through 2026-08-27
- Locked modelling: MT5 Every Tick, history quality shown in each native report
- Costs: floating broker spread, commission, swap and random execution delay
- Selection: six simple variants were compared only on 2022-01-01 through 2025-08-27; one variant per market was then frozen
- No locked-year result was used to pick its own settings

## Locked one-year results

| Market | Broker symbol | Frozen variant | Development return | Dev PF | Locked return | PF | Win rate | Max equity DD | Wins / losses | Trades | Commission | Swap |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Gold | XAUUSD | m15-rr20 | -4.62% | 0.68 | -2.85% | 0.63 | 25.00% | 6.91% | 3 / 9 | 12 | -$9.21 | $0.00 |
| Silver | XAGUSD | m5-absorption-rr20 | -17.81% | 0.26 | -5.50% | 0.00 | 0.00% | 5.50% | 0 / 5 | 5 | -$66.51 | -$3.20 |
| US30 | US30 | m15-rr20 | -0.19% | 0.99 | -0.22% | 0.96 | 30.00% | 4.34% | 3 / 7 | 10 | -$13.11 | $0.00 |
| US100 | USTEC | m5-absorption-rr20 | -2.83% | 0.80 | -2.58% | 0.43 | 14.29% | 4.82% | 1 / 6 | 7 | -$17.89 | -$38.21 |
| Bitcoin | BTCUSD | m1-rr15 | -10.64% | 0.70 | +0.71% | 1.08 | 46.15% | 6.66% | 6 / 7 | 13 | -$222.01 | $0.00 |

## Development winners carried forward

- Gold: m15-rr20, -4.62%, PF 0.68, DD 6.74%, 30 trades
- Silver: m5-absorption-rr20, -17.81%, PF 0.26, DD 17.81%, 28 trades
- US30: m15-rr20, -0.19%, PF 0.99, DD 9.60%, 38 trades
- US100: m5-absorption-rr20, -2.83%, PF 0.80, DD 5.04%, 22 trades
- Bitcoin: m1-rr15, -10.64%, PF 0.70, DD 15.92%, 58 trades

## Rules implemented

1. Detect a directional impulse spanning several completed bars, requiring a minimum ATR move and directional efficiency.
2. Require a compact consolidation to form near the impulse extreme, representing acceptance at the new price level.
3. Build a 24-row volume profile over that consolidation using Exness tick volume and calculate its POC plus 70% value area.
4. Long after price sweeps VAL and closes back inside with a strong upper close; short after the inverse VAH reclaim.
5. The stricter variant also requires reclaim-bar tick volume to be at least 1.25 times its recent average.
6. Put the stop beyond the failed-auction candle with an ATR buffer; use the frozen 1.5R/2R or impulse-size target; move to break-even at 1R.

## Important limitation

Exness CFD history has tick volume, not centralized exchange volume and not a historical order book. Therefore the EA can test a value-area sweep/reclaim and a tick-volume expansion proxy, but it **cannot prove true absorption or a failed auction from bid/ask depth**. A genuine order-flow version needs exchange futures/crypto trade and depth data.

## Files

- Source: `EA/P Continuation Failed Auction EA.mq5`
- Compiled research EA: `EA/P Continuation Failed Auction EA.ex5`
- Frozen sets: `Sets/`
- Native MT5 reports and native equity charts: `Backtest Reports/`
- Machine-readable results: `development-results.json`, `locked-results.json`
- Comparison graph: `P CONTINUATION FIVE MARKET LOCKED AUDIT.png`
