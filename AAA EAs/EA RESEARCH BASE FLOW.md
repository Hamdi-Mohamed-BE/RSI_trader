# EA Research Base Flow

This is the default research and validation workflow for every new EA idea and every material EA revision. The goal is not to maximize one backtest. The goal is to find a stable parameter region that remains profitable after costs and on unseen data.

## 1. Formalize the strategy

- Convert the trading idea into exact, non-repainting rules.
- Define the signal timeframe, entry timing, trade direction, maximum simultaneous positions, expiry rules and broker-time/session conversion.
- Use automatic broker-symbol discovery where the deployment must support suffixes such as `m`, `.`, or other broker variants.
- If the strategy does not specify markets, test: US30, US100, BTC, XAU, XAG and GBPJPY.

## 2. Data and test periods

- Use real MT5 broker history rather than cached synthetic results.
- Include broker spread, commission, swap and random execution delay.
- Prefer three years when reliable tick history is available; never use less than one year for a final decision unless the strategy depends on rare or newly available data.
- Split chronologically:
  - development/in-sample: choose broad parameter regions;
  - validation/walk-forward: reject unstable settings;
  - final locked out-of-sample: run once without changing the selected settings.
- Show one-year and three-year results when both are available.

## 3. Reward-to-risk search

- Test at least: 0.5R, 0.75R, 1R, 1.5R, 2R, 3R, 4R and 5R.
- Also test no fixed target with an exit or trailing rule when appropriate.
- Expand beyond 5R only if results remain stable and trade count is adequate.
- Select a stable plateau, not the single highest result.

## 4. Stop-loss placement

Compare the placements that make sense for the strategy:

- signal/sweep candle extreme plus buffer;
- market-structure swing;
- session or opening-range extreme;
- ATR/volatility multiple;
- fixed price or point distance;
- volume-profile/value-area invalidation.

Reject a stop that produces unrealistic fill sensitivity or depends on one broker's digits.

## 5. Exit and trailing-stop search

- Always compare no trailing stop against trailing alternatives.
- Test break-even activation, ATR/chandelier trailing, swing trailing, partial exit and the Dynamic Trailing SL rule.
- Dynamic Trailing SL definition: after a completed M15 candle reaches 50% of the original entry-to-target distance, move the stop to lock 20% of that distance. For trades without a target, use 0.5R progress as the trigger and lock 0.2R.
- Keep trailing only when it improves the locked risk-adjusted result; a higher win rate alone is not sufficient.

## 6. Risk-per-trade search

- Default test risk is 1% per trade.
- Compare at least 0.25%, 0.5%, 0.75%, 1.0% and 1.25%, with higher levels tested only while margin and drawdown remain survivable.
- For small fixed-balance systems, also test broker-valid fixed lots and explicitly model minimum lot constraints.
- Choose risk from drawdown and Monte Carlo survival, not maximum return.

## 7. Session and day filters

Compare:

- all day;
- Asia;
- London;
- New York;
- London/New York overlap;
- strategy-specific opening or macro windows;
- weekday filters when trade count supports them.

Resolve daylight-saving time using the actual market timezone. A filtered result must retain enough trades to be credible and must pass the locked period.

## 8. Robustness and Monte Carlo

- Run at least 10,000 Monte Carlo paths on the locked trade or daily-return sequence.
- Use a block bootstrap where possible to retain short-term clustering.
- Report probability of profit, probability of ruin or account-rule breach, median return, 5th/95th percentile return, median maximum drawdown and 95th-percentile maximum drawdown.
- Include parameter-neighbour stability, chronological walk-forward checks and cost/slippage stress tests.
- Flag small samples and strategies whose result depends on a handful of trades.

## 9. Required output

For every tested setting and market, provide equity graphs and a comparison table containing:

- net return;
- profit factor;
- win rate;
- maximum equity drawdown;
- trade count;
- Sharpe ratio;
- recovery factor;
- gross profit/loss and trading costs when available;
- test dates, history quality and model type.

Also show development versus locked out-of-sample results and the Monte Carlo distribution/fan chart.

## 10. Selection rule

The recommended configuration must be profitable and reasonably consistent across time, neighbouring parameters and realistic cost assumptions. Prefer lower drawdown, stronger locked profit factor, adequate trade count and better Monte Carlo survival over the highest headline return. Do not add an EA to the active BAT or website unless the user explicitly approves it after seeing the final locked evidence.
