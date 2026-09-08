# Step 6 — Volatility Compression → Expansion

## Goal and outcome

Build a no-look-ahead compression-breakout EA and run the agreed pipeline on XAU, XAG, BTC, US30, US100 and GBPJPY at a fixed **1.00% current-equity risk per trade**. The six configurations were selected using the development and pre-lock validation windows, frozen, and only then read on the untouched year.

**Outcome: do not add this EA to the live/recommended system yet.** XAU is the only version worth forward-demo testing. BTC is a useful watch candidate but its three-year native evidence is not stable. The other four fail the promotion gate.

## Native MT5 results — decisive evidence

| Asset | Decision | Locked return | PF | Win rate | DD | Trades | Sharpe | Recovery | 3y return | 3y PF | 3y DD | 3y trades |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| XAUUSD | DEMO ONLY | +18.61% | 1.33 | 40.21% | 10.20% | 97 | 5.55 | 1.73 | +93.58% | 1.32 | 17.01% | 347 |
| XAGUSD | REJECT | +6.92% | 1.14 | 27.85% | 14.49% | 79 | 2.12 | 0.39 | +12.05% | 1.15 | 15.37% | 124 |
| BTCUSD | WATCH | +13.73% | 1.73 | 45.71% | 6.86% | 35 | 10.06 | 1.98 | +5.16% | 1.08 | 17.79% | 109 |
| US30 | WATCH | +1.83% | 1.14 | 52.38% | 5.21% | 21 | 2.31 | 0.34 | +10.76% | 1.27 | 5.88% | 65 |
| US100 | REJECT | +4.45% | 1.21 | 39.39% | 7.79% | 33 | 2.70 | 0.52 | +1.80% | 1.02 | 24.86% | 130 |
| GBPJPY | REJECT | -0.83% | 0.90 | 40.00% | 5.64% | 15 | -1.46 | -0.15 | -5.15% | 0.83 | 10.12% | 48 |

Locked year: 2025-09-01 to 2026-09-01. Three-year context: 2023-09-01 to 2026-09-01. Initial balance $10,000. Native MetaTrader 5, broker history, Every Tick model, recorded spread, 1% dynamic equity risk. Sharpe and recovery are MT5 report values. History quality is 98–100%.

### Decision notes

- **XAUUSD — DEMO ONLY:** Only asset with repeatable PF across both native horizons; 3-year DD still too high for live promotion.
- **XAGUSD — REJECT:** Native PF and drawdown fail the gate despite the proxy result.
- **BTCUSD — WATCH:** Excellent locked year, but 3-year PF is only 1.08 and DD is 17.79%; likely regime-dependent.
- **US30 — WATCH:** Low DD and positive 3-year result, but the locked PF/trade count are too weak.
- **US100 — REJECT:** Three-year PF is near breakeven with 24.86% DD.
- **GBPJPY — REJECT:** Negative locked and three-year native evidence.


## Frozen configuration per asset

| Asset | TF | Session | Compression | Range/arm | Confirm | Trend | Direction | Stop | RR | Management | Max bars |
|---|---|---|---|---|---|---|---|---|---|---|---|
| XAUUSD | M30 | asia | atr-ratio 0.8 | 12/12 | body | ema50-200 | long-only | atr 1.25 | 2.0R | none | 24 |
| XAGUSD | M30 | london | atr-ratio 0.65 | 12/6 | volume | ema50 | both | atr 1.25 | 6.0R | breakeven | 24 |
| BTCUSD | H1 | london-new-york | atr-ratio 0.5 | 6/3 | close | ema50-200 | both | atr 1.25 | 2.0R | none | 12 |
| US30 | H1 | new-york | atr-ratio 0.65 | 6/3 | close | ema50 | both | atr 1.25 | 2.0R | none | 6 |
| US100 | H1 | new-york | atr-ratio 0.65 | 12/6 | volume | ema50 | both | atr 1.25 | 2.0R | none | 48 |
| GBPJPY | M15 | london | bb-keltner 1.0 | 20/6 | volume | ema50-200 | both | atr 1.25 | 2.0R | none | 12 |

All session hours are UTC with automatic DST handling for London and New York. No locked-period values were used to select these configurations.

## Monte Carlo — locked native trades

| Asset | Profit chance | End P5 | End median | End P95 | Median DD | DD P95 |
|---|---|---|---|---|---|---|
| XAUUSD | 91.2% | -3.57% | +18.64% | +46.28% | 8.45% | 15.66% |
| XAGUSD | 66.1% | -15.62% | +6.30% | +37.80% | 11.77% | 21.59% |
| BTCUSD | 91.3% | -2.62% | +13.82% | +33.69% | 4.86% | 10.16% |
| US30 | 66.3% | -4.69% | +1.74% | +9.40% | 4.72% | 7.93% |
| US100 | 73.7% | -6.90% | +4.42% | +17.90% | 6.01% | 10.85% |
| GBPJPY | 44.1% | -8.33% | -0.83% | +7.04% | 4.69% | 9.67% |

Method: 10,000 stationary five-trade block-bootstrap paths per asset. This reshuffles actual locked-year native trade returns while retaining some local clustering. It estimates sequencing risk; it cannot forecast a new market regime.

## Management comparison before the lock was opened

| Asset | Management | Validation return | PF | Win rate | DD | Trades |
|---|---|---|---|---|---|---|
| XAUUSD | none | +37.91% | 1.46 | 45.05% | 10.28% | 111 |
| XAUUSD | breakeven | +26.69% | 1.38 | 38.39% | 11.12% | 112 |
| XAUUSD | atr-trail | +24.19% | 1.35 | 47.32% | 10.81% | 112 |
| XAUUSD | dynamic-m15-50-20 | +20.61% | 1.28 | 49.14% | 11.32% | 116 |
| XAGUSD | none | +6.47% | 1.45 | 27.78% | 5.46% | 18 |
| XAGUSD | breakeven | +5.99% | 1.49 | 22.22% | 5.48% | 18 |
| XAGUSD | atr-trail | +3.90% | 1.32 | 27.78% | 4.89% | 18 |
| XAGUSD | dynamic-m15-50-20 | +5.13% | 1.36 | 27.78% | 5.46% | 18 |
| BTCUSD | none | +12.30% | 2.54 | 52.63% | 3.83% | 19 |
| BTCUSD | breakeven | +10.10% | 2.26 | 47.37% | 3.41% | 19 |
| BTCUSD | atr-trail | +10.20% | 2.28 | 52.63% | 3.41% | 19 |
| BTCUSD | dynamic-m15-50-20 | +10.54% | 2.32 | 52.63% | 3.41% | 19 |
| US30 | none | +6.82% | 1.76 | 55.56% | 5.56% | 18 |
| US30 | breakeven | +6.82% | 1.76 | 55.56% | 5.56% | 18 |
| US30 | atr-trail | +6.82% | 1.76 | 55.56% | 5.56% | 18 |
| US30 | dynamic-m15-50-20 | +6.82% | 1.76 | 55.56% | 5.56% | 18 |
| US100 | none | +11.63% | 1.72 | 51.85% | 4.38% | 27 |
| US100 | breakeven | +9.00% | 1.57 | 42.86% | 4.76% | 28 |
| US100 | atr-trail | +9.65% | 1.61 | 53.57% | 4.38% | 28 |
| US100 | dynamic-m15-50-20 | +8.59% | 1.55 | 53.57% | 4.38% | 28 |
| GBPJPY | none | +5.51% | 1.15 | 38.71% | 12.79% | 62 |
| GBPJPY | breakeven | +3.08% | 1.08 | 35.48% | 12.79% | 62 |
| GBPJPY | atr-trail | +3.42% | 1.09 | 37.10% | 12.79% | 62 |
| GBPJPY | dynamic-m15-50-20 | +2.67% | 1.07 | 39.68% | 12.46% | 63 |

The “dynamic-m15-50-20” option moves the stop to +0.20R after a completed M15 candle has reached at least +0.50R. The optimizer was allowed to reject it. It did: no management was selected for XAU, BTC, US30, US100 and GBPJPY; XAG selected simple break-even. This is important evidence that trailing logic can reduce this system's expectancy.

## Best three RR candidates in pre-lock research

| Asset | RR | Train return | Train PF | Validation return | Validation PF | Validation DD | Validation trades |
|---|---|---|---|---|---|---|---|
| XAUUSD | 2.0R | +36.56% | 1.50 | +37.91% | 1.46 | 10.28% | 111 |
| XAUUSD | 2.5R | +25.09% | 1.33 | +35.97% | 1.43 | 11.76% | 104 |
| XAUUSD | 1.5R | +32.79% | 1.46 | +18.11% | 1.23 | 11.12% | 121 |
| XAGUSD | 6.0R | +11.12% | 1.48 | +6.47% | 1.45 | 5.46% | 18 |
| XAGUSD | 4.0R | +5.18% | 1.23 | +5.83% | 1.41 | 5.46% | 18 |
| XAGUSD | 2.0R | +7.39% | 1.38 | +1.94% | 1.17 | 4.86% | 18 |
| BTCUSD | 2.0R | +8.16% | 1.92 | +12.30% | 2.54 | 3.83% | 19 |
| BTCUSD | 1.5R | +4.68% | 1.53 | +8.50% | 2.07 | 3.36% | 20 |
| BTCUSD | 1.0R | +3.58% | 1.41 | +3.77% | 1.48 | 4.40% | 21 |
| US30 | 2.0R | +11.34% | 2.21 | +6.82% | 1.76 | 5.56% | 18 |
| US30 | 1.5R | +7.92% | 1.88 | +4.34% | 1.49 | 5.21% | 18 |
| US30 | 3.0R | +10.17% | 1.96 | +3.75% | 1.38 | 5.56% | 18 |
| US100 | 2.0R | +16.71% | 1.59 | +11.63% | 1.72 | 4.38% | 27 |
| US100 | 6.0R | +19.13% | 1.49 | +13.03% | 1.58 | 10.66% | 25 |
| US100 | 4.0R | +16.18% | 1.45 | +8.81% | 1.45 | 7.11% | 25 |
| GBPJPY | 2.0R | +5.37% | 1.13 | +5.51% | 1.15 | 12.79% | 62 |
| GBPJPY | 1.5R | +2.00% | 1.05 | +0.48% | 1.01 | 14.61% | 62 |
| GBPJPY | 2.5R | -0.21% | 0.99 | -2.23% | 0.94 | 14.12% | 62 |

RR was searched from 0.5R through 6R. The table is a staged, pre-lock sensitivity view around the then-current candidate—not a second optimization on the untouched year.

## Proxy-to-native reality check

| Asset | Proxy locked return | Proxy PF | Proxy trades | Native locked return | Native PF | Native trades |
|---|---|---|---|---|---|---|
| XAUUSD | +11.05% | 1.23 | 76 | +18.61% | 1.33 | 97 |
| XAGUSD | +9.28% | 1.37 | 38 | +6.92% | 1.14 | 79 |
| BTCUSD | +9.72% | 1.78 | 24 | +13.73% | 1.73 | 35 |
| US30 | -2.12% | 0.78 | 18 | +1.83% | 1.14 | 21 |
| US100 | +9.61% | 1.52 | 29 | +4.45% | 1.21 | 33 |
| GBPJPY | -2.38% | 0.83 | 21 | -0.83% | 0.90 | 15 |

The proxy was used only to screen configurations quickly. Native execution is authoritative. The large XAG divergence is the clearest warning against publishing proxy-only statistics.

## Pipeline completed

- Five signal timeframes: M5, M15, M30, H1 and H4.
- Six session modes: all day, Asia, London, New York, London–New York overlap, and London-or-New-York.
- Four compression definitions: ATR contraction, Bollinger bandwidth percentile, narrow range and Bollinger-inside-Keltner approximation.
- Confirmation, trend, direction, stop placement, holding time, RR 0.5R–6R, break-even, ATR trail and Dynamic M15 50–20 management.
- Development year, separate validation year, untouched locked year and exact three-year native MT5 context.
- Rolling six-month proxy stability and 10,000-path native Monte Carlo.
- Compilation: **0 errors, 0 warnings**. Native trade ledger reconciles to each MT5 report.

## Honest recommendation

1. **XAU:** forward-demo only for at least 8–12 weeks and 30+ new trades. Keep risk at 1% only in demo; its 17.01% three-year DD is too high for immediate real/prop deployment.
2. **BTC:** keep as research/watch, not portfolio. Recent PF 1.73 is attractive, but three-year PF 1.08 shows regime dependence.
3. **US30:** archive as an alternate research preset. It has controlled DD, but only 21 locked trades and PF 1.14.
4. **XAG, US100 and GBPJPY:** reject this strategy/configuration.

No BAT, recommended portfolio, website catalogue, cache or live MT5 profile was changed. The EA remains tester-only until you review and explicitly choose a next action.

## Research rationale

Compression-breakout logic is a testable volatility-scaling hypothesis rather than a guaranteed edge. The build used volatility-normalized thresholds because price changes show non-trivial scaling behaviour, Bollinger bandwidth as a standard relative-volatility measure, and session filters because intraday continuation/predictability varies across the day. These ideas justified the search space; they did not determine the verdict—the native locked evidence did.
