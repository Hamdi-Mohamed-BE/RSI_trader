# John Kurisko quad-stochastic validation

This is an isolated research project. It does not modify or install any active MT5 EA or BAT portfolio.

The test uses broker-sourced one-minute OHLC and recorded spread data for BTCUSD, XAUUSD, US100, US30, and EURUSD. The training window is 2022–2024. Every selected configuration is frozen before the untouched 2025–2026 validation window is evaluated.

Run `validate_quad_stochastic.py` to rebuild the results. See `VIDEO RULE MAPPING.md` for the distinction between rules explicitly stated in the interview and assumptions needed for a mechanical test.

