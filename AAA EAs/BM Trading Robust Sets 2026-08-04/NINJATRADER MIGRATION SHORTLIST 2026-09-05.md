# NinjaTrader Migration Shortlist — 2026-09-05

## Purpose

When the NinjaTrader implementation begins, start with this shortlist. Rebuild each strategy as a native NinjaScript/C# strategy, re-test it on the appropriate futures contract and session template, and forward-test it on Sim101 before considering live execution. MT5 results are reference evidence only; they are not transferable performance claims.

## Core strategy order

1. **Nasdaq Overnight** — first pilot because it naturally maps to Nasdaq futures and provides low-drawdown diversification.
2. **DmC XAU** — balanced return, drawdown and trade count in the existing MT5 evidence.
3. **Asia Breakout XAU** — clear session structure and a straightforward native-strategy translation.
4. **Engineered Liquidity XAU — optimized** — promising three-year risk-adjusted evidence; port the approved configuration only.
5. **LTA Volume Profile XAU** — highest established return and largest sample among the current core candidates, but requires careful futures volume-profile reconstruction.

## News Pulse strategies to include

6. **News Pulse XAU**
7. **News Pulse XAG**
8. **News Pulse EURUSD**

The news bots must be treated as a separate execution project. Validate economic-calendar timing, exchange/broker clock alignment, order acknowledgement, OCO cancellation, gap handling, partial fills, slippage and spread-equivalent costs. Begin on Sim101 with hard account-level loss controls. Do not infer future performance from the unusually high MT5 news-event profit factors.

## Required validation flow

- Fixed 1% risk during research unless the instrument's minimum futures contract size makes that impossible; report the effective risk honestly.
- Development period plus an untouched out-of-sample period.
- RR, stop placement, trailing/no-trailing and session comparison.
- Commission, exchange fees, realistic slippage and contract-roll handling.
- One-year and three-year evidence where contract history permits.
- Monte Carlo sequence-risk simulation.
- Sim101 forward test before live deployment.

