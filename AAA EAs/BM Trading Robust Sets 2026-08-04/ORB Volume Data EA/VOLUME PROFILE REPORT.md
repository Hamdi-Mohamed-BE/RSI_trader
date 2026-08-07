# ORB tick-activity volume-profile research

## Honest conclusion

The volume profile is useful as context and as an on-chart explanation, but the tested filters did not earn automatic live activation. XAUUSD's value-area filter reduced the final-year return too much. BTCUSD and USTEC filters reduced their losses but remained unprofitable. US30 and US500 were better left unchanged.

The recommended live behavior is therefore: show the profile, but leave all three profile filters disabled. The original XAUUSD baseline remains validated and the original US30 baseline remains a modest pass. BTCUSD, USTEC, and US500 remain research-only with trading disabled in the supplied visual presets.

## What the chart means

- POC (orange): the price bin with the most Exness quote-tick activity from 08:00 New York through the end of the opening range.
- VAH / VAL (blue): the upper and lower edges of the contiguous bins around POC containing 70% of that activity.
- OR-high / OR-low node ratio: activity in the price bin touching that opening-range boundary divided by average activity per bin. Below 1.00 is relatively thin; above 1.00 is relatively heavy.
- A value-area breakout closes beyond both the opening range and the relevant value-area edge. A POC bias asks that POC sit on the opposite half of the range. The LVN filter accepts only a boundary ratio at or below 1.00.

This is a broker tick-activity profile, not centralized exchange traded volume. It counts quote ticks by midpoint price because Exness CFD history does not provide a single consolidated CME/NYSE volume feed.

## Locked comparison

All figures use USD 10,000 initial balance, 1% equity risk per trade, MT5 Every Tick, random execution delay, and the New York 09:30 opening range. Cells show return / max equity DD / PF / trades.
US30's 2024 PF of 107.67 comes from only nine trades and must not be treated as a stable estimate.

| Market | Candidate chosen before final | 2024 development | Jan-Aug 2025 selection | Last-year candidate | Last-year control | Decision |
|---|---|---:|---:|---:|---:|---|
| XAUUSD | va | +20.20% / 4.04% / 2.54 / 42 | +7.27% / 4.31% / 2.10 / 20 | +1.30% / 5.48% / 1.12 / 34 | +8.19% / 6.40% / 1.53 / 50 | Reject filter; retain control |
| BTCUSD | lvn100 | +26.30% / 6.54% / 2.00 / 59 | +11.02% / 4.04% / 3.55 / 17 | -4.23% / 13.04% / 0.70 / 26 | -11.59% / 16.41% / 0.51 / 42 | Reject market; filter still loses |
| US30 | control | +10.32% / 2.05% / 107.67 / 9 | +6.01% / 3.10% / 2.43 / 12 | +2.69% / 4.92% / 1.23 / 23 | +2.69% / 4.92% / 1.23 / 23 | Retain modest control |
| USTEC | va | +5.53% / 3.18% / 1.57 / 24 | +6.46% / 2.85% / 2.57 / 13 | -1.56% / 3.72% / 0.48 / 6 | -3.52% / 4.91% / 0.29 / 9 | Reject market; filter still loses |
| US500 | control | +11.34% / 3.29% / 2.87 / 20 | +1.16% / 2.26% / 1.18 / 12 | -2.32% / 9.15% / 0.86 / 25 | -2.32% / 9.15% / 0.86 / 25 | Reject market; retain research control |

## No-lookahead safeguards

- Profile window ends at the opening-range close; later ticks are never included.
- New York daylight-saving conversion is automatic.
- The profile inputs were selected on 2024 development plus Jan-Aug 2025 selection data before the final-year comparison.
- The final-year result was not used to retune thresholds after it ran.

## Files

- `Volume Profile Settings`: safe visual presets. Trading remains enabled only for XAUUSD and US30.
- `Volume Profile Settings/Research Rejected`: tested filters that failed the final-year acceptance test.
- `Volume Profile Reports`: native MT5 reports and equity graphs for audit.
