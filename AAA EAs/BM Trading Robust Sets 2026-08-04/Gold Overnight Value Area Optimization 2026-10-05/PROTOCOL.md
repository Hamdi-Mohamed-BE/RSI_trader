# Gold Overnight Value Area — payoff optimisation, 5 October 2026

Research only; stop for user review. Gold and Silver news audits are saved and deferred. Do not edit production EAs, installers, public website, live charts, or Git history.

The approved production rule is first completed M5 close outside a 64-bin/70% overnight NY 18:00–09:30 tick-volume value area. Opposite VA stop, overnight extreme target, one consumed first signal/day, entry/exit before 16:00 NY, 1% equity with upward/minimum-lot rounding. This study preserves profile and entry logic, and opens the existing locked payoff/exit parameters in a tester-only copy. Default parity against the shipped EX5 is mandatory.

## Evidence and chronology

The prior five-year raw native result was PF1.04; this fails the canonical PF1.15 gate. The user's one-at-a-time optimisation instruction is treated as exploratory research, NOT permission to promote a failed raw strategy. Earlier optimisation selected a different POC-stop variant but did not pass its frozen native gates. Neither the earlier study nor this rerun gives an untouched latest-year holdout: these eras have already been inspected.

- Development: 2021-10-05 to 2024-10-05 exclusive.
- Validation: 2024-10-05 to 2025-10-05 exclusive.
- Recent assessment: 2025-10-05 to 2026-10-05; six months 2026-04-05, three months 2026-07-05, all end at 2026-10-05 exclusive.
- Independent 3Y/5Y native replays start 2023-10-05/2021-10-05. Each starts USD10,000, 1% equity, Exness XAUUSD, leverage 1:2000, 150ms delay, Model4. Disclose mixed/generative ticks. No FTMO pass forecast.
- Safe cached M1/M5 data from the September19 study are used ONLY for development/validation screening. Never call its active-account fetching helpers. Cache hashes recorded. Its known June20 2025 gap remains unfilled.

## Frozen bounded search (not a completed full stage-5 pipeline)

Focus on the diagnosed poor payoff before adding more entry filters. Keep M5, 64 bins, 70% VA, both directions, no ADX/DI and one consumed signal/day unchanged. Broader timeframe/entry/regime searches remain NOT RUN.

Staged one-factor-at-a-time cached-bar exploration, top3 carried forward:
1. Minimum original overnight reward/risk: 0, 0.10, 0.25, 0.50, 0.75, 1.0.
2. Fixed targets: original extreme or 0.5, 0.6, 0.75, 1, 1.25, 1.5, 2R. Fixed-R targets also change eligibility when the original extreme is already behind entry; disclose this.
3. Stop: opposite VA or POC.
4. Management: static, BE at 0.25/0.5/0.75/1R, M5-close trail 0.25/0.5/0.75/1R after +1R. No partials.
5. Last entry: 10:30/11:00/12:00/13:00/14:00/15:00/16:00 NY.
6. Time exit: 15:00/15:30/16:00 NY, only exit >= last entry.
7. Joint neighbours: selected minimum-R +/-0.10 and entry cutoff +/-30min (valid bounds). This diagnostic cannot reselect on recent data.

Approximation reuses the old conservative stop-first M1 engine, spread and historically observed $5.50/lot round-trip commission. Native costs determine final results; no invented extra execution-cost overlays. Cached engine has no full historical margin/session validation and is not native drawdown. Source hash and every distinct configuration count are saved, including the earlier 195-known-configuration search as context for data snooping.

Training score: 30log(PF clipped .05..3) + 2 return/max(approxDD,1) -.5 approximateDD + .15(winrate-60), with a 0.2 penalty per trade below150. Native eligibility requires >=150 development and >=40 validation trades, both net-positive/PF>=1.20, winrate>=60%, winning streak longer than losing streak, native equityDD<=15%. Freeze one diagnostic finalist using development/validation only before opening recent native results; if no eligible candidate, show the best diagnostic without relaxing these gates.

## Verification and robustness

Compile zero errors/warnings; tester-only OnInit guard; parity exact native deal cash flows on 3M. Audit every position's complete deal group, commission/swap/fee, actual initial risk vs selected budget, causal signal/profile, NY dates, late and overnight exits; independently match exported deals to native HTML. Native input/date/symbol/delay/freshness checks. One leased isolated tester, no live API/account changes. Reject operational failures before promotion.

10,000 block-bootstrap paths, block length5; returns normalised to entry account equity including native costs. Report P05return/PF, probability of profit, closed-balance drawdown, reshuffle losing streak and 10/20% removal. Measured spread stress (one additional observed request spread per completed trade) is a fixed-ledger overlay, not a native execution rerun. Deflated Sharpe/trial-count adjustment and truly untouched holdout remain prerequisites for promotion if unavailable here. No full pipeline or institutional-validation claim.

Deliver native baseline/candidate side-by-side for1Y/6M/3M/3Y/5Y, full dates, trade counts and frequency, net PF, win rate, return, equityDD, daily-equity Sharpe, winning/losing streak, payoff, annual cash-flow breakdown and separate screen/MC evidence. Log the outcome in the local review HTML only, stop for user review.
