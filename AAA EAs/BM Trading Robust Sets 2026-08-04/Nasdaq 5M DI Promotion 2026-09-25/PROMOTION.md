# Nasdaq 5M Candle Momentum — DI filter promotion (2026-09-25)

User instruction (2026-09-25): apply the Nasdaq 5M DI filter to the system and website as a new option with its own
graph, selected by default; create a new BAT (named by the user **`claude_eas.bat`**, DI filter ON by default) that
keeps every BEST RECOMMENDED 2026-09-01 setting and changes only the Nasdaq 5M EA.

## What changed

| Item | Path | Note |
|---|---|---|
| DI production EA (new file) | `Active Portfolio Full Pipeline 2026-09-05/11 Nasdaq 5M Candle Momentum/EA/Nasdaq 5M Candle Momentum DI EA.mq5` / `.ex5` | Production v2.00 + `InpRequireDIAgreement` (default false) and `InpDIPeriod`; source = `Nasdaq 5M DI Filter Research 2026-09-23` EA with the production include path. MetaEditor 0 errors / 0 warnings; EX5 SHA-256 `49c4f03622a8ec7fb8e70db990a2f19b3006b5641aeb915a5d7f2454f26bab35`. The original production EA/EX5 are unchanged. |
| DI SET (new file) | `Selected Portfolio Settings 2026-09-01/11 Nasdaq 5M Candle Momentum - OPTIMIZED 2P5R + DI AGREE M5 - HARD 1PCT.set` | Installed SET + `InpRequireDIAgreement=true`, `InpDIPeriod=14`. |
| New BAT | `claude_eas.bat` | Copy of `BEST RECOMMENDED 2026-09-01.bat`; adds `-UseClaudeSelections`. Profile names `... - CLAUDE EAS`. |
| Installer / launcher | `_Auto Deploy/Install-BMTradingPortfolio.ps1`, `Start-Dynamic-Portfolio.ps1` | New switch `-UseClaudeSelections` (implies `-UseRecommendedSelections`); Nasdaq item gains `ClaudeExpertSource` / `ClaudeSetSource`, used only by that switch. Backups in `installer-backup-before-claude/`. |
| Website | `EA store/app/catalog.py`, `templates/detail.html` | Nasdaq 5M gets a "DI Filter" mode (the existing dynamic slot) that is the page default; Sell Nasdaq unchanged. Backups `catalog.py.before-di`, `detail.html.before-di`. |
| Website evidence | `EA store/data/evidence-cache/v1/products/nasdaq-5m-candle-momentum/dynamic/` + portfolio caches, manifest, consistency audit | DI windows 6m/1y/3y/5y ending 2026-09-07 (same as Standard) via `generate_di_cache.py`; portfolio rebuilt with `--portfolio-only` (windows unchanged, ending 2026-08-30). Pre-change caches in `cache-backup/`. |

**Unchanged by request:** `BEST RECOMMENDED 2026-09-01.bat`, `RECOMMENDED ADAPTIVE.bat` and all other BATs still install the
original Nasdaq 5M EA. The website portfolio graphs now use the DI version of Nasdaq 5M (website default), so they
match `claude_eas.bat`, not those BATs, for this one EA.

## Verification

- Parity (`run_native_parity.py`, `PARITY.json`, isolated tester, 2025-09-23 → 2026-09-23): the DI build with DI off
  reproduced all 256 production trades exactly. DI on reproduced the research DI run's 191 trades with identical
  entries, sides and exits; 6 weekend/holiday trades differ by cents in swap (the tester applies current swap rates —
  the unchanged production EX5 shows the same effect versus its own earlier run).
- Read-only `-ValidateOnly`: claude_eas configuration loads Nasdaq 5M with 54 inputs (DI SET); BEST RECOMMENDED still
  52 inputs; all 34 EAs present; nothing changed on any terminal.
- Website tests: 83 passed, 8 failed — the identical 8 fail on the pre-change baseline (tests hard-coded to 33 EAs,
  Gold Value Area logic-step count, the documented News Pulse source-hash assertion). No new failures.
- TestClient: Nasdaq page 200 with "DI Filter" default; series API returns DI and Standard; compare view shows
  Standard / Full Safe / DI Filter; portfolio page 200.

DI website evidence (native, Exness USTEC, $10,000, 1%): 6m +9.02% (PF 1.17, 90 trades); 1y +63.11% (PF 1.45, 189);
3y +120.38% (PF 1.27, 577); 5y +159.64% (PF 1.21, 971). Standard on the same windows: −0.18%, +42.61%, +111.87%, +105.74%.

## Open items / limitations

- **Pre-existing mismatch found:** the cached website Standard Nasdaq evidence records EX5 SHA `5d3a9f86…`, while the
  current production EX5 is `1cc526f1…` (rebuilt later in the adaptive-control commits). Not regenerated here.
- The DI rule was selected on 2025-09 → 2026-04 data; 2021-09 → 2025-08 was not used for the choice.
- The base EA's Friday/holiday session-close carry is unchanged in both modes.
- Updating files does not change any running MT5 chart; run `claude_eas.bat` yourself when ready.
- The public website must be restarted/redeployed by the owner to show the change.
