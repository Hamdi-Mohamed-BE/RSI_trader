# Overnight Profile — frozen raw comparison

Approved scope: only the two new interpretations, on dynamically discovered XAUUSD, US100 and S&P 500 CFDs. Existing ORB/US100 strategy transfers are deferred until user review. No optimization, live deployment, website replacement, or installer changes.

Requested interval: 2025-09-19 inclusive through 2026-09-19 exclusive. Six independent native MT5 runs, each USD 10,000, 1% current equity planned stop risk, connected Exness Zero demo contract specifications, real-tick mode with coverage disclosed, 150 ms execution delay (rounded observed connection ping). Fees and swap come from the native deal ledger. Delay is not a calibrated live slippage guarantee.

## Common frozen rules

- New York time, including US daylight saving. The verified Exness tester server clock is UTC; no fixed New York UTC hour.
- Profile: previous calendar day 18:00 through current day 09:29:59 New York. Monday starts on Sunday, not Friday. Closed broker minutes are not fabricated.
- Profile is an approximation: 64 equal-price bins from overnight low to high; each completed M1 candle contributes its broker tick volume at (high + low + close)/3. This is not exchange traded volume or tick-by-tick volume at price. At least 120 completed M1 bars are required.
- POC is the center of the largest-volume bin (lower bin wins a tie). Grow a contiguous 70% value area from the POC, adding the higher-volume adjacent bin; the upper bin wins a tie.
- Profile and overnight extremes freeze before the 09:30 opening bar; nothing from the regular session enters them.
- Only completed M5 candles that open at/after 09:30 are eligible. Earliest order is the next tick at/after 09:35. No retest, candle-color, trend, volume, news, or RR filter.
- Version VA: first close strictly above VAH buys; first close strictly below VAL sells; inside the value area waits.
- Version POC: first close strictly above POC buys; first close strictly below POC sells; equality waits.
- Long SL is VAL minus one broker tick; short SL is VAH plus one tick, in BOTH versions. Long TP is the frozen overnight high; short TP is the frozen overnight low. No trailing, break-even, or partial exits.
- One eligible signal attempt per New York weekday, one open position. If the target is already behind the executable entry, or the stop/target violates broker distances, consume the signal without trading and report it. Do not turn it into a reverse target or wait for a better hindsight entry.
- Volume uses OrderCalcProfit and rounds UP to the broker step, with the minimum lot as floor. Actual initial risk may exceed 1%; record it. Margin and valid-order constraints still apply.
- Flatten at 16:00 New York, or one minute before the last known broker trading-session close when earlier. Rejected exits retry; an unavailable quote cannot guarantee an exit. Any resulting overnight holdings are reported, not hidden.
- Entries stop at that same cutoff. No adaptive governor; these are standalone raw strategies, not a shared-account portfolio simulation.

The transcript did not specify overnight boundaries, profile construction, exact entry candle, stop, or daily limit. These are explicitly frozen research assumptions, not a claim to reproduce an undisclosed bot exactly.

## Evidence references

- https://www.tradingview.com/support/solutions/43000502040-volume-profile-indicators-basic-concepts/ — profile definitions and tick-volume proxy for CFDs.
- https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation — real versus generated history.
- https://www.metatrader5.com/en/terminal/help/algotrading/testing — native tester execution and costs.
