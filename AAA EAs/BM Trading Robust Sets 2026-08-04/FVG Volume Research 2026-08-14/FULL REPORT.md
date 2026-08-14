# FVG + Fixed-Range Volume-Profile POC Strategy

Completed: 2026-08-14  
Source concept: https://www.youtube.com/shorts/gODvrviDcQQ  
Portfolio decision: **REJECT — do not add to the active BAT**

## What the video actually teaches

The video does not present a complete mechanical trading system. It demonstrates a confluence method:

1. Identify multiple fair value gaps created during a directional swing.
2. Remove gaps that price closes through or trades deeply inside without rejection.
3. Draw a fixed-range volume profile from the swing low to swing high.
4. Prefer the still-valid FVG that contains the volume profile Point of Control (POC).
5. Wait for price to revisit that FVG/POC and print a strong rejection candle.
6. Trade the reaction away from the zone.

The video does not define timeframe, swing algorithm, minimum impulse, gap size, exact rejection rule, stop, target, expiration, holding time, risk, costs, or whether the example uses real exchange volume. Those missing elements were declared and screened transparently.

## Mechanical version tested

- Classic three-candle bullish and bearish FVG detection.
- Confirmed pivot-to-pivot swings, without using future information before pivot confirmation.
- Fixed-range 64-bin profile from the completed swing low to high or high to low.
- M1 broker tick-volume distributed across the price bins crossed by each M1 candle.
- Keep an untouched FVG only when the POC is physically inside its boundaries.
- Wait for a directional rejection close at the POC, a close outside the FVG, or a wick-rejection variant.
- Enter at the next bar open.
- One open trade at a time, risking 1% of current equity.

## Search space

- Signal timeframe: M5, M15, M30
- Pivot confirmation: 3 or 5 bars
- Minimum swing impulse: 2, 3, or 4 ATR
- Minimum FVG size: 0.05, 0.10, or 0.20 ATR
- Entry confirmation: POC reclaim, FVG-edge reclaim, or POC wick rejection
- FVG expiration: 24 or 48 bars
- Stop: beyond FVG or beyond rejection candle
- Stop buffer: 0, 0.10, or 0.25 ATR
- Target: 1.5R, 2R, 2.5R, or 3R
- Maximum hold: 6, 24, or 72 hours
- Management: fixed stop or break-even after +1R

Selection used 2022–2024 development data and 2025 validation data. Parameters were frozen before the 2026 confirmation check.

## Test conditions

- MEXAtlantic-Demo CFD M1 data, January 2022 through August 2026
- Starting balance: $10,000
- Risk: 1% of current equity per trade
- Recorded broker spreads; zero spread records replaced by the symbol median
- Additional adverse slippage: 25% of the median spread on each entry and exit
- Conservative stop-first handling when stop and target occur inside the same M1 bar
- Drawdown includes M1 marked-to-market movement during open trades
- No commission was added because the available CFD specifications did not provide a reliable historical commission schedule

**Critical volume limitation:** all six broker symbols have zero real-volume history. The profiles therefore use broker quote tick-volume, not centralized traded volume. This is particularly weak for CFDs. BTC and ETH also do not have a single centralized global order book.

## Full-period results

| Status | Market | Best TF / RR | Trades | Win rate | PF | Total return | CAGR | Max DD |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| REJECT | XAU | M5 / 2.5R | 36 | 33.33% | 1.19 | +4.43% | +0.95% | 6.20% |
| REJECT | XAG | M5 / 3R | 42 | 16.67% | 0.47 | -18.53% | -4.36% | 23.52% |
| REJECT | US30 | M5 / 1.5R | 44 | 45.45% | 1.15 | +3.38% | +0.73% | 7.58% |
| REJECT | US100 | M5 / 2.5R | 34 | 29.41% | 0.99 | -0.78% | -0.17% | 8.40% |
| REJECT | BTC | M5 / 3R | 62 | 30.65% | 1.18 | +7.50% | +1.58% | 11.82% |
| REJECT | ETH | M5 / 2R | 23 | 17.39% | 0.29 | -13.59% | -3.12% | 15.70% |

## Locked 2026 confirmation

| Market | Trades | Win rate | PF | Return | Max DD | Finding |
|---|---:|---:|---:|---:|---:|---|
| XAU | 5 | 40.00% | 1.65 | +1.90% | 3.73% | Positive but too few trades |
| XAG | 6 | 33.33% | 1.44 | +1.73% | 3.62% | Recent recovery cannot repair the long-term loss |
| US30 | 4 | 25.00% | 0.49 | -1.57% | 3.04% | Failed |
| US100 | 2 | 0.00% | 0.00 | -2.11% | 2.11% | Failed and insufficient sample |
| BTC | 13 | 38.46% | 1.53 | +4.40% | 3.90% | Positive confirmation, but long-term CAGR only 1.58% |
| ETH | 1 | 100.00% | undefined | +1.88% | 1.19% | Meaningless one-trade sample |

## Best parameters found

| Market | Pivot | Impulse | Min FVG | Rejection | Expiry | Stop | Buffer | RR | Hold | BE |
|---|---:|---:|---:|---|---:|---|---:|---:|---:|---|
| XAU | 5 | 2 ATR | 0.20 ATR | POC reclaim | 48 bars | FVG edge | 0.10 ATR | 2.5 | 6h | No |
| XAG | 3 | 2 ATR | 0.05 ATR | FVG-edge reclaim | 24 bars | FVG edge | 0.25 ATR | 3.0 | 24h | No |
| US30 | 5 | 4 ATR | 0.20 ATR | FVG-edge reclaim | 48 bars | FVG edge | 0.25 ATR | 1.5 | 6h | No |
| US100 | 3 | 2 ATR | 0.10 ATR | POC reclaim | 48 bars | FVG edge | 0.10 ATR | 2.5 | 72h | No |
| BTC | 5 | 4 ATR | 0.10 ATR | POC reclaim | 48 bars | Rejection extreme | 0.10 ATR | 3.0 | 6h | No |
| ETH | 3 | 2 ATR | 0.05 ATR | FVG-edge reclaim | 48 bars | FVG edge | 0.10 ATR | 2.0 | 24h | No |

## Verdict

The concept is visually plausible but did not produce a portfolio-quality edge in this reproducible CFD test. BTC was the only market with a positive development/validation profile and a positive 2026 confirmation, but its 2023 result was negative, its full-period CAGR was only 1.58%, and maximum drawdown was 11.82%. That is far below the previously agreed 15%+ yearly return requirement.

No MQL5 EA was added to MT5 and no installer/BAT file was changed. The next scientifically useful test would use centralized futures volume: GC for gold, SI for silver, YM for US30, NQ for US100, and exchange-specific BTC/ETH spot or futures data. The CFD tick-volume result is not strong enough to justify deployment or paid data acquisition by itself.

## Saved artifacts

- `backtest_fvg_volume.py` — complete reproducible test engine
- `Results/summary.csv` — compact comparison
- `Results/all-results.json` — full parameters and period statistics
- `Results/all-markets-equity.png` — six-market equity chart
- `Results/<MARKET>-equity.png` — individual charts
- `Results/<MARKET>-selected-trades.csv` — trade-by-trade ledgers
- `Results/<MARKET>-development-screen.csv` — screened parameter results
- `source-video.mp4`, `source-video.wav`, and extracted chart frames — source-analysis artifacts
