# Overnight Bias ORB on other assets — RAW (PLAN frozen 2026-11-11, before any run)

Owner 2026-11-11: "can we try the overnight bias approach on gold and btc? and eurusd and gbpjpy, same rules, show the raw results".
EA = the UNCHANGED raw research EA `Video ORB VWAP Ideas Raw 2026-11-09/EA/Video Ideas Raw EA.ex5`, InpStrategy=4 (same build that tested US100: PF 1.35, +117.5R).

Same rules on every symbol (all New York time):
- overnight range = NY 00:00 -> 09:30 (M15 bars); bias long if the 09:30 open is in the top third, short if in the bottom third, no trade if in the middle;
- opening range = the 09:30-09:45 M15 bar; entry at an M15 close beyond the OR in the bias direction, 09:45 -> 15:15, ADX(14, M15) > 20;
- stop 0.30 x 15-day average true daily range, target 0.90 x (3R); one trade a day; flat 15:30; weekdays only (BTC weekends not traded).

Symbols (Exness, server UTC): XAUUSD, BTCUSD, EURUSD, GBPJPY. Native Model 4, 150 ms, $10k, 1% of balance rounded UP, M15 chart,
2019-01-01 (or first available history) -> 2026-11-11 excl. Controls per symbol: ONB_NOBIAS (first OR break either way), ONB_RAND (random direction,
same distances, seed 1). Buy & hold per symbol on the same windows (pipeline buy_hold_benchmark). Windows: data_split dev / val / OOS, 3y, last year, last 6m, years.

Raw gate (house): positive all years and 3y, PF >= 1.15, >= 100 trades, beats both controls, three-way MC (resample red <= 5%, randomize red <= 10%).
No optimisation. These assets have no "opening bell" at 09:30 NY: this is a transfer test of the same clock, declared as such.
