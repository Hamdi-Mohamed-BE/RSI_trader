# USDJPY London Open: optimisation plan (frozen 2026-11-05, before any result)

**Owner request:** the EA has been weak lately; find the best optimisation (better stop trailing etc.), compare with the current one, always with OOS and Monte Carlo. Owner-approved PIPELINE stage 5 + 6.

**Data split (data_split.py, history 2019-01-01, end 2026-11-01 exclusive):** development 2019-01 -> 2023-11; validation 2023-11 -> 2024-11; OOS 2024-11 -> 2026-11.
Selection uses development only. **Recent months are never used to tune:** 2026 weakness is what prompted the request, so 3m / 6m / 1y are diagnostics only. Native Model 4, 150 ms, $10k, 1% (rounded up as production).

**Baseline:** the deployed preset: 08:00 London, 60-minute formation, Wed-Fri, ATR x 5 stop, time exit 16:00 London, break-even at 0.75R, min signal 0.2 ATR, volume 25, ADX20 + DI.

**Staged search, top 3 carried per stage (PIPELINE 5.3), every configuration recorded:** stop; break-even; R trail; ATR trail (new default-off input); one-step lock (new default-off input); target / time exit;
exit hour; formation; signal strength and volume; ADX, DI; direction; weekdays. Not applicable without new entry code, so not searched: timeframe of the signal, limit / stop entries, partial closes.

**Development score:** return / equity drawdown (MT5 relative), with PF >= 1.15 and >= 100 trades.

**Gates, in order. If any fails, the current settings stay:**
1. Plateau: at least 70% of the finalist's one-step neighbours profitable on development.
2. Validation: the top development candidates run once on validation; PF >= 1.15, positive, and better return / DD than the baseline. Best passing one goes forward.
3. OOS once: positive, PF >= 1.15, and return / DD not below the baseline's.
4. Stage 6 Monte Carlo on all trades: resample <= 5% red, randomize <= 10% red; three-way + day-block bootstrap, side by side with the baseline. Best-day check. Buy and hold USDJPY alongside.

**Honesty:** the baseline was itself chosen on 2021-24 data, and the OOS window has been viewed many times, including by the owner seeing recent weakness. OOS is previously seen, not untouched.
