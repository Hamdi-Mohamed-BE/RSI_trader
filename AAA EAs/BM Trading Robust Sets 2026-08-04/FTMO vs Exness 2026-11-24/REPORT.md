# FTMO vs Exness prices: Best 1-Step (10 EAs), 2026-11-24

Owner question: "Compare the FTMO results for the last 2 months to Exness, run the full simulation, and show the pass rate. Does it change or stay the same?"

## Method

- **FTMO prices:** read-only export from the owner's FTMO terminal (FTMO-Server4). M1 bars from 2021-06 and real ticks for 2026-09-21 → 11-20 (`export_ftmo.py`).
  - They were imported as custom symbols `*.ftmo` in the isolated research terminal (`ImportFTMO.mq5`), with specs cloned from Exness.
- **Clock:** the FTMO server is UTC+3 while the US is on daylight saving time, otherwise UTC+2 (US dates, not EU).
  - v1 used the EU dates and was 1 h off in 19 weeks of 2021-2026.
  - Found from one-hour-shifted trades in the week of Oct 26-30. Fixed in v2: `clock_check.py` now shows lag 0 in all 270 / 274 weeks for US100 / XAUUSD.
  - The v1 runs are kept in `native-INVALID-v1clock/`.
- **EAs and settings:** the Best 1-Step no-guard package EX5s and inputs, each EA alone, 1% of balance, 150 ms. Nasdaq 5M × 0.75 as installed.
- **FTMO commission** (added after the tests; custom symbols charge none):
  - XAUUSD: $3 per lot per side, measured on the owner's FTMO deals.
  - USDJPY: $2.5 per lot per side, ASSUMED.
  - US100 and UK100: $0 (US100 measured).

## 1. Last two months, native Model 4 on real ticks (2026-09-22 → data end 2026-11-20, $10k, `compare2m.py` + `report2m.py`)

| EA | Exness trades | Exness R | Exness PF | FTMO trades | FTMO R | FTMO PF | same trades |
|---|---|---|---|---|---|---|---|
| Nasdaq 5M (×0.75) | 44 | +14.60 | 2.34 | 44 | +12.79 | 2.16 | 44/44 |
| USDJPY London | 16 | −2.33 | 0.54 | 16 | −3.97 | 0.25 | 16/16 |
| 3 Way Gold | 11 | +1.82 | 1.51 | 11 | +1.38 | 1.35 | 11/11 |
| EMA3 | 6 | +10.85 | 9.47 | 6 | +10.91 | 9.50 | 6/6 |
| Selective ORB V3 | 1 | −0.06 | – | 2 | −0.51 | 0.50 | 0 |
| XAU RSI VWAP | 14 | +2.39 | 1.61 | 15 | +1.31 | 1.26 | 10 |
| ORB VP Volume Confirmed | 7 | +5.62 | 6.26 | 6 | +5.60 | 6.37 | 5 |
| Overnight Bias ORB | 20 | +9.62 | 2.27 | 20 | +9.66 | 2.28 | 20/20 |
| UK100 Monday Dip | 3 | −1.98 | 0.05 | 2 | −2.04 | 0.00 | 2 |
| Asia Breakout | 9 | +4.13 | 1.68 | 9 | +4.14 | 1.68 | 9/9 |
| **Total** | **131** | **+44.65** | **2.07** | **131** | **+39.25** | **1.88** | |

Both feeds: 66.5 trades per month, 3.16 per trading day.

## 2. Five years (native Model 1 on both feeds, test 2021-08 → 2026-10-07, sim window 2021-10-07 → 2026-10-06, weekend / holiday flat applied, `run5y.py` + `build5y.py`)

The rebuilt Exness stream reproduces the reference stream INPUTS_N75: 406.0R vs 408.2R, with the same trade counts except 3 Way Gold partial-close rows.

| EA | Exness trades | /month | Exness R | Exness PF | FTMO trades | /month | FTMO R | FTMO PF |
|---|---|---|---|---|---|---|---|---|
| Nasdaq 5M | 1,286 | 21.5 | 63.8 | 1.14 | 1,287 | 21.5 | 89.5 | 1.20 |
| Overnight Bias ORB | 542 | 9.0 | 96.1 | 1.43 | 548 | 9.1 | 103.2 | 1.46 |
| USDJPY London | 461 | 7.7 | 90.9 | 1.68 | 458 | 7.6 | 84.7 | 1.64 |
| 3 Way Gold | 434 | 7.2 | 27.7 | 1.24 | 409 | 6.8 | 23.6 | 1.22 |
| XAU RSI VWAP | 256 | 4.3 | 19.6 | 1.29 | 265 | 4.4 | 23.7 | 1.34 |
| EMA3 | 207 | 3.5 | 14.0 | 1.21 | 216 | 3.6 | 13.4 | 1.19 |
| Asia Breakout | 189 | 3.2 | 33.1 | 1.33 | 174 | 2.9 | 29.5 | 1.33 |
| UK100 Monday Dip | 124 | 2.1 | 17.2 | 1.33 | 125 | 2.1 | 28.5 | 1.59 |
| ORB VP Volume Confirmed | 119 | 2.0 | 32.3 | 1.70 | 119 | 2.0 | 33.7 | 1.73 |
| Selective ORB V3 | 34 | 0.6 | 11.2 | 4.71 | 71 | 1.2 | 7.3 | 1.41 |
| **Total** | **3,652** | **60.9** | **406.0** | **1.32** | **3,672** | **61.3** | **437.0** | **1.35** |

Trades per trading day: 2.90 on Exness, 2.92 on FTMO.

## 3. Pass rate (frozen multi-firm engine `Multi Firm Funded 2026-11-17/first_payout.py`, $100k, no guard, MC 1,000 × 28-day blocks)

Days are median calendar days.

| Account @ risk | Feed | First-try pass (MC) | Days to funded | First payout | First payout day | One fee only |
|---|---|---|---|---|---|---|
| FTMO 1-Step @0.75% | Reference N75 | 93.1% | 59 | $7,095 | 106 | 86.0% |
| FTMO 1-Step @0.75% | Exness rebuilt | 92.7% | 59 | $7,205 | 109 | 84.4% |
| FTMO 1-Step @0.75% | **FTMO prices** | **87.8%** | **53** | $7,877 | 110 | 75.2% |
| FTMO 1-Step @0.5% | Exness rebuilt | 97.4% | 86 | $4,790 | 134 | 96.5% |
| FTMO 1-Step @0.5% | **FTMO prices** | **99.3%** | **81** | $5,413 | 132 | 98.5% |
| FTMO 2-Step @0.75% | Exness rebuilt | 95.5% | 89 | $2,343 | 112 | 92.1% |
| FTMO 2-Step @0.75% | **FTMO prices** | **96.6%** | **85** | $2,627 | 104 | 94.5% |
| FTMO 2-Step @0.5% | Exness rebuilt | 99.2% | 138 | $1,826 | 158 | 99.2% |
| FTMO 2-Step @0.5% | **FTMO prices** | **99.6%** | **128** | $2,029 | 149 | 99.6% |

- **Historical starts, FTMO 1-Step @0.75%:** Exness 86.8% (median 96 days to funded); FTMO 94.3% (median 60 days).
- **FTMO's current swap table** (`_FX_FTS`, a sensitivity check): almost no change (87.7% / 99.4% / 96.7% / 99.6%).
- **Why 1-Step @0.75% drops** even though FTMO prices make more R:
  - The limit is 3% daily = 4R, and the portfolio's worst days sit at about −3.5R to −4R.
  - On FTMO prices, 3 days cross −4R: 2023-03-09 (−4.37), 2026-09-01 (−4.54) and 2026-09-11 (−4.02). On Exness, none does (worst −4.00).
  - The cause is small path differences: an RSI VWAP gap through its stop, and a 3 Way Gold trade that won on Exness and lost on FTMO.

## Limits

- Model 1 (M1 OHLC) on both feeds for the 5-year test; FTMO real ticks exist only from 2026-09-21.
- FTMO swaps are cloned from Exness in the native runs; the current FTMO table is only a sensitivity check. The USDJPY commission is assumed.
- Tick volume differs by broker: Selective ORB V3 trades twice as often on FTMO.
- No guard was modelled (the Ready for FTMO guard latches at 2.5% daily). No news closes. In-sample: the EA list was chosen with hindsight.
