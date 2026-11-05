# Edge 10 — no guard (built 2026-11-04)

Run `Edge 10 - no guard.bat`. It installs 10 EAs on the MT5 terminal that is open now, as a new 10-chart profile. It restarts MT5 once
and never places orders.

| EA | Symbol | Chart |
|---|---|---|
| USDJPY London Open Momentum | USDJPY | M15 |
| AAA Final EMA3 | XAUUSD | H4 |
| ORB Volume Profile Volume Confirmed | XAUUSD | M5 |
| ORB Volume Profile | XAUUSD | M5 |
| Sell Nasdaq 15min | USTEC | M15 |
| XAU Regime Switch | XAUUSD | M5 |
| XAU Elliott Wave 1-2-3 | XAUUSD | H4 |
| Nasdaq 5M Candle Momentum (ATR6 stop by default; the installer asks NEW / OLD) | USTEC | M5 |
| XAU RSI VWAP | XAUUSD | H1 |
| 3 Way Gold, breakout module only, market entries | XAUUSD | M15 |

**NO GUARD:**
- no FTMO / prop limits, no shared daily stop, no adaptive governor;
- risk is per trade per EA and stacks across open trades;
- 6 of the 10 EAs trade gold.

**The installer asks:**
- risk type and amount: % of equity (default 0.5%) or fixed USD;
- Nasdaq 5M DI and USDJPY DI (default ON);
- Nasdaq stop version (default NEW ATR6).

**How it is built:**
- **Sizing:** each EA's production source is included unchanged, except that its risk multiplier is replaced by the chosen risk
  (`RiskSupport.mqh`, same method as the Current 14 + ORB and ORB-only packages).
- **Strategy inputs:** the Full EA presets. They equal the inputs of the long-history runs used in
  `Edge Portfolio E10 2026-11-04`, except 3 Way Gold: modules A and C off, market entries.
- **Installer:** the Current 14 + ORB installer, adapted for 10 entries.
- **Package:** `../Packages/Edge10`, version EDGE10-NOGUARD-20261104. Rebuild with `uv run python build.py` from the EA store; it compiles all 10
  EAs again.

**Checks:**
- **Compile:** 10/10, 0 errors / 0 warnings.
- **`-ValidateOnly`:** PASS.
- **Native parity** (`Edge Portfolio E10 2026-11-04/parity.py`, Model 4, 2026-05-01 → 2026-11-01, real ticks): every wrapped EA gives trades
  identical to the production EX5 with the same inputs, 10/10.
  - The journal "rejected" counts (Nasdaq 5M 100,524, 3 Way Gold 4, Regime Switch 2) are the same in the production runs.
- **3 Way Gold:** the journal shows `modules=010 market_entries=1`; all 35 trades are breakout trades.

**Not done:** installed on any terminal; a combined 10-EA native run; pushed.

**Evidence:** see `Edge Portfolio E10 2026-11-04/README.md`, `TABLES.md` and `INCOME.md`. It is in-sample, and the list was chosen after seeing the
history.

---

# Mixed 22 — no guard (built 2026-11-05)

Run `Mixed 22 - no guard.bat`. It installs FTMO17's 17 EAs plus the five E10-only bots (ORB VP Volume Confirmed, ORB VP, Sell Nasdaq 15min, XAU Regime Switch, XAU Elliott Wave) as a new 22-chart profile, with the same questions as Edge 10.
**No guard.** 3 Way Gold keeps all three modules here, and its risk applies to each module. Many trades can be open at once.

**Build:** `build_mixed.py` → `../Packages/Mixed22`, version MIXED22-NOGUARD-20261105. No recompile: the EX5s and SETs are copied from the Current 14 + ORB and Edge 10 packages, the same files tested in `Merged E10 FTMO17 2026-11-05`.

**Checks:** `-ValidateOnly` PASS; 22 unique magics; same RiskSupport.mqh in both sources. **Not done:** installed on any terminal; a combined 22-EA native run; pushed.

**Warning:** over 2019-2026 this has the largest drawdown of the three (162R vs FTMO17 110R and E10 65R). At 0.5% it breached a funded account on 2025-05-12 in the 2024 start test. At 1% it breached in 72 days.
