# VWAP & EMA reel raw study 2026-10-26 — REJECTED at the raw gate

**Owner request:** "back test this one". The reel: short when the close is below VWAP and EMA, exit when it closes
above both; the long side mirrors it.
- **Rules:** frozen in `RULES.md`, with assumptions A1–A7:
  - EMA 20;
  - session VWAP from 09:30 New York;
  - intraday, flat at 15:55 NY;
  - 2 ATR emergency stop;
  - 1% risk.
- **Runs:** 64 native Model-4 runs (USTEC, US500, US30, XAUUSD on M5 and M15; 6m / 1y / 3y / 5y windows plus 5-year
  controls and sensitivities), end 2026-10-26.
- **Data:** `SUMMARY.json`.

## Result (5 years; trades / month in brackets)

| Symbol | M5 | M15 |
|---|---|---|
| USTEC | −93.7%, PF 0.93 (121) | −12.4%, PF 0.99 (68) |
| US500 | −100.0%, PF 0.79 (68; account wiped) | −78.6%, PF 0.91 (69) |
| US30 | −100.0%, PF 0.82 (73; wiped) | −77.0%, PF 0.90 (69) |
| XAUUSD | −71.7%, PF 0.96 (113) | −7.0%, PF 0.99 (61) |

- **3 years:** every version also loses (−18% to −94%).
- **Win rate:** 21–34%. The always-in, reversing design pays the spread on 60–120 trades a month.
- **Controls:** VWAP-only and EMA-only lose about as much (PF 0.65–0.98). The combination does not add an edge.
- **Sensitivities:**
  - EMA 50 on M15 is the only positive result: XAU +64.9% (PF 1.04), USTEC +38.8% (PF 1.02).
  - Both are post hoc and far below the PF 1.15 gate.
  - EMA 9 is worse.
- **Raw gate:** FAIL for all 8 symbol / timeframe versions. No optimisation.

## Disclosures
- **Positions held past the flat time:** on index CFDs about 1.5% of trades (47–88 in 5 years) stayed open after the
  15:55 NY flat, because the tester's market was already closed ("market closed" close failures on early-close and
  holiday sessions).
  - Those trades netted **positive**. Removing them lowers every PF (for example USTEC M15 0.99 → 0.92), so they do not
    explain the failure.
- **Ticks:** real from 2026-01-01; earlier ticks are generated.
- **Volume:** CFD tick volume stands in for futures volume, which the reel says VWAP needs.

Nothing installed, nothing pushed.
