# Nasdaq Weakness — MT5 research bot

This project converts the supplied handwritten Nasdaq/New York-open notes into
explicit, auditable rules. It uses the open MT5 terminal and automatically
discovers the broker's Nasdaq-100 alias (`US100`, `NAS100`, `USTEC`, `NDX`,
`NASDAQ`, or a dated contract such as `NAS100U6`).

## Implemented models

- **S1 — 09:30 New York weakness short**
  - Price below the previous completed H4 midpoint.
  - The 09:15–09:30 reference candle closes below its midpoint.
  - Two half-risk legs: fixed 2R target and an M15 trailing runner.
- **S2A — green second NY candle fade**
  - Evaluated at 10:00 New York time.
  - Sell limit at the reference high and sell stop at the reference low.
  - Stop above the London high; 2R and 3R variants.
- **S2B — red second NY candle continuation**
  - Research variants support a midpoint/low pair.
  - The optimized default uses one sell limit 50 Nasdaq price units above the
    red candle close, a 100-unit stop, and a 3R target.
- Body-close strength invalidation, London session range, previous H4 context,
  M15 runner trailing, order expiry, spread/slippage checks, one total 2% idea
  risk, and New York/London daylight-saving conversion.

`NOTE_POINT_TO_PRICE` is explicit because the source notes do not establish
whether “50 points” means 5 or 50 Nasdaq price points. The optimizer compares
both 0.1 and 1.0 conversions.

## Commands

```powershell
uv sync --extra dev
uv run nasdaq-weakness account
uv run nasdaq-weakness scan
uv run nasdaq-weakness backtest
uv run nasdaq-weakness optimize
uv run nasdaq-weakness forward
uv run pytest -q
```

Windows launchers are included for the same operations.

## Validation policy

Optimization sees only the first 60% of available dates. The chosen parameter
set is then measured once on a 20% validation segment and once on an untouched
20% holdout. Live execution remains locked unless the user deliberately changes
all three safety controls in `.env`; this does **not** mean a failed strategy
should be unlocked.

The current broker contract may expose less history than `HISTORY_DAYS`.
Reports always show the dates actually returned by MT5.

The current `.env` contains the training-selected candidate: **S2B,
1.0 price-unit conversion, close + 50 sell limit, 100-point stop, and 3R
target**. It passed the available historical segments and cost stresses, so it
is suitable for forward-demo observation. Live execution remains locked because
the current broker symbol is a dated `NAS100U6` contract while the one-year
research sample is the broker's older continuous `UT100` CFD.

## Live execution

The live engine includes:

- 2% account-equity risk sizing split across legs;
- market, sell-limit and sell-stop submission with filling-mode negotiation;
- OCO cancellation after a fill;
- order expiry;
- M15 body invalidation;
- runner stop management; and
- forced session exit.

It is deliberately disabled by default:

```text
ENABLE_TRADING=false
DRY_RUN=true
LIVE_UNLOCK=
```

Use the forward scanner first. A high in-sample PF is not approval.
