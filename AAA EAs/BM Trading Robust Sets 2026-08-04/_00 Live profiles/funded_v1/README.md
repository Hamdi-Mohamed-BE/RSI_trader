# funded_v1 — 9 EAs + a configurable funded-account guard (2026-10-28)

Works on **any MT5 hedging account / broker**. Every limit is a prompt with a default. The defaults are the **Leveraged
$50k reward account** rules, as Leveraged answered on 2026-10-27.

| EA | Symbol | TF | Notes |
|---|---|---|---|
| Nasdaq 5M Candle Momentum | USTEC / US100 / NAS100 | M5 | **DI filter asked** at install (default ON) |
| EMA3 | XAUUSD | H4 | engine has a grid mode, but EMA3 never uses it |
| 3 Way Gold | XAUUSD | M15 | 3 modules, pending orders |
| ORB Volume Profile Volume Confirmed | XAUUSD | M5 | **0.5R** |
| XAU ORB London NY Overlap M30 | XAUUSD | M30 | **0.5R** (ORB05 preset) |
| DMC Fresh Reaction US100 | USTEC | H1 | |
| DMC Current XAU | XAUUSD | H1 | |
| XAU RSI VWAP | XAUUSD | H1 | |
| Gold Overnight Value Area | XAUUSD | M5 | added on request; little effect on results (see below) |

Strategy settings are the Full EA BAT presets, with only these changes: the two 0.5R targets, the Nasdaq DI choice, and
adaptive off.

## Install
1. Log the normal MT5 terminal into the account (hedging).
   - Make it **flat**: no positions and no pending orders.
   - Turn **Algo Trading OFF**.
2. Run `funded_v1.bat`. Enter keeps the default for every question:

| Question | Default |
|---|---|
| Account size | 50000 |
| Firm max loss % | 6 |
| Max-loss type (0 trails highest closed balance / 1 equity / 2 static) | 0 |
| Floor locks at the initial balance once reached and after payouts | Y |
| Firm daily loss % | 3 |
| Daily reset hour (UTC) | 0 |
| Daily loss measured from (1 = higher of balance / equity at reset, 0 = balance) | 1 |
| Current max-loss level on your dashboard | blank = computed |
| **Risk per trade** % of account size | **0.5** |
| Also cap each trade at % of the room above the floor (0 = off) | 5 |
| **Max open risk** % (all stops + pending orders) | **2** |
| Max open risk per symbol % | 1.5 |
| **Max daily loss** % (close ALL trades, stop for the day) | **2** |
| **Max daily win** % (close ALL trades, stop for the day; 0 = off) | **0.75** |
| Buffer above the max-loss level % (close ALL trades if equity reaches it) | 0.25 |
| No new entries ± minutes around high-impact USD news (0 = off) | 5 |
| Delete pending orders inside news windows | N |
| **Nasdaq 5M DI filter** ON / OFF | ON |

3. If the gold or Nasdaq symbol is not recognised, the installer asks for the exact Market Watch name.
4. Type the confirmation line. The installer then:
   - closes that terminal and writes a NEW profile (9 charts);
   - saves the baseline;
   - restarts MT5 with **Algo Trading still OFF**.
5. Check the charts, then turn Algo Trading on yourself.

**Other ways to run it:**
- `funded_v1.bat -UseDefaults` skips all questions.
- `funded_v1.bat -ValidateOnly` only checks the package.
- Reruns keep the saved baseline.

## What the guard does (account-wide, all 9 EAs together)
- **Each new entry:**
  - risk = min(risk %, taper % × room above the floor);
  - cut to fit the open, per-symbol, daily-loss and buffer limits;
  - lots round **down**;
  - skipped under 0.05%.
- **Stop rules:**
  - an entry without an SL is refused;
  - an SL cannot be widened or removed;
  - a pending order's risk is held back until it fills or is cancelled.
- **Close ALL positions and pending orders, and stop for the rest of that day, when:**
  - the day's equity is **+daily win %**;
  - the day's equity is **−daily loss %**;
  - equity reaches **floor + buffer**.
- **Floor:**
  - it trails the highest closed balance;
  - it **locks at the initial size** once reached (account +6%) and after any payout, as Leveraged confirmed;
  - payouts are not counted as daily losses.
- **News:** new entries are blocked in high-impact USD news windows (live MT5 calendar).
- **Breaches and errors:** a firm-limit breach or an uncertain execution latches entries off.
- **Binding:** the guard is bound to the account, server, symbol and currency.

## Expected results (Leveraged $50k, replay of 2021-10 → 2026-10 ledgers, NOT a forecast)
Full tables: `Funded V1 Build 2026-10-28/FUNDED_SIM.md`.

| Nasdaq DI | Risk | Payout / week, 3y average | Typical range (p10 – p90) | Payout / month | Breach | First payout (median) | Trades / month (/ day) |
|---|---:|---:|---:|---:|---:|---:|---:|
| **ON** | **0.5%** | **$99** | $8 – $177 | $428 | 0% | day 234 | 53 (1.73) |
| ON | 0.3% | $80 | $14 – $137 | $348 | 0% | day 239 | 56 (1.84) |
| ON | 0.75% / 1% | $103 / $99 | $5 – $199 | $447 / $430 | 0% | day 235 | 51 (1.68) |
| OFF | 0.5% | $84 | $0 – $173 | $367 | 0% | day 242 | 56 (1.85) |

Without Gold Overnight (the 8 EAs you first listed), 0.5% DI ON gives $100 a week, so adding it changes almost nothing.

**What to expect in practice (0.5%, DI ON):**
- **Year 1 is slow:** about **$46 a week**. A payout only comes after +6% plus a $3,000 cushion, and the consistency
  rule has to be met. 33% of 1-year runs paid nothing; 5% of 3-year runs never paid.
- **Weak market (2021–23):** about **$4 a week**.
- **Strong market (2024–26):** about **$177 a week**.
- **The edge is thin:** with +0.10R of extra cost per trade, income drops to about **$2 a week**.
- **Worst simulated day:** −$1,079 (history −$1,008). Worst week −$2,306.

## Confirm / limits
- **Payouts:** confirm with Leveraged that a **payout can be partial**. The floor stays at $50,000 after a payout, so
  withdrawing everything would leave no room to trade. The model keeps a $3,000 cushion.
- **News rule:** SL/TP fills inside a ±5 min news window are **not** prevented (Leveraged also counts those). The daily
  close-all waits until a news window ends, but the daily-loss and floor close-alls do not wait.
- **Simulation limits:**
  - the live guard closes trades at +0.75% equity, while the replay only stops new entries (no intratrade prices);
  - the replay assumes the balance at 00:00 UTC (live uses max(balance, equity)).
- **Costs:** gold commission at Leveraged is $4 / lot round trip; indices are free. The tester ledgers use the tester's
  own costs.
- **Not installed on any terminal. Not pushed.**
