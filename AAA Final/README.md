# AAA Final trading suite

Latest model audit: [ROBUSTNESS_AUDIT_2026-08-02.md](ROBUSTNESS_AUDIT_2026-08-02.md)

## Selected live portfolio

| Project | Selected setup | Risk per idea | Master launcher |
|---|---|---:|---|
| EMA3 | XAUUSD H4, pivot 5, EMA200 slope/6, trail 1.5R/1R | 1.00% | enabled |
| Asia breakout | XAUUSD confirmed-close/retest, midpoint stop, 3R, trail 2R/0.5R | 1.00% | enabled |
| DmC | XAUUSD previous-body reaction/retest, fixed 1.7R | 1.00% | enabled |
| AMD | XAUUSD expanded AMD article model | 1.00% | enabled for forward testing |
| US100 weakness | US100 S2A reference-pair/OCO model, capped at 1.7R | 1.00% | enabled for forward testing |
| XAU news pulse | PPI OCO, 5R, one re-entry | 1.00% cap | live-enabled with automatic calendar refresh |
| Weekend direction | Rejected ML gate / provisional momentum research | 1.00% cap | live-ready process; validation gate currently returns `NO_TRADE` |

To validate the connected MT5 account and start all seven workers, run `run_all_live.bat` in this folder. Each worker opens in a separate visible terminal whose title contains the bot name. The master launcher checks every environment and skips workers that are already running. To run without visible terminals, use `run_all_live.bat hidden`.

Run `stop_all_bots.bat` to stop all seven workers (or run `run_all_live.bat stop`). It only closes processes launched from this suite; MetaTrader 5 and existing positions or pending orders are not changed.

Every launcher changes into its own folder before running, so relocating the suite did not introduce absolute-path dependencies. Every bot connects to the account already open in MetaTrader 5 and performs broker-symbol discovery where applicable.

All seven working `.env` files are live-enabled. News Pulse can submit only after its PPI event filter and complete T-30/T-15 lifecycle pass. Weekend Direction is technically live-ready but still returns `NO_TRADE` because its selected ML model is rejected; live switches never bypass validation. `run.bat` inside either new project remains a forced paper cycle. Risk progression and classic grid trading are disabled.

The master launcher does not create a portfolio-wide risk lock between different bots. Several workers can independently trade XAUUSD, so simultaneous 1% setups can add together. Start only the workers whose combined exposure you intend to accept.

See `ALL_BOTS_BACKTEST.md` for the complete seven-worker breakdown and `BACKTEST_60D.md` for the original frozen comparison.
