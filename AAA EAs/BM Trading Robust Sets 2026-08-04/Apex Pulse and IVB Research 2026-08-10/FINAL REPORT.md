# Apex Pulse and IVB EA research report

Date completed: 2026-08-10

## Final decision

| EA | Best market / chart | Complete Exness return | Complete PF | Max equity DD | Untouched 2025-2026 | Portfolio decision |
|---|---|---:|---:|---:|---:|---|
| Apex Pulse transparent model | EURUSD M1 | +25.60% total | 1.06 | 19.01% | -10.49%, PF 0.90 | **REJECT** |
| IVB Fixed-Range Volume Profile | US30 M1 | +5.65% total | 1.11 | 11.71% | +6.15%, PF 1.34 | **REJECT** |

Neither EA passed the existing requirement of approximately 20% or more per year together with a positive, credible holdout. Both compiled EAs are saved with trading disabled by default. Neither was added to `INSTALL AND RUN ON ACTIVE MT5.bat`.

## Test design

- Initial balance: USD 10,000.
- Risk: 1% of current equity per trade.
- Research selection: 2022-2023 training plus 2024 validation.
- Untouched holdout: 2025-01-01 through 2026-08-09.
- Complete replay: 2022-01-01 through 2026-08-09.
- Research feed: MEXAtlantic M1 bars with observed spread.
- Independent implementation replay: native MetaTrader 5 Strategy Tester on Exness-MT5Trial16, random execution delay, broker spread and contract specifications.
- Ambiguous same-minute research exits were treated conservatively, with the stop assumed first.

The IVB profile uses broker quote-tick activity because these CFD feeds contain no centralized exchange volume. POC, VAH and VAL follow the standard 70% value-area construction described in [TradingView's volume-profile documentation](https://www.tradingview.com/support/solutions/43000502040-volume-profile-indicators-basic-concepts/).

## Best Apex Pulse configuration

| Parameter | Selected value |
|---|---:|
| Symbol / chart | EURUSD M1 |
| Asia range | 00:00-07:00 Europe/London |
| Entry window | 08:00-12:00 America/New_York |
| Allowed Asia range | 15-40 pips |
| Breakout buffer | 0 pips |
| Stop | 1.0 x Asia range |
| Target | 2R |
| Management | Break-even at 1R |
| Direction / frequency | Long and short; one trade per day |
| Risk | 1% current equity |

### Apex results

| Data / period | Trades | Return | PF | Win rate | Max equity DD |
|---|---:|---:|---:|---:|---:|
| Research training, 2022-2023 | 400 | +22.01% | 1.13 | 39.50% | 14.23% closed-balance DD |
| Research validation, 2024 | 132 | +5.24% | 1.12 | 41.67% | 10.50% closed-balance DD |
| Research untouched, 2025-2026 | 280 | -21.43% | 0.81 | 39.29% | 27.07% closed-balance DD |
| Exness complete, 2022-2026 | 809 | +25.60% | 1.06 | 46.35% | 19.01% |
| Exness untouched, 2025-2026 | 281 | -10.49% | 0.90 | 46.62% | 18.87% |

The broker-native complete return looks positive only because earlier years mask the recent failure. The negative untouched period is the decisive rejection.

## Best IVB configuration

| Parameter | Selected value |
|---|---:|
| Symbol / chart | US30 M1 |
| Session | New York cash open, 09:30 America/New_York |
| Opening range | 30 minutes |
| Profile | 24 bins, 70% value area |
| Breakout filter | Relative tick volume >= 1.10 x prior 20-bar mean |
| Acceptance | One M1 close beyond opening range |
| Reload | Pullback/rejection at VAH within six M1 bars |
| Retest tolerance | 2% of opening-range width |
| Stop | Signal candle plus 5% of opening-range width |
| Target | 3R |
| Management | No break-even, trailing stop, or no-progress timeout |
| Hard exit | 16:00 America/New_York |
| Direction / frequency | Long and short; one trade per day |
| Risk | 1% current equity |

### IVB results

| Data / period | Trades | Return | PF | Win rate | Max equity DD |
|---|---:|---:|---:|---:|---:|
| Research training, 2022-2023 | 30 | +18.98% | 2.00 | 40.00% | 4.96% closed-balance DD |
| Research validation, 2024 | 17 | +6.91% | 1.64 | 35.29% | 4.90% closed-balance DD |
| Research untouched, 2025-2026 | 25 | +13.06% | 1.85 | 40.00% | 6.09% closed-balance DD |
| Exness complete, 2022-2026 | 67 | +5.65% | 1.11 | 28.36% | 11.71% |
| Exness untouched, 2025-2026 | 25 | +6.15% | 1.34 | 32.00% | 7.08% |

The large drop from the MEXAtlantic research feed to the Exness replay shows material broker/feed sensitivity. Although its untouched Exness sample stayed positive, the complete result is far below the portfolio threshold and the sample contains only 67 trades.

## Native MT5 detail

### Apex complete

- Final balance: USD 12,559.67.
- Gross profit / loss: USD 42,704.47 / -USD 40,144.80.
- Largest win / loss: USD 279.36 / -USD 144.30.
- Average win / loss: USD 113.88 / -USD 90.01.
- Balance max DD: 18.52%; equity max DD: 19.01%.
- History quality: 100%.

### IVB complete

- Final balance: USD 10,565.16.
- Gross profit / loss: USD 5,815.07 / -USD 5,249.91.
- Largest win / loss: USD 327.18 / -USD 119.88.
- Average win / loss: USD 306.06 / -USD 105.79.
- Balance max DD: 11.19%; equity max DD: 11.71%.
- History quality: 98%.

## Saved evidence

- `Native MT5 Exness Reports/apex-full.htm` and `apex-holdout.htm` are the full native Apex reports.
- `Native MT5 Exness Reports/ivb-us30-full.htm` and `ivb-us30-holdout.htm` are the full native IVB reports.
- The matching `.png` files are the MT5 balance/equity graphs.
- Research rankings, selected trades, yearly metrics, data manifests and independent research graphs remain in the `Apex Pulse EURUSD` and `IVB FRVP` folders.
