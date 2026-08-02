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

To validate the connected MT5 account and start all five workers, run `run_all_live.bat` in this folder. The master launcher checks every environment and skips workers that are already running.

Every launcher changes into its own folder before running, so relocating the suite did not introduce absolute-path dependencies. Every bot connects to the account already open in MetaTrader 5 and performs broker-symbol discovery where applicable.

All five workers are live-enabled. Starting the master BAT can submit, modify or close orders on the account currently connected to MT5. Each strategy targets 1% risk per idea and falls back to the broker's minimum lot when the calculated size is smaller. EMA3, Asia Breakout, DmC and AMD share a 4% reserved-XAU-risk cap; US100 Weakness has a separate 1% daily-risk cap. Risk progression and classic grid trading are disabled.

See `BACKTEST_60D.md` for the frozen comparison and limitations.
