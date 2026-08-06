# Start here — LTA mechanical EA

## Files

- `EA\LTA_Concepts_EA.ex5` — compiled MT5 Expert Advisor
- `EA\LTA_Concepts_EA.mq5` — auditable source code
- `EA\compile.log` — compiler proof: 0 errors and 0 warnings
- `Best Settings\` — one saved `.set` file per requested symbol
- `Backtest Reports\` — complete native MT5 HTML reports and graphs
- `LTA BACKTEST RESULTS.md` — plain-language result table and test method
- `LTA RULE COVERAGE AND LIMITS.md` — exact automation coverage and unavailable book inputs
- `EXNESS XAU VALIDATION 2026-08-06.md` — Exness broker retest, 1%–8% risk comparison, and selected lower-drawdown preset
- `EXNESS XAU DD5 OPTIMIZATION 2026-08-06.md` — risk-boundary tests and the selected preset below 5% historical drawdown
- `EXNESS XAU DD8 OPTIMIZATION 2026-08-06.md` — risk and breakeven tests for the selected preset below 8% historical drawdown

## Safety status

The EA and the selected Exness preset are installed in the standard MT5 data folder. The EA has **not** been added to the portfolio BAT.

Only the XAU M15 preset passed the untouched one-year test. The other five settings are marked `OOS FAIL` and are retained for audit/research only.

The current user-selected preset is `XAUUSD M15 - EXNESS FIXED 1.00pct.set`. It uses 1.00% of current equity per trade for both entry types, retains the strategy's contrarian breakeven rule, and disables the portfolio-wide move-all-to-breakeven override. Its one-year Exness test returned 92.15% with 14.82% relative equity drawdown. The DD5, DD8, and older 1.25% presets remain available for audit but are not the current selection. Test the fixed-1% preset on demo before considering live use; historical drawdown is not a guaranteed live cap.
