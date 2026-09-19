# XAU D14 / H1 / M5 — full optimization protocol

Scope: XAUUSD only, Exness Zero native MT5 research. No US100 optimization, live installation, BAT, website or broker changes. Raw research files remain unchanged. This protocol is saved before optimization results are inspected.

## Evidence separation

- Development: 2021-09-05 to 2024-09-05 exclusive.
- Selection validation: 2024-09-05 to 2025-09-05 exclusive.
- Search-excluded final year: 2025-09-05 to 2026-09-05 exclusive. The raw strategy's result in this period has ALREADY been seen; this is not a genuinely unseen or prospective holdout.
- Final display: the existing 6m/1y/3y/5y windows ending 2026-09-05 exclusive, each independently restarted at $10,000.
- Both training and validation lack 2026 real ticks. Real-tick mode will be requested for confirmation, but earlier history is partly/generated, not claimed full-quality real ticks.

## Frozen search sequence

1. Parameterize a tester-only copy of the raw EA. Prove raw-default 6m parity before using optimized results.
2. Native M1-OHLC development SCREEN only: 48 structural combinations (H1 pivot 1/2, M5 pivot 1/2, wick/full-candle zone, strict-body/close-only wick rejection, both/long/short direction). D1 fourteen-bar direction and at least two wicks are retained.
3. On the three best development structural settings: stop buffer {0, 0.10, 0.25} M5 ATR(14) beyond the last swing, and TP {0.75, 1, 1.5, 2, 3} R. The one-tick buffer is always retained. Maximum 45 exit combinations.
4. On the two best resulting development settings: no management, break-even at 1R, 1R-distance trail after 1.5R, confirmed M5 structural trailing after 1R, or a 6/24-hour time stop. Up to twelve combinations. Trailing management is evaluated once per new completed M5 bar; stops execute on tester ticks.
5. On the best development setting: holding windows 4/5 candles (still at least two rejection wicks), zone age 8/24h, and entry sessions 06–16 or 12–20 broker hours. These are transparent extensions, not a claim of exact video replication.
6. Select five distinct development finalists by a predeclared score that penalizes low sample size/drawdown and rewards net PF/return. Re-run each in native requested real-tick mode on DEVELOPMENT and VALIDATION. Choose one using both periods; preference requires >=30 development and >=10 validation closed trades and positive net/PF>1 in both. If none qualifies, identify the least-bad research candidate but explicitly fail promotion.
7. Freeze the selected configuration before its final-year/display reports. Do not retune after these reports. Run all four display windows, plus 0.5%-risk final-year/5y controls and 500/2000 ms fixed-delay final-year stress.
8. Check eight one-parameter neighbours on the selection-validation window, without selecting a new winner from them.
9. Restricted-family chronological walk-forward: eight ANTECEDENT fixed structural anchors (two M5 spans x wick/full-candle x both/long; H1 span two; close-only rejection for full-candle, strict for wick). For each of three folds, select from its own prior two years using native OHLC screening; run that fold's winning configuration over the next year in native requested real-tick mode. This is a smaller-family stability audit, not a claim that the full staged search was reoptimized in each fold. All anchor membership is fixed before results.
10. Enhanced Calyx audit: 10,000 block-bootstrap paths, Wilson win-rate interval, multi-test-corrected Sharpe, chronological stability and closed-P&L prop-risk proxies. Count ALL unique inspected parameter combinations, including neighbours/anchors/risk/delay alternatives, conservatively. Also run trade-specific cost sensitivity: one additional measured entry bid/ask spread, +50% recorded commission and double negative recorded swap. These are hypothetical stresses, not measured future slippage.

## Selection score

If fewer than 15 development trades, score = -10000 + trades. Otherwise score = 25*ln(net PF) + 0.12*net return percent - 1.2*maximum relative equity DD percent - 0.2*max(0,50-trades). Infinite PF is capped at 5 for ranking. Final selection is min(development score, validation score with low-sample threshold 5 and target 15), then mean score as tie-breaker, preferring the joint eligibility gate above. Sample thresholds are research filters, not proof of statistical confidence.

## Risk/costs/guardrails

- $10,000, 1% equity target, broker lot rounding UP/min lot, same Exness leverage 1:2000. Risk is not optimized upwards. Safe controls only reduce nominal risk to 0.5%; lot rounding may prevent exact halving.
- Native spread, commission, swap and floating equity DD; default fixed execution delay 1 ms. Model-1 screens are preliminary; final results use model 4 and disclose actual real-tick coverage.
- One position at a time, no grid/martingale, no stop widening, no discretionary forced fills. Log rejected/market-closed signals.
- No new macro/Markov gate: this is a price-structure strategy, not news trading. Do not add unrelated signals simply to improve history.
- Promotion requires positive development, validation, final-year and cost-stressed final-year net; final-year PF>=1.20 with >=30 trades and equity DD<=15%; >=60% positive neighbours; positive concatenated walk-forward result and >=2/3 profitable folds; bootstrap 5th-percentile return positive and common Calyx gates clear. Low data quality/previously seen history still prevents a claim of live readiness.
- Even a pass authorizes only a recommendation for isolated demo forward testing, not installation. Failed gates are reported, never optimized away using final-year data.
