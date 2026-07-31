# LTA Trading System — Development and Validation Plan

## 1. Objective

Build a trading system that follows the decision sequence shown in *The LTA Concepts e-book*:

1. Establish the macro and market context.
2. Determine sentiment, positioning, seasonality, valuation, and correlation context.
3. Locate high-timeframe supply/demand and important liquidity.
4. Calculate completed-session and structure-based volume-profile levels.
5. Wait for intraday structure to confirm the directional thesis.
6. Execute only through one explicitly defined LTA entry model.
7. Place the stop beyond structural invalidation and require a real target offering at least 2R.
8. Manage risk according to setup type, correlation, session timing, and recent results.

The system must reproduce the book's process rather than merely attach an LTA label to generic indicators.

## 2. Important Design Decision

The book describes a layered discretionary framework, not one fully specified mechanical strategy. Therefore, the project should have two stages:

- **Stage A — Decision support:** the software calculates context, zones, profiles, setup state, grade, invalidation, target, and a proposed order. A human confirms the chart pattern.
- **Stage B — Automation:** only rules that have been precisely defined, independently labeled, backtested without look-ahead bias, and forward-tested may place orders automatically.

This prevents subjective concepts such as “clean rejection,” “strong momentum,” and “fresh zone” from being silently changed during testing.

## 3. What the Book Requires

### 3.1 Context layers

The directional thesis should be assembled from:

- Macro regime: rates, inflation, central banks, growth, and major market drivers.
- Positioning and sentiment: COT, sentiment extremes, and open interest.
- Seasonality and valuation.
- High-timeframe structure: weekly, daily, 12H, and 8H supply/demand.
- Correlation confirmation: for example DXY versus EURUSD or bonds/equities versus Nasdaq.
- Intraday structure and completed-session liquidity.
- Volume-profile confirmation and an execution model.

No single layer is allowed to create an automatic trade by itself.

### 3.2 Volume-profile hierarchy

The system should calculate and freeze these levels:

- Previous day and early previous day: POC, VAH, VAL.
- Previous week and early previous week: POC, VAH, VAL.
- Current-week profile only after sufficient weekly development; initially enable it after Wednesday's close.
- Fixed-range profiles over a structural consolidation, CERC, or CME sequence.
- Swing profiles drawn wick-to-wick over a completed internal swing.
- High-volume nodes and low-volume nodes.
- Sunday open, Monday open, previous session highs/lows, previous day highs/lows, and previous week highs/lows.

Default value area is 70%. Profile bucket width must be deterministic. Start with 128 rows, then test a stable range such as 96, 128, and 160 rather than optimizing every possible row count.

### 3.3 Supply and demand

The book's four zone families must remain separate:

- Rally–Base–Rally: demand continuation.
- Drop–Base–Rally: demand reversal.
- Drop–Base–Drop: supply continuation.
- Rally–Base–Drop: supply reversal.

A valid zone needs:

- A measurable base or balance phase before the impulse.
- A displacement candle or sequence leaving the base.
- Removal of opposing structure or a meaningful imbalance.
- A freshness/touch count.
- A clear proximal and distal boundary.
- Context agreement or a documented contrarian classification.

The breakout candle is not the zone. The base that formed before the breakout is the zone.

### 3.4 Entry models

#### EM1 — Double-wick confirmation

Candidate mechanical definition:

1. Price touches a qualified POC, VAH, VAL, session level, or high-timeframe zone.
2. Rejection candle closes away from the level and has a rejection wick at least 1.25 times its body.
3. A second candle retests the level or the first wick and closes in the same rejection direction.
4. Entry occurs on the confirming close or a break of its structure.
5. Stop is beyond the two-wick extreme plus spread/slippage buffer.

The wick ratio and level tolerance are research parameters, not permanent truths.

#### EM2 — Internal swing confirmation

1. Price first mitigates the main high-timeframe point of interest.
2. A completed lower-timeframe internal swing forms.
3. Build a swing volume profile from the first-touch candle to the completed swing extreme, including wicks.
4. Prioritize the internal swing POC; test VAH/VAL only as secondary variants.
5. Wait for a retest and EM1-style confirmation.
6. Stop is beyond the internal swing invalidation.

Swing endpoints must be confirmed using only information available at that time. A future pivot may never be used retrospectively to improve an entry.

#### EM3 — Internal structure confirmation

1. Price mitigates the main level.
2. A local consolidation forms.
3. Price manipulates beyond the level or range and closes back inside.
4. A displacement candle expands in the opposite direction.
5. Entry occurs only after the displacement breaks internal structure.
6. Stop is beyond the manipulation extreme.

This is a momentum model. Entering during the consolidation is a different strategy and must not be included in EM3 results.

#### EM4 — Continuation candle flip

1. Directional bias and trend are already established.
2. Price pulls into a known volume or structure level.
3. Candle one touches and hesitates.
4. Candle two begins the flip.
5. Candle three confirms continuation.
6. Entry occurs on confirmation; stop is beyond the flip wick.

EM4 is not a reversal model. It is valid only when the continuation regime was known before the signal.

## 4. Deterministic System Architecture

Each opportunity should move through a state machine:

```text
NO_CONTEXT
  -> BIAS_READY
  -> ZONE_ARMED
  -> LEVEL_MITIGATED
  -> STRUCTURE_CONFIRMED
  -> ENTRY_MODEL_CONFIRMED
  -> ORDER_PROPOSED
  -> ORDER_LIVE
  -> MANAGED
  -> CLOSED / INVALIDATED / EXPIRED
```

Every state change must save:

- Timestamp and data available at that timestamp.
- Symbol and analysis/execution instrument.
- Context features.
- Zone/profile identifiers.
- Entry-model identifier.
- Screenshot or chart snapshot.
- Proposed entry, stop, targets, risk, grade, and expiry.
- Exact reason for acceptance, rejection, cancellation, or management.

This makes the system auditable and prevents rewriting the reason for a trade after the outcome is known.

## 5. Signal Classification

Use explicit setup classes before using A/B grades:

- **Contrarian:** high-timeframe extreme with contextual evidence, before full trend confirmation.
- **Momentum:** structure has already shifted and price confirms continuation.
- **Hybrid:** high-timeframe context plus lower-timeframe confirmation; this is the preferred automated candidate.

Suggested grade framework:

| Component | Score |
|---|---:|
| Macro/regime agrees | 0–2 |
| Positioning/sentiment agrees | 0–2 |
| Seasonality/valuation agrees | 0–1 |
| Fresh HTF zone with opposing-zone removal | 0–2 |
| Completed profile confluence | 0–2 |
| Intraday structure agrees | 0–2 |
| Correlation agrees | 0–1 |
| EM1/EM2/EM3/EM4 fully confirmed | 0–3 |
| Real target provides at least 2R | pass/fail |
| Red-folder news, poor liquidity, stale zone, or correlation conflict | penalties |

Grades must be calibrated from out-of-sample results. Do not call a setup A+ merely because its in-sample score is high.

Initial research labels:

- B: 7–8, no hard failure.
- B+: 9–10, no hard failure.
- A: 11–12, no hard failure.
- A+: 13+, all mandatory checks passed.

These thresholds are provisional and must be frozen before untouched-data testing.

## 6. Data Requirements

### 6.1 Price and execution data

- Tick or one-second bid/ask data where available.
- M1 bars for the full research period.
- Historical spread, commissions, swap, contract size, tick size, tick value, and trading hours.
- Exchange/session calendars with daylight-saving handling.
- Economic-event timestamps and actual release availability.

### 6.2 Real volume

Spot FX and broker XAUUSD do not have centralized exchange volume. A truthful LTA implementation should use:

- COMEX GC for gold analysis, mapped to the broker's XAUUSD for execution.
- COMEX SI for silver.
- CME 6E for EURUSD.
- CME NQ for Nasdaq/US100.
- CME YM for Dow/US30.
- Exchange-native BTC/ETH data for crypto.

Broker tick-volume profiles may be retained as a separate experimental variant, but must not be presented as equivalent to centralized futures volume until the two have been compared.

The futures-to-spot basis must be measured at each timestamp. Futures price levels cannot simply be copied onto the CFD without adjustment.

### 6.3 Point-in-time contextual data

- COT data stored by publication timestamp, not report date.
- Open interest available only after its actual release.
- Economic releases and revisions stored point-in-time.
- Seasonality calculated only from years preceding the test date.
- Valuation features calculated without future normalization.
- Correlation measured from trailing data only.

## 7. First Instrument Basket

Build and validate in this order:

1. **Gold:** GC analysis, XAUUSD execution.
2. **EURUSD:** 6E analysis, broker EURUSD execution.
3. **Nasdaq:** NQ analysis, broker US100 execution.
4. **Bitcoin:** exchange-native BTCUSD.
5. **GBPJPY:** only after a defensible volume method is chosen; a cross has no single clean futures profile.

Gold should be the first complete vertical slice because the book contains gold examples and the centralized GC volume source is clear. EURUSD and Nasdaq then test whether the logic generalizes. Bitcoin tests a continuously traded market. GBPJPY is deliberately later because combining GBP and JPY futures into a cross-profile proxy adds model risk.

## 8. Backtest Engine Requirements

The simulator must:

- Process events chronologically.
- Calculate profiles only from completed data.
- Respect the 18:00 New York futures-day reset.
- Apply correct DST and holiday sessions.
- Use bid for sell fills and ask for buy fills.
- Include historical or conservatively modeled spread and slippage.
- Use pessimistic resolution if entry, stop, and target occur in the same bar.
- Model gaps and stop slippage.
- Use conservative limit-fill rules; a touched limit is not automatically a fill when only bar data is available.
- Prevent duplicate entries from the same setup.
- Expire stale orders when structure, zone, session, or target changes.
- Cap correlated exposure.
- Save a complete trade ledger and rejected-signal ledger.

## 9. Risk and Trade Management

The book's baseline is:

- At least 2:1 reward-to-risk.
- Maximum 2% risk, reduced to 1% in uncertain or contrarian conditions.
- Stop after two consecutive losses, subject to predefined secured-profit rules.
- Correlated trades count as one risk idea.
- Contrarian trades may move to breakeven at 1R while the macro trend has not shifted.
- Momentum trades receive more room; breakeven is not automatic.
- Scaling in is for confirmed swing trades, not fast day trades.
- Cut stagnant London trades before New York volatility unless already working.
- Close late-New-York stagnation when volume has dried up.

For research and initial live approval, use safer limits:

- 0.25%–0.50% per trade.
- 1.0% maximum portfolio heat.
- Countertrend risk at half the momentum risk.
- Daily stop: 2R loss or two consecutive losses.
- Weekly stop: 4R–5R.
- No averaging down.
- Add to a swing only after the initial risk has been reduced and total heat stays capped.

Test these management variants separately:

1. Fixed 2R target.
2. Nearest structural target, only when it provides at least 2R.
3. Partial at 1R, contrarian remainder to breakeven, final target at 2R or next liquidity.
4. Momentum hold to next structural target without automatic 1R breakeven.
5. Time/session exit rules.

Do not select management by final balance alone. Compare expectancy, drawdown, tail loss, and parameter stability.

## 10. Research and Unseen-Data Plan

### 10.1 Data partition

Use a chronological partition for every symbol:

- 60% development.
- 20% validation.
- 20% final untouched holdout.

The final holdout must remain inaccessible until all definitions, parameters, grades, and risk rules are frozen.

For a ten-year dataset, an example is:

- 2016–2021: development.
- 2022–2023: validation and walk-forward selection.
- 2024–2026: untouched final evaluation.

If recent data has already influenced the rules, it is not unseen. In that case, reserve an older untouched block or collect future data; do not rename familiar data as a holdout.

### 10.2 Walk-forward testing

Inside development and validation:

- Train/calibrate on 24 months.
- Test on the next 6 months.
- Advance by 3 or 6 months.
- Repeat across all regimes and symbols.
- Keep the final 20% locked.

Parameters may update only at a scheduled walk-forward boundary. No change is allowed because of one losing trade or one bad month.

### 10.3 Purging and embargo

- Purge trades whose holding period overlaps a split boundary.
- Apply an embargo around split boundaries.
- Lag COT, macro, and open-interest features to their real publication times.
- Confirm swing pivots only after the required right-side candles exist.
- Never build a “fixed” profile using candles that occur after the signal.

### 10.4 Robustness tests

For every approved variant:

- Widen spread and commission by 50% and 100%.
- Randomize slippage and trade order.
- Bootstrap trades and calculate confidence intervals.
- Shift session boundaries by ±15 and ±30 minutes.
- Change profile rows by ±20%.
- Change wick/displacement thresholds by ±20%.
- Test delayed entry by one bar.
- Remove the best five trades.
- Test each year, symbol, setup family, direction, session, and regime independently.
- Test correlated portfolio exposure.

Prefer a broad stable parameter plateau over the single highest-profit parameter.

## 11. Approval Gates

### 11.1 Reject

Reject a symbol/setup if it has:

- Look-ahead leakage.
- Profit concentrated in a few trades or one year.
- Failure after realistic costs.
- Severe parameter sensitivity.
- Too few trades to estimate the result.

### 11.2 Research approved

Minimum suggested requirements:

- At least 100–150 completed historical trades.
- Positive expectancy after all costs.
- Profit factor at least 1.30.
- No single year provides more than 35% of total profit.
- Majority of walk-forward folds profitable.
- Neighboring parameter values remain profitable.

### 11.3 Paper-trading approved

- Untouched holdout profit factor at least 1.35.
- Untouched expectancy at least 0.15R per trade.
- At least 40 untouched trades, or extend the test until reached.
- Bootstrap lower confidence bound for expectancy above zero.
- Cost-stress profit factor above 1.10–1.15.
- Drawdown and loss streak fit the predetermined risk budget.

### 11.4 Micro-live approved

- 8–12 weeks or at least 50 frozen-rule forward signals.
- Expected and actual fills/slippage broadly agree.
- No material live-data/profile mismatch.
- Zero unauthorized rule changes.
- Start at 0.25% risk for at least 50 live trades.

### 11.5 Scale approved

Risk increases only after another full review. Scale gradually; do not jump from 0.25% to 2%.

No approval gate guarantees future profit. It only demonstrates that the evidence is strong enough for the next controlled stage.

## 12. Metrics and Reports

Always report:

- Trades, wins, losses, win rate.
- Net R and net cash.
- Expectancy in R.
- Profit factor.
- Maximum realized and intratrade drawdown.
- Maximum consecutive losses.
- Average and median win/loss.
- MAE and MFE.
- Holding time.
- Spread, commission, slippage, and swap.
- Results by symbol, year, month, direction, session, archetype, entry model, grade, and regime.
- Rejected-signal outcomes to detect overly restrictive filters.
- Correlation and simultaneous portfolio heat.
- Monte Carlo drawdown percentiles.

The primary ranking metric should be robust out-of-sample expectancy with controlled drawdown, not win rate or final balance alone.

## 13. Software Layout

```text
new LTA sol/
  pyproject.toml
  .env.example
  configs/
    research.yaml
    live.yaml
    symbol_families/
  data/
    raw/
    point_in_time/
    processed/
  src/lta_system/
    data/
    sessions/
    profiles/
    zones/
    macro/
    sentiment/
    seasonality/
    correlation/
    structure/
    entry_models/
      em1.py
      em2.py
      em3.py
      em4.py
    scoring/
    risk/
    backtest/
    walk_forward/
    approval/
    live/
    journal/
  tests/
    unit/
    no_lookahead/
    chart_replay/
    integration/
  reports/
    development/
    walk_forward/
    holdout/
    forward/
```

Recommended tools:

- Python managed with `uv`.
- Polars or pandas for data processing.
- NumPy/Numba for profile and simulation performance.
- Pydantic for validated configuration.
- DuckDB/Parquet for point-in-time data.
- Plotly for replay and report charts.
- MT5 adapter for broker execution.
- Separate futures/exchange data adapter for analysis volume.

## 14. Tests Before Any Backtest Result Is Trusted

- Unit tests for POC, VAH, VAL, HVN, and LVN.
- Unit tests for New York session/DST boundaries.
- No-look-ahead tests for current-week levels, pivots, zones, COT, and seasonality.
- Synthetic-candle tests for every EM1–EM4 rule.
- Golden-chart tests using manually labeled book examples.
- Replay tests that show the chart exactly as it looked at signal time.
- Fill tests for limit, stop, gap, spread, and same-bar stop/target cases.
- Position-sizing and correlated-heat tests.
- Deterministic reproduction from a saved configuration and data hash.

## 15. Recommended Build Sequence

### Milestone 0 — Freeze the specification

- Turn every discretionary phrase into a measurable rule.
- Manually label at least 50 examples and 50 non-examples for each entry model.
- Agree on invalidation and order-expiry logic.

### Milestone 1 — Gold data and profile engine

- Acquire GC and XAUUSD point-in-time data.
- Implement completed daily/weekly profiles and basis mapping.
- Verify values against TradingView or another trusted reference on sampled dates.

### Milestone 2 — Zone and structure engine

- Implement RBR, DBR, DBD, and RBD candidates.
- Add freshness, displacement, opposing-zone removal, and touch state.
- Build CERC/CME and intraday trend state.

### Milestone 3 — EM1 and EM4

- Implement the simpler candle-confirmation models first.
- Run replay tests and compare against manual labels.

### Milestone 4 — EM2 and EM3

- Add confirmed internal swings, swing profiles, manipulation, displacement, and structure break.
- Prove there is no future-pivot leakage.

### Milestone 5 — Context and grading

- Add point-in-time macro, COT, seasonality, valuation, and correlation.
- Keep each feature's marginal contribution visible.
- Remove filters that do not improve validation results.

### Milestone 6 — Multi-symbol walk-forward research

- Add EURUSD, Nasdaq, Bitcoin, and later GBPJPY.
- Run symbol-specific and pooled tests.
- Use a small family-level parameter set; avoid unique overfitted settings for every symbol.

### Milestone 7 — Locked holdout

- Freeze source version, configuration, and data cut.
- Run the final holdout once.
- Produce an approval or rejection report for each symbol/setup combination.

### Milestone 8 — Forward scanner

- Run frozen signals without orders.
- Compare expected versus realized live conditions for 8–12 weeks.
- Only then unlock micro-live execution for approved combinations.

## 16. Best First Version

The first credible version should be:

- Gold only.
- GC futures for profiles and XAUUSD for execution.
- Previous-day, previous-week, fixed, and swing POC/VAH/VAL.
- Daily/weekly supply and demand.
- Hybrid setups only.
- EM1 and EM3 first; EM2 and EM4 added after separate validation.
- Minimum 2R to an actual liquidity target.
- 0.25% research/live risk, 1% maximum total heat.
- Two-loss daily stop.
- No automatic order until a frozen-rule forward test passes.

This narrower version is more likely to reveal whether the LTA edge is genuine than an immediate all-symbol, all-model bot.

## 17. Inputs Needed Before Development

- Broker and exact execution symbols.
- Historical tick/bid-ask source.
- Futures data source for GC, 6E, NQ, YM, and SI.
- Available history length.
- Instruments ultimately intended for live trading.
- Maximum acceptable portfolio drawdown.
- Account type, leverage, commission, and prop-firm restrictions.
- Whether macro/COT/seasonality data will be licensed or sourced from public releases.

## 18. Final Recommendation

Treat LTA as a **layered research platform with four separately testable execution models**, not as one indicator bot. Build Gold end-to-end first, prove profile correctness and no-look-ahead behavior, then validate the exact same frozen logic on EURUSD, Nasdaq, and Bitcoin. Use chronological walk-forward testing and a genuinely untouched final block. Advance from historical research to paper trading to micro-live only when predefined evidence gates are passed.

