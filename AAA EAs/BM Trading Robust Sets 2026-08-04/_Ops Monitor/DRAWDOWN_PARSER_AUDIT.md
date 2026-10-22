# Drawdown parser audit: MT5 "Maximal" vs "Relative" (2026-10-22)

Research and audit only. No live MT5 was used, and no SET, BAT, installer, website, evidence-cache or study artifact was changed. Nothing was pushed.
The parser proposal is on a local branch only (section 7) and needs owner approval.

## 1. Findings in brief

- **Scope.** 5,198 native MT5 reports were parsed:
  - 4,971 under `native*/` folders in 153 study folders;
  - 227 in the EA store caches (`data/evidence-cache`, `data/evidence-jobs`).
- **Flagged.** 290 report files (266 unique reports, 60 study folders plus the EA store caches) have relative minus maximal above 0.5 percentage points (pp):
  - 255 on equity drawdown and 197 on balance drawdown;
  - the largest gaps are 30.35 pp on equity and 18.71 pp on balance;
  - maximal never exceeded relative in any report, as the definitions require.
- **Website (local EA store data).** 10 cached payloads that the site shows for an EA's recommended mode understate the equity drawdown (table W1).
  - Worst: Nasdaq 5M Candle Momentum, dynamic, 3y shows 10.06%; the worst percentage drawdown was 21.44%.
  - Default 1y view: XAU Weakness (safe) shows 5.76% instead of 6.90%.
  - The News Pulse payloads already show the relative figure.
- **Study documents.** 26 runs in 10 study folders have a `.md` file that quotes the maximal value as the drawdown (table D1).
  - Biggest case: the current Nasdaq 5M DI version, 5y, is reported as "DD 10.9%". The relative figure is 20.56%.
- **CLAUDE.md.** Every continuity line that quotes a flagged run already uses the relative figure (table C1). Turtle and BTC TSM also label the maximal figure explicitly.
  - No drawdown correction is needed in CLAUDE.md.
  - The note "7 pre-existing `test_store.py` failures" is stale: the main checkout fails 10 today (section 7.4).
- **Proposal.** Branch `audit/drawdown-parser-proposal`, commit `b41e0de17` (not merged, not pushed):
  - `max_drawdown_pct` becomes equity relative;
  - the change adds `equity_dd_rel_pct`, `balance_dd_rel_pct`, `equity_dd_maximal_pct`, `balance_dd_maximal_pct` and `drawdown_basis`.
- **Verification.**
  - The proposed parser matches an independent scan on all 5,176 non-empty reports (0 mismatches).
  - The EA store suite fails the same 60 tests with and without the change in the isolated worktree. All 60 are pre-existing or environmental; the 2 new tests pass.

## 2. What MT5 prints

| MT5 field | Printed as | Meaning |
|---|---|---|
| Equity / Balance Drawdown **Maximal** | `$amount (x%)` | The largest dollar drawdown. x% is that dollar loss divided by the peak it fell from. |
| Equity / Balance Drawdown **Relative** | `y% ($amount)` | The largest percentage drawdown, and the dollar loss at that point. |

On a run that grew, an early drawdown from a small peak can be the worst in percentage terms, while a later drawdown from a large peak is the largest in dollars. Then x% < y%.

Example: Turtle HOLD 5y (`Turtle Breakout Raw 2026-10-22/native/nw-BTCUSD-HOLD-5y`):
- 177 trades, 2.95 trades/month, 0.136 trades/weekday;
- equity drawdown maximal: $93,099 (35.08%);
- equity drawdown relative: 46.90% ($48,776).

Balance relative can also exceed equity relative, because the two use different peaks:
- Turtle HOLD 5y: balance 50.24% vs equity 46.90%;
- 70 of the 5,198 reports show a balance gap of more than 0.5 pp.

So the two figures should be shown side by side, not merged.

## 3. Method

- **Files.** Every `*.htm` / `*.htm.gz` with a `native*` folder in its path under `AAA EAs/BM Trading Robust Sets 2026-08-04/`, plus every report in `AAA EAs/EA store/data/evidence-cache/` and `data/evidence-jobs/`.
  - 18 empty failed-attempt reports (0 trades, no test period) were parsed and excluded from the parity check.
- **Snapshot.** The tool run was 2026-10-22 15:02 UTC.
  - Another session was writing `Nasdaq 5M DI One Month / Two Week 2026-10-22` reports during the audit, so 4 more reports were parsed than in the first pass.
  - The flagged set did not change.
- **Fields.** For each report:
  - symbol, timeframe, tester window, deposit, net profit, PF;
  - Total Trades;
  - equity and balance drawdown, Maximal and Relative (both $ and %);
  - the SHA-256 of the report;
  - the `max_drawdown_pct` that a study harness stored next to it (`run.json` → `metrics`), when present.
- **Frequency columns.**
  - Trades = MT5 "Total Trades" (closed deals; partial exits count separately). It can differ from a study's own position count.
  - Trades/month = trades ÷ (calendar days ÷ 30.4375).
  - Trades/day is shown as trades per weekday (Mon–Fri in the tester window). BTC also trades at weekends, so its per-calendar-day rate is lower.
- **Citations.**
  - Study docs: every `.md` in the study folder, outside `native*`. A doc quotes a value when it shows it at 2 dp, or at 1 dp with a "%".
    - The match counts as strong when the same line also holds the run's trade count, return or PF.
    - Table D1 lists strong matches only, after a manual check that removed 2 false positives (section 5).
    - A further 32 flagged runs have weak (uncorroborated) value matches only; they are not listed.
  - CLAUDE.md: the same test on a ±1-line window, then checked by hand.
  - Website:
    - each EA store report was matched to the cached product payload the site serves (`products/<slug>/<mode>/<period>.json`);
    - each payload's recommended mode was looked up with the site's own `_recommended_mode`;
    - study folders read by `app/*.py` and identical report hashes were recorded.
- **Tool.** `_Ops Monitor/drawdown_audit.py`. Output is in `_Ops Monitor/output/drawdown-audit/` (`flagged.json`, `scan.json.gz`, `tables.md`).

## 4. Website evidence

The site's cards, detail pages and period selector read the cached payloads through `app/main.py::_cached_display_product`. The default period is 1y; 6m, 3y and 5y are selectable.

`max_drawdown_pct` in those payloads comes from one of three sources:
- `_native_metrics`, which gives equity **maximal**;
- `independent_news_result` for News Pulse, which gives equity **relative**;
- `portfolio_metrics`, used when a window is trimmed, which gives the worst closed-balance percentage.

This is the local data. The public site (calyx.duckdns.org on the VPS) runs an older build and was not checked.

### W1. Payloads shown for the recommended mode (understated)

| EA (slug) | Mode | Period | Window | Trades | Trades/mo | Trades/weekday | Return % | Shown "Max DD" % (= equity maximal) | Equity DD relative % | Understated by pp | Balance DD max → rel % |
|---|---|---|---|---|---|---|---|---|---|---|---|
| nasdaq-5m-candle-momentum | dynamic | 3y | 2023-09-25 → 2026-09-25 | 536 | 14.89 | 0.684 | +162.16 | 10.06 | 21.44 | 11.38 | 8.94 → 20.25 |
| xau-regime-switch | standard | 5y | 2021-09-01 → 2026-09-01 | 211 | 3.52 | 0.162 | +96.19 | 10.21 | 15.39 | 5.18 | 7.22 → 12.98 |
| xau-weakness | safe | 3y | 2023-09-05 → 2026-09-05 | 181 | 5.03 | 0.231 | +127.19 | 6.82 | 11.49 | 4.67 | 5.84 → 10.84 |
| xau-regime-switch | standard | 3y | 2023-09-01 → 2026-09-01 | 117 | 3.25 | 0.150 | +88.30 | 10.39 | 12.33 | 1.94 | 7.48 → 9.80 |
| lta-volume-profile | safe | 5y | 2021-09-05 → 2026-09-05 | 609 | 10.15 | 0.467 | +128.30 | 20.52 | 22.09 | 1.57 | 19.20 → 20.65 |
| xau-weakness | safe | 1y | 2025-09-05 → 2026-09-05 | 85 | 7.09 | 0.326 | +56.93 | 5.76 | 6.90 | 1.14 | 4.33 → 4.69 |
| lta-volume-profile | safe | 6m | 2026-03-05 → 2026-09-05 | 107 | 17.70 | 0.811 | +29.70 | 7.77 | 8.86 | 1.09 | 7.40 → 7.40 |
| sell-nasdaq-15min | dynamic | 3y | 2023-09-07 → 2026-09-07 | 159 | 4.42 | 0.203 | +94.91 | 7.82 | 8.89 | 1.07 | 5.87 → 7.55 |
| us100-month-end-flow | standard | 5y | 2021-08-31 → 2026-08-31 | 175 | 2.92 | 0.134 | +37.84 | 9.13 | 9.68 | 0.55 | 7.79 → 7.79 |
| orb-volume-profile | standard | 5y | 2021-09-05 → 2026-09-05 | 304 | 5.07 | 0.233 | +59.19 | 6.14 | 6.68 | 0.54 | 5.34 → 5.71 |

None of these 10 payloads would cross the catalogue's 25% "Validated evidence" limit (`catalog._status_for`) with the relative figure. The highest is 22.09%.
In table W2, Nasdaq 5M standard 5y (not the default mode) would be 24.93%, just under the limit.

### W2. Other flagged EA store payloads

| EA (slug) | Mode | Period | Window | Trades | Trades/mo | Trades/weekday | Return % | Shown % | Equity DD max → rel % | Balance DD max → rel % | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| news-pulse-eurusd | standard | 1y | 2025-09-05 → 2026-09-05 | 46 | 3.84 | 0.176 | +919.45 | 21.12 | 4.26 → 21.12 | 11.94 → 11.94 | relative already shown |
| news-pulse-eurusd | standard | 5y | 2021-09-05 → 2026-09-05 | 240 | 4.00 | 0.184 | +38947.79 | 16.52 | 3.33 → 16.52 | 1.14 → 5.18 | relative already shown |
| nasdaq-5m-candle-momentum | standard | 5y | 2021-09-07 → 2026-09-07 | 1272 | 21.20 | 0.975 | +105.74 | 12.63 | 12.63 → 24.93 | 11.50 → 24.15 | maximal shown, but not the recommended (default) mode |
| news-pulse-btc | standard | 3y | 2023-09-05 → 2026-09-05 | 147 | 4.08 | 0.188 | +24256.27 | 32.35 | 20.07 → 32.35 | 14.02 → 25.38 | relative already shown |
| news-pulse-btc | standard | 5y | 2021-09-05 → 2026-09-05 | 242 | 4.03 | 0.185 | +43775.44 | 25.13 | 13.32 → 25.13 | 10.01 → 20.66 | relative already shown |
| xau-slow-trend | standard | 5y | 2021-09-05 → 2026-09-05 | 245 | 4.08 | 0.188 | +86.18 | 20.48 | 12.63 → 22.04 | 11.07 → 21.68 | payload built elsewhere (1020 trades vs 245 in this report); its DD basis was not determined here |
| news-pulse-xag | standard | 5y | 2021-09-05 → 2026-09-05 | 139 | 2.32 | 0.107 | +5340.19 | 17.97 | 8.78 → 17.97 | 4.15 → 18.17 | relative already shown |
| news-pulse-eurusd | standard | 3y | 2023-09-05 → 2026-09-05 | 147 | 4.08 | 0.188 | +21300.13 | 18.36 | 9.39 → 18.36 | 2.46 → 3.93 | relative already shown |
| nasdaq-5m-candle-momentum | standard | 3y | 2023-09-07 → 2026-09-07 | 762 | 21.16 | 0.974 | +111.87 | 12.63 | 12.63 → 20.62 | 11.49 → 19.64 | maximal shown, but not the recommended (default) mode |
| news-pulse-btc | standard | 1y | 2025-09-05 → 2026-09-05 | 52 | 4.34 | 0.199 | +6344.62 | 12.21 | 7.72 → 12.21 | 5.00 → 5.00 | relative already shown |
| xau-weakness | standard | 3y | 2023-09-05 → 2026-09-05 | 391 | 10.86 | 0.499 | +228.23 | 13.65 | 13.65 → 17.85 | 11.63 → 16.83 | maximal shown, but not the recommended (default) mode |
| news-pulse-xag | standard | 3y | 2023-09-05 → 2026-09-05 | 90 | 2.50 | 0.115 | +3719.67 | 11.54 | 8.78 → 11.54 | 4.15 → 11.46 | relative already shown |
| news-pulse-xag | standard | 1y | 2025-09-05 → 2026-09-05 | 34 | 2.84 | 0.130 | +2079.63 | 11.42 | 8.77 → 11.42 | 4.15 → 11.44 | relative already shown |
| news-pulse-xau | standard | 1y | 2025-09-05 → 2026-09-05 | 40 | 3.34 | 0.153 | +300.00 | 6.68 | 4.50 → 6.68 | 5.28 → 5.28 | relative already shown |
| news-pulse-xau | standard | 6m | 2026-03-05 → 2026-09-05 | 22 | 3.64 | 0.167 | +167.04 | 6.67 | 4.53 → 6.67 | 5.27 → 5.27 | relative already shown |
| news-pulse-xau | standard | 3y | 2023-09-05 → 2026-09-05 | 121 | 3.36 | 0.154 | +1029.12 | 6.61 | 4.49 → 6.61 | 5.22 → 5.22 | relative already shown |
| news-pulse-xau | standard | 5y | 2021-09-05 → 2026-09-05 | 194 | 3.23 | 0.149 | +2394.29 | 6.60 | 4.49 → 6.60 | 5.21 → 5.21 | relative already shown |
| news-pulse-eurusd | standard | 6m | 2026-03-05 → 2026-09-05 | 24 | 3.97 | 0.182 | +394.50 | 5.86 | 4.26 → 5.86 | 5.27 → 5.27 | relative already shown |
| asia-breakout | safe | 5y | 2021-09-05 → 2026-09-05 | 187 | 3.12 | 0.143 | +45.50 | 6.27 | 6.27 → 7.76 | 7.43 → 7.43 | maximal shown, but not the recommended (default) mode |
| news-pulse-btc | standard | 6m | 2026-03-05 → 2026-09-05 | 29 | 4.80 | 0.220 | +303.43 | 9.97 | 8.74 → 9.97 | 4.05 → 5.00 | relative already shown |
| asia-breakout | standard | 5y | 2021-10-02 → 2026-10-02 | 189 | 3.15 | 0.145 | +46.33 | 9.25 | 8.29 → 9.25 | 6.62 → 8.41 | relative already shown |
| xau-trend-progression | standard | 5y | 2021-10-02 → 2026-10-02 | 214 | 3.57 | 0.164 | +13.19 | 8.80 | 8.18 → 8.80 | 8.34 → 8.34 | relative already shown |
| btc-poc-fibonacci | standard | 5y | 2021-09-05 → 2026-09-05 | 114 | 1.90 | 0.087 | +44.30 | 14.10 | 14.10 → 14.10 | 8.70 → 11.50 | relative already shown |
| news-pulse-xag | standard | 6m | 2026-03-05 → 2026-09-05 | 18 | 2.98 | 0.136 | +400.72 | 8.79 | 8.79 → 8.79 | 4.16 → 8.81 | relative already shown |
| us100-hourly-profiles | standard | 1y | 2025-10-03 → 2026-10-03 | 1171 | 97.65 | 4.487 | +62.05 | 8.29 | 8.29 → 8.29 | 4.49 → 6.80 | relative already shown; not in the sellable catalogue |
| xau-elliott-wave-1-2-3 | standard | 5y | 2021-09-05 → 2026-09-05 | 116 | 1.93 | 0.089 | +72.30 | 10.59 | 10.59 → 10.59 | 6.47 → 8.15 | relative already shown |
| btc-poc-fibonacci | fresh job | latest.json | 2016-09-05 → 2026-09-05 | 145 | 1.21 | 0.056 | +58.43 | 14.17 | 14.17 → 14.17 | 8.74 → 11.56 | on-demand job result (latest.json is written, not read by the site) |
| us100-orb-new-york-m30 | fresh job | latest.json | 2023-09-09 → 2026-09-08 | 43 | 1.20 | 0.055 | +51.60 | 5.51 | 5.51 → 6.30 | 4.50 → 5.66 | on-demand job result (latest.json is written, not read by the site) |
| xau-trend-progression | fresh job | latest.json | 2024-02-28 → 2026-09-08 | 53 | 1.75 | 0.080 | +122.87 | 11.12 | 11.12 → 11.12 | 5.45 → 9.50 | on-demand job result (latest.json is written, not read by the site) |
| xau-weakness | fresh job | latest.json | 2024-02-28 → 2026-09-08 | 150 | 4.95 | 0.228 | +120.65 | 15.23 | 15.23 → 17.31 | 14.07 → 15.60 | on-demand job result (latest.json is written, not read by the site) |

## 5. Study documents that quote the maximal value

Manual check of the strong matches:
- **Removed:**
  - QuantLab Gold Trio Pipeline `REPORT.md:45`: the 10.2% is its "Bal DD" column; its "Eq DD" column shows the relative 11.5%.
  - Crypto Stock Edge Screen `REPORT.md:25`: the 8.4% is an ETH return.
- **Partly superseded:**
  - 3 Way Volume Profile Pipeline: `AUDITED RESULTS.md` and `FINAL REPORT.md` already use relative; only the earlier `RESULTS.md` quotes maximal.
  - BTC Time Series Momentum: `REPORT.md` was corrected to 26.1%. The generated `RESULTS.md` still prints "native eq DD 22.07%" (maximal).

### D1. Runs whose study `.md` quotes the maximal drawdown (after manual check)

| Study | Run | Window | Trades | Trades/mo | Trades/weekday | Return % | PF | Eq DD max → rel % | Bal DD max → rel % | Quoted maximal value in | Relative also quoted? |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 Way Volume Profile Pipeline 2026-09-26 | qual-USDJPY-ALL-3y-m1-raw/qual-USDJPY-ALL-3y-m1-raw.htm.gz | 2023-09-26 → 2026-09-26 | 562 | 15.61 | 0.717 | +111.90 | 1.22 | 17.71 → 19.49 | 16.03 → 19.04 | `RESULTS.md`:13 (equity) | no |
| 3 Way Volume Profile Pipeline 2026-09-26 | qual-USDJPY-ALL-3y-m4-raw/qual-USDJPY-ALL-3y-m4-raw.htm.gz | 2023-09-26 → 2026-09-26 | 554 | 15.39 | 0.707 | +84.44 | 1.18 | 16.53 → 21.79 | 15.04 → 21.61 | `RESULTS.md`:14 (equity) | `AUDITED RESULTS.md`:13 |
| 3 Way Volume Profile Pipeline 2026-09-26 | qual-USDJPY-ALL-5y-m1-raw/qual-USDJPY-ALL-5y-m1-raw.htm.gz | 2021-09-26 → 2026-09-26 | 921 | 15.35 | 0.706 | +130.54 | 1.16 | 17.73 → 27.57 | 16.05 → 26.98 | `RESULTS.md`:15 (equity) | no |
| 3 Way Volume Profile Pipeline 2026-09-26 | qual-USDJPY-ALL-5y-m4-raw/qual-USDJPY-ALL-5y-m4-raw.htm.gz | 2021-09-26 → 2026-09-26 | 913 | 15.22 | 0.700 | +99.12 | 1.13 | 16.47 → 27.73 | 27.37 → 27.37 | `RESULTS.md`:16 (equity) | `AUDITED RESULTS.md`:14; `FINAL REPORT.md`:13 |
| 3 Way Volume Profile Pipeline 2026-09-26 | qual-XAUUSD-BRK-3y-m1-raw/qual-XAUUSD-BRK-3y-m1-raw.htm.gz | 2023-09-26 → 2026-09-26 | 270 | 7.50 | 0.344 | +99.17 | 1.39 | 11.98 → 13.73 | 11.32 → 12.65 | `RESULTS.md`:22 (equity) | no |
| 3 Way Volume Profile Pipeline 2026-09-26 | qual-XAUUSD-BRK-3y-m4-raw/qual-XAUUSD-BRK-3y-m4-raw.htm.gz | 2023-09-26 → 2026-09-26 | 270 | 7.50 | 0.344 | +93.10 | 1.37 | 12.02 → 13.79 | 11.36 → 12.71 | `RESULTS.md`:26 (equity) | `AUDITED RESULTS.md`:18 |
| 3 Way Volume Profile Pipeline 2026-09-26 | qual-XAUUSD-BRK-5y-m1-raw/qual-XAUUSD-BRK-5y-m1-raw.htm.gz | 2021-09-26 → 2026-09-26 | 446 | 7.43 | 0.342 | +93.96 | 1.26 | 11.53 → 16.04 | 10.85 → 15.20 | `RESULTS.md`:27 (equity) | no |
| 3 Way Volume Profile Pipeline 2026-09-26 | qual-XAUUSD-BRK-5y-m4-raw/qual-XAUUSD-BRK-5y-m4-raw.htm.gz | 2021-09-26 → 2026-09-26 | 446 | 7.43 | 0.342 | +80.22 | 1.22 | 12.22 → 15.26 | 11.52 → 14.43 | `RESULTS.md`:31 (equity) | `AUDITED RESULTS.md`:19; `FINAL REPORT.md`:12 |
| ATR Touch Raw 2026-09-25 | at-m1-XAUUSD-H1R2-5y/at-m1-XAUUSD-H1R2-5y.htm.gz | 2021-09-25 → 2026-09-25 | 220 | 3.67 | 0.169 | +31.56 | 1.19 | 12.51 → 14.66 | 11.14 → 11.14 | `RESULTS.md`:73 (equity) | no |
| BTC Time Series Momentum Raw 2026-10-21 | nw-BTCUSD-LF-5y/nw-BTCUSD-LF-5y.htm.gz | 2021-10-20 → 2026-10-20 | 148 | 2.47 | 0.113 | +60.67 | 1.53 | 22.07 → 26.08 | 16.74 → 23.39 | `RESULTS.md`:13 (equity) | `REPORT.md`:14 |
| Crypto Stock Edge Screen 2026-09-25 | edge-m1-BTCUSD-C1-5y/edge-m1-BTCUSD-C1-5y.htm.gz | 2021-09-01 → 2026-09-01 | 104 | 1.73 | 0.080 | +15.27 | 1.50 | 8.44 → 9.00 | 6.46 → 7.29 | `RESULTS.md`:11 (equity) | no |
| DMC Video Levels Research 2026-09-25 | dmcv-CUR-XAUUSD-UNTESTED-5y/dmcv-CUR-XAUUSD-UNTESTED-5y.htm.gz | 2021-09-01 → 2026-09-01 | 97 | 1.62 | 0.074 | +11.60 | 1.18 | 13.36 → 15.53 | 14.72 → 14.72 | `REPORT.md`:39 (equity); `RESULTS.md`:101 (equity); `RESULTS.md`:17 (equity) | no |
| FTMO Fourteen EA Study 2026-09-27 | news-pulse-xau/report.htm | 2025-09-27 → 2026-09-27 | 39 | 3.25 | 0.150 | +338.02 | 11.47 | 4.45 → 6.63 | 5.26 → 5.26 | `REPORT.md`:192 (equity) | no |
| Nasdaq 5M Index Transfer 2026-09-25 | n5idx-USTEC-DI-3y/n5idx-USTEC-DI-3y.htm.gz | 2023-09-25 → 2026-09-25 | 576 | 16.00 | 0.735 | +133.59 | 1.29 | 10.88 → 20.22 | 10.06 → 19.66 | `RESULTS.md`:31 (equity) | no |
| Nasdaq 5M Index Transfer 2026-09-25 | n5idx-USTEC-DI-5y/n5idx-USTEC-DI-5y.htm.gz | 2021-09-25 → 2026-09-25 | 968 | 16.14 | 0.742 | +180.24 | 1.22 | 10.88 → 20.56 | 10.06 → 19.65 | `REPORT.md`:12 (equity); `RESULTS.md`:42 (equity) | no |
| Nasdaq 5M Index Transfer 2026-09-25 | n5idx-USTEC-NODI-3y/n5idx-USTEC-NODI-3y.htm.gz | 2023-09-25 → 2026-09-25 | 764 | 21.22 | 0.974 | +128.95 | 1.20 | 12.87 → 20.23 | 11.86 → 19.25 | `RESULTS.md`:32 (equity) | no |
| Nasdaq 5M Index Transfer 2026-09-25 | n5idx-USTEC-NODI-5y/n5idx-USTEC-NODI-5y.htm.gz | 2021-09-25 → 2026-09-25 | 1272 | 21.20 | 0.975 | +133.84 | 1.14 | 12.88 → 24.65 | 11.87 → 22.35 | `REPORT.md`:13 (equity); `RESULTS.md`:43 (equity) | no |
| Nasdaq 5M QuantLab Style Research 2026-09-25 | n5ql-USTEC-CURRENT-3y/n5ql-USTEC-CURRENT-3y.htm.gz | 2023-09-25 → 2026-09-25 | 576 | 16.00 | 0.735 | +133.59 | 1.29 | 10.88 → 20.22 | 10.06 → 19.66 | `REPORT.md`:30 (balance); `REPORT.md`:30 (equity); `REPORT.md`:31 (equity); `RESULTS.md`:29 (equity) | no |
| Nasdaq 5M QuantLab Style Research 2026-09-25 | n5ql-USTEC-CURRENT-5y/n5ql-USTEC-CURRENT-5y.htm.gz | 2021-09-25 → 2026-09-25 | 968 | 16.14 | 0.742 | +180.24 | 1.22 | 10.88 → 20.56 | 10.06 → 19.65 | `REPORT.md`:31 (equity); `RESULTS.md`:38 (equity) | no |
| Nasdaq 5M QuantLab Style Research 2026-09-25 | n5ql-USTEC-QL_ATR-3y/n5ql-USTEC-QL_ATR-3y.htm.gz | 2023-09-25 → 2026-09-25 | 536 | 14.89 | 0.684 | +162.16 | 1.40 | 10.06 → 21.44 | 8.94 → 20.25 | `REPORT.md`:29 (equity); `REPORT.md`:30 (equity); `RESULTS.md`:31 (equity) | no |
| Previous Green 1H Raw 2026-09-25 | pg1h-XAUUSD-B1-1y/pg1h-XAUUSD-B1-1y.htm.gz | 2025-09-01 → 2026-09-01 | 1390 | 115.91 | 5.326 | -5.70 | 0.99 | 28.19 → 30.38 | 27.60 → 29.73 | `RESULTS.md`:11 (equity) | no |
| Previous Green 1H Raw 2026-09-25 | pg1h-XAUUSD-B3-3y/pg1h-XAUUSD-B3-3y.htm.gz | 2023-09-01 → 2026-09-01 | 1109 | 30.80 | 1.418 | +72.26 | 1.06 | 35.84 → 37.88 | 33.59 → 36.44 | `RESULTS.md`:12 (equity) | no |
| Previous Green 1H Raw 2026-09-25 | pg1h-XAUUSD-B3-5y/pg1h-XAUUSD-B3-5y.htm.gz | 2021-09-01 → 2026-09-01 | 1617 | 26.95 | 1.240 | +32.64 | 1.02 | 34.65 → 43.86 | 32.50 → 41.73 | `RESULTS.md`:13 (equity) | no |
| Previous Green 1H Raw 2026-09-25 | pg1h-XAUUSD-L3-3y/pg1h-XAUUSD-L3-3y.htm.gz | 2023-09-01 → 2026-09-01 | 1234 | 34.27 | 1.578 | +361.39 | 1.18 | 24.79 → 31.46 | 24.52 → 31.24 | `RESULTS.md`:12 (equity) | no |
| Slow Multi Asset Trend Research 2026-09-06 | Native/eurusd-selected-full-model1/eurusd-selected-full-model1.htm | 2023-09-01 → 2026-09-01 | 70 | 1.94 | 0.090 | +13.59 | 1.22 | 17.12 → 18.60 | 12.68 → 13.36 | `REPORT.md`:68 (equity) | no |
| Slow Multi Asset Trend Research 2026-09-06 | Native/xauusd-selected-full-model1/xauusd-selected-full-model1.htm | 2023-09-01 → 2026-09-01 | 137 | 3.80 | 0.175 | +135.62 | 1.95 | 9.20 → 11.24 | 7.83 → 9.07 | `REPORT.md`:62 (equity) | no |

## 6. CLAUDE.md

| Study | Run | Window | Trades | Trades/mo | Trades/weekday | Return % | Eq DD max → rel % | CLAUDE.md line | Value quoted | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| QuantLab Gold Trio Raw 2026-09-30 | video-A+B+C-3y-m4 | 2023-07-01 → 2026-09-29 | 733 | 18.81 | 0.866 | +94.96 | 23.42 → 27.37 | 163 | "equity DD 27.4%" | relative, OK |
| QuantLab Gold Trio Pipeline 2026-09-30 | combo-prop-3-ABC-5y | 2021-04-02 → 2026-09-29 | 708 | 10.74 | 0.494 | +96.13 | 10.15 → 11.52 | 172 | "PROP trio … DD 11.5%" | relative, OK |
| No Wick Multi Asset Raw 2026-09-30 | nw-USTEC-S5-6m | 2026-03-30 → 2026-09-30 | 451 | 74.60 | 3.417 | +26.44 | 12.64 → 13.46 | 204 | "equity DD 13.46%" | relative, OK |
| USDJPY NY Open Exit 2026-10-21 | ny0930 half | 2021-10-06 → 2026-10-06 | 462 | 7.70 | 0.354 | +68.75 | 10.55 → 11.07 | 363 | "eqDD 11.1%" | relative, OK |
| BTC Time Series Momentum Raw 2026-10-21 | nw-BTCUSD-LF-5y | 2021-10-20 → 2026-10-20 | 148 | 2.47 | 0.113 | +60.67 | 22.07 → 26.08 | 379 | "eqDD 26.1% (relative; first reported 22.1% = MT5 'maximal')" | relative, maximal labelled |
| Turtle Breakout Raw 2026-10-22 | nw-BTCUSD-HOLD-5y | 2021-10-22 → 2026-10-22 | 177 | 2.95 | 0.136 | +111.59 | 35.08 → 46.90 | 392–393 | "equity DD 46.9% (relative; MT5 'maximal' 35.1%)" | relative, maximal labelled |

Two other points:
- The automatic search also matched line 276 to News Pulse XAG 3y. That was a false positive: the "11.5%" there is the BTC Weekend VA take-profit share.
- On line 379, the BTC TSM LF 5y return "+60.9%" (same in the study `REPORT.md`) differs from the native report's net profit, which gives +60.67%. That return figure was not investigated here.

## 7. Parser change proposal (not applied)

### 7.1 What changes

The branch is `audit/drawdown-parser-proposal` in the main repository, commit `b41e0de17`. Its worktree is in a scratch folder; the branch has not been merged or pushed.

- **`AAA EAs/EA store/app/mt5_evidence_jobs.py` — `_native_metrics`:**
  - `max_drawdown_pct` = **Equity Drawdown Relative**. If that row is missing, it falls back to Maximal, and `drawdown_basis` says which was used.
  - New fields:
    - `equity_dd_rel_pct`
    - `balance_dd_rel_pct`
    - `equity_dd_maximal_pct` (the old figure, kept for parity with older study files)
    - `balance_dd_maximal_pct`
    - `drawdown_basis` (`equity_relative` / `equity_maximal`)
  - Missing rows return `None`, not 0. The headline key keeps its old 0.0 fallback so the website's `float()` callers do not break.
- **`AAA EAs/EA store/tools/precompute_evidence_cache.py` — `portfolio_metrics`:** adds `drawdown_basis: "closed_balance_relative"` so trimmed-window payloads say what they show.
- **`AAA EAs/EA store/tests/test_native_drawdown.py`:** two unit tests on a synthetic UTF-16 report built from the Turtle HOLD 5y figures. They cover relative vs maximal, and the fallback when the relative rows are missing.

### 7.2 Which figure the website shows

**Decision: the website's "Max DD" shows the equity relative drawdown.** Reasons:

1. It is the worst percentage fall from an equity peak, floating losses included. That is what "Max DD %" means on a card, and it is the number the Turtle and BTC TSM corrections already moved to.
2. It makes the site consistent: News Pulse payloads already show equity relative, and trimmed windows already use a worst-percentage (closed-balance) figure.
3. CLAUDE.md asks for floating-equity drawdown to be reported separately from closed-balance drawdown.
   - Equity relative is the headline.
   - `balance_dd_rel_pct` is available for a separate "closed-balance DD" line, which the portfolio page already labels "Max closed DD".
   - Balance relative can be the larger figure (section 2), so it should be shown next to equity, not dropped.

The key name `max_drawdown_pct` is kept. The 91 lines in 15 `app/`, template and `static/` files that read it therefore need no change.

The alternative was to keep `max_drawdown_pct` as maximal and switch every reader to `equity_dd_rel_pct`. It was not chosen:
- it touches every reader;
- it leaves the 132 study scripts that import `_native_metrics` still reporting maximal.

### 7.3 Effect if approved

- **Fresh MT5 evidence jobs** show relative at once.
- **Existing caches keep their current values** until an approved cache rebuild. That rebuild is what changes the W1 numbers on the site.
- **Study scripts.** 132 scripts in the package import `_native_metrics`.
  - If re-run, they report relative.
  - Any parity check against a stored `max_drawdown_pct` will differ on compounding runs. This is expected: the stored value was maximal.
- **Not covered by this change** (follow-ups, section 8):
  - the Calyx pipeline's `reported_max_drawdown_pct`;
  - the No Wick harness's `balance_dd_pct`;
  - 55 other scripts with their own maximal-only parsers (Appendix B).

### 7.4 Tests

The suite was run in an isolated sparse worktree (EA store from HEAD `cae69abf0`).
- For the run, the study, BookMaper and clients folders were linked in read-only as directory junctions.
- The junctions were removed straight after the tests, before any other git command in that worktree.
- The tests use a temporary store database and secrets (`tests/conftest.py`).

| Run | Failed | Passed | Skipped | Notes |
|---|---:|---:|---:|---|
| Worktree, before the change | 60 | 457 | 2 | |
| Worktree, with the change | 60 | 459 | 2 | Same 60 failures; the 2 new tests pass |
| Main checkout, reference (no env sync, no bytecode or cache writes) | 34 | 484 | 1 | All 34 are among the worktree's 60 |

The 26 failures seen only in the worktree are environmental:
- `resolve()` follows the junctions, so path-identity asserts fail (4 in `test_admission_release`);
- `bs4` is missing from the fresh venv (it is not in `pyproject.toml`);
- Windows PowerShell 5.1 cannot open the scratch folder's paths over 260 characters (installer/launcher tests);
- 13 `test_orb_comments` hash and preset checks fail in the sparse checkout;
- `test_store_licenses` and 2 more `test_store.py` checks also fail only there.

**Pre-existing `test_store.py` failures in the main checkout: 10, not 7.** None involves drawdown parsing:

| Test | Failure |
|---|---|
| test_sellable_logic_is_specific_and_audit_labeled | `assert False` (line 227) |
| test_recommended_exit_settings_are_synced_per_ea | `0 == 1` (273) |
| test_news_pulse_cards_details_and_series_use_the_same_verified_evidence | `200 == 404` (569) |
| test_period_matched_news_trade_chart_is_available | news chart route |
| test_portfolio_page_shows_fixed_cached_periods | expects the text "33 EAs …" (702) |
| test_every_public_ea_uses_supported_evidence_period | roster list differs (741) |
| test_home_ranks_all_available_eas_by_default_three_year_return | `5 == 1` (762) |
| test_ea_catalogue_supports_metric_sorting_and_symbol_filtering | expects "XAUUSD (18)" (784) |
| test_fixed_cached_evidence_periods_and_pricing_bundle | gold-overnight 6m payload lacks `sharpe_ratio` and `recovery_factor` (836); `max_drawdown_pct` is present |
| test_all_recommended_eas_and_portfolio_have_every_fixed_cache | `57 == 61` cached files (937) |

The other 24 main-checkout failures are in News Pulse multi-event, launcher/BAT routing, portfolio-publication and installer tests. They are unrelated to drawdown, and identical with and without the change.

**Parity.** The proposed `_native_metrics` was run on all 5,176 non-empty reports and compared with the independent scan:
- compared fields: `max_drawdown_pct`, both relative values, both maximal values, trades and basis;
- result: 0 mismatches.

## 8. Other parsers that read "Maximal"

| Where | What it does | Effect |
|---|---|---|
| `EA store/app/mt5_evidence_jobs.py:69` `_native_metrics` | equity maximal → `max_drawdown_pct` | Website caches and fresh jobs. Also used by 132 study scripts and 7 EA store tests/tools. Fixed by the proposal. |
| `No Wick Candle Raw 2026-09-25/run_nw.py:117` `summarize()` | balance maximal → `balance_dd_pct` | Study harness. Proposed one-line change, not applied (study artifacts are frozen): `_metric(t, "Balance Drawdown Relative")` with the leading-percent parser. Re-run only on approval. |
| `Calyx Research Pipeline/calyx_pipeline.py:118` | equity maximal → `reported_max_drawdown_pct` | Feeds the News Pulse base evidence in `catalog.py:2159`. On the site, the cached relative payload replaces it. Change it to Relative together with the proposal. |
| 54 other study scripts in the package, plus 1 in `high frecency ea`, that read only "Drawdown Maximal" | their own report tables | Historical. Fix when the study is next re-run; list in Appendix B. |
| 31 study scripts that read both fields | — | No action. |

## 9. Limitations

- **Value matching is heuristic.**
  - A document can quote a drawdown in prose without the trade count, return or PF nearby; 32 runs have such weak matches only.
  - Coincidental matches are possible; two were found and removed.
- **Only `.md` files were searched.** Study `.html` reports, `RESULTS.json` and website templates were not.
- **MT5 "Total Trades" is not always the study's trade count.** It counts closed deals, so partial exits count separately.
- **The public VPS site was not checked.** No cache was rebuilt, so the W1 numbers on the local site are unchanged.
- **Only `native*` folders were scanned.** The package holds about 22,350 `.htm` / `.htm.gz` files in total; reports stored elsewhere were outside this audit's scope.

## 10. Decisions for the owner

1. Approve the parser change and merge `audit/drawdown-parser-proposal` into `new-telegram-copy`. The same change should also cover `calyx_pipeline.py:118`.
2. Approve a cache rebuild, so the website shows the relative drawdown for the W1 and W2 payloads.
3. Decide how to treat the D1 study documents. Suggestion: an erratum line in each, rather than rewriting frozen reports.
4. Update the stale "7 pre-existing `test_store.py` failures" note in CLAUDE.md to 10.

## Appendix A. Flagged runs per study

| Study | Flagged runs | Worst run | Trades | Trades/mo | Trades/weekday | Return % | Eq DD max → rel % | Eq gap pp | Max bal gap pp | Docs quote maximal | Harness stored maximal |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 Way Gold Deployment 2026-09-30 | 1 | parity-5y-market/report.htm.gz | 774 | 11.74 | 0.541 | +108.71 | 10.43 → 11.46 | 1.03 | 0.57 | 0 | 0 |
| 3 Way Volume Profile Pipeline 2026-09-26 | 9 | qual-USDJPY-ALL-5y-m4-raw/qual-USDJPY-ALL-5y-m4-raw.htm.gz | 913 | 15.22 | 0.700 | +99.12 | 16.47 → 27.73 | 11.26 | 10.93 | 8 | 8 |
| ADX DI Deployment 2026-10-03 | 3 | Long Window Comparison/asia-5y-filtered-ORIGINAL/report.htm.gz | 182 | 3.03 | 0.140 | +50.46 | 8.39 → 10.25 | 1.86 | 1.99 | 0 | 0 |
| ADX DI Next Five Review 2026-10-03 | 1 | weakness-3y-ORIGINAL/report.htm.gz | 388 | 10.78 | 0.495 | +225.10 | 14.02 → 20.12 | 6.10 | 7.13 | 0 | 0 |
| ATR Touch Raw 2026-09-25 | 1 | at-m1-XAUUSD-H1R2-5y/at-m1-XAUUSD-H1R2-5y.htm.gz | 220 | 3.67 | 0.169 | +31.56 | 12.51 → 14.66 | 2.15 | 0.00 | 1 | 1 |
| Asia Breakout Optimization 2026-10-05 | 2 | raw-5y/report.htm | 189 | 3.15 | 0.145 | +46.09 | 8.31 → 9.24 | 0.93 | 1.77 | 0 | 0 |
| BTC Time Series Momentum Raw 2026-10-21 | 12 | nw-BTCUSD-FIX-5y_m1/nw-BTCUSD-FIX-5y_m1.htm.gz | 82 | 1.37 | 0.063 | +44.40 | 35.94 → 52.83 | 16.89 | 9.35 | 1 | 12 |
| Bollinger Momentum US100 Raw 2026-10-07 | 2 | momentum-middle-r4/report.htm.gz | 836 | 17.42 | 0.802 | +16.24 | 16.59 → 18.03 | 1.44 | 0.99 | 0 | 0 |
| Conte Research Basket Raw 2026-09-28 | 2 | USTEC-day-raw-1y-m4/report.htm.gz | 248 | 17.76 | 0.816 | +6.94 | 29.70 → 33.81 | 4.11 | 3.89 | 0 | 2 |
| Crypto Stock Edge Screen 2026-09-25 | 1 | edge-m1-BTCUSD-C1-5y/edge-m1-BTCUSD-C1-5y.htm.gz | 104 | 1.73 | 0.080 | +15.27 | 8.44 → 9.00 | 0.56 | 0.83 | 1 | 1 |
| DAX Momentum Full Pipeline 2020-2023 2026-10-07 | 1 | oos-baseline/report.htm.gz | 472 | 14.21 | 0.653 | +31.49 | 12.70 → 13.39 | 0.69 | 0.80 | 0 | 0 |
| DMC Video Levels Research 2026-09-25 | 1 | dmcv-CUR-XAUUSD-UNTESTED-5y/dmcv-CUR-XAUUSD-UNTESTED-5y.htm.gz | 97 | 1.62 | 0.074 | +11.60 | 13.36 → 15.53 | 2.17 | 0.00 | 1 | 1 |
| EURUSD Grid Aggressive Research 2026-10-10 | 3 | allrr05-gridhr-raw-20x-3y-raw/report.htm | 707 | 19.63 | 0.902 | +276.49 | 49.06 → 79.41 | 30.35 | 0.00 | 0 | 0 |
| FTMO Core3 vs Core4 DI OFF Phase Timing 2026-10-16 | 2 | allrr05-nasdaq-5m-candle-momentum-core-dioff-long-20261016/report.htm | 1193 | 19.89 | 0.915 | +142.61 | 14.98 → 28.23 | 13.25 | 13.68 | 0 | 0 |
| FTMO Exit Management Research 2026-09-27 | 2 | xau-native/report.htm.gz | 20 | 3.34 | 0.154 | +120.43 | 3.67 → 6.65 | 2.98 | 3.47 | 0 | 1 |
| FTMO Fourteen EA Study 2026-09-27 | 2 | news-pulse-xau/report.htm | 39 | 3.25 | 0.150 | +338.02 | 4.45 → 6.63 | 2.18 | 0.53 | 1 | 1 |
| Gann Three Ideas Raw 2026-10-09 | 8 | Pipeline 2026-10-09/allrr05-gp-fresh-original-gold-parity-raw/report.htm | 639 | 17.75 | 0.815 | +41.14 | 17.87 → 18.57 | 0.70 | 0.88 | 0 | 0 |
| Gold Intraday Bias Pipeline 2026-09-29 | 2 | raw-3y-m1/report-attempt0.htm.gz | 599 | 16.53 | 0.760 | +19.27 | 16.21 → 19.32 | 3.11 | 2.06 | 0 | 1 |
| Gold Target Sensitivity 2026-10-02 | 1 | S-v3-5y-chunk3/reel-S-v3-5y-chunk3-d4f0752846.htm.gz | 242 | 3.36 | 0.155 | +59.91 | 23.38 → 31.66 | 8.28 | 9.36 | 0 | 0 |
| Indices Hourly EA Pipeline 2026-10-03 | 5 | hourprof-20261003-US100-1y-hold75/report.htm.gz | 922 | 76.89 | 3.533 | +55.18 | 5.66 → 7.53 | 1.87 | 2.32 | 0 | 0 |
| LTA Original Optimization 2026-10-05 | 2 | PARITY-acd50e7a5cd7ae/report.htm | 219 | 18.26 | 0.842 | +50.93 | 15.55 → 16.62 | 1.07 | 0.00 | 0 | 0 |
| LTA Original Optimization R2 2026-10-05 | 2 | PARITY-acd50e7a5cd7ae/report.htm | 219 | 18.26 | 0.842 | +50.93 | 15.55 → 16.62 | 1.07 | 0.00 | 0 | 0 |
| LTA Original Optimization R3 2026-10-05 | 2 | PARITY-acd50e7a5cd7ae/report.htm | 219 | 18.26 | 0.842 | +50.93 | 15.55 → 16.62 | 1.07 | 0.00 | 0 | 0 |
| LTA Original Optimization R4 2026-10-05 | 26 | T5Y-d5c7800c2b6dde/report.htm | 617 | 10.28 | 0.473 | +107.72 | 15.39 → 23.26 | 7.87 | 8.17 | 0 | 0 |
| LTA VWAP Developing POC Comparison 2026-10-05 | 2 | SAFE_M15/report.htm | 219 | 18.26 | 0.842 | +50.93 | 15.55 → 16.62 | 1.07 | 0.00 | 0 | 0 |
| Liquidity Continuation Raw 2026-09-27 | 1 | XAU-retest-control-6m/report.htm.gz | 177 | 11.13 | 0.513 | +29.19 | 8.23 → 9.42 | 1.19 | 0.00 | 0 | 1 |
| Matteo Golden Trio Raw 2026-10-06 | 2 | Pipeline 2026-10-07/control-vault-1-DEV/report.htm.gz | 447 | 18.64 | 0.856 | +1.42 | 9.36 → 9.43 | 0.07 | 0.58 | 0 | 0 |
| Nasdaq 5M DI Filter Research 2026-09-23 | 4 | n5-current-5y-m4-d150/n5-current-5y-m4-d150.htm.gz | 1272 | 21.20 | 0.975 | +125.62 | 12.89 → 24.61 | 11.72 | 10.42 | 0 | 0 |
| Nasdaq 5M Germany Transfer 2026-10-07 | 2 | USTEC-3y/report.htm.gz | 532 | 14.77 | 0.680 | +171.71 | 10.07 → 21.46 | 11.39 | 11.32 | 0 | 0 |
| Nasdaq 5M Index Transfer 2026-09-25 | 4 | n5idx-USTEC-NODI-5y/n5idx-USTEC-NODI-5y.htm.gz | 1272 | 21.20 | 0.975 | +133.84 | 12.88 → 24.65 | 11.77 | 10.48 | 4 | 4 |
| Nasdaq 5M Next Day Efficiency ML 2026-10-05 | 2 | 2Y_ML/report.htm | 239 | 9.97 | 0.460 | +101.67 | 10.46 → 12.72 | 2.26 | 2.89 | 0 | 0 |
| Nasdaq 5M QuantLab Style Research 2026-09-25 | 3 | n5ql-USTEC-QL_ATR-3y/n5ql-USTEC-QL_ATR-3y.htm.gz | 536 | 14.89 | 0.684 | +162.16 | 10.06 → 21.44 | 11.38 | 11.31 | 3 | 3 |
| Nasdaq Video Match 2026-10-03 | 3 | EMA_ONLY-5y/report.htm.gz | 1194 | 19.90 | 0.916 | +148.99 | 14.99 → 28.24 | 13.25 | 13.66 | 0 | 0 |
| Negative RR Study 2026-10-21 | 10 | base-dioff/allrr05-nasdaq-5m-candle-momentum-half/report.htm | 1193 | 19.89 | 0.915 | +145.44 | 14.96 → 28.19 | 13.23 | 13.65 | 0 | 0 |
| News Pulse Event Parameters Research 2026-09-19 | 9 | NativeFullBestDelay250/news-event-NativeFullBestDelay250.htm | 39 | 3.25 | 0.149 | +331.07 | 4.46 → 6.79 | 2.33 | 0.00 | 0 | 0 |
| News Pulse Multi Asset Event Parameters 2026-09-19 | 22 | EURUSDProduction1y/multi-news-EURUSDProduction1y.htm | 46 | 3.84 | 0.176 | +919.45 | 4.26 → 21.12 | 16.86 | 14.02 | 0 | 0 |
| News Pulse XAG Current Audit 2026-10-05 | 8 | 1Y-150/report.htm | 39 | 3.25 | 0.150 | +2622.82 | 4.62 → 11.28 | 6.66 | 6.64 | 0 | 0 |
| News Standalone Risk 2026-09-28 | 1 | EURUSD-new-1.25/report.htm.gz | 5 | 4.91 | 0.217 | +137.42 | 4.04 → 4.55 | 0.51 | 0.00 | 0 | 0 |
| News XAU Placement Fix 2026-10-03 | 2 | Current-test-1000-2025.10.03/report.htm.gz | 38 | 3.17 | 0.146 | +292.30 | 3.92 → 6.74 | 2.82 | 0.00 | 0 | 0 |
| No Wick Multi Asset Raw 2026-09-30 | 1 | nw-USTEC-S5-6m/nw-USTEC-S5-6m.htm.gz | 451 | 74.60 | 3.417 | +26.44 | 12.64 → 13.46 | 0.82 | 0.18 | 0 | 1 |
| Overnight VA First Candle Trail Research 2026-09-23 | 4 | onvt-XAUUSD-anytime-trail1r-1y-m4-d150/onvt-XAUUSD-anytime-trail1r-1y-m4-d150.htm.gz | 244 | 20.35 | 0.935 | +57.89 | 18.48 → 21.69 | 3.21 | 3.33 | 0 | 0 |
| PBD Gold Validation 2026-10-02 | 1 | real-2026/goldval-real-2026-08c05cc5.htm.gz | 53 | 5.89 | 0.270 | +17.64 | 5.47 → 6.05 | 0.58 | 0.00 | 0 | 0 |
| Portfolio Long History 2026-10-08 | 24 | allrr05-news-pulse-eurusd-long-c1a8fbdd1ff3/report.htm | 256 | 4.27 | 0.196 | +43115.69 | 2.93 → 20.56 | 17.63 | 18.71 | 0 | 0 |
| Portfolio Long History All ORB05 2026-10-14 | 4 | allrr05-3-way-gold-long-b8a53e250c8f/report.htm | 773 | 12.89 | 0.593 | +105.77 | 10.41 → 11.44 | 1.03 | 0.52 | 0 | 0 |
| Previous Green 1H Raw 2026-09-25 | 4 | pg1h-XAUUSD-B3-5y/pg1h-XAUUSD-B3-5y.htm.gz | 1617 | 26.95 | 1.240 | +32.64 | 34.65 → 43.86 | 9.21 | 9.23 | 4 | 4 |
| QuantLab Gold Trio Pipeline 2026-09-30 | 4 | parity-B/gts-parity-B-6cbc9a4d90.htm.gz | 266 | 6.83 | 0.314 | +52.11 | 10.86 → 12.39 | 1.53 | 2.01 | 0 (1 false positive removed) | 0 |
| QuantLab Gold Trio Raw 2026-09-30 | 4 | website-A+D+B-3y-m4/report-attempt0.htm.gz | 3728 | 95.68 | 4.407 | +119.28 | 27.20 → 43.82 | 16.62 | 2.01 | 0 | 4 |
| RSI MACD Raw 2026-09-28 | 2 | BTC-C_MACD_only-1y/report.htm.gz | 730 | 45.81 | 2.110 | +39.86 | 13.89 → 18.28 | 4.39 | 4.88 | 0 | 2 |
| Reel Three Bots Pipeline 2026-10-02 | 3 | combo-raw-baseline-5y/reel-combo-raw-baseline-5y-8afac15ed6.htm.gz | 1679 | 25.46 | 1.171 | +118.75 | 28.29 → 30.99 | 2.70 | 9.60 | 0 | 0 |
| Slow Multi Asset Trend Research 2026-09-06 | 2 | Native/xauusd-selected-full-model1/xauusd-selected-full-model1.htm | 137 | 3.80 | 0.175 | +135.62 | 9.20 → 11.24 | 2.04 | 1.24 | 2 | 0 |
| Trend Progression Optimization 2026-10-05 | 6 | T5Y-e2ebbfe05247c4/report.htm | 139 | 2.32 | 0.107 | +79.39 | 7.43 → 9.22 | 1.79 | 0.00 | 0 | 0 |
| Turtle Breakout Raw 2026-10-22 | 6 | nw-BTCUSD-HOLD-5y/nw-BTCUSD-HOLD-5y.htm.gz | 177 | 2.95 | 0.136 | +111.59 | 35.08 → 46.90 | 11.82 | 13.16 | 0 | 5 |
| US100 H1 ORB ADX RR1 Research 2026-09-23 | 2 | us100orb-H1-RR6-none-1y-m4-d150/us100orb-H1-RR6-none-1y-m4-d150.htm.gz | 72 | 6.00 | 0.276 | +23.00 | 6.84 → 6.84 | 0.00 | 0.53 | 0 | 0 |
| US100 H1 ORB Optimization 2026-10-06 | 4 | raw-1y/report.htm | 77 | 6.42 | 0.295 | +20.05 | 6.84 → 6.84 | 0.00 | 0.53 | 0 | 0 |
| US100 H1 ORB RR05 Comparison 2026-10-08 | 2 | Agent3010/rrcomp20261008-current-1y/report.htm | 77 | 6.42 | 0.295 | +20.05 | 6.84 → 6.84 | 0.00 | 0.53 | 0 | 0 |
| US100 Hourly Raw 2026-10-03 | 1 | 5y/report.htm.gz | 1287 | 21.45 | 0.987 | +11.87 | 14.24 → 15.28 | 1.04 | 1.14 | 0 | 0 |
| US100 News Reversion Pipeline 2020-2024 2026-10-08 | 1 | raw-3y/report.htm.gz | 73 | 2.03 | 0.093 | -8.43 | 16.27 → 16.79 | 0.52 | 0.05 | 0 | 0 |
| USDJPY NY Open Exit 2026-10-21 | 2 | ny0930/allrr05-usdjpy-london-open-momentum-half/report.htm | 462 | 7.70 | 0.354 | +68.75 | 10.55 → 11.07 | 0.52 | 0.00 | 0 | 0 |
| XAU Slow Trend Filter Review 2026-09-29 | 3 | adx25-di-val-m1/report.htm.gz | 39 | 3.25 | 0.149 | +33.70 | 8.50 → 9.33 | 0.83 | 0.82 | 0 | 0 |
| XAU Slow Trend Weekly Review 2026-09-29 | 2 | calendar-val-m1/report.htm.gz | 33 | 2.75 | 0.126 | +45.53 | 9.11 → 9.68 | 0.57 | 0.64 | 0 | 0 |
| evidence-cache/v1 | 36 | source-runs/news-pulse-eurusd/standard/1y.htm | 46 | 3.84 | 0.176 | +919.45 | 4.26 → 21.12 | 16.86 | 14.02 | 0 | 0 |
| evidence-jobs/btc-poc-fibonacci | 1 | latest.htm | 145 | 1.21 | 0.056 | +58.43 | 14.17 → 14.17 | 0.00 | 2.82 | 0 | 0 |
| evidence-jobs/us100-orb-new-york-m30 | 1 | latest.htm | 43 | 1.20 | 0.055 | +51.60 | 5.51 → 6.30 | 0.79 | 1.16 | 0 | 0 |
| evidence-jobs/xau-trend-progression | 1 | latest.htm | 53 | 1.75 | 0.080 | +122.87 | 11.12 → 11.12 | 0.00 | 4.05 | 0 | 0 |
| evidence-jobs/xau-weakness | 1 | latest.htm | 150 | 4.95 | 0.228 | +120.65 | 15.23 → 17.31 | 2.08 | 1.53 | 0 | 0 |

## Appendix B. Study scripts that parse only "Drawdown Maximal"

58 Python files reference "Drawdown Maximal" and never "Drawdown Relative" (55 in the package, plus `EA store/app/mt5_evidence_jobs.py`, `Calyx Research Pipeline/calyx_pipeline.py` and one in `high frecency ea`). Paths are relative to `AAA EAs/`.

- `BM Trading Robust Sets 2026-08-04/3 Way Volume Profile Raw 2026-09-26/run_3wvp.py`
- `BM Trading Robust Sets 2026-08-04/ATR Touch Raw 2026-09-25/run_at.py`
- `BM Trading Robust Sets 2026-08-04/Asia Sweep Structure Research 2026-08-29/Build-Report.py`
- `BM Trading Robust Sets 2026-08-04/Asia Sweep Structure Research 2026-08-29/Select-Winners.py`
- `BM Trading Robust Sets 2026-08-04/Ava Futures Portfolio Research 2026-09-09/EA/ORB Volume Data/Analyze-ORB-Candidates.py`
- `BM Trading Robust Sets 2026-08-04/Ava Futures Portfolio Research 2026-09-09/EA/ORB Volume Data/Analyze-Volume-Profile.py`
- `BM Trading Robust Sets 2026-08-04/Ava Futures Portfolio Research 2026-09-09/EA/ORB Volume Data/Finalize-ORB-Research.py`
- `BM Trading Robust Sets 2026-08-04/BAT Portfolio Backtest 2026-08-09/Build-BAT-Portfolio-Report.py`
- `BM Trading Robust Sets 2026-08-04/CRT Parent Range Research 2026-08-30/Analyze-CRT.py`
- `BM Trading Robust Sets 2026-08-04/Crypto Hybrid Edge Research 2026-08-30/Build-Report.py`
- `BM Trading Robust Sets 2026-08-04/Crypto Hybrid Edge Research 2026-08-30/Select-Winners.py`
- `BM Trading Robust Sets 2026-08-04/Crypto Hybrid Edge Research 2026-08-30/Slow-Holdout-Analysis.py`
- `BM Trading Robust Sets 2026-08-04/Crypto Stock Edge Screen 2026-09-25/run_edge.py`
- `BM Trading Robust Sets 2026-08-04/DMC Video Levels Research 2026-09-25/run_dmc.py`
- `BM Trading Robust Sets 2026-08-04/Dynamic Trailing Session Research 2026-09-01/EA/orb-volume/Analyze-ORB-Candidates.py`
- `BM Trading Robust Sets 2026-08-04/Dynamic Trailing Session Research 2026-09-01/EA/orb-volume/Analyze-Volume-Profile.py`
- `BM Trading Robust Sets 2026-08-04/Dynamic Trailing Session Research 2026-09-01/EA/orb-volume/Finalize-ORB-Research.py`
- `BM Trading Robust Sets 2026-08-04/EMA VWAP Pullback Raw 2026-09-25/run_ev.py`
- `BM Trading Robust Sets 2026-08-04/Elliott Wave Research 2026-09-05/Analyze-Elliott-Wave.py`
- `BM Trading Robust Sets 2026-08-04/Engineered Liquidity Sweep Research 2026-08-30/Analyze-Engineered-Liquidity.py`
- `BM Trading Robust Sets 2026-08-04/Gold Liquidity Sweep EA/Analyze-Gold-Liquidity.py`
- `BM Trading Robust Sets 2026-08-04/ICT Macro Liquidity Sweep Research 2026-08-29/Build-Report.py`
- `BM Trading Robust Sets 2026-08-04/ICT Macro Liquidity Sweep Research 2026-08-29/Select-Winners.py`
- `BM Trading Robust Sets 2026-08-04/In Play ORB Raw 2026-09-25/run_ip.py`
- `BM Trading Robust Sets 2026-08-04/Indices Hourly EA Pipeline 2026-10-03/analyse.py`
- `BM Trading Robust Sets 2026-08-04/Indices Hourly EA Pipeline 2026-10-03/build_website.py`
- `BM Trading Robust Sets 2026-08-04/LCE Volume Profile Proxy Research 2026-08-30/Build-Report.py`
- `BM Trading Robust Sets 2026-08-04/LCE Volume Profile Proxy Research 2026-08-30/Select-Winners.py`
- `BM Trading Robust Sets 2026-08-04/LTA Book Fidelity Research 2026-09-07/Analyze-Book-Fidelity.py`
- `BM Trading Robust Sets 2026-08-04/LVN Volume Profile Research 2026-09-04/Analyze-LVN.py`
- `BM Trading Robust Sets 2026-08-04/NQ Drift VWAP Pullback EA/Analyze-NQ-Drift.py`
- `BM Trading Robust Sets 2026-08-04/Nasdaq 5M Index Transfer 2026-09-25/run_idx.py`
- `BM Trading Robust Sets 2026-08-04/Nasdaq 5M QuantLab Style Research 2026-09-25/run_n5ql.py`
- `BM Trading Robust Sets 2026-08-04/No Wick Candle Raw 2026-09-25/run_nw.py`
- `BM Trading Robust Sets 2026-08-04/ORB Trade Count Audit 2026-09-29/run_orbaudit.py`
- `BM Trading Robust Sets 2026-08-04/ORB Volume Data EA/Analyze-ORB-Candidates.py`
- `BM Trading Robust Sets 2026-08-04/ORB Volume Data EA/Analyze-Volume-Profile.py`
- `BM Trading Robust Sets 2026-08-04/ORB Volume Data EA/Finalize-ORB-Research.py`
- `BM Trading Robust Sets 2026-08-04/Order Block 30m Raw 2026-09-25/run_ob30.py`
- `BM Trading Robust Sets 2026-08-04/Overnight Cross-Market Research 2026-08-30/Analyze-Overnight-CrossMarket.py`
- `BM Trading Robust Sets 2026-08-04/POC Fibonacci Volume Profile Research 2026-09-04/Analyze-POCFib.py`
- `BM Trading Robust Sets 2026-08-04/Patrick Nill PBD Fair Value Research 2026-08-29/Build-Report.py`
- `BM Trading Robust Sets 2026-08-04/Patrick Nill PBD Fair Value Research 2026-08-29/Select-Winners.py`
- `BM Trading Robust Sets 2026-08-04/Previous Green 1H Raw 2026-09-25/run_pg1h.py`
- `BM Trading Robust Sets 2026-08-04/RSI Mean Reversion 15m Raw 2026-09-25/run_rsi15.py`
- `BM Trading Robust Sets 2026-08-04/RSI VWAP Research 2026-09-02/Analyze-RSI-VWAP.py`
- `BM Trading Robust Sets 2026-08-04/Statistical Triple Print Research 2026-08-31/Analyze-Results.py`
- `BM Trading Robust Sets 2026-08-04/Trend Progression Research 2026-09-02/Analyze-Trend-Progression.py`
- `BM Trading Robust Sets 2026-08-04/Volume Profile POC Improvements Research 2026-08-31/Analyze-LTA-Hybrid.py`
- `BM Trading Robust Sets 2026-08-04/Volume Profile POC Improvements Research 2026-08-31/Analyze-POC.py`
- `BM Trading Robust Sets 2026-08-04/_Backtests/MT5-Isolated-20260805/Analyze-Reports.py`
- `BM Trading Robust Sets 2026-08-04/_Backtests/MT5-Isolated-20260805/Analyze-Retest-20260807.py`
- `BM Trading Robust Sets 2026-08-04/_Optimization Evidence/Portfolio 100K FINAL/Reproduction scripts/analyze_portfolio.py`
- `BM Trading Robust Sets 2026-08-04/_Optimization Evidence/Portfolio 100K FINAL/Reproduction scripts/write_final_analysis.py`
- `BM Trading Robust Sets 2026-08-04/goldenrock bot prompt mql5/Rebuilt 2026-08-15/Analyze-GoldenRock.py`
- `Calyx Research Pipeline/calyx_pipeline.py`
- `EA store/app/mt5_evidence_jobs.py`
- `high frecency ea/Audit/Small Balance 50 USD 2026-09-01/Analyze-Study.py`

## Appendix C. Every flagged run (relative − maximal > 0.5 pp)

Columns:
- Harness stored = what the study's `run.json` saved as `max_drawdown_pct` (maximal, relative, or — if no run.json).
- Cited:
  - `doc:max` / `doc:rel` = a study `.md` quotes the maximal / relative value (strong match, before the manual check in section 5);
  - `CLAUDE.md` = quoted in CLAUDE.md;
  - `web` = an EA store payload, or a study folder or report the site reads;
  - `invalid-run` = a smoke or invalid run.

| Study | Run | Symbol TF | Window | Trades | Trades/mo | Trades/weekday | Return % | PF | Eq DD max % | Eq DD rel % | Eq gap pp | Bal DD max % | Bal DD rel % | Bal gap pp | Harness stored | Cited |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 Way Gold Deployment 2026-09-30 | parity-5y-market/report.htm.gz | XAUUSD M15 | 2021-04-02 → 2026-09-29 | 774 | 11.74 | 0.541 | +108.71 | 1.34 | 10.43 | 11.46 | 1.03 | 8.90 | 9.47 | 0.57 | — | doc:rel |
| 3 Way Volume Profile Pipeline 2026-09-26 | qual-USDJPY-ALL-5y-m4-raw/qual-USDJPY-ALL-5y-m4-raw.htm.gz | USDJPY M15 | 2021-09-26 → 2026-09-26 | 913 | 15.22 | 0.700 | +99.12 | 1.13 | 16.47 | 27.73 | 11.26 | 27.37 | 27.37 | 0.00 | maximal | doc:max, doc:rel |
| 3 Way Volume Profile Pipeline 2026-09-26 | qual-USDJPY-ALL-5y-m1-raw/qual-USDJPY-ALL-5y-m1-raw.htm.gz | USDJPY M15 | 2021-09-26 → 2026-09-26 | 921 | 15.35 | 0.706 | +130.54 | 1.16 | 17.73 | 27.57 | 9.84 | 16.05 | 26.98 | 10.93 | maximal | doc:max |
| 3 Way Volume Profile Pipeline 2026-09-26 | qual-USDJPY-ALL-3y-m4-raw/qual-USDJPY-ALL-3y-m4-raw.htm.gz | USDJPY M15 | 2023-09-26 → 2026-09-26 | 554 | 15.39 | 0.707 | +84.44 | 1.18 | 16.53 | 21.79 | 5.26 | 15.04 | 21.61 | 6.57 | maximal | doc:max, doc:rel |
| 3 Way Volume Profile Pipeline 2026-09-26 | qual-XAUUSD-BRK-5y-m1-raw/qual-XAUUSD-BRK-5y-m1-raw.htm.gz | XAUUSD M15 | 2021-09-26 → 2026-09-26 | 446 | 7.43 | 0.342 | +93.96 | 1.26 | 11.53 | 16.04 | 4.51 | 10.85 | 15.20 | 4.35 | maximal | doc:max |
| 3 Way Volume Profile Pipeline 2026-09-26 | qual-XAUUSD-BRK-5y-m4-raw/qual-XAUUSD-BRK-5y-m4-raw.htm.gz | XAUUSD M15 | 2021-09-26 → 2026-09-26 | 446 | 7.43 | 0.342 | +80.22 | 1.22 | 12.22 | 15.26 | 3.04 | 11.52 | 14.43 | 2.91 | maximal | doc:max, doc:rel |
| 3 Way Volume Profile Pipeline 2026-09-26 | qual-USDJPY-ALL-3y-m1-raw/qual-USDJPY-ALL-3y-m1-raw.htm.gz | USDJPY M15 | 2023-09-26 → 2026-09-26 | 562 | 15.61 | 0.717 | +111.90 | 1.22 | 17.71 | 19.49 | 1.78 | 16.03 | 19.04 | 3.01 | maximal | doc:max |
| 3 Way Volume Profile Pipeline 2026-09-26 | qual-USDJPY-BRK-3y-m4-raw/qual-USDJPY-BRK-3y-m4-raw.htm.gz | USDJPY M15 | 2023-09-26 → 2026-09-26 | 272 | 7.55 | 0.347 | +56.12 | 1.24 | 15.39 | 15.39 | 0.00 | 11.08 | 13.40 | 2.32 | relative | doc:rel |
| 3 Way Volume Profile Pipeline 2026-09-26 | qual-XAUUSD-BRK-3y-m4-raw/qual-XAUUSD-BRK-3y-m4-raw.htm.gz | XAUUSD M15 | 2023-09-26 → 2026-09-26 | 270 | 7.50 | 0.344 | +93.10 | 1.37 | 12.02 | 13.79 | 1.77 | 11.36 | 12.71 | 1.35 | maximal | doc:max, doc:rel |
| 3 Way Volume Profile Pipeline 2026-09-26 | qual-XAUUSD-BRK-3y-m1-raw/qual-XAUUSD-BRK-3y-m1-raw.htm.gz | XAUUSD M15 | 2023-09-26 → 2026-09-26 | 270 | 7.50 | 0.344 | +99.17 | 1.39 | 11.98 | 13.73 | 1.75 | 11.32 | 12.65 | 1.33 | maximal | doc:max |
| ADX DI Deployment 2026-10-03 | Long Window Comparison/asia-5y-filtered-ORIGINAL/report.htm.gz | XAUUSD H1 | 2021-10-02 → 2026-10-02 | 182 | 3.03 | 0.140 | +50.46 | 1.38 | 8.39 | 10.25 | 1.86 | 6.52 | 8.51 | 1.99 | — | web |
| ADX DI Deployment 2026-10-03 | Long Window Comparison/asia-5y-baseline-ORIGINAL/report.htm.gz | XAUUSD H1 | 2021-10-02 → 2026-10-02 | 189 | 3.15 | 0.145 | +46.33 | 1.33 | 8.29 | 9.25 | 0.96 | 6.62 | 8.41 | 1.79 | — | web |
| ADX DI Deployment 2026-10-03 | Long Window Comparison/trend-5y-baseline-ORIGINAL/report.htm.gz | XAUUSD H4 | 2021-10-02 → 2026-10-02 | 214 | 3.57 | 0.164 | +13.19 | 1.15 | 8.18 | 8.80 | 0.62 | 8.34 | 8.34 | 0.00 | — | web |
| ADX DI Next Five Review 2026-10-03 | weakness-3y-ORIGINAL/report.htm.gz | XAUUSD M30 | 2023-10-02 → 2026-10-02 | 388 | 10.78 | 0.495 | +225.10 | 1.52 | 14.02 | 20.12 | 6.10 | 12.04 | 19.17 | 7.13 | — | — |
| ATR Touch Raw 2026-09-25 | at-m1-XAUUSD-H1R2-5y/at-m1-XAUUSD-H1R2-5y.htm.gz | XAUUSD M5 | 2021-09-25 → 2026-09-25 | 220 | 3.67 | 0.169 | +31.56 | 1.19 | 12.51 | 14.66 | 2.15 | 11.14 | 11.14 | 0.00 | maximal | doc:max |
| Asia Breakout Optimization 2026-10-05 | raw-5y/report.htm | XAUUSD H1 | 2021-10-05 → 2026-10-05 | 189 | 3.15 | 0.145 | +46.09 | 1.33 | 8.31 | 9.24 | 0.93 | 6.63 | 8.40 | 1.77 | — | — |
| Asia Breakout Optimization 2026-10-05 | raw-5y/report.htm.gz | XAUUSD H1 | 2021-10-05 → 2026-10-05 | 189 | 3.15 | 0.145 | +46.09 | 1.33 | 8.31 | 9.24 | 0.93 | 6.63 | 8.40 | 1.77 | — | — |
| BTC Time Series Momentum Raw 2026-10-21 | nw-BTCUSD-FIX-5y_m1/nw-BTCUSD-FIX-5y_m1.htm.gz | BTCUSD H1 | 2021-10-20 → 2026-10-20 | 82 | 1.37 | 0.063 | +44.40 | 1.20 | 35.94 | 52.83 | 16.89 | 49.08 | 49.08 | 0.00 | maximal | — |
| BTC Time Series Momentum Raw 2026-10-21 | nw-BTCUSD-BH-5y_m1/nw-BTCUSD-BH-5y_m1.htm.gz | BTCUSD H1 | 2021-10-20 → 2026-10-20 | 1 | 0.02 | 0.001 | -25.56 | 0.00 | 74.17 | 88.44 | 14.27 | 25.56 | 25.56 | 0.00 | maximal | — |
| BTC Time Series Momentum Raw 2026-10-21 | nw-BTCUSD-S_T30-5y_m1/nw-BTCUSD-S_T30-5y_m1.htm.gz | BTCUSD H1 | 2021-10-20 → 2026-10-20 | 141 | 2.35 | 0.108 | +72.62 | 1.41 | 30.53 | 37.11 | 6.58 | 24.32 | 33.67 | 9.35 | maximal | — |
| BTC Time Series Momentum Raw 2026-10-21 | nw-BTCUSD-S_L20-5y_m1/nw-BTCUSD-S_L20-5y_m1.htm.gz | BTCUSD H1 | 2021-10-20 → 2026-10-20 | 168 | 2.80 | 0.129 | +48.74 | 1.44 | 21.59 | 30.87 | 9.28 | 26.90 | 26.90 | 0.00 | maximal | — |
| BTC Time Series Momentum Raw 2026-10-21 | nw-BTCUSD-S_WK-5y_m1/nw-BTCUSD-S_WK-5y_m1.htm.gz | BTCUSD H1 | 2021-10-20 → 2026-10-20 | 95 | 1.58 | 0.073 | +60.77 | 2.00 | 15.48 | 23.48 | 8.00 | 18.96 | 18.96 | 0.00 | maximal | — |
| BTC Time Series Momentum Raw 2026-10-21 | nw-BTCUSD-S_D1-5y_m1/nw-BTCUSD-S_D1-5y_m1.htm.gz | BTCUSD H1 | 2021-10-20 → 2026-10-20 | 252 | 4.20 | 0.193 | +45.09 | 1.40 | 21.93 | 26.28 | 4.35 | 17.00 | 24.09 | 7.09 | maximal | — |
| BTC Time Series Momentum Raw 2026-10-21 | nw-BTCUSD-VTL-5y_m1/nw-BTCUSD-VTL-5y_m1.htm.gz | BTCUSD H1 | 2021-10-20 → 2026-10-20 | 161 | 2.68 | 0.123 | +3.46 | 1.07 | 39.81 | 46.60 | 6.79 | 13.68 | 13.68 | 0.00 | maximal | — |
| BTC Time Series Momentum Raw 2026-10-21 | nw-BTCUSD-LF-5y/nw-BTCUSD-LF-5y.htm.gz | BTCUSD H1 | 2021-10-20 → 2026-10-20 | 148 | 2.47 | 0.113 | +60.67 | 1.53 | 22.07 | 26.08 | 4.01 | 16.74 | 23.39 | 6.65 | maximal | doc:max, doc:rel |
| BTC Time Series Momentum Raw 2026-10-21 | nw-BTCUSD-LF-5y_m1/nw-BTCUSD-LF-5y_m1.htm.gz | BTCUSD H1 | 2021-10-20 → 2026-10-20 | 148 | 2.47 | 0.113 | +60.66 | 1.53 | 22.10 | 26.08 | 3.98 | 16.75 | 23.39 | 6.64 | maximal | doc:rel |
| BTC Time Series Momentum Raw 2026-10-21 | nw-BTCUSD-S_CAP2-5y_m1/nw-BTCUSD-S_CAP2-5y_m1.htm.gz | BTCUSD H1 | 2021-10-20 → 2026-10-20 | 148 | 2.47 | 0.113 | +60.66 | 1.53 | 22.10 | 26.08 | 3.98 | 16.75 | 23.39 | 6.64 | maximal | doc:rel |
| BTC Time Series Momentum Raw 2026-10-21 | nw-BTCUSD-S_V60-5y_m1/nw-BTCUSD-S_V60-5y_m1.htm.gz | BTCUSD H1 | 2021-10-20 → 2026-10-20 | 127 | 2.12 | 0.097 | +53.61 | 1.54 | 19.34 | 21.58 | 2.24 | 14.98 | 19.67 | 4.69 | maximal | — |
| BTC Time Series Momentum Raw 2026-10-21 | nw-BTCUSD-S_T10-5y_m1/nw-BTCUSD-S_T10-5y_m1.htm.gz | BTCUSD H1 | 2021-10-20 → 2026-10-20 | 150 | 2.50 | 0.115 | +29.27 | 1.57 | 11.66 | 13.86 | 2.20 | 12.36 | 12.36 | 0.00 | maximal | — |
| Bollinger Momentum US100 Raw 2026-10-07 | momentum-middle-r4/report.htm.gz | USTEC H1 | 2020-01-01 → 2024-01-01 | 836 | 17.42 | 0.802 | +16.24 | 1.04 | 16.59 | 18.03 | 1.44 | 15.40 | 16.39 | 0.99 | — | — |
| Bollinger Momentum US100 Raw 2026-10-07 | momentum-middle-final/report.htm.gz | USTEC H1 | 2020-01-01 → 2024-01-01 | 835 | 17.40 | 0.801 | +14.26 | 1.04 | 17.18 | 17.83 | 0.65 | 15.72 | 15.96 | 0.24 | — | — |
| Conte Research Basket Raw 2026-09-28 | USTEC-day-raw-1y-m4/report.htm.gz | USTEC M1 | 2025-07-29 → 2026-09-27 | 248 | 17.76 | 0.816 | +6.94 | 1.03 | 29.70 | 33.81 | 4.11 | 28.26 | 32.15 | 3.89 | maximal | doc:rel |
| Conte Research Basket Raw 2026-09-28 | USTEC-orb-long-2r-5y-m1/report.htm.gz | USTEC M1 | 2021-07-29 → 2026-09-27 | 803 | 12.96 | 0.596 | +31.08 | 1.12 | 7.93 | 9.70 | 1.77 | 7.20 | 8.87 | 1.67 | maximal | doc:rel |
| Crypto Stock Edge Screen 2026-09-25 | edge-m1-BTCUSD-C1-5y/edge-m1-BTCUSD-C1-5y.htm.gz | BTCUSD H1 | 2021-09-01 → 2026-09-01 | 104 | 1.73 | 0.080 | +15.27 | 1.50 | 8.44 | 9.00 | 0.56 | 6.46 | 7.29 | 0.83 | maximal | doc:max |
| DAX Momentum Full Pipeline 2020-2023 2026-10-07 | oos-baseline/report.htm.gz | DE30 M1 | 2024-01-01 → 2026-10-08 | 472 | 14.21 | 0.653 | +31.49 | 1.11 | 12.70 | 13.39 | 0.69 | 12.08 | 12.88 | 0.80 | — | — |
| DMC Video Levels Research 2026-09-25 | dmcv-CUR-XAUUSD-UNTESTED-5y/dmcv-CUR-XAUUSD-UNTESTED-5y.htm.gz | XAUUSD H1 | 2021-09-01 → 2026-09-01 | 97 | 1.62 | 0.074 | +11.60 | 1.18 | 13.36 | 15.53 | 2.17 | 14.72 | 14.72 | 0.00 | maximal | doc:max |
| EURUSD Grid Aggressive Research 2026-10-10 | allrr05-gridhr-raw-20x-3y-raw/report.htm | EURUSD M5 | 2023-10-10 → 2026-10-10 | 707 | 19.63 | 0.902 | +276.49 | 1.36 | 49.06 | 79.41 | 30.35 | 39.50 | 39.50 | 0.00 | — | — |
| EURUSD Grid Aggressive Research 2026-10-10 | allrr05-gridhr-raw-10x-3y-raw/report.htm | EURUSD M5 | 2023-10-10 → 2026-10-10 | 707 | 19.63 | 0.902 | +138.24 | 1.36 | 42.21 | 60.30 | 18.09 | 34.04 | 34.04 | 0.00 | — | — |
| EURUSD Grid Aggressive Research 2026-10-10 | allrr05-gridhr-raw-5x-3y-raw/report.htm | EURUSD M5 | 2023-10-10 → 2026-10-10 | 707 | 19.63 | 0.902 | +69.29 | 1.36 | 32.97 | 40.70 | 7.73 | 26.64 | 26.64 | 0.00 | — | — |
| FTMO Core3 vs Core4 DI OFF Phase Timing 2026-10-16 | allrr05-nasdaq-5m-candle-momentum-core-dioff-long-20261016/report.htm | USTEC M5 | 2021-10-06 → 2026-10-06 | 1193 | 19.89 | 0.915 | +142.61 | 1.17 | 14.98 | 28.23 | 13.25 | 13.45 | 27.13 | 13.68 | — | — |
| FTMO Core3 vs Core4 DI OFF Phase Timing 2026-10-16 | allrr05-nasdaq-5m-candle-momentum-core-dioff-long-20261016/report.htm.gz | USTEC M5 | 2021-10-06 → 2026-10-06 | 1193 | 19.89 | 0.915 | +142.61 | 1.17 | 14.98 | 28.23 | 13.25 | 13.45 | 27.13 | 13.68 | — | — |
| FTMO Exit Management Research 2026-09-27 | xag-native/report.htm.gz | XAGUSD M1 | 2026-03-02 → 2026-08-31 | 16 | 2.68 | 0.123 | +257.31 | 7.66 | 8.29 | 8.29 | 0.00 | 3.81 | 7.28 | 3.47 | relative | — |
| FTMO Exit Management Research 2026-09-27 | xau-native/report.htm.gz | XAUUSD M1 | 2026-03-02 → 2026-08-31 | 20 | 3.34 | 0.154 | +120.43 | 12.81 | 3.67 | 6.65 | 2.98 | 5.28 | 5.28 | 0.00 | maximal | doc:rel |
| FTMO Fourteen EA Study 2026-09-27 | news-pulse-xau/report.htm | XAUUSD M1 | 2025-09-27 → 2026-09-27 | 39 | 3.25 | 0.150 | +338.02 | 11.47 | 4.45 | 6.63 | 2.18 | 5.26 | 5.26 | 0.00 | maximal | doc:max |
| FTMO Fourteen EA Study 2026-09-27 | us100-h1-orb-13utc/report.htm | USTEC M15 | 2025-09-27 → 2026-09-27 | 74 | 6.17 | 0.285 | +22.74 | 1.64 | 6.84 | 6.84 | 0.00 | 4.87 | 5.40 | 0.53 | relative | — |
| Gann Three Ideas Raw 2026-10-09 | Pipeline 2026-10-09/allrr05-gp-fresh-original-gold-parity-raw/report.htm | XAUUSD M15 | 2023-10-09 → 2026-10-09 | 639 | 17.75 | 0.815 | +41.14 | 1.12 | 17.87 | 18.57 | 0.70 | 16.73 | 17.61 | 0.88 | — | — |
| Gann Three Ideas Raw 2026-10-09 | Pipeline 2026-10-09/allrr05-gp-fresh-original-gold-parity-raw/report.htm.gz | XAUUSD M15 | 2023-10-09 → 2026-10-09 | 639 | 17.75 | 0.815 | +41.14 | 1.12 | 17.87 | 18.57 | 0.70 | 16.73 | 17.61 | 0.88 | — | — |
| Gann Three Ideas Raw 2026-10-09 | Pipeline 2026-10-09/allrr05-gp-xauusd-eighth-rejection-3y-raw/report.htm | XAUUSD M15 | 2023-10-09 → 2026-10-09 | 639 | 17.75 | 0.815 | +41.14 | 1.12 | 17.87 | 18.57 | 0.70 | 16.73 | 17.61 | 0.88 | — | — |
| Gann Three Ideas Raw 2026-10-09 | Pipeline 2026-10-09/allrr05-gp-xauusd-eighth-rejection-3y-raw/report.htm.gz | XAUUSD M15 | 2023-10-09 → 2026-10-09 | 639 | 17.75 | 0.815 | +41.14 | 1.12 | 17.87 | 18.57 | 0.70 | 16.73 | 17.61 | 0.88 | — | — |
| Gann Three Ideas Raw 2026-10-09 | Pipeline 2026-10-09/parity-gold/report.htm.gz | XAUUSD M1 | 2023-10-09 → 2026-10-09 | 639 | 17.75 | 0.815 | +41.14 | 1.12 | 17.87 | 18.57 | 0.70 | 16.73 | 17.61 | 0.88 | — | — |
| Gann Three Ideas Raw 2026-10-09 | Pipeline 2026-10-09/parity-v2-gold/report.htm.gz | XAUUSD M1 | 2023-10-09 → 2026-10-09 | 639 | 17.75 | 0.815 | +41.14 | 1.12 | 17.87 | 18.57 | 0.70 | 16.73 | 17.61 | 0.88 | — | — |
| Gann Three Ideas Raw 2026-10-09 | allrr05-gann-xauusd-eighth-rejection-3y-raw/report.htm | XAUUSD M15 | 2023-10-09 → 2026-10-09 | 635 | 17.63 | 0.810 | +23.95 | 1.16 | 8.91 | 9.49 | 0.58 | 8.30 | 8.98 | 0.68 | — | — |
| Gann Three Ideas Raw 2026-10-09 | allrr05-gann-xauusd-eighth-rejection-3y-raw/report.htm.gz | XAUUSD M15 | 2023-10-09 → 2026-10-09 | 635 | 17.63 | 0.810 | +23.95 | 1.16 | 8.91 | 9.49 | 0.58 | 8.30 | 8.98 | 0.68 | — | — |
| Gold Intraday Bias Pipeline 2026-09-29 | raw-3y-m1/report-attempt0.htm.gz | XAUUSD M1 | 2023-09-20 → 2026-09-27 | 599 | 16.53 | 0.760 | +19.27 | 1.10 | 16.21 | 19.32 | 3.11 | 15.31 | 17.37 | 2.06 | maximal | doc:rel |
| Gold Intraday Bias Pipeline 2026-09-29 | control-5y-m1/report-attempt0.htm.gz | XAUUSD M1 | 2021-09-20 → 2026-09-27 | 1108 | 18.40 | 0.846 | +15.22 | 1.04 | 24.79 | 24.79 | 0.00 | 23.19 | 23.83 | 0.64 | relative | — |
| Gold Target Sensitivity 2026-10-02 | S-v3-5y-chunk3/reel-S-v3-5y-chunk3-d4f0752846.htm.gz | XAUUSD H4 | 2020-10-01 → 2026-10-02 | 242 | 3.36 | 0.155 | +59.91 | 1.24 | 23.38 | 31.66 | 8.28 | 21.64 | 31.00 | 9.36 | — | — |
| Indices Hourly EA Pipeline 2026-10-03 | hourprof-20261003-US100-1y-delay500/report.htm.gz | USTEC M1 | 2025-10-03 → 2026-10-03 | 1171 | 97.65 | 4.487 | +63.34 | 1.30 | 8.32 | 8.32 | 0.00 | 4.52 | 6.84 | 2.32 | — | — |
| Indices Hourly EA Pipeline 2026-10-03 | hourprof-20261003-US100-1y-baseline/report.htm.gz | USTEC M1 | 2025-10-03 → 2026-10-03 | 1171 | 97.65 | 4.487 | +62.05 | 1.30 | 8.29 | 8.29 | 0.00 | 4.49 | 6.80 | 2.31 | — | web |
| Indices Hourly EA Pipeline 2026-10-03 | hourprof-20261003-US100-1y-hold75/report.htm.gz | USTEC M1 | 2025-10-03 → 2026-10-03 | 922 | 76.89 | 3.533 | +55.18 | 1.30 | 5.66 | 7.53 | 1.87 | 4.76 | 6.47 | 1.71 | — | — |
| Indices Hourly EA Pipeline 2026-10-03 | hourprof-20261003-US100-1y-entry05/report.htm.gz | USTEC M1 | 2025-10-03 → 2026-10-03 | 1171 | 97.65 | 4.487 | +41.33 | 1.19 | 7.76 | 7.85 | 0.09 | 5.09 | 6.41 | 1.32 | — | — |
| Indices Hourly EA Pipeline 2026-10-03 | hourprof-20261003-US100-1y-hold45/report.htm.gz | USTEC M1 | 2025-10-03 → 2026-10-03 | 1171 | 97.65 | 4.487 | +42.64 | 1.22 | 5.43 | 6.32 | 0.89 | 5.01 | 6.07 | 1.06 | — | — |
| LTA Original Optimization 2026-10-05 | PARITY-acd50e7a5cd7ae/report.htm | XAUUSD M15 | 2025-10-05 → 2026-10-05 | 219 | 18.26 | 0.842 | +50.93 | 1.23 | 15.55 | 16.62 | 1.07 | 13.81 | 13.81 | 0.00 | — | doc:rel |
| LTA Original Optimization 2026-10-05 | PARITY-acd50e7a5cd7ae/report.htm.gz | XAUUSD M15 | 2025-10-05 → 2026-10-05 | 219 | 18.26 | 0.842 | +50.93 | 1.23 | 15.55 | 16.62 | 1.07 | 13.81 | 13.81 | 0.00 | — | doc:rel |
| LTA Original Optimization R2 2026-10-05 | PARITY-acd50e7a5cd7ae/report.htm | XAUUSD M15 | 2025-10-05 → 2026-10-05 | 219 | 18.26 | 0.842 | +50.93 | 1.23 | 15.55 | 16.62 | 1.07 | 13.81 | 13.81 | 0.00 | — | doc:rel |
| LTA Original Optimization R2 2026-10-05 | PARITY-acd50e7a5cd7ae/report.htm.gz | XAUUSD M15 | 2025-10-05 → 2026-10-05 | 219 | 18.26 | 0.842 | +50.93 | 1.23 | 15.55 | 16.62 | 1.07 | 13.81 | 13.81 | 0.00 | — | doc:rel |
| LTA Original Optimization R3 2026-10-05 | PARITY-acd50e7a5cd7ae/report.htm | XAUUSD M15 | 2025-10-05 → 2026-10-05 | 219 | 18.26 | 0.842 | +50.93 | 1.23 | 15.55 | 16.62 | 1.07 | 13.81 | 13.81 | 0.00 | — | doc:rel |
| LTA Original Optimization R3 2026-10-05 | PARITY-acd50e7a5cd7ae/report.htm.gz | XAUUSD M15 | 2025-10-05 → 2026-10-05 | 219 | 18.26 | 0.842 | +50.93 | 1.23 | 15.55 | 16.62 | 1.07 | 13.81 | 13.81 | 0.00 | — | doc:rel |
| LTA Original Optimization R4 2026-10-05 | T3Y-8cbf9280f4a041/report.htm | XAUUSD M15 | 2023-10-05 → 2026-10-05 | 445 | 12.36 | 0.569 | +143.99 | 1.25 | 15.38 | 23.18 | 7.80 | 13.65 | 21.82 | 8.17 | — | — |
| LTA Original Optimization R4 2026-10-05 | T3Y-8cbf9280f4a041/report.htm.gz | XAUUSD M15 | 2023-10-05 → 2026-10-05 | 445 | 12.36 | 0.569 | +143.99 | 1.25 | 15.38 | 23.18 | 7.80 | 13.65 | 21.82 | 8.17 | — | — |
| LTA Original Optimization R4 2026-10-05 | T5Y-d5c7800c2b6dde/report.htm | XAUUSD M15 | 2021-10-05 → 2026-10-05 | 617 | 10.28 | 0.473 | +107.72 | 1.17 | 15.39 | 23.26 | 7.87 | 13.61 | 21.70 | 8.09 | — | — |
| LTA Original Optimization R4 2026-10-05 | T5Y-d5c7800c2b6dde/report.htm.gz | XAUUSD M15 | 2021-10-05 → 2026-10-05 | 617 | 10.28 | 0.473 | +107.72 | 1.17 | 15.39 | 23.26 | 7.87 | 13.61 | 21.70 | 8.09 | — | — |
| LTA Original Optimization R4 2026-10-05 | D-37bb5e7f1098bd/report.htm | XAUUSD M5 | 2021-10-05 → 2024-10-05 | 390 | 10.83 | 0.497 | +41.30 | 1.13 | 15.53 | 21.77 | 6.24 | 13.89 | 19.88 | 5.99 | — | — |
| LTA Original Optimization R4 2026-10-05 | D-37bb5e7f1098bd/report.htm.gz | XAUUSD M5 | 2021-10-05 → 2024-10-05 | 390 | 10.83 | 0.497 | +41.30 | 1.13 | 15.53 | 21.77 | 6.24 | 13.89 | 19.88 | 5.99 | — | — |
| LTA Original Optimization R4 2026-10-05 | D-ed74c9f2b41229/report.htm | XAUUSD M5 | 2021-10-05 → 2024-10-05 | 390 | 10.83 | 0.497 | +41.30 | 1.13 | 15.53 | 21.77 | 6.24 | 13.89 | 19.88 | 5.99 | — | — |
| LTA Original Optimization R4 2026-10-05 | D-ed74c9f2b41229/report.htm.gz | XAUUSD M5 | 2021-10-05 → 2024-10-05 | 390 | 10.83 | 0.497 | +41.30 | 1.13 | 15.53 | 21.77 | 6.24 | 13.89 | 19.88 | 5.99 | — | — |
| LTA Original Optimization R4 2026-10-05 | D-68714de2c46f10/report.htm | XAUUSD M5 | 2021-10-05 → 2024-10-05 | 300 | 8.33 | 0.383 | +28.26 | 1.10 | 25.96 | 27.48 | 1.52 | 22.95 | 26.98 | 4.03 | — | — |
| LTA Original Optimization R4 2026-10-05 | D-68714de2c46f10/report.htm.gz | XAUUSD M5 | 2021-10-05 → 2024-10-05 | 300 | 8.33 | 0.383 | +28.26 | 1.10 | 25.96 | 27.48 | 1.52 | 22.95 | 26.98 | 4.03 | — | — |
| LTA Original Optimization R4 2026-10-05 | D-3158bfbe4cf9c3/report.htm | XAUUSD M5 | 2021-10-05 → 2024-10-05 | 264 | 7.33 | 0.337 | +31.85 | 1.27 | 14.63 | 16.76 | 2.13 | 13.59 | 16.64 | 3.05 | — | — |
| LTA Original Optimization R4 2026-10-05 | D-3158bfbe4cf9c3/report.htm.gz | XAUUSD M5 | 2021-10-05 → 2024-10-05 | 264 | 7.33 | 0.337 | +31.85 | 1.27 | 14.63 | 16.76 | 2.13 | 13.59 | 16.64 | 3.05 | — | — |
| LTA Original Optimization R4 2026-10-05 | D-39f54823cf2d11/report.htm | XAUUSD M5 | 2021-10-05 → 2024-10-05 | 503 | 13.97 | 0.642 | +35.96 | 1.15 | 15.97 | 18.08 | 2.11 | 15.70 | 17.60 | 1.90 | — | — |
| LTA Original Optimization R4 2026-10-05 | D-39f54823cf2d11/report.htm.gz | XAUUSD M5 | 2021-10-05 → 2024-10-05 | 503 | 13.97 | 0.642 | +35.96 | 1.15 | 15.97 | 18.08 | 2.11 | 15.70 | 17.60 | 1.90 | — | — |
| LTA Original Optimization R4 2026-10-05 | D-335e17dc69d9e9/report.htm | XAUUSD M5 | 2021-10-05 → 2024-10-05 | 365 | 10.14 | 0.466 | +37.06 | 1.22 | 16.11 | 17.79 | 1.68 | 15.84 | 17.03 | 1.19 | — | — |
| LTA Original Optimization R4 2026-10-05 | D-335e17dc69d9e9/report.htm.gz | XAUUSD M5 | 2021-10-05 → 2024-10-05 | 365 | 10.14 | 0.466 | +37.06 | 1.22 | 16.11 | 17.79 | 1.68 | 15.84 | 17.03 | 1.19 | — | — |
| LTA Original Optimization R4 2026-10-05 | D-bc55cb556b3338/report.htm | XAUUSD M5 | 2021-10-05 → 2024-10-05 | 365 | 10.14 | 0.466 | +37.06 | 1.22 | 16.11 | 17.79 | 1.68 | 15.84 | 17.03 | 1.19 | — | — |
| LTA Original Optimization R4 2026-10-05 | D-bc55cb556b3338/report.htm.gz | XAUUSD M5 | 2021-10-05 → 2024-10-05 | 365 | 10.14 | 0.466 | +37.06 | 1.22 | 16.11 | 17.79 | 1.68 | 15.84 | 17.03 | 1.19 | — | — |
| LTA Original Optimization R4 2026-10-05 | PARITY-acd50e7a5cd7ae/report.htm | XAUUSD M15 | 2025-10-05 → 2026-10-05 | 219 | 18.26 | 0.842 | +50.93 | 1.23 | 15.55 | 16.62 | 1.07 | 13.81 | 13.81 | 0.00 | — | doc:rel |
| LTA Original Optimization R4 2026-10-05 | PARITY-acd50e7a5cd7ae/report.htm.gz | XAUUSD M15 | 2025-10-05 → 2026-10-05 | 219 | 18.26 | 0.842 | +50.93 | 1.23 | 15.55 | 16.62 | 1.07 | 13.81 | 13.81 | 0.00 | — | doc:rel |
| LTA Original Optimization R4 2026-10-05 | T1Y-acd50e7a5cd7ae/report.htm | XAUUSD M15 | 2025-10-05 → 2026-10-05 | 219 | 18.26 | 0.842 | +50.93 | 1.23 | 15.55 | 16.62 | 1.07 | 13.81 | 13.81 | 0.00 | — | doc:rel |
| LTA Original Optimization R4 2026-10-05 | T1Y-acd50e7a5cd7ae/report.htm.gz | XAUUSD M15 | 2025-10-05 → 2026-10-05 | 219 | 18.26 | 0.842 | +50.93 | 1.23 | 15.55 | 16.62 | 1.07 | 13.81 | 13.81 | 0.00 | — | doc:rel |
| LTA Original Optimization R4 2026-10-05 | D-3b07af72841f25/report.htm | XAUUSD M5 | 2021-10-05 → 2024-10-05 | 550 | 15.27 | 0.702 | +31.35 | 1.13 | 15.98 | 17.03 | 1.05 | 15.24 | 15.93 | 0.69 | — | — |
| LTA Original Optimization R4 2026-10-05 | D-3b07af72841f25/report.htm.gz | XAUUSD M5 | 2021-10-05 → 2024-10-05 | 550 | 15.27 | 0.702 | +31.35 | 1.13 | 15.98 | 17.03 | 1.05 | 15.24 | 15.93 | 0.69 | — | — |
| LTA Original Optimization R4 2026-10-05 | D-29925d92f54762/report.htm | XAUUSD M5 | 2021-10-05 → 2024-10-05 | 446 | 12.39 | 0.569 | +48.00 | 1.14 | 21.50 | 21.50 | 0.00 | 19.07 | 19.61 | 0.54 | — | — |
| LTA Original Optimization R4 2026-10-05 | D-29925d92f54762/report.htm.gz | XAUUSD M5 | 2021-10-05 → 2024-10-05 | 446 | 12.39 | 0.569 | +48.00 | 1.14 | 21.50 | 21.50 | 0.00 | 19.07 | 19.61 | 0.54 | — | — |
| LTA VWAP Developing POC Comparison 2026-10-05 | SAFE_M15/report.htm | XAUUSD M15 | 2025-10-05 → 2026-10-05 | 219 | 18.26 | 0.842 | +50.93 | 1.23 | 15.55 | 16.62 | 1.07 | 13.81 | 13.81 | 0.00 | — | — |
| LTA VWAP Developing POC Comparison 2026-10-05 | SAFE_M15/report.htm.gz | XAUUSD M15 | 2025-10-05 → 2026-10-05 | 219 | 18.26 | 0.842 | +50.93 | 1.23 | 15.55 | 16.62 | 1.07 | 13.81 | 13.81 | 0.00 | — | — |
| Liquidity Continuation Raw 2026-09-27 | XAU-retest-control-6m/report.htm.gz | XAUUSD M5 | 2025-05-31 → 2026-09-27 | 177 | 11.13 | 0.513 | +29.19 | 1.33 | 8.23 | 9.42 | 1.19 | 9.38 | 9.38 | 0.00 | maximal | doc:rel |
| Matteo Golden Trio Raw 2026-10-06 | Pipeline 2026-10-07/control-vault-1-DEV/report.htm.gz | USTEC M1 | 2021-10-07 → 2023-10-07 | 447 | 18.64 | 0.856 | +1.42 | 1.01 | 9.36 | 9.43 | 0.07 | 8.59 | 9.17 | 0.58 | — | — |
| Matteo Golden Trio Raw 2026-10-06 | Pipeline 2026-10-07 R3/control-vault-1-DEV/report.htm.gz | USTEC M1 | 2021-10-07 → 2023-10-07 | 447 | 18.64 | 0.856 | +1.42 | 1.01 | 9.36 | 9.43 | 0.07 | 8.59 | 9.17 | 0.58 | — | — |
| Nasdaq 5M DI Filter Research 2026-09-23 | n5-current-5y-m4-d150/n5-current-5y-m4-d150.htm.gz | USTEC M5 | 2021-09-23 → 2026-09-23 | 1272 | 21.20 | 0.975 | +125.62 | 1.13 | 12.89 | 24.61 | 11.72 | 11.88 | 22.30 | 10.42 | — | — |
| Nasdaq 5M DI Filter Research 2026-09-23 | n5-di-5y-m4-d150/n5-di-5y-m4-d150.htm.gz | USTEC M5 | 2021-09-23 → 2026-09-23 | 969 | 16.15 | 0.743 | +177.21 | 1.21 | 10.87 | 20.59 | 9.72 | 10.05 | 19.69 | 9.64 | — | — |
| Nasdaq 5M DI Filter Research 2026-09-23 | n5-di-3y-m4-d150/n5-di-3y-m4-d150.htm.gz | USTEC M5 | 2023-09-23 → 2026-09-23 | 575 | 15.97 | 0.735 | +129.05 | 1.28 | 10.88 | 20.22 | 9.34 | 10.06 | 19.66 | 9.60 | — | — |
| Nasdaq 5M DI Filter Research 2026-09-23 | n5-current-3y-m4-d150/n5-current-3y-m4-d150.htm.gz | USTEC M5 | 2023-09-23 → 2026-09-23 | 762 | 21.16 | 0.974 | +118.99 | 1.18 | 12.87 | 20.23 | 7.36 | 11.86 | 19.25 | 7.39 | — | — |
| Nasdaq 5M Germany Transfer 2026-10-07 | USTEC-3y/report.htm.gz | USTEC M5 | 2023-10-07 → 2026-10-07 | 532 | 14.77 | 0.680 | +171.71 | 1.43 | 10.07 | 21.46 | 11.39 | 8.95 | 20.27 | 11.32 | — | — |
| Nasdaq 5M Germany Transfer 2026-10-07 | DE30-3y/report.htm.gz | DE30 M5 | 2023-10-07 → 2026-10-07 | 501 | 13.91 | 0.641 | +45.19 | 1.14 | 12.71 | 13.40 | 0.69 | 12.10 | 12.90 | 0.80 | — | — |
| Nasdaq 5M Index Transfer 2026-09-25 | n5idx-USTEC-NODI-5y/n5idx-USTEC-NODI-5y.htm.gz | USTEC M5 | 2021-09-25 → 2026-09-25 | 1272 | 21.20 | 0.975 | +133.84 | 1.14 | 12.88 | 24.65 | 11.77 | 11.87 | 22.35 | 10.48 | maximal | doc:max |
| Nasdaq 5M Index Transfer 2026-09-25 | n5idx-USTEC-DI-5y/n5idx-USTEC-DI-5y.htm.gz | USTEC M5 | 2021-09-25 → 2026-09-25 | 968 | 16.14 | 0.742 | +180.24 | 1.22 | 10.88 | 20.56 | 9.68 | 10.06 | 19.65 | 9.59 | maximal | doc:max |
| Nasdaq 5M Index Transfer 2026-09-25 | n5idx-USTEC-DI-3y/n5idx-USTEC-DI-3y.htm.gz | USTEC M5 | 2023-09-25 → 2026-09-25 | 576 | 16.00 | 0.735 | +133.59 | 1.29 | 10.88 | 20.22 | 9.34 | 10.06 | 19.66 | 9.60 | maximal | doc:max |
| Nasdaq 5M Index Transfer 2026-09-25 | n5idx-USTEC-NODI-3y/n5idx-USTEC-NODI-3y.htm.gz | USTEC M5 | 2023-09-25 → 2026-09-25 | 764 | 21.22 | 0.974 | +128.95 | 1.20 | 12.87 | 20.23 | 7.36 | 11.86 | 19.25 | 7.39 | maximal | doc:max |
| Nasdaq 5M Next Day Efficiency ML 2026-10-05 | 2Y_LAG/report.htm | USTEC M5 | 2024-10-05 → 2026-10-05 | 186 | 7.76 | 0.358 | +85.92 | 1.68 | 10.07 | 10.60 | 0.53 | 5.62 | 8.51 | 2.89 | — | — |
| Nasdaq 5M Next Day Efficiency ML 2026-10-05 | 2Y_ML/report.htm | USTEC M5 | 2024-10-05 → 2026-10-05 | 239 | 9.97 | 0.460 | +101.67 | 1.60 | 10.46 | 12.72 | 2.26 | 9.70 | 9.91 | 0.21 | — | — |
| Nasdaq 5M QuantLab Style Research 2026-09-25 | n5ql-USTEC-QL_ATR-3y/n5ql-USTEC-QL_ATR-3y.htm.gz | USTEC M5 | 2023-09-25 → 2026-09-25 | 536 | 14.89 | 0.684 | +162.16 | 1.40 | 10.06 | 21.44 | 11.38 | 8.94 | 20.25 | 11.31 | maximal | doc:max |
| Nasdaq 5M QuantLab Style Research 2026-09-25 | n5ql-USTEC-CURRENT-5y/n5ql-USTEC-CURRENT-5y.htm.gz | USTEC M5 | 2021-09-25 → 2026-09-25 | 968 | 16.14 | 0.742 | +180.24 | 1.22 | 10.88 | 20.56 | 9.68 | 10.06 | 19.65 | 9.59 | maximal | doc:max |
| Nasdaq 5M QuantLab Style Research 2026-09-25 | n5ql-USTEC-CURRENT-3y/n5ql-USTEC-CURRENT-3y.htm.gz | USTEC M5 | 2023-09-25 → 2026-09-25 | 576 | 16.00 | 0.735 | +133.59 | 1.29 | 10.88 | 20.22 | 9.34 | 10.06 | 19.66 | 9.60 | maximal | doc:max |
| Nasdaq Video Match 2026-10-03 | EMA_ONLY-5y/report.htm.gz | USTEC M5 | 2021-10-02 → 2026-10-02 | 1194 | 19.90 | 0.916 | +148.99 | 1.17 | 14.99 | 28.24 | 13.25 | 13.47 | 27.13 | 13.66 | — | doc:rel |
| Nasdaq Video Match 2026-10-03 | VIDEO_ATR-5y/report.htm.gz | USTEC M5 | 2021-10-02 → 2026-10-02 | 1130 | 18.84 | 0.867 | +73.13 | 1.10 | 17.98 | 29.30 | 11.32 | 16.88 | 28.52 | 11.64 | — | doc:rel |
| Nasdaq Video Match 2026-10-03 | VIDEO_ATR_DI-1y/report.htm.gz | USTEC M5 | 2025-10-02 → 2026-10-02 | 169 | 14.09 | 0.648 | +43.59 | 1.40 | 8.61 | 9.17 | 0.56 | 7.50 | 8.04 | 0.54 | — | doc:rel |
| Negative RR Study 2026-10-21 | base-dioff/allrr05-nasdaq-5m-candle-momentum-half/report.htm | USTEC M5 | 2021-10-06 → 2026-10-06 | 1193 | 19.89 | 0.915 | +145.44 | 1.17 | 14.96 | 28.19 | 13.23 | 13.44 | 27.09 | 13.65 | — | doc:rel |
| Negative RR Study 2026-10-21 | base-dioff/allrr05-nasdaq-5m-candle-momentum-half/report.htm.gz | USTEC M5 | 2021-10-06 → 2026-10-06 | 1193 | 19.89 | 0.915 | +145.44 | 1.17 | 14.96 | 28.19 | 13.23 | 13.44 | 27.09 | 13.65 | — | doc:rel |
| Negative RR Study 2026-10-21 | rr075/allrr05-3-way-gold-half/report.htm | XAUUSD M15 | 2021-10-06 → 2026-10-06 | 711 | 11.85 | 0.545 | +65.94 | 1.18 | 8.55 | 10.37 | 1.82 | 8.04 | 9.83 | 1.79 | — | doc:rel |
| Negative RR Study 2026-10-21 | rr075/allrr05-3-way-gold-half/report.htm.gz | XAUUSD M15 | 2021-10-06 → 2026-10-06 | 711 | 11.85 | 0.545 | +65.94 | 1.18 | 8.55 | 10.37 | 1.82 | 8.04 | 9.83 | 1.79 | — | doc:rel |
| Negative RR Study 2026-10-21 | rr060/allrr05-3-way-gold-half/report.htm | XAUUSD M15 | 2021-10-06 → 2026-10-06 | 783 | 13.05 | 0.600 | +69.51 | 1.20 | 8.98 | 10.11 | 1.13 | 8.31 | 8.41 | 0.10 | — | doc:rel |
| Negative RR Study 2026-10-21 | rr060/allrr05-3-way-gold-half/report.htm.gz | XAUUSD M15 | 2021-10-06 → 2026-10-06 | 783 | 13.05 | 0.600 | +69.51 | 1.20 | 8.98 | 10.11 | 1.13 | 8.31 | 8.41 | 0.10 | — | doc:rel |
| Negative RR Study 2026-10-21 | base/allrr05-3-way-gold-half/report.htm | XAUUSD M15 | 2021-10-06 → 2026-10-06 | 773 | 12.89 | 0.593 | +105.61 | 1.33 | 10.42 | 11.42 | 1.00 | 8.89 | 9.82 | 0.93 | — | doc:rel |
| Negative RR Study 2026-10-21 | base/allrr05-3-way-gold-half/report.htm.gz | XAUUSD M15 | 2021-10-06 → 2026-10-06 | 773 | 12.89 | 0.593 | +105.61 | 1.33 | 10.42 | 11.42 | 1.00 | 8.89 | 9.82 | 0.93 | — | doc:rel |
| Negative RR Study 2026-10-21 | base/allrr05-us100-month-end-flow-half/report.htm | USTEC M30 | 2021-10-06 → 2026-10-06 | 175 | 2.92 | 0.134 | +38.49 | 1.37 | 8.88 | 9.76 | 0.88 | 7.58 | 7.63 | 0.05 | — | doc:rel |
| Negative RR Study 2026-10-21 | base/allrr05-us100-month-end-flow-half/report.htm.gz | USTEC M30 | 2021-10-06 → 2026-10-06 | 175 | 2.92 | 0.134 | +38.49 | 1.37 | 8.88 | 9.76 | 0.88 | 7.58 | 7.63 | 0.05 | — | doc:rel |
| News Pulse Event Parameters Research 2026-09-19 | NativeFullBestDelay250/news-event-NativeFullBestDelay250.htm | XAUUSD M1 | 2025-09-19 → 2026-09-19 | 39 | 3.25 | 0.149 | +331.07 | 11.40 | 4.46 | 6.79 | 2.33 | 5.36 | 5.36 | 0.00 | — | doc:rel |
| News Pulse Event Parameters Research 2026-09-19 | NativeFullBestDelay250V2/news-event-NativeFullBestDelay250V2.htm | XAUUSD M1 | 2025-09-19 → 2026-09-19 | 39 | 3.25 | 0.149 | +331.07 | 11.40 | 4.46 | 6.79 | 2.33 | 5.36 | 5.36 | 0.00 | — | doc:rel |
| News Pulse Event Parameters Research 2026-09-19 | NativeXauEvent1y/news-event-NativeXauEvent1y.htm | XAUUSD M1 | 2025-09-05 → 2026-09-05 | 40 | 3.34 | 0.153 | +300.00 | 13.12 | 4.50 | 6.68 | 2.18 | 5.28 | 5.28 | 0.00 | — | web |
| News Pulse Event Parameters Research 2026-09-19 | NativeXauEvent6m/news-event-NativeXauEvent6m.htm | XAUUSD M1 | 2026-03-05 → 2026-09-05 | 22 | 3.64 | 0.167 | +167.04 | 14.53 | 4.53 | 6.67 | 2.14 | 5.27 | 5.27 | 0.00 | — | web |
| News Pulse Event Parameters Research 2026-09-19 | NativeXauEvent3y/news-event-NativeXauEvent3y.htm | XAUUSD M1 | 2023-09-05 → 2026-09-05 | 121 | 3.36 | 0.154 | +1029.12 | 10.69 | 4.49 | 6.61 | 2.12 | 5.22 | 5.22 | 0.00 | — | web |
| News Pulse Event Parameters Research 2026-09-19 | NativeXauEvent5y/news-event-NativeXauEvent5y.htm | XAUUSD M1 | 2021-09-05 → 2026-09-05 | 194 | 3.23 | 0.149 | +2394.29 | 10.22 | 4.49 | 6.60 | 2.11 | 5.21 | 5.21 | 0.00 | — | web |
| News Pulse Event Parameters Research 2026-09-19 | NativeFullBest/news-event-NativeFullBest.htm | XAUUSD M1 | 2025-09-19 → 2026-09-19 | 38 | 3.17 | 0.146 | +262.10 | 10.64 | 4.50 | 6.60 | 2.10 | 5.21 | 5.21 | 0.00 | — | doc:rel |
| News Pulse Event Parameters Research 2026-09-19 | NativeFullBestV2/news-event-NativeFullBestV2.htm | XAUUSD M1 | 2025-09-19 → 2026-09-19 | 38 | 3.17 | 0.146 | +262.10 | 10.64 | 4.50 | 6.60 | 2.10 | 5.21 | 5.21 | 0.00 | — | doc:rel |
| News Pulse Event Parameters Research 2026-09-19 | NativeProductionParity/news-event-NativeProductionParity.htm | XAUUSD M1 | 2025-09-19 → 2026-09-19 | 38 | 3.17 | 0.146 | +262.10 | 10.64 | 4.50 | 6.60 | 2.10 | 5.21 | 5.21 | 0.00 | — | doc:rel |
| News Pulse Multi Asset Event Parameters 2026-09-19 | EURUSDProduction1y/multi-news-EURUSDProduction1y.htm | EURUSD M1 | 2025-09-05 → 2026-09-05 | 46 | 3.84 | 0.176 | +919.45 | 11.37 | 4.26 | 21.12 | 16.86 | 11.94 | 11.94 | 0.00 | — | doc:rel, web |
| News Pulse Multi Asset Event Parameters 2026-09-19 | EURUSDFitted/multi-news-EURUSDFitted.htm | EURUSD M1 | 2025-09-19 → 2026-09-19 | 45 | 3.75 | 0.172 | +751.20 | 9.62 | 4.26 | 21.11 | 16.85 | 11.94 | 11.94 | 0.00 | — | doc:rel |
| News Pulse Multi Asset Event Parameters 2026-09-19 | EURUSDProductionParity/multi-news-EURUSDProductionParity.htm | EURUSD M1 | 2025-09-19 → 2026-09-19 | 45 | 3.75 | 0.172 | +751.20 | 9.62 | 4.26 | 21.11 | 16.85 | 11.94 | 11.94 | 0.00 | — | doc:rel |
| News Pulse Multi Asset Event Parameters 2026-09-19 | EURUSDFittedDelay250/multi-news-EURUSDFittedDelay250.htm | EURUSD M1 | 2025-09-19 → 2026-09-19 | 45 | 3.75 | 0.172 | +729.79 | 9.45 | 4.50 | 21.06 | 16.56 | 11.88 | 11.88 | 0.00 | — | doc:rel |
| News Pulse Multi Asset Event Parameters 2026-09-19 | XAGProduction5y/multi-news-XAGProduction5y.htm | XAGUSD M1 | 2021-09-05 → 2026-09-05 | 139 | 2.32 | 0.107 | +5340.19 | 8.92 | 8.78 | 17.97 | 9.19 | 4.15 | 18.17 | 14.02 | — | doc:rel, web |
| News Pulse Multi Asset Event Parameters 2026-09-19 | EURUSDProduction5y/multi-news-EURUSDProduction5y.htm | EURUSD M1 | 2021-09-05 → 2026-09-05 | 240 | 4.00 | 0.184 | +38947.79 | 9.02 | 3.33 | 16.52 | 13.19 | 1.14 | 5.18 | 4.04 | — | doc:rel, web |
| News Pulse Multi Asset Event Parameters 2026-09-19 | BTCProduction3y/multi-news-BTCProduction3y.htm | BTCUSD M1 | 2023-09-05 → 2026-09-05 | 147 | 4.08 | 0.188 | +24256.27 | 11.84 | 20.07 | 32.35 | 12.28 | 14.02 | 25.38 | 11.36 | — | doc:rel, web |
| News Pulse Multi Asset Event Parameters 2026-09-19 | BTCProduction5y/multi-news-BTCProduction5y.htm | BTCUSD M1 | 2021-09-05 → 2026-09-05 | 242 | 4.03 | 0.185 | +43775.44 | 8.54 | 13.32 | 25.13 | 11.81 | 10.01 | 20.66 | 10.65 | — | doc:rel, web |
| News Pulse Multi Asset Event Parameters 2026-09-19 | EURUSDProduction3y/multi-news-EURUSDProduction3y.htm | EURUSD M1 | 2023-09-05 → 2026-09-05 | 147 | 4.08 | 0.188 | +21300.13 | 8.78 | 9.39 | 18.36 | 8.97 | 2.46 | 3.93 | 1.47 | — | doc:rel, web |
| News Pulse Multi Asset Event Parameters 2026-09-19 | XAGProduction3y/multi-news-XAGProduction3y.htm | XAGUSD M1 | 2023-09-05 → 2026-09-05 | 90 | 2.50 | 0.115 | +3719.67 | 9.47 | 8.78 | 11.54 | 2.76 | 4.15 | 11.46 | 7.31 | — | doc:rel, CLAUDE.md, web |
| News Pulse Multi Asset Event Parameters 2026-09-19 | XAGProduction1y/multi-news-XAGProduction1y.htm | XAGUSD M1 | 2025-09-05 → 2026-09-05 | 34 | 2.84 | 0.130 | +2079.63 | 10.87 | 8.77 | 11.42 | 2.65 | 4.15 | 11.44 | 7.29 | — | doc:rel, web |
| News Pulse Multi Asset Event Parameters 2026-09-19 | XAGFitted/multi-news-XAGFitted.htm | XAGUSD M1 | 2025-09-19 → 2026-09-19 | 33 | 2.75 | 0.126 | +2523.64 | 8.67 | 8.78 | 11.45 | 2.67 | 4.31 | 11.47 | 7.16 | — | doc:rel |
| News Pulse Multi Asset Event Parameters 2026-09-19 | XAGProductionParity/multi-news-XAGProductionParity.htm | XAGUSD M1 | 2025-09-19 → 2026-09-19 | 33 | 2.75 | 0.126 | +2523.64 | 8.67 | 8.78 | 11.45 | 2.67 | 4.31 | 11.47 | 7.16 | — | doc:rel |
| News Pulse Multi Asset Event Parameters 2026-09-19 | XAGFittedDelay250/multi-news-XAGFittedDelay250.htm | XAGUSD M1 | 2025-09-19 → 2026-09-19 | 32 | 2.67 | 0.123 | +2655.34 | 8.93 | 5.13 | 10.81 | 5.68 | 4.31 | 10.83 | 6.52 | — | doc:rel |
| News Pulse Multi Asset Event Parameters 2026-09-19 | XAGProduction6m/multi-news-XAGProduction6m.htm | XAGUSD M1 | 2026-03-05 → 2026-09-05 | 18 | 2.98 | 0.136 | +400.72 | 10.85 | 8.79 | 8.79 | 0.00 | 4.16 | 8.81 | 4.65 | — | web |
| News Pulse Multi Asset Event Parameters 2026-09-19 | BTCProduction1y/multi-news-BTCProduction1y.htm | BTCUSD M1 | 2025-09-05 → 2026-09-05 | 52 | 4.34 | 0.199 | +6344.62 | 9.39 | 7.72 | 12.21 | 4.49 | 5.00 | 5.00 | 0.00 | — | doc:rel, web |
| News Pulse Multi Asset Event Parameters 2026-09-19 | BTCFitted/multi-news-BTCFitted.htm | BTCUSD M1 | 2025-09-19 → 2026-09-19 | 49 | 4.09 | 0.188 | +3773.32 | 10.22 | 9.17 | 12.22 | 3.05 | 4.04 | 5.00 | 0.96 | — | doc:rel |
| News Pulse Multi Asset Event Parameters 2026-09-19 | BTCProductionParity/multi-news-BTCProductionParity.htm | BTCUSD M1 | 2025-09-19 → 2026-09-19 | 49 | 4.09 | 0.188 | +3773.32 | 10.22 | 9.17 | 12.22 | 3.05 | 4.04 | 5.00 | 0.96 | — | doc:rel |
| News Pulse Multi Asset Event Parameters 2026-09-19 | EURUSDProduction6m/multi-news-EURUSDProduction6m.htm | EURUSD M1 | 2026-03-05 → 2026-09-05 | 24 | 3.97 | 0.182 | +394.50 | 15.47 | 4.26 | 5.86 | 1.60 | 5.27 | 5.27 | 0.00 | — | doc:rel, web |
| News Pulse Multi Asset Event Parameters 2026-09-19 | BTCProduction6m/multi-news-BTCProduction6m.htm | BTCUSD M1 | 2026-03-05 → 2026-09-05 | 29 | 4.80 | 0.220 | +303.43 | 7.99 | 8.74 | 9.97 | 1.23 | 4.05 | 5.00 | 0.95 | — | doc:rel, web |
| News Pulse Multi Asset Event Parameters 2026-09-19 | XAGBaselineDelay250/multi-news-XAGBaselineDelay250.htm | XAGUSD M1 | 2025-09-19 → 2026-09-19 | 38 | 3.17 | 0.146 | +86.00 | 4.15 | 3.95 | 5.10 | 1.15 | 3.90 | 4.28 | 0.38 | — | doc:rel |
| News Pulse Multi Asset Event Parameters 2026-09-19 | XAGBaseline/multi-news-XAGBaseline.htm | XAGUSD M1 | 2025-09-19 → 2026-09-19 | 38 | 3.17 | 0.146 | +81.74 | 3.99 | 3.99 | 4.77 | 0.78 | 3.94 | 4.28 | 0.34 | — | doc:rel |
| News Pulse XAG Current Audit 2026-10-05 | 1Y-150/report.htm | XAGUSD M1 | 2025-10-05 → 2026-10-05 | 39 | 3.25 | 0.150 | +2622.82 | 7.56 | 4.62 | 11.28 | 6.66 | 4.66 | 11.30 | 6.64 | — | doc:rel |
| News Pulse XAG Current Audit 2026-10-05 | 1Y-150/report.htm.gz | XAGUSD M1 | 2025-10-05 → 2026-10-05 | 39 | 3.25 | 0.150 | +2622.82 | 7.56 | 4.62 | 11.28 | 6.66 | 4.66 | 11.30 | 6.64 | — | doc:rel |
| News Pulse XAG Current Audit 2026-10-05 | 6M-150/report.htm | XAGUSD M1 | 2026-04-05 → 2026-10-05 | 22 | 3.66 | 0.169 | +543.57 | 7.75 | 4.63 | 9.32 | 4.69 | 4.66 | 9.35 | 4.69 | — | doc:rel |
| News Pulse XAG Current Audit 2026-10-05 | 6M-150/report.htm.gz | XAGUSD M1 | 2026-04-05 → 2026-10-05 | 22 | 3.66 | 0.169 | +543.57 | 7.75 | 4.63 | 9.32 | 4.69 | 4.66 | 9.35 | 4.69 | — | doc:rel |
| News Pulse XAG Current Audit 2026-10-05 | 3M-3000/report.htm | XAGUSD M1 | 2026-07-05 → 2026-10-05 | 13 | 4.30 | 0.200 | +196.84 | 7.12 | 5.01 | 8.75 | 3.74 | 4.67 | 6.67 | 2.00 | — | doc:rel |
| News Pulse XAG Current Audit 2026-10-05 | 3M-3000/report.htm.gz | XAGUSD M1 | 2026-07-05 → 2026-10-05 | 13 | 4.30 | 0.200 | +196.84 | 7.12 | 5.01 | 8.75 | 3.74 | 4.67 | 6.67 | 2.00 | — | doc:rel |
| News Pulse XAG Current Audit 2026-10-05 | 3M-150/report.htm | XAGUSD M1 | 2026-07-05 → 2026-10-05 | 13 | 4.30 | 0.200 | +213.19 | 7.27 | 4.63 | 8.31 | 3.68 | 4.66 | 6.28 | 1.62 | — | doc:rel |
| News Pulse XAG Current Audit 2026-10-05 | 3M-150/report.htm.gz | XAGUSD M1 | 2026-07-05 → 2026-10-05 | 13 | 4.30 | 0.200 | +213.19 | 7.27 | 4.63 | 8.31 | 3.68 | 4.66 | 6.28 | 1.62 | — | doc:rel |
| News Standalone Risk 2026-09-28 | EURUSD-new-1.25/report.htm.gz | EURUSD M1 | 2026-07-01 → 2026-08-01 | 5 | 4.91 | 0.217 | +137.42 | 15.35 | 4.04 | 4.55 | 0.51 | 3.63 | 3.63 | 0.00 | — | web |
| News XAU Placement Fix 2026-10-03 | Current-test-1000-2025.10.03/report.htm.gz | XAUUSD M1 | 2025-10-03 → 2026-10-03 | 38 | 3.17 | 0.146 | +292.30 | 10.41 | 3.92 | 6.74 | 2.82 | 5.36 | 5.36 | 0.00 | — | — |
| News XAU Placement Fix 2026-10-03 | Current-test-150-2025.10.03/report.htm.gz | XAUUSD M1 | 2025-10-03 → 2026-10-03 | 39 | 3.25 | 0.149 | +338.02 | 11.47 | 4.45 | 6.63 | 2.18 | 5.26 | 5.26 | 0.00 | — | — |
| No Wick Multi Asset Raw 2026-09-30 | nw-USTEC-S5-6m/nw-USTEC-S5-6m.htm.gz | USTEC M5 | 2026-03-30 → 2026-09-30 | 451 | 74.60 | 3.417 | +26.44 | 1.09 | 12.64 | 13.46 | 0.82 | 12.56 | 12.74 | 0.18 | maximal | doc:rel, CLAUDE.md |
| Overnight VA First Candle Trail Research 2026-09-23 | onvt-XAUUSD-anytime-m15-1y-m4-d150/onvt-XAUUSD-anytime-m15-1y-m4-d150.htm.gz | XAUUSD M5 | 2025-09-23 → 2026-09-23 | 244 | 20.35 | 0.935 | +25.88 | 1.16 | 27.45 | 27.45 | 0.00 | 17.50 | 20.83 | 3.33 | — | doc:rel |
| Overnight VA First Candle Trail Research 2026-09-23 | onvt-XAUUSD-anytime-trail1r-1y-m4-d150/onvt-XAUUSD-anytime-trail1r-1y-m4-d150.htm.gz | XAUUSD M5 | 2025-09-23 → 2026-09-23 | 244 | 20.35 | 0.935 | +57.89 | 1.33 | 18.48 | 21.69 | 3.21 | 15.91 | 16.69 | 0.78 | — | doc:rel |
| Overnight VA First Candle Trail Research 2026-09-23 | onvt-XAUUSD-anytime-target1r-6m-m4-d150/onvt-XAUUSD-anytime-target1r-6m-m4-d150.htm.gz | XAUUSD M5 | 2026-03-19 → 2026-09-19 | 101 | 16.71 | 0.765 | +47.35 | 1.69 | 8.40 | 10.86 | 2.46 | 7.63 | 7.63 | 0.00 | — | doc:rel |
| Overnight VA First Candle Trail Research 2026-09-23 | onvt-BTCUSD-first-trail1r-1y-m4-d150/onvt-BTCUSD-first-trail1r-1y-m4-d150.htm.gz | BTCUSD M5 | 2025-09-23 → 2026-09-23 | 119 | 9.92 | 0.456 | +21.50 | 1.24 | 18.62 | 20.36 | 1.74 | 16.37 | 16.37 | 0.00 | — | doc:rel |
| PBD Gold Validation 2026-10-02 | real-2026/goldval-real-2026-08c05cc5.htm.gz | XAUUSD M1 | 2026-01-01 → 2026-10-02 | 53 | 5.89 | 0.270 | +17.64 | 1.76 | 5.47 | 6.05 | 0.58 | 5.10 | 5.10 | 0.00 | — | doc:rel |
| Portfolio Long History 2026-10-08 | allrr05-news-pulse-btc-long-1abd36c90f3b/report.htm | BTCUSD M1 | 2021-10-06 → 2026-10-06 | 242 | 4.03 | 0.186 | +46724.89 | 8.78 | 10.93 | 26.98 | 16.05 | 8.13 | 26.84 | 18.71 | — | — |
| Portfolio Long History 2026-10-08 | allrr05-news-pulse-btc-long-1abd36c90f3b/report.htm.gz | BTCUSD M1 | 2021-10-06 → 2026-10-06 | 242 | 4.03 | 0.186 | +46724.89 | 8.78 | 10.93 | 26.98 | 16.05 | 8.13 | 26.84 | 18.71 | — | — |
| Portfolio Long History 2026-10-08 | allrr05-news-pulse-eurusd-long-c1a8fbdd1ff3/report.htm | EURUSD M1 | 2021-10-06 → 2026-10-06 | 256 | 4.27 | 0.196 | +43115.69 | 8.96 | 2.93 | 20.56 | 17.63 | 1.03 | 6.32 | 5.29 | — | — |
| Portfolio Long History 2026-10-08 | allrr05-news-pulse-eurusd-long-c1a8fbdd1ff3/report.htm.gz | EURUSD M1 | 2021-10-06 → 2026-10-06 | 256 | 4.27 | 0.196 | +43115.69 | 8.96 | 2.93 | 20.56 | 17.63 | 1.03 | 6.32 | 5.29 | — | — |
| Portfolio Long History 2026-10-08 | allrr05-news-pulse-xag-long-05a7fb91fcfa/report.htm | XAGUSD M1 | 2021-10-06 → 2026-10-06 | 151 | 2.52 | 0.116 | +23190.56 | 7.00 | 5.47 | 20.95 | 15.48 | 5.50 | 21.33 | 15.83 | — | — |
| Portfolio Long History 2026-10-08 | allrr05-news-pulse-xag-long-05a7fb91fcfa/report.htm.gz | XAGUSD M1 | 2021-10-06 → 2026-10-06 | 151 | 2.52 | 0.116 | +23190.56 | 7.00 | 5.47 | 20.95 | 15.48 | 5.50 | 21.33 | 15.83 | — | — |
| Portfolio Long History 2026-10-08 | allrr05-xau-slow-trend-long-7541cb232c8c/report.htm | XAUUSD H4 | 2021-10-06 → 2026-10-06 | 1020 | 17.00 | 0.782 | +81.70 | 1.13 | 15.66 | 21.09 | 5.43 | 14.49 | 20.34 | 5.85 | — | — |
| Portfolio Long History 2026-10-08 | allrr05-xau-slow-trend-long-7541cb232c8c/report.htm.gz | XAUUSD H4 | 2021-10-06 → 2026-10-06 | 1020 | 17.00 | 0.782 | +81.70 | 1.13 | 15.66 | 21.09 | 5.43 | 14.49 | 20.34 | 5.85 | — | — |
| Portfolio Long History 2026-10-08 | allrr05-xau-regime-switch-long-202aaccf8ba2/report.htm | XAUUSD M5 | 2021-10-06 → 2026-10-06 | 205 | 3.42 | 0.157 | +91.54 | 1.44 | 18.13 | 19.47 | 1.34 | 14.59 | 17.35 | 2.76 | — | — |
| Portfolio Long History 2026-10-08 | allrr05-xau-regime-switch-long-202aaccf8ba2/report.htm.gz | XAUUSD M5 | 2021-10-06 → 2026-10-06 | 205 | 3.42 | 0.157 | +91.54 | 1.44 | 18.13 | 19.47 | 1.34 | 14.59 | 17.35 | 2.76 | — | — |
| Portfolio Long History 2026-10-08 | allrr05-xau-elliott-wave-1-2-3-long-067d56035da9/report.htm | XAUUSD H4 | 2021-10-06 → 2026-10-06 | 117 | 1.95 | 0.090 | +66.11 | 1.67 | 13.39 | 13.39 | 0.00 | 7.98 | 10.58 | 2.60 | — | — |
| Portfolio Long History 2026-10-08 | allrr05-xau-elliott-wave-1-2-3-long-067d56035da9/report.htm.gz | XAUUSD H4 | 2021-10-06 → 2026-10-06 | 117 | 1.95 | 0.090 | +66.11 | 1.67 | 13.39 | 13.39 | 0.00 | 7.98 | 10.58 | 2.60 | — | — |
| Portfolio Long History 2026-10-08 | allrr05-btc-poc-fibonacci-long-d31dc8212068/report.htm | BTCUSD M15 | 2021-10-06 → 2026-10-06 | 115 | 1.92 | 0.088 | +38.96 | 1.39 | 14.64 | 14.64 | 0.00 | 9.54 | 11.75 | 2.21 | — | — |
| Portfolio Long History 2026-10-08 | allrr05-btc-poc-fibonacci-long-d31dc8212068/report.htm.gz | BTCUSD M15 | 2021-10-06 → 2026-10-06 | 115 | 1.92 | 0.088 | +38.96 | 1.39 | 14.64 | 14.64 | 0.00 | 9.54 | 11.75 | 2.21 | — | — |
| Portfolio Long History 2026-10-08 | allrr05-asia-breakout-long-094b3e2656e9/report.htm | XAUUSD H1 | 2021-10-06 → 2026-10-06 | 189 | 3.15 | 0.145 | +46.16 | 1.33 | 8.30 | 9.23 | 0.93 | 6.63 | 8.40 | 1.77 | — | — |
| Portfolio Long History 2026-10-08 | allrr05-asia-breakout-long-094b3e2656e9/report.htm.gz | XAUUSD H1 | 2021-10-06 → 2026-10-06 | 189 | 3.15 | 0.145 | +46.16 | 1.33 | 8.30 | 9.23 | 0.93 | 6.63 | 8.40 | 1.77 | — | — |
| Portfolio Long History 2026-10-08 | allrr05-3-way-gold-long-b8a53e250c8f/report.htm | XAUUSD M15 | 2021-10-06 → 2026-10-06 | 773 | 12.89 | 0.593 | +105.78 | 1.33 | 10.41 | 11.44 | 1.03 | 8.89 | 9.43 | 0.54 | — | — |
| Portfolio Long History 2026-10-08 | allrr05-3-way-gold-long-b8a53e250c8f/report.htm.gz | XAUUSD M15 | 2021-10-06 → 2026-10-06 | 773 | 12.89 | 0.593 | +105.78 | 1.33 | 10.41 | 11.44 | 1.03 | 8.89 | 9.43 | 0.54 | — | — |
| Portfolio Long History 2026-10-08 | allrr05-3-way-gold-long-c95671d4b15c/report.htm | XAUUSD M15 | 2021-10-06 → 2026-10-06 | 773 | 12.89 | 0.593 | +105.78 | 1.33 | 10.41 | 11.44 | 1.03 | 8.89 | 9.43 | 0.54 | — | — |
| Portfolio Long History 2026-10-08 | allrr05-3-way-gold-long-c95671d4b15c/report.htm.gz | XAUUSD M15 | 2021-10-06 → 2026-10-06 | 773 | 12.89 | 0.593 | +105.78 | 1.33 | 10.41 | 11.44 | 1.03 | 8.89 | 9.43 | 0.54 | — | — |
| Portfolio Long History 2026-10-08 | allrr05-us100-month-end-flow-long-3723b01f81aa/report.htm | USTEC M30 | 2021-10-06 → 2026-10-06 | 175 | 2.92 | 0.134 | +38.43 | 1.37 | 8.88 | 9.76 | 0.88 | 7.58 | 7.63 | 0.05 | — | — |
| Portfolio Long History 2026-10-08 | allrr05-us100-month-end-flow-long-3723b01f81aa/report.htm.gz | USTEC M30 | 2021-10-06 → 2026-10-06 | 175 | 2.92 | 0.134 | +38.43 | 1.37 | 8.88 | 9.76 | 0.88 | 7.58 | 7.63 | 0.05 | — | — |
| Portfolio Long History 2026-10-08 | allrr05-xau-trend-progression-long-3ea55fd5bd70/report.htm | XAUUSD H4 | 2021-10-06 → 2026-10-06 | 213 | 3.55 | 0.163 | +14.18 | 1.16 | 8.11 | 8.65 | 0.54 | 8.20 | 8.20 | 0.00 | — | — |
| Portfolio Long History 2026-10-08 | allrr05-xau-trend-progression-long-3ea55fd5bd70/report.htm.gz | XAUUSD H4 | 2021-10-06 → 2026-10-06 | 213 | 3.55 | 0.163 | +14.18 | 1.16 | 8.11 | 8.65 | 0.54 | 8.20 | 8.20 | 0.00 | — | — |
| Portfolio Long History All ORB05 2026-10-14 | allrr05-3-way-gold-long-b8a53e250c8f/report.htm | XAUUSD M15 | 2021-10-06 → 2026-10-06 | 773 | 12.89 | 0.593 | +105.77 | 1.33 | 10.41 | 11.44 | 1.03 | 8.89 | 9.41 | 0.52 | — | — |
| Portfolio Long History All ORB05 2026-10-14 | allrr05-3-way-gold-long-b8a53e250c8f/report.htm.gz | XAUUSD M15 | 2021-10-06 → 2026-10-06 | 773 | 12.89 | 0.593 | +105.77 | 1.33 | 10.41 | 11.44 | 1.03 | 8.89 | 9.41 | 0.52 | — | — |
| Portfolio Long History All ORB05 2026-10-14 | allrr05-3-way-gold-long-c95671d4b15c/report.htm | XAUUSD M15 | 2021-10-06 → 2026-10-06 | 773 | 12.89 | 0.593 | +105.77 | 1.33 | 10.41 | 11.44 | 1.03 | 8.89 | 9.41 | 0.52 | — | — |
| Portfolio Long History All ORB05 2026-10-14 | allrr05-3-way-gold-long-c95671d4b15c/report.htm.gz | XAUUSD M15 | 2021-10-06 → 2026-10-06 | 773 | 12.89 | 0.593 | +105.77 | 1.33 | 10.41 | 11.44 | 1.03 | 8.89 | 9.41 | 0.52 | — | — |
| Previous Green 1H Raw 2026-09-25 | pg1h-XAUUSD-B3-5y/pg1h-XAUUSD-B3-5y.htm.gz | XAUUSD H1 | 2021-09-01 → 2026-09-01 | 1617 | 26.95 | 1.240 | +32.64 | 1.02 | 34.65 | 43.86 | 9.21 | 32.50 | 41.73 | 9.23 | maximal | doc:max |
| Previous Green 1H Raw 2026-09-25 | pg1h-XAUUSD-L3-3y/pg1h-XAUUSD-L3-3y.htm.gz | XAUUSD H1 | 2023-09-01 → 2026-09-01 | 1234 | 34.27 | 1.578 | +361.39 | 1.18 | 24.79 | 31.46 | 6.67 | 24.52 | 31.24 | 6.72 | maximal | doc:max |
| Previous Green 1H Raw 2026-09-25 | pg1h-XAUUSD-B3-3y/pg1h-XAUUSD-B3-3y.htm.gz | XAUUSD H1 | 2023-09-01 → 2026-09-01 | 1109 | 30.80 | 1.418 | +72.26 | 1.06 | 35.84 | 37.88 | 2.04 | 33.59 | 36.44 | 2.85 | maximal | doc:max |
| Previous Green 1H Raw 2026-09-25 | pg1h-XAUUSD-B1-1y/pg1h-XAUUSD-B1-1y.htm.gz | XAUUSD H1 | 2025-09-01 → 2026-09-01 | 1390 | 115.91 | 5.326 | -5.70 | 0.99 | 28.19 | 30.38 | 2.19 | 27.60 | 29.73 | 2.13 | maximal | doc:max |
| QuantLab Gold Trio Pipeline 2026-09-30 | parity-B/gts-parity-B-6cbc9a4d90.htm.gz | XAUUSD M1 | 2023-07-01 → 2026-09-29 | 266 | 6.83 | 0.314 | +52.11 | 1.33 | 10.86 | 12.39 | 1.53 | 9.17 | 11.18 | 2.01 | — | web |
| QuantLab Gold Trio Pipeline 2026-09-30 | combo-prop-3-ABC-5y/gts-combo-prop-3-ABC-5y-0baec7a121.htm.gz | XAUUSD M1 | 2021-04-02 → 2026-09-29 | 708 | 10.74 | 0.494 | +96.13 | 1.29 | 10.15 | 11.52 | 1.37 | 10.01 | 10.01 | 0.00 | — | doc:rel, CLAUDE.md, web |
| QuantLab Gold Trio Pipeline 2026-09-30 | combo-prop-3-ABC-3y/gts-combo-prop-3-ABC-3y-a8eb4633cc.htm.gz | XAUUSD M1 | 2023-04-02 → 2026-09-29 | 412 | 9.83 | 0.452 | +30.19 | 1.18 | 10.19 | 11.45 | 1.26 | 10.15 | 10.15 | 0.00 | — | doc:max, web |
| QuantLab Gold Trio Pipeline 2026-09-30 | ftmo-market-variant-5y/gts-ftmo-market-variant-5y-6c80694fbc.htm.gz | XAUUSD M1 | 2021-04-02 → 2026-09-29 | 774 | 11.74 | 0.541 | +108.71 | 1.34 | 10.43 | 11.46 | 1.03 | 8.90 | 9.47 | 0.57 | — | web |
| QuantLab Gold Trio Raw 2026-09-30 | website-A+D+B-3y-m4/report-attempt0.htm.gz | XAUUSD M1 | 2023-07-01 → 2026-09-29 | 3728 | 95.68 | 4.407 | +119.28 | 1.06 | 27.20 | 43.82 | 16.62 | 43.40 | 43.40 | 0.00 | maximal | doc:rel |
| QuantLab Gold Trio Raw 2026-09-30 | video-A+B+C-3y-m4/report-attempt0.htm.gz | XAUUSD M1 | 2023-07-01 → 2026-09-29 | 733 | 18.81 | 0.866 | +94.96 | 1.16 | 23.42 | 27.37 | 3.95 | 21.40 | 22.28 | 0.88 | maximal | doc:rel, CLAUDE.md |
| QuantLab Gold Trio Raw 2026-09-30 | video-A+BQ4+C-3y-m4/report-attempt0.htm.gz | XAUUSD M1 | 2023-07-01 → 2026-09-29 | 533 | 13.68 | 0.630 | +72.67 | 1.17 | 20.66 | 23.46 | 2.80 | 19.04 | 19.04 | 0.00 | maximal | doc:rel |
| QuantLab Gold Trio Raw 2026-09-30 | B-breakout-3y-m4/report-attempt0.htm.gz | XAUUSD M1 | 2023-07-01 → 2026-09-29 | 266 | 6.83 | 0.314 | +52.11 | 1.33 | 10.86 | 12.39 | 1.53 | 9.17 | 11.18 | 2.01 | maximal | doc:rel |
| RSI MACD Raw 2026-09-28 | BTC-C_MACD_only-1y/report.htm.gz | BTCUSD M15 | 2025-05-30 → 2026-09-27 | 730 | 45.81 | 2.110 | +39.86 | 1.11 | 13.89 | 18.28 | 4.39 | 12.75 | 17.63 | 4.88 | maximal | doc:rel |
| RSI MACD Raw 2026-09-28 | XAU-D_A_without_RSI-3y/report.htm.gz | XAUUSD M15 | 2023-05-30 → 2026-09-27 | 1573 | 39.37 | 1.810 | +42.18 | 1.05 | 20.56 | 23.77 | 3.21 | 19.57 | 23.38 | 3.81 | maximal | doc:rel |
| Reel Three Bots Pipeline 2026-10-02 | raw-B-control-301/reel-raw-B-control-301-14500ffcd7.htm.gz | XAUUSD M1 | 2021-04-04 → 2026-10-02 | 352 | 5.34 | 0.245 | +45.26 | 1.13 | 30.12 | 30.12 | 0.00 | 18.60 | 28.20 | 9.60 | — | — |
| Reel Three Bots Pipeline 2026-10-02 | combo-raw-baseline-5y/reel-combo-raw-baseline-5y-8afac15ed6.htm.gz | XAUUSD M1 | 2021-04-04 → 2026-10-02 | 1679 | 25.46 | 1.171 | +118.75 | 1.11 | 28.29 | 30.99 | 2.70 | 28.10 | 30.05 | 1.95 | — | — |
| Reel Three Bots Pipeline 2026-10-02 | raw-A-3y-m1/reel-raw-A-3y-m1-f7630de15f.htm.gz | DE30 M1 | 2023-04-04 → 2026-10-02 | 699 | 16.66 | 0.766 | +42.29 | 1.14 | 12.13 | 13.28 | 1.15 | 11.78 | 12.89 | 1.11 | — | — |
| Slow Multi Asset Trend Research 2026-09-06 | Native/xauusd-selected-full-model1/xauusd-selected-full-model1.htm | XAUUSD M15 | 2023-09-01 → 2026-09-01 | 137 | 3.80 | 0.175 | +135.62 | 1.95 | 9.20 | 11.24 | 2.04 | 7.83 | 9.07 | 1.24 | — | doc:max, web |
| Slow Multi Asset Trend Research 2026-09-06 | Native/eurusd-selected-full-model1/eurusd-selected-full-model1.htm | EURUSD M15 | 2023-09-01 → 2026-09-01 | 70 | 1.94 | 0.090 | +13.59 | 1.22 | 17.12 | 18.60 | 1.48 | 12.68 | 13.36 | 0.68 | — | doc:max, web |
| Trend Progression Optimization 2026-10-05 | T5Y-e2ebbfe05247c4/report.htm | XAUUSD H4 | 2021-10-05 → 2026-10-05 | 139 | 2.32 | 0.107 | +79.39 | 1.92 | 7.43 | 9.22 | 1.79 | 8.91 | 8.91 | 0.00 | — | — |
| Trend Progression Optimization 2026-10-05 | T5Y-e2ebbfe05247c4/report.htm.gz | XAUUSD H4 | 2021-10-05 → 2026-10-05 | 139 | 2.32 | 0.107 | +79.39 | 1.92 | 7.43 | 9.22 | 1.79 | 8.91 | 8.91 | 0.00 | — | — |
| Trend Progression Optimization 2026-10-05 | D-74887f19513b0e/report.htm | XAUUSD H4 | 2021-10-05 → 2024-10-05 | 111 | 3.08 | 0.142 | +37.91 | 1.58 | 6.92 | 7.73 | 0.81 | 5.64 | 5.64 | 0.00 | — | — |
| Trend Progression Optimization 2026-10-05 | D-74887f19513b0e/report.htm.gz | XAUUSD H4 | 2021-10-05 → 2024-10-05 | 111 | 3.08 | 0.142 | +37.91 | 1.58 | 6.92 | 7.73 | 0.81 | 5.64 | 5.64 | 0.00 | — | — |
| Trend Progression Optimization 2026-10-05 | T5Y-837208ed7798b3/report.htm | XAUUSD H4 | 2021-10-05 → 2026-10-05 | 214 | 3.57 | 0.164 | +13.19 | 1.15 | 8.18 | 8.80 | 0.62 | 8.34 | 8.34 | 0.00 | — | — |
| Trend Progression Optimization 2026-10-05 | T5Y-837208ed7798b3/report.htm.gz | XAUUSD H4 | 2021-10-05 → 2026-10-05 | 214 | 3.57 | 0.164 | +13.19 | 1.15 | 8.18 | 8.80 | 0.62 | 8.34 | 8.34 | 0.00 | — | — |
| Turtle Breakout Raw 2026-10-22 | nw-BTCUSD-S55-5y/nw-BTCUSD-S55-5y.htm.gz | BTCUSD M30 | 2021-10-22 → 2026-10-22 | 2508 | 41.81 | 1.923 | -3.83 | 1.00 | 44.51 | 51.85 | 7.34 | 37.56 | 50.72 | 13.16 | maximal | doc:rel |
| Turtle Breakout Raw 2026-10-22 | nw-BTCUSD-HOLD-5y/nw-BTCUSD-HOLD-5y.htm.gz | BTCUSD M30 | 2021-10-22 → 2026-10-22 | 177 | 2.95 | 0.136 | +111.59 | 1.47 | 35.08 | 46.90 | 11.82 | 50.24 | 50.24 | 0.00 | maximal | doc:rel, CLAUDE.md |
| Turtle Breakout Raw 2026-10-22 | nw-BTCUSD-RND_DAY1-5y/nw-BTCUSD-RND_DAY1-5y.htm.gz | BTCUSD M30 | 2021-10-22 → 2026-10-22 | 1616 | 26.94 | 1.239 | +7.99 | 1.02 | 29.21 | 31.05 | 1.84 | 26.91 | 31.48 | 4.57 | maximal | doc:rel |
| Turtle Breakout Raw 2026-10-22 | native-INVALID-v3-day-quote-gap/nw-BTCUSD-RND_DAY1-5y/nw-BTCUSD-RND_DAY1-5y.htm.gz | BTCUSD M30 | 2021-10-22 → 2026-10-22 | 1415 | 23.59 | 1.085 | +9.95 | 1.02 | 29.17 | 30.84 | 1.67 | 26.91 | 30.74 | 3.83 | maximal | invalid-run |
| Turtle Breakout Raw 2026-10-22 | nw-BTCUSD-RND_HOLD3-5y/nw-BTCUSD-RND_HOLD3-5y.htm.gz | BTCUSD M30 | 2021-10-22 → 2026-10-22 | 136 | 2.27 | 0.104 | +27.11 | 1.22 | 24.82 | 27.43 | 2.61 | 23.64 | 23.64 | 0.00 | maximal | doc:rel |
| Turtle Breakout Raw 2026-10-22 | nw-BTCUSD-RND_HOLD1-5y/nw-BTCUSD-RND_HOLD1-5y.htm.gz | BTCUSD M30 | 2021-10-22 → 2026-10-22 | 131 | 2.18 | 0.100 | +57.08 | 1.46 | 29.49 | 29.49 | 0.00 | 10.78 | 11.41 | 0.63 | relative | doc:rel |
| US100 H1 ORB ADX RR1 Research 2026-09-23 | us100orb-H1-RR6-none-1y-m4-d150/us100orb-H1-RR6-none-1y-m4-d150.htm.gz | USTEC M15 | 2025-09-23 → 2026-09-23 | 72 | 6.00 | 0.276 | +23.00 | 1.67 | 6.84 | 6.84 | 0.00 | 4.87 | 5.40 | 0.53 | — | doc:rel |
| US100 H1 ORB ADX RR1 Research 2026-09-23 | us100orb-H1-RR6-production-1y-m4-d150/us100orb-H1-RR6-production-1y-m4-d150.htm.gz | USTEC M15 | 2025-09-23 → 2026-09-23 | 72 | 6.00 | 0.276 | +23.00 | 1.67 | 6.84 | 6.84 | 0.00 | 4.87 | 5.40 | 0.53 | — | doc:rel |
| US100 H1 ORB Optimization 2026-10-06 | raw-1y/report.htm | USTEC M15 | 2025-10-06 → 2026-10-06 | 77 | 6.42 | 0.295 | +20.05 | 1.53 | 6.84 | 6.84 | 0.00 | 4.87 | 5.40 | 0.53 | — | — |
| US100 H1 ORB Optimization 2026-10-06 | raw-1y/report.htm.gz | USTEC M15 | 2025-10-06 → 2026-10-06 | 77 | 6.42 | 0.295 | +20.05 | 1.53 | 6.84 | 6.84 | 0.00 | 4.87 | 5.40 | 0.53 | — | — |
| US100 H1 ORB Optimization 2026-10-06 | raw-3y/report.htm | USTEC M15 | 2023-10-06 → 2026-10-06 | 184 | 5.11 | 0.235 | +97.81 | 1.82 | 6.82 | 6.82 | 0.00 | 4.86 | 5.39 | 0.53 | — | — |
| US100 H1 ORB Optimization 2026-10-06 | raw-3y/report.htm.gz | USTEC M15 | 2023-10-06 → 2026-10-06 | 184 | 5.11 | 0.235 | +97.81 | 1.82 | 6.82 | 6.82 | 0.00 | 4.86 | 5.39 | 0.53 | — | — |
| US100 H1 ORB RR05 Comparison 2026-10-08 | Agent3010/rrcomp20261008-current-1y/report.htm | USTEC M15 | 2025-10-06 → 2026-10-06 | 77 | 6.42 | 0.295 | +20.05 | 1.53 | 6.84 | 6.84 | 0.00 | 4.87 | 5.40 | 0.53 | — | — |
| US100 H1 ORB RR05 Comparison 2026-10-08 | Agent3010/rrcomp20261008-current-1y/report.htm.gz | USTEC M15 | 2025-10-06 → 2026-10-06 | 77 | 6.42 | 0.295 | +20.05 | 1.53 | 6.84 | 6.84 | 0.00 | 4.87 | 5.40 | 0.53 | — | — |
| US100 Hourly Raw 2026-10-03 | 5y/report.htm.gz | USTEC M1 | 2021-10-02 → 2026-10-02 | 1287 | 21.45 | 0.987 | +11.87 | 1.04 | 14.24 | 15.28 | 1.04 | 13.26 | 14.40 | 1.14 | — | doc:rel |
| US100 News Reversion Pipeline 2020-2024 2026-10-08 | raw-3y/report.htm.gz | USTEC M1 | 2022-01-01 → 2025-01-01 | 73 | 2.03 | 0.093 | -8.43 | 0.84 | 16.27 | 16.79 | 0.52 | 15.73 | 15.78 | 0.05 | — | — |
| USDJPY NY Open Exit 2026-10-21 | ny0930/allrr05-usdjpy-london-open-momentum-half/report.htm | USDJPY M15 | 2021-10-06 → 2026-10-06 | 462 | 7.70 | 0.354 | +68.75 | 1.44 | 10.55 | 11.07 | 0.52 | 10.28 | 10.28 | 0.00 | — | doc:rel, CLAUDE.md |
| USDJPY NY Open Exit 2026-10-21 | ny0930/allrr05-usdjpy-london-open-momentum-half/report.htm.gz | USDJPY M15 | 2021-10-06 → 2026-10-06 | 462 | 7.70 | 0.354 | +68.75 | 1.44 | 10.55 | 11.07 | 0.52 | 10.28 | 10.28 | 0.00 | — | doc:rel, CLAUDE.md |
| XAU Slow Trend Filter Review 2026-09-29 | adx25-di-val-m1/report.htm.gz | XAUUSD H4 | 2024-09-27 → 2025-09-27 | 39 | 3.25 | 0.149 | +33.70 | 1.93 | 8.50 | 9.33 | 0.83 | 7.01 | 7.01 | 0.00 | — | doc:rel |
| XAU Slow Trend Filter Review 2026-09-29 | adx25-di-dev-m1/report.htm.gz | XAUUSD H4 | 2021-09-27 → 2024-09-27 | 117 | 3.25 | 0.149 | +28.63 | 1.25 | 17.50 | 17.50 | 0.00 | 15.40 | 16.22 | 0.82 | — | — |
| XAU Slow Trend Filter Review 2026-09-29 | adx20-di-exit24h-val-m1/report.htm.gz | XAUUSD H4 | 2024-09-27 → 2025-09-27 | 31 | 2.59 | 0.119 | +23.99 | 1.85 | 6.87 | 7.40 | 0.53 | 5.80 | 5.80 | 0.00 | — | doc:rel |
| XAU Slow Trend Weekly Review 2026-09-29 | adx-calendar-val-m1/report.htm.gz | XAUUSD H4 | 2024-09-27 → 2025-09-27 | 26 | 2.17 | 0.100 | +44.10 | 3.02 | 7.63 | 7.63 | 0.00 | 3.64 | 4.28 | 0.64 | — | — |
| XAU Slow Trend Weekly Review 2026-09-29 | calendar-val-m1/report.htm.gz | XAUUSD H4 | 2024-09-27 → 2025-09-27 | 33 | 2.75 | 0.126 | +45.53 | 2.54 | 9.11 | 9.68 | 0.57 | 6.98 | 6.98 | 0.00 | — | doc:rel |
| evidence-cache/v1 | source-runs/news-pulse-eurusd/standard/1y.htm | EURUSD M1 | 2025-09-05 → 2026-09-05 | 46 | 3.84 | 0.176 | +919.45 | 11.37 | 4.26 | 21.12 | 16.86 | 11.94 | 11.94 | 0.00 | — | web |
| evidence-cache/v1 | source-runs/news-pulse-xag/standard/5y.htm | XAGUSD M1 | 2021-09-05 → 2026-09-05 | 139 | 2.32 | 0.107 | +5340.19 | 8.92 | 8.78 | 17.97 | 9.19 | 4.15 | 18.17 | 14.02 | — | web |
| evidence-cache/v1 | source-runs/news-pulse-eurusd/standard/5y.htm | EURUSD M1 | 2021-09-05 → 2026-09-05 | 240 | 4.00 | 0.184 | +38947.79 | 9.02 | 3.33 | 16.52 | 13.19 | 1.14 | 5.18 | 4.04 | — | web |
| evidence-cache/v1 | source-runs/nasdaq-5m-candle-momentum/standard/5y.htm | USTEC M5 | 2021-09-07 → 2026-09-07 | 1272 | 21.20 | 0.975 | +105.74 | 1.12 | 12.63 | 24.93 | 12.30 | 11.50 | 24.15 | 12.65 | — | web |
| evidence-cache/v1 | source-runs/news-pulse-btc/standard/3y.htm | BTCUSD M1 | 2023-09-05 → 2026-09-05 | 147 | 4.08 | 0.188 | +24256.27 | 11.84 | 20.07 | 32.35 | 12.28 | 14.02 | 25.38 | 11.36 | — | web |
| evidence-cache/v1 | source-runs/news-pulse-btc/standard/5y.htm | BTCUSD M1 | 2021-09-05 → 2026-09-05 | 242 | 4.03 | 0.185 | +43775.44 | 8.54 | 13.32 | 25.13 | 11.81 | 10.01 | 20.66 | 10.65 | — | web |
| evidence-cache/v1 | source-runs/nasdaq-5m-candle-momentum/dynamic/3y.htm | USTEC M5 | 2023-09-25 → 2026-09-25 | 536 | 14.89 | 0.684 | +162.16 | 1.40 | 10.06 | 21.44 | 11.38 | 8.94 | 20.25 | 11.31 | — | web |
| evidence-cache/v1 | source-runs/xau-slow-trend/standard/5y.htm | XAUUSD H4 | 2021-09-05 → 2026-09-05 | 245 | 4.08 | 0.188 | +86.18 | 1.42 | 12.63 | 22.04 | 9.41 | 11.07 | 21.68 | 10.61 | — | web |
| evidence-cache/v1 | source-runs/news-pulse-eurusd/standard/3y.htm | EURUSD M1 | 2023-09-05 → 2026-09-05 | 147 | 4.08 | 0.188 | +21300.13 | 8.78 | 9.39 | 18.36 | 8.97 | 2.46 | 3.93 | 1.47 | — | web |
| evidence-cache/v1 | source-runs/nasdaq-5m-candle-momentum/standard/3y.htm | USTEC M5 | 2023-09-07 → 2026-09-07 | 762 | 21.16 | 0.974 | +111.87 | 1.18 | 12.63 | 20.62 | 7.99 | 11.49 | 19.64 | 8.15 | — | web |
| evidence-cache/v1 | source-runs/news-pulse-xag/standard/3y.htm | XAGUSD M1 | 2023-09-05 → 2026-09-05 | 90 | 2.50 | 0.115 | +3719.67 | 9.47 | 8.78 | 11.54 | 2.76 | 4.15 | 11.46 | 7.31 | — | CLAUDE.md, web |
| evidence-cache/v1 | source-runs/news-pulse-xag/standard/1y.htm | XAGUSD M1 | 2025-09-05 → 2026-09-05 | 34 | 2.84 | 0.130 | +2079.63 | 10.87 | 8.77 | 11.42 | 2.65 | 4.15 | 11.44 | 7.29 | — | web |
| evidence-cache/v1 | source-runs/xau-regime-switch/standard/5y.htm | XAUUSD M5 | 2021-09-01 → 2026-09-01 | 211 | 3.52 | 0.162 | +96.19 | 1.59 | 10.21 | 15.39 | 5.18 | 7.22 | 12.98 | 5.76 | — | web |
| evidence-cache/v1 | source-runs/xau-weakness/standard/3y.htm | XAUUSD M30 | 2023-09-05 → 2026-09-05 | 391 | 10.86 | 0.499 | +228.23 | 1.58 | 13.65 | 17.85 | 4.20 | 11.63 | 16.83 | 5.20 | — | web |
| evidence-cache/v1 | source-runs/xau-weakness/safe/3y.htm | XAUUSD M30 | 2023-09-05 → 2026-09-05 | 181 | 5.03 | 0.231 | +127.19 | 1.88 | 6.82 | 11.49 | 4.67 | 5.84 | 10.84 | 5.00 | — | web |
| evidence-cache/v1 | source-runs/news-pulse-xag/standard/6m.htm | XAGUSD M1 | 2026-03-05 → 2026-09-05 | 18 | 2.98 | 0.136 | +400.72 | 10.85 | 8.79 | 8.79 | 0.00 | 4.16 | 8.81 | 4.65 | — | web |
| evidence-cache/v1 | source-runs/news-pulse-btc/standard/1y.htm | BTCUSD M1 | 2025-09-05 → 2026-09-05 | 52 | 4.34 | 0.199 | +6344.62 | 9.39 | 7.72 | 12.21 | 4.49 | 5.00 | 5.00 | 0.00 | — | web |
| evidence-cache/v1 | source-runs/btc-poc-fibonacci/standard/5y.htm | BTCUSD M15 | 2021-09-05 → 2026-09-05 | 114 | 1.90 | 0.087 | +44.30 | 1.47 | 14.10 | 14.10 | 0.00 | 8.70 | 11.50 | 2.80 | — | web |
| evidence-cache/v1 | source-runs/xau-regime-switch/standard/3y.htm | XAUUSD M5 | 2023-09-01 → 2026-09-01 | 117 | 3.25 | 0.150 | +88.30 | 1.93 | 10.39 | 12.33 | 1.94 | 7.48 | 9.80 | 2.32 | — | web |
| evidence-cache/v1 | source-runs/us100-hourly-profiles/standard/1y.htm.gz | USTEC M1 | 2025-10-03 → 2026-10-03 | 1171 | 97.65 | 4.487 | +62.05 | 1.30 | 8.29 | 8.29 | 0.00 | 4.49 | 6.80 | 2.31 | — | web |
| evidence-cache/v1 | source-runs/news-pulse-xau/standard/1y.htm | XAUUSD M1 | 2025-09-05 → 2026-09-05 | 40 | 3.34 | 0.153 | +300.00 | 13.12 | 4.50 | 6.68 | 2.18 | 5.28 | 5.28 | 0.00 | — | web |
| evidence-cache/v1 | source-runs/news-pulse-xau/standard/6m.htm | XAUUSD M1 | 2026-03-05 → 2026-09-05 | 22 | 3.64 | 0.167 | +167.04 | 14.53 | 4.53 | 6.67 | 2.14 | 5.27 | 5.27 | 0.00 | — | web |
| evidence-cache/v1 | source-runs/news-pulse-xau/standard/3y.htm | XAUUSD M1 | 2023-09-05 → 2026-09-05 | 121 | 3.36 | 0.154 | +1029.12 | 10.69 | 4.49 | 6.61 | 2.12 | 5.22 | 5.22 | 0.00 | — | web |
| evidence-cache/v1 | source-runs/news-pulse-xau/standard/5y.htm | XAUUSD M1 | 2021-09-05 → 2026-09-05 | 194 | 3.23 | 0.149 | +2394.29 | 10.22 | 4.49 | 6.60 | 2.11 | 5.21 | 5.21 | 0.00 | — | web |
| evidence-cache/v1 | source-runs/asia-breakout/standard/5y.htm | XAUUSD H1 | 2021-10-02 → 2026-10-02 | 189 | 3.15 | 0.145 | +46.33 | 1.33 | 8.29 | 9.25 | 0.96 | 6.62 | 8.41 | 1.79 | — | web |
| evidence-cache/v1 | source-runs/sell-nasdaq-15min/dynamic/3y.htm | USTEC M15 | 2023-09-07 → 2026-09-07 | 159 | 4.42 | 0.203 | +94.91 | 1.78 | 7.82 | 8.89 | 1.07 | 5.87 | 7.55 | 1.68 | — | web |
| evidence-cache/v1 | source-runs/xau-elliott-wave-1-2-3/standard/5y.htm | XAUUSD H4 | 2021-09-05 → 2026-09-05 | 116 | 1.93 | 0.089 | +72.30 | 1.88 | 10.59 | 10.59 | 0.00 | 6.47 | 8.15 | 1.68 | — | web |
| evidence-cache/v1 | source-runs/news-pulse-eurusd/standard/6m.htm | EURUSD M1 | 2026-03-05 → 2026-09-05 | 24 | 3.97 | 0.182 | +394.50 | 15.47 | 4.26 | 5.86 | 1.60 | 5.27 | 5.27 | 0.00 | — | web |
| evidence-cache/v1 | source-runs/lta-volume-profile/safe/5y.htm | XAUUSD M15 | 2021-09-05 → 2026-09-05 | 609 | 10.15 | 0.467 | +128.30 | 1.23 | 20.52 | 22.09 | 1.57 | 19.20 | 20.65 | 1.45 | — | web |
| evidence-cache/v1 | source-runs/asia-breakout/safe/5y.htm | XAUUSD H1 | 2021-09-05 → 2026-09-05 | 187 | 3.12 | 0.143 | +45.50 | 1.40 | 6.27 | 7.76 | 1.49 | 7.43 | 7.43 | 0.00 | — | web |
| evidence-cache/v1 | source-runs/news-pulse-btc/standard/6m.htm | BTCUSD M1 | 2026-03-05 → 2026-09-05 | 29 | 4.80 | 0.220 | +303.43 | 7.99 | 8.74 | 9.97 | 1.23 | 4.05 | 5.00 | 0.95 | — | web |
| evidence-cache/v1 | source-runs/xau-weakness/safe/1y.htm | XAUUSD M30 | 2025-09-05 → 2026-09-05 | 85 | 7.09 | 0.326 | +56.93 | 1.97 | 5.76 | 6.90 | 1.14 | 4.33 | 4.69 | 0.36 | — | web |
| evidence-cache/v1 | source-runs/lta-volume-profile/safe/6m.htm | XAUUSD M15 | 2026-03-05 → 2026-09-05 | 107 | 17.70 | 0.811 | +29.70 | 1.38 | 7.77 | 8.86 | 1.09 | 7.40 | 7.40 | 0.00 | — | web |
| evidence-cache/v1 | source-runs/xau-trend-progression/standard/5y.htm | XAUUSD H4 | 2021-10-02 → 2026-10-02 | 214 | 3.57 | 0.164 | +13.19 | 1.15 | 8.18 | 8.80 | 0.62 | 8.34 | 8.34 | 0.00 | — | web |
| evidence-cache/v1 | source-runs/us100-month-end-flow/standard/5y.htm | USTEC M30 | 2021-08-31 → 2026-08-31 | 175 | 2.92 | 0.134 | +37.84 | 1.37 | 9.13 | 9.68 | 0.55 | 7.79 | 7.79 | 0.00 | — | web |
| evidence-cache/v1 | source-runs/orb-volume-profile/standard/5y.htm | XAUUSD M5 | 2021-09-05 → 2026-09-05 | 304 | 5.07 | 0.233 | +59.19 | 1.43 | 6.14 | 6.68 | 0.54 | 5.34 | 5.71 | 0.37 | — | web |
| evidence-jobs/btc-poc-fibonacci | latest.htm | BTCUSD M15 | 2016-09-05 → 2026-09-05 | 145 | 1.21 | 0.056 | +58.43 | 1.45 | 14.17 | 14.17 | 0.00 | 8.74 | 11.56 | 2.82 | — | web |
| evidence-jobs/us100-orb-new-york-m30 | latest.htm | ENQc1 M30 | 2023-09-09 → 2026-09-08 | 43 | 1.20 | 0.055 | +51.60 | 2.60 | 5.51 | 6.30 | 0.79 | 4.50 | 5.66 | 1.16 | — | web |
| evidence-jobs/xau-trend-progression | latest.htm | GCEc1 H4 | 2024-02-28 → 2026-09-08 | 53 | 1.75 | 0.080 | +122.87 | 2.50 | 11.12 | 11.12 | 0.00 | 5.45 | 9.50 | 4.05 | — | web |
| evidence-jobs/xau-weakness | latest.htm | GCEc1 M30 | 2024-02-28 → 2026-09-08 | 150 | 4.95 | 0.228 | +120.65 | 1.61 | 15.23 | 17.31 | 2.08 | 14.07 | 15.60 | 1.53 | — | web |
