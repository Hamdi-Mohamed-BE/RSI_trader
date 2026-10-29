# Turbo 50k - Custom 5 Guarded (2026-10-27)

The owner's 5-EA portfolio for the **Turbo $50k reward account**, with the **Turbo guard** built into every EA.

| EA | Symbol | Timeframe |
|---|---|---|
| Nasdaq 5M Candle Momentum, **DI filter OFF** | USTEC | M5 |
| XAU RSI VWAP | XAUUSD | H1 |
| Gold Overnight Value Area | XAUUSD | M5 |
| 3 Way Gold (3 modules, pending orders) | XAUUSD | M15 |
| EMA3 | XAUUSD | H4 |

Strategy settings are the same presets the Full EA BAT installs. Only the following were changed:
- EA risk request 0.75%;
- adaptive governor off;
- Nasdaq DI off.

## How to install
1. Log the **normal** MT5 terminal into the Turbo account (hedging).
   - Make it **flat**: no positions and no pending orders.
   - Turn **Algo Trading OFF**.
2. Run `Install Turbo 5 Guarded.bat` and answer the prompts:
   - **Account size** [50000].
   - **Current max-loss level** from the Turbo dashboard. Leave it blank only if the account has never been above its
     starting balance (default = balance − 6%).
   - **Equity trailing?** Y/N [N].
3. Type the confirmation line. The installer then:
   - closes that terminal and writes a NEW profile (5 charts);
   - saves the baseline;
   - restarts MT5 with Algo Trading still OFF.
4. Check the 5 charts and inputs, then turn Algo Trading on yourself.

**Reinstalls and checks:**
- **Reruns keep the saved baseline:** `MQL5\Files\Calyx-Turbo5-<login>-<hash>.json`.
- **Check mode:** `Install Turbo 5 Guarded.bat -ValidateOnly` checks the package hashes without touching any account.

## What the guard does (on every new entry, account-wide, all 5 EAs together)
| Rule | $50k value |
|---|---|
| Risk per trade | min($375, **5% of the room above the trailing floor**), so at most **$150**; cut to fit all limits below; lots round DOWN; skipped under $25 |
| Trailing floor | highest closed balance − $3,000 (or the dashboard level you enter); re-based to (balance after a withdrawal) − $3,000 |
| Max open risk (all stops, incl. pending orders) | $1,000 |
| Max open risk per symbol | $750 |
| Daily soft stop (today's realised loss + open stops) | $1,000 (firm limit $1,500) |
| Buffer above the floor | $125 |
| Daily profit cap (20% consistency helper) | no new entries once the day is up $375 |

**It also:**
- refuses entries without a stop-loss;
- refuses a widened or removed SL, and a pending-order change that raises risk;
- holds a pending order's risk against later entries until it fills or is cancelled;
- latches entries off on an equity breach or an uncertain execution;
- binds itself to the account, server, symbol and currency;
- requires a hedging account.

**It never closes trades.** Gaps, slippage and costs can exceed planned stop risk.

## Expected results (simulation, NOT a forecast)
In-sample replay of frozen native ledgers, 2021-10 → 2026-10, 80% trader share
(`Turbo 50k Funded Portfolio 2026-10-26/CUSTOM5.md`).

| Risk setting | Payout / week, 3y MC mean | Payout / month | Breach | Worst day | Trades / month (/ day) |
|---|---:|---:|---:|---:|---:|
| 0.5% guard | $45 | $195 | 0% | −$900 | 42 (1.4) |
| **0.75% guard (this package)** | **$65** | **$282** | 0% | −$735 | 50 (1.6) |

- **Without the guard,** the same 5 EAs breached in 100% of simulated paths, after an average of 12 days at 0.75%.
- **The first payout** takes a median of about 227 days, because the 20% consistency rule and the 3 profitable days
  are slow to meet with five EAs.

## Test evidence (`Turbo Guard Build 2026-10-26/`)
- **Wrapper fidelity:** each guarded EA in pass-through mode reproduces the original EA trade for trade. 5 / 5 match
  over 6 months, Model 4, $50k, 1:30.
- **Guard ON, each EA alone, 1 year (Model 4, tester-simulated rewards):** the audit passes for all 5.
  - Every entry was sized exactly to the rule.
  - Every refusal was justified.
  - The floor matched an independent rebuild within $0.63.
  - No breach; equity stayed at least $1,190 above the daily limit and $1,360 above the floor.
- **Harness, 12 / 12 PASS:** sizing, no-SL refusal, SL widen / remove refusal, pending reservation, pending modify
  refusal, withdrawal re-base, breach latch.
- **Installer:** sandbox-tested end to end on a fake data folder: 5 charts, armed SETs, baseline kept on rerun,
  Algo OFF.

## Not proven / confirm with Turbo
- **No combined native test of all 5 together.** The MT5 tester runs one EA at a time; the portfolio numbers come
  from the Python replay.
- **No payout in the single-EA test years.** One EA rarely meets the 3 × $250 days and the consistency rule. The
  withdrawal path is proven by the harness.
- **Confirm with Turbo before going live:**
  - balance or equity trailing;
  - whether the floor locks at the starting balance;
  - where the floor goes after a payout (the guard re-bases it to balance − $3,000);
  - the daily-loss basis and day reset time (the guard uses UTC+2/+3);
  - whether EAs, news trading and hedging are allowed.
- **Not installed on any terminal. Nothing pushed.**
