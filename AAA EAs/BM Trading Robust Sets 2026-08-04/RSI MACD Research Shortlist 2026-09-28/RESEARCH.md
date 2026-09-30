# RSI + MACD research shortlist

28 September 2026. Research and proposed test rules only. **No new EA, backtest, optimization or live deployment has been performed for these combinations.** No verified winner or projected win rate is being claimed.

## Conclusion

First candidate: **trend-side RSI pullback with MACD recovery confirmation**. Second candidate: **RSI extreme recovery plus a fresh MACD crossover**. Keep a simple MACD-only control to measure whether RSI actually helps. Do not presume one set of parameters transfers to every asset.

Scope: XAUUSD, BTCUSD, US30, US100, EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD and NZDUSD. Resolve the actual broker symbols and account-specific contract specifications before any test. CFD BTC is not interchangeable with exchange spot/perpetual BTC.

## Evidence, not advertising

- [Chio, 2022, comparative MACD study](https://arxiv.org/pdf/2206.12282): reports high win rates for combined RSI/MACD on daily US stock samples during 2015–2021. It is long-only and explicitly excludes transaction costs. Its results concern constituent stocks, not our US30/US100 CFDs, and establish no edge for gold, Bitcoin or FX. The paper's P&L ratio is average win/average loss, not profit factor. Its mathematical RSI lookback condition also needs careful interpretation before literal replication. Treat it as motivation, not a production specification or expected win rate.
- [Fidelity RSI guide](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/rsi): RSI can remain extreme in a strong trend, and its useful ranges shift with direction. That supports testing trend-side pullbacks instead of automatically fading every overbought/oversold reading.
- [Fidelity MACD guide](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/macd): MACD is primarily a trend/momentum tool; range-bound crossover whipsaws are a known limitation. Indicator agreement is not two independent sources of evidence, because both come from price.
- [Deprez and Frommel, 2024, Bitcoin technical rules](https://www.sciencedirect.com/science/article/pii/S1059056024003010): a broad study considers trading costs, multiple testing and out-of-sample portfolios. It supports a cost-aware validation process, not a specific guaranteed RSI/MACD combination.
- [Lin et al., 2026, volume-price-adjusted MACD](https://arxiv.org/html/2604.26063): daily ETF research with a chronological split and explicit assumed costs. It is not an RSI strategy or evidence for intraday broker tick-volume filters. Keep it outside this initial two-indicator study.

Our own `RSI Mean Reversion 15m Raw 2026-09-25/REPORT.md` rejected all nine tested RSI-only asset/variant combinations on the longer-term gate. Many wins and long winning streaks did not offset losses and costs. This is evidence against those specific RSI(2) implementations, not all RSI strategies.

## Proposed raw candidate A — trend pullback and recovery

These precise settings are **our research hypotheses**, not settings proven by the cited papers.

- M15 entries; H1 directional context. Only completed candles, with the H1 bar required to have closed before the M15 signal decision.
- Indicators: RSI14, EMA200 on H1, MACD(12,26,9) on H1 and M15, ATR14 on M15.
- Long context: last completed H1 close is above EMA200 and H1 MACD main line is positive.
- Long trigger: M15 RSI crosses up through 40 (previous close <=40, current close >40), and MACD main-minus-signal increases on each of the last two completed M15 intervals.
- Short context: last completed H1 close below EMA200 and H1 MACD main line negative.
- Short trigger: RSI crosses down through 60, and main-minus-signal decreases on each of the last two completed M15 intervals.
- Enter at the next tradable quote after the signal closes; no retrospective entry at the signal candle's price.
- Initial stop 2 ATR; fixed target 1R for the first raw test. Exit after 16 M15 bars if neither stop nor target is reached. One position, at most two entries per broker day. No martingale, averaging down or stop widening. These are proposed defaults, not existing EA changes.
- First raw comparison uses all available trading hours so asset/session tuning is not hidden in the baseline. Later session variants require explicit counted tests.

## Proposed raw candidate B — extreme reversal confirmation

Same stop/target/risk/holding policy as A. An oversold RSI14 reading <=30 within the preceding eight closed M15 bars arms a long setup. Enter only once RSI is back above 30 and M15 MACD crosses above its signal; expire the armed setup after eight bars and consume it on entry. Shorts mirror the logic with >=70 and a bearish MACD crossover. No discretionary chart divergence or hindsight swing detection. This is a separate hypothesis, not a fallback that silently combines with A.

## Control and implementation pitfall

Use a MACD-only crossover control with identical execution and management. Also compare A with its RSI condition disabled as a labelled ablation; it measures the incremental effect, not an independently optimized competitor.

**MT5's native MACD signal is SMA9, whereas many charting/paper implementations use EMA9.** Use MT5's native definition consistently for the raw EA and independent verifier, or explicitly create and label the EMA-signal alternative as an additional tested configuration. The visible MT5 MACD bars are its main line; main-minus-signal must be calculated explicitly. [Official MetaTrader documentation](https://www.metatrader5.com/en/terminal/help/indicators/oscillators/macd).

## How to decide whether a strategy is actually good

1. Freeze rules, timeframe, costs and gates before running. Start with raw native tests across all 11 assets; do not turn a failed raw family into an unrestricted parameter hunt.
2. Use the existing isolated pipeline, matched 6m/1y/3y/5y windows, native execution delay, spread, commission and swap. Disclose generated versus real ticks and missing contracts/history. Do not substitute a different broker's costs without saying so.
3. Report return, net win rate, PF, maximum floating-equity DD, average win/loss, win/loss streaks, sample size and trades/day/week/month. Report confidence intervals rather than treating a small sample as a reliable probability.
4. A **60%+ win rate is a screening objective, not a forecast**. Require positive net expectancy and robust PF as well. For example, 65% wins at 0.5R yields -0.025R per trade before costs. Before costs, break-even win rates are 66.67% at 0.5R, 57.14% at 0.75R and 50% at 1R.
5. Only survivors should proceed to the existing chronological optimization/validation/holdout process. Then compare exits such as 0.5R, 0.75R, 1R and 1.5R on development data, without choosing the holdout winner after the fact. Retain every trial count.
6. A higher win rate bought with occasional huge losses is unacceptable. Check cost stress, minimum-lot exposure, gaps, losing streaks, correlated FX/USD exposure and portfolio overlap. FTMO eligibility would require a separate full portfolio/equity-path simulation.

**Recommended next action:** raw-test candidate A first, with B and the controls shown separately. No existing strategy, BAT or website selection should be replaced until results are reviewed.
