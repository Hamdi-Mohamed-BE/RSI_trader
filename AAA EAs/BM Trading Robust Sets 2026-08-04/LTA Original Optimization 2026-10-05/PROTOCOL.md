# LTA original-entry optimisation, frozen before search

Research only. User requested sequential optimisation, no deployed changes. First EA only: LTA Volume Profile on Exness XAUUSD. Isolated MT5 tester only; production sources, compiled bots, SETs, BATs, website caches and the running account must remain untouched. Stop after this EA and present the results for review.

## Evidence and splits

The current Recommended Safe M15 benchmark is the original EM1/EM4 market-entry strategy, 3R target, original structural stop, daily two-loss pause, 1% intended equity stop risk, original upward/minimum lot rounding. The prior October5 native year replay gave 219 whole positions / PF1.228 / +50.93% / 30.1% wins / 16.62% equity DD. The poor recent quarter was already observed. Previous M5 VWAP/POC and range-flow experiments are NOT substituted for the original strategy.

Development 2021-10-05 to 2024-10-05 exclusive (3 years): all parameter searches happen here. Validation 2024-10-05 to 2025-10-05 exclusive: rank three frozen finalists once. Candidate out-of-search recent test 2025-10-05 to 2026-10-05 exclusive, six months and quarter ending October5: apply the one chosen candidate without further tuning. Longer replay 2021-10-05 to 2026-10-05; older stress 2019-10-05 to 2021-10-05 if history exists. All these dates may have been seen in previous LTA development: temporal out-of-search evaluation is NOT virgin independent history. No claim of an untouched holdout or production qualification solely from this search.

Fast screens use native Model1 (generated every tick), 150ms execution delay. Finalists and the current benchmark use native Model4, same 150ms, historical bid/ask and recorded fees/swaps, USD10,000, leverage1:2000. Newest year mixes real/generated ticks, real history begins January2026. Model choice and dates are recorded per row. Same risk is held constant; risk is not optimised. Count wins and streaks per whole position including all costs and partial exits. Report native floating-equity DD; use daily sampled equity Sharpe with sqrt252, not MT5's incomparable Sharpe headline.

## Bounded staged search

This is an original-rule optimisation pass, not an exhaustive search over all possible strategies. Ineligible constructions (new limit/stop entry order engine, pyramiding, economic-data filters, other assets and leveraged risk searches) are deferred, not represented as tested. Original D1/H1 macro logic, Markov Safe gate (40 / 5% /0.05) and broker profile algorithm stay fixed. Changes are research-only inputs, default OFF. Verify OFF parity against the prior current Safe native year run before any search.

At each stage carry forward the best three distinct configurations. Development minimum 60 whole positions, positive net P/L, PF>=1.10; preferred PF>=1.20 and at least50% net wins. Rank qualifying PF>=1.20/high-win candidates first, then PF and return/DD with minimum counts, daily equity Sharpe and longest win/loss runs as tie breakers. If none meets PF>=1.20 and50% wins, retain the best positive expectancy candidates and label the objective unmet. Never select maximum return alone. No candidate enters the live portfolio.

Stages, frozen values:
1. Execution timeframe M5/M15/M30/H1 (profiles stay M15; wider timeframe changes the signal meaning). Exclude M1/M3 high-turnover microstructure and H4/D1 mismatch to existing intraday entry definitions.
2. Entry models EM1+EM4 original, EM1 only, EM4 only, EM2 only, EM3 only, all four; unchanged market entry at new bar on closed signal.
3. Stop geometry original structure, structure-distance x0.75/x1.25/x1.5, ATR(14) x1/x1.5/x2, and 0.25% price. All stops and targets broker-valid; actual fill/risk exported.
4. Target R0.5/0.6/0.75/1/1.25/1.5/2/2.5/3/4/5/6.
5. Management original no-all-BE, BE at0.5R/1R, native dynamic50/20 (M15 closes), ATR trail from1R at1ATR/2ATR, 50% partial at1R plus BE (broker minimum-lot partial skipped/logged). No stop is ever widened. Pending/current original entry rules unchanged.
6. UTC entry sessions all, Asia00-08, London07-12, NewYork13-21, overlap13-16. These are fixed existing UTC blocks, NOT DST-adjusted US cash-open sessions.
7. Direction both, long only, short only.
8. ADX(14) on completed execution bars: off, >=20, >=25; DI direction only; ADX20+DI, ADX25+DI. Filters block entries, never protective exits.
9. Daily maximum trades 1/2/unlimited (original one concurrent position and two-loss pause retained); day exclusions none/Monday/Friday/both. Do not disable safety controls to increase trade count.

Stable plateau: joint neighbours of the final development candidates varying R +/-20% and stop factor +/-20%; at least 2/3 neighbours positive and median PF>=1.10 with minimum30 development positions. Freeze three finalists, check Model4 development/validation. Validation needs >=20 positions, positive P/L, PF>=1.15; prefer PF>=1.20 and >=50% wins. Choose once using validation, never recent-period results. If recent PF<=1 or loss, flag/reject rather than retune.

## Robustness

On the frozen candidate's native Model4 whole positions: 10,000-path block bootstrap, block5; reshuffle longest losing streak / closed-path DD; 10% and20% random omission; count all distinct configurations tried for deflated daily-equity Sharpe. Extra cost stress must be based on exported actual fill versus requested price, not invented fees; if nearly zero, say it is a weak stress. Ledger Monte Carlo cannot reconstruct floating-equity margin or a shared FTMO account. No FTMO pass-probability forecast or portfolio promotion is made in this bounded EA review.

Save every tested setting, report/journal, position ledger, hashes, rejection and selection reasoning. Report current vs selected candidate over recent quarter,6m,1y,3y/5y where tested; returns, net PF, net win rate, counts, trades/month/weekday, native equity DD, daily equity Sharpe, W/L max and costs. A promising retrospective candidate stays exploratory pending prospective/broker validation and user approval.
