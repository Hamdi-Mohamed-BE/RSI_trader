# Kane PO3 / SMT research approximation — frozen before testing

This is NOT Kane's exact strategy, a claim about his skill, or replication of his advertised returns.
The transcript leaves swing-range selection, discretion and some management exceptions undefined.
No live terminal API, account login, deployment, orders or production changes. Tester-only guard.

## Source and deliberate mechanical assumptions (ours)

- Source: daily/H4/H1 location, hourly sweep, NQ/ES divergence, inverse FVG, 50% base hit, structural breakeven.
- Instruments: same Exness feed USTEC and US500 CFDs, NOT NQ/ES futures. Only USTEC traded.
- Source server timestamps assumed UTC based on existing history. US New York DST calculated explicitly.
- Entries 10:00 <= New York time < 11:30, Monday–Friday excluding NYSE holidays. Mondays and Fridays retained because transcript contradicts blanket exclusion with examples (ours).
- Flat at 12:00 New York (ours); no PM trades, runners, crypto or discretionary overrides.
- Decision on the first USTEC tick after a completed M3 candle. Same timestamps required for both assets for ALL M3 history used. No current/future US500 candle is used.
- Previous NY calendar trading-day range (skip weekends/NYSE holidays) gives daily midpoint. Minimum 600 M1 bars, from that day only (ours; not a discretionary dealing range).
- Custom H4 blocks at 02/06/10/14/18/22 NY; previous completed block defines reference H4 range, not broker H4 candles. Minimum 180 M1 bars in prior block (ours).
- Prior completed H1 range requires >=50 M1 bars. Current hour's highs/lows use only completed M3 bars.
- Bearish SMT: exactly one asset exceeds its own previous-hour high by >=one tick; bullish mirrored. Both cross means no SMT. Current-hour aggregate, not a generic correlation statistic (ours).
- Aligned entry: SMT plus either asset sweeping previous custom-H4 extreme during the current H4 block, and USTEC signal close in daily AND previous-H4 premium for shorts / discount for longs. Previous-day extreme sweep is NOT mandatory: the transcript's examples do not consistently require it.
- Control: USTEC previous-hour sweep only, no SMT, daily/H4 requirements.
- Inversion: a bullish three-candle gap low[i] > high[i-2] by >=one tick is crossed DOWN by the just-closed M3 close; bearish gap inverted upward is mirrored. Most recent qualifying gap formed within preceding ten completed M3 bars. Crossing requires prior close on original side and latest close across opposite edge. Can form before or after sweep; both conditions must hold at entry (ours).
- Entry market at next tick after inversion. No assumed perfect limit retest.
- SL beyond highest/lowest USTEC price in current hour, including decision quote, plus max(two ticks,current spread) (ours).
- Target midpoint of combined prior-hour and current-hour USTEC range, frozen at signal. Require target in correct direction and >=0.5 planned reward/risk (ours).
- Maximum two entries per NY day, one position at a time. New inversion required for retry; no averaging or pyramiding.
- Static case: only initial SL, midpoint TP and noon close.
- Structural BE case: once price is in profit, move stop to entry plus cost allowance when the current H1 candle crosses its open in the favourable direction OR price crosses prior completed M15 extreme. Trigger uses previous observed price and a genuine new cross; not merely an already-satisfied condition (ours).
- 1R BE control: same one-way stop adjustment after favourable move of one initial price risk (ours).
- BE offset: max(one tick, current spread + $0.70 per lot converted to price). This is an explicit assumed fee allowance, NOT guaranteed net breakeven or measured target-broker cost. Native fills can gap/slip. Stops never loosen.
- Fixed $100 initial risk on $10,000 native research balance; lot step rounded DOWN (documented conservative exception to pipeline round-up convention). Actual quote/OrderCalcProfit and margin checks.
- Raw execution 150ms, native broker costs; native leverage 1:2000 research-only. Separate account replay applies FTMO Swing / Instant leverage and caps.
- 6m/1y Model4 requested, 3y/5y Model1 screens. Report actual tick coverage, synchronized reference-data failures and capital exhaustion.
- Four predeclared variants are ablations, not a parameter search. No tuning after poor performance.
- Prop simulation reuses reviewed local lifecycle engine with price-path/cost/rule limitations documented separately. Historical restart frequencies are NOT independent future probabilities.
- Failed raw gate means no parameter search, deployment or claimed promotion; full promotion Monte Carlo only after valid raw gate/long confirmation.

