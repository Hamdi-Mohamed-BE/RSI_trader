# Nasdaq 5M + Overnight Bias ORB on UK100 / DE30 — RAW (frozen 2026-11-16, before any run)

Owner 2026-11-16: "test these two bots on UK100, and germany tech stock and india tech stock if supported by the broker".

## Broker coverage (Exness-MT5Trial16, checked in the isolated tester)
- UK100 (UK 100 Index): history from 2019-07-16. TESTED.
- Germany tech (TecDAX): NOT offered. Closest = DE30 (Germany 30 / DAX), history from 2019-07-16. TESTED as the substitute.
- India tech (Nifty IT): NOT offered. IN50 (India 50) exists but has data only 2022-12-27 -> 2023-06-27 (discontinued). NOT TESTED.

## EAs (rules unchanged)
- NAS = Nasdaq 5M production EX5 2488443f62a8 (EMA12 signal bar, ATR6 stop, ATR6 trail from +1R, no TP, REPLACE carry), Edge 10 / Best 1-Step inputs, DI OFF (package default).
- ONB = Overnight Bias ORB raw research EA (Video Ideas Raw EA, InpStrategy=4): overnight thirds bias (local 00:00 -> open), 15-min opening range,
  break in the bias direction, ADX(15m) > 20, stop 0.30 x daily ATR, target 0.90 x daily ATR, entries open+30 .. open+345 min, flat at open+360 min.

## Versions
- NY  = the EAs exactly as they are (New York 09:30 clock) attached to UK100 / DE30 — what happens if you simply attach them.
- LOC = research copies whose clock is the market's own: UK100 = London 08:00 (UTC+0/+1), DE30 = Frankfurt 09:00 (UTC+1/+2), EU DST
  (last Sunday March / October 01:00 UTC). Only the time-zone function (and, for ONB, the hard-coded NY minutes made relative to the open) change;
  every offset keeps its NY distance from the open. Parity: LOC copies with the NY clock must equal production on USTEC (6 months).
- Risk 1% of balance (EA sizing), $10k, native Model 4, 150 ms, 2019-07-16 -> 2026-11-16 (end exclusive). Older ticks are generated (real ticks from 2026-01-01).
- Buy & hold UK100 / DE30 on the same window (pipeline benchmark).
- Report: all years, data_split dev / val / last-2-years OOS, calendar years, last 12 months, last 2 months, three-way MC.

Raw gate (pipeline): all years and last 3y positive, PF >= 1.15, >= 100 trades, MC resample red <= 5%. Controls (random direction / entry) only for a version that passes.

## Addendum 1 (2026-11-16, before the runs): US30 and US500
Owner: "what about us30 and smp500?". Same EAs UNCHANGED (New York clock is the natural one for US indices), same inputs, 1%, $10k, Model 4,
2019-07-16 -> 2026-11-16 excl. Cases US30/US500 x NAS_NY / ONB_NY + buy & hold (benchmark EA, USD symbols). Same report and gate.

## Addendum 2 (2026-11-16, after the US runs, before any control): US500 ONB controls
US500 ONB_NY is the only version near the raw gate (R-based PF 1.16, native PF 1.14, MC resample 3.4%, randomize 7.7%). Controls, Model 1 for speed, same window:
ONB_M1 (like-for-like), NOBIAS (InpUseBias=false), RNDDIR 1..20 (InpRandomDirection=true, InpSeed). p = share of seeds >= ONB_M1 R.
