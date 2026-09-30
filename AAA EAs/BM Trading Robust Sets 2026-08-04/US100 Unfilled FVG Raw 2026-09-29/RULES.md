# US100 unfilled-FVG exhaustion — frozen raw interpretations

User source: the supplied short clip, not a full rulebook. The 72% claim is unverified.
Instrument: Exness USTEC (US100 CFD), NOT exchange NQ futures.
Six fixed variants: parent M1/M5/M15, each with M1 CISD or M1 IFVG confirmation.
These are alternative operational definitions, not six optimized parameter sets.

## Setup
Use three fully closed consecutive parent candles A, B, C. Bullish displacement:
B.close>B.open, C.low>A.high, C.close<=B.high. Gap=[A.high,C.low].
Bearish mirror: B.close<B.open, C.high<A.low, C.close>=B.low; gap=[C.high,A.low].
Aggressive (ours): B body >= simple mean true range of 14 candles BEFORE B,
and body >=60% of its full high-low range. No volume claim is tested.
Target (ours) is the parent gap midpoint. Fade bullish displacement short, bearish long.
Only one pending setup, first eligible wins; ignore further parent setups while pending.

## Confirmation (ours; ambiguous in clip)
All confirmation bars must CLOSE AFTER the setup is known. Never enter at C's historical close.
CISD: at setup activation, locate the latest same-displacement-colour candle among the
last 20 closed M1 bars, walk back through its contiguous same-colour leg, and freeze
the FIRST candle's open. Initial close must not already have crossed it. Subsequently
require a fresh M1 close across this level against displacement, with prior close on
the original side. This is one explicit delivery-shift interpretation.
IFVG: find a same-displacement-direction M1 FVG formed in the last 20 minutes,
whose far edge lies on the entry side of the parent midpoint. It must not have
previously been closed through. Require a fresh M1 close through its far edge.
Most recent qualifying gap wins. It can form before or after parent activation.
The parent gap itself cannot be used when its inversion has already traversed the target.

Partial entry into the parent gap is allowed: 'unfilled' here means midpoint NOT yet
touched since activation (ours). Cancel on any intervening M1 high/low touching the
midpoint, or on a current bid/ask already beyond target, or after 30 minutes (ours).
That includes the confirmation candle: no counting a target reached before entry.

## Execution and risk (ours)
Market entry at first available quote within 10 seconds of the next M1 bar, 150ms delay.
Target=rounded midpoint, stop mirrored at equal price distance from the decision quote;
nominal 1:1 BEFORE commissions/slippage, actual fill RR may differ. No breakeven/trailing.
Both directions; one position, no pyramiding, one entry attempt per parent setup.
NY weekdays 09:30 <= entry <15:30; US DST applied to broker UTC history. Parent C must
close in that window. Close at first quote after 60 minutes, 15:55 NY, or 5 minutes
before the published broker trading-session end. Quote gaps can delay exits.
1% current equity stop risk; round lots UP/minimum as existing user policy, check margin,
broker stop distances/max volume. Actual risk is measured; this is NOT a risk ceiling.
USD10,000, 1:2000 demo testing. Broker spread/commission/swap; no live trading.

## Frozen comparison and gate
Control: same setup/confirmation logic, seeded random long/short at those opportunities,
same distance and 1:1. Positions can end at different times, so later eligibility may
diverge. This is a directional ablation, NOT a fully time-matched random-entry test.
Seed 290929. Report overlap and do not claim statistical superiority from one seed.
Windows end 2026-09-27, starts 2026-03-27 / 2025-09-27 / 2023-09-27 / 2021-09-27.
Model1 long-window screens; Model4 all raw windows plus long-window controls.
Real-tick coverage must be disclosed; Model4 falls back to generated ticks when absent.
Both 3y and 5y: positive net, PF>=1.15, >=30 trades, mean net R > control, clean execution.
Also require positive latest year for recommendation. Windows overlap, NOT holdouts.
Failure stops. No parameter search, Monte Carlo promotion, deployment or live orders.
