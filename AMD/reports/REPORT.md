# AMD Session Strategy Backtest

- Period: **2025-07-30T00:00:00+00:00 to 2026-07-30T00:00:00+00:00**
- Data source: **MT5 / MEXAtlantic-Real**
- Starting balance per symbol: **$1,000**
- Risk: **3.00% of current balance per leg; maximum planned exposure 3.00%**
- Asia range: **00:00-08:00 UTC**
- London reference: **08:00-09:00 UTC H1 close; no London trade is placed**
- A close beyond the Asia range establishes direction; New York trades only the opposite side
- Entry mode: **single_fallback** — Rest the liquidity limit during the observation window; if it does not fill, cancel it and replace it with the breakout stop.
- New York observation window: **45 minutes from 13:30 UTC**
- Breakout target: **4.00R**; stop buffer: **5.00% of the Asia range**
- Management: **at +0.50R, stop advances to +0.15R**
- Pending orders expire at 16:00 UTC.
- Any open trade is closed at **21:00 UTC**
- Conservative rule: when SL and TP are both touched in one M1 bar, SL is assumed first.

- Max DD is realized balance drawdown; intrabar floating drawdown is not included.

| Symbol | Trades | NY limit | NY stop | Both-filled days | Win rate | PF | Net R | Max exposure | Realized max DD | Ending balance |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| XAUUSD (XAUUSD..) | 34 | 24 | 10 | 0 | 38.24% | 0.68 | -4.56R | 3.00% | 38.79% | $842.06 |

## Entry-leg breakdown

| Symbol | Leg | Trades | Win rate | PF (R-based) | Net R |
|---|---|---:|---:|---:|---:|
| XAUUSD | NY liquidity limit | 24 | 29.17% | 0.35 | -11.10R |
| XAUUSD | NY breakout stop | 10 | 60.00% | 2.64 | 6.54R |
