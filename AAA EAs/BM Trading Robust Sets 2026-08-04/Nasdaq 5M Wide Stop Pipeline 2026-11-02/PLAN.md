# Nasdaq 5M wide-stop optimisation: plan (frozen 2026-11-02, before any result)

**Owner request (2026-11-02):** optimise the Nasdaq 5M EA with a wider SL range, using in-sample and out-of-sample data. Target the QuantLab "Session Open Momentum" profile since 2019 (NAS100 M5, one window a day at the New York open, "protect with a wide stop", "let the move run"):
- +505.8% at 1% risk;
- win rate 56.4%, PF 1.24, max DD −26.6%;
- 1,792 trades, 4.4 a week.

**The QuantLab trade in the owner's screenshot (2 Nov 2026):** a sell of 3.4 lots showing +$55.93 at 28,581.05, so entry ≈ 28,597.5. With SL 28,927.03, the stop is ≈ 330 points ≈ **1.15% of price**. Ours is 0.60%. QuantLab's exact rules are behind a subscription; only step names and summary statistics are public. They are a target profile, not a specification.

## Fixed (unchanged)
- **EA:** production `Nasdaq 5M DI Wide ATR EA.ex5` (sha fe9f391db5af) with the production preset.
  - Signal: the 09:30 New York M5 candle versus EMA12; DI14 agreement when ON.
  - Exits: overnight holding allowed unless a version closes at the session end.
  - Risk: 1% of equity per trade; adaptive off.
- **Inputs only:** no code change.
- **Test setup:** USTEC (Exness CFD), $10,000, 150 ms, broker costs.
  - **Search:** native MT5 Model 1. Entries are at the next bar's open after the signal candle closes, and the stops are wide.
  - **Confirmation:** Model 4 on the chosen version and the baseline, with a Model 1 / Model 4 parity check.

## Data split (shared `data_split.py`; history from 2019-01-01, end 2026-11-01 exclusive)
| Part | Dates | Use |
|---|---|---|
| Development | 2019-01-01 → 2023-11-01 | selection |
| Validation | 2023-11-01 → 2024-11-01 | pass / fail |
| **OOS** | 2024-11-01 → 2026-11-01 (last two years) | reported once |

Each full-period run is split by **trade entry date**. Part metrics are in R (1% risk budget at entry), plus return and closed DD inside each part.

**The OOS is previously viewed.** The current production preset (0.60%, ATR6) was chosen on 2021–2026 data, so the baseline's OOS is not untouched. The new versions are selected on development only.

## Search space (124 runs)
- **Stop % of price:** 0.40, 0.60, 0.80, 1.00, 1.15, 1.30, 1.50, 2.00.
- **Management:**
  - M1: ATR14×6 trail from +1R, no TP (current);
  - M2: ATR×4 trail from +1R;
  - M3: ATR×10 trail from +1R;
  - M4: no trail, TP 2R;
  - M5: no trail, TP 1R;
  - M6: no trail, no TP, close at 15:55 NY (day trade);
  - M7: ATR×6 trail from +0.5R.
- **DI filter:** ON / OFF.
- That gives 8 × 7 × 2 = 112 runs. Plus **ATR-based stops** (stop mode ATR): 6, 9 and 12 × ATR14(M5), with M1 or M4, DI ON / OFF = 12.

## Selection rules (development only)
1. **Eligible:** at least 200 development trades, development PF ≥ 1.15, net R > 0.
2. **Plateau:** the neighbouring stop values (one step either side, same management and DI) must have development PF ≥ 1.10.
3. **Pick:** the highest development net R ÷ max closed-DD R among eligible plateau versions.
4. **Validation:** must be positive with PF ≥ 1.10, otherwise REJECTED_AT_VALIDATION.
5. **OOS:** reported once, no re-selection.
6. **Monte Carlo** on the chosen version is mandatory: 4-week block bootstrap of the full-period trade ledger, 2,000 paths. It gives P(loss year), DD percentiles and the return distribution.
7. **Baseline (current production) comparison** in every table.
