# Long-Only VAH Rejection + Bullish Engulfing — Final Report

Completed: 2026-08-14  
Video: https://www.youtube.com/shorts/xGHhSs3ENyk  
Starting balance: USD 10,000  
Risk: 1.00% of current balance per trade  
Target: fixed 3R, exactly as stated in the video

## Final decision

**Reject for live deployment on all six markets. Do not add it to the active BAT.**

US30 and US100 looked strong before the locked confirmation period but both lost money in 2026. BTC was the only market with a meaningful positive 2026 sample, but its full annualized return was only 2.71%. XAU produced no 2026 trades at all.

## Video rules

The Short gives the following long-only setup:

1. Draw a volume profile from a swing low to swing high.
2. Mark Value Area High (VAH), Point of Control (POC), and Value Area Low (VAL).
3. Wait for price to reject VAH.
4. Require bullish-engulfing confirmation.
5. Enter long, place the stop below the setup low, and target 3R.

It does not define the swing algorithm, minimum leg size, value-area percentage, VAH tolerance, whether engulfing must touch VAH or follow a separate rejection, setup expiry, exact meaning of “the low,” or maximum holding time. Those missing definitions were screened without using 2026.

## Honest results

| Market | Best TF | Trades | Win rate | PF | Total return | CAGR | Max equity DD | 2026 trades | 2026 PF | 2026 return | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| XAU | H1 | 29 | 58.62% | 2.68 | +20.53% | +4.15% | 6.97% | 0 | 0.00 | 0.00% | Reject: no confirmation trades |
| XAG | H1 | 36 | 41.67% | 1.89 | +19.46% | +3.94% | 7.19% | 6 | 0.78 | -0.96% | Reject |
| US30 | H1 | 51 | 43.14% | 2.16 | +39.04% | +7.44% | 6.25% | 8 | 0.99 | -0.16% | Reject |
| US100 | H1 | 123 | 47.15% | 1.57 | +34.01% | +6.58% | 8.67% | 16 | 0.63 | -3.42% | Reject |
| BTC | H1 | 43 | 58.14% | 2.00 | +13.09% | +2.71% | 4.24% | 8 | 1.97 | +2.10% | Reject: CAGR below 15% |
| ETH | M30 | 32 | 34.38% | 1.37 | +8.08% | +1.70% | 8.19% | 1 | 999.00* | +1.25% | Reject: insufficient sample |

`*` ETH's 2026 PF is meaningless because it represents one winning trade and no losses.

Total return covers approximately January 2022 through August 2026. It is not a one-year return.

## Exact selected configurations

| Market | Pivot | Minimum leg | Structure | Value area | VAH tolerance | Confirmation timing | Expiry | Stop | Buffer | Hold |
|---|---:|---:|---|---:|---:|---|---:|---|---:|---:|
| XAU H1 | 2 | 2.5 ATR | Strict HH + HL | 60% | 0.05 ATR | VAH rejection, then engulf | 48 bars | Swing low | 0 ATR | 72h |
| XAG H1 | 5 | 3.5 ATR | Higher-high break | 80% | 0.15 ATR | VAH rejection, then engulf | 48 bars | Setup low | 0.25 ATR | 72h |
| US30 H1 | 5 | 1.5 ATR | Higher-high break | 80% | 0.15 ATR | Engulfing candle touches VAH | 12 bars | Setup low | 0.25 ATR | 72h |
| US100 H1 | 2 | 1.5 ATR | Higher-high break | 60% | 0.05 ATR | Engulfing candle touches VAH | 12 bars | Setup low | 0.25 ATR | 6h |
| BTC H1 | 2 | 1.5 ATR | Strict HH + HL | 60% | 0.15 ATR | VAH rejection, then engulf | 24 bars | Swing low | 0.10 ATR | 24h |
| ETH M30 | 5 | 3.5 ATR | Strict HH + HL | 60% | 0.15 ATR | VAH rejection, then engulf | 48 bars | Setup low | 0.10 ATR | 72h |

Every configuration kept the video's fixed 3R target and long-only direction. These are research finalists, not recommended live presets.

## Optimization and validation flow

1. Swing pivots were usable only after their right-side confirmation bars closed, preventing future leakage.
2. Tested M5, M15, M30, and H1; 2-, 3-, and 5-bar pivots; 1.5, 2.5, and 3.5 ATR legs; and relaxed versus strict bullish structure.
3. Constructed 64-row profiles and tested 60%, 70%, and 80% value areas.
4. Tested VAH tolerances of 0.05 and 0.15 ATR.
5. Tested engulfing on the VAH-touch candle versus engulfing within two candles after a separate bullish VAH rejection.
6. Invalidated the VAH-support setup if price closed below POC before entry.
7. Tested setup expiries of 12, 24, and 48 bars; setup-low versus swing-low stops; three stop buffers; and 6-, 24-, and 72-hour time exits.
8. Screened 72 structure definitions, up to 432 reaction/profile variants, and 288 execution variants per market.
9. Used 2022–2024 for development and 2025 for validation. The chosen parameters were then applied to untouched 2026.
10. Deployment required at least eight 2026 trades, 2026 PF >=1.05, positive 2026 return, 2026 DD below 15%, full PF >=1.05, and CAGR >=15%.

## Execution assumptions

- MEXAtlantic-Demo M1 broker history was used.
- Recorded spread plus an additional 25% of median spread as slippage was applied to every fill.
- Stop-first ordering was assumed when stop and target were both reachable in one M1 bar.
- Drawdown included minute-level marked-to-market equity.
- Only one position per market could be open at a time.
- Risk compounded at 1% of current equity.

## Volume limitation

These CFD histories contain no centralized real volume. The profiles use broker tick activity distributed across the price rows crossed by each M1 bar. TradingView also documents that POC is the highest-volume row and that its forex, index, and crypto-CFD profiles use tick volume: https://www.tradingview.com/support/solutions/43000502040-volume-profile-indicators-basic-concepts/

This approximation is appropriate for a reproducible CFD test, but it is not CME, COMEX, or exchange order-flow data.

## Saved files

- `Results/all-markets-equity.png` — combined graph
- `Results/<MARKET>-equity.png` — individual graph
- `Results/summary.csv` — comparison table
- `Results/<MARKET>-selected-result.json` — exact settings and period statistics
- `Results/<MARKET>-selected-trades.csv` — complete trades with POC, VAH, VAL, entry, stop, target, and R result
- `Results/<MARKET>-development-screen.csv` — optimization candidates
- `Results/all-results.json` — combined machine-readable report
- `backtest_vah_engulfing.py` — reproducible tester

## Deployment action

No MQL5 EA or `.set` file was promoted. `INSTALL AND RUN ON ACTIVE MT5.bat` remains unchanged.
