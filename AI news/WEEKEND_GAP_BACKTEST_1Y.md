# XAUUSD Friday Weekend-Straddle Backtest

Period: 2025-08-01 through 2026-08-02 UTC  
Broker feed: `MEXAtlantic-Demo` / `XAUUSD..` M1  
Spread and weekend gap slippage: included

## Selected robust configuration

- Offset: `$1.50` outside the completed M1 wick
- Placement: `5` minutes before the inferred Friday close
- Stop: `$20.00`
- Reward/risk: `4.0:1`
- Maximum hold: `720` market minutes
- First fill cancels the opposite pending order
- If neither pending trigger is crossed at the weekly reopen, both are cancelled immediately

## Full-period result

| Trades | Win rate | Profit factor | Net | Max drawdown | Friday fills | Reopen fills | Expired weekends |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 46 | 50.00% | 2.855 | +43.28R | 4.58R | 32 | 14 | 5 |

At a hypothetical fixed 1% account risk per filled trade, this sequence compounds to **+52.30%** with **4.50%** maximum equity drawdown.

## Frozen holdout validation

The configuration was selected using only the first 75% of the year. The last 25% was opened once after selection.

| Sample | Trades | Win rate | Profit factor | Net | Max drawdown |
|---|---:|---:|---:|---:|---:|
| Development | 33 | 51.52% | 3.475 | +38.75R | 3.86R |
| Holdout | 13 | 46.15% | 1.590 | +4.52R | 4.58R |

## Four-block stability

| Block | Trades | Win rate | Profit factor | Net | Max drawdown |
|---|---:|---:|---:|---:|---:|
| Q1 (2025-08-01 to 2025-10-31) | 10 | 40.00% | 1.966 | +4.86R | 2.01R |
| Q2 (2025-10-31 to 2026-01-31) | 11 | 54.55% | 4.491 | +17.26R | 3.09R |
| Q3 (2026-01-31 to 2026-05-02) | 12 | 58.33% | 3.928 | +16.64R | 2.00R |
| Q4 (2026-05-02 to 2026-08-02) | 13 | 46.15% | 1.590 | +4.52R | 4.58R |

## Where the edge came from

| Fill source | Trades | Win rate | Profit factor | Net |
|---|---:|---:|---:|---:|
| Friday pre-close | 32 | 53.12% | 4.184 | +42.12R |
| Weekly reopen | 14 | 42.86% | 1.115 | +1.16R |

Most of the historical edge came from stops triggered before Friday close. The Monday-only gap component was only marginally profitable.

## Limits

M1 bars do not reveal tick order inside a candle. Ambiguous candles use stop-first logic, and when both pending sides are touched in one M1 bar the worse completed side is selected. Real weekend fills can be worse than this broker history because liquidity and spreads vary.
