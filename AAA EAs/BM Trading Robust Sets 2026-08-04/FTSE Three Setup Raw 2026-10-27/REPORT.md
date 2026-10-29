# FTSE 100 three-setup bot raw study 2026-10-27 — only S2 (Monday dip) passes; the clip's bot FAILS

**Owner request:** "backtest and re-create this EA and show me its raw results". The pasted clip describes a UK 100 bot
with three setups and claims "+313% since 2017".

- **Rules:** frozen in `RULES.md` before testing. Gaps (S3 slope / distance, RSI / ATR periods) are filled with
  declared defaults; stops, 2R and 24 h come from the same bot's 2026-10-19 clip.
- **Runs:** 27 native MT5 Model-4 runs on Exness UK100 H1, 150 ms, $10,000, 0.75% equity risk, end 2026-10-27:
  - S1, S2, S3 and ALL over 6m / 1y / 3y / 5y / MAX (from 2019-08; the tester has no UK100 history before mid-2019,
    so "since 2017" cannot be tested);
  - 7 controls on 5y.
- **Data:** full tables in `RESULTS.md`, data in `RESULTS.json`, chart in `balance.png`.

## Results (trades / month in brackets)
| Version | 6m | 1y | 3y | 5y | MAX (2019-08 →) | Gate |
|---|---|---|---|---|---|---|
| S1 panic drop (long) | +5.6%, PF 1.35 (7.3) | +3.8%, PF 1.10 | +5.5%, PF 1.05 | −15.3%, PF 0.92 (8.5) | −34.4%, PF 0.86 | FAIL |
| **S2 Monday dip (long)** | +6.4%, PF 4.54 (2.2) | +12.7%, PF 3.51 | +20.5%, PF 1.91 | **+13.7%, PF 1.34 (2.1)** | +17.8%, PF 1.28 | **PASS** |
| S3 trend pullback (long + short) | +4.5%, PF 1.17 (10.6) | +5.6%, PF 1.12 | +1.2%, PF 1.01 | −16.0%, PF 0.93 (10.6) | −47.8%, PF 0.82 | FAIL |
| **ALL three (the clip's bot)** | +17.1%, PF 1.37 (20.1) | +22.4%, PF 1.24 | +26.7%, PF 1.09 | **−20.8%, PF 0.94 (21.2)** | **−61.0%, PF 0.84** | **FAIL** |

- **Win rates over 5y:**
  - S1 41% (clip 44%).
  - S2 51% (clip 54%).
  - S3 41%. It has 5× S2's trades (clip: about 3×).
- **Drawdowns:**
  - Equity DD (relative), 5y: S2 10.1%, ALL 52.1%.
  - Over MAX: ALL 76.5%.
- **Which setup carries it:** only S2 makes money. Over 5y S1 loses $1,528 and S3 loses $1,597 while S2 earns $1,367.
  The clip's 38% (S3) / 25% (S2) profit split is not reproduced.
- **S3 direction:** shorts helped in the last 6–12 months but lost over 3y; both directions lose over MAX.
- **Calendar years:** ALL lost in 2019–2024 (−7% to −31% a year) and gained only in 2025 (+3%) and 2026 (+38%). The
  recent-window profits are a regime effect, not a stable edge.
- **Controls (5y):**
  - random long PF 0.73;
  - random direction PF 0.75;
  - S2 on Tuesday–Friday PF 0.85.
  - The rules beat random, but only S2 is profitable. Monday clearly matters for S2.

## S2 (Monday dip) caveats
- **When it made its money:** 2020–2023 was flat to negative (+7%, −1%, −1%, −5%); this window was viewed in the
  2026-10-19 study. Most of the profit is from 2024–2026, including +14% in 2026 (PF 6.1, 21 trades).
  4 of 8 calendar years positive.
- **Sample size:** small, 2.1 trades a month.
- **Best-day check:** passes. 5y net without the 5 best days is +$596.
- **Exits over 5y:** 16 hit TP, 47 hit SL and 64 closed at 24 h. Half the trades end on the time exit, so the 2R target
  is rarely reached.

## Disclosures
- **Ticks:** real UK100 ticks start 2026-01-02. Earlier windows use MT5-generated ticks from M1 bars.
- **Skipped entries:** 24–40 entries per 5y run were refused with "market closed" (signal on the Friday 20:00 bar after
  the cash close) and skipped. S1 / S3 also had 2 invalid-stops refusals. Neither affects the S2 verdict.
- **Assumptions (ours):** the 24 h exit and stop sizes come from the earlier clip. The S3 rules ("pointing up" =
  SMA100 above its value 5 bars earlier; "well under" = 1.5 ATR) are our reading. Other readings were not tested.
- **Next step:** stage 5 (optimisation) only if the owner asks, and only for S2.

Nothing installed, deployed or pushed.
