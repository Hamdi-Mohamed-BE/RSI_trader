# News Pulse XAG, BTC and EURUSD - event-family research

Research only. No website, production EA, BAT, attached chart, or normal account changes are authorized by this optimization request. EURUSD remains inactive in the portfolio.

## Frozen scope

- 2025-09-19 inclusive through 2026-09-19 exclusive, matching the XAU event study.
- Isolated Exness-MT5Trial16 tester, USD 10,000, leverage 1:2000, M1, Model 4.
- Normal-terminal MCP initialization returned authorization failed; the previously configured isolated Exness tester is used instead. This is not an FTMO simulation or evidence from the normal currently connected account.
- Same frozen 30-release calendar as XAU: 11 NFP, 11 primary CPI, 8 FOMC.
- 0.75% equity planned per pending side; both sides remain eligible. Broker-valid upward lot rounding and minimum volume can exceed nominal risk; gaps and fees can exceed it further.
- XAG/BTC baseline: selected installer SETs. EURUSD baseline: last archived two-sided SET, not an active profile.
- Event-family settings, not different hindsight settings for each individual release.
- Lead 5-120 seconds; current bid/ask, active M1 or previous closed M1 anchors; symbol-scaled entry/stop distances; TP none or 0.5-8R; trailing off/on and distance/start; event close 60-600 seconds.
- Approximately 6,060 frozen-seed candidates per asset. This is bounded randomized screening with baseline neighbors, not an exhaustive global optimum.
- Top 100 per family ranked by screening return minus twice approximate DD, reranked under modest extra costs. The full-year fit is hindsight/in-sample. Independent earlier-only selection uses releases before 2026-05-19 and is compared against baseline on 2026-05-19 through 2026-09-19.
- Later-period evidence is one small chronological check, not a guarantee or independent validation of the full-year fitted selection.

## Reproduction

Use the existing system Python with NumPy, pandas, Numba and the existing Calyx report parser. Do not run two native test commands concurrently against the same portable tester.

1. `python research.py prepare` creates research-only copies from the preserved XAU source/calendar and freezes baseline SETs.
2. `python research.py collect` exports quote-only paths and runs untouched native baselines for all three assets.
3. `python search.py` runs per-family bounded screening and writes full/train selections plus top-100 lists.
4. `python research.py run --variant BaselineHoldout --start 2026.05.19` runs independent later-period baselines.
5. `python validate.py` runs full-fit, earlier-selected, earlier-selected holdout and native 250ms baseline/full-fit sensitivity checks.
6. `python -m unittest test_research -v` checks causal candle export, costs, sizing-comparison outputs, search boundaries and preserved two-sided behavior.
7. `python sensitivity.py` evaluates frozen-selection later-period cost stresses and local parameter perturbations without reselection.
8. `python make_report.py` builds the final native comparison tables and machine-readable summary when all required runs exist.

These commands generate research outputs and use only the isolated tester. They must not be confused with active portfolio installers. Research wrappers fail initialization outside Strategy Tester.

## Important limitations

- Existing official-calendar/FXMacroData receipt provenance is retained from the XAU study; a receipt alone does not establish historical point-in-time schedule vintage.
- Model 4 can include generated ticks. Preserve the exact percentage from each report.
- Native commission and swap are parsed from deals. Screening commission is calibrated per contract from the same asset's native baseline; it is not the XAU fee copied to all symbols.
- Screening uses historical bid/ask plus explicit adverse-fill/spread scenarios. It is not a liquidity/queue simulator and does not fully model margin or native order rejection.
- Screening equity envelopes are approximate and can disagree with MT5 equity DD even when trade count, wins and cash match. Native relative equity DD is authoritative.
- Native fixed execution delay can change the trade path in either direction. It does not certify future news fills or represent every source of latency.
- Final recommendations must consider chronological validation and equity risk, not only the largest fitted return.

See `RESULTS.md` and `SUMMARY.json` for completed evidence; do not quote preliminary screening estimates as native results.
