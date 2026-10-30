# US100 CRT three-candle setup: raw test (2026-10-29), REJECTED at the raw gate

**What was tested:** the pasted "Nitro Trades" CRT / candle range theory setup, as mechanical rules frozen in `RULES.md` before testing.
- **Setup:** C2 sweeps C1's low or high and closes back inside.
- **Entry:** C3 breaks C2's high or low (direct break or rebreak).
- **Exit:** TP at C1's opposite extreme, stop for 1.5R.
- **Session:** New York 09:30–12:00 ET, first trigger of the day.
- **Bias:** a declared rule for the H1 sweep / break bias.

**Test setup:** USTEC (Exness US100 CFD), M1 chart, M15 / M30 / H1 setups, **native MT5 Model 4**, 150 ms delay, $10,000, 1% equity risk per trade. The period is 2021-10-27 → 2026-10-27, split by trade entry date:
- development 2021-23;
- validation 2023-24;
- **out-of-sample: the last two years, 2024-26.**

Tables: `RESULTS.md`. Raw data: `RESULTS.json`. Chart: `balance.png`. Runs and journals: `native/`.

## Results (Model 4)
| Version | Part | Trades (/month, /day) | Win % | PF | Return | Closed DD |
|---|---|---:|---:|---:|---:|---:|
| **MAIN**: first of M15 / M30 / H1, rebreak, H1 bias (the clip's "best") | Development 2021-23 | 339 (14.1, 0.65) | 36.0 | 0.70 | −53.6% | 55.2% |
| | Validation 2023-24 | 155 (12.9, 0.59) | 37.4 | 0.70 | −26.2% | 29.7% |
| | **OOS 2024-26** | 349 (14.6, 0.67) | 45.3 | **1.03** | **+6.3%** | 17.7% |
| | Last 12 months | 171 (14.3, 0.66) | 46.2 | 1.06 | +6.8% | 14.3% |
| | All 5 years | 843 (14.1, 0.65) | 40.1 | 0.78 | **−63.6%** | 69.2% |
| **SIMPLE**: first TF, direct break, no bias (the clip's "easy" version) | Development / Validation / OOS | 498 / 244 / 492 | 39.6 / 38.9 / 43.7 | 0.78 / 0.76 / 0.93 | −48.8% / −31.3% / −21.9% | |
| | All 5 years | 1,234 (20.6, 0.95) | 41.1 | 0.81 | **−72.5%** | 72.5% |
| M15 only (rebreak, bias) | Development / Validation / OOS | 261 / 122 / 272 | | 0.81 / 0.61 / 1.06 | −29.3% / −29.3% / +9.1% | 5y −45.4% |
| M30 only | Development / Validation / OOS | 124 / 52 / 130 | | 0.70 / 0.87 / 1.15 | −23.6% / −4.0% / +12.2% | 5y −17.7% |
| H1 only | Development / Validation / OOS | 68 / 37 / 77 | | 0.48 / 0.63 / 1.01 | −24.7% / −9.0% / +0.6% | 5y −31.1% |
| Random direction RND1–3 (MAIN entries) | All 5 years | about 840 each | 34–38 | 0.57 / 0.63 / 0.74 | −75% to −88% | |

**Native Model 4 windows for MAIN:**
- 6m: −4.8%, PF 0.92.
- 1y: +6.8%, PF 1.06.
- 3y: −21.6%, PF 0.92.
- 5y: −63.6%, PF 0.79.
- Equity DD (MT5 "relative"): 14.8% / 14.8% / 32.4% / 69.2%.

## Raw gate: **FAIL for all five Model 4 versions**
- **3y and 5y returns:** negative for every version except M30 on 3y (+7.7%, PF 1.07, still below 1.15).
- **PF:** below 1.15 everywhere.
- **Random-direction control:** every version does beat it. The direction choice carries some information (MAIN PF 0.78 vs control 0.65), but it is not enough to cover costs and the structure.
- **Best-day test:** not applicable, because the totals are negative.

## Why it fails
- **Win rate:** **40% realised vs the claimed 70–80%**, against the ~40% needed to break even at 1.5R (a realised ~1.45R after spread).
- **Costs on tight setups:** many setups are very tight (median stop about 15 points), so the spread and the 150 ms delay take a real share of each trade. That is why random entries at 1.5R lose about 0.2R per trade instead of breaking even.
- **2024-26 near break-even:** this is the only near-break-even period (MAIN PF 1.03, M30 PF 1.15). It comes after three losing years; picking it out now would be curve-fitting.

## Validity checks
- **Model 1 screen invalid (Addendum 1):** Model 1 filled the breakout 3–4 points late (RR 1.5 → ~1.0). It is excluded from all decisions and kept as a labelled diagnostic.
- **Model 4 fills:** a median 0.04–0.42 points from the level in every year, with RR at fill 1.42–1.49, on both generated (2021–25) and real (2026) ticks.
- **Run checks:** every report matches its EA, symbol, dates and inputs.
- **Skipped trades:** a few very tight setups were refused by the broker (`Invalid stops`) and skipped (MAIN 2, SIMPLE 10).

## Not tested (discretionary in the clip)
- skipping "chop";
- news-day selection;
- choosing direct vs rebreak by "candle aggression";
- the clip's own reading of key levels (our bias is a declared mechanical proxy);
- futures (NQ / MNQ) costs, instead of the CFD spread.

## Decision
**REJECTED at the raw gate.** Per the pipeline: no optimisation without an explicit exploratory override from the owner. Nothing installed, deployed or pushed.
