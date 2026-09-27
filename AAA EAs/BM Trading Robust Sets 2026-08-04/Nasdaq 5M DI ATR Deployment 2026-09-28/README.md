# Nasdaq 5M: DI + wider price stop + ATR trailing — 2026-09-28

Explicit user selection, not a new optimization or a claim of pipeline approval.
Same completed 09:30 New York M5 signal: EMA12 and DI14 agreement, both directions.
Initial stop: 0.60% of entry price (not 0.60% account risk). No TP. ATR14 M5 trailing
distance 6 ATR from the running extreme after open profit reaches +1 initial R.
No break-even, MA trail or Dynamic 50/20. No 15:55 close: holds overnight/weekends.
One position at a time; held positions suppress new daily entries.

Normal launcher risk policies remain unchanged, including Recommended Adaptive's
Nasdaq 0.25x multiplier. FTMO remains fixed maximum $50 planned stop risk, rounded
down, with its existing admission guards and News OFF. Broker costs/gaps can exceed
planned risk. Changing stop distance is not authorization to increase cash risk.

The distributed EX5 and SET are byte-identical to the retained QL_ATR research
artifacts. Archived research, original fixed-target presets and old FTMO simulation
results are not rewritten. The old FTMO pass-rate/time estimates DO NOT describe
this changed portfolio. The one-year native study returned +55.45%, 179 trades,
51.4% wins, PF 1.48 and 10.06% equity DD. Five-year equity DD was 24.07% at 1% risk,
versus 10.88% for the old fixed-target DI version. Both windows end 2026-09-25.
Real ticks begin January 2026; earlier data uses generated ticks.

Operational caveat retained from the tested build: the native journal contains
repeated rejected stop-modification attempts during market-closed intervals.
The old protective stop remains; the strategy retries on ticks. This is not a
successful fill or an extra trade. No throttling change was silently introduced
under the same backtest statistics. Demo checking of broker request limits is
required before live use, especially for overnight holding.

No live MT5 deployment, terminal restart, account change, order submission or Git
push is part of this update. The user reapplies a BAT on a suitable account when
ready. Website files/caches require the running site's own restart/deployment.
Rollback copies are in `before/`. Verification results are written separately.
