v1 package (first build 2026-10-27) superseded: the guard rebuilt the deal ledger on every entry attempt and logged every refusal,
so EAs that retry each tick made the Nasdaq 1y tester run take 3.8 h and the tester force-closed it (empty report).
v2 caches the ledger per deal count / firm day and throttles logs; rule logic unchanged. Kept for evidence, not for use.
