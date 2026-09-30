# 3 Way Gold — system integration (2026-09-30)

At the user's request the optimised gold trio from `QuantLab Gold Trio Pipeline 2026-09-30` was added to the system as
**3 Way Gold**. The name is unrelated to the older research folders `3 way gold * 2026-09-13` (a different
momentum/trend-change/breakout engine that was never deployed); those stay research-only.

Nothing was installed on a terminal, no MT5 chart/SET/AutoTrading was changed, nothing was pushed or published.

## What was added

| Item | Path |
|---|---|
| Production EA | `3 Way Gold EA/3 Way Gold EA.mq5` / `.ex5` (EX5 SHA-256 `63d2dd2744a9e917…`, compiled 0 errors / 0 warnings on the MT5 build installed 2026-09-30) |
| Normal SET | `Selected Portfolio Settings 2026-09-01/25 3 Way Gold - BEST OPTIMISED - 1PCT PER MODULE.set` |
| Installer item | `_Auto Deploy/Install-BMTradingPortfolio.ps1` (label `3 Way Gold`, XAUUSD, M15 chart) — used by all eight normal BATs via `Start-Dynamic-Portfolio.ps1`; `AVA EAS.bat` untouched |
| FTMO SET (market entries) | `3 Way Gold Deployment 2026-09-30/Sets/3 Way Gold - FTMO MARKET ENTRIES.set` |
| FTMO package entry 14 | `FTMO Thirteen EA Deployment 2026-09-27/package/FTMO13-3-way-gold.*`, manifest version `FTMO14-20260930-3WAYGOLD-MARKET` |
| FTMO launcher | `_Auto Deploy/Install-FTMO13.ps1` now expects 14 entries; BAT title updated (file name kept for compatibility) |
| Website | catalogue product `3-way-gold` (`app/catalog.py`), evidence cache 6m/1y/3y/5y ending 2026-09-05, portfolio caches regenerated |

## Behaviour

- Three independent modules on one XAUUSD chart (magic 930930100 / 101 / 102), each sized from the BAT's risk
  setting: percent of equity or fixed USD per **module** trade; adaptive governor when the BAT enables it. Up to three
  positions can be open together, so combined planned risk can reach 3× the per-trade setting. Lots are rounded up
  (broker minimum if needed), as with every normal Calyx EA.
- Settings are locked to the frozen BEST version (momentum H4, breakout M15 London–NY overlap, turn of month).
- Session filters are in UTC; live accounts derive the broker's UTC offset automatically. H4/D1 candles still follow
  the broker's server clock, so bars can differ from the Exness (UTC) backtests on brokers with other server times.
- Trailing-stop updates rejected during the daily market break are retried after the reopen.
- Requires a hedging account.

## FTMO build

The FTMO guard admits market entries only (pending orders are rejected and block all entries), so the user chose the
**market-entry variant**: `InpMarketEntries=true`, momentum and breakout enter at market; the guard applies $50 maximum
planned stop risk per trade (rounded down), $225 total / $150 per symbol open risk, 7 entries/day, account/server/symbol
locks. Guard source unchanged (same SHA as before). The market variant was defined after the frozen results were
seen (compatibility diagnostic), so it has no independent out-of-sample test:

| Native Model 4, 1% per module | 5y 2021-09→2026-09 | Older holdout 2019-09→2021-09 | Last year |
|---|---|---|---|
| BEST (limit entries, normal BATs) | +114.3%, PF 1.44, DD 7.9%, 439 trades | −20.3%, PF 0.74 | +14.5%, PF 1.38 |
| Market entries (FTMO) | +108.7%, PF 1.35, DD 11.5%, 562 trades | −6.6%, PF 0.93 | +24.2%, PF 1.44 |

The guarded build cannot run in the Strategy Tester (the guard blocks the tester by design); FTMO $50 sizing and the
guard caps change the results above. XAUUSD positions share the guard's $150 per-symbol cap with the other gold EAs,
so some 3 Way Gold entries will be refused when gold exposure is already high.

## Verification

- Parity (`PARITY.json`, native 5y, same windows): production with `InpMarketEntries=false` reproduced the research
  BEST trio exactly (439/439 positions, +$11,435.14); with `true` it reproduced the research market variant exactly
  (562/562, +$10,870.84).
- The MT5 terminal auto-updated during the first parity run ("tester forced to close"); the EA was recompiled and both
  parity runs were repeated on the new build.
- `-ValidateOnly`: all normal BAT modes (Best Recommended, Dynamic percent/USD, Full Safe, Standard, Recommended
  Adaptive, Claude EAs) and the FTMO launcher pass; no account accessed.
- FTMO package: the original 13 entries, all their files and the guard are byte-identical; only 4 files were added.

## Evidence status

Research evidence only — the optimised settings lost 20.3% on the untouched 2019–2021 holdout and the deflated Sharpe
was 63% (pipeline requires 95%). The website labels the product "Watch only - failed older holdout". Demo first.
