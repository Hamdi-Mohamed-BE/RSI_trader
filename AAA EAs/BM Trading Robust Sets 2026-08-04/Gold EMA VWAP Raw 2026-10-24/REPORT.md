# Gold EMA + VWAP raw study 2026-10-24 — REJECTED at the raw gate

Owner request: "find and backtest a good EMA + VWAP combo on gold". Two published TradingView rule sets were found and
frozen in `RULES.md` before testing, with the missing details written down as assumptions.

- **Test setup:** native MT5 Model 4, XAUUSD, $10k, 1% risk, end 2026-10-24.
- **Runs:** 26 runs with 0 errors; 8 place failures over A's 5 years.
- **Files:** `RESULTS.md`, `RESULTS.json`, `balance.png`.

## Verdict

| Version | 5y return | 5y PF | 3y | 1y | Trades / month | Trades / day | Eq DD 5y | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A — EMA 5/13 cross + VWAP / ADX / separation, M15, stop at EMA cross, 2R | −79.1% | 0.86 | −29.5% (PF 0.95) | −3.8% | 28.3 | 1.30 | 81.6% | **FAIL** |
| B — EMA 9 crosses session VWAP + EMA 9/21 trend + VWAP slope, M5, 1.5 ATR, 2R | −15.4% | 0.93 | −15.9% (PF 0.90) | −4.3% | 5.3 | 0.24 | 29.3% | **FAIL** |

- **No window works.** Neither version made money in the dev, validation or OOS window except B in dev (+1.7%).
  A's last 6 months were +2.7% with PF 1.02, which is noise.
- **The VWAP part does reduce losses, but not into profit.**
  - A without VWAP lost 88.8% over 5 years.
  - A with no filters (pure EMA 5/13 cross) lost 100%.
  - B without its VWAP-slope filter lost 100%.
  - Both main versions beat their coin-flip-direction controls (A −81% to −85%; B −1% to −40%). So the filters cut losing
    trades, but no positive edge remains after spread.
- **Sensitivities:** none reaches PF 1.15.
  - The best are B with VWAP reset at server midnight (+18.9%, PF 1.07) and B with a 3R target (+12.1%, PF 1.05).
  - Both are post hoc and below the gate, so they are not recommended for optimisation.

## Disclosures
- **Unclear published rules:** the A stop ("EMA intersection"), ADX length, separation threshold and B's slope
  definition were not published. The assumptions are in `RULES.md`.
- **Ticks:** real from 2026-01-01; earlier ticks are generated.
- **VWAP volume:** tick volume, not exchange volume.

No optimisation, nothing installed, nothing pushed.
