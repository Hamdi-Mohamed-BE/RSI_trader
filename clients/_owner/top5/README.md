# Top Five — owner handoff

Only send `clients/top 5`. Its seven files are five EX5s, one BAT, and one standalone HTML. Never distribute this `_owner` directory: it contains strategy source/build tools and private native tester configuration.

## Licence and renewal

Initial term: 30 September 2026 17:39:14 UTC to 30 October 2026 17:39:14 UTC. Broker time ahead of UTC may stop entries a few hours early. Term starts at BUILD, not first installation. No automatic refresh. Expiry is compiled into EX5s, not an editable setting/BAT date.

Recipient login/server were not provided: this initial build has no permanent account binding. The installer requires account/server/symbol confirmation to prevent accidental cross-account operation. Those editable operational checks do NOT prevent redistribution. Offline checks are not unbreakable DRM and have no instant remote revocation. Do not promise otherwise.

Only after an owner/user explicitly requests renewal, run from the repository root:

```powershell
& 'C:\Program Files\Python313\python.exe' 'clients/_owner/top5/renew.py' --days 365
```

To also bind a renewed build, append `--login ACTUAL_NUMBER --server "EXACT_BROKER_SERVER"`. Never infer those values. The renewal tool retains prior delivery under `renewal-archive`, verifies trading-logic fingerprints unchanged, rebuilds the installer and preserves the explicitly dated historical report with a licence-only renewal notice. It does NOT claim fresh backtests for the new licence binary. If fingerprints change, it restores delivery and stops: new native benchmarks are required.

Send all seven replacement files; client reruns BAT and closes/reopens the selected terminal. Stable dedicated client magic IDs prevent duplicate charts during profile renewal. Existing binaries are backed up on the client. Restoring older expired binaries does not extend them.

## Runtime behaviour

- 17 October 2026 client-package change: Nasdaq 5M DI agreement is **OFF by default** in both the compiled EA input and the BAT's embedded profile settings. The input remains available for an explicit opt-in. `build.py` applies this client-only override without changing the shared Nasdaq source or Prop Ready's DI-ON settings. The licence expiry, risk logic and other four compiled EAs are unchanged. Rebuilding the Nasdaq default is not a licence renewal.

- Fixed USD or current BALANCE percentage per trade, per EA. Not equity percentage. USD hedging accounts only; percent limited to 5 by the client guard. No portfolio/daily loss cap was requested for this delivery; risk can stack.
- Volume rounds DOWN above the broker minimum. If the selected risk sizes below that minimum, the current client guard uses the broker **minimum lot**, logs the override and can exceed the selected risk. Stops/gaps/spread/commission/slippage can increase actual losses further. This differs from the earlier skip-below-minimum benchmark edition.
- EX5 guard intercepts native and CTrade order calls. New entries blocked at expiry; own pending entry orders cancelled. Own protective modification, partial/full closure continue. No ExpertRemove or forced liquidation at licence expiry.
- One-second timer checks alongside OnTick; original strategy logic/management still runs. Account/server/symbol mismatch refuses requests. Other/manual positions and orders are never licensed for management by these EAs.
- Runtime uses later of UTC/server time and a terminal global high-water check. This is conservative, not a trusted remote time service. Clock rollback prevention can be defeated by a sophisticated client controlling the environment. Broker disconnection affects management/cancellation.
- Native tester permits historical benchmarks; special test builds force expiry in history. Test EX5s are NOT shipped.

## Installer

Current onboarding follows the actual `installer.ps1` main flow: open and log in to the intended supported standard MT5, choose it from the numbered running-terminal list, select fixed USD/current-balance percentage and enter risk, then manually type the exact Gold/USD and Nasdaq CFD symbols from Market Watch (including broker suffixes). Other supported terminals may remain open and are not restarted. Submitting the Nasdaq symbol starts setup. The selected terminal closes gracefully; saved account/server/current profile are read and rechecked; the original profile is cloned and the selected terminal restarts once with five client EAs. EA management briefly pauses. Global AutoTrading stays unchanged; if already enabled, the EAs may trade immediately after attachment. The current main flow does **not** run automatic symbol discovery or verify typed symbols. USD hedging compatibility is enforced by the EAs on startup. No passwords, login override, DLLs or Python are required. Failure recovery attempts normal startup and never force-kills a terminal. The unused symbol-detector helpers do not change these actual prompts. Recipient demo acceptance is still required.

Saved account/profile checks are mandatory and rechecked. Research/Ava/portable/custom-config targets are refused. The original profile and unrelated charts remain intact. Existing EX5s are backed up before replacement. If AutoTrading is already on, attached EAs can trade after restart. Original selected-EA magic IDs in the source profile cause a duplicate-risk abort. The five trading binaries, expiry and native benchmark evidence remain unchanged by this installer-only revision.

The end-to-end interactive installation into the recipient's terminal still needs recipient demo acceptance. Automated fixture tests cover profile generation and safety checks; no normal MT5 profile/account was changed during packaging.

## Evidence

The original September 3m/6m native benchmarks below used Nasdaq DI **ON** and the earlier skip-below-minimum sizing policy; they are historical evidence, not results for the newly shipped DI-OFF/minimum-lot-override package. Do not relabel their statistics or source hashes as fresh tests. Current-package comparison evidence must have separate dates, inputs and compiled-binary hashes.

- `test_di_default.py`: client-only source override, generated MQL default, clean Nasdaq compilation, public EX5/BAT/manifest agreement and preservation of the other four binaries, risk guard and licence. `test_installer.ps1` additionally verifies DI OFF in the generated charts for both risk modes without installing into MT5.

- `test_native.py`: 20 native real-tick runs, $10k each, 150ms delay, fixed $100 and 1% current balance, 3m/6m through Sep 29, 2026. No optimization. Audits EX5/settings/report/ledger hashes and planned-risk rounding. `tests-native` contains original evidence.
- `test_expiry.py`: each EA expires halfway through its first position. Requires no subsequent entries and identical existing-position exit time/P&L to unexpired baseline.
- `test_guard.py`: tester-only harness checks expiry new-entry block, own pending cleanup, foreign-order protection, and protective modification/close after expiry.
- `test_installer.ps1`: fixture-only both risk modes, five charts, unrelated-chart preservation, renewal no duplication, original-EA duplicate block.
- `Install Top 5.bat --validate`: hashes five EX5s only. No terminal/account modification.
- `report.py`: initial report from exact audited compiled builds. Single-EA equity DD is native; combined is an independent closed-ledger overlay, NOT shared-account portfolio performance. Combined floating-equity DD is unavailable. All net fees/swap retained; rates/counts/streaks recomputed over closing deals.

Do not overwrite website evidence or publish these files automatically. Normal MT5 remained untouched. Paper/crypto projects are outside this task.
