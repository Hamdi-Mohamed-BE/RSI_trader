# FTSE 100 three-setup bot — full pipeline (EXPLORATORY OVERRIDE) — plan, frozen 2026-10-27 before any search result

**Why an override:** the raw study (`FTSE Three Setup Raw 2026-10-27`) passed only S2 (Monday dip). S1, S3 and the
combined bot FAILED the raw gate. PIPELINE.md stage 4 says "no optimizing a loser". The owner explicitly asked
(2026-10-27) to "optimize all three together and run through unseen data and Monte Carlo simulation". So this runs as
a labelled exploratory override, like the Nasdaq H1, Gold Trio and EURUSD searches.

Research only: isolated tester, nothing deployed.

## Data split (data_split.py, frozen)
- Study end **2026-10-27 exclusive**. History starts 2019-08-01 (the first UK100 data in the tester).
- **Development:** 2019-08-01 → 2023-10-27, 4.2 years. All searching and plateau checks happen here.
- **Validation:** 2023-10-27 → 2024-10-27. Finalist choice only.
- **OOS:** 2024-10-27 → 2026-10-27, run ONCE for the frozen finalist.
- **NOTHING on UK100 is unseen.** The raw study viewed 2019-08 → 2026-10, and the 2026-10-19 study viewed 2020–2023.
  Validation and OOS are therefore **retrospective** (viewed, not pristine). This is stated on every result.
- **Genuinely unseen evidence:** a **transfer test**. The frozen final version, unchanged, runs on **DE30 (DAX)** and
  **US500** (5y, Model 4). Neither has ever been run with these rules.

## Engine
A case-table EA, `engine.py` (EURUSD pipeline pattern; native MT5 optimizer over InpCase, per-pass deal ledgers).
- **Three setups**, each with its own timeframe and parameters:
  - **S1 panic drop:** close beyond Bollinger(band_h, dev), RSI beyond the threshold.
  - **S2 Monday dip:** Monday (or Mon–Tue), close vs SMA(ma_h), RSI.
  - **S3 trend pullback:** SMA(trend_h) slope over N bars, distance from SMA(ma_h) in ATR, RSI.
- **Indicator lengths:** given in HOURS and converted to bars of the setup's timeframe (M30 / H1 / H4). RSI and ATR
  are 14 bars.
- **Per setup:** ATR stop, TP in R (or none), time exit (h or none), break-even, ATR trail, direction (clip direction,
  mirror, both), London session filter, ADX filter, D1 EMA50 trend filter.
- **Sizing and execution:** sizing, gap checks, time exits and the clock are unchanged from the raw EA. 0.75% equity
  risk, lots rounded up, $10,000, 1:2000, 150 ms.
- **Parity gate before searching:** the base case must reproduce the raw ALL 5y Model 4 ledger exactly (entries,
  exits, cash).

## Staged search: each setup alone, development, native Model 1, top 3 carried forward per stage
For each setup S1 / S2 / S3:
1. **Signal × timeframe:**
   - S1: tf 30/60/240 × band 20/40/60 h × dev 1.5/2/2.5 × RSI 30/35/40.
   - S2: tf 30/60/240 × MA 10/20/40 h × RSI 35/40/45 × day Mon / Mon–Tue.
   - S3: tf 30/60/240 × trend 50/100/200 h × distance 1/1.5/2 ATR × RSI 35/40/45; then slope 3/5/10 bars × MA
     20/40/60 h.
2. **Stop:** ATR 1 / 1.5 / 2 / 2.5 / 3.
3. **Exit:** TP none / 0.5 / 0.75 / 1 / 1.5 / 2 / 2.5 / 3 / 4 / 5 / 6 R × time exit 8 / 24 / 48 h / none (none + none
   excluded).
4. **Management:** none; break-even at 0.5 / 1 R; ATR trail 1 / 2 ATR from 0.5 / 1 R.
5. **Direction:** clip direction / mirror / both.
6. **Session:** all hours; London 08:00–16:30; London 07:00–21:00.
7. **Filters (one at a time):** none; ADX ≥ 20 / 25; ADX ≤ 20 / 25; with D1 EMA50 trend; against it.

**Ranking (development):**
- Eligible: ≥ 50 trades, net > 0, PF ≥ 1.05.
- Rank by return ÷ closed-balance DD; ties broken by PF.
- If fewer than 3 are eligible, the stage carries the best PF with ≥ 50 trades, labelled "not profitable".

## Combination ("all three together")
- Every combination of {each setup's 3 finalists or OFF}: 4³ − 1 = 63 bots, run as ONE combined bot on development.
- Ranked the same way, with ≥ 80 trades. The top 3 go on.

## Plateau, validation, OOS
- **Plateau:** one-step neighbours of each top combination: RSI / stop / TP / time exit ±1 step, for each enabled
  setup separately. It passes if ≥ 70% of neighbours have net > 0 AND median PF ≥ 1.05.
- **Confirmation:** survivors run at Model 4 on development and validation.
  - Validation picks ONE: highest validation PF with ≥ 15 trades and net > 0.
  - If none qualifies → REJECTED_AT_VALIDATION.
- **OOS once (Model 4, retrospective):** net > 0, PF ≥ 1.15, ≥ 30 trades, recent-half PF > 1, and the best-day /
  best-trade check PASS. A failure is final: no re-tuning.

## Monte Carlo and robustness (owner request: run on the final version whatever the OOS verdict; labelled)
- **Full-period run:** the final version at Model 4 over 2019-08 → 2026-10.
- **Day-block bootstrap** (robustness.py), 10,000 paths of 252 trading days, 5-day blocks: return, max DD, losing
  streak, worst day.
- **Trade-order reshuffle:** max DD distribution.
- **Random 20% trade removal:** 1,000 draws.
- **Cost stress:** +1 spread-equivalent per trade.
- **Probability of a losing year.**
- **Transfer test (unseen):** DE30 and US500, 5y, Model 4.
- **Search breadth:** the deflated Sharpe uses the full tested-configuration count.

Every table shows trades, trades/month and trades/day. Every configuration is counted and kept (SEARCH RESULTS.json).

## Addendum 1 (2026-10-27, written before any search result)
- **Early rejection:** if the pipeline rejects at plateau or validation, the best development combination (rank 1)
  is still carried through OOS, Monte Carlo and the transfer test. Those results are labelled **DIAGNOSTIC**, because
  the owner asked to see them; they are never a pass.
- **R units:** per trade, R = net ÷ (0.75% × balance before the trade).
- **Cost stress:** subtract 1.0 index point per trade, converted to R with that trade's initial stop distance.
- **Deflated Sharpe:**
  - Inputs: daily returns of the development + validation Model-4 run.
  - Trial count: the total number of tested configurations.
  - SR variance: taken across all development screens.

## Addendum 2 (2026-10-27, parity method; before any search)
- **First parity run:** 1,273 vs 1,273 trades and the same net ($−2,076.65). Exits and volumes are identical, with
  1-cent rounding on some trades. 7 entry times differed only because the raw report pairs overlapping positions FIFO.
- **Revised check:** entries are compared with the raw EA's own `FTSE3_ENTRY` journal lines (minute, setup, side,
  initial SL). Exits are compared by (close, volume) exactly, with net within $0.02.
- **Engine unchanged:** pipeline.py was re-frozen after this change only.

## Addendum 3 (2026-10-27, after OOS/MC, before the transfer test ran)
- **Bug:** `transfer()` indexed the batch result list as a dict and crashed before any transfer test ran.
- **Fix:** one-line fix (`[0]`), then re-froze. No search, selection, OOS or MC code changed.
