# Global Macro Auction-Market Strategy — Validation Report

Completed: 2026-08-14  
Source: supplied 1h44m transcript  
Starting balance: USD 10,000 per market  
Risk: 1.00% of current balance per trade  
History: January 2022 through 7–10 August 2026, depending on market

## Research verdict and user deployment decision

**Research verdict: none of the six markets passed the original 15% CAGR deployment gate.**

**Deployment status: on 2026-08-14 the user explicitly approved all six research variants. They are now enabled in the active BAT at 1% equity risk per trade per chart.** This approval changes the installation decision, not the historical statistics or research verdict.

The video presents a credible discretionary trading framework, not a complete mechanical strategy. Its technical value-area layer showed promising behavior on XAG and ETH, but no market met the original deployment requirement of at least 15% CAGR plus positive locked-2026 confirmation.

If all six Auction Market charts stop out concurrently, their planned combined loss is approximately 6% of current equity before gaps and slippage. Existing BAT EAs can add further simultaneous exposure; there is no portfolio-level drawdown governor in this EA.

- XAG came closest: 14.33% CAGR, 2.74 PF, 9.25% maximum equity drawdown, and positive but weak 2026 confirmation.
- ETH had the strongest 2026 result: +19.04%, 7.10 PF, and 5.83% drawdown, but this was only six trades. Its full CAGR was 11.55% and 2024 lost 5.03%.
- US100 failed badly in locked 2026: -10.89%, 0.19 PF, and 14 losing trades out of 15.
- XAU's attractive 3.78 full PF came from only 25 trades; 2026 supplied one nearly-flat losing trade.

These remain user-approved research presets rather than independently validated production presets.

## What the video actually teaches

The process has four layers:

1. Form a discretionary macro scenario using inflation, growth, unemployment, central-bank policy, rates, and risk appetite.
2. Select markets through intermarket capital flows.
3. Assess participation using CFTC Commitments of Traders data, volume, and VIX for equities.
4. Time a trade with auction-market/value-area structure.

Two technical entries are stated:

- **Failed auction / break-in:** price moves beyond VAL or VAH, then an H4 or daily candle closes back inside value. Target at least the opposite side of value.
- **Breakout/retest:** price closes outside value, retests the broken edge, and continues in the direction of migrating value.

For US equity indices, the video prefers long-only entries. For range-bound markets, it uses mean reversion; when fair value is migrating and the macro thesis agrees, it uses trend following.

## What was objectively tested

The backtest encoded only the reproducible technical layer:

- 64-row composite volume profiles built from prior M1 bars only.
- 70% value area, with POC, VAH, and VAL.
- H4 and daily confirmation.
- 10-, 20-, 40-, and 80-trading-day composite profiles.
- Value migration measured over five or ten trading days.
- Migrating-value and balanced-value regimes.
- Failed-auction and breakout/retest entries.
- US30 and US100 long only; both directions on XAU, XAG, BTC, and ETH.
- Failed-auction target at the opposite value-area edge, as stated in the video.
- Breakout targets of 1.5R, 2R, or 3R.
- Candle-extreme stops with 0, 0.10, or 0.25 ATR buffers.
- 72-, 168-, and 336-hour maximum holding windows.
- Fixed stops versus break-even after +1R.

The macro thesis, intermarket market selection, COT interpretation, and VIX context were **not** encoded because the video gives no objective numerical rules for them. Therefore these results validate the technical execution layer, not the full discretionary method.

## Honest results

| Market | Selected model | TF | Trades | Win rate | PF | Total return | CAGR | Max equity DD | 2026 trades | 2026 PF | 2026 return | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| XAU | Breakout/retest | D1 | 25 | 56.00% | 3.78 | +24.67% | +4.92% | 3.57% | 1 | 0.00 | -0.00% | Reject: no meaningful confirmation sample |
| XAG | Failed auction | H4 | 78 | 28.21% | 2.74 | +85.20% | +14.33% | 9.25% | 9 | 1.36 | +1.66% | Reject: CAGR below 15% |
| US30 | Failed auction, long only | H4 | 30 | 23.33% | 2.59 | +38.36% | +7.32% | 8.42% | 6 | 1.56 | +2.53% | Reject: CAGR below 15% |
| US100 | Failed auction, long only | H4 | 43 | 23.26% | 2.23 | +44.45% | +8.33% | 14.75% | 15 | 0.19 | -10.89% | Reject: failed confirmation |
| BTC | Failed auction | H4 | 66 | 28.79% | 1.81 | +42.87% | +8.07% | 13.12% | 13 | 1.27 | +2.40% | Reject: CAGR below 15% |
| ETH | Failed auction | H4 | 68 | 23.53% | 2.09 | +65.40% | +11.55% | 14.70% | 6 | 7.10 | +19.04% | Reject: CAGR and sample size |

Total return is the compounded result over the full available period, not a one-year return.

## Development, validation, and locked confirmation

| Market | 2022–2024 return / PF | 2025 return / PF | 2026 return / PF |
|---|---:|---:|---:|
| XAU | +15.34% / 4.56 | +8.09% / 2.99 | -0.00% / 0.00 |
| XAG | +56.35% / 2.95 | +16.52% / 2.97 | +1.66% / 1.36 |
| US30 | +10.10% / 1.94 | +22.56% / 4.35 | +2.53% / 1.56 |
| US100 | +33.54% / 2.86 | +21.39% / 11.16 | -10.89% / 0.19 |
| BTC | +21.92% / 1.87 | +13.28% / 2.02 | +2.40% / 1.27 |
| ETH | +29.76% / 1.86 | +7.07% / 1.59 | +19.04% / 7.10 |

Parameters were developed on 2022–2024, ranked with 2025 validation, then frozen before 2026 was examined. The US100 collapse shows why the locked period matters.

## Selected research configurations

| Market | Profile | Regime | Entry detail | Stop / target | Max hold | Management |
|---|---|---|---|---|---:|---|
| XAU D1 | 80 days | Balanced over 5 days, ≤0.50 ATR POC shift | Breakout/retest within 6 bars, 0.10 ATR tolerance | 0.10 ATR buffer / 3R | 168h | Break-even at +1R |
| XAG H4 | 80 days | Balanced over 10 days, ≤0.25 ATR shift | Failed auction, close 0.10 ATR inside | Candle extreme / opposite edge; minimum 1.5R | 168h | Break-even at +1R |
| US30 H4 | 80 days | Balanced over 5 days, ≤0.50 ATR shift | Long-only failed auction | Candle extreme / opposite edge; minimum 1.5R | 336h | Fixed |
| US100 H4 | 40 days | Migrating over 5 days | Long-only failed auction | Candle extreme / opposite edge; minimum 1.5R | 168h | Fixed |
| BTC H4 | 40 days | Migrating over 5 days | Failed auction | 0.10 ATR buffer / opposite edge; minimum 1R | 336h | Fixed |
| ETH H4 | 80 days | Balanced over 5 days, ≤0.50 ATR shift | Failed auction | Candle extreme / opposite edge; minimum 1R | 336h | Fixed |

## Execution assumptions

- MEXAtlantic-Demo M1 broker history was used.
- Recorded spread plus an additional 25% of median spread was charged as slippage on every fill.
- If stop and target could both occur in the same M1 bar, the stop was assumed first.
- Drawdown includes minute-level marked-to-market equity, not only closed trades.
- Only one position per market could be active at a time.
- Risk compounded at 1% of current equity.
- Profile values for a day used only completed prior days, preventing future leakage.

## Volume and COT limitations

The broker histories have zero centralized real volume. Profiles therefore use quote-tick activity distributed through each M1 candle's price rows. TradingView documents that volume profiles are built from lower-timeframe data and that index, forex, and crypto-CFD profiles may use tick volume:

https://www.tradingview.com/support/solutions/43000502040-volume-profile-indicators-basic-concepts/

CFTC states that COT data represents Tuesday open interest, is generally released Friday, and trader classifications reflect reported business purpose. It also says it does not know why traders hold their positions. Therefore the video's shorthand that non-commercial positions are automatically “smart money” is not sufficient as a mechanical signal:

https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm

## Files

- `backtest_auction_market.py` — reproducible research code.
- `EA/Auction Market Value Area EA.mq5` — MT5 source code.
- `EA/Auction Market Value Area EA.ex5` — compiled EA; zero compiler errors and zero warnings.
- `Presets/ACTIVE USER APPROVED - *.set` — six enabled 1% presets used by the BAT installer.
- `Results/summary.csv` — one-row-per-market summary.
- `Results/all-results.json` — full settings, splits, and yearly metrics.
- `Results/*-development-screen.csv` — all finalist execution screens.
- `Results/*-selected-trades.csv` — every selected-model trade.
- `Results/all-markets-equity.png` — six-market equity chart.
- `Results/*-equity.png` — individual equity charts.

## Next valid research step

Do not optimize the price rules further against 2026. A genuinely new test would need a predeclared macro/COT filter using point-in-time release dates—for example, COT data lagged until Friday publication plus explicit rate/inflation/risk-regime rules—and then a new untouched forward period. Without that, extra tuning would be data mining rather than validation.
