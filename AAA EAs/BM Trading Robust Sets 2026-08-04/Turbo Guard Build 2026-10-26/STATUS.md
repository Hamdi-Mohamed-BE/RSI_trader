# Turbo guard build 2026-10-26/27 — COMPLETE for the owner's 5-EA portfolio

**Deliverable:** `_00 Live profiles/Turbo 50k - Custom 5 Guarded/`
- `Install Turbo 5 Guarded.bat`;
- EAs/ and Sets/ with SHA-256 values in `PORTFOLIO.json`;
- README.

The BAT installs `_00 Live profiles/Packages/Turbo5/`:
- version `TURBO5-GUARDED-20261027-v2`;
- guard `CalyxTurboGuard.mqh`;
- `Install-Turbo5.ps1`.

## Files
| File | What |
|---|---|
| `guard/CalyxTurboGuard.mqh` | the guard (master copy). v2 caches the deal walk and throttles logs. |
| `build_turbo5.py` | builds the package from the Full EA BAT sources / presets: OrderSend → TurboOrderSend, CTrade shim, wrappers. All 5 compile with 0 errors / 0 warnings. |
| `native_tests.py`, `audit.py` | native Model-4 tests and their audit → `AUDIT.md` / `AUDIT.json` |
| `harness/Turbo Guard Harness.mq5` | rule harness in the tester: 12 / 12 PASS |
| `test_install_sandbox.ps1` | the real installer statements on a fake data folder: PASS |
| `superseded-v1/` | first build. Its guard rebuilt the ledger on every retry, so the Nasdaq 1y run hung for 3.8 h. Also holds the morning original runs, superseded by tester swap drift. Kept as evidence. |

## Results
- **Parity:** 5 / 5 identical, guarded pass-through vs original. The comparison uses originals rerun on the same day,
  because the tester swap spec changed between the morning and evening runs.
- **Guard ON, 1y, each EA:** 5 / 5 audits PASS. Results are in AUDIT.md.
- **Harness:** 12 / 12 PASS.
- **Installer:** BAT `-ValidateOnly` PASS; sandbox PASS.

## Limits
- No combined 5-EA native run (the tester runs one EA at a time).
- No payout occurred in the single-EA years; the withdrawal re-base is proven by the harness.
- The Turbo rule assumptions still need written confirmation from Turbo.
- Not installed on any terminal; nothing pushed.
