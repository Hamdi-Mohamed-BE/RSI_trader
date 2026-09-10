# XAU Squeeze Momentum — final 1% research verdict

Research completed on 2026-09-10. No website, BAT installer, active MT5 profile, or live account was changed.

## Deployment addendum — user approved 2026-09-10

After reviewing the research, the user approved three saved choices for the shared system: Standard (3.5 ATR / 1.5R), High Win (3 ATR / 0.75R), and Safe (Standard plus the completed-D1 gate). The website and shared BAT installer now expose those choices. Static BATs default to 1% risk and dynamic-risk BATs replace that value with the user's input. This approval does not change the evidence verdict below: the EA remains demo/watch-only, and the exact 0.75R choice has development evidence rather than a standalone untouched validation.

## Verdict

- **Highest defensible win rate:** Safe/Markov at 1% risk — `WATCH_ONLY`.
- **Best broad-evidence version:** Standard at 1% risk — `WATCH_ONLY`.
- **Not guaranteed profitable and not approved for the active portfolio.** Safe mode has the best statistics, but only 13 locked real-tick trades. Standard mode has more total evidence but weak recent subperiod stability.
- The literal 5% risk specification is rejected for deployment because three-year max drawdown reached 32.32%.

## Final results

All win rates and trade counts below are position-level. Partial exits were aggregated back into their original position.

| Version / evidence window | Return | PF | Win rate | Max equity DD | Trades |
|---|---:|---:|---:|---:|---:|
| Raw literal 5% — 3Y | +217.69% | 1.50 | 40.74% | 32.32% | 162 |
| Raw literal 5% — 5Y | +426.40% | 1.50 | 40.08% | 32.53% | 247 |
| Raw literal 5% — locked real ticks | +0.00% | 0.00 | 0.00% | 0.00% | 0 |
| Standard 1% — development | +25.25% | 2.35 | 50.00% | 2.73% | 74 |
| Standard 1% — purged validation | +3.63% | 1.38 | 34.38% | 4.99% | 32 |
| Standard 1% — locked real ticks | +3.87% | 1.79 | 50.00% | 2.43% | 18 |
| Standard 1% — 3Y | +22.75% | 1.87 | 45.35% | 5.69% | 86 |
| Standard 1% — 5Y | +33.22% | 1.83 | 45.31% | 5.69% | 128 |
| Standard 1% — random delay | +22.40% | 1.85 | 45.35% | 5.81% | 86 |
| Standard 1% — fixed 500 ms | +22.72% | 1.87 | 45.35% | 5.71% | 86 |
| Safe 1% — development | +12.04% | 3.98 | 61.90% | 2.47% | 21 |
| Safe 1% — purged validation | +3.51% | 1.96 | 50.00% | 3.06% | 14 |
| Safe 1% — locked real ticks | +5.24% | 2.89 | 61.54% | 1.60% | 13 |
| Safe 1% — 3Y | +22.60% | 3.89 | 65.79% | 3.36% | 38 |
| Safe 1% — 5Y | +23.00% | 3.16 | 60.42% | 3.35% | 48 |
| Safe 1% — random delay | +22.62% | 3.89 | 65.79% | 3.34% | 38 |
| Safe 1% — fixed 500 ms | +22.60% | 3.89 | 65.79% | 3.36% | 38 |
| High Win 0.75R — development selection | +16.54% | 1.88 | 60.76% | 3.01% | 79 |
| High Win 0.75R — post-selection 3Y | +10.10% | 1.40 | 54.44% | 5.01% | 90 |
| High Win 0.75R — post-selection 5Y | +19.89% | 1.52 | 56.30% | 5.25% | 135 |
| XAG frozen standard 1% — 3Y | +14.16% | 1.97 | 50.85% | 2.27% | 59 |
| XAG frozen standard 1% — locked real ticks | +3.02% | 2.11 | 54.55% | 1.78% | 11 |

## Recommended settings

Both versions use completed H1 signals only, long direction, all UTC hours Monday–Friday, and 1% equity risk.

| Component | Final value |
|---|---|
| Squeeze | BB length 24, multiplier 1.8; KC length 24, multiplier 1.3 |
| Momentum | LazyBear-style linear-regression momentum, length 28, positive and rising |
| Trend | Close above SMA 200 |
| Volatility | Wilder ATR 14 |
| Initial stop | 3.5 ATR |
| Take profit | 1.5R |
| Trailing stop | Ratcheting 3.5 ATR on completed H1 bars |
| Momentum exit | Exit when negative or when strength falls by more than 50% |
| Breakeven / partial | Off |
| Effective leverage cap | 9.8x |

Safe mode adds the completed-D1 no-lookahead Markov gate: 40-day return labels, ±5% Bull/Bear threshold, minimum 252 labels, and a directional probability signal greater than 0.05.

## Statistical stress audit

### Standard 1%

- Locked bootstrap probability of profit: 86.42%; return P5: -1.80%; PF P5: 0.64.
- Locked win-rate Wilson 95% interval: 29.03%–70.97%.
- Recent-half PF: 0.93; only one of three locked subperiods was profitable.
- Three-year 10,000-path block Monte Carlo: return P5 +7.36%; DD P95 7.96%; 10% total-loss proxy breach 0.30%.
- Extra measured-spread stress retained PF 1.78.
- Verdict: `WATCH_ONLY`.

### Safe 1%

- Locked bootstrap probability of profit: 95.95%; return P5: +0.25%; PF P5: 1.03.
- Locked win-rate Wilson 95% interval: 35.52%–82.29%.
- Recent-half PF: 1.11; all three locked subperiods were profitable.
- Three-year 10,000-path block Monte Carlo: return P5 +12.20%; DD P95 3.59%; 10% total-loss proxy breach 0.00%.
- Extra measured-spread stress retained PF 2.89.
- Deflated Sharpe confidence is only 24.73% after accounting for 135 tested configurations, and the locked sample is below the 30-trade minimum.
- Verdict: `WATCH_ONLY`.

## Failed high-win-rate shortcuts

- A 0.5R target reached 67.90% wins in development but lost in both purged validation (−0.27%, PF 0.97) and locked real ticks (−0.09%, PF 0.98). Rejected.
- The partial-at-2R version reached 65.33% position wins in development, but completed zero locked trades. Rejected.

## Evidence design and costs

- Development: 2021-09-01 to 2024-08-31.
- Purged validation: 2024-09-07 to 2025-08-31.
- Locked test: 2025-09-07 to 2026-09-01, every tick based on real ticks.
- Three-year context: 2023-09-01 to 2026-09-01.
- Five-year context: 2021-09-01 to 2026-09-01.
- MT5 historical spread, commission, and swap are included. Random-delay and fixed-500-ms execution stresses were also run, plus an additional measured-spread cost stress.
- Locked real-tick history quality is 67%, which is another reason not to call this deployable proof.
- Mandatory XAG evidence gate passed; XAG is positive but also has only 11 locked trades.

## Practical conclusion

If one version is forward-tested, use **Safe 1%**. It has the best win rate, PF, drawdown, delay resilience, bootstrap tail, and subperiod behavior. Keep **Standard 1%** as the broader-trade benchmark. Require at least 30 new forward/locked trades before reconsidering system inclusion.
