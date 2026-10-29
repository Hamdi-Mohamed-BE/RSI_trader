# Small Account Challenge 2026-10-23 — can $100 become $5k or $10k?

Owner request: "inspired by the 20 pips challenge, come up with an EA or idea to turn $100 into $5k or $10k; show backtest
data and the expected days to reach it or to breach (blow) the $100." Research only; nothing installed, nothing live.
Method predeclared in `PLAN.md`; native protocol in `PROTOCOL.txt` (revision 1).

## Verdict

1. **The classic 20 pips challenge** is a ±20% 1:1 bet. It only grows if the win rate after costs is above **55.0%**.
   At 50% it busts 97% of the time; at 55% it still busts 55% of the time (part A).
2. **The idea tested here** keeps the compounding but swaps the coin flip for EA trades that already have a measured
   edge. Each trade risks a fixed 3–5% of the balance to the stop: no 20% bets, no martingale.
3. **Best balance of speed and survival** (2-year horizon, from $100; history = real chronological trades, MC = 5,000
   block-bootstrap paths):

   | Policy | Reach $10k: history / MC | Bust (<$10): history / MC | Median days to $10k: history / MC | Trades / month | / day |
   |---|---:|---:|---:|---:|---:|
   | FTMO 17-EA basket, 3% risk | 49.0% / 46.3% | 0.0% / 0.0% | 532 / 576 | 64–71 | 2.1–2.3 |
   | Prop ready nine, 5% risk | 49.6% / 50.2% | 5.8% / 1.2% | 502 / 563 | 39 | 1.3 |

   That is roughly a coin flip to reach $10k, taking about **17–19 months** when it works. The median path still falls
   **56–68%** from a peak at some point.
4. **Faster versions fail.** 10%+ risk reaches $10k sooner when it works (median 2–14 months) but busts 14–99% of the time. The 17-EA
   basket at 10% busts 84% of history starts.
5. **Nasdaq 5M on its own is too thin for this.** At 15 trades/month it reaches $10k in at most 13.5% of MC paths and
   at most 6.9% of history starts.
6. **Native MT5 single paths (Nasdaq 5M alone, 5% risk research copy):**
   - Last 2 years: $100 → $16,510; reached $10k on day 539.
   - Last 12 months: only $100 → $780.
   - Equity drawdown was 42–44% in both.
   - The last two years were this EA's best regime; earlier starts mostly failed.

PR9 = the Prop ready nine EAs (DI ON stream). FTMO17 = the 17-EA Current 14 + ORB basket. Trades/month and /day are
medians over paths that did not bust, per calendar day.

## A. The 20 pips challenge as a ±20% 1:1 bet (no market data, 100,000 paths, max 400 trades)

| Win rate | Growth per trade (typical path) | Reach $5k | Reach $10k | Bust (<$10) | Median trades to $10k |
|---:|---:|---:|---:|---:|---:|
| 50% | −2.02% | 1.6% | 0.8% | 97.1% | 166 |
| 55% | −0.01% | 28.8% | 22.1% | 55.5% | 217 |
| 60% | +2.03% | 87.2% | 84.3% | 8.7% | 173 |
| 65% | +4.12% | 99.3% | 99.2% | 0.7% | 106 |

At 3 trades/day, 170 trades is about 2 months. That is why the challenge looks fast, but it needs a sustained 60%
win rate at 1:1 after spread. None of our tested systems has that at 1:1.

## B/C. EA compounding from $100 (full tables: `RESULTS.md`)

Data: frozen five-year native trade ledgers (2021-10-07 → 2026-10-06), net of recorded Exness costs.
- Sizing: closed balance × risk ÷ stop, rounded **down** to the lot step.
- Minimum lots (USTEC 0.05, XAU/USDJPY 0.01, from `SPECS.json`) are used only if their risk is ≤ 3× the budget;
  otherwise the trade is skipped.
- Bust = closed balance below $10.

Selected rows, MC first, history (782 weekday starts, overlapping) second:

| Stream | Risk | Reach $5k | Median days to $5k | Reach $10k | Median days to $10k (p25–p75) | Ever below $50 | Bust | Median days to bust | Median balance 1y / 2y | Median max DD | Trades / month | / day |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| FTMO17 MC | 3% | 61.5% | 521 | 46.3% | 576 (485–653) | 16.8% | 0.0% | – | $695 / $7,002 | 55.9% | 70.8 | 2.33 |
| FTMO17 hist | 3% | 51.3% | 478 | 49.0% | 532 (476–598) | 33.6% | 0.0% | – | $239 / $4,857 | 61.1% | 64.3 | 2.11 |
| FTMO17 MC | 5% | 76.2% | 392 | 69.9% | 446 (344–562) | 38.4% | 3.9% | 492 | $1,540 / $35,174 | 75.1% | 76.4 | 2.51 |
| FTMO17 hist | 5% | 37.6% | 288 | 37.6% | 340 (275–404) | 72.0% | 30.8% | 360 | $127 / $37 | 90.8% | 78.7 | 2.59 |
| FTMO17 MC | 10% | 50.9% | 207 | 49.2% | 255 (170–383) | 75.3% | 48.9% | 95 | $272 / $372 | 94.1% | 82.2 | 2.70 |
| FTMO17 hist | 10% | 15.6% | 190 | 15.6% | 203 (155–273) | 89.4% | 84.4% | 93 | $9 / $9 | 94.4% | 89.0 | 2.93 |
| PR9 MC | 3% | 25.8% | 632 | 9.5% | 650 (590–695) | 14.2% | 0.0% | – | $485 / $2,095 | 44.1% | 38.4 | 1.26 |
| PR9 hist | 3% | 37.9% | 628 | 25.1% | 631 (584–692) | 17.9% | 0.0% | – | $278 / $1,285 | 57.2% | 38.4 | 1.26 |
| PR9 MC | 5% | 66.8% | 513 | 50.2% | 563 (473–647) | 17.3% | 1.2% | 504 | $864 / $7,713 | 60.7% | 39.3 | 1.29 |
| PR9 hist | 5% | 50.0% | 476 | 49.6% | 502 (422–595) | 46.6% | 5.8% | 593 | $358 / $4,559 | 68.0% | 38.8 | 1.28 |
| PR9 MC | 10% | 75.1% | 352 | 69.0% | 409 (296–533) | 42.9% | 14.4% | 159 | $1,459 / $24,051 | 88.4% | 39.6 | 1.30 |
| PR9 hist | 10% | 44.6% | 363 | 43.6% | 407 (293–472) | 77.9% | 41.7% | 225 | $297 / $152 | 92.0% | 39.0 | 1.28 |
| PR9 MC | ladder 10→5→2.5% | 74.5% | 407 | 58.9% | 520 (422–619) | 42.0% | 14.1% | 156 | $1,920 / $11,289 | 76.1% | 39.6 | 1.30 |
| PR9 hist | ladder 10→5→2.5% | 43.4% | 407 | 42.8% | 458 (356–558) | 71.9% | 41.7% | 225 | $378 / $1,536 | 91.0% | 39.0 | 1.28 |
| NAS5M MC | 10% | 20.2% | 465 | 13.4% | 506 (389–605) | 68.5% | 23.4% | 366 | $138 / $145 | 91.3% | 15.2 | 0.50 |
| NAS5M hist | 10% | 8.4% | 429 | 6.9% | 443 (402–556) | 98.0% | 4.5% | 212 | $15 / $14 | 90.7% | 6.1 | 0.20 |

How to read it:
- "Reach" counts a path even if it later fell back. Days are calendar days from the $100 start. The p25–p75 range
  covers only the paths that reached $10k.
- History and MC disagree most at 5–10% risk. The real 2022–2023 sequence had long losing runs that a shuffled
  4-week-block bootstrap breaks up, so **use the history column as the stricter guide**.
- **Skipped trades:** at $100 a minimum lot often risks more than 3× the budget, so those trades are skipped. Median
  skipped per 2-year path for the 3% FTMO17 basket: 452 (history), 312 (MC). Part of the basket's early edge is
  therefore not used.
- **Stacked open risk:** at 10% risk the 17-EA basket had open stop risk above 100% of the balance at some moment in
  57–63% of paths. That is how it busts.

## D. Native MT5 single paths — Nasdaq 5M EA alone, $100 deposit

Setup:
- USTEC M5, Model 4, 150 ms, 1:2000, Exness-MT5Trial16 isolated tester.
- Ticks: real from 2026-01-01; the reports say 80% real for 1y and 40% real for 2y.
- EA: research copy of the production EA with the 1% cap raised to 10%. No other source or input change except
  `InpRiskPercent` and standalone mode.
- Sizing is the EA's own: percent of **equity**, rounded **up**, with the broker minimum always allowed. This is more
  aggressive than the simulation's round-down rule.

| Run | Window | Risk | End balance | Net PF | Win | Trades | / month | / day | Equity DD (relative) | Lowest closed balance | Days to $1k / $5k / $10k | Lots |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Research copy | 2025-10-23 → 2026-10-23 | 5% | $780 | 1.37 | 52.2% | 180 | 15.0 | 0.49 | 43.8% | $97.84 | – / – / – | 0.05–0.24 |
| Research copy | 2025-10-23 → 2026-10-23 | 10% | $1,991 | 1.25 | 52.2% | 180 | 15.0 | 0.49 | 68.6% | $90.34 | 112 / – / – | 0.06–1.30 |
| Research copy | 2024-10-23 → 2026-10-23 | 5% | $16,510 | 1.39 | 53.1% | 360 | 15.0 | 0.49 | 42.3% | $100 | 169 / 425 / 539 | 0.05–5.01 |
| Research copy | 2024-10-23 → 2026-10-23 | 10% | $329,432 | 1.26 | 53.1% | 360 | 15.0 | 0.49 | 68.3% | $100 | 124 / 169 / 336 | 0.09–214.54 |
| Production EA (1% cap → min lot) | 2025-10-23 → 2026-10-23 | 1% | $471 | 1.54 | 52.2% | 180 | 15.0 | 0.49 | 24.5% | – | – / – / – | 0.05 |
| Production EA (1% cap → min lot) | 2024-10-23 → 2026-10-23 | 1% | $960 | 1.68 | 53.1% | 360 | 15.0 | 0.49 | 17.9% | – | – / – / – | 0.05–0.06 |

What the native runs show:
- **Same trades, different sizes.** All six runs take the same 180 / 360 trades. At $100 the 1% production EA is
  effectively a fixed 0.05-lot account.
- **The last two years were the best regime for this EA.** Starting the simulation on the same date
  (2024-10-23, 5%, round-down sizing) gives the same picture: $5k at day 433, $10k at day 618, $11,889 at the data end
  (2026-10-06). The native run reached them sooner (days 425 / 539) because it sizes on equity and rounds up.
  - Earlier starts did badly. Of 782 history starts from 2021-10 to 2024-10, only 0.8% reached $10k at 5% (part B).
  - **One good recent window is not a probability.**
- **The last 12 months alone did not reach $5k** at 5% or 10% risk.
- **Equity drawdowns of 42–69%** are the price of 5–10% risk. That is the floating loss inside the tester, not just
  closed trades.
- **The $329k path is not realistic.** It ends on 214-lot USTEC orders. Fills, slippage and broker limits at that size
  are not modelled. Its useful information is the time to $10k (336 days).
- Costs on the 5% 2-year path: commission −$328, swap −$1,151 (included).
- The journals contain 47,294 / 72,940 "stop modification failed: market closed" lines (trail attempts while the
  market is shut) and a few "invalid stops". The production-EA runs have exactly the same counts, so this does not come
  from the sizing change.
- Balance curves: `CHART-NATIVE.png`.

## The idea as an EA: "Calyx Small Account Challenge" (not built)

If the owner wants it built, this is the version the data supports:
- **Basket:** the Prop ready nine or the FTMO 17-EA basket, unchanged signals, standalone, one account.
- **Per-trade risk:** 5% (PR9) or 3% (FTMO17) of closed balance to the stop.
  - Lots round **down**.
  - Minimum lot only if its risk is ≤ 3× the budget; otherwise skip.
  - This is the client-build style sizing, not the Calyx round-up rule.
- **Open-risk cap:** at most 15% of the balance at stop across all open trades. This is new and was not in these
  simulations; it would lower the bust rate and slow growth.
- **Stop rule:** at $5k, switch to 1% risk or withdraw the original $100 plus profits. The challenge is over; do not
  keep 5% risk on a $5k account.
- **What must change in code:**
  - The production Nasdaq 5M EA caps risk at 1%.
  - The Calyx BAT sizing rounds UP.
  - So a dedicated research/profile build is required, like `EA/Nasdaq 5M Uncapped Research.mq5` here (cap raised only).
  - That copy is research-only and must not be attached to a live chart.

## Caveats

- **In-sample.** These EAs and settings were chosen after seeing this history. Real results are likely worse.
  Ticks before 2026 are generated, not recorded.
- **Not enough edge for certainty.** Even on in-sample data, about half the starts fail to reach $10k in 2 years.
- **Drawdowns are deep.** The typical path loses more than half of the account from a peak at some point.
- **Gaps.** P&L is booked at close and sized on closed balance. Weekend and news gaps and slippage can exceed the stop;
  at 5–10% risk one gap can take a large share of the account.
- **Costs at $100.** Exness Standard spreads/commissions are in the ledgers. A cent account or a different broker
  changes minimum lots and costs.
- **Not advice.** This is research, not a forecast or a recommendation. Any real attempt belongs on a demo account
  first.

## Files
- `PLAN.md`, `PROTOCOL.txt`, `sim.py` (theory / run / table), `THEORY.json`, `RESULT-*.json`, `RESULTS.md`.
- `SPECS.json` + `EA/Spec Probe.mq5`: broker lot rules read in the isolated tester.
- `chart.py` → `CHART-MC.png`, `CHART-NATIVE.png`. The MC fan re-runs the same paths and checks parity with
  `RESULT-*.json`.
- `native.py`, `native/`: uncapped research-copy runs.
- `native-CAPPED-1PCT/`: the first production-EA runs, which were capped at 1% (see its NOTE.txt).
- `EA/Nasdaq 5M Uncapped Research.mq5/.ex5` + compile log: the cap line is the only source change.
