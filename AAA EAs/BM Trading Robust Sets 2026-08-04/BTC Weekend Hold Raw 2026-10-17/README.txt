BTC WEEKEND HOLD - FIXED RAW TEST - 2026-10-17

Open Results.html for the tables and every recent completed trade.
RESULTS.json contains the complete reproducible results; VERIFICATION.json
reconciles cash, gross/spread/financing components, counts, sizing and coverage.

Frozen rule: buy Friday 17:00 America/New_York; sell Sunday 17:00 in the same
timezone. Use exact scheduled bar OPEN only; missing endpoints are skipped.
Local clocks are converted separately, including 47-/49-hour DST weekends.
There is no stop, profit target, timing search or optimization.

Headline account starts at USD10000 and spends 100% of CURRENT cash each weekend,
using fractional BTC. This is capital allocation, NOT 1% stop risk. The separate
fixed-initial-USD10000 notional reference can exceed available cash after losses
and is not presented as a cash-funded executable account.

Recent archived BTCUSD M1 coverage: 2025-08-01 to 2026-10-13 00:02 UTC.
Testing ends exclusively 2026-10-13 00:00 UTC; latest complete trade is Oct9-11.
This is NOT coverage through Oct17. The Oct16-18 weekend is still incomplete.
All 63 scheduled recent entry/exit pairs are present, but 20 weekends have gaps
inside the holding window. Sampled OPEN-equity DD can miss those gaps and all
intraminute extremes; it is not true tick-level equity DD.

SPREAD-ONLY CASH-COMPOUNDING RESULTS (BEFORE OTHER COSTS):
3 months: 13 trades; +8.41085%; 84.62% wins; PF44.849; sampled M1 equity DD3.87%.
6 months: 26 trades; +9.97544%; 76.92% wins; PF3.006; sampled M1 equity DD4.66%.
1 year:   52 trades; +0.42976%; 69.23% wins; PF1.015; sampled M1 equity DD20.80%.
Full:     63 trades; +1.29110%; 68.25% wins; PF1.039; sampled M1 equity DD20.80%.
The very high 3-month PF comes from only 13 trades and two small losses. It is
not evidence of a stable 44.8 PF strategy; the longer recent record is weak.

Costs are a BAR-SPREAD PROXY: buy at bid OPEN + recorded bar spread * USD0.01;
sell at bid OPEN. Bar spread is not an opening timestamp-matched ask quote.
Commission, slippage, lot rounding, actual margin and historical financing are
not verified. Never call these measured all-in net results.

Financing sensitivity on the FULL recent sample, using archived current long
swap -1863.7 points/BTC/charge and USD0.01/point: 0 assumed charges +1.29110%;
3 assumed charges/weekend -3.01775%; 4 assumed charges/weekend -4.41357%.
These constant charges are booked at exit and affect next weekend's quantity.
They are NOT reconstructed historical financing. Friday17:00 fill/rollover
ordering and swap-free account eligibility can change real charges.

Separate longer Trial16 M5 check: 2022-01-01 to 2026-09-01 exclusive, 242 traded
weekends, 60.33% wins, PF1.178, +30.6263% GROSS BEFORE ALL COSTS. One missing
entry (2025-06-20) is skipped. Its feed is never spliced into Trial15 M1.

Offline execution: run.py requires NumPy and the two hash-locked local archives
named in PROTOCOL.json. test_weekend.py has 11 passing synthetic fixtures for
DST, exact/no-lookahead fills, spread conversion, no-stop sizing, PF/DD,
streaks, zero-trade calendar days, incomplete windows and financing units.
No network, MT5 API, terminal launch, live EA changes or order execution.

Broker context: https://get.exness.help/hc/en-us/articles/17854191888540-Cryptocurrencies
BTCUSD is a continuously traded CFD. The schedule uses conventional FX-weekend
boundaries; BTC does not reopen Sunday. Trading and financing terms remain
account-specific. Historical results do not guarantee future performance.
