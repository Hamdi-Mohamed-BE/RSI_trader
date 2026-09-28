# Release validation

- Five distributed ORB EA sources were compared with the pre-change commit; only the shared comment include and order-comment expression changed.
- Five ordinary/Ava/export builds and two guarded FTMO builds compiled with zero errors and zero warnings.
- Thirteen native MQL formatter cases passed in the isolated tester, with no orders submitted. They cover all seven current ORB labels and length/variant/profile/session edge cases.
- The focused ORB, Nasdaq DI, Nasdaq wider-stop/ATR, standalone news-risk and adaptive-news suite passed: **61 tests**.
- FTMO risk settings, account locks, all thirteen SET input maps, eleven non-ORB binaries and the guard hash are unchanged. Package checksums reconcile.
- The full website test suite completed with **146 passed, 7 failed**. The seven failures are in the unchanged `test_store.py` catalogue/cache expectations (33 versus 34 products, logic-card counts, asset counts, five-year wording and absent cached Sharpe/recovery fields). No website catalogue, templates, cached results or historical trades were changed in this release. These unrelated failures remain; this is not a claim that the full suite is green.
- The previous Nasdaq DI-choice and standalone-news-risk regression checks passed within that run. FTMO News remains OFF.

No live installation/restart was performed. New comments require loading the rebuilt EAs through the normal safe deployment workflow. The existing positions shown in the user's screenshot keep their original comments.
