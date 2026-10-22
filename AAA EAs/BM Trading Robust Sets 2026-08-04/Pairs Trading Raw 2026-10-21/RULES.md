# Pairs trading (spread z-score mean reversion) — raw rules (frozen 2026-10-21, before any test)

Source: a social-media clip pasted by the user (2026-10-21), treated as data. Its rules:
- Pick two assets that move together.
- When the gap stretches more than **2 standard deviations** from normal, short the one that ran up and buy the one that fell behind.
- **Exit when the gap closes**, and cut it if the gap blows past **3–4 standard deviations**.
- It cites the Yale study (Gatev, Goetzmann & Rouwenhorst, US stocks 1962–2002, "up to 11% a year") and warns that returns
  shrank and that pairs like ETH/BTC can trend apart for years.
Research only. Isolated tester, nothing deployed.

## Pairs (fixed before testing; A = chart symbol / first leg, B = second leg; all USD-quoted Exness Trial16 CFDs)
| Id | A / B | Why |
|---|---|---|
| P1 | ETHUSD / BTCUSD | the clip's crypto example |
| P2 | XAUUSD / XAGUSD | classic metals pair |
| P3 | AUDUSD / NZDUSD | classic FX pair |
| P4 | EURUSD / GBPUSD | European FX pair |
| P5 | US500 / US30 | S&P 500 vs Dow |
| P6 | US500 / USTEC | S&P 500 vs Nasdaq 100 |
| P7 | GOOGL / META | same-industry megacaps; Coke/Pepsi are not available in the tester |
| P8 | AMD / NVDA | same-industry semiconductors (a known "breakup" risk) |
| P9 | MSFT / AAPL | megacap tech |

## Our defaults
- **Spread:** s = ln(A) − β·ln(B) on aligned D1 closes. Main version β = 1, which means equal dollar legs (dollar-neutral),
  as in the Gatev study. Signal on the last 60 closed days: z = (s − mean) / standard deviation (ours: the clip's "normal" is undefined).
- **Timing:** once per day, at the first moment both symbols have a fresh tick in their trading session (00:00 UTC for
  24/7 markets, the cash open for stocks). Market orders on both legs.
- **Entry:**
  - z ≥ +2 means A ran up: short A, long B.
  - z ≤ −2 means long A, short B.
  - One pair position at a time.
- **Exit and stop:**
  - Exit when the gap closes: z crosses back through 0.
  - Stop when |z| ≥ 3.5 on the same side (the clip says 3–4).
  - After a stop, no new entry on that side until |z| is back below 2 (ours, to avoid instant re-entry). No time limit.
- **Size (ours, Calyx 1% standard):** each leg's notional = 1% of equity ÷ (1.5 × spread standard deviation), so the move
  from entry (2σ) to stop (3.5σ) costs about 1% of equity. Capped at 3× equity per leg, rounded to the nearest lot step;
  the pair is skipped if either leg is below the broker minimum. If either leg fails to fill, the other is closed immediately.
- Broker spread, commission and swap on both legs (native).

## Versions
| Id | What |
|---|---|
| **FADE** | Main: the clip's rule (bet the gap closes) |
| MOM | Control: the opposite bet (gap keeps widening), same entries / exits / stop levels |
| RND1–3 | Control: same entry days and exit rules, random direction (3 seeds) |
| S_N20 / S_N120 | Sensitivity: 20 / 120-day window |
| S_E25 | Sensitivity: entry at 2.5σ |
| S_ST4 | Sensitivity: stop at 4σ |
| S_NOSTOP | Sensitivity: no stop (the "pair that never comes back" risk); sized as if the stop were at 3.5σ |
| S_BETA | Sensitivity: rolling OLS hedge ratio β over the window; leg B notional = β × leg A |

## Test setup and gate
- **Revision after the smoke test, before any real run:** two-symbol Model 4 took 53 s for 80 days, about 17 min per 5y run.
  The rule acts once a day at the first tick with no intraday stops, so Model 1 is used for the screen; on the daily
  BTC TSM study, Model 1 and Model 4 agreed within 0.2%.
  - Screen: FADE on every pair in native MT5 Model 1, 150 ms, $100,000, separate 6m / 1y / 3y / 5y runs, plus every
    control and sensitivity on 5y (like for like). End 2026-10-20 exclusive.
  - Confirmation: native Model 4 3y and 5y for every pair that passes the gate on Model 1; the verdict needs both to agree.
- **Metrics:** per pair trade (both legs together) — PF, win rate, streaks, exit vs stop mix, holding days; account
  return, Sharpe from daily equity, native equity DD, closed DD, trades/month and trades/day.
- **Raw gate per pair (PIPELINE.md stage 4):**
  - FADE positive with pair-trade PF ≥ 1.15 on 3y AND 5y;
  - ≥ 30 pair trades in 5y;
  - Model 1 5y PF above both the MOM and the RND mean;
  - no flip to ≤ 0 without the best day or best trade.
- Real ticks only from 2026-01 for most symbols; earlier ticks are generated.
