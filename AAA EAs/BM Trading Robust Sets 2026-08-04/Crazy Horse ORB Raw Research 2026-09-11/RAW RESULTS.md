# Crazy Horse ORB — raw reconstruction

## Scope

Research only. No pipeline optimization and no website, BAT or live-account change.

## Rules that were actually stated

- New York cash open, 09:30 ET.
- Build the first 15-minute range.
- Enter after the first M5 candle body closes outside that range; no retest.
- Use higher-timeframe direction.
- The example used 1:1 because its 227-point opening range was described as overextended.
- Trail by a proprietary "shelf" method.

## Missing rules and transparent reconstruction

The transcript does not define the proprietary trend signal, auto-stop, range-overextension threshold or shelf algorithm. The `stated minimum` row therefore uses the opposite edge of the 15-minute range as the stop, a fixed 1R target, one first breakout per day, signals only through 10:30 ET, and no trailing. The second row adds a clearly labelled H1 EMA200 trend proxy. This is not claimed to be the creator's proprietary model.

## Five-year Exness Raw Spread result

| Symbol | Raw interpretation | Trades | Return | PF | Win rate | Max DD | Sharpe | Avg R | Costs |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| XAUUSD | stated minimum | 1143 | -21.03% | 0.95 | 48.99% | 36.61% | -0.38 | -0.02R | $1047.06 |
| XAUUSD | H1 EMA200 proxy | 619 | -24.07% | 0.89 | 47.50% | 35.90% | -0.83 | -0.04R | $569.10 |
| USTEC | stated minimum | 1161 | -43.66% | 0.89 | 51.51% | 46.18% | -0.90 | -0.05R | $6479.55 |
| USTEC | H1 EMA200 proxy | 591 | -7.13% | 0.97 | 53.30% | 22.27% | -0.22 | -0.01R | $4269.93 |

Returns use a $10,000 balance and 1% equity risk per trade, recorded bar spreads, broker-valid lot steps, $3.50/lot/side commission, conservative stop-first handling when both exits fall inside one M5 bar, and a 16:00 ET forced exit. The CSV also contains one- and three-year rows.

## Promotion decision

**Skip the full pipeline for now.** Every five-year row loses after costs and the best five-year win rate is far below the advertised 80%. XAU improves in the latest year, but that isolated recovery does not justify optimizing a five-year loser. Reconsider only after obtaining the creator's exact HTF signal, auto-stop, overextension threshold and shelf-trailing rules.

Broker: Exness Technologies Ltd / Exness-MT5Trial16 / Zero.
