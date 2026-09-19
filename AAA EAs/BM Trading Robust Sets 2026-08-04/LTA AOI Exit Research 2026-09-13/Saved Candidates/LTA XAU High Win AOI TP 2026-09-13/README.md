# LTA XAU High Win AOI TP — saved candidate

Saved 2026-09-13 at the user's request. **Research only; not deployed and not prop-firm validated.** The current 3R configuration, website and installers remain unchanged.

This is case 3, **Nearest day/week TP**, from the completed LTA AOI exit comparison. It had the highest win rate among the practical repeated-trade variants in all four tested windows. This does not mean highest profitability or lowest drawdown. The frozen-trail diagnostic's one-trade 100% result is not a useful selection basis.

## Frozen rules

- XAUUSD, M15; unchanged original LTA entry rules, initial stop and one-position-per-symbol behavior.
- Choose the nearest favorable previous-day or previous-week POC, VAH or VAL beyond the broker's minimum stop distance. Freeze TP at entry.
- If no qualifying level exists, retain the original 3R TP. In the 3-year test, 513 entries used an AOI target and 168 used the 3R fallback.
- 64 profile bins, 70% value area, completed broker day/week exit profiles; real volume if available, otherwise broker tick volume. This is not OANDA or centralized exchange gold volume.
- No AOI trailing and no generic dynamic trailing. Original applicable break-even logic remains unchanged.
- Preserve the tested 1% equity risk inputs and Safe Markov filter. Account-wide adaptive controls were OFF for this isolated comparison.
- Current lot-round-up/minimum-lot behavior can exceed the nominal risk input: observed maximum planned risk was 1.41% in the 3-year run and 1.82% in the 5-year run. Costs and gaps can add further loss.

## Saved evidence

Independent $10,000 starting balances; Exness Zero demo feed; all periods end 2026-09-05 exclusive. Results are net of recorded commission, swap and fees. Equity drawdown is the larger of native MT5 relative equity drawdown and the independent every-tick observer.

| Window | Start | Trades | Net win rate | Net return | Net PF | Max equity DD |
|---|---|---:|---:|---:|---:|---:|
| 6 months | 2026-03-05 | 177 | 53.67% | +11.14% | 1.117 | 10.82% |
| 1 year | 2025-09-05 | 371 | 53.10% | +31.48% | 1.137 | 18.93% |
| 3 years | 2023-09-05 | 681 | 53.60% | +104.10% | 1.201 | 16.49% |
| 5 years | 2021-09-05 | 939 | 51.65% | +30.95% | 1.068 | 42.37% |

Recorded commission / swap: 6m -$84.52 / -$11.76; 1y -$220.23 / -$95.18; 3y -$875.92 / -$529.44; 5y -$976.89 / -$460.93.

Native MT5 model 4 was requested with 1 ms delay. Older history can contain generated ticks; recorded tester costs are not a reconstruction of every historical fee or high-margin requirement. Periods overlap and are not independent out-of-sample validations. Tiny AOI targets can have very low reward-to-risk. No new optimization or backtest was run to save this package.

## How to retrieve or test later

Ask for **LTA XAU High Win AOI TP**.

Load [LTA XAU High Win AOI TP - RESEARCH ONLY.set](LTA%20XAU%20High%20Win%20AOI%20TP%20-%20RESEARCH%20ONLY.set) with the matching frozen EA in the MT5 Strategy Tester. The EA source default is case 0: **the saved SET must be loaded to select case 3**. The fixed SET contains no optimization ranges. Only the exit-case selector and audit output ID differ from the source batch SET.

The unchanged EA deliberately refuses live-chart initialization. Do not remove that guard or load this SET into the ordinary LTA EA: the exit logic depends on the matching research EA. Future live deployment requires a separately reviewed implementation and explicit approval.

Before any prop-firm use, retest firm-specific daily and total equity loss limits, margin/leverage, simultaneous portfolio risk, execution/cost stress and broker data. The 42.37% historical drawdown at the tested risk makes this **not prop-ready**; lowering risk alone is not proof of compliance.

## Package contents and integrity

- EA/: exact copied source, compiled binary and dependencies; no source defaults changed.
- Evidence/: four case-3 run records, ledgers, audit exports and native batch XML reports (the XMLs also contain other comparison cases), plus frozen protocol and full research results.
- manifest.json: file hashes, evidence provenance, fixed settings checks and period metrics.
- The original research remains in the parent research folder. No BAT, website, terminal deployment or Git push was performed for this save request.
