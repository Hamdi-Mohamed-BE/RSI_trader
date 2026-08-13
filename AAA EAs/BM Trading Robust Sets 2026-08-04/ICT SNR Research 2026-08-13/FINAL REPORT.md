# ICT + SNR Liquidity-Reversal Research — Final Report

## Honest verdict

The mechanical ICT + support/resistance combination did **not** pass out-of-sample validation for live deployment. XAG and US30 were marginally profitable, but neither produced enough return or profit-factor margin to survive realistic uncertainty. XAU and US100 lost money; US100 failed decisively.

No active BAT, installation pipeline, or live MT5 portfolio was changed.

## Untouched one-year validation

- Period: 2025-08-11 through 2026-08-10
- Starting balance: USD 10,000 per independent market test
- Risk: 1% of current equity per trade; one position per symbol
- Execution: Exness MT5, full Every Tick simulation from broker M1 history, random execution delay
- History quality: 99–100%
- Settings: selected only on 2023-08-11 through 2025-08-10, then frozen
- Real-tick limitation: Exness-MT5Trial16 canceled historical real-tick downloads. Invalid zero-bar reports were rejected, not counted. Final validation therefore uses MT5-generated intrabar ticks from broker M1 data, not broker-recorded tick history.

| Market | Chart | Final balance | Net / return | Max equity DD | PF | Win rate | Trades | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| XAU | M15 | $9,752.71 | $-247.29 / -2.47% | 6.06% | 0.52 | 20.00% | 10 | REJECT |
| XAG | M5 | $10,193.82 | $193.82 / +1.94% | 6.09% | 1.12 | 44.83% | 29 | WEAK / WATCH |
| US30 | M1 | $10,419.43 | $419.43 / +4.19% | 8.10% | 1.15 | 52.73% | 55 | WEAK / WATCH |
| US100 | M1 | $7,747.07 | $-2,252.93 / -22.53% | 24.66% | 0.43 | 36.76% | 68 | REJECT |

## Training-to-validation stability

| Market | Training return / PF / trades | Validation return / PF / trades | Assessment |
|---|---:|---:|---|
| XAU | +14.13% / 2.44 / 30 | -2.47% / 0.52 / 10 | Edge reversed; reject. |
| XAG | +1.45% / 1.25 / 9 | +1.94% / 1.12 / 29 | Positive but training and validation samples remain too weak. |
| US30 | +12.42% / 1.87 / 31 | +4.19% / 1.15 / 55 | Best survivor, but PF 1.15 leaves little margin for costs or regime change. |
| US100 | +14.08% / 1.67 / 42 | -22.53% / 0.43 / 68 | Severe regime failure; reject. |

## Mechanical strategy tested

1. Build zones from the prior-day high/low, completed Asian range, previous week, and confirmed H1 swings.
2. Increase a zone's score when independent levels cluster and recent closed candles reject it.
3. During the configured London/New York window, require a liquidity sweep beyond the zone followed by a close back through it.
4. Require a closed-bar market-structure shift through the pre-sweep internal swing, ATR-sized displacement, and a three-candle fair-value gap.
5. Enter only on a later FVG retracement and directional close. Place the stop beyond the raid extreme with an ATR buffer; target a fixed R multiple, with optional break-even/trailing variants.

## Why this was the defensible translation

- ICT's own Episode 6 explicitly links fair-value gaps with market-structure shifts; the EA uses that sequence rather than trading every gap: https://www.youtube.com/watch?v=Bkt8B3kLATQ
- Empirical S/R research finds local extrema are useful approximations, repeated bounces matter, and effects decay; the EA therefore uses confirmed swings, rejection counts, and ATR-normalized zones: https://arxiv.org/abs/2101.07410
- Federal Reserve research found intraday S/R levels can help predict trend interruptions, but their strength varies; this supports treating S/R as a conditional filter, not certainty: https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.pdf
- Intraday volume and volatility have strong session seasonality, supporting explicit London/New York windows: https://arxiv.org/abs/1810.12099

## Robustness and limitations

- The EA is closed-bar and non-repainting: confirmed right-side swings only; no same-bar FVG retracement entry.
- 173 training/refinement/neighborhood cases were screened. This creates selection bias even though the final year was untouched.
- XAG's selected training sample had only nine trades, so it was weak before validation.
- A one-year final window is useful but not enough to establish a durable edge across multiple regimes.
- CFD spreads, swaps, and random delay were represented by MT5; broker-recorded historical tick data and external commissions were not available.
- 'ICT' language is descriptive. This experiment tests these objective rules; it does not prove claims about institutional intent.

## Decision

Do not add this EA to the active portfolio. If research continues, use US30 only as the starting hypothesis and require a second broker plus a later forward test. Do not optimize the failed final year, because doing so would contaminate the holdout.
