# US100 Precision ORB — raw test completed

Open Results.html. Dates: 6 October 2023 through 5 October 2026. No optimisation. Deposit $10,000, fixed $100 planned stop-risk per trade. This is the supplied trigger-on rule adapted to Exness USTEC CFD, not six NQ futures contracts.

334 trades, −$487.34 / −4.8734%, net PF 0.85885, net win rate 81.437%, longest win/loss runs 22/6. Native MT5 maximal equity drawdown: $1,185.76 (11.86% at that drawdown's peak); see native report for other drawdown definitions. Daily net closing-ledger Sharpe −0.4312. All native trade costs reconciled to final balance $9,512.66. The chart attributes both entry/exit commissions at closing time; therefore its 11.4194% ledger drawdown differs slightly from native account-balance drawdown 11.44%, which books entry fees immediately.

Gross P&L AFTER spread/delayed execution but BEFORE commissions: +$52.36. Commissions: −$539.70. Net: −$487.34. Average net winner $10.90, average net loser −$55.69. 291 target exits, 26 stops, 17 time/other exits; maximum hold 480 seconds. High win rate alone did not produce a profitable three-year strategy.

Native headline win rate (83.83%) and PF (0.87) differ from whole-position net metrics because this study includes both entry and exit costs in each trade's classification. Use net 81.44% / PF 0.86 for the comparison.

Broker real ticks begin 1 January 2026. Native report says 25% real ticks; earlier parts use generated ticks. Thus this is NOT a fully real-tick three-year validation, and the small 0.3 ATR target is particularly sensitive to that limitation. 2026 subset: 90 trades, net PF 1.315, net win rate 88.89%, +$248.95. Its +2.687% return uses the $9,263.71 balance inherited from previous years, not a new $10,000 deposit.

Remaining platform-equivalence limitations: native MT5 ATR uses a rolling arithmetic true-range average; Roboquant public SDK reference lists Atr::new but does not specify smoothing. No exact SDK-output parity is claimed. CFD tick-volume replaces futures traded volume, Bid replaces futures last trade, and Ask/Bid spread affects fills. Incomplete 15-minute ranges are skipped (7 days), unlike source accepting any available range bars; minimum-lot risk overruns are skipped. Trade-time close is based on actual fill time rather than the source's next-tick fill-detection clock. No production bots, BATs, website catalogue, or trading accounts changed.

Files: native/report.htm (original MT5), native/trades.json, native/decisions.csv, native/equity.csv, Trades.csv, results.json, verification.json, build.json. tester.ini and journal are private diagnostics and must not be shared as a client package. The research binary refuses to initialise outside the strategy tester.
