# Reproducing this research

This folder is not a live installer. The MQL5 source deliberately refuses to initialize outside the Strategy Tester. It does not change the normal MT5 charts, live profile, BATs or website.

Use the saved evidence first. `RESULTS.md` contains the review table, costs, execution stresses, validation, monthly/yearly cash flows and caveats. `RESULTS.json` and each `native/*/trades.json` preserve the underlying numbers. Every period is a separate $10,000 start unless explicitly described as a continuous-run monthly breakdown or a fixed-ledger overlay.

## Fixed research sequence

1. `PROTOCOL.md` freezes the family, dates, selection gates and stress tests before parameter search.
2. `manifest.json`, `data-audit.json` and `data/*.npz` identify the connected Exness account's frozen M1/M5 history and contract. Do not overwrite them with another account's data. A new broker, symbol contract, data revision or study window needs a new study folder.
3. `build.py` mechanically creates the tester-only research EA from the prior raw source and compiles it in the isolated tester. The raw source stays unchanged. `build.json` pins source and binary hashes.
4. `native.py` reproduces the raw version, including exact equality with the 200 prior one-year trades, then tests each independent period.
5. `screen.py` runs the frozen bar-approximation grid and chronological walk-forward diagnostic. Its selected parameters are saved before native finalist evaluation. Never describe its bar results as real-tick MT5 results.
6. `pipeline.py` runs native training/validation for the three finalists, freezes one candidate, evaluates the four requested periods, fixed-delay stresses, 0.5% requested risk, and local neighbors. Failed gates remain failed; latest-year results cannot change the selected parameters.
7. `verify.py --unit`, `verify.py`, and `probe_history.py` verify boundary/engine behavior, every saved native ledger/profile/signal, and the suspicious June 2025 history day.
8. `report.py` reconciles all complete reports, applies explicitly labeled cash overlays and resampling diagnostics, and creates the review report and evidence index.

Use the configured Python 3.13 environment that already contains MetaTrader5, NumPy and Numba. Run scripts from this study folder, one native runner at a time. The runner uses the separate `_Backtests/MT5-DMC-20260811` terminal, not the normal terminal, for Strategy Tester execution. It verifies the normal connected account read-only before each run. Never restart or close the normal terminal just to run these tests.

Completed cases are reused only if their settings/build/contract fingerprint matches. A mismatch raises an error rather than silently relabeling old results. A running native batch must finish before another is launched.

## Reproducibility caveats

- Real ticks begin 2026-01-01 on this broker feed. Older MT5 tests use generated ticks; the five-year evidence is not five years of genuine real ticks.
- Repeated broker history queries confirm that 2025-06-20 lacks the NY session. No artificial bars/trades were added. See `history-gap-probe.json`.
- The prior latest-year raw result was already known. This research cannot honestly claim a fully untouched holdout.
- Rounded-up/minimum lots can exceed the requested percentage risk. Stops and simulated execution delays do not cap all live gap losses.
- Reported zero swaps are the tester's recorded amounts, not an assumption that holding overnight is always free.
- `frozen_parser.py` is a mechanical snapshot of the existing pure MT5 HTML/deal parsing functions. It avoids importing the website while an unrelated Git operation has left conflicts there. `parser-isolation.json` verifies identical pre-existing ledgers. Do not regenerate this snapshot from changed upstream code and assume previous evidence is unchanged.
- Do not rerun a parameter search on the latest year and then call its outcome validation. Use new forward evidence for the next decision.

**User-review gate:** Gold remains research-only. Do not start the five S&P 500 pipelines, deploy, update BATs/website, or push automatically.
