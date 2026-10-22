# Nasdaq 5M — DI ON vs DI OFF, last two weeks (2026-10-08 → 2026-10-22 exclusive)

Protocol: [PROTOCOL.txt](PROTOCOL.txt).

**Setup:**
- Exact production EX5 (`fe9f391db5af`) and selected SET (`24911cd513b2`). DI OFF changes only `InpRequireDIAgreement=false`.
- USTEC M5, native MT5 Model 4, **100% real ticks**, 150 ms, $10,000 flat start, 1% risk.
- Standalone: no portfolio overlay or FTMO guard.

**Result: identical.** Both versions took exactly the same 9 trades: same entries, exits, lots and P&L, checked trade for
trade.

| Version | Return | Trades | / month | / weekday | Net PF | Win % | Equity DD (max %) | Net $ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DI ON (current default) | +4.32% | 9 | 19.6 | 0.90 | 2.05 | 55.6 | 2.65% | +431.71 |
| DI OFF | +4.32% | 9 | 19.6 | 0.90 | 2.05 | 55.6 | 2.65% | +431.71 |

**Why identical:**
- **9 signal days:** on every one, the 09:30 NY candle closed on the same side of EMA12 as the DI14 direction, so the DI
  filter never blocked a trade.
- **The 10th weekday (Mon 12 Oct):** no entry in either version, because the 9 Oct short was still open. The EA allows
  one position at a time.
- No positions were open at the test end. Costs: commission −$3.20, swap $0.

| Entry (NY) | Side | Lots | Exit (NY) | Hold | Net $ | Exit |
|---|---|---:|---|---:|---:|---|
| Thu 10-08 09:35 | Long | 0.54 | 10-08 12:49 | 3.2 h | −101.09 | stop |
| Fri 10-09 09:35 | Short | 0.54 | Mon 10-12 18:21 | 80.8 h | +124.05 | trailing stop |
| Tue 10-13 09:35 | Short | 0.55 | 10-13 18:41 | 9.1 h | −99.75 | stop |
| Wed 10-14 09:35 | Short | 0.55 | 10-15 00:51 | 15.3 h | +327.09 | trailing stop |
| Thu 10-15 09:35 | Short | 0.58 | 10-15 10:42 | 1.1 h | −105.04 | stop |
| Fri 10-16 09:35 | Short | 0.57 | Sun 10-18 18:02 | 56.5 h | +302.46 | trailing stop |
| Mon 10-19 09:35 | Long | 0.59 | 10-19 13:00 | 3.4 h | +9.22 | trailing stop |
| Tue 10-20 09:35 | Short | 0.60 | 10-20 10:07 | 0.5 h | −106.88 | stop |
| Wed 10-21 09:35 | Long | 0.59 | 10-21 14:49 | 5.2 h | +81.65 | trailing stop |

**Limits:**
- Two weeks and 9 trades is a tiny retrospective sample. It shows that DI made no difference in this window, not which
  setting is better.
- The longer-run evidence (Best Prop retest, FTMO studies) favoured DI ON.
- Nothing installed, no SET/BAT/live change, no push.
