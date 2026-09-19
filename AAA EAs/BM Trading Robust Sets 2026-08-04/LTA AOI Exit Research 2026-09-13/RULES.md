# LTA volume-profile exits — frozen comparison

Approved research only, XAUUSD Exness Zero demo feed. No deployed EA, installer, website or live account change. Date windows are the existing system 6m/1y/3y/5y ending 2026-09-05 exclusive. Initial balance $10,000 USD, 1% equity sizing with the current EA's round-UP/minimum-lot policy; actual risk may exceed 1%. Current selected Safe Markov filter remains ON, portfolio adaptive overlay OFF to isolate exit behavior. Entries, initial SL, original entry profiles, daily consecutive-loss rule and all other settings stay unchanged.

Six predeclared variants, no parameter search:
0. Current fixed 3R TP.
1. Nearest favorable previous-day POC/VAH/VAL TP.
2. Nearest favorable previous-week POC/VAH/VAL TP.
3. Nearest favorable level among both profiles TP.
4. No TP; stair-step SL using both profiles frozen at entry.
5. No TP; stair-step SL using both profiles refreshed after each newly completed broker day/week.

User clarification during the run: no-TP must retain the same LTA entry logic, with only the exit changed. This is already true of the instrumented core. Variant 5 (rolling AOI trail) is the primary interpretation of that request; variant 4 is retained only as an extra diagnostic explaining why an entry-frozen ladder can leave a position open indefinitely. The original one-position-per-symbol rule remains unchanged; therefore identical entry logic does not imply identical executed trade counts after different exits.

AOI exit profiles use the existing 64-bin / 70% volume-profile algorithm and M15 broker bars, but a strictly exclusive period end (CopyRates end minus one second). Original entry-profile calculation is untouched; it currently includes the bar opening at the endpoint. That pre-existing boundary convention remains in the control and every variant to avoid mixing an entry change with an exit experiment. Volume is real volume when provided, otherwise broker tick volume; this is not centralized gold exchange volume or OANDA/TradingView replication.

TP is the nearest level strictly on the profitable side and beyond broker minimum distance, without any minimum-R optimization. No qualifying target => retain original 3R fallback, logged explicitly. Targets are frozen at entry. This preserves valid entries rather than silently removing trades with no target. Report target/fallback counts and actual initial R.

Trailing: require a completed M15 close crossing beyond a favorable AOI plus a fixed price buffer: max(0.05 x completed M15 ATR14 at ENTRY, 2 points). The preceding M15 close must be on the other side of that threshold. Both profiles form one sorted, deduplicated ladder. After breaking a rung, move SL to the immediately preceding rung in the trade direction, minus buffer for buys / plus buffer for sells. Can still be below entry for buys: this is not automatic break-even. Never loosen SL and respect current broker stop/freeze distance. No preceding rung => no change. Gap across several rungs => use the furthest crossed rung's predecessor. Once beyond the outermost rung, fixed-ladder variant keeps its last stop; rolling variant can use later completed profiles. Rolling profiles are loaded AFTER managing the just-closed candle, so a newly computed ladder is never credited with a break before it existed. Original protective SL always remains; no TP is not no SL. Freeze the buffer and entry price until flat; only one position at a time. Report failed modifications; keep old valid SL on rejection.

Risk stays per-trade equity-based, so different exits can produce different entry counts and lot sizes. This is an independent full strategy run per variant, NOT a same-entry trade-replay claim. Historical backtests are exploratory, not unseen out-of-sample evidence or a full pipeline/promotion.

Native MT5 model 4, 1ms base execution delay, loaded Exness commissions/swap/spreads. Pre-2026 ticks may be generated; preserve quality logs and mark this limitation. Historical fee schedules, dynamic leverage/HMR and all real-world slippage are not reconstructed. Isolated terminal only, Experts Enabled=0/AllowLiveTrading=0 and an empty research chart profile. The EA refuses non-tester initialization. No connecting a research EA to a live chart.

Verification: native deal ledger sums, net PF/win rate, per-tick equity DD, initial risk and RR, profile timestamps strictly before decision, directional targets, SL never widened, completed-bar confirmation, signed fees, runtime errors, original source fingerprints and baseline fidelity. Preserve all native optimization reports and per-case ledgers. Add individual native HTML reports for the control and comparison leader if useful.

References: [CopyRates interval semantics](https://www.mql5.com/en/docs/series/copyrates), [PositionModify return-code validation](https://www.mql5.com/en/docs/standardlibrary/tradeclasses/ctrade/ctradepositionmodify).
