# Treasury Auction FX and Gold/Silver Cross-Session Momentum — raw research

Generated: 2026-09-11

## Verdict

These are **research-only raw replications**. Nothing was added to the website, BAT files or live MT5 account. The Treasury result is a conservative core-calendar replication rather than a claim of exact parity with the authors' Bloomberg calendar. The metals paper has only a two-year, strongly bullish published sample and no independent out-of-sample evidence.

## 1. Treasury Auction-Conditioned FX

### Mechanical rule tested

1. Identify a monitored U.S. macro release day whose immediately preceding business day had a coupon Treasury note or bond auction.
2. At 17:00 New York time on the auction day, buy EURUSD and GBPUSD and sell USDJPY in equal weights.
3. Close all three legs at 17:00 New York on the macro day. There is no stop, target or trailing rule in the paper's raw return construction.
4. Use the connected Exness account's recorded bar spreads, $3.50 per lot per side commission and the terminal's current swap-point schedule. The stress row adds another 0.5 pip round trip.

### Connected-account result

| Scope | Events/trades | Return | PF | Win rate | Max DD | Sharpe | Mean/event |
|---|---:|---:|---:|---:|---:|---:|---:|
| 3-leg portfolio gross / paper style | 151 events / 453 legs | 2.68% | 1.10 | 44.37% | 5.94% | 0.55 | 1.90 bps |
| 3-leg portfolio after broker costs | 151 events / 453 legs | -1.95% | 0.94 | 42.38% | 7.19% | -0.34 | -1.16 bps |
| EURUSD | 151 | -5.41% | 0.84 | 43.05% | 9.35% | -1.04 | -3.54 bps |
| GBPUSD | 151 | -0.30% | 1.00 | 48.34% | 7.15% | -0.00 | -0.02 bps |
| USDJPY | 151 | -0.26% | 1.00 | 43.05% | 8.14% | 0.02 | 0.07 bps |
| Portfolio +0.5 pip stress | 151 | -2.54% | 0.92 | 41.72% | 7.34% | -0.46 | -1.56 bps |

Exact evidence window: 2021-09-11 through 2026-09-11. Official-source calendar contains 264 core macro days and 152 auction-conditioned days before intersecting tradable bars.

### Fidelity limit

The accessible official calendar covers BLS CPI and Employment Situation, BEA GDP and DOL Initial Jobless Claims. The paper also used ADP Employment, ISM Manufacturing and Conference Board Consumer Confidence. Those three series were omitted rather than guessed. Therefore this is a **core-calendar replication**, not a paper-exact reproduction. The authors' headline total-return chart also abstracts from transaction costs; our headline above is after observable broker costs.

### Pipeline recommendation

**Skip.** The recent five-year three-pair portfolio is negative after broker costs; the added 0.5-pip stress is worse. The gross return is too small to survive spread, commission and swap, so a parameter search would be trying to manufacture an edge absent from the raw executable rule.

## 2. Gold/Silver Cross-Session Momentum

### Mechanical rule tested

UTC sessions are Asia 00:00–08:00, Europe 08:00–14:30 and US 14:30–24:00. At each session open, take the sign of the immediately preceding session's return. The long-only variant holds one unit only after a positive preceding session and otherwise stays flat. Positions are recalculated at every boundary; weekends reset the signal.

| Symbol | Window | Cost model | Sessions/days | Return | PF | Win rate | Max DD | Sharpe |
|---|---|---|---:|---:|---:|---:|---:|---:|
| XAUUSD | paper-sample | paper-2bp | 365 | 41.26% | 1.36 | 40.27% | 17.16% | 1.17 |
| XAUUSD | paper-sample | broker | 365 | 52.62% | 1.46 | 40.82% | 15.51% | 1.44 |
| XAUUSD | five-year-transfer | paper-2bp | 906 | 46.32% | 1.18 | 36.20% | 17.16% | 0.63 |
| XAUUSD | five-year-transfer | broker | 906 | 63.34% | 1.24 | 36.75% | 15.51% | 0.81 |
| XAGUSD | paper-sample | paper-2bp | 368 | 43.36% | 1.21 | 41.30% | 30.94% | 0.70 |
| XAGUSD | paper-sample | broker | 368 | 24.23% | 1.13 | 40.76% | 30.82% | 0.46 |
| XAGUSD | five-year-transfer | paper-2bp | 917 | 32.48% | 1.09 | 37.08% | 31.60% | 0.31 |
| XAGUSD | five-year-transfer | broker | 917 | -34.13% | 0.94 | 35.55% | 56.10% | -0.23 |

The `paper-2bp` rows apply the paper's 0.02% charge per unit of position change. The `broker` rows use the connected Exness account's recorded spreads plus $3.50/lot/side commission and charge the recorded long/short swap whenever a position survives the U.S.-session rollover. Weekends reset the signal.

### Interpretation

The paper-sample row is the closest comparison to the authors' 22 July 2024–7 August 2026 sample. The five-year transfer is the important robustness check because the published sample was a large precious-metals bull market. Session decomposition and every tested raw variant are retained in the CSV, including Asia-only, Europe-only, US-only and long/short versions; none is promoted automatically.

### Pipeline recommendation

**The approved XAUUSD full pipeline is complete and failed the strict research gate; skip XAGUSD.** The selected XAU configuration stayed profitable in the locked year, but its 10,000-path bootstrap P5 return was negative and only half of nearby parameter settings were profitable. It was therefore not promoted or deployed. Silver remains rejected because it loses over the five-year transfer.

## Sources and audit trail

- Krohn and Vala, *Auctions, Announcements, and Abnormal Returns*, April 2025/updated 2026.
- U.S. Treasury Fiscal Data auction API (`auctions_query`).
- BLS annual release schedules, BEA annual release schedules and the DOL UI Weekly Claims publication schedule.
- Wei, *Who Moves the Price? Trading-Session Return Decomposition and Cross-Session Momentum in Gold and Silver Markets*, August 2026.
- Broker: Exness Technologies Ltd / Exness-MT5Trial16 / account type Zero.

## Files

- `treasury-results.csv` — headline and per-pair statistics.
- `treasury-event-portfolio.csv` and `treasury-trades.csv` — auditable event and leg returns.
- `metals-cross-session-results.csv` — all raw variants, both cost models and both windows.
- `metals-session-decomposition.json` — gross session attribution.
- `Data/source-audit.json` and `Data/broker-data-audit.json` — source receipts and broker metadata.
- `Charts/` — equity curves.
