# BookMaper Markov Regime EA research

This isolated uv project reproduces the supplied Markov-regime method and tests it in two ways:

1. a standalone 1%-risk, ATR-managed daily strategy on XAU, US100, BTC and ETH proxies;
2. a no-lookahead regime veto applied to the existing active-EA MT5 report cash flows.

Run `INSTALL.bat` once, then `RUN BACKTEST.bat`. Nothing in this folder can place a live order, and the active portfolio installer is not modified.

The installed `databento` package and `.env` key placeholder prepare the project for a later licensed-data adapter. The current reproducible study uses fresh Yahoo daily data because no Databento key or dataset entitlement is assumed.
