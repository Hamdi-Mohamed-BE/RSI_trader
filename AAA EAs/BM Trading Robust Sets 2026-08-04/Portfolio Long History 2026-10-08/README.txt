Frozen portfolio long-history extension, 8 October 2026

Requested coverage: 6 October 2021 to 6 October 2026 (end exclusive).
Three-year coverage: 6 October 2023 to 6 October 2026 (end exclusive).

Membership, strategy sources and parameters are fixed in PLAN.json before testing.
No optimization, re-selection, deployment, live-account API, or folder rename.
The dedicated portable MT5 strategy tester uses an empty chart profile with live
expert execution disabled. A shared file lease prevents concurrent tester jobs.
Only a process created by the runner may be terminated on its own timeout.

Each component is tested over five years, with frozen current rules and 150 ms
execution delay. Native report parameters, deals, costs, hashes and cash totals
are verified. Equivalent ACTIVE parameters may reuse an explicitly referenced
native test; inactive/operational settings never cause silent strategy changes.

Each portfolio is then replayed OFFLINE, with its own membership, entry-time risk
and admission controls. This is NOT a native simultaneous shared-margin account.
Three-year/recent windows are clearly labelled signal-ledger slices/replays, not
independent native tests. Carry-in/carry-out positions are excluded. Intratrade
floating equity and partial-close timing are not reconstructed.
Positions forcibly liquidated by MT5 only because the five-year test ended are
also excluded from portfolio closed-trade replays, not counted as strategy exits.

Five screened ORB versions remain fixed, including the current 4R US100 New York
and 2R Selective variants. Existing selected-profile annual references remain
separate. Longer data is not used to optimize hours, risk references or settings.

Full normal portfolio: historical Gold News V9 predictions are unavailable. The
live HTTP/file bridge MUST NOT be called or interpreted as zero historical P/L.
Its missing coverage is explicit. News Pulse uses saved official-source release
receipts in a tester-only include; it is not a point-in-time calendar vintage.
The copied news source accelerates only the immutable UTC calendar lookup, using
cached epochs and a binary search. The one-second timer, callbacks, placement,
management and exits are untouched. 412,384 predicate checks and a native monthly
trade/cash/report parity comparison passed; see Calendar Search Proof.json and
Calendar Lookup Parity/VERIFICATION.json. Production news sources are unchanged.
Hourly EAs have NO STOP: their original historical-loss reference is retained,
not recalibrated on the five-year sample and not described as a future loss cap.
Adaptive loss-run tapers use separate magic-number lanes for 3-Way Gold's
modules, matching its source RiskBudget; other rows retain their EA-level lane.
XAU Weakness preserves its existing half-risk limit/stop split; the selected
idea budget is not independently assigned in full to both filled orders.

Real-tick coverage varies; earlier unavailable ticks may be synthesized by MT5.
Read AUDIT.json and source_history_quality before interpreting these results.
Contract multipliers are checked against native exit-leg profits (including
partials). ETHUSD in this isolated Exness tester uses multiplier 1. USDJPY
initial-stop risk uses the stop-price USD conversion; the exact conversion
bid/ask is not exported, so exit-profit reconciliation allows 0.05% for JPY.

Research runner: run.py all --wait
Verification and evidence: publish.py
Independent native cash / contract / publication reconciliation: verify.py
Website publisher: EA store/tools/build_portfolio_catalog.py
Outputs: RUN_STATUS.json, HISTORIES.json, RISK_ROWS.json, AUDIT.json, native/.
