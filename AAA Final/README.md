# AAA Final trading suite

Latest model audit: [ROBUSTNESS_AUDIT_2026-08-02.md](ROBUSTNESS_AUDIT_2026-08-02.md)

| Project | Live launcher | Research launcher | Actual live environment |
|---|---|---|---|
| DmC | `DmC\\run_live.bat` | `DmC\\run_backtest.bat` | enabled |
| Asia breakout | `asia breakout\\run_live.bat` | `asia breakout\\run_backtest.bat` | enabled |
| AMD | `AMD\\run_live.bat` | `AMD\\run_backtest.bat` | enabled |
| EMA3 | `EMA3\\run_live_bot.bat` | `EMA3\\run_backtest.bat` | enabled |
| US100 weakness | `US100 weekness\\run_live.bat` | `US100 weekness\\run_backtest.bat` | enabled |

Every launcher changes into its own folder before running, so relocating the suite did not introduce absolute-path dependencies. Every bot connects to the account already open in MetaTrader 5 and performs broker-symbol discovery where applicable.

The actual `.env` files are live-enabled as requested. Starting a live BAT can submit, modify or close orders. Do not run overlapping bots on the same symbol unless their combined exposure is intentionally budgeted.

See `BACKTEST_60D.md` for the frozen comparison and limitations.
