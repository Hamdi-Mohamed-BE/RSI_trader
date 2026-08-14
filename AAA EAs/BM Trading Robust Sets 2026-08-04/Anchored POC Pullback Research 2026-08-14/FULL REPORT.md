# Swing-Anchored Volume-Profile POC Pullback — Final Report

Completed: 2026-08-14  
Video: https://www.youtube.com/shorts/hEshGpglJUg  
Starting balance: USD 10,000  
Risk: 1.00% of current balance per trade

## Final decision

**No market passed the 15% annualized-return deployment requirement. The active EA installer was not changed.**

XAU and XAG produced genuine positive locked-2026 confirmation, so the underlying idea is more credible than a purely in-sample pattern. Their annualized returns were still only 9.94% and 8.24% respectively at 1% risk. US30, US100, and BTC deteriorated in 2026. ETH had no valid 2022–2025 selection edge.

## What the video actually teaches

The Short determines bullish or bearish sentiment from swing structure. For bullish structure, it anchors a volume profile from the most recent swing low to swing high; for bearish structure, from swing high to swing low. It identifies the Point of Control (POC), waits for price to retrace to that level, requires a reaction, and trades continuation in the original direction.

The video does not define pivot sensitivity, minimum leg size, POC row count, POC tolerance, the exact reaction candle, setup expiry, stop placement, reward/risk, maximum hold time, or trade management. Those variables were screened explicitly rather than chosen after seeing the final data.

## Honest results

| Market | Best TF | Trades | Win rate | PF | Total return | CAGR | Max equity DD | 2026 trades | 2026 PF | 2026 return | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| XAU | H1 | 204 | 33.82% | 1.51 | +54.57% | +9.94% | 10.76% | 31 | 1.11 | +1.36% | Reject: CAGR below 15% |
| XAG | H1 | 163 | 46.63% | 1.48 | +43.94% | +8.24% | 12.56% | 23 | 1.45 | +4.99% | Reject: CAGR below 15% |
| US30 | M30 | 252 | 29.37% | 1.24 | +27.63% | +5.46% | 10.08% | 35 | 0.99 | -0.30% | Reject: failed confirmation |
| US100 | M30 | 292 | 40.75% | 1.24 | +47.27% | +8.79% | 12.42% | 42 | 0.90 | -3.11% | Reject: failed confirmation |
| BTC | H1 | 224 | 36.61% | 1.14 | +16.51% | +3.38% | 18.68% | 45 | 0.55 | -13.31% | Reject: failed confirmation |
| ETH | H1 | 193 | 35.23% | 0.72 | -13.99% | -3.22% | 19.42% | 34 | 1.07 | +0.41% | Reject: no development edge |

The “total return” covers roughly January 2022 through August 2026. It must not be confused with a one-year return.

## Exact selected configurations

All six selected strict swing structure: bullish requires a higher high and higher low; bearish requires a lower low and lower high. Every selected stop was beyond the opposite swing origin, not merely the reaction candle.

| Market | Pivot | Minimum leg | POC reaction | POC tolerance | Setup expiry | Stop buffer | Target | Max hold | Management |
|---|---:|---:|---|---:|---:|---:|---:|---:|---|
| XAU H1 | 5 bars | 2.5 ATR | Directional wick rejection | 0.05 ATR | 48 bars | 0.25 ATR | 3.0R | 72h | Break-even at +1R |
| XAG H1 | 5 bars | 3.5 ATR | Close through previous bar after POC touch | 0.05 ATR | 12 bars | 0.10 ATR | 2.5R | 72h | Fixed |
| US30 M30 | 5 bars | 2.5 ATR | Directional wick rejection | 0.15 ATR | 24 bars | 0 ATR | 2.0R | 72h | Break-even at +1R |
| US100 M30 | 3 bars | 3.5 ATR | Directional body >=55% of candle | 0.05 ATR | 12 bars | 0 ATR | 2.0R | 72h | Fixed |
| BTC H1 | 2 bars | 3.5 ATR | Close through previous bar after POC touch | 0.05 ATR | 24 bars | 0.10 ATR | 2.5R | 72h | Fixed |
| ETH H1 | 2 bars | 3.5 ATR | Directional body >=55% of candle | 0.05 ATR | 12 bars | 0.10 ATR | 1.5R | 6h | Break-even at +1R |

These are research finalists, not recommended live presets.

## Test and optimization protocol

1. A pivot was considered known only after its required right-side bars closed. This prevents future leakage.
2. Bullish structure required a break above the previous swing high; strict mode additionally required a higher swing low. Bearish logic was mirrored.
3. The completed swing leg had to measure at least 1.5, 2.5, or 3.5 ATR.
4. A 64-row fixed-range profile was built from M1 activity across the confirmed swing leg. The highest-activity row became POC.
5. Four reaction definitions were tested: directional POC reclaim, wick rejection, strong directional body, and a close through the previous bar after touching POC.
6. POC tolerances of 0.05 and 0.15 ATR and expiries of 12, 24, and 48 bars were tested.
7. Stops at the swing origin or reaction extreme, three stop buffers, five targets from 1R to 3R, three time exits, and fixed versus +1R break-even management were tested.
8. The workflow screened 72 structure bases, up to 288 reaction variants, and 2,880 execution combinations per market.
9. Parameters were developed on 2022–2024 and validated on 2025. The chosen configuration was then tested on untouched 2026 data.
10. Deployment required at least eight 2026 trades, 2026 PF >=1.05, positive 2026 return, 2026 DD below 15%, full PF >=1.05, and CAGR >=15%.

## Execution assumptions

- MEXAtlantic-Demo M1 broker history was used.
- Recorded spread was applied on each M1 bar, plus 25% of the median spread as additional slippage per fill.
- Stop-first ordering was assumed if stop and target were both reachable in the same minute.
- Drawdown included minute-by-minute marked-to-market equity.
- Only one position per market could be active at a time.
- Risk compounded at 1% of current balance.

## Important volume limitation

The six CFD histories report zero centralized `real_volume`. The profile therefore uses broker tick activity. Each M1 bar's activity is distributed over the price rows crossed by that bar. This is a reproducible approximation, but it is not CME/COMEX order-flow volume.

TradingView likewise documents that volume profile uses lower-timeframe data, defines POC as the price row with the greatest volume, and uses tick volume for forex, indices, and crypto CFDs: https://www.tradingview.com/support/solutions/43000502040-volume-profile-indicators-basic-concepts/

## Saved files

- `Results/all-markets-equity.png` — six-market equity graph
- `Results/<MARKET>-equity.png` — individual graph
- `Results/summary.csv` — compact comparison
- `Results/<MARKET>-selected-result.json` — exact parameters and all period metrics
- `Results/<MARKET>-selected-trades.csv` — complete trade list including POC, entry, stop, target, and R result
- `Results/<MARKET>-development-screen.csv` — optimization candidates
- `Results/all-results.json` — combined machine-readable report
- `backtest_anchored_poc.py` — reproducible tester

## Deployment action

No MQL5 EA was promoted and `INSTALL AND RUN ON ACTIVE MT5.bat` was left unchanged. XAU and XAG are suitable for further research or forward observation, but neither meets the current active-system gate.
