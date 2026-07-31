# LTA System

Gold-first implementation of the process described in the LTA Concepts
e-book. The application separates market context, zones, profiles, structure,
entry models, grading, risk, and execution so every decision can be audited.

## Safety

- Configured risk is **2.5% per trade**, as requested.
- Live order submission is disabled by default.
- `ENABLE_TRADING=true` alone is not enough; the code also requires a separate
  live-unlock token after validation.
- The initial MT5 profile uses broker tick volume and is labeled
  `TICK_VOLUME_APPROX`. It is not presented as centralized COMEX volume.

## Commands

```powershell
uv sync --extra dev
uv run lta account
uv run lta scan
uv run lta forward
uv run lta backtest
uv run lta validate
uv run pytest
```

Windows launchers are included for account status, scanning, backtesting, and
validation.

## Current scope

- Automatic broker symbol discovery.
- H1 context with M15 execution by default.
- Completed previous-day and previous-week volume profiles.
- Deterministic supply/demand candidates.
- EM1, EM2, EM3, and EM4 research implementations.
- EM1 and EM3 are the safe defaults. EM2 and EM4 remain disabled until
  independently labeled lower-timeframe examples pass validation.
- A/B grading with mandatory 2R target feasibility.
- Chronological bar-by-bar backtest with spread and conservative same-bar
  resolution.
- Chronological development/validation/holdout reports.
- Forward scanner with proposed entry, invalidation, targets, grade, and cash
  risk.

See `LTA_SYSTEM_DEVELOPMENT_PLAN.md` for the full research and approval plan.
