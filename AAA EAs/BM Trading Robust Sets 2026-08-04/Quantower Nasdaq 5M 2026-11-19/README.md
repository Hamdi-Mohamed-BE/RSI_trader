# Calyx Nasdaq 5M for Quantower (2026-11-19)

Owner 2026-11-19: move the US100 bots to futures on Quantower, "let's start with the 5m bot".
Port of the production MT5 EA `Nasdaq 5M Carry Replace Deployment 2026-11-09/EA/Nasdaq 5M DI Wide ATR EA.mq5` (EX5 2488443f62a8) with the
Best 1-Step inputs. Quantower on this PC: `C:\Quantower\TradingPlatform\v1.146.17` (.NET 10). .NET SDK 10.0.404 installed 2026-11-19 (winget, owner approved).

## Files
- `src/CalyxNasdaq5M.cs` - the Quantower strategy (class `CalyxQuantower.CalyxNasdaq5M : Strategy`).
- `src/N5Logic.cs` - pure signal maths (EMA / ATR / DI with MT5 formulas, NY time), shared by the strategy and the test.
- `src/CalyxNasdaq5M.csproj` - builds against the installed `TradingPlatform.BusinessLayer.dll`; output `src/bin/CalyxNasdaq5M.dll`.
- `test/` - `export_bars.py` (USTEC M5 from the isolated research terminal), `ParityTest` (runs N5Logic on those bars), `compare.py` -> `PARITY.json`.

Build: `dotnet build -c Release` in `src/` (0 errors, 0 warnings).

## Rules (same as MT5)
| MT5 input / code | Quantower |
|---|---|
| M5, signal = closed 09:30 NY bar (Mon-Fri), entry at its close (09:35) | same; runs on `NewHistoryItem` (previous bar just closed) |
| Direction = close vs EMA(12) (iMA EMA) | same formula (seed = first close, alpha 2/13) |
| InpRequireDIAgreement (iADX +DI/-DI 14) | `Require DI agreement`, default OFF (profile default) |
| One entry per NY date; InpCarryMode 2 = REPLACE | same; `Carry` input 0 / 2 / 3 |
| Stop = entry -/+ 6 x iATR(14) of the signal bar (iATR = simple average of TR) | same, rounded to tick size; attached as the order's stop loss |
| No TP; ATR(14, current bar) x 6 trail from +1R, best price since entry, only tightens | same, checked at most once a second |
| No session close | `Flat time NY` = -1 (hold); set e.g. 1609 for prop firms that require flat by 15:10 CT |
| InpRiskPercent of equity, lots rounded UP | `Risk %` of **balance** (Best 1-Step 0.5% x 0.75 = 0.375 default); contracts rounded **DOWN** (skip if < 1) unless `Round contracts up` |
| magic number 862020 | futures accounts NET per contract: the strategy remembers the position it opened and refuses to enter if another position is on the same contract/account |
| - | `Trading enabled` default OFF = log signals only (no orders) |
| restart: deal history | restart-safe state file `%LOCALAPPDATA%\CalyxQuantower\n5m-<account>-<symbol>.txt` |

## Checks done (2026-11-19)
- Compile against Quantower 1.146.17: PASS (all API calls exist).
- Signal parity, the SAME `N5Logic.cs` on USTEC M5 bars vs the MT5 production EA entries (native Model 4, DI OFF, 2026-08-17 -> 11-18):
  **68 / 68 entry days and directions identical, no extra or missing day**. Stop distance (6 x ATR): mean difference 1.22 points (0.57%), max 4.25 points
  on 92-471 point stops; with Wilder's ATR instead the difference would be up to 110 points, so the formula is right; the rest = the terminal's stored
  M5 bars vs the tester's tick-built bars.

## NOT tested yet
- Order placement with the attached stop, the stop modification (trail), REPLACE close, position adoption and the state file inside Quantower
  (needs a Quantower Backtest & Optimize run or a simulation account).
- Futures data: NQ/MNQ prices differ from the USTEC CFD; contract roll (quarterly) is manual: pick the front month.
- Results under futures rules (contract rounding, commissions, flat-by-close) are not simulated.
2026-11-19 (owner "copy it"): `CalyxNasdaq5M.dll` (sha256 992038e80b0d...) + `.pdb` copied to
`C:\Quantower\TradingPlatform\v1.146.17\bin\Scripts\Strategies\CalyxNasdaq5M\` (new folder; Quantower was not running). No order was placed.
To remove: delete that folder. A rebuild must be copied again (and Quantower restarted if it was open).
