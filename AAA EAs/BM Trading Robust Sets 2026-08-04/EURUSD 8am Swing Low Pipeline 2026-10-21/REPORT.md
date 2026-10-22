# EURUSD 8am swing low — full pipeline REPORT (exploratory override, 2026-10-21)

**Verdict: REJECTED for both sessions at the plateau stage. There is no robust "best approach" to promote.**
Run as an owner-requested exploratory override after the raw gate failed (PLAN.md). Generated tables: TABLES.md; every tested
configuration: SEARCH RESULTS.json (699 configurations); parity: PARITY.json; plateau: PLATEAU-*.json; diagnostic: DIAGNOSTIC.json.

## What was done
- **Parity first:** the case-table engine reproduced the raw study's native Model 4 5-year ledgers exactly (L8 100/100,
  NY8 130/130, SHORT_NY8 159/159 trades; 0 mismatches; identical cash).
- **Staged search:** London and New York separately, development 2016-10-17 → 2023-10-17 (7 years; 2016–21 never viewed),
  native MT5 Model 1, 150 ms, $10k, 1%, top 3 carried per stage.
  - Stages: swing definition/timeframe 72 → entry 12 → stop 27 → management 24 → exit 87 → anchor time 18 → direction 9 → filters 33.
  - Plateau grids: 81 London + 54 New York.
  - Every pass reconciled to the optimizer's profit; no failed entries.
- **Plateau rule** (frozen): ≥ 70% of the ±1-step neighbours profitable AND median neighbour PF ≥ 1.05.

## Best development configurations and their plateau
| Track | Best development configuration | Dev PF / trades / per month / return / closed DD | Profitable neighbours | Median neighbour PF | Plateau |
|---|---|---|---|---|---|
| London 1 | 08:00 London, M30 2-bar pivot within 4 bars, lower low, long, stop-entry above last M30 high, stop pivot − 0.5 ATR, 4 h exit, skip Friday | 1.65 / 174 / 2.07 / +61.9% / 6.9% | 52% | 1.00 | FAIL |
| London 2 | same + 2 ATR trail from 0.5R, skip Mon+Fri | 1.99 / 127 / 1.51 / +52.9% / 6.0% | 44% | 0.91 | FAIL |
| London 3 | same + 2 ATR trail from 0.5R, skip Friday | 1.72 / 174 / 2.07 / +56.9% / 6.5% | 56% | 1.01 | FAIL |
| New York 1 | 08:00 New York, H1 2-bar pivot confirmed at 08:00, lower low, long, limit 0.25 ATR below, stop pivot − 0.1 ATR, 4 h exit, ATR below median | 1.82 / 77 / 0.92 / +48.5% / 9.1% | 33% | 0.90 | FAIL |
| New York 2 | same, stop at pivot, no filter | 1.59 / 122 / 1.45 / +53.2% / 10.9% | 28% | 0.80 | FAIL |
| New York 3 | same, stop pivot − 0.1 ATR, no filter | 1.60 / 122 / 1.45 / +50.7% / 11.1% | 28% | 0.83 | FAIL |
Small changes (freshness window ±1 step, exit ±1 step, start time ±30 min) turn each into a break-even or losing setting.

## What each dimension showed (development; full side-by-side tables in TABLES.md)
- **Exit:** a 4 h time exit was best on both tracks. Every fixed target from 0.5R to 3R was about break-even (PF 0.85–1.06).
- **Anchor:** 08:00 local was best on both tracks; 07:00 and 09:00 were clearly worse (London PF 1.20 / 1.03 vs 1.49).
- **Direction:** long after a fresh low was best. Short after a fresh high was weak (London PF 1.08) and "both" added nothing.
- **Management:** break-even and trailing did not improve the best versions.
- **Filters:** H1 EMA200 / EMA50-slope trend filters hurt (London PF 0.94 / 1.01). Day-of-week skips and the ATR regime raised
  development PF but cut the trade count. These are the kinds of fits the plateau test rejected.

## POST-REJECTION DIAGNOSTIC (labelled; changes no decision) — the six rejected finalists, Model 4
| Finalist | Validation 2023-24: trades / return / PF | OOS 2024-26: trades / per month / return / PF / equity DD |
|---|---|---|
| London 1 | 28 / −5.0% / 0.66 | 61 / 2.54 / −12.7% / 0.51 / 13.2% |
| London 2 | 23 / −3.6% / 0.66 | 49 / 2.04 / −13.6% / 0.29 / 14.5% |
| London 3 | 28 / −7.0% / 0.50 | 61 / 2.54 / −12.5% / 0.47 / 13.0% |
| New York 1 | 12 / +17.1% / 4.50 | 23 / 0.96 / −15.1% / 0.10 / 16.0% |
| New York 2 | 16 / +13.8% / 2.64 | 30 / 1.25 / −9.9% / 0.53 / 11.5% |
| New York 3 | 16 / +15.4% / 3.12 | 30 / 1.25 / −10.8% / 0.48 / 11.9% |
Every finalist loses in the last two years. The plateau gate rejected them correctly.

## Not done (by the frozen plan)
No validation pick, OOS gate or Monte Carlo: nothing survived the plateau. Stage 6 applies only to a frozen survivor.
Deflated Sharpe at 699 configurations would penalise the development results further.

## Limits
Generated ticks before 2026; Model 1 screen (finalists re-checked in Model 4 only in the diagnostic); Exness Trial16 costs.
The validation/OOS windows were already seen in the raw study (labelled retrospective). Nothing installed, no SET/BAT/live
change, no push.
