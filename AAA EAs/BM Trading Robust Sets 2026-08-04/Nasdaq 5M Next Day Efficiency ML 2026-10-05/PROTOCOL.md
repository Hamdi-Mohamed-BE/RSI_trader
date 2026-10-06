# Frozen next-day efficiency experiment — 2026-10-05
This is an independent reconstruction, not the creator's undisclosed model.
Production EA, BATs, presets, account and website remain unchanged.

## Market and time
Exness USTEC M5 OHLC, broker-server UTC as in the canonical EA tester preset.
New York regular session 09:30–16:00, DST-aware. Only complete sessions (78 bars)
are used to learn labels/features. Forecast every weekday (including shortened sessions)
from the most recent earlier completed session; shortened sessions are excluded from
model target scoring, not silently excluded from EA trading. Today's RTH prices never
enter today's prediction.
The entry gate must use a prediction timestamp strictly earlier than the 09:35 entry.

## Target
ER = abs(last close - first open) / (abs(first close - first open) +
sum(abs(consecutive close changes))). No overnight gap in ER. High ER means
ER >= median ER of training targets. This predicts efficiency, NOT direction.

## Fifteen fixed features from the prior completed RTH session
1 ER; 2 five-session mean ER; 3 twenty-session mean ER;
4 absolute open-to-close return; 5 signed open-to-close return;
6 range/open; 7 realized M5 log-return volatility;
8 mean absolute M5 return; 9 closing location in range;
10 body/range; 11 fraction positive M5 returns;
12 lagged overnight gap (today open / preceding session close - 1);
13 five-session close-to-close volatility; 14 twenty-session close-to-close volatility;
15 five-session / twenty-session mean range ratio.
All quantities refer to the feature session or earlier. No volume/order-flow proxy.

## Model, training and gate frozen BEFORE recent trading results
StandardScaler + LogisticRegression(C=1, L2, solver=lbfgs, max_iter=3000).
Training targets: 2020-01-01 through 2023-12-31.
Diagnostic calibration: 2024-01-01 through 2024-10-04. NO parameter or gate selection.
Holdout: 2024-10-05 through 2026-10-04. Training never expands into holdout.
Fixed gate: trade only if predicted probability(high ER) >= 0.50.
No probability threshold/risk/strategy optimization against holdout P&L.
A simple lagged-ER >= training-median control is also evaluated.
Insufficient complete training history (<400 sessions), one-class target, or failed
off-switch parity invalidates the experiment; do not silently revise dates.

## Native EA experiment
Shipped Nasdaq 5M DI Wide ATR EA binary + canonical BAT SET.
DI14 ON, EMA12, completed first 09:30 NY M5 candle, entry ~09:35 NY,
initial SL 0.60% price, ATR6 trailing after +1R, no fixed TP/session exit,
one own open position. No bullish/bearish candle-body requirement is added.
$10,000, 1% equity risk (broker's rounding-up/minimum rule unchanged),
adaptive portfolio multiplier/guards OFF to isolate this single EA.
ML gate default OFF; research executable refuses live/non-tester use.
Gate changes entries only, not stops/trailing/exits/direction.
Precomputed frozen past-only forecast table embedded in research binary; no network.
Missing forecast blocks the gated entry, is logged, and must be zero on tested entries.

## Windows / comparisons
2 years: 2024-10-05–2026-10-05 exclusive.
6 months: 2026-04-05–2026-10-05 exclusive.
3 months: 2026-07-05–2026-10-05 exclusive.
Each native window starts flat with $10,000; end-of-test liquidation labelled.
All cases rerun natively because skipped trades can free later entries / change sizing.
Model4 real ticks where broker provides them; 150ms delay; broker spread/commission/swap.
Audit exact off-switch parity with shipped binary in 3M.
Report net-cost PF/win rate/streaks, MT5 floating-equity DD and MT5 Sharpe;
also consistently calculated daily-equity annualized Sharpe on instrumented runs.
Diagnostic high/low baseline-entry cohorts are not counterfactual bot simulations.
The ML holdout is unseen by this model, NOT evidence that previously optimized EA
parameters were selected without recent data. No deployment from this test.
