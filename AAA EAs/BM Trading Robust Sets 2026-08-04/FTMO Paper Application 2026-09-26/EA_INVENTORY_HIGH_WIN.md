# EA inventory and high-win / win-streak shortlist

Read-only-source review, 27 September 2026. No MT5 connection, optimization, fresh native tests, trades or launcher changes.

## What is available

The current installer contains 34 entries. This means configured for installation, NOT confirmed attached or running on the connected account. Standard/Safe/DI variants are not necessarily distinct entry strategies.

### XAUUSD (19)

- Gold Overnight Value Area
- LTA Volume Profile
- ORB Volume Profile
- ORB Volume Profile Volume Confirmed
- XAU ORB New York M30
- XAU ORB London NY Overlap M30
- AAA Final Asia Breakout
- DMC Current XAU
- DMC Fresh Reaction XAU
- AAA Final EMA3
- AAA Final XAU Weakness
- XAU Squeeze Momentum Standard
- News Pulse XAU
- Gold News V9 Direction
- XAU RSI VWAP
- XAU Trend Progression
- XAU Elliott Wave 1-2-3
- XAU Slow Trend
- XAU Regime Switch

### BTCUSD (3)

- BTC Top Down FVG Liquidity
- BTC POC Fibonacci
- News Pulse BTC

### ETHUSD (1)

- ETH Top Down FVG Liquidity

### USTEC (8)

- US100 ORB New York M30
- US100 H1 ORB 13UTC
- US100 Selective ORB V3
- DMC Fresh Reaction US100
- Nasdaq Overnight
- Nasdaq 5M Candle Momentum
- Sell Nasdaq 15min
- US100 Month End Flow

### USDJPY (1)

- USDJPY London Open Momentum

### XAGUSD (1)

- News Pulse XAG

### EURUSD (1)

- News Pulse EURUSD

### Saved outside the current launcher

- ORB Volume Profile High Win 0.75R
- XAU Squeeze Momentum High Win 0.75R
- Engineered Liquidity XAU
- XAG Session VWAP Snapback
- 3 Way Gold and 3 Way Volume Profile research families; research presence is not deployment approval.

The website still has cached evidence for the first four. Their removal is not reversed by this review.

## Native saved one-year evidence

Standalone broker tests, NOT FTMO portfolio outcomes. Each row uses its saved settings/sizing; most are nominal 1% equity risk. Different window endpoints (1–18 September 2026) and initialization prevent treating this as a perfectly matched leaderboard. DD is the saved native-reported equity drawdown metric, not newly replayed FTMO equity. Winning streaks are historical maxima, not expected future runs.

| EA | Window | Trades | Trades/week | Win rate | PF | Reported DD | Longest wins/losses | Return |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Gold Overnight Value Area — raw | 2025-09-19–2026-09-18 | 200 | 3.83 | 74.00% | 1.56 | 4.00% | 11/3 | +22.26% |
| EMA3 — Full Safe | 2025-09-05–2026-09-05 | 37 | 0.71 | 70.27% | 2.71 | 3.33% | 9/4 | +16.27% |
| EMA3 — Standard | 2025-09-05–2026-09-05 | 39 | 0.75 | 69.23% | 2.55 | 3.52% | 9/3 | +17.09% |
| ORB Volume Profile — 0.75R (saved; not current launcher) | 2025-09-05–2026-09-05 | 51 | 0.98 | 70.59% | 1.63 | 3.10% | 7/2 | +7.08% |
| Nasdaq Overnight | 2025-09-05–2026-09-05 | 72 | 1.38 | 62.50% | 1.80 | 2.40% | 10/3 | +8.28% |
| Gold RSI VWAP | 2025-09-05–2026-09-05 | 46 | 0.88 | 71.74% | 1.38 | 3.50% | 7/3 | +4.07% |
| XAU Squeeze Momentum — Safe | 2025-09-01–2026-09-01 | 14 | 0.27 | 64.29% | 3.27 | 1.58% | 6/2 | +6.26% |
| DMC Fresh Reaction US100 | 2025-09-01–2026-09-01 | 12 | 0.23 | 66.67% | 1.88 | 2.99% | 4/1 | +3.68% |
| Nasdaq 5M — Claude DI | 2025-09-07–2026-09-07 | 189 | 3.62 | 44.97% | 1.45 | 10.82% | 11/10 | +63.11% |
| US100 Selective ORB V3 | 2025-09-05–2026-09-05 | 5 | 0.10 | 80.00% | 1.60 | 3.68% | 2/1 | +1.75% |

## Recent equal-risk stress check

2 March–30 August 2026, standalone saved trades before portfolio admissions. Each trade is normalized by its reconstructed initial stop risk. PF is calculated from net R, not unequal dollar positions. Same adverse execution assumptions as the FTMO study: gross wins -10%, losses +10%, extra slippage, commission floors and conservative carry. No lot rounding, combined exposure gates or probability simulation in this table.

| EA | Trades | Win rate | Stressed PF (net R) | Sum R | Longest wins/losses |
|---|---:|---:|---:|---:|---:|
| Gold Overnight Value Area — raw | 100 | 74.00% | 1.55 | +7.39 | 11/3 |
| EMA3 — Full Safe | 17 | 52.94% | 1.10 | +0.89 | 4/4 |
| EMA3 — Standard | 21 | 47.62% | 0.91 | -1.08 | 4/4 |
| ORB Volume Profile — 0.75R (saved; not current launcher) | Unavailable: incomplete audited stop/cost ledger | — | — | — | — |
| Nasdaq Overnight | 56 | 62.50% | 1.25 | +2.60 | 10/3 |
| Gold RSI VWAP | 32 | 68.75% | 0.85 | -1.67 | 7/2 |
| XAU Squeeze Momentum — Safe | 0 | — | — | 0 | — |
| DMC Fresh Reaction US100 | 5 | 60.00% | 1.69 | +1.55 | 2/1 |
| Nasdaq 5M — Claude DI | 90 | 37.78% | 0.89 | -6.87 | 3/10 |
| US100 Selective ORB V3 | 3 | 66.67% | 0.69 | -1.00 | 1/1 |

The saved 0.75R ORB ledger was excluded from the prior portfolio preparation because it lacks complete native cost/volume/price fields. Its headline win rate is evidence to investigate, not proof it improves a jointly traded FTMO portfolio.

## Gold News V9: highest reported win rate, different evidence quality

The archived Execution V2 replay reports 27 wins/29 releases (93.10%), PF 3.17, +4.69% at nominal 1% risk, and 1.17% tick-equity DD. Recomputed longest streaks: 13 wins and 1 loss. Execution settings were selected on 20 releases; nine later releases produced 8 wins (88.89%), PF 1.883 and +0.89%. This is an execution holdout, not an independent audit of every model-training input.

Configuration: prediction T-15 minutes, entry T-10 seconds, $20 gold-price stop, $4 target, time exit T+15 minutes. Runtime currently defaults to 0.75% risk; the cited replay is 1%. Full-year data ends with the 4 September 2026 NFP; only 29 events, roughly 0.56/week.

The replay uses archived ticks plus M1 continuation where needed. Spread and tick gaps are included, but commission, network delay, rejection and market-depth impact are not. TP overshoot assumptions need checking. This is NOT a comparable fully costed native MT5 portfolio test. Do not advertise 93% as established live performance.

The 0.2R target requires 83.33% wins just to break even before costs if every winner earns 0.2R and every loser loses 1R. Five nominal TP wins offset one nominal stop. It trades the same gold news events as News Pulse, so adding it does not provide independent event diversification.

## Five-year context for the shortlist

| EA | Trades | Win rate | PF | Reported DD | Longest wins/losses |
|---|---:|---:|---:|---:|---:|
| Gold Overnight Value Area — raw | 1027 | 68.35% | 1.04 | 28.90% | 12/5 |
| EMA3 — Full Safe | 102 | 60.78% | 1.86 | 5.03% | 8/4 |
| EMA3 — Standard | 209 | 57.89% | 1.53 | 7.50% | 12/6 |
| ORB Volume Profile — 0.75R (saved; not current launcher) | 304 | 64.14% | 1.13 | 12.71% | 11/4 |
| Nasdaq Overnight | 199 | 56.28% | 1.28 | 4.83% | 10/7 |
| Gold RSI VWAP | 260 | 73.46% | 1.37 | 5.34% | 14/3 |
| XAU Squeeze Momentum — Safe | 48 | 60.42% | 3.16 | 3.35% | 7/4 |
| DMC Fresh Reaction US100 | 82 | 58.54% | 1.39 | 7.57% | 8/3 |
| Nasdaq 5M — Claude DI | 971 | 40.27% | 1.21 | 10.80% | 11/12 |
| US100 Selective ORB V3 | 34 | 67.65% | 3.16 | 3.67% | 4/2 |

Different native start dates/warm-up and sizing can alter histories, so a five-year standalone run is not guaranteed to reproduce every trade in a separately initialized one-year run. Two five-year native headline win rates differ from net-ledger win rates: Nasdaq DI is 40.27% reported vs 40.16% net, and Selective ORB is 67.65% reported vs 64.71% net. All one-year shortlisted rates match the net ledger; streaks are net-outcome streaks.

## Proposed research order, not deployment approval

1. Core + Nasdaq Overnight alone. Different session and positive recent stressed net-R expectancy; longer two-year stress was approximately flat, so this is not an established edge. Do not confuse with Nasdaq 5M DI.
2. Core + EMA3 Full Safe alone. Good one-year metrics and stronger five-year PF; recent stress is weak (17 trades, PF about 1.10). Shared gold exposure and carry require a cap.
3. Reconstruct the saved 0.75R ORB native costs/stops, then consider it alone with the core. Shares signals with the original ORB; do not count them as independent diversification.
4. Audit Gold News V9 execution and point-in-time model inputs before any FTMO probability claim. Same-event XAU risk must be pooled with Pulse.

Do not add RSI VWAP or full-risk Nasdaq DI solely for headline wins/streaks: the prior matched portfolio simulation worsened six-month payout outcomes. US100 Selective ORB V3 has 80% wins on only five yearly trades, and Squeeze Safe had no trades in the last six-month audited pool; neither supplies reliable daily activity.

The completed 3 Way Volume Profile research does not supply an obvious high-win replacement: most optimized variants failed older validation or the latest-year comparison. USDJPY VA reversal, for example, had 58.3% wins but lost 4.29% in the comparison year.

Any next comparison should use a strict per-trade dollar ceiling with lot rounding DOWN (skip if minimum lot exceeds the cap), since the inherited $71.43 model rounded UP. Keep aggregate risk fixed when adding an EA and evaluate daily equity, margin, correlated losses, pass/payout and stalled-account rates—not win rate alone.

FTMO permits EAs subject to legitimate execution and risk/practice rules; permission for a specific pre-news approach is not established merely by the general EA permission: [official rules](https://ftmo.com/en/faq/which-instruments-can-i-trade-and-what-strategies-am-i-allowed-to-use/).

## Checks

Recomputed counts and W/L streaks match all 20 shortlisted cached windows; net win rates match 18/20, with the two five-year differences disclosed above. Verified Nasdaq DI build and SET hashes. Recomputed V9 wins/streaks from its 29-trade replay. Source hashes preserved in EA_INVENTORY_HIGH_WIN.json.
