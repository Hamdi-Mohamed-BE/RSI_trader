# Best Prop Portfolio (2026-10-20): nine EAs, 1% risk per trade

**What it is:** the nine EAs of the Prop Ready portfolio, rebuilt as their own package.
- **Risk per trade:** 1% of the account ($100 on a $10,000 account), up from Prop Ready's $50.
- **Shared guard:** a new portfolio guard compiled into every EA. It is sized for 1% risk and enforces prop-firm style loss limits across all nine EAs together.
- **Nasdaq 5M:** the DI filter is OFF by default, at the owner's request. You can switch it back on at install.
- **Accounts:** works on any MT5 **hedging** account, with any broker, currency or balance.

> **Not a guarantee.** Every number below comes from historical replays of past market data, mostly with simulated ticks before 2026. FTMO's real execution, spreads and rules can differ. Past results do not predict future results.

## Folder contents

| File / folder | What it is |
|---|---|
| `Install Best Prop Portfolio.bat` | Double-click to install on the MT5 account that is open now |
| `Install-BestProp.ps1` | The installer the BAT runs. It checks everything, asks for confirmation, writes a 9-chart profile and restarts that MT5 |
| `EAs/` | The 9 final compiled EAs (`BP9-*.ex5`) |
| `Sets/` | The 9 final settings files (`BP9-*.set`), one per EA |
| `package/` | Build copy used by the installer: wrappers, shared strategy code, guard, compiled EAs, SETs and compile logs |
| `CalyxFTMOGuard.mqh` | Source of the shared portfolio guard |
| `PACKAGE.json` | Manifest with policy values and SHA-256 hashes. The installer refuses to run if any file changed |
| `build.py` | Offline rebuild from the Prop Ready sources (MetaEditor compile only, never touches a terminal) |
| `Account-Helpers.ps1`, `probe_account.py` | Read-only account checks used by the installer |

## How to install (about 2 minutes)

1. Open MT5 and log into the account you want to use: a demo first, then the FTMO account.
2. Make sure:
   - the account is **flat**, with no open positions and no pending orders;
   - **Algo Trading is OFF**;
   - it is a **hedging** account (FTMO accounts are).
3. Double-click **`Install Best Prop Portfolio.bat`**.
4. Answer three questions (press Enter to accept a default):
   - **Phase:** 1 = Challenge (stops trading after +10%), 2 = Verification (stops after +5%), 3 = Funded (no target). Default **1**.
   - **Risk per trade:** % of current equity, default **1.0**. The guard never lets a trade risk more than 1% of the starting balance, even if you type a larger number.
   - **Nasdaq 5M DI filter:** default **OFF**.
5. The installer then checks the account, finds the broker's gold, Nasdaq 100 and USDJPY symbols, and shows the limits.
6. **Type the confirmation line exactly** as it is shown.
7. MT5 closes and reopens with a new profile, `Calyx-BestProp9-<login>-<time>`, holding 9 charts with the EAs attached and **Algo Trading still OFF**.
8. Check the charts and inputs, then switch **Algo Trading ON** yourself.

For Phase 2 (a new Verification account): log into that account and run the BAT again with phase 2. Each login gets its own starting-balance reference.

The installer never places, modifies or closes trades, and it never switches Algo Trading on. Re-running it keeps the saved starting balance, so it cannot reset a loss stop.

A safe check that touches nothing: `"Install Best Prop Portfolio.bat" -ValidateOnly` verifies all files and hashes.

## How the portfolio works

### 1. Nine independent strategies, three markets
Each EA runs on its own chart with its own magic number. They trade at different times and on different setups, so their losses tend not to come all at once:
- **Nasdaq 100 (US100 / USTEC):** five EAs. The cash open, an hourly range, month-start flow and two opening-range breakouts.
- **Gold (XAUUSD):** three EAs. Oversold VWAP rebounds and two opening-range breakouts.
- **USDJPY:** one EA, London-open momentum.

### 2. One shared risk guard over all nine
Every EA's order goes through the same guard before it reaches the broker. The guard shares its state between the charts through MT5 global variables, keyed by account, so the nine EAs act as one portfolio.

| Rule | Value (on a $10,000 start) | What it does |
|---|---|---|
| Risk per trade | 1% of the starting balance ($100), and never more than 1% of current equity | Lots are sized from the stop distance and **rounded down**. If even the minimum lot is too big, the trade is skipped |
| Total open risk | 4.5% ($450) | The sum of all open trades' initial stop risk. A profitable trailing stop does not free up this risk |
| Open risk per market | 3% ($300) | For example, all Nasdaq trades together |
| Daily loss stop | −3% of the day's starting balance ($300) | Counts open losses plus a 1.25× reserve on open trades. No new entries for the rest of the day (Prague time, which matches FTMO's day) |
| Equity entry floor | 92% of the start ($9,200) | No new trades if the projected equity would fall below it |
| Hard latch | equity ≤ 90% of the start, or −5% on the day | Mirrors FTMO's limits. Once hit, new entries are blocked until you review |
| Trades per day | max 7 entries, and stop after 3 losing trades | Avoids over-trading on bad days |
| Margin | at most 80% of protected equity | No over-leveraging |
| Phase target | Challenge: stops new entries at +10% once 4 trading days are reached. Verification: same at +5% | Lets open trades finish, then waits for you to request review |
| Stops | every entry must have a stop loss, and stops can never be widened | Strategy management (trailing, break-even, time exits) keeps running after entry stops |

The guard only blocks **new entries**. It never force-closes positions. Gaps, slippage and costs can make a real loss bigger than the planned risk.

### 3. Locked to the account it was installed on
Each EA checks the login, server, currency and symbol it was installed for. It refuses to trade on any other account, or in the Strategy Tester. This is safety, not licensing.

## The nine EAs and their settings

Magic numbers are unique per EA. "R" is one unit of the trade's planned risk.

### 1. Nasdaq 5M Candle Momentum
- **Setup:** `BP9-nasdaq-5m-candle-momentum` · USTEC · M5 · magic 862020.
- **Entry:** when the 09:30–09:35 New York 5-minute candle closes, buy if price is above EMA(12), or sell if it is below.
- **DI filter:** OFF by default (`InpRequireDIAgreement=false`). When ON, a buy also needs +DI(14) > −DI(14), and a sell the reverse.
- **Stop:** 0.60% of price (`InpInitialStopPercent=0.60`).
- **Target:** none (`InpUseFixedTarget=false`).
- **Trailing:** ATR(14) × 6 trail starting at +1R (`InpTrailingATR=6`, `InpTrailStartR=1`).
- **Holding:** no session close, so it can hold overnight and over weekends.
- **Limits:** one position at a time.

### 2. USDJPY London Open Momentum
- **Setup:** `BP9-usdjpy-london-open-momentum` · USDJPY · M15 · magic 980908901.
- **Entry:** measures the 08:00–09:00 London move, then follows its direction. Wednesday to Friday only.
- **Filters:**
  - the move must be at least 0.2 × ATR;
  - formation tick activity must be at least 25% of its 20-day median;
  - ADX(14) on M15 must be ≥ 20, with DI direction agreement.
- **Stop:** 5 × ATR(14).
- **Target:** 1R (`InpTargetR=1.0`).
- **Break-even:** at +0.75R.
- **Time exit:** closes 30 seconds before 16:00 London.

### 3. US100 Month End Flow
- **Setup:** `BP9-us100-month-end-flow` · USTEC · M30 · magic 969060500.
- **Entry:** turn-of-month flow, long only, on the first three business days of the month. It enters after the first New York hour.
- **Stop:** 1.5 × ATR(14).
- **Target:** 2.5R.
- **Time exit:** after 6 hours (`InpMaximumHoldHours=6`).
- **Filter:** rejects trades where the spread is above 20% of the risk.

### 4. XAU RSI VWAP
- **Setup:** `BP9-xau-rsi-vwap` · XAUUSD · H1 · magic 926400006.
- **Entry:** long only. Uses RSI(16) calculated on a VWAP that resets each broker day, and buys when RSI crosses back up through 18 from below.
- **Stop:** below the lowest low of the last 5 H1 candles, plus 0.1 ATR.
- **Target:** 0.5R. The break-even setting (0.75R) sits beyond the target, so it does not normally activate.
- **Session:** all broker hours.

### 5. US100 H1 ORB 13UTC
- **Setup:** `BP9-us100-h1-orb-13utc` · USTEC · M15 · magic 962000402.
- **Range:** 13:00–14:00 UTC. The width must be 0.35–4.0 × H1 ATR, and opening activity at least 0.5 × its median.
- **Entry:** a breakout within the next 60 minutes, confirmed by a closed M15 candle: body ≥ 55%, close ≥ 0.03 ATR beyond the range, relative activity ≥ 0.7.
- **Stop:** the opposite side of the range plus 0.1 ATR, at most 3 ATR away.
- **Target:** 0.5R.
- **Time exit:** flat at 20:00 UTC.
- **Limits:** one trade a day.

### 6. US100 ORB New York M30
- **Setup:** `BP9-us100-orb-new-york-m30` · USTEC · M30 · magic 961000310.
- **Range:** 09:30–09:35 New York. The width must be 0.2–1.8 × M15 ATR, and opening activity ≥ 0.6.
- **Entry:** within 180 minutes, a closed M30 candle breaks out (body ≥ 55%, activity ≥ 0.8, close ≥ 0.03 ATR beyond the range).
- **Stop:** the opposite side of the range plus 0.1 ATR, at most 2 ATR away.
- **Target:** 0.5R.
- **Time exit:** flat at 15:55 New York.
- **Limits:** one trade a day; the spread must be ≤ 12% of the range.

### 7. US100 Selective ORB V3
- **Setup:** `BP9-us100-selective-orb-v3` · USTEC · M5 · magic 86260823.
- **Range:** the 30-minute New York opening range. The width must be 0.05–0.35 × daily ATR, and opening activity ≥ 0.6.
- **Breakout:** a strong M5 candle (activity ≥ 0.9, body ≥ 75%, buffer 0.015 daily ATR) that agrees with session VWAP.
- **Entry:** on a controlled retest of the broken edge, within 3 candles.
- **Direction schedule:** both directions 10:00–10:29, longs only 10:30–10:59, shorts only 11:00–11:30.
- **Stop:** the opposite side of the range plus 0.05 × range, at most 0.8 daily ATR away.
- **Target:** 0.5R.
- **Time exit:** flat at 15:55 New York.

### 8. XAU ORB New York M30
- **Setup:** `BP9-xau-orb-new-york-m30` · XAUUSD · M30 · magic 961000301.
- **Range:** 09:30–10:00 New York. The width must be 0.2–1.8 × M15 ATR.
- **Entry:** within 180 minutes, a confirmed M30 breakout (body ≥ 55%, activity ≥ 0.8).
- **Stop:** the opposite side of the range plus 0.1 ATR, at most 2 ATR away.
- **Target:** 0.5R.
- **Time exit:** flat at 15:55 New York.

### 9. XAU ORB London–NY Overlap M30
- **Setup:** `BP9-xau-orb-london-ny-overlap-m30` · XAUUSD · M30 · magic 961000303.
- **Range:** 13:00–13:05 UTC.
- **Entry:** within 180 minutes, a confirmed M30 breakout (body ≥ 55%, activity ≥ 0.8, close ≥ 0.03 ATR beyond the range).
- **Stop:** the opposite side of the range plus 0.05 ATR, at most 1.5 ATR away.
- **Target:** 0.5R.
- **Time exit:** flat at 16:00 UTC.

### Settings shared by every EA in this package
- **Strategy risk request:** `InpRiskPercent=1.0`. The guard then sizes the trade down to its cap.
- **Guard allocation:** `FTMOAllocationMode=1`, `FTMOAllocationValue=1.0` (1% of current equity).
- **Default phase:** `FTMOPhase=1` (Challenge).
- **Account binding fields:** `FTMOExpectedLogin` / `Server` / `Symbol` / `Currency`, `FTMOReferenceBalance` and `FTMOStartUtcTime` are left blank in the `Sets/` files. The installer fills them for your account. Attaching a SET by hand without these values makes the EA refuse to start, by design.
- **Excluded:** news EAs, hourly bots and the adaptive governor (`InpAdaptivePortfolioControls=false`) are not part of this portfolio.

## Test results

Retest of this exact package configuration, on 2026-10-20: nine EAs, 1%, the 1% / 4.5% / 3% guard, a $300 daily stop and the $9,200 floor. The retest files are in `../../Best Prop Portfolio Retest 2026-10-20/`. These are historical replays: the out-of-sample period was previously inspected, and they are not forecasts.

**1. Out of sample: both FTMO phases, 394 starts from Oct 2024 to Apr 2026**

| Nasdaq DI | Passed ≤180 d | Funded ≤90 d | Funded ≤60 d | Median days to funded | Breaches | Stalled at buffer | Worst equity DD | Worst day |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **OFF (default)** | 87–90% | 61–69% | 27–39% | 64–71 | 0 | 20–25% | $1,515 | $271 |
| ON | 96–97% | 62–70% | 25–34% | 70–77 | 0 | 7–9% | $1,120 | $271 |

**2. Monte Carlo (2,000 block-bootstrap paths over 5 years)**

| Nasdaq DI | Costs | Passed ≤180 d | Funded ≤90 d | Median days to funded | Breaches | Stalled | Equity DD p95 |
|---|---|---:|---:|---:|---:|---:|---:|
| **OFF** | recorded | 55.5% | 38.9% | 71 | 0 | 53% | $1,460 |
| **OFF** | stress | 42.6% | 29.8% | 72 | 0 | 65% | $1,550 |
| ON | recorded | 63.6% | 40.0% | 78 | 0 | 45% | $1,358 |
| ON | stress | 49.6% | 30.3% | 80 | 0 | 55% | $1,454 |

**3. Continuous trading over the out-of-sample years (Oct 2024 to Oct 2026, no phase stop, $100 per trade)**

| Nasdaq DI | Costs | Trades (/month) | Return | PF | Win rate | Max equity DD | Positive months |
|---|---|---:|---:|---:|---:|---:|---:|
| **OFF** | recorded | 908 (37.9) | +170.8% | 1.52 | 56.8% | $1,375 | 21/25 |
| **OFF** | stress | 19 | **−7.7%** | 0.30 | 36.8% | $787 | **stalled** |
| ON | recorded | 832 (34.7) | +183.7% | 1.65 | 58.2% | $1,023 | 21/25 |
| ON | stress | 831 (34.7) | +160.9% | 1.56 | 58.0% | $1,090 | 20/25 |

**What the stalled run shows:**
- With Nasdaq DI OFF and higher costs, the first month (Oct 2024) lost $713. Nasdaq caused most of it: 8 trades, −$682.
- That left equity at about $9,234, just above the $9,200 entry floor, so the guard blocked every new entry afterwards. FTMO was never breached, but the account was effectively stuck.
- **DI ON was better in every test.** You can choose it at install.

## What is new compared with Prop Ready (`Packages/PropReady`)

| | Prop Ready | Best Prop Portfolio |
|---|---|---|
| Risk per trade | 0.5% ($50) | **1% ($100)** |
| Total / per-market open risk | 2.25% / 1.5% | **4.5% / 3%** |
| Strategy risk request (`InpRiskPercent`) | 0.5 | **1.0** |
| Nasdaq 5M DI filter (default) | ON | **OFF** |
| Default phase | Funded (no target) | **Challenge (+10% stop)** |
| Daily stop, 92% buffer, 90% floor, 5% daily latch, 7 entries / 3 losses | same | same |
| Strategy signals, stops, targets, five ORBs at 0.5R | same | same |

The original Prop Ready package is unchanged: `build.py` verifies its hashes before and after building.
