# Small Account Challenge 2026-10-23 — plan (written before any result)

**Owner request:** "inspired by the 20 pips challenge, come up with an EA or idea to turn $100 into $5k or $10k; show
backtest data and the expected days to reach it or to breach (blow) the $100."
Research only. No live trading, nothing installed.

## The 20 pips challenge, as usually told
Start small. Each trade aims for +20 pips and the lot size grows after every win, so the account compounds roughly 20%
per trade; about 25–30 straight-ish wins turn $100 into $10k.

That is a 1:1 bet risking about 20% of the account each time. Each win multiplies the account by 1.2 and each loss by
0.8, so it only grows when p·ln(1.2) + (1−p)·ln(0.8) > 0, i.e. a win rate above **55.0%** after costs, and even then the
path is very likely to blow up first. Part A quantifies this with no market data.

## The idea tested here: a compounding challenge on top of EAs with a measured edge
Replace the "20 pips" coin flip with trades that have positive expectancy in five years of native MT5 data, and choose
how hard to compound.

**Signal streams** (frozen five-year native ledgers, 2021-10-07 → 2026-10-06, net of recorded Exness costs; the same
data as the prop studies):

| Stream | What | Trades / month (approx.) |
|---|---|---:|
| NAS5M | Nasdaq 5M Candle Momentum alone (DI ON) | 15 |
| PR9 | Prop ready nine (DI ON) | 40 |
| FTMO17 | the 17-EA Current 14 + ORB basket (3 Way Gold as module lanes) | 86 |

**Account and broker rules:** start $100. Exness-MT5Trial16 lot rules read in the isolated tester (`SPECS.json`):
- USTEC minimum 0.05 lot, about 5% of $100 at a typical Nasdaq stop;
- XAUUSD and USDJPY minimum 0.01;
- 1:2000 leverage, stop-out 0% — margin is not binding at these sizes and is not modelled.

**Risk policies** (all declared here, none chosen after results):
- **Fixed fraction f** = 3%, 5%, 10%, 15% or 20% of closed balance per trade, measured to the trade's initial stop. Lots
  round DOWN to the step. If that is below the broker minimum, the minimum lot is used only when its risk is at most
  3 × f × balance; otherwise the trade is skipped.
- **LADDER_10:** 10% until the balance reaches $1,000, then 5% until $5,000, then 2.5%.
- **LADDER_20:** 20% → 10% (from $1,000) → 5% (from $5,000).
- One position per EA at a time, as in the source. Concurrent positions of different EAs are allowed: their stop risks
  add up, and this is reported.

**Outcomes** (2-year horizon):
- Reached $5,000; reached $10,000; **busted** = closed balance below $10 (90% lost); or neither.
- Days to each event.
- Balance after 1 and 2 years.
- Trades per month and per day.

## Evidence (separate types, labelled)
- **A. Theory:** a ±20% 1:1 bet at win rates 50%, 55%, 60% and 65%, 100,000 simulated paths.
- **B. History:** every weekday start from 2021-10-07 to 2024-10-06, each run on the real chronological trades for 2
  years. Overlapping starts are not independent.
- **C. Monte Carlo:** 5,000 block-bootstrap paths (4-week blocks of trades, 26 blocks = 2 years), seed 20261023.
- **D. Native MT5 single paths:** the production Nasdaq 5M EX5/SET with a $100 deposit, at the best f that the EA input
  allows (max 10%), over the last 12 months and the last 24 months. The EA's own rounding (UP to step, minimum if
  needed) differs slightly from the simulation.

## Caveats
- In-sample: these EAs and settings were chosen after seeing this history, and older ticks are generated (real ticks
  from 2026).
- P&L is booked at close and sized on closed balance. Intratrade floating losses are not modelled, apart from the
  reported open-risk exposure.
- Gaps, slippage, weekend gaps and broker changes can exceed stop risk; at 10–20% risk a single gap can end the
  challenge.
- Not a forecast and not advice. Any real attempt should start on demo.
