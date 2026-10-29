# funded_v1 build 2026-10-28 — COMPLETE (9 EAs, configurable funded-account guard)

**Owner requests:**
- build `funded_v1` for any account, with a BAT that asks the DI filter, the risk per trade and every guard variable
  (with defaults);
- guard with max daily loss, max open risk and max daily win (auto-close all);
- show expected value per week and a realistic data table;
- 8 EAs, then "add gold overnight too".

**Deliverable:** `_00 Live profiles/funded_v1/`
- `funded_v1.bat`;
- EAs/ and Sets/ with SHA-256 values in PORTFOLIO.json;
- README.md.

The BAT installs `_00 Live profiles/Packages/FundedV1` (`FUNDED-V1-20261028-9EA`, guard `CalyxFundedGuard.mqh`,
installer `Install-FundedV1.ps1`).

## Firm rules (Leveraged, answers 2026-10-27, the guard defaults)
- **Max loss:** 6% trailing the highest CLOSED balance. It locks at the initial $50,000 at +6% and after any payout.
- **Daily loss:** 3% from the higher of balance / equity at 00:00 UTC.
- **Payouts:** reward after 14 days; ≥ 3 days of ≥ 0.5%; best day < 20% of the period profit.
- **EAs:** self-developed EAs allowed. Grid / martingale escalation and HFT are prohibited.
- **News:** no opening or closing ±5 min around high-impact news.
- **Commission:** gold $4 / lot round trip; indices free.

## Files
| File | What |
|---|---|
| `guard/CalyxFundedGuard.mqh` | the guard: Turbo v2 core plus every limit as an input, floor lock, UTC reset with a max(balance, equity) day reference, close-all on daily win / daily loss / floor buffer, news entry blackout (live MT5 calendar), payouts excluded from daily loss |
| `build_funded_v1.py`, `restore_tested_ex5.py` | package build. The 8 original EX5 are the exact binaries tested as v2; all sources are byte-identical |
| `native.py`, `audit.py` → `AUDIT.md` | native Model-4 tests and their audit |
| `harness/Funded Guard Harness.mq5` | rule harness (2 modes) |
| `test_install_sandbox.ps1` | the real installer statements on a fake data folder |
| `funded_sim.py`, `funded_table.py` → `FUNDED_SIM.md` | Leveraged-rule simulation. Kernel check: exact against a direct ledger sum (1,196 trades, $4,523.16) |
| `volconf_rows.py` → `VOLCONF_05R_ROWS.json` | ORB VP Volume Confirmed 0.5R ledger from a fresh 5y native run: +11.3%, PF 1.33, 122 trades; matches the report to the cent |
| `superseded/` | the first package (optimizer-format SETs), v1 (the day-reference bug the harness found), the v2 8-EA package and their native runs |

## Test results (final package)
- **Wrapper fidelity:** 9 / 9 guarded EAs in pass-through mode reproduce the originals trade for trade (6m, Model 4,
  $50k, 1:30).
- **Guard ON, each EA alone, 1y:** 9 / 9 audits PASS.
  - Every entry is sized exactly to the rule.
  - Every refusal is justified.
  - Floor lock and day lock are correct.
  - The floor rebuild is within $0.89.
  - No breach.
  - Daily-win close-alls happened naturally: Nasdaq 5M 20, DMC Current 6.
- **Harness:** 19 / 19 PASS (mode 1) and 3 / 3 PASS (mode 2, a real −2% loss closes everything at −$1,005).
- **Installer:** sandbox PASS for the defaults run and the typed-answers run. It found and fixed two installer bugs:
  - `[Math]::Min(5,0.75)` returned 1;
  - G17 formatting wrote 0.3 as 0.29999999999999999.
- **BAT:** `-ValidateOnly` PASS.

## Expected results (Python replay of ledgers 2021-10 → 2026-10, Leveraged rules, $3,000 payout cushion; NOT a forecast)
| Nasdaq DI | Risk | Payout / week 3y mean (p10 – p90) | Per month | First-year / week | Breach | First payout (median day) | Trades / month (/ day) |
|---|---:|---:|---:|---:|---:|---:|---:|
| ON | 0.3% | $80 ($14 – $137) | $348 | $39 | 0% | 239 | 56 (1.84) |
| **ON** | **0.5%** | **$99 ($8 – $177)** | **$428** | **$46** | **0%** | **234** | **53 (1.73)** |
| ON | 0.75% | $103 ($6 – $199) | $447 | $47 | 0% | 235 | 51 (1.68) |
| ON | 1% | $99 ($5 – $197) | $430 | $46 | 0% | 234 | 51 (1.66) |
| OFF | 0.5% | $84 ($0 – $173) | $367 | $42 | 0% | 242 | 56 (1.85) |

- **By market (0.5% DI ON):** weak 2021–23 ≈ $4 / week; middle 2023–24 ≈ $24; strong 2024–26 ≈ $177.
- **Cost stress:** +0.10R per trade → ≈ $2 / week.
- **Smaller cushion:** a $1,500 cushion → $77 / week.
- **Gold Overnight:** adding it changes almost nothing ($100 → $99 a week), in line with the Turbo leave-one-out
  finding that it is a drag.

## Limits
- **No combined native run:** the tester runs one EA at a time.
- **Daily-win close-all:** the replay stops new entries only. The live guard closes everything at +0.75% equity.
- **Day reference:** live uses max(balance, equity) at reset; the replay uses balance.
- **News:** SL/TP fills inside a news window are not prevented, and the blackout is untestable in the tester (no
  calendar there).
- **Confirm with Leveraged:** that partial payouts are allowed.
- **Not installed on any terminal; not pushed.**
