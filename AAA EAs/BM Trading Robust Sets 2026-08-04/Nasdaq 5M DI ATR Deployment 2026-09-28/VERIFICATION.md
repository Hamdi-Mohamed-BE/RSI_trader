# Verification

- Exact SHA-256 match against the tested QL_ATR research EX5 and all four SETs.
- All four report hashes, requested windows, every explicit input, trade counts
  and net profits checked before publishing; no fixed-target returns relabelled.
- 4 new website tests pass: preset, artifact/ledger identity, rendered default,
  guarded FTMO risk/account-lock/news policy.
- All 8 normal launcher modes pass offline parameter assertions, including
  Adaptive 0.25x and Dynamic risk handling. All 13 FTMO charts pass construction
  checks; FTMO ValidateOnly passes without account access.
- All 13 guarded package EAs compile with 0 errors / 0 warnings.
- Whole website suite: 87 passed, 8 failed. Before these changes: 83 passed,
  the same 8 failed. Existing failures concern stale EA counts, Gold metadata
  and an older News source-hash expectation, not this change.
- Portfolio caches rebuilt from matching new Nasdaq ledgers, using each period's
  common intersection. These remain closed-trade overlays, not simultaneous
  shared-margin or floating-equity backtests.
- MT5 live process left untouched. No account, position, order or active profile
  was changed. Read-only HTTP verification after the GitHub push returned 200
  from the public Nasdaq page, but its text still specifies fixed 2.5R, no
  trailing and a 15:55 exit. Public-site deployment is pending, not complete.

Not claimed: clean out-of-sample validation, a completed Monte Carlo/FTMO pipeline
for this management, guaranteed risk cap, or readiness for immediate live use.
Known market-closed stop-modification retries are disclosed in README.md.
