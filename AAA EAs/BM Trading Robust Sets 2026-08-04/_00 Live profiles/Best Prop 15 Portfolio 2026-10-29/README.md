# Best Prop 15 Portfolio (2026-10-29): Best Prop 9 + six gold / DMC EAs, 1% risk per trade

**What it is:** the nine Best Prop EAs plus six more (owner request), with the **same guard and the same 1% risk**.

**The six added EAs:**
- EMA3
- 3 Way Gold
- Gold Overnight Value Area
- DMC Current XAU
- DMC Fresh Reaction XAU
- DMC Fresh Reaction US100

**Accounts:** works on any MT5 **hedging** account, with any broker, currency or balance. The installer, its questions and the safety checks are the same as Best Prop 9.

> **Not backtested as a 15-EA portfolio.** No replay or native run of this exact mix exists yet. The Best Prop 9 results (in `Best Prop Portfolio 2026-10-20/README.md`) do **not** apply to it. See the caveats below before using it on a paid challenge.

## The 15 EAs
| Market | EAs |
|---|---|
| Nasdaq 100 (US100 / USTEC) | Nasdaq 5M Candle Momentum (DI filter asked at install, default OFF), US100 H1 ORB 13 UTC (0.5R), US100 ORB New York M30 (0.5R), US100 Selective ORB V3 (0.5R), US100 Month End Flow, **DMC Fresh Reaction US100** |
| Gold (XAUUSD) | XAU RSI VWAP, XAU ORB New York M30 (0.5R), XAU ORB London-NY Overlap M30 (0.5R), **EMA3**, **3 Way Gold** (3 modules, market entries), **Gold Overnight Value Area**, **DMC Current XAU**, **DMC Fresh Reaction XAU** |
| USDJPY | USDJPY London Open Momentum (DI + ADX20 kept) |

**Strategy settings:**
- Signals, stops and targets are the Full EA presets used by the FTMO / Prop Ready builds.
- Every EA requests 1%, and adaptive mode is off.
- **DMC Fresh Reaction XAU** is new to the guarded builds. It uses the same EA as the US100 version, with the catalog preset `21 DMC Fresh Reaction XAU - ASIA 3R - DYNAMIC 50-20`. That preset was converted the same way the FTMO build converted the US100 one: adaptive off and guard inputs added. The build checks this.

## Guard (shared by all 15, identical limits to Best Prop 9)
| Rule | On a $10,000 start |
|---|---|
| Risk per entry | max **1%** of the saved starting balance ($100); lots round **down** |
| All open stops together | max **4.5%** ($450) |
| One symbol | max **3%** ($300) |
| Daily reserve / daily hard loss | 3% / 5% |
| Equity entry buffer / floor | 92% / 90% |
| Per trading day | max 7 entries / 3 losing positions |

The guard keeps its own state (`BP15`), separate from Best Prop 9.

## Caveats
- **Gold-heavy:** **8 of the 15 EAs trade gold.** They all share the **3% gold cap** ($300 = about three 1% trades at once) and the **7-entries-a-day** limit. On busy gold days the guard will refuse or shrink some of their entries, so adding EAs does not add risk one-for-one. It does change *which* trades get taken, which is exactly what has not been tested.
- **Research flags on the added EAs:**
  - **3 Way Gold** is labelled "watch only": it failed its older holdout.
  - In the Turbo study, **EMA3** and **Gold Overnight** were drags in both development and validation.
  - **DMC Fresh Reaction XAU** has no guarded test.
- **Before using it on a challenge:** run a replay of this 15-EA mix (FTMO 2-step, the same engine as the Best Prop retest), or at least a demo forward test.

## Install
1. MT5 open and logged in; account **flat**; **Algo Trading OFF**; hedging account.
2. Double-click **`Install Best Prop 15 Portfolio.bat`**.
3. Answer the questions; Enter keeps the default:

| Question | Choices | Default |
|---|---|---|
| Phase | 1 Challenge (stop at +10%) / 2 Verification (+5%) / 3 Funded (no target) | 1 |
| **Risk type** | 1 = % of current equity / 2 = fixed amount per trade in the account currency | 1 |
| **Risk per trade** | any value, e.g. `0.25`, `0.5`, `1.0` (comma accepted), or e.g. `50` for a fixed amount | 1.0 % (or 100) |
| **Nasdaq 5M DI filter** | ON / OFF | OFF |
| **USDJPY London DI filter** | ON / OFF (its ADX20 filter always stays on) | ON |

   - Only these two EAs have a DI filter; the other 13 have none.
   - **The guard caps every trade at 1% of the saved starting balance.** A higher request shows a warning and is capped. Going above 1% needs a guard rebuild.
   - **Non-interactive form:** `-RiskMode FIXED_USD -RiskValue 50 -NasdaqDIFilter ON -UsdJpyDIFilter OFF -Phase Funded`.
4. **Type the confirmation line exactly:** `BEST PROP 15 <login> <currency> <phase>`.
5. MT5 restarts into a new profile, `Calyx-BestProp15-<login>-<time>`, with **15 charts** and **Algo Trading still OFF**. Check the charts, then turn Algo Trading on yourself.

**Safe check:** `"Install Best Prop 15 Portfolio.bat" -ValidateOnly` verifies every file and hash and touches no account (PASS on 2026-10-29).

## Files
| File / folder | What it is |
|---|---|
| `Install Best Prop 15 Portfolio.bat` | double-click installer |
| `Install-BestProp15.ps1`, `Account-Helpers.ps1`, `probe_account.py` | installer, generated from Best Prop 9's by `build.py` (asserted substitutions), plus read-only account checks |
| `EAs/`, `Sets/` | the 15 compiled EAs (`BP15-*.ex5`) and their SETs |
| `package/` | the build copy used by the installer (wrappers, shared sources, guard, EX5, SETs, compile logs) |
| `CalyxFTMOGuard.mqh` | the guard source |
| `PACKAGE.json` | manifest with policy values and SHA-256 hashes; the installer refuses to run if anything changed |
| `build.py` | offline rebuild: compiles with MetaEditor only and never touches a terminal |

## Build check (2026-10-29)
- **Compile:** 15 / 15 compiled with 0 errors and 0 warnings.
- **Magic numbers:** 15 unique.
- **Source packages:** PropReady, FTMO-AnyBroker and Best Prop 9 are byte-for-byte unchanged.
- **Validation:** `-ValidateOnly` passes for both this installer and Best Prop 9's.
- **Not done:** installed on any terminal, or backtested.
