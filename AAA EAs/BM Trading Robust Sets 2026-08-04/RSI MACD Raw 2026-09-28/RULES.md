# Frozen raw RSI + MACD rules

28 September 2026. Research hypotheses from the preceding shortlist, not published profitable parameters.
No existing EAs, website evidence, launchers or live positions are changed by this study.

## Shared execution and sizing

- Broker instruments: isolated Exness CFD history, not FTMO fills or exchange BTC. Resolve/verify each exact symbol and contract in native tester startup metadata; unavailable data is missing, not zero-return evidence.
- M15 decisions using only closed candles. RSI14 close; native MT5 MACD12/26/9 (EMA12 minus EMA26, signal **SMA9**); ATR14. H1 context uses its last completed candle, EMA200 and MACD12/26/9 main line.
- The first tradable quote after the M15 signal closes is the decision/entry quote. Skip signals if that quote is 60 seconds or more late. Require the H1 reference to have closed no later than the M15 signal close. No using current H1 values.
- 2 ATR stop from the submission ask (buy) / bid (sell), tick-size rounded; target 1R from that submission quote. Execution delay can alter the filled RR; do not retrospectively move stops/target to the fill.
- One position, maximum two successful entries per broker calendar day. No re-entry on the same signal. All trading hours. Time exit after 16 subsequent available M15 bars, at the first tradable quote; retry failed closes on later quotes no more than once a minute. Weekends/closures can extend elapsed time.
- $10,000 independent starting equity; requested 1% current-equity stop risk. Existing shared AAA_LotsForRisk/AAA_Volume helper rounds UP to step, with broker minimum/max. Actual stop risk can exceed 1%; record it. Reject orders that fail valid stops/free-margin checks rather than inventing a fill.
- No adaptive risk, trailing, break-even, averaging, recovery sizing or portfolio overlay. Shared session/dynamic-trailing inputs remain disabled.
- Native Model4, 150ms simulated delay, broker bid/ask spread, commission, swap and fees as present in the tester. No assumed extra-cost stress presented as measured. Earlier generated ticks remain labelled as such.
- Main windows: last 6m/1y/3y/5y ending 27 September 2026 exclusive, plus 120-day indicator warmup without trading. Four short XAU engineering smoke runs precede the grid. Every case and rerun is counted.

## Four separately tested entry definitions

**A — trend pullback:** long if completed H1 close > EMA200 and H1 MACD main >0, M15 RSI crosses from <=40 to >40, and MACD main-minus-signal rises over two completed intervals (h1>h2>h3). Short mirrors: H1 close<EMA200, main<0, RSI from >=60 to <60, h1<h2<h3.

**B — extreme recovery:** RSI<=30 arms a long; RSI>=70 arms a short. The most recent corresponding extreme must be one to eight completed M15 bars before the trigger. Long requires RSI>30 and a fresh main-minus-signal crossover from <=0 to >0; short requires RSI<70 and a cross from >=0 to <0. An extreme refreshes the same-side arm; a successful entry consumes that side's arm. Arms update even while a position is open, expire after eight available bars, and are not reset at midnight. No H1 trend requirement.

**C — MACD-only control:** fresh main-minus-signal cross above zero buys; cross below zero sells. Same execution, management, sizing and trade limits. This is not random-control evidence and does not isolate all indicators independently.

**D — A without RSI:** A's H1 context and two-interval MACD recovery, but no RSI crossing requirement. Labelled ablation, not an optimized alternative. Repeated monotonic bars may be new signals, still subject to one position/two entries per day.

## Predeclared decisions

Raw gate for A/B: positive net return, net PF>=1.15, >=30 trades, and higher return AND net PF than C on BOTH 3y and 5y. A must additionally exceed D's return and PF on both windows to establish RSI's benefit. 60%+ wins is reported separately, never a profitability guarantee. Drawdown, confidence intervals and minimum-lot exposure must be shown even if a gate passes.

Fail => stop, no full-parameter optimization of a failed raw family. Pass/clear near-miss => report for user review; no automatic optimization, promotion or FTMO deployment. All overlapping raw windows have been inspected and are not untouched holdouts for later optimization.

## Verification

Freeze source/dependency/binary/rule/config hashes. Validate native report identity, all requested inputs, dates, execution delay and history flags. Export full deals to reconcile position-ID net cash against native totals; export a compact decision audit of indicator values, completed H1 times, signals and outcomes. Independently recompute rule triggers, two-trade/day limits, stop/target sizing and time exits. Report unresolved inconsistencies before selecting any winner.
