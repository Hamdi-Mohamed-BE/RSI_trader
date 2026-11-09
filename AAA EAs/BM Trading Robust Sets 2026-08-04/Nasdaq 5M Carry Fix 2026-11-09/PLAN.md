# Nasdaq 5M: trading the day's signal when yesterday's trade is still open (frozen 2026-11-09, before any result)

## Problem
The owner runs Edge 10 (no guard) with Nasdaq 5M DI OFF. The EA checks for an entry once a day, at the close of the 09:30 New York M5 candle. If its previous trade is still open at that moment (held overnight or over a weekend), it skips the day and never checks again. On Monday 2026-11-09, Friday's trade closed near breakeven and no new trade followed.

## Variants (research copy of the production source; only `InpCarryMode` is added)
| Mode | Name | Rule when a trade is still open at the 09:35 check |
|---:|---|---|
| 0 | PROD | Skip the day (current behaviour). Must match the production EX5 trade for trade. |
| 1 | LATE | Remember today's signal direction. When the old trade closes, enter that direction at the next M5 close, if the close is still on the same side of EMA12 and before 15:30 New York. |
| 2 | REPLACE | Close the old trade and take today's signal. |
| 3 | FLIP_ONLY | If today's signal is the same direction as the old trade, keep the old trade and skip. If it is opposite, close the old trade and take today's signal. |

Not tested: opening a second position alongside the old one. The EA manages one position per magic number, so this would need new management code and doubles open risk.

All modes keep one trade entry per New York day, the same signal, stop, ATR6 trail from +1R and no target.

## Settings
- Production EX5 `fe9f391db5af` with the Edge 10 installed inputs, DI OFF (owner setting), 1% risk.
- USTEC, native Model 4 (every tick), 150 ms, $10k.
- Whole period 2019-07-16 to 2026-11-10, one run per mode, ledger split by entry date with `data_split.research_split`. The split has been viewed before for this EA, so OOS is not untouched.
- DI ON: amended 2026-11-09 before any result (owner: "try DI on and OFF too"). All four modes are also run with DI ON and the same choice rule is applied to them separately.

## Choice rule (fixed now)
- **Requirements:** a mode replaces PROD only if its development return / closed drawdown (R) is higher than PROD's, and it is also not worse than PROD in validation and in out-of-sample on total R.
- **Monte Carlo:** it must pass the three-way Monte Carlo gates (full-sample resample red ≤5%, randomize ≤10%).
- **Several qualifying modes:** take the highest development return / drawdown.
- **None qualifies:** PROD stays.
- **Extra report:** the number of days PROD skipped because a trade was still open.

Nothing is installed or deployed by this study.
