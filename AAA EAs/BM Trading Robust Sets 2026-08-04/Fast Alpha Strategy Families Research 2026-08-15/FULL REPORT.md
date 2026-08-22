# Fast Alpha Strategy-Family Research — 2026-08-15

## Decision

Only **XAU trend-following swing with the fast-alpha overlay** is strong enough to advance to an MT5-native validation. It returned **+52.89%** from 2021-08-10 through 2026-08-07 with **9.86% maximum marked-equity drawdown**, **PF 1.66**, and **116 trades**. Its locked last year returned **+28.58%**, with **5.46% drawdown**, **PF 2.87**, and **26 trades**.

This is a research pass, not permission to add it to the active BAT portfolio. It still needs an Exness MT5 real-tick test, explicit commission/swap modelling, parameter-neighbourhood testing, and forward demo observation.

The same trend parameters were then frozen and applied unchanged to EURUSD, US30, and US100. They failed on EURUSD and US100, while US30 was positive over the full window but lost 7.46% in the locked last year. The preferred result is therefore **XAU-specific**, not evidence of a universal trend model.

The US100 VWAP fast-alpha variant is interesting but not deployment-ready: the headline return is high, yet PF is only 1.15, maximum drawdown is 21.55%, one delayed stop lost 9.16R, and the available CFD data has only broker tick volume rather than exchange volume. ORB is weak over the full history. Supply/demand fails. The paper-style ATR/open trend deteriorates in the locked last year. The macro result has only ten trades and uses revised FRED data, so its apparent PF is not statistically credible.

## Test design

- Starting balance: USD 10,000.
- Risk: 1% of current balance per trade.
- Fill model: historical minute spread plus slippage equal to 25% of the instrument's median spread on every market fill; stop-first when stop and target are both inside the same minute; worse open fill when price gaps through a stop.
- Not included: explicit broker commission, overnight swap/financing, exchange fees, or market impact. This omission matters most to VWAP and ORB.
- Development: start of available data through 2024-12-31.
- Selection: 2025-01-01 through 2025-08-07. Only the five best development candidates entered selection.
- Locked final year: 2025-08-08 through 2026-08-07.
- XAU history: 2021-08-10 through 2026-08-07 (almost five years).
- US30/US100 history: 2022-01-02 through 2026-08-07 (four years and seven months, not five years).
- Source: MEXAtlantic demo M1 bid bars. `real_volume` is zero for every instrument; volume-based tests therefore use broker tick volume.
- Position concurrency: one trade at a time within each strategy family. The figures are individual-family results, not a combined live portfolio.
- Engine: independent minute-data research engine, not an MT5 Strategy Tester report.

## Full-period and locked-year results

| Family / symbol | Variant | Full return | CAGR | Max equity DD | PF | Win rate | Trades | Locked last year | Last-year DD | Last-year PF | Last-year trades | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Trend swing / XAU | Baseline | +45.35% | 7.78% | 9.54% | 1.52 | 36.97% | 119 | +16.92% | 7.77% | 1.92 | 27 | Good control |
| **Trend swing / XAU** | **Fast alpha** | **+52.89%** | **8.88%** | **9.86%** | **1.66** | **38.79%** | **116** | **+28.58%** | **5.46%** | **2.87** | **26** | **Advance** |
| ORB / XAU | Baseline | +14.00% | 2.66% | 26.98% | 1.07 | 42.47% | 445 | +9.18% | 6.86% | 1.21 | 94 | Reject |
| ORB / XAU | Fast alpha | +7.67% | 1.49% | 27.42% | 1.04 | 44.01% | 434 | +10.30% | 8.73% | 1.25 | 91 | Reject |
| VWAP / US100 | Baseline | +34.18% | 6.61% | 17.43% | 1.06 | 46.88% | 1,169 | +23.02% | 13.34% | 1.22 | 255 | Reject |
| VWAP / US100 | Fast alpha | +97.93% | 16.03% | 21.55% | 1.15 | 49.50% | 1,095 | +16.74% | 10.41% | 1.16 | 243 | Research only |
| Supply/demand / US30 | Baseline | -11.91% | -2.72% | 20.42% | 0.91 | 32.71% | 214 | -2.00% | 10.24% | 0.92 | 40 | Reject |
| Supply/demand / US30 | Fast alpha | -8.04% | -1.81% | 16.92% | 0.94 | 34.50% | 200 | -1.74% | 10.40% | 0.94 | 39 | Reject |
| ATR/open trend / US100 | Baseline | +17.76% | 3.62% | 7.64% | 1.19 | 54.34% | 438 | -1.17% | 3.84% | 0.94 | 85 | Watch only |
| ATR/open trend / US100 | Fast alpha | +19.38% | 3.93% | 8.08% | 1.21 | 54.78% | 429 | -2.01% | 4.15% | 0.89 | 84 | Watch only |
| Economic trend / US100 | Baseline | +13.26% | 2.75% | 4.57% | 3.53 | 50.00% | 10 | -1.00% | 1.54% | 0.00 | 1 | Invalid sample |
| Economic trend / US100 | Fast alpha | +13.51% | 2.80% | 4.46% | 3.65 | 50.00% | 10 | -1.00% | 1.60% | 0.00 | 1 | Invalid sample |

## Parameter-selection audit

These are baseline results for the selected parameter set before the fast-alpha variant was applied. This matters because the overlay was not used to choose the slow-strategy parameters.

| Family | Development return / PF / trades | Selection return / PF / trades | Locked final result | Interpretation |
|---|---:|---:|---:|---|
| Trend swing | +19.92% / 1.39 / 77 | +3.67% / 1.34 / 15 | +16.92% baseline; +28.58% overlay | Survived every split |
| ORB | +3.39% / 1.02 / 299 | +1.00% / 1.04 / 52 | +9.18% baseline | Full-history edge too thin |
| VWAP | +7.97% / 1.02 / 761 | +1.02% / 1.02 / 153 | +23.02% baseline | Late-period improvement; fragile PF |
| Supply/demand | -4.38% / 0.95 / 147 | -6.00% / 0.72 / 27 | -2.00% | Failed all splits |
| ATR/open trend | +14.22% / 1.23 / 306 | +4.32% / 1.46 / 47 | -1.17% | Edge decayed in final year |
| Economic trend | +9.29% / 3.27 / 8 | +2.85% / 999 / 1 | -1.00% / one trade | Too few observations; revised-data bias |

## Frozen cross-market check of the preferred trend inputs

No parameter was changed after selecting the XAU setup.

| Symbol | Variant | Full return | CAGR | Max DD | PF | Trades | Locked last year | Last-year PF | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| XAU | Baseline | +45.35% | 7.78% | 9.54% | 1.52 | 119 | +16.92% | 1.92 | Pass |
| XAU | Fast alpha | +52.89% | 8.88% | 9.86% | 1.66 | 116 | +28.58% | 2.87 | Preferred |
| EURUSD | Baseline | -2.59% | -0.52% | 19.00% | 0.97 | 109 | -0.75% | 0.94 | Fail |
| EURUSD | Fast alpha | -4.43% | -0.90% | 17.27% | 0.94 | 108 | -0.61% | 0.95 | Fail |
| US30 | Baseline | +27.66% | 5.46% | 11.53% | 1.37 | 104 | -7.46% | 0.56 | Fail recent |
| US30 | Fast alpha | +25.90% | 5.14% | 12.65% | 1.32 | 107 | -8.49% | 0.54 | Fail recent |
| US100 | Baseline | +4.88% | 1.04% | 21.10% | 1.06 | 110 | -10.49% | 0.52 | Fail |
| US100 | Fast alpha | +1.13% | 0.24% | 21.05% | 1.01 | 112 | -10.29% | 0.52 | Fail |

## Selected setups

### 1. XAU trend-following swing — preferred

- H4 close breaks the prior 80 completed H4 bars' high for a long or low for a short.
- Long also requires close above EMA(50); short requires close below EMA(50).
- Initial stop: 2.5 × H4 ATR(14).
- Target: 3R. Maximum hold: 20 days.
- Fast entry overlay: after the H4 signal, wait up to 30 minutes for one completed M5 candle opposite the slow trade, then enter at the next minute open. Skip if none appears.
- Fast stop overlay: after the stop is first crossed, wait up to 30 minutes for one completed M5 candle favourable to the position, then exit. This can exceed the planned 1R loss; the worst observed trade was -1.67R.
- No breakeven or trailing stop was enabled.

The overlay improves full-period PF from 1.52 to 1.66 and locked-year return from 16.92% to 28.58%, while drawdown remains close. A 20,000-path block bootstrap of historical active months gives an estimated 83.9% probability of a positive next 12 months, a median +9.01%, a 5th–95th percentile range of -5.17% to +29.19%, and a 0.37% chance of closed-trade drawdown over 15%. Those probabilities are model estimates, not guarantees, and do not include future regime change.

### 2. XAU New York ORB — rejected

- First 15 minutes from 09:30 America/New_York.
- Opening tick volume must be at least 0.8× its prior-20-session median.
- M5 close must break the range, have at least 70% candle body, and tick volume at least 1.2× the prior-20-bar median.
- Stop on the other side of the opening range; 3R target; force exit 15:55 New York.

The ORB research literature reports that unusual trading activity is central to the edge. Our CFD tick-volume proxy is weaker than consolidated stock/futures volume, and the observed full-history PF of 1.07 is too close to break-even to survive missing commissions and execution error.

### 3. US100 VWAP trend — research only

- Session VWAP from 09:30 New York using M15 broker tick volume.
- From 10:30, enter with trend after a close beyond VWAP ± 0.25 × M15 ATR(14).
- Stop at session open, target 1.5R, force exit 15:55 New York.

The fast-alpha curve is visually attractive and positive in each complete calendar year, but it contains a -9.16R delayed-stop loss, PF is only 1.15, and actual exchange volume is absent. VWAP is fundamentally an execution benchmark; treating it as a directional alpha requires separate evidence. Retest on NQ futures trades/volume and include commissions before considering it.

### 4. US30 supply/demand break-and-retest — rejected

- H1 impulse candle body at least 1.2 × ATR(14).
- Demand/supply zone is the impulse candle's wick-to-body edge.
- First confirmed retest within six H1 bars.
- Stop 0.3 × ATR beyond the zone, 2R target, maximum seven-day hold.

Empirical work supports temporary support/resistance effects, especially at levels with repeated bounces, but this single-impulse zone definition does not capture that evidence. It lost money in development, selection, and final testing.

### 5. US100 ATR/open intraday trend — watch only

- M15 close beyond New York session open ± 0.7 × previous daily ATR(14).
- Stop at session open; exit by 15:55 New York.
- Fixed 1% risk replaces the paper's 2% daily-volatility targeting, so this is paper-inspired rather than an exact SPY replication.

It was positive in development and selection but negative in the locked final year. Do not deploy it from this test.

### 6. US100 economic-data trend — invalid until vintage-data retest

- Inputs: unemployment, CPI, industrial production, and effective Fed funds.
- Conservative 20-day availability lag, three-month macro trend, 2.5× daily ATR stop, 4R target, maximum 90-day hold.
- Current revised FRED values were used. A lag prevents obvious calendar look-ahead but cannot remove data-revision look-ahead.

ALFRED stores the values that were actually known on each historical date and is required for a defensible macro backtest. With only ten trades and one locked-year trade, no decision should be based on PF 3.53.

## Calendar consistency

Returns below are recomputed from trade R values with each calendar year starting at USD 10,000 and 1% current-balance risk. 2021 and 2026 are partial years.

| Variant | 2021* | 2022 | 2023 | 2024 | 2025 | 2026* |
|---|---:|---:|---:|---:|---:|---:|
| XAU trend baseline | -3.95% | -0.39% | +18.05% | +6.18% | +16.53% | +4.02% |
| XAU trend fast alpha | -4.00% | -0.12% | +11.07% | +7.48% | +20.02% | +11.28% |
| XAU ORB baseline | +3.21% | +15.56% | +0.87% | -14.06% | +4.98% | +5.03% |
| US100 VWAP baseline | — | +1.10% | -0.51% | +7.34% | -1.89% | +26.68% |
| US100 VWAP fast alpha | — | +16.35% | +17.87% | +10.96% | +15.96% | +12.16% |
| US100 ATR/open baseline | — | +11.97% | +3.58% | -1.51% | +4.04% | -0.91% |
| US30 supply/demand baseline | — | -15.24% | +8.25% | +4.22% | -10.76% | +3.23% |

## Research basis

- The supplied Concretum note distinguishes informational alpha from directly monetizable alpha. Its standalone five-minute reversal signal fails after costs, but it improves a slower SPY intraday trend strategy by roughly two percentage points of net CAGR. This study therefore tests the fast signal only as an execution overlay.
- The time-series momentum literature documents return persistence across equity-index, currency, commodity, and bond futures, supporting the slow trend family as a sensible prior rather than a data-mined invention.
- ORB research finds the strongest results when activity is unusually high (“stocks in play”), which motivated relative-volume filters.
- Published VWAP research primarily treats VWAP as an execution target and benchmark; it does not establish that every VWAP crossover is directional alpha.
- Empirical support/resistance research finds that levels with more previous bounces are more likely to bounce again and that the effect decays with age. The tested impulse-zone model lacks repeated-bounce scoring, one reason not to infer that all supply/demand approaches fail.
- Macro-cycle research supports using continuous business/financial cycle trends, but the implementation must use vintage data.

## Files

- `research_fast_alpha_families.py`: reproducible research engine.
- `SELECTED PARAMETERS.json`: exact selected inputs and status.
- `Results/summary.csv`: complete comparison table.
- `Results/all-results.json`: machine-readable metrics and test dates.
- `Results/development-screens.json`: every parameter screen.
- `Results/trend-cross-market-frozen.csv`: unchanged-parameter generalisation check.
- `Results/*-trades.csv`: full trade ledgers.
- `Results/*-equity.png`: baseline-versus-overlay equity charts.

## References

- Concretum Group, *Improving Performance with Fast Alphas*: https://concretumgroup.com/quantip-improving-performance-with-fast-alphas-a-tactical-overlay-for-intraday-trend-trading/
- Moskowitz, Ooi, and Pedersen, *Time Series Momentum*: https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf
- Zarattini, Barbon, and Aziz, *A Profitable Day Trading Strategy for the U.S. Equity Market*: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4729284
- Cartea and Jaimungal, *A Closed-Form Execution Strategy to Target VWAP*: https://epubs.siam.org/doi/10.1137/16M1058406
- Chung and Bellotti, *Evidence and Behaviour of Support and Resistance Levels in Financial Time Series*: https://arxiv.org/abs/2101.07410
- European Investment Bank, *Macro-based asset allocation*: https://www.eib.org/en/publications/economics-working-paper-2019-11
- Federal Reserve Bank of St. Louis, ALFRED: https://fred.stlouisfed.org/docs/api/fred/alfred.html

## Next gate

Advance only the XAU trend-swing fast-alpha setup. The next pass should: implement one MQL5 EA; use Exness real ticks; model commission and swap; test adjacent values around lookback 60/80/100, EMA 40/50/60, stop 2.0/2.5/3.0 ATR, and target 2.5/3.0/3.5R without selecting on the locked year; then run at least four weeks on demo. The active BAT portfolio remains unchanged.
