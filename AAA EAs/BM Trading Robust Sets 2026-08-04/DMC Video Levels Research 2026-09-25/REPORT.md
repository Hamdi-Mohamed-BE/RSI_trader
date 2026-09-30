# DMC video-levels study — report (2026-09-25)

User request: improve the DMC EAs using the "How to Find Levels with DMC" video (youtube kE76NlmKmY8, transcript
pasted by the user) and re-test on US100, BTC and XAU for every website period, side by side per DMC EA / asset / period.
Research only — nothing was installed, deployed or published. Full tables: `RESULTS.md`; machine-readable: `RESULTS.json`.

## Setup

- Isolated tester `_Backtests/MT5-DMC-20260811`, Exness-MT5Trial16 demo, $10,000, 1% risk, H1, Model 4
  (real ticks only from 2026-01; bars-generated before), 150 ms delay. Windows 6m/1y/3y/5y ending 2026-09-01
  (the website's DMC windows). Current source + exact production SETs.
- Research EAs `EA/DMC Current Video Research.mq5` and `EA/DMC Fresh Reaction Video Research.mq5` = production
  wrappers + a research copy of the Fresh Reaction engine with new inputs, all default OFF.
- **Parity:** with the new inputs off, the research builds reproduced production exactly on the 1y window
  (CUR XAU 116/116, FRX XAU 15/15, FRU US100 12/12 trades; identical entries and exits) — `native/PARITY.json`.
- Off-native symbols for CUR/FRX use a 1.5×H1-ATR stop (the production US100 DMC stop) because a fixed XAU
  dollar stop does not transfer; everything else is the SET.
- 120 native runs, no failed run. Some 5y journals show "failed modify … [Market closed]": the dynamic trailing stop
  tried to move a stop while the market was closed (identical in BASE); no entry was rejected.

## Rules taken from the transcript

| Rule | Implementation | Status |
|---|---|---|
| A level is used once; a tested level is not traded again | `InpDmCFreshMode=1` (first test only) + `InpDmCFreshIgnoreOpeningTouch` (the day opens on yesterday's close = a body edge; that opening touch is not a test) | **UNTESTED** |
| Target the first untested level in the reverse direction; beyond it is "gambling" | `InpDmCLevelTarget`: TP at the nearest level (D1 bodies 20d, W1/MN1 bodies) not traded through since it formed; capped at the SET R; skip if < 0.25R | **TARGET** |
| Prefer levels with 0–1 pass-throughs | Pass-throughs are counted from the level's origin to current price. Yesterday's body level has none, so the rule is always satisfied for this engine | Not applicable |
| HTF priority, H4 trend change + 15m open retest | Not specified numerically in the video; not implemented | Not tested |

VIDEO = UNTESTED + TARGET. Two implementation errors were found and fixed before the reported runs (pre-formation
pass-through count; counting the opening touch). Those runs are in `native/superseded-*` and are not results.

## Results — native symbol (the only profitable combinations)

| EA / window | BASE (current) | VIDEO | UNTESTED only |
|---|---|---|---|
| DMC Current XAU 1y | +14.87%, PF 1.17, DD 11.4% | +0.54%, PF 1.04 | −1.42%, PF 0.90 |
| DMC Current XAU 3y | +55.70%, PF 1.26, DD 14.5% | +0.66%, PF 1.02 | +23.28%, PF 1.48, DD 13.1% |
| DMC Current XAU 5y | +11.96%, PF 1.05, DD 37.0% | −10.49%, PF 0.76 | +11.60%, PF 1.18, DD 13.4% |
| Fresh Reaction XAU 1y | +9.60%, PF 1.99, DD 4.0% | +9.82%, PF 8.69, win 88% | +8.41%, PF 3.25, DD 3.4% |
| Fresh Reaction XAU 3y | +48.28%, PF 2.46, DD 5.4% | +18.19%, PF 4.67, win 89% | **+48.21%, PF 3.75, DD 4.0%** |
| Fresh Reaction XAU 5y | +32.86%, PF 1.62, DD 19.5% | +5.52%, PF 1.28 | **+32.45%, PF 1.89, DD 13.6%** |
| Fresh Reaction US100 3y | +18.25%, PF 2.00, DD 4.3% | +15.04%, PF 2.66, DD 2.3% | +16.51%, PF 2.21, DD 3.8% |
| Fresh Reaction US100 5y | +12.53%, PF 1.33, DD 8.3% | +10.89%, PF 1.61, DD 4.7% | +11.93%, PF 1.51, DD 6.9% |

## Conclusions

1. **Next-level target (TARGET) hurts XAU.** Alone it took DMC Current XAU 5y from +12.0% to −19.4% and Fresh Reaction
   XAU from +32.9% to +3.0%. It raises the win rate (Fresh Reaction XAU 70–89%) but cuts average winners by more.
   Not recommended as a return improvement; it produces the high-win-rate, low-R profile only.
2. **First test only (UNTESTED) is the useful rule.** On Fresh Reaction XAU it kept 3y/5y return (−0.1 / −0.4 pp)
   with higher PF and lower DD (5y DD 19.5% → 13.6%). On Fresh Reaction US100 it cost 0.6–2 pp of return with lower
   3y/5y DD. On DMC Current XAU it cut 5y DD from 37.0% to 13.4% at the same 5y return, but lost 32 pp on 3y and
   16 pp on 1y — mixed, and DMC Current XAU is preserved by the user's decision anyway.
3. **No DMC config works on BTC or off its native symbol.** Every off-native BASE loses over 3y/5y (down to −61%).
   The video rules only lose less by trading less. The best BTC cells (CUR VIDEO 3y +3.8%, PF 1.07; FRU UNTESTED
   5y +0.7%, 27 trades) are not an edge. A BTC DMC EA is not supported by this evidence.
4. **Candidate for further validation (not deployed):** Fresh Reaction XAU with UNTESTED. It is the only change that
   holds return while improving PF and drawdown across 3y/5y. Caveat: UNTESTED was chosen after seeing the 5y
   ablation of these same years (in-sample choice among 3 rule sets); pre-2026 history is bars-generated; trade counts
   are small (8–59 per window). Next step if wanted: forward/demo observation or an untouched period, then the
   normal promotion path (parity, SET, website evidence) with the user's approval.

## Files

- `run-config.json`, `run_dmc.py` (stages compile/parity/main/ablation/untested/summary), `make_report.py`
- `EA/` research sources + EX5 + compile logs; `native/build.json` (source/EX5 hashes), `native/PARITY.json`
- `native/dmcv-*/` per run: SET, tester.ini, run.json (metrics, checks, flags), trades.json, report `.htm.gz`,
  `journal.txt.gz`
