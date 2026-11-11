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
