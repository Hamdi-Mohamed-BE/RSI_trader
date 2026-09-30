# Nasdaq 5M — QUANT_LAB "Momentum v2.0" recreation vs current claude_eas (2026-09-25)

Source: the user's WhatsApp video (25 s, no audio) of "QUANT_LAB DE - Momentum v2.0" on NAS100.r M5. Frames show a
session-open momentum buy on Fri 18 Sep 2026 at 29543.71 (comment `SessOpenMom_`), a 0.60% initial stop, **no take
profit**, the stop trailed up to a slow moving average, the trade **held over the weekend** and closed Tue 22 Sep for
+8,870.78 USD on 100k. Research only — nothing installed, deployed or published. Full tables: `RESULTS.md`.

## What we built

Research copy of the production Nasdaq 5M DI EA (v2.10) with two default-off additions: a percent-of-price initial stop
and a slow-MA trailing stop. Parity: with them off it reproduced production exactly (190/190 trades, same net).
Variants (same entry rule in all — 09:30 NY M5 close vs EMA(12) + DI agreement):

- CURRENT — production DI EX5 + installed claude_eas SET: 4 ATR stop, 2.5R target, flat 15:55 NY.
- QL — recreation: 0.60% stop, no target, stop = EMA(200) M5 once +0.5R, held overnight/weekend.
- QL_ATR — same but trailing with our existing 6 ATR trail from +1R.
- WIDE — only the 0.60% stop (target and session close kept).

The MA period and +0.5R start are assumptions (not visible in the video), fixed before testing.
Smoke test 14–25 Sep 2026: QL reproduced the video trade (buy 18 Sep 29,545.25 → exit 22 Sep 30,465, ≈ +5.2R);
CURRENT was stopped out on the same entry (−1R). At ~$1/point/lot the video's 9.1 lots × 177-pt stop ≈ 1.6% risk,
so its +8.9% is about +5.2R, not +8.9R (depends on their contract size, not visible).

## Results (USTEC, windows ending 2026-09-25)

| Window | CURRENT | QL (video recreation) | QL_ATR | WIDE |
|---|---|---|---|---|
| 6m | +17.5%, PF 1.30, win 42%, DD 10.5% | **+23.0%, PF 1.65, win 51%, DD 8.0%** | +19.0%, PF 1.37, DD 6.6% | +24.9%, PF 1.53, DD 6.2% |
| 1y | +50.6%, PF 1.38, DD 10.9% | +38.0%, PF 1.49, DD 8.8% | **+55.5%, PF 1.48, DD 10.1%** | +41.2%, PF 1.40 |
| 3y | +133.6%, PF 1.29, DD 10.9% | +83.0%, PF 1.32, DD 17.3% | **+162.2%, PF 1.40, DD 10.1%** | +76.9%, PF 1.25, DD 19.4% |
| 5y | +180.2%, PF 1.22, DD **10.9%** | +81.4%, PF 1.18, DD **28.8%** | **+212.7%**, PF 1.29, DD **24.1%** | +104.7%, PF 1.18, DD 24.6% |

Streaks, holding time, overnight share, swap and best-trade multiples are in `RESULTS.md`.

## Conclusions

1. **The faithful recreation (QL) loses to the current version over 1y/3y/5y** (5y +81% vs +180%) with far larger
   drawdown (28.8% vs 10.9%); it only wins the last 6 months, which is the window a promotional video comes from.
2. **The slow-MA trail is the weak part.** Keeping the "wide stop, no target, hold overnight" idea but trailing with our
   ATR trail (QL_ATR) beat CURRENT on 1y/3y/5y returns and PF, with equal 1y/3y drawdown but **24% vs 11% 5y drawdown**
   and ~5× the swap cost; best trades reach 20×+ the median loss.
3. **A wider stop alone (WIDE) does not help** — it more than halves long-run returns and doubles drawdown.
4. QL_ATR was picked from 3 variants on these same years, so it is not validated. Next step if wanted: check it on the
   untouched USTEC 2019-09 → 2021-09 window and an FTMO equity-DD simulation (overnight/weekend holding and the larger
   5y drawdown matter for prop rules) before any promotion.
5. Pre-existing production behaviour found: when a session-end close falls while the market is closed (holidays/early
   closes), the EA retries the close on every tick until the reopen (identical counts in production and research runs).
   Harmless in the tester; live it could spam broker requests — worth a throttle in a future production update.

## Files

`run-config.json`, `run_n5ql.py` (compile | parity | main | summary), `make_report.py`, `EA/` (research source/EX5),
`native/PARITY.json`, `native/n5ql-*/` (SET, tester.ini, run.json, trades.json.gz, report .htm.gz, journal.txt.gz), `RESULTS.md`.
