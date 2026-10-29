# VWAP & EMA reel raw study 2026-10-26 — rules (frozen before any test)

**Source:** owner-shared reel, "Trading with VWAP & EMA" (Finshala with Priya). Data, not authority.
- **Short:** enter when price **closes below** VWAP and EMA. Exit when price **closes above** VWAP and EMA.
- **Note on the reel:** "For indices VWAP is applicable only on the futures chart".
- **Not stated:** EMA length, timeframe, stop and long side ("comment settings to know complete").

## Frozen interpretation (assumptions marked A)
- **Instruments:** USTEC, US500, US30 (index CFDs, the reel's market type) and XAUUSD.
  - Exness-MT5Trial16, Model 4 (real ticks from 2026-01-01; earlier generated), 150 ms, $10,000, 1:2000.
  - **A1:** CFD tick volume stands in for futures volume.
- **Timeframes:** M5 and M15 (A2).
- **EMA:** EMA(20) on close (A3). Sensitivities EMA 9 and EMA 50.
- **VWAP:** session VWAP anchored at 09:30 New York (DST-aware), typical price × tick volume (A4).
- **Signal states on each closed bar:**
  - ABOVE = close > max(VWAP, EMA).
  - BELOW = close < min(VWAP, EMA).
  - BETWEEN = otherwise.
- **Short:**
  - Enter on the first close that turns BELOW (the previous closed bar was not BELOW).
  - Exit when a bar closes ABOVE.
- **Long (A5, mirror of the reel's short):**
  - Enter on the first close that turns ABOVE.
  - Exit when a bar closes BELOW.
- An exit that is also a fresh opposite signal reverses at once. A BETWEEN close keeps the position.
- **Session (A6):** signals only from the 09:35 bar close; no new entries after 15:30 New York; everything is flat at
  15:55 New York (intraday, because the VWAP resets daily).
- **Execution:** a market order on the first tick of the next bar.
- **Protective stop (A7):** the reel has none, so an emergency stop at 2 × ATR(14) of the signal timeframe is placed.
  - It also defines sizing: 1% of equity to that stop, rounded UP (Calyx standard).
  - Exits are by signal, the stop, or the session close. No take profit.
- **Windows:** separate native runs over 6 months, 1 year, 3 years and 5 years ending 2026-10-26 (exclusive).
  Dev / validation / OOS windows inside the 5-year runs come from `data_split.py`.

## Controls (5 years)
- **VWAP_ONLY:** same rules on close vs VWAP only.
- **EMA_ONLY:** same rules on close vs EMA only.
- The main rule must beat both. A random-direction control is not meaningful for an always-reversing rule.

## Sensitivities (5 years, not used to pick)
EMA 9 and EMA 50 on both timeframes.

## Raw gate (PIPELINE.md stage 4)
- Positive and PF ≥ 1.15 on 3y and 5y, with ≥ 30 trades.
- Mean R above both controls.
- Best day / best trade check PASS.
- A FAIL stops the study: no optimisation.
