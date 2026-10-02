# Gold-only news launchers

Owner request, 2 October 2026: disable non-gold news EAs in all BATs.

The common manifest policy excludes XAG, BTC, EURUSD and any unrecognised news EA before source-file checks, symbol lookup, risk settings or chart generation. Normal Standard, Safe, dynamic, 100K, 900, Best Recommended, Claude, Recommended Adaptive and compatibility BATs all use this policy. Their two gold news EAs remain: XAU News Pulse and Gold News V9 Direction. The Ava BATs keep gold News Pulse and omit silver News Pulse.

The FTMO NEWS OFF launcher stays NEWS OFF, including gold. Client Top 5 has no news EAs; it is unchanged. Existing standalone Python/AI gold-news launchers are gold-only and remain unchanged. Backtest/data-research launchers are not trading installers and their historical evidence was not rewritten.

This is an installer change, not an account operation: no running terminal was restarted, EA detached, order cancelled, or position closed. Existing non-gold news charts remain active until the user switches/reinstalls the managed profile or removes them. Historical binaries and settings are retained but cannot be selected by the managed installer.

Run `_Auto Deploy/Test-News-Launcher-Policy.ps1` for non-mutating filtering and syntax tests. Shared installer `-ValidateOnly` verifies packaged sources without changing a terminal. Portfolio performance estimates for the previous news basket are not evidence for the newly filtered basket.
