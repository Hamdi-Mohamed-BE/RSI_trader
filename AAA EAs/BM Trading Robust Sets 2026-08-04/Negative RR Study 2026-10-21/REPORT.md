# Negative RR Study 2026-10-21 — REPORT

**Question (owner):** set every Current14 ORB05 EA that uses ≥ 1R to a 0.75R / 0.60R / 0.50R take-profit (EAs already
below 1R unchanged). Faster / better prop pass? Monthly income once funded?

**Verdict: REJECTED at every level.** Lower targets raise win rates for every EA but cut expectancy for 9 of 10 changed
EAs; the Best Prop 9 prop portfolio gets funded less often and much more slowly, and funded income falls by half or more.
Keep the current targets. Full generated tables: FINAL.md, STANDALONE.md. Plan + corrections: PLAN.md.

## Evidence and gates
- 44 native MT5 Model-4 runs (isolated tester `_Backtests/MT5-DMC-20260811`, 150 ms, $10k, 1%, 2021-10-06 → 2026-10-06):
  11 fresh baselines + 33 target variants; 0 failures; every variant differs from its baseline (all overrides active).
- Parity: two stored baselines re-run → USDJPY identical; all 10 fresh baselines have identical entries/exits/exit reasons
  to the stored ones (BASELINE-CHECK.json). Cash differs 0–2.3% because the tester's swap specification refreshed since
  2026-10-08, so variants are compared with FRESH baselines. Prop driver: stored baseline reproduces the Best Prop retest
  OOS challenge, the First Payout e2e / e2e MC and the LOWRISK income results exactly.
- Correction found before analysis: USDJPY's current exit is a 16:00 London TIME EXIT (InpTargetMode=0), not 1R; the
  first USDJPY runs had no effect, were kept as *.INVALID-time-exit-mode and re-run with InpTargetMode=1.
- 3-Way Gold: tester-only TP accessor override for all three modules (behaviour-neutral at 0, verified).

## Prop — Best Prop 9, $10k, DI OFF, recorded costs (FINAL.md has stress)
| Target | OOS starts: pass ≤180 d | funded ≤90 d | median days funded | All starts: pass ≤180 d | MC: funded | MC: first payout | median days to payout | median payout | Trades / month | / day |
|---|---|---|---|---|---|---|---|---|---|---|
| Current | 90% | 69% | 64 | 61% | 57% | 49% | 88 | $245 | 11.9 | 0.55 |
| 0.75R | 94% | 37% | 95 | 37% | 31% | 26% | 124 | $89 | 17.5 | 0.80 |
| 0.60R | 92% | 36% | 99 | 40% | 30% | 25% | 124 | $87 | 19.1 | 0.88 |
| 0.50R | 78% | 14% | 126.5 | 33% | 20% | 16% | 134 | $77 | 21.5 | 0.99 |

## Funded $100k, Monte Carlo 36 months, recorded (re-baseline after every reward assumed)
| Target | 1%: monthly while trading | 1%: median days | 1%: total median / mean | 0.5%: monthly | 0.5%: median days | 0.5%: total median / mean | 0.5%: trades / month / day |
|---|---|---|---|---|---|---|---|
| Current | $5,109 | 79 | $11,148 / $18,859 | $2,209 | 532 | $37,322 / $42,671 | 43.4 / 2.00 |
| 0.75R | $2,388 | 86 | $5,502 / $9,378 | $828 | 401 | $9,958 / $13,174 | 44.2 / 2.03 |
| 0.60R | $2,144 | 96 | $5,614 / $9,453 | $739 | 383 | $8,717 / $11,548 | 44.5 / 2.05 |
| 0.50R | $1,777 | 93 | $4,229 / $7,369 | $586 | 352 | $5,854 / $8,432 | 44.7 / 2.06 |
0% breaches everywhere; accounts end by freezing at the 92% buffer.

## Standalone (5 years, native) — return / average R per trade
Nasdaq 5M DI ON +215% / 0.138R → 0.75R −7% / −0.003R, 0.50R −22%; DI OFF +145% → −27% to −40%. USDJPY +148% → +34% / +22% /
+9%. Month End Flow +39% → +8% / +3% / −3%. Squeeze +42% → +19% / +14% / +7%. EMA3 +65% → +53% / +51% / +38%. 3-Way Gold
+106% → +66% / +70% / +65%. DMC Current +16% → +11% / −16% / −19% (DD 36% → 16% at 0.75R). DMC Fresh +9.7% → +8.8% / +4.2% /
+7.0%. Nasdaq Overnight +8.1% → +7.4% / +6.9% / +3.9%. Only Gold Overnight improved: +9.6% → +18.6% / +13.0% / +7.2%.

## Side result — DI ON funded income (owner asked for the best approach)
Stored DI ON stream (same tester state as the stored DI OFF LOWRISK results), $100k, MC 36 months, recorded:
0.5%: $2,267/month while trading, median 835 days, 41% still trading at 36 m, total $58,103 median / $54,185 mean,
39.0 trades/month, 1.79/day (DI OFF 0.5%: $2,203, 532 d, $37,026 / $42,479). 1%: $4,841/month, 105 d, $14,652 / $23,621.
History 12 m, 0.5%: $2,488/month (development starts $1,517, OOS starts $3,636), 0% breach.

## Limitations
In-sample (the portfolio and prior settings were chosen on this history); older ticks generated (real from 2026-01-01);
Python replay of native signals for the prop part; FTMO post-reward handling assumed (balance back to 100k, guard
re-baselined manually — the as-built guard blocks entries after the first reward). Not a forecast. Nothing installed,
no SET/BAT/guard/live change, no push.
