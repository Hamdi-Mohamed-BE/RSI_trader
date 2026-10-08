# DAX momentum research pipeline

This study implements the user's explicit date override: develop on 2020–2023,
then evaluate the frozen candidate from 1 January 2024 through the last available
tick on 7 October 2026. It does not change the central two-year OOS policy.

## Split and sequence

1. Verify the original source, binary and preset fingerprints. Run the production
   binary on DE30 over 2020–2023. Require exact research-copy trade parity.
2. Search only 2020–2022, with two retained candidates at each declared stage.
   Test opening anchor, timeframe, EMA, initial stop, target, trailing stop,
   break-even, holding time, quality filters, direction/weekdays, adaptive targets
   and dynamic trailing. Record all trials, including losing/rejected trials.
3. Test ±20% stop/target-or-trail neighbours on development history. Select at
   most three development finalists for tick-level 2023 validation.
4. Freeze the selected configuration, internal-validation verdict and trial count.
   Rerun full 2020–2023 without reselecting. Evaluate only the frozen candidate
   and unchanged baseline on 2024 onward, yearly and recent windows.
5. Run delay and half-risk sensitivity; 10,000 five-observation block-bootstrap
   paths; Wilson win-rate intervals; trial-adjusted Sharpe; chronological/recent
   stability; measured additional-spread sensitivity; native floating DD audit.

The raw 2020–2023 baseline PF is below the usual 1.15 development gate. The
user requested optimisation, so continuation is explicitly exploratory. A good
later result does not erase that failure. The baseline's future history was
already examined in an earlier study: this is a retrospective temporal holdout,
not a genuinely unseen prospective validation.

## Execution and limitations

- All tests use the isolated research terminal, an empty chart profile and
  disabled normal-account Expert Advisors. No active trading API is used.
- Search uses M1 OHLC screening. Finals use native every-tick mode with real
  ticks where available. Development has 0% real ticks; DE30 broker real-tick
  history starts in January 2026. Earlier ticks are generated, not historical
  bid/ask tape. Read each native report's real-tick share.
- $10,000 starting balance, USD, 1% current-equity risk target, 150 ms execution
  delay, broker commission, spread, swap and fee included. Original minimum-lot
  and upward lot-step rounding remain; actual risk may exceed the target.
- Each displayed window starts a new account; do not add yearly-window returns.
  Today is incomplete. Native tester end-of-window liquidations are included.
- Original entry is the signal candle's **close versus EMA**, not necessarily
  bullish/bearish candle-body confirmation. Body agreement is a separate trial.
- Native maximum relative floating equity DD is authoritative. One-minute
  balance/equity exports permit a daily-equity Sharpe and sampled equity curve,
  but can miss intraminute drawdown. MT5's chart-sensitive Sharpe is not used
  for selection or the main final comparison.
- Monte Carlo is a circular block bootstrap, not new market paths, an exact
  compounding/risk-management simulator, or an FTMO pass-probability model.
  It preserves local five-observation blocks but not all market dependence.
  It uses closed-balance daily returns / trade cash for policy risk proxies;
  native floating DD and daily-equity Sharpe are measured separately.
- Added-cost sensitivity charges one **additional** measured full spread per
  trade. Existing costs remain in the original P&L. It is not an exact quote-
  widening rerun. Delay sensitivity is separately rerun natively.
  In this study the sampled 2026 bid/ask quotes have zero spread: no positive
  cost was invented, additional-spread stress is unavailable, and its gate
  fails. Recent results may be optimistic if these quotes do not reflect
  executable spreads.
- A staged beam search is not an exhaustive global optimum. OOS results never
  trigger another parameter search or candidate switch in this study.

## Outputs

`Results.html`, `SUMMARY.json`, `AUDITS.json`, `FROZEN.json`, complete search and
validation tables, native report/deal/equity/quote archives and original-binary
parity proof. The `Frozen Research EA` export is **tester-only**; it refuses live
charts. Its compiled candidate fields are recorded in `FROZEN.json`; its small
`.set` controls case index, audit tag and risk, not a production preset.

Live EAs, normal/FTMO BATs, website, production presets and central policy remain
unchanged. No Git commit, push or live install is performed by this study.

Resume with `pipeline.py all` in the existing EA-store Python environment plus
pandas. Batches are immutable and cached only when dates, settings, risk,
execution model and engine fingerprints match exactly.
