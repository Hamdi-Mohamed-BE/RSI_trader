# AAA Final US100 Weakness Exact EA

This is a separate implementation of the supplied chart example. It does not
replace the older US100 Weakness EA.

## Exact baseline logic

1. The 09:30-09:45 New York M15 candle must close red.
2. A later bullish M15 candle must close back above the red candle's open.
3. Place two sell stops at the red candle's low, expiring at 16:00 New York.
4. Both legs use the same 60.0-index-point stop (600 TradingView ticks).
5. The fixed leg uses a 100.0-point target (1,000 TradingView ticks).
6. The runner has no target. When the fixed target is reached, close 20% of the
   runner and trail the remaining stop above each newly closed M15 candle high.

Total equity risk is 1%, split equally between the two legs. This EA requires a
hedging account so the fixed-target and runner positions remain separate.

The compiled EA is disabled by default because the latest one-year validation
lost money. Loading the supplied baseline set enables it for manual testing.
