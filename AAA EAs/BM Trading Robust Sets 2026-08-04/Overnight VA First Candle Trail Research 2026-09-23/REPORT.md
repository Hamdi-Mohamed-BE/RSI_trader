# Overnight value area — first M5 candle breakout with M5 candle trailing (raw, last year)

Date: 2026-09-23. Raw research only, no optimization. No production EA, SET, BAT, website cache or live chart changed.

## Rules tested (as confirmed by the user)

- Profile: 00:00 UTC (Asia open, Tokyo 09:00) to 09:30 New York. 64 bins, completed M1 candles weighted by broker
  tick volume at (H+L+C)/3, contiguous 70% value area. Same profile code as `Overnight Profile Raw Comparison 2026-09-19`
  except the start time (that study used 18:00 NY of the previous day).
- Version A (`first`): only the 09:30–09:35 NY M5 candle. Close above VAH = buy, below VAL = sell, inside = no trade.
- Version B (`anytime`): first M5 close outside the value area from 09:30 NY until 16:00 NY (or broker session end).
- Initial stop: opposite end of the signal candle, one tick beyond. No take-profit.
- Trailing: after every later closed M5 candle, stop moves to that candle's low (long) / high (short) ± one tick,
  only when tighter. If price is already through the new level, exit at market. No time exit.
- One position; weekdays only for entries. 1% of equity risk, lots rounded up to the broker step (minimum lot floor).

## Evidence type

Native MT5 Strategy Tester, isolated portable terminal `_Backtests/MT5-DMC-20260811`, profile "Calyx Research Empty",
`[Experts] Enabled=0`. Exness-MT5Trial16 demo contract specs, $10,000, 1:2000, Model=4 (every tick based on real
ticks), 150 ms delay, M5 chart, 2025-09-23 → 2026-09-23. History quality **72% real ticks** for all three symbols
(real ticks from 2026-01-01; earlier months generated from bars). EA `EA/Overnight VA Candle Trail.mq5`, compiled
0 errors / 0 warnings (EX5 SHA-256 b7f498509883…). All 6 runs exit 0 with fresh reports matching EA, symbol, dates
and entry mode. Metrics: `NATIVE_RESULTS.json`; ledgers `native/trades.json`; per-run journals and EA audit CSVs under `native/`.

## Results ($10,000, 1% risk)

| Asset | Version | Trades | Win % | PF | Return | Equity DD | Balance DD | Worst loss streak | Avg win / loss | Commission |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| XAUUSD | A first candle | 122 | 31.1 | 1.24 | +14.8% | 22.8% | 14.6% | 8 | $199 / −$72 | −$212 |
| XAUUSD | B any time | 244 | 32.8 | 1.32 | +38.7% | 25.6% | 20.4% | 12 | $197 / −$73 | −$342 |
| BTCUSD | A first candle | 119 | 26.9 | 1.30 | +23.5% | 18.8% | 15.6% | 14 | $318 / −$90 | −$733 |
| BTCUSD | B any time | 255 | 27.5 | 1.04 | +5.7% | 26.2% | 19.4% | 16 | $207 / −$75 | −$1,009 |
| US100 (USTEC) | A first candle | 150 | 30.7 | 0.93 | −5.9% | 18.4% | 17.6% | 11 | $157 / −$75 | −$458 |
| US100 (USTEC) | B any time | 255 | 28.6 | 0.85 | −17.1% | 31.6% | 28.5% | 17 | $136 / −$64 | −$579 |

Swap: $0 in every run. Median hold 6–9 minutes; longest hold about 1 hour; no position was held overnight
(the per-candle trail always closed trades within the session, so "no time exit" never mattered in this year).

EA audit (version A): first candle closed inside the value area on 136 (XAU), 142 (BTC), 106 (US100) of ~258 days.
Trailing-stop modifications rejected by broker distance: 0–2 per run (the previous stop stayed in place).
US100 had 2 entry orders rejected in each version.

## Findings

1. **Positive on gold and (version A) bitcoin, negative on US100.** Best: XAUUSD version B +38.7% (PF 1.32) and
   BTCUSD version A +23.5% (PF 1.30). US100 loses in both versions.
2. **This is a low win-rate, big-winner profile, not a high-win one.** Win rates 27–33%, average win ≈ 2.7–3.5×
   average loss, worst loss streaks 8–17. The per-candle trail exits most trades within minutes.
3. **Equity drawdown (18–32%) is far above what a prop account allows**, and is larger than balance drawdown because
   open winners give back profit before the trail catches up. At 1% risk a 12–17-loss streak alone uses most of a
   10% max-loss limit.
4. Version B doubles trade count. It helped gold but hurt BTC and US100.
5. BTC commissions are heavy: $733–$1,009 on $10,000 over the year.
6. Comparison: the earlier fixed-target overnight VA study (18:00 NY profile, stop beyond the opposite value-area
   edge, target overnight high/low) returned +22.3% on XAUUSD with 74% wins and 4.0% equity DD, and −6.4% on US100.
   Two things differ (profile start and exits), so the comparison is indicative only.

## Recommendation

**REVISE RAW RULES** for XAUUSD/BTCUSD, **SKIP** US100 in this form. The per-candle trail makes the edge thin and the
drawdown too deep. Worth testing next: start trailing only after +1R (or on M15 candles), or keep the fixed
overnight-high/low target and add the trail only after the first 1R. Validate any change on earlier years before use.

## Limitations

- One year; 28% of it uses generated ticks, which cannot reproduce the exact 09:30 fills or trailing behaviour.
- Stop placement one tick beyond the candle; real slippage on stop fills is not modeled beyond the 150 ms delay.
- 00:00 UTC is the chosen "Asia open"; other definitions (e.g. 18:00 NY) change the profile.
- Historical results are not a forecast.

## Follow-up 2026-09-23: exit variants (EA v1.10)

Same entries, same evidence type and settings as above. EA v1.10 adds three inputs whose defaults reproduce v1.00;
**parity confirmed**: v1.10 with defaults gave the identical 122 XAUUSD version-A trades (entry, exit, net P/L).
EX5 SHA-256 5e03fa277847…, 0 errors / 0 warnings. 18 new runs, all exit 0 with matching reports.

- **Trail after 1R**: M5 candle trail starts only after the best price since entry reached +1R. No target.
- **M15 trail**: trail on closed M15 candles from the start. No target.
- **Target + trail after 1R**: take-profit at the overnight (00:00 UTC–09:30 NY) high for longs / low for shorts,
  plus the M5 trail once +1R is reached. If the target is already behind the entry price the signal is skipped
  (XAU 22/45, BTC 14/46, US100 53/84 skips for A/B).

| Asset | Entry | Exit | Trades | Win % | PF | Return | Equity DD | Balance DD | Worst loss streak |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| XAUUSD | A | M5 trail (original) | 122 | 31.1 | 1.24 | +14.8% | 22.8% | 14.6% | 8 |
| XAUUSD | A | trail after 1R | 122 | 37.7 | 1.10 | +7.7% | 23.1% | 14.8% | 8 |
| XAUUSD | A | M15 trail | 122 | 28.7 | 0.90 | −7.5% | 26.5% | 18.3% | 11 |
| XAUUSD | A | **target + trail after 1R** | 100 | **54.0** | **1.55** | **+30.7%** | 14.2% | 7.7% | 7 |
| XAUUSD | B | M5 trail (original) | 244 | 32.8 | 1.32 | +38.7% | 25.6% | 20.4% | 12 |
| XAUUSD | B | trail after 1R | 244 | 43.0 | 1.33 | +57.9% | 21.7% | 16.7% | 11 |
| XAUUSD | B | M15 trail | 244 | 30.3 | 1.16 | +25.9% | 27.5% | 20.8% | 18 |
| XAUUSD | B | **target + trail after 1R** | 199 | **55.8** | **1.58** | **+70.2%** | 14.7% | 7.6% | 8 |
| BTCUSD | A | M5 trail (original) | 119 | 26.9 | 1.30 | +23.5% | 18.8% | 15.6% | 14 |
| BTCUSD | A | trail after 1R | 119 | 31.1 | 1.24 | +21.5% | 20.4% | 16.4% | 9 |
| BTCUSD | A | M15 trail | 119 | 26.9 | 1.16 | +14.4% | 25.2% | 18.4% | 9 |
| BTCUSD | A | target + trail after 1R | 105 | 46.7 | 1.18 | +11.4% | 17.7% | 14.0% | 7 |
| BTCUSD | B | M5 trail (original) | 255 | 27.5 | 1.04 | +5.7% | 26.2% | 19.4% | 16 |
| BTCUSD | B | trail after 1R | 255 | 35.7 | 1.01 | +2.5% | 25.9% | 22.9% | 12 |
| BTCUSD | B | M15 trail | 255 | 28.6 | 1.01 | +1.0% | 33.6% | 24.4% | 13 |
| BTCUSD | B | target + trail after 1R | 209 | 50.2 | 1.06 | +7.7% | 14.1% | 13.5% | 5 |
| US100 | A | M5 trail (original) | 150 | 30.7 | 0.93 | −5.9% | 18.4% | 17.6% | 11 |
| US100 | A | trail after 1R | 150 | 38.7 | 0.91 | −8.4% | 20.1% | 19.3% | 10 |
| US100 | A | M15 trail | 150 | 33.3 | 0.91 | −7.9% | 22.8% | 19.2% | 10 |
| US100 | A | target + trail after 1R | 97 | 44.3 | 0.37 | −32.8% | 35.0% | 34.2% | 12 |
| US100 | B | M5 trail (original) | 255 | 28.6 | 0.85 | −17.1% | 31.6% | 28.5% | 17 |
| US100 | B | trail after 1R | 255 | 36.9 | 0.80 | −29.0% | 40.0% | 36.9% | 15 |
| US100 | B | M15 trail | 255 | 28.6 | 0.73 | −35.3% | 46.3% | 44.0% | 15 |
| US100 | B | target + trail after 1R | 171 | 49.1 | 0.50 | −38.5% | 41.7% | 40.5% | 15 |

No position was held more than a day (longest 11.9 h). Swap $0 everywhere.

### Follow-up findings

1. **Gold with the overnight high/low target plus trail-after-1R is the clear best**: 54–56% win rate, PF 1.55–1.58,
   balance DD 7.6–7.7%, worst loss streak 7–8. Version B: +70.2% on 199 trades.
2. The target turns the strategy into a higher-win profile on gold and BTC, but on US100 the overnight extreme is
   usually too close (avg win $43–45 vs avg loss $88–95), so US100 gets much worse. **US100: SKIP.**
3. Delaying the trail until +1R helped gold version B only; M15 trailing was worse almost everywhere.
4. BTC: the original M5 trail on version A (+23.5%) remains its best; BTC has no strong exit variant.
5. **Equity DD (14–15% for the best gold variants) is still about double balance DD** because open trades give back
   profit before the target/trail; average losses ($120–136) exceed the 1% ($100) plan because of stop slippage,
   gold's daily trading break (60 "market closed" journal lines in version B) and rounding up to the lot step.
6. Selection warning: 4 exit variants × 2 entries × 3 assets = 24 configurations, all chosen and judged on the same
   year after the first results were seen. The best one is an in-sample pick, not validation.

### Next step before any use

Run the gold "target + trail after 1R" (A and B) on 2021-09 → 2025-09 native, a period not used for any of these
choices, and check equity DD against the prop limits at 0.5% risk as well as 1%.

## 2026-09-24: "Gold Overnight IVB" on the website windows (decision input)

User-proposed name for XAUUSD, entry B, target + trail after 1R. Same native settings; windows copied from the website's
gold-overnight-value-area cache (end 2026-09-19 exclusive). Runner `run_native.py website`; summary
`website_summary.py` → `WEBSITE_PERIOD_RESULTS.json`. Note: the 1y run reused the folder name of the earlier
2025-09-23→2026-09-23 run and replaced it; that earlier run's figures remain in the table above. EX5 rebuilt from the
unchanged v1.10 source (SHA-256 25442085a9a8…; MetaEditor output is not byte-deterministic across builds).

| Window | IVB trades | Win % | PF | Return | Equity DD | Balance DD | Win / loss streak | Real ticks | Gold VA (website): win / PF / return / DD |
|---|---:|---:|---:|---:|---:|---:|---|---|---|
| 6m | 101 | 52.5 | 1.69 | +47.4% | 10.9% | 7.6% | 5 / 8 | 100% | 71.0% / 1.52 / +9.4% / 4.0% |
| 1y | 198 | 55.6 | 1.56 | +69.1% | 14.7% | 7.6% | 7 / 8 | 71% | 74.0% / 1.56 / +22.3% / 4.0% |
| 3y | 600 | 48.8 | 1.15 | +44.3% | 26.8% | 25.7% | 8 / 8 | 23% | 69.2% / 1.15 / +18.4% / 11.8% |
| 5y | 1020 | 45.4 | **0.84** | **−43.4%** | **72.3%** | 71.9% | 8 / 11 | 14% | 68.4% / 1.04 / +9.1% / 28.9% |

IVB net by calendar year (5y run, USD): 2021 (from Sep) −1,729; 2022 −3,396; 2023 −1,276; 2024 −449; 2025 +167;
2026 YTD +2,342. Minimum equity in the 5y run: $2,794.

**Decision input: do not promote.** The edge exists only in roughly the last 12–18 months; 2021–2024 lose every year.
Earlier years use bar-generated ticks, which matters for 5-minute stops, but the existing Gold Value Area product ran
on the same data and stayed positive over 5y, so data quality alone does not explain a four-year losing run.
Recommendation: **WATCH ONLY / REVISE RAW RULES**. Not added to BATs, installer or website.

## 2026-09-24: rule revision attempt (EA v1.20) — failed

Diagnosis from the 5y ledger: 2021-09→2024-09 lost in every entry-time bucket and on both sides; 2024-09→2026-09 won.
Hypothesis: the breakout needs a trending gold regime. Four regime filters were fixed before testing
(`run-config.json` → `revision`): R1 D1 close vs D1 EMA50 direction; R2 D1 ADX(14) ≥ 20; R3 = R1+R2; R4 = R1 + ADX ≥ 25.
Selection on development 2021-09-19→2024-09-19 only; holdout 2024-09-19→2026-09-19. One native 5y run per candidate
(EX5 SHA-256 aaa4e55ae51a…); window metrics are recompounded slices of those native ledgers (`revision_summary.py`,
`REVISION_RESULTS.json`). Parity: v1.20 with filters off reproduced all 1,020 v1.10 trades exactly.

| Candidate | Dev trades | Dev win % | Dev PF | Dev return | Dev bal. DD | Holdout trades | Holdout PF | Holdout return | 5y native return / equity DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| none (IVB) | 621 | 41.1 | 0.65 | −68.7% | 71.9% | 399 | 1.34 | +81.1% | −43.4% / 72.3% |
| R1 trend | 323 | 42.7 | 0.68 | −42.0% | 51.1% | 201 | 1.35 | +40.3% | −18.6% / 53.2% |
| R2 ADX≥20 | 498 | 41.0 | 0.63 | −63.3% | 63.6% | 360 | 1.30 | +66.0% | −39.0% / 66.5% |
| R3 trend+ADX≥20 | 248 | 44.4 | 0.71 | −31.2% | 40.3% | 179 | 1.35 | +35.6% | −6.8% / 42.8% |
| R4 trend+ADX≥25 | 199 | 46.2 | 0.77 | −20.9% | 30.6% | 150 | 1.35 | +26.7% | +0.2% / 33.4% |

The pre-set rule selects R1, but no candidate has a development PF above 1. The filters reduce losses without creating
an edge in 2021–2024. **Decision: SKIP Gold Overnight IVB.** Not added to BATs, installer or website.
