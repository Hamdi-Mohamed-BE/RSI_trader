# 3 way gold — frozen raw v0.1

Frozen before viewing results, 2026-09-13. Research-only native MT5 EA. No deployment, website/installer edits, Git push or optimization authorized or performed.

## What is and is not known

The supplied quant_labde screenshot/transcript describes momentum, trend-change and volatility-breakout engines. It claims 2019–2026 results of +504%, 13% maximum drawdown, 1,561 trades and PF 1.44, but gives no executable entry rules, timeframe, exits, risk allocation, broker, costs or exact dates. Public searches and an attempt to open the Instagram profile did not recover a verifiable rulebook or source code. Do not claim to reproduce that bot or those results. The rules below are OUR original, transparent implementation of the concept, not a 100% clone.

## Fixed rules, no search

All three engines read CLOSED H1 bars only and enter at the first available tick of the next H1 bar. Index 1 is the just-completed candle, index 2 its predecessor. Warm-up requires at least 250 calculated EMA200 bars. Long and short rules are symmetric. There is no lookahead regime label or learned regime gate.

1. **Momentum / strong-trend pullback:** EMA50 > EMA200, close1 > EMA50, ADX14 >= 25, +DI > -DI; close2 <= EMA20[2] and close1 > EMA20[1]. Reverse all inequalities and DI relationship for sells. This waits for a fresh EMA20 reclaim, not a buy every trending hour.
2. **Early trend change:** EMA9 crosses above EMA21 on candle 1 and RSI14 > 50. Short when EMA9 crosses below EMA21 and RSI14 < 50. RSI exactly 50 has no signal. No EMA200 gate, to allow early changes; this is a crossover proxy, not proof of a true market reversal.
3. **Volatility expansion breakout:** close1 breaks the highest high / lowest low of the 20 candles BEFORE the signal candle (indexes 2 through 21), true range1 >= 1.5 * ATR14[2], and ATR14[1] > ATR14[2]. No extra squeeze filter is assumed because none was specified in the clip.

## Exits and combined-account mechanics

- One open position per engine, at most three total on a single shared hedging account. Engines can overlap in either direction; this is not three independent equity curves added together.
- Each engine risks a nominal **0.30% of current shared equity** per new trade, approximately 0.90% if all three open together. Preserve the project's round-UP/minimum-lot policy; actual stop risk can exceed those numbers and is reported. No martingale or loss-based doubling.
- Initial SL = 2 * closed-bar ATR14 from executable ask for buys / bid for sells. Broker minimum distance plus spread is respected, and prices are rounded outward to valid ticks. TP = 2 times the resulting SL distance. Actual fill RR may differ under slippage.
- Fixed SL and TP only; no trailing, break-even, time exit, daily target or adaptive overlay. No session/news filter. Existing trades remain open until SL/TP or tester-end liquidation.
- All signals on an hour are processed momentum, change, breakout. Orders use current equity after earlier fills. Each engine independently ignores new signals while occupied; market closures/margin/order rejections are logged, never disguised as filled trades.
- MT5 Strategy Tester only; the EA refuses live use, non-XAUUSD symbols, non-H1 timeframe, and non-hedging accounts. No automatic live attachment.

## Experiment

Native MT5 real-tick model requested (Model 4), fixed 1 ms execution delay, $10,000 independent starting deposit for each run, Exness-MT5Trial16 Zero feed, leverage 1:2000 to match the connected demo. This is NOT an FTMO simulation. Broker spread and recorded commissions/swap/fees included; no invented historical cost reconstruction. Generated-tick fallbacks and available history must be disclosed even if a report shows 100% history quality.

Main windows match existing system evidence: 2026-03-05 / 2025-09-05 / 2023-09-05 / 2021-09-05 through 2026-09-05 exclusive. Additional descriptive run: 2019-01-01 through 2026-09-05 exclusive if history is available. This is not the creator's verified exact window. These windows overlap; they are not independent out-of-sample evidence.

Three additional 5-year engine-only runs use the SAME 0.30% per-engine risk, same rules and costs to diagnose contribution, not choose or tune parameters. Per-engine attribution inside the combined run is separately reported and reconciles exactly to its P/L. It need not equal the standalone account because equity-dependent sizing differs.

Checks: native MQL signal self-tests, independent Python decision replay, closed-bar timestamps, directional stop/target and RR, maximum one position per engine, deal/entry correspondence, every position closed, commissions and swaps counted once, native report reconciliation, stopout/error counts, source hashes and true coverage dates. Retain native HTML reports, decisions, events, deal ledger, equity samples and monthly/yearly breakdowns. Drawdown is every-tick/native maximum equity drawdown, not just sampled or closed-balance drawdown.

## Research references

Engine-by-engine online review was expanded at the user's request before running any tests. No source identified universally best settings, nor verified this creator's rules. The three fixed rules above remain deliberately simple baselines:

| Engine | Primary-source support | What is still our assumption |
|---|---|---|
| Momentum | [AQR Time Series Momentum](https://www.aqr.com/Insights/Research/Journal-Article/Time-Series-Momentum) reports multi-asset trend evidence on MONTHLY horizons; [Fidelity EMA guide](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/ema) describes buying pullbacks toward a rising EMA; [ADX guide](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/adx) explains trend strength. | Translating this to H1 gold, 20/50/200 lengths and the combined entry test. The academic paper does NOT validate our H1 setup. |
| Trend change | [Fidelity EMA guide](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/ema) explains earlier response and more short-term changes; [RSI guide](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/rsi) discusses different RSI behavior in up/down trends. | 9/21 crossover plus RSI50 is a transparent proxy, not a verified optimal reversal system. Fast crossover whipsaw is an important risk. |
| Breakout | [Original Turtle system](https://www.tradingblox.com/originalturtles/system.htm) documents channel breakouts, volatility sizing and explicit exits. | 20 HOUR rather than 20 DAY channel, closed-bar entry, 1.5-ATR expansion gate, fixed 2R target and no pyramiding are our simplifications. This is NOT a Turtle replication. |

These sources motivate testable hypotheses rather than prove the resulting bot has an edge. The evidence check for whether combining them helps is the actual shared-account run plus unchanged single-engine diagnostics.

- User-supplied screenshot and transcript: concept and unverified promotional statistics only. [Creator profile](https://www.instagram.com/quant_labde/) could not be retrieved during research.
- [MetaQuotes ADX explanation](https://www.metatrader5.com/en/terminal/help/indicators/trend_indicators/admi) and [iADX buffer definitions](https://www.mql5.com/en/docs/indicators/iadx): direction/strength indicator mechanics, not evidence for this complete strategy.
- [iMA](https://www.mql5.com/en/docs/indicators/ima), [iRSI](https://www.mql5.com/en/docs/indicators/irsi), [iATR](https://www.mql5.com/en/docs/indicators/iatr): native indicator implementation.
- [MT5 testing features](https://www.metatrader5.com/en/terminal/help/algotrading/testing_features): simulator behavior and limitations.

Higher historical returns or combining three engines does not establish profitability, diversification or prop-firm suitability. No parameters will be changed in response to these raw results.
