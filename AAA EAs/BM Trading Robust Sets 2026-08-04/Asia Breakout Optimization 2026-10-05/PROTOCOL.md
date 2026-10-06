# Asia Breakout Gold — frozen exploratory protocol, 5 October 2026

Research only; no live account, installed files, BAT, public website or Git changes. One EA, then stop for user review. Gold/Silver news deferred; Trend 1.5R future keep preserved.

Baseline: exact current asia-breakout.set and shipped EX5; XAUUSD H1, 1% intended equity risk, USD10,000, broker native costs, 150ms. Rounded-up/minimum volume retained, so 1% is not a hard risk ceiling. Exact default-copy native deal parity is mandatory before selecting anything.

Current tester clock mode1 assumes UTC+2/+3, unlike Exness UTC server and live automatic offset. Preserve mode1 as the tested baseline. Test mode0 as an explicit clock-alignment diagnostic, not a silent correction or matched-exit comparison.

Bounded search, NOT the complete full pipeline: staged targets 0.5/0.6/0.75/1/1.5/2/3/4R; management original, fixed-only, stable-original-risk trailing; neighbours; breakout buffer, signal timeframe, final entry hour, long-only/short-only, midpoint versus opposite-band SL, Markov off/stronger gate. No ADX/DI re-promotion: user previously rejected Asia DI on longer evidence. All trials retained, including failures. Fast screen model1 (generated every tick), final checks model4 real ticks where supplied, otherwise generated. No cached approximate fills.

Development 2021-10-05–2024-10-05 exclusive. Validation 2024-10-05–2025-10-05 exclusive. Latest evaluation 2025-10-05–2026-10-05 exclusive, 6M from2026-04-05, 3M from2026-07-05. Full3Y from2023-10-05, full5Y from2021-10-05. All periods restart10k. These previously researched dates are NOT an untouched holdout.

Qualification frozen: development ≥90 and validation ≥30 whole positions, positive return, net PF≥1.20, win rate≥50%, longest win run>loss run, native equity DD≤15%; no failed entry/close or critical audit errors. Legacy stop-modify rejections are counted explicitly; new stable manager must not produce them. Rank qualifying settings by PF × sqrt(number of positions) / (1+equityDD/10), then WR, lower DD. If none qualifies, show the highest-ranked descriptive diagnostic, do not relax gates. At most top3 sufficiently distinct initial finalists on older validation; freeze one before recent native results. Additional stage filters only from chosen older-trained exit configuration. Validation reused for bounded selection is not independent final proof.

Raw3Y/5Y gates PF≥1.15, positive, ≥30 trades; if failed search remains exploratory under prior user instruction, not a promoted pipeline winner. Random entry comparison, complete stage5, shared portfolio, FTMO replay and rolling independent WFO NOT part of this bounded audit.

Independent full native deal reconciliation including commission/swap/fee, whole-position net metrics, sampled daily floating-equity Sharpe sqrt252, native intraday equity DD, W/L streaks and frequency. Never inflate trade counts with exit legs.

10,000 circular-block bootstrap paths length5, shuffle and 10/20% trade omission on proportional whole-position closed returns. MC positive-return≥95%, returnP5>0, PFP5>1; approximate deflated Sharpe≥95%. Count all new configurations plus at least6 earlier Asia filter variants; older unknown trials mean DSR optimistic. Extra one actually observed entry spread cash stress with unchanged fills; no invented spreads. Conditional resampling is not a future probability or FTMO margin/equity simulation.

Regime skill audit: completed D1 only, matrix re-estimated from past bars; do not apply a full-sample matrix backwards. Skill helper script missing; audit current engine's exact 40-day±5% states and transition exclusion directly. Export matrix evidence on entry candidates, with newest completed D1 time and training cutoff. Framework Roan (@RohOnChain); historical, not forward-looking.
