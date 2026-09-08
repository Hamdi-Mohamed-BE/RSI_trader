# Close-Drive Intraday Momentum research

Step 1 of the two approved new-strategy ideas. Markets: US100 (broker USTEC) and US30. Step 2, relative-value pairs, waits for user review.

This folder contains a separate research EA, exact input sets, native MT5 reports, reconciled trade ledgers, configuration comparisons and Monte Carlo figures. It does not modify portfolio BAT files, recommended selections or website data.

Run `python run_research.py` from this folder using the existing isolated MT5 installation. The runner uses its saved demo research account; it starts an empty chart profile with terminal-level EA trading disabled while the Strategy Tester runs. It requires the existing `_Backtests/MT5-DMC-20260811` terminal, MetaEditor and broker history, Python, beautifulsoup4, numpy and matplotlib. It reuses the existing adjacent native-report parser. Do not run another job on the same isolated tester concurrently.

`python verify_evidence.py` reconciles the reports and checks New York entry timing, source versions and holding periods. `python run_research.py --report` rebuilds only tables/graphs without another backtest.

The research default risks 1% per trade. Timed exits occur at 15:55 New York or five minutes before the broker trading session closes, whichever happens first. A structural stop on the wrong side is rejected; structural distances are capped at 3 ATR. Shortened holiday-session windows are conservatively excluded. Broker CFD history and session definitions differ from the ETF data used in the motivating paper.

Development uses M1 OHLC and 1 ms execution. Validation uses generated Every Tick and random delay (`ExecutionMode=-1`). Broker spread, reported commissions and swap are reflected in native reports. Real-tick validation has not been performed. The selected three-year curve includes the development sample and cannot be described as out-of-sample performance.

Sources:
- [Gao et al., Market Intraday Momentum](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2440866)
- [MetaQuotes tester configuration and delay modes](https://www.metatrader5.com/en/terminal/help/start_advanced/start)
