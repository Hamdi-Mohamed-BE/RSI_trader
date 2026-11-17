# Gold EMA Ribbon — RAW rules (frozen 2026-11-12, before any run)

Owner 2026-11-12: "try this one" — pasted social clip "Gold EMA Ribbon Strategy" (claims: 2 years, 293 trades, 31% win, avg win ~$2,400 / avg loss ~$600 at $750 risk
on $100k, worst day -2%, max DD 9.1%, 89% of 1,000 simulated FTMO challenges passed). SOURCE = said in the clip; ASSUMPTION = ours (the clip leaves it out).

## Rules
- SOURCE: XAUUSD, 1-hour chart. Five moving averages lined up in order fastest -> slowest; price above the 200 EMA for a buy, below for a sell.
- SOURCE: stop 1.5 x "average candle size" from entry. ASSUMPTION: ATR(14) on H1 at the signal bar.
- SOURCE: no target; exit when price CLOSES below the slowest of the five (buy) / above it (sell). ASSUMPTION: H1 close, exit at the next tick.
- SOURCE: $750 per trade on $100k = 0.75% risk. ASSUMPTION: 0.75% of balance, lots rounded DOWN to the step (no oversizing), $100k deposit.
- ASSUMPTION (lengths not given): EMA 8 / 13 / 21 / 34 / 55 (Fibonacci ribbon) + EMA 200, all close prices.
- ASSUMPTION (trigger not given), MAIN = CROSS: enter at the close of the H1 bar on which the five EMAs BECOME aligned (not aligned on the previous bar), with the close on the
  right side of EMA 200; one position at a time; both directions.

## Versions (native, end 2026-11-12 excl.)
- MAIN (Model 4) on 6m / 1y / 2y (the clip's span) / 3y / 5y / all (2019-01 ->).
- Sensitivities (Model 4, all years): STATE = enter on any aligned bar while flat once the close is back on the right side of the slowest EMA; RIB2 = EMA 5/10/20/30/50;
  RIB3 = EMA 10/20/30/40/50; LONG = long only (gold's trend).
- Controls (Model 1, all years, 20 seeds each): RNDDIR = MAIN with a random direction; RNDENTRY = entries at random H1 bars with the MAIN's entry rate, direction = side
  of EMA 200, same stop and exit rule (stage-4 random-entry control; p = share of seeds >= MAIN Model 1). MAIN Model 1 for the like-for-like comparison.
- Buy & hold XAUUSD on the same windows (pipeline buy_hold_benchmark).
- Cost stress: each trade's recorded commission + swap and the entry spread (logged by the EA) in R; robustness.cost_stress at 1x / 2x / 3x.
- FTMO: if it passes the raw gate, the frozen FTMO 1-Step / 2-step engines at 0.75%.

Raw gate (pipeline): all years and 3y positive, PF >= 1.15, >= 100 trades, beats the random controls (random-entry p <= 0.10), positive at 2x costs, three-way MC.
Weekend: report the share of trades held over a weekend (FTMO 1-Step funded / Standard accounts may not hold them).
