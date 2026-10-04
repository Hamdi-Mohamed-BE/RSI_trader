# Gold candle lifecycle — raw one-year test

Verdict: none of the three literal raw versions was profitable after costs. H4 was nearly flat, but its floating-equity drawdown was large. This tests the frozen interpretation, not an exact undisclosed video strategy.

Period: 3 Oct 2025–2 Oct 2026 inclusive. XAUUSD Exness MT5 broker-server candles, 10000 USD separate accounts, 1% equity-risk TARGET, lots rounded up/minimum lot. Actual planned risk can exceed the target. Native Model 4, 150ms delay, broker spread/commission/swap. 75% real-tick coverage; real ticks start 1 Jan 2026.

## Exact implementation

Bearish only: previous parent candle red; new candle trades at least one tick above its open in first half; a completed M1 candle in second half closes below that open, current bid also below. Sell once. Stop above the maximum high KNOWN at entry plus current spread and two ticks, widened for broker rules. No TP/trailing; exit on first tradable quote at/after parent-end. These entry-confirmation/stop/exit details are our assumptions. No future final high or final close was used to enter.

Control: sell after previous red at first completed M1 in second half, without first-half-up / bearish-flip filters; same sizing, observed-high stop and time exit. It is not matched random.

## Native results

| Timeframe | Version | Net return | Net PF | Win rate | Equity DD | Trades | /month | /weekday | W / L streak | Sharpe¹ |
|---|---|---|---|---|---|---|---|---|---|---|
| H1 | Video interpretation | -18.70% | 0.970 | 45.5% | 52.95% | 1994 | 166.28 | 7.640 | 9 / 12 | -0.17 |
| H1 | Control | -107.20% | 0.750 | 34.0% | 106.99% | 1740 | 145.10 | 6.667 | 5 / 12 | -1.68 |
| H4 | Video interpretation | -0.27% | 0.999 | 40.0% | 26.75% | 517 | 43.11 | 1.981 | 7 / 11 | 0.11 |
| H4 | Control | 103.91% | 1.148 | 34.0% | 35.53% | 709 | 59.12 | 2.716 | 6 / 12 | 1.42 |
| D1 | Video interpretation | -6.43% | 0.849 | 48.3% | 9.05% | 89 | 7.42 | 0.341 | 7 / 6 | -0.56 |
| D1 | Control | -19.66% | 0.730 | 36.2% | 23.21% | 127 | 10.59 | 0.487 | 4 / 10 | -1.37 |

## Candle claims (descriptive, not entry rules)

| TF | Candles² | Previous-red sample | Next red after red | High first half after red | High near midpoint³ | Final-red high first half⁴ |
|---|---|---|---|---|---|---|
| H1 | 5903 | 2919 | 49.4% | 53.7% | 13.2% | 85.1% |
| H4 | 1486 | 715 | 49.2% | 53.0% | 15.6% | 81.4% |
| D1 | 258 | 127 | 48.8% | 45.7% | 16.7% | 75.4% |

Previous-red continuation was about 49%, with bootstrap intervals covering no improvement over other prior candles. A high in the first half was only about 53–54% on H1/H4 and 45% on D1 overall. Highs specifically near halfway were uncommon. The much higher first-half-high rate among candles that FINALLY close red (75–85%) is retrospective conditioning: final colour was unknown at entry.

² Timing diagnostics require quotes in BOTH halves and a prior native candle; exclude truncated session/Sunday candles. Native trading uses the real broker series; its prior D1 may be a short Sunday candle. No New York day anchoring assumed.
³ High timestamp between 40% and 60% of nominal candle duration, not a traded filter.
⁴ Conditioned on future final colour for descriptive analysis only. Tied extrema first/last occurrence tested separately; M1 resolution, not exact tick times.

## Execution limitations

H1 time closes repeatedly encountered historical broker market-closed states (10018); rejected entries were not counted as trades, and exits retried at subsequent quotes. Invalid stops (10016) and insufficient margin (10019) are reported as MISSED entries, never repaired into successful fills. Initial verifier-only classification amendments and original failed-validation logs are retained; strategy source and parameters never changed.

H1 control finished with negative simulated capital (−107.20% return). That is a failed risk scenario in the MT5 simulation, not an investable strategy or a claim about broker negative-balance protection. Broker minimum lots and gap/quote execution can violate the nominal 1% target.

| TF / version | Entry attempts | Fills | Market-closed entries | Invalid-stop entries | No-margin entries | Close retries (closed) | Late exits >60s | Max delay hours | Max planned risk / target |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| H1-model | 2007 | 1994 | 13 | 0 | 0 | 113708 | 71 | 50.12 | 1.98× |
| H1-control | 1771 | 1740 | 25 | 6 | 0 | 119778 | 45 | 50.12 | 11.75× |
| H4-model | 517 | 517 | 0 | 0 | 0 | 0 | 0 | 0.00 | 1.82× |
| H4-control | 715 | 709 | 0 | 5 | 1 | 0 | 1 | 27.18 | 1.89× |
| D1-model | 89 | 89 | 0 | 0 | 0 | 0 | 10 | 47.12 | 3.36× |
| D1-control | 127 | 127 | 0 | 0 | 0 | 0 | 9 | 47.03 | 3.75× |

¹ Calendar-day closed-balance return Sharpe, zero risk-free rate, includes zero days; not floating-equity Sharpe. Control Sharpe is not meaningful as a viable performance measure after capital failure.

Independent verification: 5273 entry attempts and 5223 fills (including smoke) reconstructed from native M1 and parent data. All source and binary hashes unchanged. Native parent OHLC matches M1 aggregation; no future price leakage. Six unique raw strategy/timeframe configurations; two identical-input H1 reruns after verifier-only corrections, plus one technical smoke test and no-order exporter.

No optimisation, no live/BAT changes, no FTMO promotion, no full 3-/5-year pipeline gate. This is one-year exploratory evidence, not proof of future results.