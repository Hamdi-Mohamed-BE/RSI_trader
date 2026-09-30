# Claude Nasdaq DI addition and Gold News Pulse risk comparison

Research only — 27 September 2026. No production EA, launcher, website, trading account or live terminal changed.

## Exact scope

J keeps the prior eight instances: raw Gold Overnight Value Area, Nasdaq Overnight, EMA3 Safe, ORB Volume Profile 0.75R, News Pulse XAU, News Pulse XAG, an additional EMA3 M15 ATR-trailing instance, and an additional ORB 0.50R instance. M adds Claude's promoted Nasdaq 5M DI-filter EA as the ninth instance. Nasdaq Overnight remains. No RSI/VWAP is added.

The Nasdaq addition is the verified saved DI binary: DI agreement period 14, EMA12, 09:30 New York M5 signal, fixed 2.5R target, ATR trailing OFF. This is not the wider-stop/ATR experiment. Its exact binary and SET were rerun with real ticks and 150 ms fixed delay in the isolated tester; no source modifications. The other eight ledgers are the previously verified 150 ms native runs.

Gold-only N30 and N50 mean $30 and $50 per pending order respectively, not per event. Both sides are retained, making $60/$100 planned event risk before gaps/costs. N10 is a $10/order control. No sizing cap is silently introduced to make $30/$50 fit.

## Method and assumptions

Historical replay: 4 March–30 August 2026, $10,000 start, 180 calendar days / 128 weekdays. Profits below are continuous-account P&L, not withdrawals or payout income. Portfolio DD is a stop-reserve proxy, NOT tick-measured combined equity. Actual combined equity DD is unavailable.

Monte Carlo: 1,000 matched paths per configuration and cost case, five configurations × two cost cases = 10,000 paths. Same seed 20260926 and 26 joint source weeks (2 March–30 August), synthetic purchase 28 September 2026. All milestones are conditional on these fitted historical paths, not calibrated future probabilities.

Same strict 0.01-lot rounding down, ordinary risk ceiling $71.43, daily admission budget $300, aggregate initial risk $225, correlated-metal/per-symbol cap $150, projected $9,200 buffer, maximum seven entries/day and three-loss admission stop. Pending news sides reserve both risk AND full gross margin, with an 80% available-equity margin budget. No credit for hedge-margin offsets is assumed. That is the research controller's conservative assumption, not a verified FTMO order-rejection rule.

Instrument margin assumptions: gold/silver/Nasdaq 1:15. Gold 1:15 matches FTMO's February 2026 published update; account-wide Swing up to 1:30 does not mean gold is 1:30. Exact connected-account hedge/pending margin was not queried or tested.

FTMO model: 2-Step +10% / +5%, four entry days per phase, 5% daily and 10% static loss limits with Prague DST reset. Two business days between phases, five until funded activation, first reward at least 14 calendar days after the first funded trade while flat and at least $25 profitable, then four business days for receipt and an 80% share are retained modeling assumptions. Tests stop at first reward request or day 180; no lifetime funded-account survival estimate.

Reference uses native fills and commission floors. Stress retains the prior hypothetical adverse-cost scenario: gross wins reduced 10%, losses enlarged 10%, extra adverse price cost ($1 on gold news, $0.20 ordinary gold, $0.04 silver, 2 Nasdaq points), doubled negative swaps/carry. These are sensitivity assumptions, not measured FTMO slippage.

## Continuous shared-account results

### Stressed costs

| Case | Trades | /30 days | /weekday | Net USD | Return | Win rate | PF | Closed DD | Reserve DD proxy | Max W/L |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| J | 237 | 39.50 | 1.85 | +$3,411.28 | 34.11% | 70.04 | 2.17 | 3.11% | 4.51% | 12/3 |
| M | 315 | 52.50 | 2.46 | +$2,879.08 | 28.79% | 60.95 | 1.41 | 7.33% | 8.99% | 9/6 |
| N10 | 20 | 3.33 | 0.16 | +$874.72 | 8.75% | 60.00 | 6.20 | 1.11% | 1.30% | 8/4 |
| N30 | 0 | 0.00 | 0.00 | +$0.00 | 0.00% | — | — | 0.00% | 0.00% | 0/0 |
| N50 | 0 | 0.00 | 0.00 | +$0.00 | 0.00% | — | — | 0.00% | 0.00% | 0/0 |
### Reference costs

| Case | Trades | /30 days | /weekday | Net USD | Return | Win rate | PF | Closed DD | Reserve DD proxy | Max W/L |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| J | 239 | 39.83 | 1.87 | +$4,954.71 | 49.55% | 70.29 | 3.00 | 2.06% | 3.02% | 12/3 |
| M | 322 | 53.67 | 2.52 | +$5,362.01 | 53.62% | 61.80 | 1.87 | 5.07% | 6.41% | 9/5 |
| N10 | 20 | 3.33 | 0.16 | +$1,109.15 | 11.09% | 60.00 | 10.49 | 0.69% | 0.82% | 8/4 |
| N30 | 0 | 0.00 | 0.00 | +$0.00 | 0.00% | — | — | 0.00% | 0.00% | 0/0 |
| N50 | 0 | 0.00 | 0.00 | +$0.00 | 0.00% | — | — | 0.00% | 0.00% | 0/0 |

## FTMO modeled milestones — stressed costs

| Case | Funded 30d | Paid 60d | Paid 120d | Funded 180d | Paid 180d | Breach before first reward | Median P1 days* | Median P2 days* | Median funded days* | Median paid days* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| J | 0.9% | 3.4% | 48.3% | 94.0% | 88.1% | 0.0% | 51.8 | 28.0 | 94.6 | 114.6 |
| M | 3.6% | 6.6% | 41.6% | 73.5% | 64.5% | 0.0% | 44.8 | 23.2 | 80.8 | 105.7 |
| N10 | 0.0% | 0.0% | 0.0% | 1.6% | 0.4% | 0.0% | 148.6 | 51.0 | 171.7 | 174.4 |
| N30 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | — | — | — | — |
| N50 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | — | — | — | — |

*Conditional on milestone completion within 180 days. Phase 2 duration starts at availability; other timing is from purchase. Censored/untraded accounts are not blown accounts. Zero modeled breaches is not zero real risk.

| Case | First reward median if paid* | P95 reserve DD | Paths touching internal total buffer |
|---|---:|---:|---:|
| J | $168.65 | 6.39% | 1/1000 |
| M | $209.04 | 11.89% | 326/1000 |
| N10 | $99.30 | 1.73% | 0/1000 |
| N30 | $— | 0.00% | 0/1000 |
| N50 | $— | 0.00% | 0/1000 |

## Nine-EA contributions — stressed costs

| EA | Trades | /30 days | /weekday | Win rate | PF | Net USD | Max W/L |
|---|---:|---:|---:|---:|---:|---:|---:|
| Claude Nasdaq 5M DI, 2.5R | 88 | 14.67 | 0.69 | 37.50% | 0.88 | −$486.00 | 3/10 |
| Gold Value Area raw | 82 | 13.67 | 0.64 | 79.27% | 2.11 | +$599.52 | 18/2 |
| News Pulse XAG | 16 | 2.67 | 0.12 | 43.75% | 4.19 | +$1,444.89 | 2/4 |
| Nasdaq Overnight | 52 | 8.67 | 0.41 | 61.54% | 1.24 | +$153.50 | 10/4 |
| ORB Volume Profile | 35 | 5.83 | 0.27 | 65.71% | 1.36 | +$203.74 | 6/3 |
| ORB Volume Profile 0.50R (added copy) | 24 | 4.00 | 0.19 | 75.00% | 1.30 | +$107.64 | 6/2 |
| EMA3 Safe | 4 | 0.67 | 0.03 | 75.00% | 2.52 | +$72.95 | 3/1 |
| EMA3 Safe ATR trail (added copy) | 8 | 1.33 | 0.06 | 62.50% | 0.97 | −$5.67 | 3/2 |
| News Pulse XAU | 6 | 1.00 | 0.05 | 100.00% | — | +$788.49 | 6/0 |

Contributions reflect trades accepted by the shared controller. Adding a strategy changes which other trades fit; its individual P&L is not the entire causal portfolio effect. Originals retain priority over added versions on simultaneous entries.

## News margin audit

| Per-side risk | Lot/side | Full two-side margin range | Source events fitting initial $8,000 budget |
|---|---:|---:|---:|
| $10 | 0.05 | $2,688.04–$3,461.13 | 15/15 |
| $30 | 0.15 | $8,064.12–$10,383.39 | 0/15 |
| $50 | 0.25 | $13,440.20–$17,305.64 | 0/15 |

N30/N50 follow the same full-two-side margin reserve as all prior portfolio studies. If orders do not fit, they are skipped, not shrunk or assumed filled. Actual platform behavior may reserve differently; verify symbol and hedge/pending-order specifications before interpreting skips as broker rejections.

For diagnostics only, RESULTS.json also saves cash from resizing every historical gold-news fill at each risk without admission gates. Those numbers ignore margin feasibility and cannot be used as FTMO pass/payout estimates.

## Monthly net cash — stressed costs

| Case | Month | Closed trades | Net USD |
|---|---|---:|---:|
| J | 2026-03 | 38 | +$213.99 |
| J | 2026-04 | 30 | +$264.54 |
| J | 2026-05 | 38 | +$323.18 |
| J | 2026-06 | 42 | +$805.78 |
| J | 2026-07 | 51 | +$1,500.99 |
| J | 2026-08 | 38 | +$302.80 |
| M | 2026-03 | 52 | −$200.24 |
| M | 2026-04 | 43 | −$109.69 |
| M | 2026-05 | 51 | +$504.09 |
| M | 2026-06 | 52 | +$1,117.73 |
| M | 2026-07 | 65 | +$1,461.62 |
| M | 2026-08 | 52 | +$105.57 |
| N10 | 2026-03 | 5 | +$72.28 |
| N10 | 2026-04 | 3 | +$37.36 |
| N10 | 2026-05 | 4 | −$97.20 |
| N10 | 2026-06 | 3 | +$172.22 |
| N10 | 2026-07 | 3 | +$469.27 |
| N10 | 2026-08 | 2 | +$220.78 |
| N30 | 2026-03 | 0 | +$0.00 |
| N30 | 2026-04 | 0 | +$0.00 |
| N30 | 2026-05 | 0 | +$0.00 |
| N30 | 2026-06 | 0 | +$0.00 |
| N30 | 2026-07 | 0 | +$0.00 |
| N30 | 2026-08 | 0 | +$0.00 |
| N50 | 2026-03 | 0 | +$0.00 |
| N50 | 2026-04 | 0 | +$0.00 |
| N50 | 2026-05 | 0 | +$0.00 |
| N50 | 2026-06 | 0 | +$0.00 |
| N50 | 2026-07 | 0 | +$0.00 |
| N50 | 2026-08 | 0 | +$0.00 |

## Native Nasdaq operational finding

The exact unmodified build emitted repeated failed session-close requests (market closed) on 6 March 2026. Its long opened at 14:35 and actually closed on 8 March at 22:00:02, crossing the weekend. The report retains that real simulated outcome and swaps; it does NOT assume the requested Friday close succeeded. The retry behavior and broker-session handling require review before any FTMO deployment; failure messages are duplicated across journal streams, so the aggregate message count is not a unique request count.

## Limits and deployment blockers

- Only 26 source weeks. News settings were fitted to overlapping history, and the DI rule was selected on September 2025–April 2026, also overlapping the sample. The results are not independent forward validation.
- Exness native tick ledgers plus a portfolio overlay, not a native FTMO multi-EA test. Shared skips can affect future EA state, and the overlay does not recreate that interaction.
- Weekly resampling does not preserve the actual future calendar of CPI/NFP/FOMC releases. A few large news winners can dominate estimates; repetitions are not new evidence.
- No real combined intratrade equity reconstruction. Planned risk/reserves do not bound stop slippage, gaps, outages or real daily-loss breaches.
- Swing permission to trade news does not override FTMO prohibited gap trading. Written clarification of this pre-event two-sided stop implementation is still required. Disqualification and operational-hyperactivity risk are not priced into the probabilities.
- Nothing deployed. No EA logic, BAT settings, production data or website changed.

## Evidence

NATIVE_FROZEN.json: exact Nasdaq inputs and hashes. native-di/: fresh report, trades and journal. FROZEN.json: portfolio choices/assumptions/evidence hashes fixed before replay. RESULTS.json: all historical ledgers, margin diagnostics and compact Monte Carlo paths. CHECKS.json: input/source/cash/funnel validation and exact eight-EA baseline reproduction.

- [FTMO 2-Step comparison](https://ftmo.com/en/comparison-table/)
- [Gold Swing leverage update](https://ftmo.com/en/blog/trading-updates/trading-update-2-feb-2026/)
- [Account specifications](https://ftmo.com/en/faq/what-are-the-account-specifications/)
- [Forbidden trading practices](https://ftmo.com/en/forbidden-trading-practices/)
