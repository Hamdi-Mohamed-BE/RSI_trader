# AAA Final — frozen 60-day validation

Generated 2026-08-01 using history from the MT5 account already connected to the terminal. MT5 M1/H4 data was used because it preserves the connected broker's symbols, spreads and session timestamps; TradingView is suitable for chart confirmation but was not substituted for executable broker history.

| Bot | Market | Actual data range (UTC) | Trades | Win rate | Profit factor | Max drawdown |
|---|---|---|---:|---:|---:|---:|
| DmC pullback | NAS100U6 | 2026-06-15 01:00 — 2026-07-31 23:54 | 9 | 55.56% | 1.07 | 3.96% realized / 4.21% intratrade |
| Asia breakout | BTCUSD | 2026-06-02 — 2026-08-01 | 29 | 75.86% | 1.93 | 6.08% |
| Asia breakout | EURJPY.. | 2026-06-02 — 2026-08-01 | 9 | 44.44% | 1.99 | 6.45% |
| Asia breakout | XAUUSD.. | 2026-06-02 — 2026-08-01 | 18 | 72.22% | 3.27 | 5.30% |
| AMD article model | XAUUSD.. | 2026-06-02 — 2026-08-01 | 11 | 90.91% | 4.71 | 3.00% |
| EMA3 pivot reversal | XAUUSD.. | 2026-06-02 11:38 — 2026-08-01 11:38 | 23 | 43.48% | 1.00 | 403.26% realized / 394.97% equity |
| US100 weakness | NAS100U6 | 2026-06-15 01:00 — 2026-07-31 23:54 | 8 | 50.00% | 3.28 | 3.96% |

## Interpretation

- AMD was strongest in this small in-sample window, but 11 trades are not enough to establish a durable edge.
- The Asia XAU configuration was the next strongest; its 18 trades are still a small sample.
- US100 weakness produced a good PF from only eight trades and needs additional contract/history validation.
- The literal DmC video translation did not reproduce the advertised 2+ PF: PF was 1.07 over nine trades. It remains a research baseline, not a validated live edge.
- EMA3's unconstrained pivot-to-opposite-pivot exits generated account-ruin-level intratrade exposure at fixed 0.10 lot. It should not be treated as live-safe merely because the final net result recovered to +3.31%.

All figures are historical simulation results and include the assumptions encoded by each project. They are not guarantees of future execution or returns.

## MT5 comment contract

Opening orders now use `bot_name setup_rank simple_reason` and stay within MT5's 31-character comment limit:

- `DmC A+ D1+H4 aligned`
- `AsiaBreakout A BUY range break`
- `AMD A+ AF BUY session fade`
- `EMA3 B+ H4 pivot reversal`
- `US100Weak A+ S2B RUN`
