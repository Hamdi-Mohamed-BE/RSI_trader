# Step 1 — Last-30-Minute Hedging Momentum

## Goal

Replicate the unoptimized intraday momentum rule from Baltussen, Da, Lammers and Martens (2021), *Journal of Financial Economics*, on the existing Exness USTEC contract.

## Raw rules

- Main ROD rule: at 15:30 New York, use the sign of the return from the prior 16:00 cash close through 15:30; buy when positive and sell when negative.
- ONFH paper comparator: use the sign of the return from the prior close through 10:00 New York.
- Agreement paper comparator: trade only when the ROD and ONFH signs match.
- Exit at 16:00 New York.
- No take profit, trailing stop, breakeven, weekday selection, regime filter, trend filter, or optimization.
- Risk is capped at 1% of current equity using a 10× M15 ATR emergency stop. The emergency stop is operational protection; the strategy's normal exit is time-based.
- Native MT5 Every Tick test with broker spread, commission, swap and random execution delay.

Paper: https://academicweb.nd.edu/~zda/intramom.pdf

## Results

| Period | Raw paper variant | Return | Net P/L | PF | Win rate | Max DD | Trades | Sharpe | Recovery | Expected payoff |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 years | ROD main | -4.84% | -$483.84 | 0.85 | 46.73% | 8.11% | 597 | -4.83 | -0.60 | -$0.81 |
| 3 years | ONFH | -5.31% | -$530.74 | 0.84 | 47.91% | 8.90% | 597 | -5.00 | -0.60 | -$0.89 |
| 3 years | Agreement | -3.27% | -$327.40 | 0.86 | 48.21% | 6.88% | 446 | -4.31 | -0.48 | -$0.73 |
| 1 year | ROD main | +1.71% | +$171.26 | 1.19 | 50.50% | 2.07% | 200 | 4.95 | 0.82 | +$0.86 |
| 1 year | ONFH | +1.15% | +$114.85 | 1.13 | 55.00% | 3.24% | 200 | 3.30 | 0.35 | +$0.57 |
| 1 year | Agreement | +1.62% | +$161.53 | 1.23 | 54.09% | 2.41% | 159 | 5.77 | 0.67 | +$1.02 |

History quality was 98% for the three-year tests and 100% for the one-year tests.

## Execution limitation

The Exness USTEC contract reports the market closed at 15:30 New York on Mondays. MT5 therefore rejects the exact paper entry on Mondays. The executable results contain Tuesday–Friday trades; this was retained rather than moving the entry away from the paper's prescribed time.

## Decision before optimization

The recent year is positive, but every raw three-year version loses money after costs. The raw rule is not suitable for the recommended portfolio. It may be passed through the Calyx pipeline as research, but it must prove a stable out-of-sample edge before any system or website integration.
