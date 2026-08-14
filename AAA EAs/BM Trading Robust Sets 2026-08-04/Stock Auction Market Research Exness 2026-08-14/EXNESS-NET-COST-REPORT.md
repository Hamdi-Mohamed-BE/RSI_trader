# Exness stock/index auction-market backtest

Generated 2026-08-14. This is a research backtest, not a profit forecast.

## Test design

- Broker/data: Exness `Exness-MT5Trial16`, Zero demo symbols.
- Instruments: US500 plus NVDA, AAPL, MSFT, AMZN, GOOGL, META, AVGO, AMD, INTC, TSLA and JPM.
- Data: broker M1 history from January 2022 through 14 August 2026.
- Direction: long only.
- Starting balance: USD 10,000.
- Risk: 1% of current balance per trade, compounding.
- Development: 2022-2024.
- Validation: 2025.
- Locked confirmation: 2026 data was not used to choose the setup.
- Profiles: broker tick activity, because real exchange volume is not present in these CFD files.
- Costs: recorded M1 entry spread, slippage equal to 25% of median spread at entry and exit, two-sided commission, and long financing.

## Net results after modeled costs

| Instrument | Trades | Win rate | PF | Net return | CAGR | Max DD | Locked 2026 trades | Locked 2026 PF | Locked 2026 return | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| SP500 / US500 | 38 | 50.00% | 2.02 | +22.83% | 4.56% | 5.38% | 3 | 0.00 | -3.26% | REJECT |
| NVDA | 31 | 41.94% | 2.52 | +23.92% | 4.76% | 4.71% | 2 | 296.79* | +2.97% | REJECT |
| AAPL | 25 | 32.00% | 1.90 | +15.40% | 3.16% | 8.02% | 4 | 0.89 | -0.41% | REJECT |
| MSFT | 16 | 56.25% | 3.50 | +19.89% | 4.01% | 2.47% | 1 | 0.00 | -1.04% | REJECT |
| AMZN | 23 | 56.52% | 3.22 | +23.90% | 4.76% | 2.87% | 1 | 0.00 | -1.02% | REJECT |
| GOOGL | 20 | 50.00% | 4.84 | +46.17% | 8.59% | 4.90% | 1 | 0.00 | -1.02% | REJECT |
| META | 35 | 51.43% | 2.82 | +38.58% | 7.33% | 5.13% | 3 | 5.88 | +4.95% | REJECT |
| AVGO | 24 | 25.00% | 2.51 | +16.38% | 3.35% | 7.70% | 3 | 3.00 | +2.10% | REJECT |
| AMD | 18 | 11.11% | 0.87 | -1.70% | -0.37% | 6.65% | 0 | 0.00 | 0.00% | REJECT |
| INTC | 24 | 54.17% | 4.73 | +28.81% | 5.64% | 5.42% | 3 | 2.97 | +1.99% | REJECT |
| TSLA | 37 | 10.81% | 1.94 | +20.82% | 4.19% | 10.69% | 12 | 0.00 | -8.81% | REJECT |
| JPM | 24 | 25.00% | 1.67 | +8.33% | 1.75% | 6.49% | 1 | 0.00 | -0.06% | REJECT |

\* NVDA's very high confirmation PF is not reliable: it comes from only two trades and one losing trade was nearly flat after management.

All setups fail the final gate. A PASS required positive locked confirmation with at least three trades, PF at least 1.05, drawdown below 15%, and at least 15% annualized return across the full period.

## Effect of all modeled costs

| Instrument | Before all costs | After recorded spread + slippage | Final after commission + swap | Total return reduction |
|---|---:|---:|---:|---:|
| SP500 | +36.30% | +32.06% | +22.83% | 13.47 points |
| NVDA | +37.18% | +29.52% | +23.92% | 13.26 points |
| AAPL | +20.51% | +18.28% | +15.40% | 5.11 points |
| MSFT | +24.82% | +21.12% | +19.89% | 4.93 points |
| AMZN | +27.73% | +25.57% | +23.90% | 3.82 points |
| GOOGL | +53.56% | +50.23% | +46.17% | 7.39 points |
| META | +48.67% | +42.12% | +38.58% | 10.09 points |
| AVGO | +22.92% | +20.01% | +16.38% | 6.54 points |
| AMD | +2.48% | +0.21% | -1.70% | 4.17 points |
| INTC | +37.64% | +31.41% | +28.81% | 8.83 points |
| TSLA | +23.56% | +22.41% | +20.82% | 2.73 points |
| JPM | +14.24% | +11.56% | +8.33% | 5.91 points |

## Exness versus MEXAtlantic net return

The two runs use the same research procedure, but optimize on each broker's own historical feed. Therefore this is a broker/data robustness comparison, not an identical-trade execution comparison.

| Instrument | Exness | MEXAtlantic | Exness minus MEXAtlantic |
|---|---:|---:|---:|
| SP500 | +22.83% | +27.43% | -4.59 points |
| NVDA | +23.92% | +21.11% | +2.81 points |
| AAPL | +15.40% | +17.38% | -1.98 points |
| MSFT | +19.89% | +13.73% | +6.16 points |
| AMZN | +23.90% | +13.52% | +10.39 points |
| GOOGL | +46.17% | +15.34% | +30.83 points |
| META | +38.58% | +30.07% | +8.51 points |
| AVGO | +16.38% | +16.57% | -0.19 points |
| AMD | -1.70% | +23.53% | -25.23 points |
| INTC | +28.81% | +32.86% | -4.05 points |
| TSLA | +20.82% | +46.99% | -26.17 points |
| JPM | +8.33% | +11.78% | -3.45 points |

The large GOOGL, AMD and TSLA differences are a warning that the selected setups are sensitive to broker data and/or the parameter-selection sample. This weakens the evidence for deployment.

## Cost-model limitations

- US500 Zero commission uses Exness's published exact USD 0.50 per lot per side.
- Each stock uses the published **from USD 0.50 per lot per side** as a lower-bound estimate because the account-specific instrument table was unavailable. Actual stock commission may be higher, so stock results may be optimistic.
- The terminal's 2026-08-14 long-swap snapshot was applied throughout the historical sample. Historical swap rates were unavailable and can change daily.
- Calendar holding days approximate daily rollover and Friday triple swap.
- Historical dividend adjustments were not available and were not modeled.
- The maximum-drawdown figure preserves the minute-marked strategy drawdown as a floor, but does not mark financing continuously inside an open trade.
- Tick volume is quote activity, not centralized exchange volume.

## Conclusion

Do not add these stock/index variants to the active BAT based on this test. META, AVGO and INTC are the only candidates with minimally positive locked confirmation, but each has too few 2026 trades and annualized return remains below the 15% requirement. A longer untouched forward test and exact live-account commission/swap records are required before reconsidering them.

## Official cost references

- Exness Zero account: https://get.exness.help/hc/en-us/articles/17537782878236-Zero-account
- Exness commissions: https://get.exness.help/hc/en-us/articles/360012007919-Are-trading-accounts-charged-a-commission-fee
- Exness stocks: https://get.exness.help/hc/en-us/articles/17854435814428-Stocks
- Exness indices: https://get.exness.help/hc/en-us/articles/17854383867548-Indices
