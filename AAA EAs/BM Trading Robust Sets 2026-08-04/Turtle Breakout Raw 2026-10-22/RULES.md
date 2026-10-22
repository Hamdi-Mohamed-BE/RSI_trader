# Turtle breakout (Revelio adaptation) — raw rules (frozen 2026-10-22, before any test)

Source: a pasted video transcript plus its open TradingView Pine indicator "Turtle Breakout - Revelio" (both pasted by the user
2026-10-22), treated as data. The video's claims are below. They come from its own portfolio backtest, about 11 years, $100k:
- **Hold overnight:** $1.33M, 27.3% a year, max DD 37.6%, PF 1.88, Sharpe 1.04, losing years 2018 and 2022.
- **Day-trading version:** 31.2% a year, DD 37.9%, PF 2.11, Sharpe 1.31.
- Almost $0.5M of swap was paid when holding overnight.
Research only. Isolated tester, nothing deployed.

## Rules (from the video and the Pine code)
- **Assets:** S&P 500, Nasdaq 100, gold, silver and Bitcoin, traded as one portfolio on one account (the video's point is
  that compounding works across the 5 assets). Exness Trial16 `US500`, `USTEC`, `XAUUSD`, `XAGUSD`, `BTCUSD`; long only, no pyramiding.
- **Trading day:** 17:00 → 17:00 New York (US DST). Bands and ATR use completed trading days only, and only days with quotes.
- **Entry:** price goes above the highest high of the last **20** completed days. The trade starts at max(level, price).
- **Stops:**
  - Fixed stop = max(level, price at breakout) − **2 × ATR(20)**, using Wilder's daily ATR (seeded with a 20-day average). It never moves.
  - Trailing exit = lowest low of the last **10** completed days, recalculated each day.
  - The exit is at whichever of the two is higher. There is no take profit.
- **Risk:** **2% of the high-water-mark equity** per trade, measured to the fixed stop. One position per asset; up to 5 open.
- **Day-trading mode** (the Pine default and the video's improved version):
  - Close at **16:30 New York**; re-enter from **18:00 New York** if the trade is still valid (price ≥ active stop).
  - Flat over the weekend: Friday 16:30 → Sunday 18:00, Bitcoin included.
  - A breakout during the break becomes a trade at 18:00 if still valid. A stop hit while flat ends the trade.

## Our defaults (the video / Pine leave these open)
- **Execution:** native MT5. A breakout triggers when the bid moves above the level, filled with a market buy at the ask.
  The exit is a broker SL at the active stop, raised once a day at the 17:00 NY rollover. Gaps fill at the market.
- **Daily bars:** built from M30 bars between 17:00 NY boundaries (the boundaries fall on M30 bars in UTC).
- **Sizing:** lots rounded UP to the lot step (Calyx standard). Day-trading re-entries reuse the original lot size
  (same trade). The high-water mark uses equity checked on every poll.
- Broker spread, commission and swap (native). $100,000, 1:2000, server clock UTC.

## Versions
| Id | What |
|---|---|
| **HOLD** | Main: hold overnight and through weekends |
| **DAY** | Main: day-trading mode (16:30 close / 18:00 re-entry / flat weekend) |
| RND_DAY 1–3, RND_HOLD 1–3 | Control: random long entries at the 18:00 NY re-entry time, probability matched to each version's entry rate; same stops, sizing and schedule |
| S55 | Sensitivity of DAY: Turtle System 2 — 55-day high entry, 20-day low exit |
| SATR3 | Sensitivity of DAY: 3 ATR fixed stop |
| SR1 | Sensitivity of DAY: 1% risk |

## Test setup and gate
- **Execution:** native MT5 Model 4 (intraday stops matter), 150 ms, end **2026-10-22** exclusive.
- **Windows:** separate 6m / 1y / 3y / 5y runs for HOLD and DAY (US500 / USTEC history in the tester starts in 2019, so the
  video's 11-year window cannot be rebuilt); controls and sensitivities on 5y.
- **Report:** per year, per asset, swap paid, trades/month and trades/day.
- **Raw gate:**
  - HOLD and DAY each positive with PF ≥ 1.15 on 3y AND 5y;
  - ≥ 30 trades;
  - mean R above the matching random control mean;
  - no flip to ≤ 0 without the best day or best trade.
- Older ticks are generated (real ticks from 2026-01).

## Revision 2026-10-22 — EA implementation fix (no rule change)
- **What happened:** the first HOLD run (6m, +7.92%, PF 2.2, 9 trades) flagged 964 rejected requests. The daily stop
  raise was sent only once, exactly at the 17:00 NY rollover. US500, USTEC, XAUUSD and XAGUSD are closed then
  ("Market closed"), so for those four assets the 10-day-low trailing exit never moved in HOLD mode.
- **Fix (implements the rule above):** the raise is applied at the first in-session tick after the rollover. If
  price has already gapped through the new stop, the position closes at the market (reason `stop_gap`).
- **DAY mode** is flat at the rollover and re-enters with the current stop, so it is unaffected apart from holiday
  early closes.
- **Invalid runs:** all pre-fix runs (DAY smoke, HOLD 6m, and an interrupted DAY 6m) are kept in
  `native-INVALID-pre-stop-fix/` and are not used. Every run is repeated with the fixed EA.

## Revision 2 2026-10-22 — DAY-mode close in US winter (tester session table)
- **Problem:** the DAY 3y run (v2 build) showed 141 positions held over 23 h. The tester applies each symbol's current
  trade-session table, fixed in UTC, to all history; that table is the US-summer one. So in US winter, indices and
  metals cannot trade from 16:00 to 17:00 NY, and the 16:30 NY close could not happen:
  - US500 and USTEC closed at 17:00 NY instead, and Friday closes were missed (weekend holds);
  - XAU and XAG had no scheduled close at all in winter.
- **Fix (DAY mode only):** close at 16:30 NY, or 5 minutes before the symbol's session ends if that comes first and
  falls within the hour before 16:30. No re-entry until 18:00 NY.
  - Effect: in US winter, indices and metals close at about 15:55 NY. Summer, Bitcoin and HOLD mode are unchanged.
  - Holiday early closes are not in the session table and can still carry a position to the next session; they are
    counted in the results ("Positions > 23 h").
- **HOLD mode:** the code path is unchanged. HOLD runs from the v2 build (`native/build-v2-stopfix-a65596191b1e.json`
  with its archived source/EX5) stay valid, and a HOLD smoke parity rerun with the v3 build confirms they are
  identical. HOLD still cannot trade 16:00–17:00 NY in US winter: the tester's session table is a disclosed limitation.
- **Invalid runs:** the DAY runs made with v2 move to `native-INVALID-v2-day-winter/`.

## Revision 3 2026-10-22 — DAY-mode close when quotes stop early (v4 build)
- **Problem:** the v3 DAY 5y run still held 126 positions over 23 h, some for weeks. Older index quotes in the tester stop
  before 16:30 NY: in summer 2022, US500 and USTEC quote only until 15:58 NY. With no tick in the 16:30 window, the 16:30
  close could not happen and the trade was simply held. This caused 50–75 missed closes a year for the indices in
  2022–2023, and few after 2024. These v3 DAY results, and the DAY controls and S55, were partly HOLD trades.
- **Fix (DAY mode only, no look-ahead):** close at 16:30 NY, or 5 minutes before the time the symbol's quotes stopped on
  the previous trading day (the last in-session quote between 15:00 and 17:00 NY), whichever is earlier.
  - With the winter session-table rule this gives about 15:53 NY for 2022 indices and about 15:52–15:55 NY in winter;
    16:30 NY otherwise.
  - Learned quote-end times are logged (`TURTLE_QEND`).
- **Checks:**
  - 2022 summer DAY smoke: no positions over 23 h.
  - Winter smoke: only holiday early closes (Thanksgiving, Christmas) and the end of the test.
  - HOLD smoke: identical to v2.
- **Invalid runs:** v3 DAY runs, DAY controls and the interrupted S55 run move to `native-INVALID-v3-day-quote-gap/`.
- **Still valid:** HOLD runs (v2) and RND_HOLD controls (v3). The HOLD code path is unchanged, and the v2→v4 HOLD parity
  check confirms it.

## Revision 4 2026-10-22 — quote-end time per weekday (v5 build, final)
- **Problem:** the v4 DAY 5y run still had 117 positions over 23 h. In 2023–2024 index quotes end at 16:58 NY Monday to
  Thursday but at 15:58 NY on Fridays. The v4 rule learned from the previous day (Thursday), so it waited for 16:30 on
  Fridays and held over the weekend. The remaining Sunday→Tuesday cases were Monday holidays.
- **Fix:** the early close uses the quote-end time of the latest earlier day with the same NY weekday. It is seeded
  from the M1 bars of the 3 weeks before the start (`TURTLE_QSEED`), so there is still no look-ahead.
- **Checks (v5):**
  - 2023 summer smoke: Fridays close at 15:53 NY; the only positions over 23 h are the Juneteenth and July 4 holidays.
  - 2022 summer smoke: none.
  - Winter smoke: Thanksgiving, Christmas and the end of the test only.
  - HOLD smoke: identical to v2.
- **Accepted limitation:** US holiday early closes and closed holidays are not in any table the EA can see, so a DAY
  position can be carried over a holiday. They are counted ("Positions > 23 h").
- **Invalid runs:** v4 DAY runs move to `native-INVALID-v4-day-friday/`.
