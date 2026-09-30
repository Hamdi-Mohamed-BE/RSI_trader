# Interpretation and source checks

- Broker timestamps are GMT+0; DST belongs to the tested local clocks, not the Exness series. [Exness default MetaTrader timezone](https://get.exness.help/hc/en-us/articles/360014390760-What-is-the-default-timezone-set-for-MetaTrader), accessed 29 September 2026.
- Exness describes rollover at 21:00 GMT in summer / 22:00 in winter. The frozen screen excludes positions spanning 17:00 New York. [Exness swap timing](https://get.exness.help/hc/en-us/articles/360014709151-About-swap).
- MqlRates records bar start time, OHLC, volume and spread. Its bar spread cannot establish the spread at a particular entry tick. The official programming book describes it as the minimum per bar. [MqlRates reference](https://www.mql5.com/en/docs/constants/structures/mqlrates), [MQL5 Programming for Traders, p. 653](https://www.mql5.com/files/book/mql5book.pdf). A median floor and hypothetical stress are safeguards, not replacements for tick-level fill validation.
- Multiple seasonal searches can overfit financial history. The paper motivates separate tests, not any particular effect in this study. [Bailey et al., Backtest Overfitting in Financial Markets](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2731886); search abstract accessible, full SSRN page returned 403 in this session.

## Collector incident

The first data-only collector attempt used a daily open-price simulation clock with M5 CopyRates requests. MT5 rejected the lower-timeframe request before producing an export. It placed no trades. The collector was corrected to an M5 clock (same intended data, instruments and dates), compiled cleanly and completed. The failed journal is retained as collector-journal.txt.gz; the successful journal has an attempt timestamp. This was an infrastructure repair before inspecting strategy outcomes, not a rule change.

No live terminal API, trading call, EA, production SET or launcher was modified. The isolated tester generated history for data export only. Its simulation mode is not evidence of tick-accurate strategy execution.
