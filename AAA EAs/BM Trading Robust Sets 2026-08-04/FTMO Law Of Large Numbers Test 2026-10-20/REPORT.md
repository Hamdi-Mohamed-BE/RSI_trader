# Test of the claim "PF > 0.95 + many uncorrelated bets beats prop firms" (2026-10-20)

**Verdict: rejected, both mathematically and on our EAs.** The law of large numbers only works FOR you when the edge is real. With a profit factor at or below 1, more bets drag you toward the loss limit, not the target.

## Part A: pure maths (i.i.d. 1:1 bets, FTMO 2-step Swing $10k rules, 20,000 paths)

The simulation applies FTMO's targets (+10% then +5%) and loss limits (10% total, 5% daily), with 4 or more trading days per phase and about 6 months to finish. A 40-trading-day funded stage then pays 80% of profits, with the fee (assumed $170) refunded on the first payout.

| PF | Risk / bet | Bets / day | P(pass both ≤ ~6 months) | P(funded ≤ 90 days) | Median days to funded | P(fail evaluation) | P(funded then breached ≤40 d) | EV per attempt (fee $170, 40 funded days) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.90 | 0.25% | 3 | 0.0% | 0.0% | 173.6 | 22.5% | 0.0% | -170 $ |
| 0.90 | 0.25% | 10 | 0.2% | 0.0% | 117.6 | 87.5% | 0.0% | -170 $ |
| 0.90 | 0.5% | 3 | 1.8% | 0.4% | 127.4 | 68.7% | 0.3% | -167 $ |
| 0.90 | 0.5% | 10 | 3.6% | 2.8% | 56.0 | 95.9% | 2.6% | -165 $ |
| 0.90 | 1% | 3 | 12.7% | 9.8% | 60.2 | 86.4% | 7.6% | -132 $ |
| 0.90 | 1% | 10 | 7.3% | 7.3% | 21.0 | 92.7% | 7.3% | -167 $ |
| 0.90 | 2% | 3 | 11.1% | 11.1% | 21.0 | 88.9% | 11.0% | -163 $ |
| 0.90 | 2% | 10 | 10.8% | 10.8% | 18.2 | 89.2% | 10.8% | -170 $ |
| 0.95 | 0.25% | 3 | 0.1% | 0.0% | 162.4 | 10.1% | 0.0% | -170 $ |
| 0.95 | 0.25% | 10 | 1.5% | 0.3% | 130.2 | 59.9% | 0.2% | -168 $ |
| 0.95 | 0.5% | 3 | 5.5% | 1.1% | 127.4 | 50.6% | 0.4% | -156 $ |
| 0.95 | 0.5% | 10 | 11.8% | 8.1% | 68.6 | 86.1% | 6.8% | -139 $ |
| 0.95 | 1% | 3 | 20.8% | 15.6% | 61.6 | 77.7% | 10.7% | -88 $ |
| 0.95 | 1% | 10 | 11.3% | 11.2% | 21.0 | 88.7% | 11.2% | -161 $ |
| 0.95 | 2% | 3 | 14.3% | 14.3% | 19.6 | 85.7% | 14.3% | -158 $ |
| 0.95 | 2% | 10 | 14.2% | 14.2% | 18.2 | 85.8% | 14.2% | -170 $ |
| 1.00 | 0.25% | 3 | 0.2% | 0.0% | 169.4 | 4.3% | 0.0% | -170 $ |
| 1.00 | 0.25% | 10 | 9.3% | 1.5% | 135.8 | 28.6% | 0.5% | -142 $ |
| 1.00 | 0.5% | 3 | 12.3% | 2.5% | 127.4 | 34.8% | 0.9% | -132 $ |
| 1.00 | 0.5% | 10 | 30.2% | 20.1% | 71.4 | 66.0% | 11.4% | -27 $ |
| 1.00 | 1% | 3 | 32.2% | 23.9% | 63.0 | 65.9% | 13.5% | -7 $ |
| 1.00 | 1% | 10 | 17.1% | 17.1% | 21.0 | 83.0% | 16.9% | -148 $ |
| 1.00 | 2% | 3 | 17.7% | 17.7% | 21.0 | 82.3% | 17.6% | -149 $ |
| 1.00 | 2% | 10 | 17.9% | 17.9% | 18.2 | 82.0% | 17.9% | -170 $ |
| 1.05 | 0.25% | 3 | 0.8% | 0.0% | 166.6 | 1.6% | 0.0% | -168 $ |
| 1.05 | 0.25% | 10 | 30.9% | 5.1% | 131.6 | 10.1% | 0.5% | -38 $ |
| 1.05 | 0.5% | 3 | 23.9% | 4.6% | 127.4 | 21.4% | 1.0% | -76 $ |
| 1.05 | 0.5% | 10 | 55.5% | 38.5% | 68.6 | 41.3% | 13.3% | +227 $ |
| 1.05 | 1% | 3 | 44.8% | 33.7% | 61.6 | 53.2% | 15.3% | +118 $ |
| 1.05 | 1% | 10 | 24.5% | 24.5% | 21.0 | 75.5% | 24.2% | -117 $ |
| 1.05 | 2% | 3 | 21.3% | 21.3% | 21.0 | 78.7% | 21.2% | -134 $ |
| 1.05 | 2% | 10 | 21.1% | 21.1% | 18.2 | 78.9% | 21.1% | -169 $ |
| 1.20 | 0.25% | 3 | 13.2% | 0.1% | 161.0 | 0.0% | 0.0% | -117 $ |
| 1.20 | 0.25% | 10 | 96.5% | 47.1% | 91.0 | 0.1% | 0.0% | +688 $ |
| 1.20 | 0.5% | 3 | 69.8% | 20.6% | 113.4 | 3.6% | 0.5% | +272 $ |
| 1.20 | 0.5% | 10 | 94.2% | 87.8% | 46.2 | 5.7% | 4.5% | +1,321 $ |
| 1.20 | 1% | 3 | 75.8% | 63.7% | 53.2 | 23.7% | 11.9% | +665 $ |
| 1.20 | 1% | 10 | 47.3% | 47.3% | 21.0 | 52.7% | 44.4% | +153 $ |
| 1.20 | 2% | 3 | 33.4% | 33.4% | 19.6 | 66.6% | 32.8% | -51 $ |
| 1.20 | 2% | 10 | 32.6% | 32.6% | 18.2 | 67.4% | 32.6% | -159 $ |

- **PF 0.95:** the best pass-both rate is ~21%, and **the expected value is negative in every setting**. Spreading risk over more, smaller bets makes it worse: 0.25% × 10 bets/day passes in 1.5% of paths.
- **PF 1.00:** roughly break-even at best (−$7 per attempt).
- **PF 1.05:** first positive expected value (+$118 to +$227).
- **PF 1.20:** small risk with many bets passes 94–96% of the time, at +$688 to +$1,321 per attempt. This is where "many bets" actually helps.

## Part B: our EAs (26 EAs on XAUUSD / USTEC / USDJPY, modelled FTMO guard, dev / val / OOS starts)

Each EA's profit factor was measured on development trades only (2021-10 to 2023-10). The resulting baskets:
- **LLN_PF095:** the claim's rule, every EA with development PF above 0.95 (17 EAs).
- **LLN_ALL:** all 26 EAs.
- **EDGE_PF110:** a contrast basket, every EA with development PF above 1.10 (7 EAs).

| Basket | EAs | Cap | Pass ≤180 d dev / val / OOS (avg of 2 cost scenarios) | Funded ≤90 d dev / val / OOS | Median days to funded (OOS) | Trades /month (OOS) | Blocked entries / start (OOS) |
|---|---:|---:|---|---|---:|---:|---:|
| LLN_PF095 | 17 | $25 | 1% / 39% / 77% | 0% / 0% / 10% | 134 | 61.57 | 24.0 |
| LLN_PF095 | 17 | $50 | 23% / 54% / 87% | 14% / 17% / 53% | 79.0 | 55.24 | 33.5 |
| LLN_PF095 | 17 | $100 | 17% / 10% / 67% | 13% / 7% / 49% | 71 | 25.07 | 135.0 |
| LLN_PF095 | 17 | $150 | 13% / 3% / 56% | 8% / 0% / 47% | 52.5 | 14.89 | 223.5 |
| LLN_ALL | 26 | $25 | 3% / 11% / 99% | 2% / 0% / 21% | 118 | 82.87 | 71.5 |
| LLN_ALL | 26 | $50 | 12% / 47% / 97% | 9% / 7% / 57% | 75 | 71.52 | 88.5 |
| LLN_ALL | 26 | $100 | 14% / 62% / 73% | 12% / 33% / 56% | 65 | 39.08 | 237.5 |
| LLN_ALL | 26 | $150 | 1% / 27% / 50% | 1% / 23% / 42% | 49.0 | 14.35 | 382.5 |
| EDGE_PF110 | 7 | $25 | 0% / 0% / 0% | 0% / 0% / 0% | None | 13.87 | 9.0 |
| EDGE_PF110 | 7 | $50 | 0% / 17% / 0% | 0% / 0% / 0% | None | 16.83 | 11.0 |
| EDGE_PF110 | 7 | $100 | 49% / 94% / 40% | 0% / 5% / 8% | 148 | 17.39 | 17.0 |
| EDGE_PF110 | 7 | $150 | 23% / 30% / 57% | 5% / 14% / 3% | 144.0 | 10.99 | 48.5 |

Against the claim test declared in `PLAN.json`:
- **Pass rate at small caps:** LLN_PF095 at $25 / $50 passes only 1–23% in development, far from 70%.
- **Against Prop Ready 9 at $100:** LLN_PF095 loses in development (23% vs 58%) but wins in the bad 2023-24 validation year (54% vs 28%).
- **Conclusion: rejected.** Diversification softened the bad regime but did not create a pass-rate edge. The guard's 7-entries-per-day and open-risk caps also block much of the extra volume; see the blocked-entries column.
- **EDGE_PF110 is unstable:** 94% in validation but 40% in OOS at $100. A development PF filter did not persist.

### Development profit factors per EA

| EA | Source | Symbol | Dev trades | Dev PF (R) | In LLN_PF095 | In EDGE_PF110 |
|---|---|---|---:|---:|---|---|
| us100-selective-orb-v3 | ftmo | USTEC | 15 | 2.9778 | yes | yes |
| xau-squeeze-momentum-standard | ftmo | XAUUSD | 41 | 1.8423 | yes | yes |
| usdjpy-london-open-momentum | ftmo | USDJPY | 188 | 1.5281 | yes | yes |
| orb-volume-profile-volume-confirmed | full-eas | XAUUSD | 50 | 1.3704 | yes | yes |
| ema3 | ftmo | XAUUSD | 76 | 1.311 | yes | yes |
| orb-volume-profile | full-eas | XAUUSD | 134 | 1.125 | yes | yes |
| us100-orb-new-york-m30 | ftmo | USTEC | 18 | 1.1121 | yes | yes |
| xau-orb-new-york-m30 | ftmo | XAUUSD | 30 | 1.0991 | yes |  |
| sell-nasdaq-15min | full-eas | USTEC | 110 | 1.0836 | yes |  |
| nasdaq-5m-candle-momentum | ftmo | USTEC | 387 | 1.0574 | yes |  |
| xau-regime-switch | full-eas | XAUUSD | 91 | 1.0447 | yes |  |
| xau-elliott-wave-1-2-3 | full-eas | XAUUSD | 45 | 1.011 | yes |  |
| us100-month-end-flow | ftmo | USTEC | 71 | 0.9952 | yes |  |
| lta-volume-profile | full-eas | XAUUSD | 453 | 0.975 | yes |  |
| xau-rsi-vwap | ftmo | XAUUSD | 127 | 0.9676 | yes |  |
| xau-slow-trend | full-eas | XAUUSD | 413 | 0.9673 | yes |  |
| asia-breakout | full-eas | XAUUSD | 56 | 0.9651 | yes |  |
| gold-overnight-value-area | ftmo | XAUUSD | 426 | 0.9061 |  |  |
| us100-h1-orb-13utc | ftmo | USTEC | 106 | 0.899 |  |  |
| xau-trend-progression | ftmo | XAUUSD | 65 | 0.8895 |  |  |
| xau-weakness | full-eas | XAUUSD | 277 | 0.822 |  |  |
| nasdaq-overnight | ftmo | USTEC | 31 | 0.8128 |  |  |
| xau-orb-london-ny-overlap-m30 | ftmo | XAUUSD | 46 | 0.7848 |  |  |
| dmc-fresh-reaction-us100 | ftmo | USTEC | 36 | 0.7505 |  |  |
| dmc-fresh-reaction-xau | full-eas | XAUUSD | 32 | 0.6029 |  |  |
| dmc-current-xau | ftmo | XAUUSD | 95 | 0.5989 |  |  |

## What this does NOT prove

- **The maths assumes independent bets with fixed odds.** Real EAs are correlated and change with the market regime.
- **The EA results are previously inspected.** They are guard-model replays, not FTMO execution or forecasts.
- **The fee and payout model is a simple illustration.**

## Files

- [PLAN.json](PLAN.json), [theory.py](theory.py), [THEORY.json](THEORY.json).
- [prepare_universe.py](prepare_universe.py), [UNIVERSE.json](UNIVERSE.json), [run.py](run.py), [RESULTS.json](RESULTS.json), [FROZEN.json](FROZEN.json).
