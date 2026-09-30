# Research-only operating notes

This folder is not a production EA package. Nothing here attaches an EA to an
account, changes running charts, deploys the website or pushes to GitHub.

## Completed decision — 2026-09-28

All three assets failed validation. The 1,242 staged search tests (1,152 unique
asset/settings combinations) and 20 native confirmation/baseline runs are
complete. The final audit passed seven helper tests and checked 59 completed
batches / 1,262 cases, including position-ID ledgers, source/build hashes,
native costs and results, no-trade warmup, position caps and session boundaries.
All nine finalist validation runs lost money. Development sensitivity checks
passed, but that does not override the failed validation gate.

`REPORT.md` contains the final same-date raw/candidate comparison and all
validation alternatives. Holdout, Monte Carlo, FTMO and promotion were not
started because no candidate qualified. The isolated tester has exited; the
normal MT5 process was left untouched. Do not resume or promote this study
merely because the historical resume instructions below are present.

## Resume

Run `search.py all` with the existing Python 3.13 runtime. Completed immutable
batches in `native-v2/` are reused only when their full manifest matches. A
changed strategy/protocol requires a new output namespace, not overwriting old
evidence. `native/` retains the pre-review baseline runs.

The runner refuses to use an occupied isolated tester or tester port. It uses
only `_Backtests/MT5-DMC-20260811`, an empty chart profile, disabled live Experts,
local test agents and unique Common Files tags. It never terminates an unrelated
process. The normal terminal under Program Files must be left untouched.

`status.json` shows the most recently started/completed batch. It is not proof
the whole pipeline passed. `SEARCH RESULTS.json` retains every completed search
case; `FINALISTS.json` records conditional gate outcomes. Run `verify.py` and
`report.py` after confirmations complete to refresh the evidence audit/report.

## Interpretation

Model 1 is a coarse M1-OHLC screen, particularly approximate for intrabar touch,
pending-order and trailing logic. Model 4 confirmation is mandatory. A staged
beam search can miss interactions and is not proof of a global optimum. Trade
and equity statistics from these two models must not be blended or relabelled.

Raw defaults reproduce all four original single-engine entries/exits/volumes and
net P&L. Gold combined has independent position IDs for its two engines, so its
ledger must not be reconstructed by a same-symbol FIFO parser.

If development/plateau/validation/frozen confirmation fails, stop that candidate
and report rejection. If early history is unavailable, report the blocked check;
do not silently shorten it. Only eligible frozen candidates proceed to the
conditional robustness stages in PROTOCOL.md. No live/FTMO approval is automatic.

Generated tester configurations include an account/server reference copied from
the existing isolated research setup. They are local-only. Do not publish raw
journals or configuration files without a privacy review.
