# Previous-day value area re-entry ("80% rule") — XAUUSD raw native test (2026-09-24)

Research only. Nothing deployed; no BAT, installer or website change.

## Rules (user description, with disclosed assumptions)

- Previous UTC calendar day profile: M1 (H+L+C)/3 × broker tick volume, 64 bins, contiguous 70% value area.
  Monday's "previous day" is Sunday, which has too few gold bars (< 300), so **Mondays are skipped**
  (1,030 profiles on 1,299 weekdays). A Friday-profile rule for Mondays would be a separate variant.
- Setup: today's first price (first tick after 00:00 UTC) is above VAH or below VAL (426 days).
- Trigger ("close back inside with strong conviction"): a completed candle closes strictly inside the value area,
  body ≥ 50% of its range, body pointing back into the area. First trigger only; one trade per day.
- Trade toward the opposite edge: opened above → sell, target VAL; opened below → buy, target VAH.
  Stop one tick beyond the trigger candle's high/low. Entries until 18:00 UTC; flat at 20:45 UTC or 1 minute before
  the broker session ends.
- "Works best on ranging markets": optional filter last completed D1 ADX(14) < 20.
- 1% equity risk, lots rounded up to the broker step.

## Evidence type

Native MT5 Strategy Tester, isolated terminal `_Backtests/MT5-DMC-20260811`, profile "Calyx Research Empty",
`[Experts] Enabled=0`, Exness-MT5Trial16 demo XAUUSD, $10,000, 1:2000, Model=4, 150 ms delay,
2021-09-19 → 2026-09-19 (end exclusive). History quality **14% real ticks** (real ticks from 2026-01-01).
EA `EA/Prior Day VA Reentry.mq5` (EX5 SHA-256 6c9a2d0272c0…, 0 errors / 0 warnings). One native 5y run per
variant; all exit 0 with matching reports and clean journals. **6m / 1y / 3y are slices of each native 5y ledger,
recompounded from $10,000** (`summarize.py`, `RESULTS.json`).

## Results

| Variant | 5y trades | Win % | 5y PF | 5y return | 5y equity DD | 3y PF / return | 1y PF / return (trades) | 6m PF / return | Best win / worst loss streak |
|---|---:|---:|---:|---:|---:|---|---|---|---|
| **M30 trigger** | 280 | 32.1 | 1.07 | +10.5% | 41.2% | 1.54 / +62.1% | 2.32 / +43.1% (53) | 3.55 / +42.5% | 6 / 11 |
| M30 + ADX < 20 | 48 | 25.0 | 0.78 | −7.6% | 18.6% | 1.49 / +6.9% | 7.33 / +7.7% (2) | 7.33 / +7.7% | 2 / 8 |
| M15 trigger | 293 | 25.6 | 0.76 | −37.5% | 56.3% | 0.99 / −1.7% | 1.67 / +29.4% (56) | 1.91 / +22.2% | 4 / 14 |
| M15 + ADX < 20 | 51 | 21.6 | 0.72 | −10.8% | 23.1% | 1.00 / 0.0% | 9.16 / +9.1% (2) | 9.16 / +9.1% | 2 / 10 |

Commission: M30 −$379, M15 −$447 over 5y; swap $0 (all trades close the same day).

## Findings

1. **It is not an 80% win-rate strategy in this form**: 22–32% wins. Targets (opposite value-area edge) are far and
   the trigger-candle stop is tight, so wins are large and rare. The "80%" in the classic rule refers to price
   *reaching* the other side, not to a trade with a tight stop winning.
2. **M30 is profitable over 5y (+10.5%) but with a 41% equity drawdown**; almost all of the gain is in the last
   3 years (+62%), so 2021–2023 lost heavily. M15 loses over 5y.
3. The **ranging-market filter (daily ADX < 20) removes ~83% of trades and turns both versions negative** in this data.
4. Not suitable for a prop account as tested (drawdown, 11–14-loss streaks).

## Recommendation

**REVISE RAW RULES** before any pipeline: test a wider, structure-based stop (beyond today's extreme outside the value
area) that matches the classic rule's "price traverses the value area" logic, and a Monday rule using Friday's
profile. Choose any revision on 2021-09 → 2024-09 only and check it on the later period.
Historical results are not a forecast.
