# Gold Overnight Value Area — approved raw production integration

Added 19 September 2026 at the user's explicit confirmation. This is the **raw Value Area version**, not the optimized candidate, POC variant, or an FTMO deployment.

## Unchanged trading rules

- Gold only; 18:00 previous day to 09:30 America/New_York overnight profile.
- 64 bins, M1 HLC3 weighted by broker tick volume, 70% contiguous value area.
- First completed M5 close above VAH buys; below VAL sells.
- Stop one price tick beyond the opposite value-area edge. Target overnight high/low.
- Invalid reward/stop geometry consumes that day's attempt. One attempt per day, no breakeven or trailing stop. Close by 16:00 New York or shortly before the broker session ends.
- Default 1% equity risk; broker lots round upward, including the minimum lot. This can exceed the requested cash risk. Fixed-dollar and custom-percent installer inputs are supported. Insufficient margin and invalid broker geometry still prevent orders.

## Operational additions

Automatic live broker-time offset; explicit tester offset. Hedging-account safeguard. Restart-aware daily attempt state. Timer retries exits but never creates entries. Shared adaptive controls apply to this non-news EA only when the Adaptive BAT enables them. Raw signal/exit settings are locked.

All seven maintained normal MT5 BATs use the same updated 34-EA roster, including RECOMMENDED ADAPTIVE.bat. Full Safe preserves these raw rules; no invented Safe result is assigned. Ava and archived installers were not changed. No live terminal charts were installed or restarted for this task.

## Evidence and verification

- Compilation: 0 errors, 0 warnings.
- Isolated native MT5 control: **200/200 one-year trades exactly match** original raw entry/exit times, side, size, prices, net profit, commission, swap, original SL and TP. See parity.json and retained verification report.
- Native raw period caches: 6 months, 1 year, 3 years and 5 years. Exness gold, $10K, 1% target, 150 ms delay. Real ticks begin January 2026; earlier coverage is generated ticks. June 20, 2025 NY session is missing. These are not native FTMO results.
- New website tests reconcile count, fees and net P/L, reject date rebasing, check all period endpoints, and reconcile all portfolio ledgers.
- 44 focused website/adaptive/news tests pass. One pre-existing archived News Pulse source-hash assertion remains excluded: it expects SHA 895f66..., while the unchanged legacy file is 0871ca.... Current production news report/source/parity checks pass; the legacy hash was not silently blessed or its unrelated source rewritten.
- Pure-function PowerShell checks pass for seven BAT routes and default/adaptive/fixed-dollar/custom-percent/raw-preserving Safe settings. They never execute installer top-level actions.
- The local website was restarted and returned HTTP 200 for the new EA and portfolio; 34 catalog entries, one raw Gold entry. Gold News V9 remains evidence-pending, so 33 EAs contribute tested portfolio ledgers.

## Publication and recovery notes

Existing generated JSON and installer/catalog source contained committed merge-marker fragments. Relevant source conflicts were resolved to the approved event-specific side. Generated originals were backed up in verification/website-merge-backup.zip before recovery; sixteen news windows were independently validated against their native report/source/calendar/SET identities.

The portfolio now uses the intersection of available component windows, ending August 30, 2026; product pages retain their individual native windows. The curve remains a closed-cash-flow overlay of independently sized tests, not a shared-margin account simulation. Existing mode-selection audit JSON is a historical snapshot, not a new full optimization. The manifest and current portfolio caches were refreshed to include Gold.

The new FTMO study is separate: see ../FTMO Combination Study 2026-09-19/REPORT.md. Its $71.43 ordinary risk, reduced news alternatives and extra admission controls have **not** replaced the regular BAT risks or news exemptions. No guaranteed pass/payout claim is supported.
