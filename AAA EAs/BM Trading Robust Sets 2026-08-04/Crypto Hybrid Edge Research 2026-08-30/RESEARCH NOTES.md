# Crypto hybrid edge research notes

## Evidence used

- A peer-reviewed intraday study reports both momentum and reversal in BTC, ETH, LTC and XRP, with the dominant effect depending on market state and liquidity: https://www.sciencedirect.com/science/article/pii/S1062940822000833
- A cross-sectional study finds short-term reversal concentrated in less-liquid coins, while the largest and most-liquid cryptocurrencies exhibit momentum: https://www.sciencedirect.com/science/article/pii/S1057521921002349
- Dynamic time-series momentum has been documented across cryptocurrency intraday frequencies: https://www.sciencedirect.com/science/article/abs/pii/S1062940821000590
- Earlier evidence also finds that cryptocurrency momentum is mainly a short-horizon phenomenon: https://www.sciencedirect.com/science/article/pii/S0165176519303647
- A recent preprint reports pervasive 15-minute reversal but estimates a gross edge of roughly 1.3 basis points against a 5-basis-point cost assumption, illustrating why statistical predictability may not be tradable after costs: https://arxiv.org/abs/2608.21888

## Translation into testable rules

The EA compared three non-lookahead rule families:

1. Trend pullback: H1/H4 EMA alignment, prior 24-hour momentum, pullback to the fast EMA and a completed-candle reclaim.
2. Extreme reversion: a completed close outside a Bollinger envelope with extreme RSI, followed by a completed-candle re-entry.
3. Breakout-retest: a Donchian break supported by ATR-normalized candle body and relative tick volume, followed by a completed-candle retest.

Every entry used a structural stop and a fixed 0.5R, 0.7R or 1.0R target. Risk was 1% of current equity. No future bars or cached synthetic price data were used.

## Broker scope

The connected Exness-MT5Trial16 account exposes BTCUSD and ETHUSD as tradeable crypto CFDs. Other visible majors such as SOLUSD, XRPUSD, LTCUSD, BCHUSD and BNBUSD were disabled for trading on this account, so they were not presented as deployable MT5 tests.

## Honest result

The M15 development winners failed the untouched one-year test. A disclosed second investigation reduced turnover to H1/H4 and used development, validation and a final six-month holdout. Those final holdouts also failed. No tested configuration qualifies for the active portfolio.

See `FULL REPORT.md` and `SLOW FULL REPORT.md` for the result tables, and the `Charts` and `Slow Charts` folders for equity curves.
