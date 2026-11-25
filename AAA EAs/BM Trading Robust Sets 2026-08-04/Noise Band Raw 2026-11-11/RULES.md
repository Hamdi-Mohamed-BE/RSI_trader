# Noise Band intraday momentum — RAW rules (frozen 2026-11-11, before any run)

Owner 2026-11-11: "get ideas from here maybe" — QuantLab research library (api-quantlab.com/research/noise-band, read 2026-11-11), the only study there marked
"survived". Source paper: Zarattini, Aziz, Barbon (2024) "Beat the Market" (SSRN 4824172); QuantLab's simplified band. SOURCE = stated on that page.

## Rules (SOURCE)
- Reference = price at the New York 09:30 open (open of the 09:30 M30 bar).
- Checkpoints every 30 minutes from 10:00 to 15:00 New York on CLOSED 30-minute candles. K = half-hours since 09:30 (1 at 10:00 ... 11 at 15:00).
- threshold = k x sqrt(K) x ATR(14) on M30. Signal when (close - open09:30) > threshold -> long; < -threshold -> short. Entry at the next candle's open.
- Initial stop = s x ATR; trailing stop 2 x ATR behind the best price once the trade is +1R; exit at stop, trailing stop or 16:00 New York at the latest. Never overnight.
- WIDE (QuantLab's pick): k 1.4, stop 2 ATR. PAPER: k 0.6, stop 1.5 ATR.

## Assumptions (ours)
- One trade per day (first signal); the page does not say whether a stopped trade may re-enter.
- ATR value at the signal bar is fixed for the trade's stop and trailing distances. Trailing checked on every tick.
- Exness CFDs USTEC (Nasdaq 100) and US500 (S&P 500), server = UTC. 1% of balance per trade, lots rounded UP (house raw convention). Model 4, 150 ms, $10k, M30.
- 16:00 NY exit at the first tick at or after 16:00 (the CFDs trade until 17:00 NY).

## Runs (native, end 2026-11-11 excl., start 2019-01-01 / first history)
WIDE and PAPER on USTEC and US500; control WIDE_RND (random direction, same distances, seed 1) on both; buy & hold per symbol (pipeline buy_hold_benchmark).
Windows: data_split dev / val / OOS (OOS = last two years, viewed by QuantLab's selection — NOT untouched), last year, years.
Raw gate (house): all years and 3y positive, PF >= 1.15, >= 100 trades, beats the random control, three-way MC (resample red <= 5%, randomize red <= 10%).
Disclosed: k 1.4 was chosen by QuantLab after seeing these years; no untouched period exists for it.

## Addendum 1 (2026-11-24, before any run): the assets on QuantLab's deep-dive page
Owner 2026-11-24: "go back to the noise band idea and test on the same assets as the website". QuantLab's deep-dive page
(api-quantlab.com/algorithmen/noise-band/analyse, read 2026-11-24) says "Nasdaq 100, S&P 500 and DAX 40, nothing overnight". It shows +420.0 % since start,
PF 1.28, max DD -19.48 %, win rate 48.6 % (start date, sizing and per-asset split not shown; the rules are locked behind a subscription).
It also shows an example trade: short 2023-01-18, held 4 h, +$6,628, around 11,500 = Nasdaq 100.
- Assets (Exness CFDs, server = UTC, history from 2019-07-16 for all three): USTEC (Nasdaq 100), US500 (S&P 500), DE30 (Germany 40 / DAX).
- EA v1.10 adds only a market clock: InpMarketClock / InpOpenMin / InpLastCheckMin / InpFlatMin. The US defaults are identical to v1.00
  (parity: v1.10 = v1.00 trade for trade on USTEC, 6 months).
- DAX: Frankfurt clock (UTC+1 / +2, EU DST). Reference = 09:00 open (Xetra cash open). Checkpoints from 09:30 to 16:30 (K = 1 .. 15), flat 17:30 (Xetra close).
  This is the same structure as the US: first check open + 30 min, last check close - 60 min, flat at the close. ASSUMPTION: QuantLab's DAX times are not published.
- Window 2019-07-16 -> 2026-11-21 (tester data end 2026-11-20). Model 4, $10k, 1% of balance, 150 ms. Older ticks are generated (real from 2026-01-01).
- Cases per asset: WIDE (k 1.4, stop 2 ATR), PAPER (k 0.6, stop 1.5 ATR), WIDE_RND seeds 1..5 (random direction, same distances).
  Plus a combined 3-asset R stream for WIDE (each asset 1 R per trade; the sum = one account trading all three).
- Report (house raw format):
  - Per asset / version / window: return, PF, win, consistency (share of profitable months), average win / loss streak, Sharpe (annualised, daily R),
    balance and equity DD, trades / month / day.
  - Calendar years; data_split dev / val / OOS; last 12 months.
  - Best-day dependence; three-way MC; 2x cost stress; buy & hold.
  - Balance graph.
- Gate unchanged (see above).

## Addendum 2 (2026-11-24, after the first run USTEC WIDE, before any other result): flat 5 minutes before the close
The first native run (USTEC WIDE, kept in native-INVALID-flat1600/) held 144 of 1,159 trades (12%) overnight. In the 2020-2024 Exness USTEC history the quotes
often end exactly at 16:00 New York, so the EA saw no tick at or after 16:00 and its close failed until the next session ([Market closed], first retry 22:30 UTC).
This breaks the frozen rule "never overnight". Execution fix, not a strategy change: flat at 15:55 New York (InpFlatMin 955) and 17:25 Frankfurt (1045),
i.e. at the last 5-minute mark before the cash close. Every other rule unchanged; parity is unaffected (the flat time is an input). All cases rerun.
