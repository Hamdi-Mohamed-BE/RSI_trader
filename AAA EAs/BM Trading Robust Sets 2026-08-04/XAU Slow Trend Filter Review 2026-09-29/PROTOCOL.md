# XAU Slow Trend: focused filter/re-entry comparison

Authorized scope: inspect the active normal MT5 account and show research results. No production edits, installation, account changes, or website publication. This is a bounded comparison, not the full optimization/promotion pipeline.

Account evidence: read-only native Python API, exact already-running normal terminal. Attribute manual exits by original position ID, not exit magic. Broker history currently starts on 2026-09-21 for this magic. Saved chart is XAUUSDr while actual deals are XAUUSD; saved chart is therefore not proof of active runtime inputs. Installed binary hash differs from current source build. Compare installed binary against switches-off research clone before claiming parity. Actual live input settings cannot be read through Python MT5 API; use saved H4/1.5ATR/6R/1% inputs, clearly disclose this limitation.

Keep momentum (1/3/6 month majority), EMA600 on H4, ATR14 x1.5 stop, 6R target, no trailing, both directions, one position, original 24h entry-to-entry cooldown and 1% equity risk rounded upward unchanged. Run XAUUSD CFD in the separate native tester, USD10,000, 150ms delay, broker costs. No live terminal restart. The installed binary is copied for tester use only.

Freeze eleven versions before results: baseline; DI agreement only; ADX14 >=20 only; ADX14 >=25 only; ADX20 + DI; ADX25 + DI; ADX20 + DI + ADX rising; wait24h after any full exit; wait for original signal to change after any full exit; ADX20 + DI + exit24h; ADX20 + DI + signal reset. ADX is native iADX, completed H4 bar only. DI agreement: +DI > -DI for buys, reverse for sells. Rising compares closed bar1 to bar2. Zero threshold disables strength filter. Re-entry rules affect all full exits in historical tests; manual-only pause cannot be profitability-tested without a reproducible manual exit rule.

First parity on 2025-09-27 through 2026-09-27 (exclusive), native Model1. If parity fails, stop and investigate, do not describe current source as identical to installed EA.

Development: 2021-09-27 through 2024-09-27. Compare all eleven on Model1. Rank net-positive candidates with >=20 trades, PF>=1.15 by return/max-equity-DD; retain top3, then compare them with baseline on validation 2024-09-27 through 2025-09-27. Pick among positive validation candidates with >=10 trades and PF>=1.1 by validation return/DD. If none qualifies, report failure without pretending there is a validated winner. No new thresholds invented after seeing results.

Recent-year and six-month checks: 2025-09-27/2026-03-27 through 2026-09-27. Native Model4 baseline and frozen winner, if any. Also recent Model4 check the best development candidate if validation fails, explicitly exploratory (not promotion). Original recent period already used for parity and overlapping website history already seen: not pristine holdout. No parameter retuning afterward. Native actual equity DD, costs and closed-trade ledger reconciled; older history may use generated ticks. Count all configurations and tests. Long-running swaps use tester's broker specification, not reconstructed historical swap schedules. Manual-closing live results are not unattended bot results.

No Monte Carlo or deployment claim; a survivor would require the full robustness pipeline and new approval before any implementation in production.
