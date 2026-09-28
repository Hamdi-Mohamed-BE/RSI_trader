# Clear ORB trade comments — 28 September 2026

Comments identify the actual opening range, the signal/confirmation timeframe and the session start. The symbol is already shown on the MT5 position row. Existing position/history comments cannot be changed by this update.

| Current portfolio EA | New trade comment |
|---|---|
| ORB Volume Profile | `ORB 15m M5 NY09:30` |
| ORB Volume Profile Volume Confirmed | `ORB 15m M5 NY09:30 VolConf` |
| XAU ORB New York M30 | `ORB 30m M30 NY09:30` |
| XAU ORB London NY Overlap M30 | `ORB 5m M30 13UTC` |
| US100 ORB New York M30 | `ORB 5m M30 NY09:30` |
| US100 H1 ORB 13UTC | `ORB 1H M15 13UTC` |
| US100 Selective ORB V3 | `ORB 30m M5 NY09:30 V3Retest` |

The first duration is the opening range; the following M5/M15/M30 token is the signal timeframe. In particular, the XAU overlap and US100 New York M30 presets actually use a five-minute opening range. Labelling those simply “ORB 30m” would misstate the settings. `13UTC` is a fixed UTC session; `NY09:30` follows the EA's existing New York clock logic.

`VolConf` means at least one configured opening/breakout relative-volume minimum is greater than 1.0. It does not claim exchange volume or future performance. `VP` appears when an actual profile filter is enabled. Retest variants are marked `Retest`, `SelRetest` or `V3Retest`; the formatter shortens tags to `VC`/`RT` or omits a lower-priority tag only if needed to fit 31 characters. All seven current portfolio labels above fit without this shortening. Labels follow input changes automatically and are used for presentation only, never to determine ownership or trade management.

## Distribution

- The canonical ORB Volume Data and Selective ORB binaries are rebuilt in place, so the ordinary, recommended, Claude and adaptive BATs retain their existing file paths and settings.
- Both Ava Futures equivalents and the active ORB source/compiled export are rebuilt too.
- Only the two ORB binaries in the FTMO 13-EA package are recompiled. Its other eleven binaries, all preset inputs, risk guard, account locks, $50 planned stop-risk policy, Nasdaq DI selection and News-OFF policy remain unchanged.
- `RELEASE.json` is an explicit comment-only exception for rebuilding the FTMO package from its historical frozen sources. The historical `FROZEN.json`, SET files, backtest reports and cached website trade comments are not rewritten.
- No terminal was restarted, no production chart was reloaded and no trade/order was submitted. The update affects future orders only after the updated EA is loaded. Pulling files alone cannot update an EA already loaded in MT5. Do not run a reinstall over an active account merely to rename comments; use the launcher's normal flat-account/safety workflow.

## Verification and reproducibility

`build.py` compares all five edited EA sources against commit `53d4a171db59371248810cc3560a1dc185e6e1e4`: reversing only the new include and comment-construction expression must reproduce the original source exactly (line endings normalized). It compiles those sources with zero errors and warnings and writes old/new artifact fingerprints. The shared helper has no trading or account calls.

`CommentProbe.mq5` is tester-only and submits no orders. `run_probe.py` checks the actual native MQL formatter in the isolated research terminal; all 13 cases pass. `NATIVE-CHECK.json` records the output. Private tester configuration and journals remain ignored in `native/`. `tests/test_orb_comments.py` additionally checks real presets, release hashes and the FTMO package invariants. Git attributes preserve hashed source/package bytes across Windows checkouts.

This is a presentation-only update, not a new strategy optimization or a claim of improved trading results. Earlier RSI/MACD, PD-sweep and liquidity-continuation work reached completed rejection decisions; no failed research candidate was deployed.
