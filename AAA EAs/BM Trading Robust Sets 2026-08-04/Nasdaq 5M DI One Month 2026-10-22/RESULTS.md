# Nasdaq 5M — DI ON vs DI OFF, last month (2026-09-22 → 2026-10-22 exclusive)

Protocol: [PROTOCOL.txt](PROTOCOL.txt).

**Setup:**
- Exact production EX5 (`fe9f391db5af`) and SET (`24911cd513b2`). DI OFF changes only `InpRequireDIAgreement=false`.
- USTEC M5, native MT5 Model 4, **100% real ticks**, 150 ms, $10,000 flat start, 1% risk, standalone.
- 22 weekdays in the window.

| Version | Return | Trades | / month | / weekday | Net PF | Win % | Equity DD (max %) | Net $ | Swap $ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DI ON (current default) | +9.81% | 15 | 15.2 | 0.68 | 3.26 | 73.3 | 2.65% | +981.15 | −11.14 |
| DI OFF | **+11.03%** | 19 | 19.3 | 0.86 | 3.02 | 73.7 | 2.89% | **+1,103.14** | −22.41 |

**Where they differ:**
- **5 days DI filtered:** DI OFF traded them and DI ON did not.

  | Date | Side | Net $ |
  |---|---|---:|
  | 09-23 | short | +88.08 |
  | 09-28 | short | +41.68 |
  | 09-29 | short | −105.22 |
  | 10-02 | long, held to 10-05 | +101.06 |
  | 10-06 | short | +97.41 |
  | **Total** | 4 won, 1 lost | **+223.01** |

- **1 trade only DI ON took:** the 10-05 long (+99.22). DI OFF was still holding its 10-02 long, which closed at the same
  moment (10-05 21:46 NY), so DI OFF could not open it.
- **No trade in either:**
  - 10-07: DI ON found no signal; DI OFF was still holding the 10-06 short.
  - 10-12: both were holding the 10-09 short.
- **Same trades, slightly different size:** every other trade is the same entry and exit. From 10-08 on, DI OFF's
  slightly larger equity gives slightly larger lots (−$1.8 net).
- **Net difference:** DI OFF +$121.99 better over the month.

**Limits:**
- This is one month: 15 vs 19 trades, a retrospective snapshot.
- The extra DI OFF trades won 4 of 5 here; that says nothing about the long run. The 1-year, 5-year and FTMO studies
  favoured DI ON.
- Nothing installed, no SET/BAT/live change, no push.
