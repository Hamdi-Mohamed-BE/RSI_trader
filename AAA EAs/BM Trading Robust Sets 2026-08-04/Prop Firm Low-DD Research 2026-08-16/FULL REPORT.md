# Prop-Firm Low-Drawdown Strategy Review — 2026-08-16

## Decision

There is no strategy that can guarantee a prop-firm pass or payout. The best currently deployable candidate from the existing MT5 evidence is a two-strategy XAUUSD portfolio:

1. **ORB Volume Profile EA — XAUUSD M5**
2. **AAA Final EMA3 EA — XAUUSD H4**

Use it only on an **FTMO Challenge: 2-Step Swing** account. The proposed evaluation risk is **0.50% per trade**, with **1.00% maximum total open risk**. Reduce to **0.35% per trade** after funding.

This recommendation optimizes survival and rule compatibility, not headline win rate. Its five-year win rate is 44.67%, but PF is 1.39 and the scaled realized drawdown is 4.98%. A superficially high win rate is not sufficient: the locally tested literal third-deviation VWAP system won 59.85% of trades but lost 75.20% with PF 0.57 after costs.

Do not buy a challenge solely from this report. First pass at least two FTMO Free Trials or complete 8–12 weeks of forward demo observation with the same symbol mapping, spread, clock, and risk limits.

## Why FTMO 2-Step Swing

- Phase targets: 10% and 5%.
- Maximum daily loss: 5% of initial simulated capital.
- Maximum total loss: static 10% of initial simulated capital.
- Minimum trading days: four in each evaluation phase.
- Trading period: unlimited.
- Base 2-Step reward share: 80%; up to 90% under the stated programmes.
- A reward can be requested on or after day 14 from the first funded-account trade, subject to profit, closed positions/orders, account review, and the agreement.
- Legitimate self-built EAs and algorithmic trading are allowed, subject to real-market behaviour and forbidden-practice rules.
- Swing is required because the H4 strategy may hold overnight or over weekends.

Official rules:

- https://ftmo.com/en/2-step-challenge/
- https://ftmo.com/au/comparison-table/
- https://ftmo.com/en/trading-objectives/
- https://ftmo.com/faq/ftmo-swing-account-type/
- https://ftmo.com/faq/which-instruments-can-i-trade-and-what-strategies-am-i-allowed-to-use/
- https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/
- https://ftmo.com/en/forbidden-trading-practices/

No prop firm or reward is guaranteed. FTMO accounts use simulated capital, and reward eligibility remains subject to the agreement and review.

## Strategy definitions

### 1. XAUUSD New York ORB with relative volume

- New York opening range: first 15 minutes from 09:30 America/New_York.
- Signal chart: M5.
- Opening-range tick volume must be at least 0.60 times its 20-session reference.
- Breakout-bar tick volume must be at least 0.80 times its 20-bar reference.
- Breakout candle body must be at least 55% of its range.
- Opening range must be between 0.20 and 1.20 times M15 ATR(14).
- Reward/risk target: 2.5R.
- Break even at 1R.
- Flat by 15:55 New York.
- Risk: 0.50% in evaluation, 0.35% when funded.

Important: the selected set uses broker tick-volume confirmation. Its visual profile levels are displayed, but POC, value-area, and LVN filters are disabled. It must not be described as exchange-volume or order-book validation.

### 2. XAUUSD H4 EMA/pivot trend breakout

- Trend filter: 200 EMA and positive/negative six-bar EMA slope.
- Long: completed H4 close above the previous five completed bars' high, above a rising EMA.
- Short: completed H4 close below the previous five completed bars' low, below a falling EMA.
- Stop: the opposite five-bar pivot extreme.
- Target: 1.7R.
- Trailing begins at 1.5R, with a 1R distance.
- Risk: 0.50% in evaluation, 0.35% when funded.

## Five-year MT5 evidence

Period: 2021-08-11 through 2026-08-10. Each source EA was tested standalone from USD 10,000 at approximately 1% risk using the existing MT5 every-tick reports.

| EA | Symbol / TF | Return | Max equity DD | PF | Win rate | Trades |
|---|---:|---:|---:|---:|---:|---:|
| ORB Volume Profile | XAUUSD M5 | +57.07% | 6.31% | 1.41 | 41.53% | 301 |
| AAA Final EMA3 | XAUUSD H4 | +32.10% | 8.70% | 1.36 | 49.73% | 187 |

### Combined, scaled to 0.50% per trade

| Measure | Result |
|---|---:|
| Starting balance | $10,000.00 |
| Final realized balance | $14,458.33 |
| Net return | +44.58% |
| CAGR | +7.66% |
| Combined PF | 1.39 |
| Combined win rate | 44.67% |
| Trades | 488 |
| Realized balance max DD | 4.98% |
| Conservative sum of scaled individual equity DDs | 7.50% |
| Worst historical realized day | -1.27% |

The combined curve is a chronological sum of the two MT5 deal streams. It is not a synchronized multi-EA MT5 equity backtest. The 4.98% figure is realized balance drawdown, while the conservative 7.50% figure sums the separately observed scaled equity drawdowns. Concurrent floating loss, symbol mapping, swaps, and portfolio-level margin can differ live.

## Latest complete year

Period: 2025-08-11 through 2026-08-10.

| EA at source 1% | Return | Max equity DD | PF | Win rate | Trades |
|---|---:|---:|---:|---:|---:|
| ORB Volume Profile | +9.70% | 6.29% | 1.67 | 42.86% | 49 |
| AAA Final EMA3 | +16.94% | 2.85% | 2.30 | 64.10% | 39 |

At 0.50% risk, the simple scaled sum is +13.32%, PF 1.97, win rate 52.27%, and 88 trades. The conservative sum of scaled individual equity drawdowns is 4.57%.

## Prop-rule simulation

Method: 20,000 paths, 20-trading-day block bootstrap of the combined five-year daily deal stream. Each path models FTMO phase 1 at +10%, phase 2 at +5%, a static -10% failure floor, a -5% daily limit, four trading days per phase, then a first funded reward after at least ten trading days and +2% funded profit. The first reward uses the base 80% split. The stress version cuts positive daily results by 10% and enlarges negative daily results by 10%.

These are conditional model estimates, not real probabilities or guarantees.

### 0.50% per trade

| Horizon | First reward — historical bootstrap | First reward — execution stress | Failed account — historical | Failed account — stress |
|---|---:|---:|---:|---:|
| 1 year | 10.66% | 2.93% | 0.26% | 2.04% |
| 2 years | 51.20% | 17.26% | 0.69% | 7.22% |
| 3 years | 78.77% | 33.77% | 1.13% | 12.21% |

- Median time to first reward among paths that achieved one: 429 trading days, approximately 20 months.
- Median first funded gross profit: 2.42%.
- Median reward at the 80% split: 1.93% of account size — approximately $1,933 on a $100,000 account, excluding the refundable challenge fee.

### Risk-speed trade-off

| Risk per EA | Five-year realized DD | Conservative scaled-equity DD sum | Nominal 2-year first reward | Stressed 2-year first reward | Stressed 3-year account failure |
|---|---:|---:|---:|---:|---:|
| 0.35% | 3.49% | 5.25% | 23.10% | 4.42% | 2.89% |
| **0.50%** | **4.98%** | **7.50%** | **51.20%** | **17.26%** | **12.21%** |
| 0.75% | 7.48% | 11.26% | 73.63% | 36.30% | 33.41% |

The 0.75% configuration is rejected: its conservative equity-DD estimate already exceeds the 10% FTMO floor, and the stress model has a one-in-three three-year failure rate. The 0.35% configuration is safer but probably too slow for most buyers. The 0.50% configuration is the compromise, not a guarantee.

## Mandatory portfolio guardrails

- Challenge risk: 0.50% per trade.
- Funded risk: 0.35% per trade.
- Maximum combined open stop risk: 1.00% during evaluation, 0.70% when funded.
- Internal daily equity stop: -1.50%; disable new entries until the next FTMO day.
- Internal weekly equity stop: -3.00%; disable until the next week.
- Internal total equity circuit breaker: -6.00% from initial balance; manual review before restarting.
- No martingale, grid, averaging down, recovery lot multiplier, or trades without a hard stop.
- No new strategy is enabled merely to satisfy a minimum trading day.
- Daily reset and internal limits must use FTMO's CE(S)T reset, including floating P/L, swaps, and commissions.

These limits require a portfolio-level risk controller. Independent EAs cannot safely enforce aggregate exposure by themselves.

## Explicit exclusions

- **Nasdaq Overnight:** profitable and higher-win, but its deliberate close-to-open entry can be interpreted as prohibited gap trading. Excluded to reduce reward-review risk even on Swing.
- **News Pulse:** the apparent five-year result contains only 19 recent event trades because the historical event schedule is incomplete; it is not valid five-year evidence.
- **ATR Candle Breakout:** profitable, but its source 1% run had 23.66% equity drawdown and a 23.43% win rate. It is not a low-DD/high-win candidate.
- **VWAP third-deviation mean reversion:** high headline win rate but negative expectancy after costs; rejected.
- **All grid and martingale-like EAs:** structurally unsuitable for a static prop-firm loss floor.

## Required gate before purchase

1. Add a portfolio-level equity/risk governor, without changing either entry strategy.
2. Run a synchronized MT5 test with both EAs, actual FTMO symbol specifications if obtainable, commissions, swaps, spread, random delay, and portfolio floating equity.
3. Run two FTMO Free Trials or 8–12 weeks on demo with zero rule breaches.
4. Buy one account only. Do not buy ten cloned accounts before the first reviewed reward is actually received.

The active installation BAT was not changed by this research.

