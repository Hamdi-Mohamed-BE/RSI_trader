# Chronos gold pilot: frozen protocol

Source: archived AAA Final/XAU weakness/data/XAUUSD.._M15_1000d.csv.
Validation: February 1 through April 30, 2026. Held-out: May 1 through July 31, 2026.
Model: amazon/chronos-2, pretrained, no fine-tuning. Input: last 256 completed
M15 bid closes. Forecast every clock hour, horizons 1, 2, 4 bars.
Each window is a separate series, cross-learning disabled. Forecasts use no future data.
Past market closures are compressed into trading bars; exclude forecasts spanning
missing future bars. Timestamps use the archive labels; broker timezone is unverified.

Direction is median forecast minus last close. Comparators: always long, last
one-bar momentum, opposite last one-bar momentum, and unchanged price forecast.
Choose a single horizon and signal threshold on validation only. Thresholds:
0, 0.1, 0.25, 0.5 of forecast 10%-90% interval width. Require 100 validation
trades; choose highest net mean price P/L, including costs. Also report all
unfiltered horizons on held-out; these are diagnostics, not a second selection.

Execution proxy: next bar bid open to horizon bar bid close, one round trip per
forecast. A long pays entry spread; a short pays exit spread. Assume point 0.01
(two-decimal archive prices), plus $0.10 adverse price slippage per side and
$7 commission per standard 100oz lot round trip ($0.07/oz). Stress adds $0.50/oz.
Bar spreads are proxies, not historic executable bid/ask ticks. Constant one ounce
exposure; no compounding, margin, stop, or take-profit. Realized drawdown only.

Report direction accuracy, MAE versus unchanged-price, 80% interval coverage,
trade coverage, net PF, net dollar-per-ounce P/L, monthly breakdown and a 95%
day-block bootstrap interval for mean P/L. No profitable edge is established
unless the frozen rule is positive after costs with consistent held-out evidence.
This pilot cannot establish generalization across years or exclude pretraining
contamination. It is not a verified live execution backtest or event-specific study.
