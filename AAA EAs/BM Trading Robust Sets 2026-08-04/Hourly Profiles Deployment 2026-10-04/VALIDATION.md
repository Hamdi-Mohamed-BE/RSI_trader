# Validation record — 4 October 2026

- v1.11 source and compiled EX5 fingerprints: `RELEASE.json`.
- Native MetaEditor: **0 errors, 0 warnings**.
- Four isolated native Model 4 smoke tests, 28 September–3 October exclusive:
  US30/US100 × 0.5% balance/fixed $50. All produced entries and no account failure.
  Final build used 0.08 US30 lots and 0.13 US100 lots on this Exness test broker.
  `FUNCTIONAL.json` binds the exact EX5 to archived reports and inputs. This short
  smoke test checks operation/sizing, not profitability or long-history robustness.
- Archived pre-correction `hoursized-20261004-*` smoke runs used upward rounding;
  only `hoursized-v111-20261004-*` validates the shipped build.
- Pure PowerShell tests: 20 mode/risk cases passed; all five normal launcher modes
  expose 37 items; separate Ava policy remains eight and FTMO remains unchanged.
- Installer `-ValidateOnly`: all 37 source/SET paths checked. No active terminal,
  charts, account settings or orders changed.
- Focused website/installer/news-placement/admission tests: 108 passed, 10
  unrelated legacy assertions deselected; four current-build deployment tests
  also passed, including native smoke fingerprints.
- Full existing website suite is **not green**: 293 passed, 31 failed, one skipped
  at the last complete run. Failures include older news compatibility fingerprints,
  native cache coverage/count mismatches, old BAT version text, and old website
  period/ranking assertions. These are not silently waived or described as a full
  successful validation. They require a separate evidence/cache cleanup.
- Local web server was reloaded; `/api/health` reports 37 installed/available,
  35 licensed-for-sale and two experimental. Both recent detail routes return 200
  and clearly identify original fixed-one-lot benchmark results.
- Original frozen hourly MQ5/EX5 and all original website native ledgers/caches
  are unchanged. Existing shared-portfolio evidence remains labelled archived
  and excludes the additions. The FTMO comparison is an exploratory replay only.
