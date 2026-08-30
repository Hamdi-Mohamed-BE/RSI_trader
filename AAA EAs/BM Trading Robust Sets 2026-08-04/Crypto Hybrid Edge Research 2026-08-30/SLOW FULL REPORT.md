# Slower crypto edge — three-stage MT5 validation

The M15 candidates failed their locked test. A second, explicitly disclosed pass reduced signal frequency to H1/H4 and used development, validation, then a final six-month holdout.

| Symbol | Selected variant | Development return / PF | Validation return / PF | Final holdout return / PF | Win rate | Equity DD | Trades | Decision |
|---|---|---:|---:|---:|---:|---:|---:|---|
| ETHUSD | trend-h4-both-r07 | -2.78% / 0.85 | +0.64% / 1.10 | -1.01% / 0.92 | 51.52% | 6.77% | 33 | REJECT |
| BTCUSD | trend-h4-both-r10 | +1.34% / 1.06 | +1.18% / 1.19 | -1.44% / 0.89 | 48.28% | 6.33% | 29 | REJECT |

- Exness MT5 Trial 16, native Every Tick model, 100% history quality, random execution delay, spread, commission and swap included.
- $10,000 initial balance and 1% equity risk per trade.
- Development: 2024-08-29 to 2025-08-28; validation: 2025-08-29 to 2026-02-28; final holdout: 2026-03-01 to 2026-08-28.
- The second-pass investigation was started after the first M15 locked test failed; that sequence is disclosed to avoid presenting the research as a pristine one-shot discovery.
- No active BAT or website file was changed.
