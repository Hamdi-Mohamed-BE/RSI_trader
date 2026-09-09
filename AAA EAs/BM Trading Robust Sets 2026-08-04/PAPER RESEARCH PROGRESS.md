# Calyx paper research progress

Last updated: 2026-09-09

| # | Research idea | Scope completed | Status | Key evidence / next action |
|---:|---|---|---|---|
| 1 | Hedging-demand rest-of-day momentum | Raw paper implementation plus XAU, XAG, EURUSD, GBPUSD, GBPJPY and US30 transfer tests | Rejected | All three-year transfers lost money. Keep the reports for reference; no portfolio strategy survives. |
| 2 | London Open FX Momentum | Raw test and full pipeline on USDJPY and EURUSD | USDJPY watch/demo by user approval; EURUSD rejected | USDJPY selected full history: +178.41%, PF 1.46, win rate 53.97%, DD 12.12%, 693 trades. Latest year: +12.72%, PF 1.33, win rate 51.85%. EURUSD failed the latest year. |
| 3 | Gold VWAP-EMA Regime | Raw paper reconstruction on XAUUSD | Rejected | Five-year return -4.08%, PF 0.95, win rate 31.49%, DD 18.41%. Do not optimize further unless the data model changes. |
| 4 | Bitcoin Overnight MAX(10) | Raw replication and complete locked Calyx pipeline on BTCUSD | Rejected | Optimized locked return -18.32%, PF 0.53, win rate 22.41%, DD 19.17%. Latest year also negative. |
| 5 | Noise-Boundary VWAP Momentum | Raw US500/USTEC screen and complete 83-case locked pipeline on USTEC | Rejected | Optimized locked return -3.87%, PF 0.93, win rate 30.57%, DD 17.82%, 157 trades. Monte-Carlo P(profit) 36.14%. Latest year recovered, but cannot override the failed locked window. |
| 6 | Post-FOMC FX Reversal | Raw timing implication tested on seven FX CFDs plus raw transfer to XAU, XAG, BTC and US100 over 5y, 3y and 1y | Raw complete — awaiting review | FX transfer failed recently. Non-FX five-year basket: +2.32%, pooled PF 1.53, win rate 50.62%; XAU and BTC stay positive in every window, while US100 fails latest year. No production change. |
| 7 | Value Area Reversion / “Stupid Simple Order Flow” | Raw reconstruction and full 456-case pipeline on XAUUSD, XAGUSD, BTCUSD and USTEC | XAU/BTC watch only; XAG/US100 rejected | XAU optimized locked: +6.90%, PF 1.54, win rate 63.16%, DD 4.28%, 38 trades, but latest year -0.42%. BTC optimized locked: +3.30%, PF 1.34, win rate 56.67%, DD 5.71%, only 30 trades. Neither clears production gates. |
| 8 | Precious-metals Night Effect | Publicly auditable raw momentum branch mapped to Exness XAUUSD and XAGUSD CFDs over 5y, 3y and 1y | Rejected | XAU: -18.52%, PF 0.84, win rate 47.34%, DD 19.86% over 5y. XAG: -94.29%, PF 0.15, win rate 27.65%, DD 94.29%. Every period is negative before commission. No production change. |

## Current non-paper queue

1. **DMC Fresh-Reaction research — complete, awaiting production decision.** The approved isolated filter was implemented and tested in 100 native MT5 cases. XAU candidate: locked +6.88%, PF 1.90, win rate 46.67%, DD 3.11%, 15 trades; three-year +36.18%, PF 2.49, win rate 60.00%, DD 4.08%, 55 trades. US100 candidate: locked +3.68%, PF 1.88, win rate 66.67%, DD 2.99%, 12 trades; three-year +17.94%, PF 1.99, win rate 65.22%, DD 4.39%, 46 trades. Both are watch/demo candidates because the locked samples are small. US30 and BTC were rejected. No active EA, BAT, portfolio or website change was made.
2. **Post-FOMC reversal — raw CFD tests complete, awaiting review.** All seven FX pairs lost in the latest year. The raw non-FX transfer is promising on XAU and BTC, secondary on XAG, and rejected on US100. No production action before review.
3. **Precious-metals Night Effect — raw CFD transfer rejected.** The accessible paper rules lose on both XAUUSD and XAGUSD in 5y, 3y and 1y native tests. No pipeline or production action is warranted.

## Pipeline control

- Risk is dynamic equity percentage and defaults to 1% for non-news research.
- Parameter selection uses development data only.
- Settings are frozen before native MT5 Every-Tick locked tests.
- Broker spread, commission, swap and random execution delay are included.
- Rejected work stays in research folders and is not added to the recommended system.
