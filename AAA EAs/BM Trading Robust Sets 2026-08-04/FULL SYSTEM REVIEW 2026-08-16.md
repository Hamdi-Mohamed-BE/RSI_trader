# BM Trading EA System — Full Review

Review date: 2026-08-16 (Asia/Shanghai)  
Reviewed deployment root: `C:\Users\hama101\Desktop\geek\ai trader\AAA EAs\BM Trading Robust Sets 2026-08-04`  
No BAT, EA, preset, chart profile, order, or open position was changed during this review.

## 1. Executive verdict

The system is **not ready to be treated as a live 26-EA portfolio**.

There are three different states that must not be confused:

1. **Current BAT source:** defines 26 EAs and all 26 symbols resolve on the connected Exness account.
2. **Persisted MT5 profile:** contains only 13 older chart files, not the 26-EA source roster.
3. **Operationally confirmed EAs:** zero. Ten of the 13 persisted charts have no `<expert>` attachment. The three remaining vendor EAs repeatedly call `ExpertRemove()` after licence/web-request failures. Therefore no EA can currently be confirmed as running and managing trades.

The current BAT also has no portfolio risk governor. At the default settings, every one of the 26 charts is allowed roughly 1% risk. On the current USD 11,658.96 balance, the theoretical planned risk is approximately **USD 3,031.33, or 26%**, if one trade from every chart is open at once. Gaps and news slippage can make the actual loss larger.

The old 12-valid-EA portfolio produced an attractive latest-year arithmetic overlay, but its five-year merged curve crossed below zero. The five-year portfolio therefore **failed by ruin**, even though it later recovered arithmetically in the report.

The correct next step is to repair deployment verification and reduce the roster/risk. It is not safe to run the current 26-EA BAT unchanged.

## 2. What is actually on now

### Connected account snapshot

| Item | Current value |
|---|---:|
| Account | 472334559 |
| Broker/server | Exness / Exness-MT5Trial16 |
| Mode | Demo, hedging |
| Balance | USD 11,658.96 |
| Equity | USD 11,580.52 |
| Open P/L | -USD 78.44 |
| Expert trading permission | Enabled |
| Open positions | 5 |
| Pending orders | 1 |

Snapshot was read from the running terminal. Trading permission being enabled does not prove that any EA is attached or operational.

### Current persisted profile

Profile: `BM Trading ANY BALANCE - AUTO`

| Chart | Symbol / TF in file | Expert block |
|---:|---|---|
| 1 | XAUUSD / M15 | None |
| 2 | XAUUSD / M5 | None |
| 3 | XAUUSD / H1 | None |
| 4 | XAUUSD / H1 | None |
| 5 | XAUUSD / H1 | None |
| 6 | US30 / H1 in persisted file | Go Long EA |
| 7 | XAUUSD / H1 in persisted file | None |
| 8 | XAUUSD / M15 | None |
| 9 | EURUSD / M5 | Ninja Turtle Scalper EA |
| 10 | UT100 / M1 | None |
| 11 | UT100 / H1 in persisted file | Turnaround Tuesday EA |
| 12 | UT100 / M15 | None |
| 13 | XAUUSD / M1 | None |

The three vendor experts are not operational:

- Go Long: Exness licence check reached the vendor but WebRequest failed with code 4014; it requested `bmtrading.de` be added to allowed URLs, then called `ExpertRemove()`.
- Ninja Turtle: same WebRequest/licence failure and `ExpertRemove()`. It is no longer in the current BAT source, but remains in the stale persisted profile.
- Turnaround Tuesday: same licence failure and `ExpertRemove()`; it also logged an inability to load Moving Average on UT100, error 4801.

### Stale deployment record

`_Auto Deploy\LAST INSTALL.txt` is dated 2026-08-09 and describes a 13-chart installation on account 90490218 at MEXAtlantic-Demo with a USD 4,272.72 balance. It is not a record of the current 26-EA source roster or the current Exness account.

The 26-EA installer source was modified after the 13-chart profile was created. The source roster has therefore not been installed as a complete portfolio.

### Open trades that may no longer be managed by their EAs

| Origin | Symbol | Side / lot | Open P/L | Broker SL / TP | Management concern |
|---|---|---:|---:|---|---|
| Asia Breakout | XAUUSD | Buy 0.03 | +USD 20.62 | SL and TP present | Dynamic EA management is not confirmed |
| EMA3 | XAUUSD | Buy 0.01 | -USD 15.97 | SL and TP present | Dynamic EA management is not confirmed |
| Nasdaq Overnight | USTEC | Buy 0.19 | +USD 0.02 | SL present; TP is zero | Timed overnight close may not occur if EA is detached |
| Trade PH VIP, external | EURCAD | Buy 0.22 | -USD 41.86 | SL and TP present | Not part of this BAT |
| Trade PH VIP, external | GBPJPY | Sell 0.31 | -USD 41.25 | SL and TP present | Not part of this BAT |

There is also one external Trade PH VIP US30 sell-stop order. Existing broker-side stops remain active, but trailing, time exits, break-even logic, pending-order cancellation, and other EA-side actions require a functioning EA.

## 3. Current BAT source roster

All rows below are defined by `_Auto Deploy\Install-BMTradingPortfolio.ps1`. They are the roster the BAT will attempt to install the next time it is run; they are not the presently confirmed live roster.

| # | EA | Canonical symbol / chart | Risk in AUTO | Evidence status |
|---:|---|---|---:|---|
| 1 | LTA Volume Profile | XAUUSD M15 | Fixed 1% | Five-year weak/unsafe DD |
| 2 | ORB Volume Profile | XAUUSD M5 | Fixed 1% | Core multi-year candidate |
| 3 | ATR Candle Breakout | XAUUSD H1 | Adaptive, default 1% | Candidate only at reduced risk |
| 4 | AAA Final Asia Breakout | XAUUSD H1 | Adaptive, default 1% | Five-year near break-even |
| 5 | AAA Final DmC | XAUUSD H1 | Adaptive, default 1% | Five-year loss |
| 6 | Go Long | US30 D1 | Adaptive-sized fixed lot | Five-year flat; vendor licence issue |
| 7 | AAA Final EMA3 | XAUUSD H4 | Adaptive, default 1% | Core multi-year candidate |
| 8 | AAA Final XAU Weakness | XAUUSD M15 | Adaptive, default 1% | Five-year loss |
| 9 | Nasdaq Overnight | USTEC M1 | Adaptive, default 1% | Low-return diversifier candidate |
| 10 | Turnaround Tuesday | USTEC D1 | Adaptive-sized fixed lot | Five-year loss; vendor issue |
| 11 | AAA Final US100 Weakness | USTEC M15 | Adaptive, default 1% | Five-year loss |
| 12 | Auction Market XAU | XAUUSD D1 | Fixed 1% | Research-only, 25 trades |
| 13 | Auction Market XAG | XAGUSD H4 | Fixed 1% | Best auction candidate; still research |
| 14 | Auction Market US30 | US30 H4 | Fixed 1% | Research/demo candidate |
| 15 | Auction Market US100 | USTEC H4 | Fixed 1% | Failed locked 2026 |
| 16 | Auction Market BTC | BTCUSD H4 | Fixed 1% | Research/demo candidate |
| 17 | Auction Market ETH | ETHUSD H4 | Fixed 1% | Research/demo candidate |
| 18 | Auction Stock SP500 | US500 H4 | Fixed 1% | Experimental; failed final gate |
| 19 | Auction Stock NVDA | NVDA D1 | Fixed 1% | Experimental; tiny confirmation sample |
| 20 | Auction Stock MSFT | MSFT H4 | Fixed 1% | Experimental; failed 2026 confirmation |
| 21 | Auction Stock AMZN | AMZN D1 | Fixed 1% | Experimental; failed 2026 confirmation |
| 22 | Auction Stock GOOGL | GOOGL H4 | Fixed 1% | Experimental; one 2026 loss |
| 23 | Auction Stock META | META H4 | Fixed 1% | Best stock watch candidate; only 3 confirmation trades |
| 24 | Auction Stock AVGO | AVGO H4 | Fixed 1% | Watch candidate; only 3 confirmation trades |
| 25 | Auction Stock INTC | INTC D1 | Fixed 1% | Watch candidate; only 3 confirmation trades |
| 26 | News Pulse, NFP/CPI/FOMC, long only | XAUUSD M1 | Fixed 1% | Backtest/live mismatch and news gap risk |

Ninja Turtle is absent from the source roster. Its appearance in the chart profile is stale.

## 4. Risk architecture audit

### Maximum planned risk at the current balance

One percent of USD 11,658.96 is USD 116.59.

| Risk bucket | Charts | Planned risk | Current-account amount |
|---|---:|---:|---:|
| Legacy/core entries excluding News Pulse | 11 | 11% | USD 1,282.49 |
| Six auction-market instruments | 6 | 6% | USD 699.54 |
| Eight auction stock/index instruments | 8 | 8% | USD 932.72 |
| News Pulse | 1 | 1% | USD 116.59 |
| **Total** | **26** | **26%** | **USD 3,031.33** |

### Concentration by underlying theme

| Exposure cluster | EAs | Maximum nominal risk |
|---|---:|---:|
| XAU | 9 | 9% |
| US100/Nasdaq | 4 | 4% |
| US30/Dow | 2 | 2% |
| XAG | 1 | 1% |
| BTC | 1 | 1% |
| ETH | 1 | 1% |
| US500 | 1 | 1% |
| Individual US technology stocks | 7 | 7% |

This is not genuine diversification. XAU bots can trigger in the same volatility regime, and the US100, US500, and technology-stock bots share a strong equity/technology risk factor.

### Important AUTO limitation

The `-AdaptiveRiskPercent` option controls only nine entries. LTA, ORB, News Pulse, and all fourteen Auction Market charts remain fixed at 1%. Therefore lowering adaptive risk to 0.25% would still leave 17% fixed risk plus 2.25% adaptive risk, or **19.25% total nominal risk**.

The BAT does not optimize strategy parameters. It resolves broker symbols, copies already-selected `.set` files, and adjusts some risk inputs/lots. “AUTO BALANCE” means sizing, not automatic backtest optimization.

### Missing controls

- No portfolio-level maximum open risk.
- No XAU/equity-index correlation bucket limit.
- No daily, weekly, or monthly realized loss lock.
- No account-equity drawdown kill switch.
- No central rule preventing several EAs from opening the same-direction XAU trade.
- No robust runtime heartbeat proving every chart still has a functioning EA.
- Installer checks chart-file `<expert>` tags after launch, but that does not prove successful initialization or ongoing operation.

## 5. Core BAT backtests

Both tables used USD 10,000 initial balance per independent EA, roughly 1% risk per EA trade, Exness history, and MT5 every-tick modelling with random delay. The combined overlays are arithmetic cash-flow merges, not native shared-equity multi-EA tests.

### One-year versus five-year results

| EA | Latest 1Y: return / DD / PF / trades | 5Y: return / DD / PF / trades | Live closed result since Aug 9 | Review |
|---|---|---|---:|---|
| LTA Volume Profile | +86.65% / 14.36% / 1.39 / 244 | +26.19% / 42.84% / 1.04 / 1,160 | +USD 121.80, 3 trades | Disable at 1%; recent regime dependence |
| ORB Volume Profile | +9.70% / 6.29% / 1.67 / 49 | +57.07% / 6.31% / 1.41 / 301 | +USD 144.18, 2 trades | Best core robustness candidate |
| ATR Candle Breakout | +30.39% / 8.72% / 1.39 / 119 | +72.04% / 23.66% / 1.14 / 670 | No closed trade | Candidate only at reduced risk |
| Asia Breakout | +20.10% / 12.67% / 1.25 / 120 | +7.91% / 35.03% / 1.02 / 660 | -USD 91.14, 1 trade | Disable |
| DmC | +26.48% / 9.78% / 1.20 / 235 | -16.52% / 37.08% / 0.93 / 572 | +USD 38.51, 4 trades | Disable; five-year failure |
| Go Long | +16.96% / 8.24% / 1.20 / 312 | +0.74% / 34.38% / 1.00 / 1,555 | No closed trade | Disable; no edge plus licence issue |
| EMA3 | +16.94% / 2.85% / 2.30 / 39 | +32.10% / 8.70% / 1.36 / 187 | -USD 75.48, 1 trade | Core candidate, preferably 0.5% risk |
| XAU Weakness | +11.49% / 17.70% / 1.06 / 279 | -28.90% / 58.49% / 0.96 / 1,486 | +USD 165.19, 6 trades | Disable; live gain does not repair 5Y failure |
| Nasdaq Overnight | +7.76% / 2.39% / 1.81 / 72 | +7.84% / 4.82% / 1.28 / 189 | +USD 81.88, 2 trades | Low-return diversifier candidate |
| Turnaround Tuesday | +3.29% / 6.11% / 1.20 / 30 | -4.36% / 15.59% / 0.93 / 148 | No closed trade | Disable; licence issue and 5Y loss |
| US100 Weakness | +3.34% / 6.03% / 1.16 / 70 | -21.10% / 26.83% / 0.81 / 370 | +USD 94.14, 1 trade | Disable; one live win is not validation |
| News Pulse long only | +62.51% / 1.46% / 41.00 / 19 | Same 19 trades reported in 5Y run | -USD 244.91, 1 trade | Demo only at much lower risk or disable |

News Pulse's current preset is long-only; watches NFP, CPI, and FOMC; places 30 seconds before the event; uses a USD 6 entry offset, USD 6 stop, 1% equity risk, and force-closes 60 seconds after the event. The identical 19-trade one-year and five-year result does not establish genuine five-year event coverage. Its first observed live closed result lost USD 244.91, about 2.1% of the current balance, demonstrating that news gaps/slippage can exceed nominal 1% risk.

### Portfolio-level core result

| Period | Apparent final / return | Realized-balance DD | PF | Trades | Honest verdict |
|---|---:|---:|---:|---:|---|
| 2025-08-11 to 2026-08-10 | USD 39,561.18 / +295.61% | 25.34% | 1.34 | 1,588 | Positive recent overlay, but not a native shared-equity test |
| 2021-08-11 to 2026-08-10 | USD 29,552.64* / +195.53%* | 154.57% | 1.06 | 7,317 | **FAIL: curve reached -USD 6,151.72; real account would have been ruined** |

The starred five-year final balance is a later arithmetic recovery after the model balance had already gone below zero. It is not an achievable live result.

## 6. Live system performance since the recorded Aug 9 install time

Closed positions were grouped by EA magic number on the connected Exness account.

| EA | Closed trades | Wins / losses | Win rate | Net | PF |
|---|---:|---:|---:|---:|---:|
| XAU Weakness | 6 | 3 / 3 | 50.00% | +USD 165.19 | 1.53 |
| ORB Volume Profile | 2 | 1 / 1 | 50.00% | +USD 144.18 | 2.35 |
| LTA Volume Profile | 3 | 1 / 2 | 33.33% | +USD 121.80 | 1.58 |
| US100 Weakness | 1 | 1 / 0 | 100.00% | +USD 94.14 | No loss yet |
| Nasdaq Overnight | 2 | 2 / 0 | 100.00% | +USD 81.88 | No loss yet |
| DmC | 4 | 2 / 2 | 50.00% | +USD 38.51 | 1.19 |
| EMA3 | 1 | 0 / 1 | 0.00% | -USD 75.48 | 0.00 |
| Asia Breakout | 1 | 0 / 1 | 0.00% | -USD 91.14 | 0.00 |
| News Pulse | 1 | 0 / 1 | 0.00% | -USD 244.91 | 0.00 |
| **Known BAT EAs total** | **21** | **10 / 11** | **47.62%** | **+USD 234.17** | **1.19** |

The three still-open known-BAT positions add +USD 4.67 marked P/L, making the currently observed known-system total approximately +USD 238.84. This is a very small sample, includes periods before the current profile became detached/stale, and cannot validate the 26-EA source portfolio.

External Trade PH VIP and manual/unknown trades were excluded from the BAT total.

## 7. Auction-market EAs already defined in the BAT

These were research-engine tests from January 2022 to August 2026 at 1% compounded risk. Recorded spread plus modeled slippage was included. They used broker tick activity, not centralized exchange volume. None passed the original 15% CAGR deployment gate.

| Market | TF | Trades | Win rate | PF | Total return | CAGR | Max DD | Locked 2026 | Review |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| XAU | D1 | 25 | 56.00% | 3.78 | +24.67% | 4.92% | 3.57% | -0.00%, 1 trade | Too few trades; no confirmation |
| XAG | H4 | 78 | 28.21% | 2.74 | +85.20% | 14.33% | 9.25% | +1.66%, PF 1.36, 9 trades | Best auction candidate; demo/reduced risk |
| US30 | H4 | 30 | 23.33% | 2.59 | +38.36% | 7.32% | 8.42% | +2.53%, PF 1.56, 6 trades | Research/demo only |
| US100 | H4 | 43 | 23.26% | 2.23 | +44.45% | 8.33% | 14.75% | -10.89%, PF 0.19, 15 trades | Disable |
| BTC | H4 | 66 | 28.79% | 1.81 | +42.87% | 8.07% | 13.12% | +2.40%, PF 1.27, 13 trades | Research/demo only |
| ETH | H4 | 68 | 23.53% | 2.09 | +65.40% | 11.55% | 14.70% | +19.04%, PF 7.10, 6 trades | Promising but tiny confirmation sample |

The video's discretionary macro, intermarket, COT, and VIX layers were not mechanically encoded. These EAs validate only the technical auction/value-area layer.

## 8. Stock/index Auction EAs already defined in the BAT

These tests used Exness M1 history from January 2022 to August 2026, long-only entries, 1% compounded risk, and modeled spread, slippage, commission, and financing. All eight BAT entries have full-period PF above 2 because that was the user's inclusion rule, but every one still failed the research team's final deployment gate.

| Instrument | Trades | Win rate | PF after modeled costs | Net return | CAGR | Max DD | Locked 2026 | Review |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| SP500 / US500 | 38 | 50.00% | 2.02 | +22.83% | 4.56% | 5.38% | -3.26%, 3 trades | Disable |
| NVDA | 31 | 41.94% | 2.52 | +23.92% | 4.76% | 4.71% | +2.97%, 2 trades | Watch only |
| MSFT | 16 | 56.25% | 3.50 | +19.89% | 4.01% | 2.47% | -1.04%, 1 trade | Disable |
| AMZN | 23 | 56.52% | 3.22 | +23.90% | 4.76% | 2.87% | -1.02%, 1 trade | Disable |
| GOOGL | 20 | 50.00% | 4.84 | +46.17% | 8.59% | 4.90% | -1.02%, 1 trade | Watch only; insufficient confirmation |
| META | 35 | 51.43% | 2.82 | +38.58% | 7.33% | 5.13% | +4.95%, PF 5.88, 3 trades | Best stock watch candidate |
| AVGO | 24 | 25.00% | 2.51 | +16.38% | 3.35% | 7.70% | +2.10%, PF 3.00, 3 trades | Watch only |
| INTC | 24 | 54.17% | 4.73 | +28.81% | 5.64% | 5.42% | +1.99%, PF 2.97, 3 trades | Watch only |

The eight charts add 8% nominal risk to one correlated US-equity factor. Their sample sizes are 16–38 trades over more than four years, and the locked confirmation samples are only 1–3 trades. Full-period PF alone is not enough to justify live deployment.

## 9. Proposed XAU trend additions

The two recently reviewed trend variants are **not in the BAT and are not yet MT5-native validated EAs**. They are research-engine results on MEXAtlantic M1 bid data with spread and modeled slippage, but without explicit commission/swap.

| Variant | Full period | Full return | Max DD | PF | Win rate | Trades | Locked last year | Last-year DD / PF / trades |
|---|---|---:|---:|---:|---:|---:|---:|---|
| XAU trend baseline | 2021-08-10 to 2026-08-07 | +45.35% | 9.54% | 1.52 | 36.97% | 119 | +16.92% | 7.77% / 1.92 / 27 |
| XAU trend fast-alpha | 2021-08-10 to 2026-08-07 | +52.89% | 9.86% | 1.66 | 38.79% | 116 | +28.58% | 5.46% / 2.87 / 26 |

Running both at 0.5% + 0.5% produced:

| Metric | Full period | Locked last year |
|---|---:|---:|
| Return | +49.12% | +22.75% |
| PF | 1.59 | 2.35 |
| Closed-trade max DD | 6.98% | 4.80% |
| Conservative marked-DD planning | 10–12% | 7–9% |
| Trades | 235 | 53 |

The variants have 0.90 monthly-return correlation and 85.7% entry overlap. They are two executions of the same XAU idea, not diversification. The fast-alpha version alone is the better candidate. It should be implemented and tested on Exness real ticks before any BAT inclusion; if it passes, 0.5% risk is a sensible first deployment level.

## 10. Source-code and maintainability review

Source `.mq5` and compiled `.ex5` files are available for LTA, ORB, Asia Breakout, DmC, EMA3, XAU Weakness, Nasdaq Overnight, US100 Weakness, News Pulse, and Auction Market. Auction Market's one codebase is reused across fourteen chart presets.

Source code is not available in the reviewed folders for ATR Candle Breakout, Go Long, or Turnaround Tuesday. Go Long and Turnaround Tuesday are vendor-licensed EX5 files and currently fail runtime licence/web checks. ATR is also EX5-only, so its internal logic and risk handling cannot be fully audited or repaired locally.

The installer has useful protections—account probing, symbol aliases, safe profile backup, set copying, and a post-launch chart-file check—but lacks an operational heartbeat. A robust deployment system should require each EA to publish a running status, last tick time, last signal time, magic number, and initialization error. The installer should fail if an EA self-removes or remains silent.

## 11. Recommended system state

### Production-candidate core, after deployment is repaired

| EA | Suggested starting risk | Reason |
|---|---:|---|
| ORB Volume Profile | 0.50% | Best combination of five-year PF, DD, and sample size |
| EMA3 | 0.50% | Good five-year PF and low DD; smaller sample |
| Nasdaq Overnight | 0.50% | Low return but low DD and different holding logic |
| ATR Candle Breakout | 0.20–0.25% | Positive five-year return but 23.66% DD and PF only 1.14 at 1% risk |

This starts around 1.70–1.75% planned concurrent risk, with 1.20–1.25% concentrated in XAU. Portfolio results must still be retested natively with shared equity.

### Research/demo-only watch list

- Auction XAG: 0.25%.
- Auction US30: 0.25%.
- Auction BTC: 0.25%.
- Auction ETH: 0.25%.
- META, AVGO, and INTC Auction stocks: 0.10–0.25% each only if specifically forward-tested.
- News Pulse: at most 0.10–0.25% on demo because the observed gap loss exceeded nominal risk.
- XAU trend fast-alpha: 0.50% only after MQL5/Exness real-tick validation.

### Disable from the production BAT now

- LTA at its current 1% risk.
- Asia Breakout.
- DmC.
- Go Long.
- XAU Weakness.
- Turnaround Tuesday.
- US100 Weakness.
- Auction US100.
- Auction XAU until a meaningful confirmation sample exists.
- SP500, NVDA, MSFT, AMZN, GOOGL stock variants for production; they may remain outside the BAT as research candidates.
- Ninja Turtle stale chart entry.

## 12. Required engineering fixes before the next install

1. Add a per-EA `Enabled` and per-EA risk value so all 26 entries can be scaled; remove the 17 hard-coded 1% exceptions.
2. Add a portfolio open-risk cap. Recommended initial cap: 2–3% total.
3. Add cluster caps: XAU/XAG, US equity indices/stocks, and crypto.
4. Add account-equity controls: daily loss, weekly loss, and hard peak-equity drawdown lock.
5. Add a runtime heartbeat and fail installation when an EA self-removes or fails initialization.
6. Reconcile or remove detached open positions before replacing the profile, especially the Nasdaq Overnight position with no TP.
7. Remove vendor EAs until licence/WebRequest requirements are working and verifiable.
8. Generate a fresh install manifest from the Exness account after a successful install.
9. Run one native shared-account forward test. Do not add standalone EA returns together as a profit forecast.
10. Keep production, demo-experimental, and research presets in separate BAT/profile files.

## 13. Bottom line

- **Configured in source:** 26 EAs.
- **Persisted older charts:** 13.
- **Confirmed operational EAs:** 0.
- **Known BAT live result since Aug 9:** +USD 234.17 closed, PF 1.19, 21 trades; +USD 238.84 including current open P/L.
- **Old core latest-year overlay:** +295.61%, 25.34% realized DD, PF 1.34.
- **Old core five-year overlay:** ruined the account; 154.57% realized DD and balance below zero.
- **Current theoretical planned risk:** 26% before slippage/gaps.
- **Most defensible current core candidates:** ORB, EMA3, Nasdaq Overnight, and ATR at reduced risk.
- **Best new research candidate:** XAU trend fast-alpha, but only after an Exness MT5-native validation.
- **Do not run the present 26-EA BAT unchanged.**

## 14. Evidence files

- `INSTALL AND RUN ON ACTIVE MT5.bat`
- `_Auto Deploy\Install-BMTradingPortfolio.ps1`
- `_Auto Deploy\LAST INSTALL.txt`
- `Active BAT Backtest 2026-08-12\FULL REPORT.md`
- `Active BAT Backtest 5Y 2026-08-12\FULL REPORT.md`
- `Global Macro Auction Market Research 2026-08-14\FULL REPORT.md`
- `Stock Auction Market Research Exness 2026-08-14\EXNESS-NET-COST-REPORT.md`
- `Fast Alpha Strategy Families Research 2026-08-15\FULL REPORT.md`
- `Fast Alpha Strategy Families Research 2026-08-15\TWO VARIANT PORTFOLIO REPORT.md`
