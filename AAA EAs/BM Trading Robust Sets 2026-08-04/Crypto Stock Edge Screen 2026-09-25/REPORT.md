# Crypto & stock edge screen — report (2026-09-25)

User request: "can you find a good new edge on crypto? and stocks maybe?". Four published anomalies were screened with
raw rules fixed before testing (`run-config.json`), on the crypto, stock and index CFDs with history in the isolated
tester. Research only — nothing installed, deployed or published. Full tables: `RESULTS.md`.

## Method

- EA `EA/Edge Screen Research EA.mq5` (one mode per run, long only, 0 errors / 0 warnings). 1% of equity to a
  catastrophe stop of 3 × ATR(14, D1) (breakout: stop at the day's open); lots rounded up per portfolio policy.
- Server clock: Exness = UTC (repo-verified in `Overnight Profile Raw Comparison 2026-09-19/VERIFICATION.md`).
- Screen: Model 1 (1-minute OHLC) on 3y and 5y ending 2026-09-01, each edge against its own control (144 runs).
- Gate (fixed before testing): positive and PF ≥ 1.15 on 3y and 5y, ≥ 20/30 trades, and above its control.
- Survivors: Model 4 real ticks on 6m/1y/3y/5y + controls (54 runs; results equal the screen within rounding).
- Holdout: the index RSI(2) survivors on 2019-09 → 2021-09, a window never used (6 runs).
- Smoke test found Exness stock CFDs quote 06:00–15:44 New York in 2026, so the overnight entry was moved from 15:50
  to 15:40 NY for all S1 symbols before any screen result. Older stock data closes 19:45 UTC (14:45 NY in winter,
  per `Overnight Cross-Market Research 2026-08-30`), so stock S1 trades only in DST months — limitation noted; the
  index S1 runs traded every day and still failed.

## Verdict per edge

| Edge | Evidence | Result |
|---|---|---|
| C1 crypto time-series momentum (20d return > 0, long/flat) | Liu & Tsyvinski 2021 | **ETH passes** (3y +8.4% PF 1.58, 5y +3.8% PF 1.15, DD 9.7% vs always-long −2.4%). **BTC fails only "above control" on 3y** (+14.6% vs +16.1%) while its DD is 8.4% vs 25.7%; 5y +15.3% PF 1.50. Prior repo work (`Time Series Momentum Raw Research 2026-09-09`) found BTC momentum positive; `Slow Multi Asset Trend Research` rejected ETH on walk-forward. Win rate 27–30%, loss streaks up to 14. |
| C2 crypto volatility breakout | Williams | **Fail** (PF 1.01–1.12; no better than buying every open). |
| S1 overnight drift | Kelly & Clark 2011; Lou, Polk & Skouras 2019 | **Fail on all 15 symbols** — after CFD spread + swap the effect is gone (indices PF 1.06–1.12 on 3y, negative on 5y). Consistent with `Overnight Cross-Market Research 2026-08-30`. |
| S2 daily RSI(2) pullback above SMA200 | Connors & Alvarez 2008 | **Pass on 8/17** (US500, USTEC, US30, AMD, AVGO, JPM, NVDA, BTCUSD); 14/17 positive over 5y; the random control loses on most. New to this repository. |

## S2 details (Model 4 real ticks)

| Symbol | 6m | 1y | 3y | 5y | Control 5y |
|---|---|---|---|---|---|
| US500 | 3t +0.1% | 12t +2.2% PF 20.9 | 37t +6.7% PF 3.45 win 84% DD 1.6% | 55t +7.5% PF 2.60 win 73% DD 1.7% | −2.2% PF 0.62 |
| USTEC | 5t +1.1% | 13t +1.8% PF 3.46 | 42t +5.4% PF 2.28 win 71% DD 2.3% | 61t +9.3% PF 2.88 win 72% DD 2.4% | −1.3% PF 0.80 |
| US30 | 6t +1.8% | 16t +4.2% | 42t +1.2% PF 1.15 | 63t +1.7% PF 1.16 | −2.9% PF 0.55 |
| AMD | 4t +1.6% | 12t +1.9% | 26t +3.3% PF 1.82 | 41t +4.9% PF 1.82 win 73% | −3.5% |
| AVGO | 3t −0.9% | 10t −0.5% | 32t +2.7% PF 1.49 | 47t +3.4% PF 1.42 | −0.3% |
| JPM | 2t +0.2% | 7t +1.1% | 23t +1.9% PF 1.40 | 40t +3.8% PF 1.46 | −3.2% |
| NVDA | 6t +1.4% | 12t +2.0% | 34t +3.4% PF 1.71 | 49t +3.8% PF 1.49 win 71% | −1.5% |
| BTCUSD | 0t | 3t +0.1% | 29t +2.4% PF 1.50 | 47t +1.9% PF 1.21 win 72% | 0.0% |

Baskets (ledger overlay of independent 1%-risk runs on one $10k — not a native portfolio test, not compounded):

| Basket | 3y | 5y |
|---|---|---|
| All 17 S2 symbols (no selection) | 496 trades, +25.8%, PF 1.32, win 66%, closed DD 15.7% | 751 trades, +43.2%, PF 1.36, win 66%, closed DD 13.8% |
| 3 indices | 121 trades, +13.3%, PF 1.91, win 74%, DD 4.3% | 179 trades, +18.6%, PF 1.92, win 70%, DD 4.2% |
| 8 survivors (selected on these years — optimistic) | 265 trades, +27.0%, PF 1.70, win 71%, DD 9.0%, avg streak W 4.3 / L 1.8 (max 18/6), up to 7 open | 403 trades, +36.4%, PF 1.62, win 69%, DD 8.5%, 33 stop-outs |

Untouched holdout 2019-09 → 2021-09 (Model 4; SMA200 warm-up limits the sample): **US500 15t +3.3% PF 3.91 win 87%;
USTEC 18t +3.8% PF 3.40 win 83%** (both above control); **US30 14t −1.5% PF 0.59 — fails**. `native/HOLDOUT-2019-2021.json`.

## Conclusions

1. **Best new edge: daily RSI(2) pullback on US500 and USTEC.** Positive in every window 6m–5y, PF 2.3–3.5 on 3y/5y,
   70–84% win rate, average losing streak ~1.2–1.4, DD ≤ 2.4%, beats random entries, and holds on the untouched
   2019–2021 window. It matches the high-win-rate, short-losing-streak profile wanted for prop accounts.
2. Returns are small at this sizing (1% risk to a 3 × ATR daily stop ⇒ small positions; ~12 trades/year/index).
   Scaling risk or stop distance is a sizing/optimization decision for pipeline step 5 — not done here.
3. Stock breadth is real but weaker (PF 1.4–1.8 on the passing names, some names fail); treat stocks as a diversified
   basket, not single picks. BTC RSI(2) is marginal (PF 1.21 over 5y).
4. Crypto momentum: ETH passes the gate but has a contrary prior walk-forward result; BTC momentum has the better
   risk-adjusted profile and prior support. Low win rate (27–30%), long losing streaks — not a prop-friendly profile.
5. Overnight drift and crypto volatility breakout: rejected.

## Proposed next step (needs approval)

Step 5 for RSI(2) indices: (a) native two-symbol portfolio test US500 + USTEC; (b) sizing study (risk % / stop
multiple) with 2021–2024 for choice and 2024–2026 plus the 2019–2021 holdout for checking; (c) correlation with the
existing Nasdaq-heavy portfolio; (d) then the normal promotion path (production EA, SET, parity, website evidence).

## Files

`run-config.json`, `run_edge.py` (compile | screen | confirm | summary), `make_report.py`, `EA/`, `native/ADVANCE.json`,
`native/HOLDOUT-2019-2021.json`, `native/edge-m{1,4}-*/` (SET, tester.ini, run.json, trades.json.gz, report .htm.gz,
journal.txt.gz), `RESULTS.md`.
