# Nasdaq 5M: ATR(14) x 6 initial stop everywhere (2026-11-02)

**Owner request (2026-11-02):** "apply the best nasdaq 5m everywhere ... update the website section ... push ... update all portfolios".

This is an explicit owner choice. It is **not** a qualified pipeline version.

## What changed
- **The one change:** the initial stop is now `6 x M5 ATR(14)` (`InpStopMode=0`, `InpInitialStopATR=6.0`). Before, it was `0.60% of price` (`InpStopMode=2`).
- **Unchanged:**
  - the EX5 (`fe9f391db5af`) and every guarded wrapper EX5 (the stop settings are real inputs; nothing recompiled);
  - the signal: 09:30 NY M5, EMA12 + DI14;
  - the DI choice of each launcher;
  - no TP, the ATR6 trail from +1R, and overnight/weekend holding;
  - every launcher's risk policy (Adaptive 0.25x, FTMO $50 cap, Prop Ready / Best Prop guards).

| Old | New |
|---|---|
| SET `Selected Portfolio Settings 2026-09-01/11 Nasdaq 5M - DI WIDE 0P60PCT ATR6 NO TP - 1PCT.set` (kept for history) | SET `11 Nasdaq 5M - DI ATR6 STOP ATR6 TRAIL NO TP - 1PCT.set`, sha `35783fc7a48d` |

## Evidence (`Nasdaq 5M Wide Stop Pipeline 2026-11-02`, native MT5, USTEC M5, 1%, $10k, 150 ms, recorded commission/swap)
The study searched 124 versions on Model 1 over 2019-01 → 2026-11. Three finalists were re-run on Model 4. Every trade matched the Model 1 run (same entry minute and direction). Real-tick fills cost about 0.01R per trade.

| Model 4, 2019-26 | ATR6 stop (new) | 0.60% stop (old) |
|---|---:|---:|
| Development 2019-23: PF / return | 1.10 / +50.2% | 0.98 / −10.0% |
| Validation 2023-24 | 1.03 / +3.2% | 0.93 / −7.3% |
| OOS 2024-26 (viewed during the search) | 1.28 / +70.4% | 1.60 / +213.4% |
| All 2019-26: return / PF / closed DD | +164.1% / 1.16 / 24.0% | +161.6% / 1.20 / 39.2% |
| Trades (per week) | 1,308 (3.2) | 1,343 (3.29) |
| Worst year | 2020 −11.6% | 2020 −27.5% |
| Monte Carlo (1 y, 2,000 paths, 4-week blocks): P(losing year) / median return / DD p95 | 20% / +14.2% / 22.7% | 26% / +12.6% / 27.4% |

**Website windows** (the new native runs end 2026-11-01):

| Window | ATR6 return / PF / trades | Old 0.60% stop, same window (replay of its Model 4 ledger) |
|---|---|---|
| 6 months | +14.27% / 1.32 / 87 | +19.6% / 1.44 / 88 |
| 1 year | +30.77% / 1.31 / 173 | +48.1% / 1.48 / 178 |
| 3 years | +76.2% / 1.21 / 539 | +190.5% / 1.42 / 536 |
| 5 years | +113.49% / 1.18 / 887 (equity DD 20.49% MT5 maximal) | +219.4% / 1.26 / 923 |

**Read this honestly:**
- On every recent window the old stop earned more, at a similar closed drawdown.
- The ATR6 stop wins on 2019-2023 and on worst-case drawdown.
- Its development PF on real-tick fills (1.10) is below the 1.15 gate.
- All years were seen during the search, so the OOS figures are retrospective.
- October 2026: ATR6 made +4.40% (17 trades, PF 1.60) against +3.42% for the old stop, on the same 17 signals.
- The ATR stop is not always wider. Its median stop-out distance is 0.61% of price (p10 0.28%, p90 1.20%).

## Updated (all checked offline; no MT5 terminal, chart, account or AutoTrading touched)
- **Canonical installer** `_Auto Deploy/Install-BMTradingPortfolio.ps1` (SetSource + ClaudeSetSource): this covers every normal root BAT, `claude_eas`, `reviwed_Eas` and the Full EA portfolio.
- **Package SETs, plus their manifest hashes and recorded inputs:**
  - FTMO Thirteen;
  - FTMO17, FTMO-AnyBroker, PropReady (= Prop ready / Codex_Best_FTMO);
  - Best Prop 9, Best Prop 15;
  - FundedV1 (funded_v1), Turbo5 (Turbo 50k Custom 5);
  - the Turbo 50k Funded research files;
  - Current14 + ORB 0.5R: Package, Checksums, the single-file `current14_orb05.bat` rebuilt `--no-compile`, and `Verify-Release.py` PASS.
- **Generator-owned folders** regenerated with `build_live_profiles launchers`. This also synced the any-broker EX5 copies and the package versions in `Profiles.json` to the 2026-10-30 risk-cap rebuild that was already committed (`89cb62575`).
- **Installer messages and BAT comments** now describe the ATR stop.
- **Website:**
  - the Nasdaq product's dynamic caches 6m/1y/3y/5y (`deploy.py publish`, report/input/trade-count/net checks);
  - the catalog text, with the mode renamed "DI + ATR6 Stop + ATR Trail";
  - the tests.

`deploy.py prepare | pins | publish` reproduces the file changes. `PREPARE.json` lists the hash map. Rollback copies are in the local, git-ignored `before*/` folders; git history also has every original.

## Not done / limitations
- **Not updated:** the combined website portfolio cache. `precompute_evidence_cache --portfolio-only` refuses because the News Pulse XAU 6m evidence fails its freshness check. That guard is fail-closed and was not bypassed, so the cache stays at its 2026-10-02 build.
- **Portfolio library histories (`data/portfolios.json`) were not re-simulated.** The site now shows its built-in warning: "A launcher manifest changed after this publication". Removing it requires new native runs of each package's own wrapper builds plus a re-run of the portfolio engines.
- **Earlier results no longer describe these portfolios.** Previous portfolio, FTMO, prop and income results used the 0.60% stop.
- **Left alone:**
  - the issued `clients/top 5` licensed package (an issued, licensed build);
  - Ava;
  - archived research snapshots;
  - superseded builds.
- **Pre-existing, unrelated:** `reviwed_Eas.bat -ValidateOnly` fails. Its selection manifest has had 27 'live' entries since the 2026-10-13 ORB commit, while `Reviewed-Portfolio-Policy.ps1` requires 25.
- **Still open:** the market-closed stop-modify retries reported before remain (≈100k–400k rejected requests per tester run). A demo check of broker request limits is still required.
- **Push does not deploy.** A git push does not change running MT5 charts or the public VPS website. The owner re-applies a BAT and updates the VPS.
