# Recent EA comparison — 30 September 2026

24/24 fresh native tests verified. Twelve shortlisted current presets; not an exhaustive rerun of all 35 EAs.

Six months: 30 March–29 September 2026. Three months: 30 June–29 September 2026. End date is exclusive; September 30 is incomplete.

$10,000 separate starting balance per test, Exness-MT5Trial16, real-tick model, 150 ms delay, original selected 1% sizing. Three-Way Gold can risk 1% per module; risk stacks. Lot rounding, overnight exits and overlapping positions mean returns are not equal-risk portfolio forecasts. Existing settings unchanged; no optimization.

Win rate and profit factor below are recomputed per closing deal, reconciled to MT5 trade counts, including reported commission/swap. Partial exits can count separately and are not independent setups (particularly 3-Way Gold). Same-side entry fees are allocated by matched volume; FIFO fragments are recombined by exit ticket, not counted as extra trades. Drawdown is native maximum relative EQUITY drawdown, including open P&L. No additional hypothetical broker commission was inserted.


## Recent screen

Positive return, net PF ≥1.20 in both overlapping windows, at least 20 six-month and 10 three-month trades. A pass is only a recent screen, not independent validation. Ranking is six-month net win rate, not expected future profit.

| EA | 6m win | 6m PF | 6m return | 6m equity DD | 6m trades | 3m win | 3m PF | 3m return | 3m trades | Max win/loss streak 6m | Screen |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Gold Overnight Value Area | 72.0% | 1.73 | +11.90% | 3.86% | 100 | 69.2% | 1.08 | +0.80% | 52 | 11/3 | 3m PF below 1.20 |
| XAU RSI VWAP | 71.9% | 1.32 | +3.51% | 3.80% | 32 | 72.2% | 1.51 | +2.76% | 18 | 7/3 | PASS |
| 3 Way Gold | 67.9% | 1.18 | +3.57% | 8.82% | 53 | 69.2% | 1.05 | +0.49% | 26 | 12/6 | 3m PF below 1.20; 6m PF below 1.20 |
| Nasdaq Overnight | 60.7% | 1.44 | +4.34% | 2.50% | 56 | 51.5% | 1.02 | +0.13% | 33 | 9/4 | 3m PF below 1.20 |
| BTC Top Down FVG Liquidity | 54.5% | 2.26 | +6.98% | 2.19% | 11 | 40.0% | 1.26 | +0.84% | 5 | 3/2 | 3m insufficient sample; 6m insufficient sample |
| US100 H1 ORB 13UTC | 50.0% | 1.00 | +0.03% | 3.62% | 36 | 50.0% | 0.86 | -0.78% | 16 | 4/4 | 3m nonpositive profit; 3m PF below 1.20; 6m PF below 1.20 |
| Nasdaq 5M Candle Momentum | 48.9% | 1.40 | +19.79% | 6.55% | 88 | 48.9% | 1.23 | +5.62% | 45 | 5/6 | PASS |
| US100 Month End Flow | 47.1% | 2.03 | +8.01% | 3.36% | 17 | 44.4% | 1.42 | +1.84% | 9 | 3/3 | 3m insufficient sample; 6m insufficient sample |
| ORB Volume Profile Volume Confirmed | 46.7% | 2.90 | +12.17% | 2.98% | 15 | 50.0% | 3.99 | +6.40% | 6 | 3/3 | 3m insufficient sample; 6m insufficient sample |
| ORB Volume Profile | 44.4% | 1.94 | +13.77% | 4.80% | 36 | 31.6% | 0.93 | -0.61% | 19 | 6/6 | 3m nonpositive profit; 3m PF below 1.20 |
| USDJPY London Open Momentum | 40.9% | 1.31 | +7.11% | 7.71% | 66 | 45.7% | 1.01 | +0.16% | 35 | 8/13 | 3m PF below 1.20 |
| LTA Volume Profile | 30.8% | 1.25 | +25.09% | 13.82% | 107 | 22.9% | 0.86 | -5.56% | 48 | 5/12 | 3m nonpositive profit; 3m PF below 1.20 |

## Material caveats


- 3-Way Gold failed an earlier 2019–2021 holdout. Its latest strong figures do not make it a validated production recommendation.
- Gold Overnight has weak longer-term expectancy; judge the latest three-month deterioration, not just its winning percentage. Its six-month test includes one rejected entry on April 13 (invalid stops); do not confuse duplicated journal/summary matches with separate rejected orders.
- News Pulse is excluded from this fresh ranking: checked-in verified calendar covers only 12 June–11 September 2026. Older cached results and fitted event settings are not fresh, independent evidence through today.
- Twelve shortlisted presets were selected from existing evidence. Selection bias remains. The windows overlap; neither is a newly reserved holdout. Do not add their returns together or promise these win rates.
- All results are simulated, not the recipient’s broker or live trading. Spread, slippage, fees and symbol contracts can change results.

## Monthly licensing plan (not implemented)

The store already has single-EA BAT/ZIP generation, per-product keys, account/server binding, expiry and revoke/extend controls. A five-EA customer bundle can reuse these components, but a customer installer is not an administrator licence builder.

1. Owner selects the five authorised EA versions and recipient account/server. Generate separate licensed EX5 files, matching SETs and one portfolio installer. Do not ship source code, original unlicensed EX5s or signing secrets.
2. Set a true 30-day runtime expiry, not merely the existing 12-month update entitlement. Only an owner action extends expiry; routine licence checks do not renew it.
3. Enforce entitlement inside each EA, not in the BAT. Use HTTPS and a signed expiration/account/product entitlement; cap any offline grace at the entitlement expiry.
4. On expiry, prevent new entries and cancel that EA’s own pending entry orders, but continue protective management of existing positions until flat. Do not interfere with unrelated/manual trades.
5. Test expiry, renewal, offline/restart behaviour, wrong account/server, altered settings and all original strategy exits on demo before distribution; then verify licensed/unlicensed backtest parity.
IMPORTANT: current code checks about every 24 hours, allows 72 hours offline after last success and uses ExpertRemove on denial. That can stop trailing/time exits and is unsuitable for the proposed precise, safe monthly expiry without changes. Server expiry support alone is not sufficient.
MQL5 WebRequest requires an allowed URL and does not execute in Strategy Tester: https://www.mql5.com/en/docs/network/webrequest . ExpertRemove stops the EA: https://www.mql5.com/en/docs/common/expertremove . Licence lifecycle therefore needs demo tests as well as backtests.
No licence was issued, no package distributed, no live terminal changed and no website evidence overwritten in this study.