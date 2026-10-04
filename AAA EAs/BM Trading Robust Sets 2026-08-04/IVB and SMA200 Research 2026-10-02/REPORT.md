# QQQ/TQQQ SMA200 — headline video result not reproduced

Historical simulation, not a forecast.

| Fund / window | Final marked equity | Total return | CAGR | Close equity DD | Closed trades | Win rate | Closed PF | Sharpe | Max win/loss run |
|---|---|---|---|---|---|---|---|---|---|
| QQQ 16y | $79,203.23 | +692.03% | 13.81% | 25.75% | 43 | 20.9% | 4.774 | 0.89 | 2/8 |
| QQQ common-start | $73,335.78 | +633.36% | 13.40% | 25.75% | 43 | 20.9% | 4.718 | 0.87 | 2/8 |
| QQQ 5y | $20,969.20 | +109.69% | 15.99% | 20.81% | 10 | 30.0% | 6.005 | 1.02 | 1/6 |
| QQQ 3y | $19,204.12 | +92.04% | 24.32% | 13.56% | 3 | 66.7% | 21.518 | 1.36 | 1/1 |
| QQQ 1y | $11,968.45 | +19.68% | 19.76% | 11.22% | 1 | 0.0% | 0.000 | 1.04 | 0/1 |
| TQQQ 16y | $1,098,153.18 | +10,881.53% | 34.15% | 48.14% | 45 | 40.0% | 5.546 | 0.89 | 4/7 |
| TQQQ common-start | $1,098,153.18 | +10,881.53% | 34.52% | 48.14% | 45 | 40.0% | 5.546 | 0.90 | 4/7 |
| TQQQ 5y | $40,751.60 | +307.52% | 32.51% | 36.87% | 14 | 57.1% | 4.629 | 0.86 | 4/2 |
| TQQQ 3y | $27,589.63 | +175.90% | 40.29% | 36.87% | 10 | 50.0% | 3.485 | 0.94 | 3/2 |
| TQQQ 1y | $11,695.97 | +16.96% | 17.02% | 33.64% | 4 | 25.0% | 0.862 | 0.56 | 1/3 |

## Caveats

- The quoted +210% QQQ /−87% TQQQ outcome was NOT reproduced under the stated rule and our explicit execution/data assumptions. Exact video dates, code, adjustment policy and fees were not supplied; this is not an accusation about its unseen implementation.
- TQQQ started in February2010 and its first valid 200-session average here is24November2010. We did not fabricate pre-inception prices or warmup. QQQ can trade from4October2010; TQQQ remains in cash until its first valid signal. The common-eligible comparison starts26November2010.
- Raw vendor open and close are split-adjusted. Adjusted close includes dividends; adj_close/close applied once to open creates a synthetic reinvested total-return series. No separate dividend/split application. Verify actual cash dividends, taxes, broker share rounding and corporate actions before deployment.
- One full cash-funded fund position, no extra margin leverage, shorts, stop-loss or profit target. TQQQ already targets3x DAILY Nasdaq100 performance. It is not3x the multi-year QQQ return. Zero cash interest; ETF expenses are embedded in market prices, not separately charged twice.
- Signal at completed daily close; execution next session open. Same-close sensitivity is optimistic timing, not an implementable promise.5bp each side is illustrative execution friction, not a measured broker calibration.
- Both final positions remain open. Total return/equity DD include their marked unrealized P&L; PF, win rate and streaks include CLOSED trades only. DD is daily close-to-close marked equity, not intraday drawdown.
- Whole-share rounding, liquidity limits, spread, tax, market impact and slippage are not fully simulated. Long-history percentage returns rely on full compounding and a favourable historical Nasdaq sample; do not use as payout/income forecasts.
- 20,000 paired circular daily-return block samples of length20 diagnose historical return uncertainty, not a new strategy run or forecast. No pristine untouched holdout/parameter search; latest1/3/5-year windows overlap.
- This is low-frequency ETF investing, not an FTMO-compatible EA portfolio: last5years have only10 QQQ/14 TQQQ CLOSED trades. These win rates do not satisfy the user preference for high-win-rate scalping.
- IVB paid futures download was not started. The user subsequently requested an Exness US100 quote-count proxy, researched separately. Literal-source .els file is uncompiled and contains documented timing/EOD hazards. No active-EA/account/website/BAT changes or Git push.
