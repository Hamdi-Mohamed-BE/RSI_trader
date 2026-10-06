# Slow Trend sequential optimisation — research only

Frozen before the first new backtest, 5 October 2026. Next EA after LTA. The user clarified: do not remove or deploy anything. No live MT5 connection, chart attachment, terminal restart, source/EX5/SET replacement, BAT, website, inventory or Git changes. Only dated research copies and the isolated tester are used. Stop after this EA for review.

## References and parity

The actual normal BAT source is `Gold Targets Deployment 2026-10-02/EA/Calyx Slow Trend EA.ex5`, with `Sets/xau-slow-trend-normal.set`: H4, 1/3/6-month vote, EMA100 trading-day-scaled filter, both sides, first eligible quote, ATR14 x1.5 stop, fixed 1R, no management, one position, 24-hour cooldown. The FTMO SET changes only the target to 0.5R. It is compared at the same nominal 1% risk to isolate the target; this is NOT the guarded FTMO $50 profile or a pass/payout forecast.

The research copy keeps defaults OFF and the original entry/exit clock, ATR, EMA, horizons, risk rounding and cooldown. It adds tester-only auditing and switches. Shipped-binary versus all-OFF research parity must match every native entry/exit time, price, volume and cost over the recent year before searching. Normal and FTMO references each get parity. Broker minimum/upward lot rounding remains and can exceed the intended risk.

## Split and execution

- Development: 2021-10-05 to 2024-10-05 exclusive. All searching here.
- Validation: 2024-10-05 to 2025-10-05 exclusive. Three finalists checked once; select one before recent results.
- Recent out-of-search: 2025-10-05 to 2026-10-05 exclusive, plus six months from 2026-04-05 and quarter from 2026-07-05.
- Longer replay: three years from 2023-10-05 and five from 2021-10-05, all ending 2026-10-05 exclusive.
- Older stress: 2019-10-05 to 2021-10-05 exclusive if covered.

All these periods may have been used in prior research. No virgin holdout claim. Exness XAUUSD, separate USD10,000 account, nominal 1% equity risk, leverage1:2000, 150ms delay, recorded broker costs. Screens use Model0 generated every tick; confirmations use Model4, which falls back to generated ticks where real ticks are missing. No OHLC screen is mislabeled every tick. Only `_Backtests/MT5-DMC-20260811`, empty chart profile and live expert permission disabled. Use the same exclusive tester lease as the LTA study and check the isolated process and port3000 before each run. No existing process is killed.

Native reports/input hashes, complete deals including magic-zero final liquidation, events, equity and logs are archived. Whole positions aggregate partial exits and every fee/swap; tiny breakeven losses remain losses. Native floating-equity DD, daily sampled equity Sharpe with sqrt252, net PF, returns, trades/month and per weekday and max win/loss runs are reported.

## Bounded original-strategy staged search

This is not an exhaustive search over all possible strategies or the complete promotion pipeline. No new pending-order engine, pyramiding, risk optimisation, new asset, news filter or regime-ML model. Retain top three per stage; all attempts counted. The raw reference is allowed to fail: optimisation then remains explicitly exploratory, not a production qualification.

1. Timeframe H4/D1/W1. These are the three timeframes for which the existing ScaleBars method preserves the intended trading-day horizons. Intraday alternatives below H4 would silently change monthly horizons in the original implementation, so are excluded.
2. Momentum horizon: 1m, 3m, 6m, original1/3/6m, 3/6/12m; original majority vote versus unanimous vote; optional same-direction completed signal candle confirmation. No future candle information.
3. Trend filter: none, existing EMA100, EMA200, EMA200 plus21-day slope, all scaled as original. Closed bars only.
4. Initial stop: ATR x0.75/1/1.5/2/3; original swing/clamped; original chandelier/clamped; price0.25/0.5%; fixed gold price distances10/20; completed signal candle extreme with the original0.75–5ATR clamp. No stop widening after entry.
5. Management, M15-close clock retained: original none; BE at0.5R/1R; ATR trail from1R at1.5/2.5ATR; original chandelier from1R; original step0.5R→0.2R; percentage trail from1R at0.25%; 50% partial at1R plusBE (skip/log partial if broker minimum would be violated). Managed alternatives use an explicit broker stop-distance guard; OFF reference retains original behaviour.
6. Targets fixed0.5/0.6/0.75/1/1.25/1.5/2/2.5/3/4/5/6R; original signal-reversal exit withoutTP; noTP with chosen management and a5-day limit; original adaptive4R unanimous/1.5R mixed-vote exit. No-TP variants still retain a stop.
7. Fixed broker-clock entry blocks all/00–08/07–12/13–21/13–16, and original exact-minute alternatives01:00/08:00/13:30/14:00. Fixed presets, not independently verified exchange/DST sessions. Exit management stays active outside entry hours.
8. Direction both/long/short. ADX14 on the completed signal bar: off/20/25; DI only; ADX20+DI/ADX25+DI. Filters gate entries, never protective exits.
9. Original cooldown or48/72 hours; day exclusions none/Monday/Friday/both; maximum hold original/2/5days. Single position retained. W1 original cooldown remains7days; never loosen it to create artificial trade count.

Canonicalise inactive parameters before counting; repeated settings are reused, not presented as independent trials. Development eligibility: at least60 whole positions, positive net, PF>=1.10, zero audited execution rejections. Prefer PF>=1.20, >=50% net wins and winning run greater than losing run; then PF/return-to-DD/sample-size strength, daily equity Sharpe and streak balance. Goal-met preference never rescues a negative expectancy variant. If a stage has no eligible candidate, explicitly labeled exploratory seeds with >=30 trades and valid execution may be carried on PF and return/DD even if negative; this permits the requested loser optimisation without claiming the original gate passed. No execution-valid30-trade seed means stop. Final dev/validation gates remain unchanged.

Plateau: RR +/-20% and ATR stop multiple +/-20% (for non-ATR stops vary their active distance), joint3x3; at least2/3 neighbours execution-valid, positive and >=30 trades, median PF of valid neighbours>=1.10. Three native Model4 dev+val finalists. Validation >=20 trades, positive net, PF>=1.15 and no execution rejection, with the same high-win/streak preference. If none qualifies, retain only a labeled unqualified exploratory candidate for descriptive comparison. Freeze once before recent windows. A recent loss/PF<=1 means rejection; never retune on recent results.

## Robustness and output

10,000-path whole-position proportional closed-return block bootstrap (length5), shuffle,10/20% trade omissions,95% Wilson win-rate interval, approximate actual-trial-count deflated daily-equity Sharpe and stress using actually recorded extra commissions/negative swaps/adverse requested-versus-filled entry slippage. Count the actual distinct settings. No invented spread, fees or slippage. Ledger resampling cannot model floating equity, exact broker lot recalculation, portfolio margin, elapsed days or FTMO pass probabilities. Do not promote if bootstrapP5 return<=0 or P5PF<=1 or deflated Sharpe below95%; full portfolio/prop validation is deferred rather than claimed complete.

Standalone report contains all tested settings, frozen selection, failures, graphs, recent and3/5-year comparisons against both targets where tested. No production changes. Await review before Trend Progression.
