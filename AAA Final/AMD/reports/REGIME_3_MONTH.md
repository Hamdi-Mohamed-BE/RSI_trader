# AMD Session Strategy Backtest

- Period: **2026-04-30T00:00:00+00:00 to 2026-07-30T00:00:00+00:00**
- Data source: **MT5 / MEXAtlantic-Demo**
- Starting balance per symbol: **$1,000**
- Risk: **3.00% of current balance per leg; maximum planned exposure 3.00%**
- Asia range: **00:00-08:00 UTC**
- London reference: **08:00-09:00 UTC H1 close; no London trade is placed**
- A close beyond the Asia range establishes direction; New York trades only the opposite side
- Entry mode: **stop_only** — After the configured New York observation window, place only an opposite-London breakout stop beyond that range.
- New York observation window: **45 minutes from 13:30 UTC**
- Breakout target: **4.00R**; stop buffer: **7.50% of the Asia range**
- Management: **at +0.30R, stop advances to +0.15R**
- Pending orders expire at 16:00 UTC.
- Any open trade is closed at **21:00 UTC**
- Conservative rule: when SL and TP are both touched in one M1 bar, SL is assumed first.

- Max DD is realized balance drawdown; intrabar floating drawdown is not included.

| Symbol | Trades | NY limit | NY stop | Both-filled days | Win rate | PF | Net R | Max exposure | Realized max DD | Ending balance |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| XAUUSD (XAUUSD..) | 7 | 0 | 7 | 0 | 85.71% | 11.04 | 11.45R | 3.00% | 3.00% | $1381.26 |

## Entry-leg breakdown

| Symbol | Leg | Trades | Win rate | PF (R-based) | Net R |
|---|---|---:|---:|---:|---:|
| XAUUSD | NY liquidity limit | 0 | 0.00% | 0.00 | 0.00R |
| XAUUSD | NY breakout stop | 7 | 85.71% | 12.45 | 11.45R |
