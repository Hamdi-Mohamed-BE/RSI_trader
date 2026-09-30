# What the research actually supports

Review date: 2026-09-28. Primary-method checks, not a claim to have reproduced every original dataset or independently verified the interviewer's career/payout claims.

## 1. Intraday momentum -> interview ORB

Gao, Han, Li and Zhou study whether the return from the prior close through 10:00 predicts the final half-hour return. Their timing model trades at 15:30, not at the morning range breakout. The paper reports a small predictive relationship, with variation across market conditions. Its economic interpretation is not proof of a particular order-imbalance mechanism. Our 30-minute ORB is a new hypothesis inspired by the interview; neither a universal optimal range nor the best reward/risk follows from the cited finding. [Primary manuscript, methodology pp. 6-8 and timing pp. 17-18](https://assets.super.so/e46b77e7-ee08-445e-b43f-4ffd88ae0a0e/files/ee7dac49-530b-4950-b5d0-e0b5eee08f2e.pdf); [SSRN record](https://ssrn.com/abstract=2440866).

## 2. VWAP direction

The authors' model reverses exposure when the completed one-minute price signal changes side of regular-session VWAP and holds no overnight position. Original sizing allocates all available equity without leverage; there is no fixed stop-distance risk budget. They assume no fill slippage and explicitly call the work exploratory. Consequently their reported ETF return cannot be imported into an MT5 CFD account. Our version changes instrument, volume source, sizing and execution; its ATR stop is an additional hypothesis. [Author PDF, sections 3.1-3.4](https://concretumgroup.com/wp-content/uploads/2026/02/Volume-Weighted-Average-Price.pdf). A local source copy and rendered methodology page are in papers/.

## 3. Post-earnings announcement drift

The 2006 Livnat/Mendenhall study finds a larger measured drift when surprise is based on analysts' forecasts than when based on a time-series earnings model. This supports distinguishing the data definitions; it does not make today's consensus a valid substitute for the forecast known before each historical release. [Publisher abstract](https://onlinelibrary.wiley.com/doi/10.1111/j.1475-679X.2006.00196.x).

For our interview-inspired implementation, earnings release timestamps, historical consensus, actual EPS, universe membership, delistings and individual-stock prices are missing. The 60-session hold is specified, not optimized or asserted universally optimal. No valid actual-data result or prop pass estimate is available. Do not replace these inputs with index candles, current analyst estimates or a surviving-stocks-only list. Broker access to the relevant equities and financing would also need confirmation.

## 4. Overnight effect

Cliff, Cooper and Gulen decompose the historical US equity premium and find substantially stronger overnight than daytime returns in their sample, including equity indexes and futures. Their abstract also discusses high opening prices and early-session reversals. This is a return-decomposition finding, not a guarantee that 90% of future index profits will occur overnight. Transaction costs, financing and closure gaps matter in our CFD transfer. [Original SSRN record](https://ssrn.com/abstract=1004081). The accessible abstract was checked; the complete original PDF could not be fetched here, so we do not claim a full-paper replication.

## Risk overlays are separate hypotheses

Moreira/Muir scale exposure using prior realized variance; that is not identical to sizing a trade by its stop distance. [Author manuscript](https://law.yale.edu/sites/default/files/area/workshop/leo/leo17_moreira.pdf). Harvey and coauthors examine volatility targeting across assets and find the Sharpe effects differ by asset class; improvement is not automatic. [Authors' institutional summary](https://www.man.com/insights/the-impact-of-volatility-targeting).

Our protected position size is floor($100 / loss per lot at initial hard stop), subject to broker limits. This is fixed stop-risk sizing, not a claimed replication of either volatility-targeting paper. Wider daily ATR reduces overnight lots; tighter M5 ATR can raise intraday turnover and cost sensitivity. Prop simulations add margin/headroom caps rather than assuming unlimited leverage.

## Corrections to the interview's stronger claims

- Passing one out-of-sample test does not establish that a model was never overfit. Repeated model selection and repeated use of the same latest year remain selection bias.
- Trade reshuffling changes path risk; it cannot by itself establish a genuine predictive edge. Resampling also assumes the source history is informative about the future.
- A 70% estimated win rate is not a promise of exactly 70 winners in the next 100 trades. Loss size, costs and clustered losses matter.
- SSRN includes working papers. Publication or peer review is evidence to evaluate, not a guarantee that a trading system will make money.
- The interview's institutional adoption percentages, individual earnings and universal profitability claims are not independently verified here and are not inputs to our models.

## Source-access limitations

SSRN's direct pages/PDF endpoint returned access errors for some requests. The VWAP author's public PDF and the intraday-momentum manuscript hosted publicly were accessible through web retrieval. A direct download of the latter was denied; no access control was bypassed. PEAD is based on the publisher abstract plus the user's supplied transcript; the older PEAD papers were identified but not fully read. No result is presented as a full replication of those papers.
