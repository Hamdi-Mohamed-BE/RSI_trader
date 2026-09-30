# Completed — intraday bias discovery, 29 September 2026

User requested discovery and survival testing of clock-time bias across US30, US100, SP500, XAU, BTC, ETH and major FX. Completed all 13 requested/fixed instruments on same-feed Exness five-minute history, September 2021–September 2026. No live trading or deployment.

Outcome: **zero strict survivors** among the 13 development-selected candidates. Gold long 23:00 London / 120 minutes is the only materially promising cross-period result (PF 1.39 / 1.42 / 1.48) but fails neighboring-time stability in development and holdout Holm correction (0.55). No replacement selection, refinement or native trading run after failures. Other finalists mostly lose in validation and holdout; EURUSD's tiny final-year gain disappears under cost stress.

Protocol RULES.md frozen before discovery; FINALISTS.json saved before validation/holdout evaluation. 10,826 distinct development configurations from a maximum grid of 11,232; 5,051,182 bars. Three time clocks, half-hour starts, three holding periods, both directions. No stops/indicators/regime or weekday optimization. One final candidate per instrument, no post-holdout fallback.

Evidence is Python fixed-notional replay plus 10,000 five-day block bootstrap paths per finalist, on native-exported bid bars. It is not a native strategy execution backtest or completion of the production EA pipeline. Spread floors use development-only data. Stress doubles modeled spread plus two ticks; it is hypothetical, not measured slippage. Commission is not separately modeled. No leverage, prop-firm claim or guarantee. Read REPORT.md and METHODS_SOURCES.md.

Audit: 14 unit tests pass, all holdout trades independently recalculated from exported prices, Holm calculation independently checked, all 14 exported files hash-verified. Seven older same-feed FX archives match common OHLC bars 100%. Live original terminal PID/creation time preserved; isolated collector exited; tracked git diff empty. Only this dated research folder and the unique tester-only collector binary were added. No production EA/SET/BAT/website changes.

Do not reinterpret gold as validated or retune using this observed holdout. Any future study must retain this failed test and seek genuinely new/incremental confirmation. Report includes post-generation readability clarifications only; selection/evaluation source and frozen protocol were not changed after results.
