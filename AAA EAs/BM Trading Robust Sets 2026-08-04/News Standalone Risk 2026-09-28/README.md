# Separate news risk per order — v2.18

Implemented 28 September 2026 at the user's request. Scope: the eight portfolio BATs that already ask for ordinary trade risk. No installer was executed on a live terminal.

## What the user selects

The launcher asks separately for **news risk per ORDER in percent**. It is independent of ordinary EA percentage/fixed-dollar risk. Enter keeps the former 0.75% default; that value is no longer hard-coded as the only allowed value.

Example on $10,000 current equity: ordinary EA risk 0.50%, news risk 0.30%. A News Pulse order plans $30 to its initial stop. If both pending directions trigger, they plan $60 combined for that asset/event, before costs and execution effects. As equity changes, dollar risk changes; it is not a static $30 allocation.

- News Pulse XAU, XAG, BTC and EURUSD use the selected percentage of **current equity** at placement.
- Gold News V9 uses the same independently selected news percentage, but its existing sizing uses **current balance**.
- Both pending sides remain armed. No opposite-order cancellation was added.
- Event selection, placement times, anchors, distances, stops, targets, trailing and expiry rules are unchanged.
- News remains exempt from the ordinary adaptive risk taper and entry-stop controls. This is independent user sizing, not new adaptive management.
- Four simultaneous two-sided straddles can plan **8 × the selected percentage**, plus Gold News V9 exposure. Minimum lots/upward rounding, commissions, spreads, gaps and slippage can exceed the planned loss. This setting is not a guaranteed maximum-loss cap.
- **FTMO's dedicated 13-EA / NEWS OFF launcher is unchanged and news remains disabled.**
- Nasdaq 5M remains DI + wider stop + ATR, including its existing adaptive allocation.

## Launchers covered

1. `BEST RECOMMENDED 2026-09-01.bat`
2. `claude_eas.bat`
3. `INSTALL AND RUN DYNAMIC CONFIG ON ACTIVE MT5.bat`
4. `INSTALL AND RUN FULL SAFE ON ACTIVE MT5.bat`
5. `INSTALL AND RUN ON 100K MT5.bat`
6. `INSTALL AND RUN ON 900 USD MT5.bat`
7. `INSTALL AND RUN ON ACTIVE MT5.bat`
8. `RECOMMENDED ADAPTIVE.bat`

All route through `Start-Dynamic-Portfolio.ps1` and `Install-BMTradingPortfolio.ps1`. Direct scripted calls can pass `-NewsRiskPercent`. Non-interactive validation does not prompt. The accepted range is finite 0.00000001% to 10%; these are input bounds, not a recommended risk range. A tiny target can still be exceeded by minimum lot sizing.

Pulling Git changes alone does not change EAs already running on charts. The owner must review and run the chosen BAT to install the new compiled EA and selected inputs. Do not run the BAT merely to read this report. Website deployment/restart is owner-managed.

## Verification

- Both active News Pulse sources compiled with **0 errors, 0 warnings**. Their compiled v2.18 binaries are included.
- **16 native isolated MT5 cases passed**, four per asset: original binary at 0.75%, new binary at 0.75%, new binary at 0.30%, and new binary at 1.25%.
- Window: July 2026; Model 4, 150 ms delay, $10,000 start. These are functional release checks, not new annual performance estimates or a profitability claim.
- The old and new default-risk ledgers match **exactly** on each asset. Custom risk changes filled volumes but preserves tested entry/exit time, direction, prices and comments. Both pending sides are retained in the code and effective input checks.
- **67 focused automated tests passed**, covering 24 ordinary-risk/safety/adaptive/news-risk configurations, mocked prompts and child calls, invalid values, chart inputs, FTMO news-off status, current Nasdaq selection, news website evidence, and fail-closed integrity checks.
- The legacy source's stale hash assertion was corrected to the pre-release committed source at `03a47d30`, with CRLF/LF normalization. The legacy code itself is unchanged; normalized working-copy content equals that pre-release commit.
- Historical website returns remain based on **0.75% per order**. They are not rescaled to the user's custom risk. A strict compatibility record links the unchanged historical source to the verified risk-only release; missing/changed source, binary, baseline or parity evidence is rejected.

`BUILD.json` and `NATIVE_VERIFICATION.json` retain hashes and sanitized functional evidence. `baseline/` preserves the former source and binaries. `verify_native.py` reuses the existing isolated tester only; private account INIs, journals and native working files stay local and are excluded from Git. No normal MT5 chart, position or account setting was changed.
