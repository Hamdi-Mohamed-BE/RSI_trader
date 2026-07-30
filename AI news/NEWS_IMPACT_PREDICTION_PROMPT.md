# Gold News-Impact Prediction System

## Scope

Do not build a complete trading system, signal strategy, or automated trade
execution bot.

Build a news-impact prediction system focused only on forecasting the immediate
direction of Gold (`XAUUSD`) during high-impact economic news releases. The
system is analytical only. It must never place, modify, or manage trades.

## Primary Objective

When queried 15-30 minutes before a scheduled high-impact event, the system
must:

1. Identify the upcoming event and exact release time.
2. Collect information that was genuinely available before the release.
3. Run a statistical or machine-learning prediction model.
4. Predict the most likely initial XAUUSD reaction:
   - `BUY / BULLISH`
   - `SELL / BEARISH`
   - `NO TRADE / UNCERTAIN`
5. Display calibrated confidence and conditions that could invalidate or reverse
   the prediction.
6. Monitor the release and report the observed impulse direction in real time.
7. Never place or manage trades.

## Target Events

- US CPI and Core CPI
- US Nonfarm Payrolls, unemployment, and earnings
- FOMC rate decisions and statements
- Federal Reserve press conferences
- PCE and Core PCE
- Initial jobless claims
- US GDP
- Retail sales
- ISM Manufacturing and Services
- Other major USD inflation, employment, growth, and interest-rate events

## Model Inputs

Use available, point-in-time information such as:

- Previous, consensus, and forecast values
- Historical actual-versus-forecast surprises
- Historical XAUUSD reactions to the same event
- Current market expectations and positioning
- DXY and US Treasury yield behavior
- Recent inflation, employment, and Federal Reserve data
- XAUUSD volatility, momentum, and market regime
- Correlations between Gold, DXY, yields, and the event
- Pre-news price action and liquidity conditions
- Revisions to previous economic data
- Conflicting components within the same release

Never fabricate unavailable inputs. Mark missing consensus, DXY, yield,
positioning, or tick data explicitly.

## Real-Time Release Logic

At release time:

- Capture published actual values as quickly as the configured data source
  permits.
- Compare actual values with forecasts and previous values.
- Calculate a normalized surprise score when the required values are available.
- Classify the fundamental Gold bias as bullish, bearish, mixed, or neutral.
- Detect the first genuine impulse using tick or sub-minute data when available.
- Separate the initial spike from the sustained move.
- Warn when components conflict.
- Record spread, volatility, maximum favorable excursion, maximum adverse
  excursion, and reversals.

## Pre-Release Output

```text
Event: [event name]
Release time: [time and timezone]
Predicted Gold direction: BUY / SELL / NO TRADE
Confidence: [0-100%]
Expected impulse size: [estimated XAUUSD price range]
Expected reaction window: [for example, first 5-30 seconds]
Main reasons: [short explanation]
Key invalidation condition: [what result invalidates the prediction]
Alternative scenario: [direction if the result differs from expectations]
Data quality: [complete, partial, delayed, or unavailable]
```

## Post-Release Output

```text
Actual values: [reported data]
Forecast values: [consensus data]
Surprise score: [calculated score]
Fundamental Gold bias: BUY / SELL / MIXED / NEUTRAL
Observed first impulse: UP / DOWN / NO CLEAR MOVE
Impulse detected at: [timestamp, with milliseconds when available]
Initial impulse size: [price movement]
Sustained direction after 30 seconds: [direction]
Sustained direction after 1, 5, and 15 minutes: [direction and return]
Prediction result: CORRECT / INCORRECT / UNCLEAR
Reversal detected: YES / NO
Notes: [conflicts, revisions, spread expansion, or unusual behavior]
```

## Backtesting Requirements

- Use historical economic calendars with actual, forecast, previous, and revised
  values when a licensed point-in-time source is available.
- Use high-resolution XAUUSD data around each release.
- Prevent look-ahead bias and data leakage.
- Reconstruct information available 30 and 15 minutes before each event.
- Test every event type separately.
- Measure the initial impulse and sustained direction at 30 seconds, 1 minute,
  5 minutes, and 15 minutes when the price resolution supports those horizons.
- Report confidence calibration, precision, recall, F1, confusion matrix, Brier
  score, and prediction coverage.
- Report results by event, market regime, surprise magnitude, and confidence.
- Compare the model against simple baseline rules.
- Use walk-forward validation, never only a random split.
- Report insufficient historical data clearly.

## Definitions and Safeguards

- Define impulse direction objectively using a volatility-adjusted threshold.
- Generate and permanently save each forecast before actual data is available.
- Return `NO TRADE` when confidence is weak, effects conflict, or data is
  missing.
- Do not claim certainty.
- Do not fabricate forecasts, actual values, prices, timestamps, or confidence.
- Keep pre-release prediction, post-release interpretation, and observed market
  reaction strictly separate.

## Final Product

Create a queryable application or machine-learning service that runs the latest
trained model 30-15 minutes before a high-impact release and returns a clear
`BUY`, `SELL`, or `NO TRADE` forecast for Gold's initial news impulse, with
confidence, reasoning, expected movement, invalidation conditions, and data
quality.

The product is a prediction and research tool only. It must not execute trades.
