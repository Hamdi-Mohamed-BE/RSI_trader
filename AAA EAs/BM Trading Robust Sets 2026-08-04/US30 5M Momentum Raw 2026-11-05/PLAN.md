# Nasdaq 5M rules on US30: raw test plan (frozen 2026-11-05, before any result)

**Owner request:** test the best version of Nasdaq 5M on US30 and show the results. The best Nasdaq version is not decided yet (`Nasdaq 5M Candle Rule 2026-11-05` is running), so the three contenders run side by side. **No tuning: every Nasdaq value is kept as it is.**

**Versions, all EMA12 entry on the 09:30 New York M5 candle, DI14 ON:**
- ATR6: stop 6 x ATR(14), ATR x 6 trail from +1R, no target, holds overnight (deployed on Nasdaq).
- P60: stop 0.60% of price, same trail and no target.
- FIXED: stop 4 x ATR, fixed 2.5R target, no trail, closed at 15:55 New York.

**Control:** ATR6 traded the opposite way (close above EMA = short).

**Test:** native Model 4, 150 ms, $10k, 1%, the research EX5 of the Nasdaq study with InpDirectionRule 0, chart M5, symbol US30. data_split windows: development 2019-01 -> 2023-11, validation -> 2024-11, OOS -> 2026-11, and all. Ticks generated before 2026.

**Report:** every window; by year; 6m / 1y / 3y / 5y from the all-years ledger; win rate and break-even win rate; trades per month and day; best-day check; equity DD (MT5 relative). Three-way Monte Carlo + day-block bootstrap. Buy and hold US30 on the same windows.

**Raw gate (PIPELINE stage 4):** positive and PF >= 1.15 on 3y and 5y, >= 30 trades, better than the control. A version that fails stops here: no optimisation without a separate owner request.
