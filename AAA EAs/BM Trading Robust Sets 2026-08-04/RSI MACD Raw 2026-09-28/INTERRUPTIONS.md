# Execution interruption log

1. XAU A_pullback 6m, started 2026-09-28 14:57:58 UTC. A long wall-clock gap
   occurred during execution. The native journal then reported shutdown and the
   tester being forced to close. The resulting report had blank expert/symbol/input
   fields, 1970 dates, and no valid results. The runner correctly rejected it on
   input verification. Windows System events later confirmed sleep for the reason
   `Battery`, from 14:58:20 UTC to 15:08:52 UTC. No power settings were changed.
   The same frozen XAU case succeeded on retry (64 trades). All earlier
   44 main runs and four smoke runs are intact and independently audited.
   Archived under `interrupted/XAU-A_pullback-6m-20260928T1509/`; excluded from
   all performance tables. Retry uses exactly the same frozen EA and parameters.

This is one additional attempted execution, not an extra strategy configuration.
