# Relative-Volume ORB: 60-Day Research Report

Period: 2026-05-08 to 2026-07-07
Starting balance: $300.00
Walk-forward validation: **FAILED**

## Walk-Forward Selection

- Symbols: NVDA, AMD, TSLA, FSLR, RCL, W, OKTA, ADBE, WDC, NFLX, ASML, CDNS, META, AMZN, AAPL, MSFT
- Opening range: 5 minutes
- Stop: 20% of prior 14-session ATR
- Minimum relative volume: 1.0
- Daily rank limit: 1
- Training: -2.75% over 7 trades
- Validation: 2.50% over 6 trades
- Full period: $299.26 (-0.25%), 13 trades, 4.36% max drawdown

## Full-Period Winner (In-Sample)

- Symbols: AMD, CDNS, NVDA
- Configuration: 5m range, 5% ATR stop, RVOL >= 1.0, top 3
- Training: 22.75% over 15 trades
- Validation: -0.96% over 1 trade
- Full period: $365.38 (+21.79%), 16 trades, 5.27% max drawdown

This winner is reported for transparency, not promoted to a live default, because it did not pass the chronological validation gate.

## Paper-Faithful Baseline

- Configuration: 5m range, 10% ATR stop, RVOL >= 1.0, top 20
- Full period: $222.97 (-25.68%), 46 trades, 26.16% max drawdown
- Win rate: 6.52%; profit factor: 0.11

## Data Limitation

The paper uses consolidated U.S. share volume. This broker supplies MT5 tick volume for its stock CFDs, so relative volume is only an activity proxy and the one-million-share eligibility filter cannot be reproduced faithfully.
