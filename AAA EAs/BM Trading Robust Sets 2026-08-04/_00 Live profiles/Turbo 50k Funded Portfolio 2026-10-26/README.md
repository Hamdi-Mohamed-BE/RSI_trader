# Turbo 50k Funded Portfolio (2026-10-26, v2 "improved") — RESEARCH FILES, NOT AN INSTALLER

Built for the owner's existing **$50k Turbo reward account**. The rules come from the owner's screenshot:
- 3% daily loss;
- 6% trailing max loss;
- 3 profitable days of ≥ 0.5%;
- 20% consistency rule;
- 80% / 95% share.

Evidence: `AAA EAs/BM Trading Robust Sets 2026-08-04/Turbo 50k Funded Portfolio 2026-10-26/` (PLAN, sim.py, improve.py,
RESULTS.md, ALL_PORTFOLIOS.md, REPORT.md). v1 (25 EAs) is superseded; its README is kept as
`README-v1-25EA.md.bak` in the evidence folder.

## What is in this folder
- **`EAs/`:** the 17 exact EX5 files used by the tested ledgers (SHA-256 values in `PORTFOLIO.json`).
- **`Sets/`:** 20 SETs. Each is the tested preset plus the tested overrides, with:
  - risk **0.3% = $150 per trade** (`InpRiskPercent`, and the three LTA risk inputs);
  - `InpAdaptivePortfolioControls=false`.
- **`RISK_PROFILE.json`:** the firm rules as modelled, plus the guard profile.

## The 20 EAs to keep
| Group | EAs |
|---|---|
| Strongest contributors (removing them cost the most, in every window) | USDJPY London Open Momentum, 3 Way Gold (watch-only EA), XAU Regime Switch, BTC POC Fibonacci, XAU RSI VWAP, XAU Elliott Wave 1-2-3, DMC Fresh Reaction XAU |
| Useful | Sell Nasdaq 15min, ETH Top Down FVG Liquidity, US100 Selective ORB V3, Nasdaq Overnight, XAU Squeeze Momentum, XAU Trend Progression, ORB Volume Profile, Asia Breakout |
| Neutral / mixed (kept) | US100 ORB New York M30 (0.5R), XAU ORB New York M30 (0.5R), ORB Volume Profile Volume Confirmed, LTA Volume Profile, Nasdaq 5M Candle Momentum |

**Removed:**
- **Drags** (removing them raised income in both 2021–23 and 2023–24): EMA3, XAU Weakness, XAU Slow Trend,
  Gold Overnight Value Area, US100 H1 ORB 13UTC.
- **Earlier exclusions:** News Pulse ×4 (not credible), US30 / US100 hourly (no stop-loss), Gold News V9, DMC Current
  XAU, DMC Fresh Reaction US100, BTC Top Down FVG, XAU ORB London-NY, US100 Month End Flow.

## Risk-management profile (the guard)
| Rule | Value |
|---|---|
| Risk per trade | **min($375, 5% of the remaining trailing room)** → at most **$150** (the room is at most $3,000); cut to fit every limit; skip if under $25 |
| Max total open risk (all stops) | $1,000 |
| Max open risk per symbol | $750 |
| Daily profit cap | No new trades once the day is up **$375** (helps the 20% consistency rule) |
| Daily soft stop (today's realised loss + all open stops) | $1,000 (the firm limit is $1,500) |
| Trailing buffer | Keep $125 above the trailing floor (balance − all open stops) |
| Rewards | Request as soon as eligible |

## Simulated result
Pessimistic model: every open stop hit. Fractional lots. In-sample.
- **Breaches and freezes:** 0% breach and 0% frozen in 3 years.
- **Average trader income** (80% share):
  - about **$580 / month** over 3 years (median $556);
  - first-year history **$775 / month**;
  - $1,000–1,330 / month in the 2023–26 windows;
  - about $210 / month in the weak 2021–23 window.
- **Worst simulated day / week:** −$1,000 / −$1,513.
- **Trading activity:** about 49 trades a month (1.6 a day).

## IMPORTANT — what is NOT done
- **No guard EA enforces this profile yet.** The EAs only size by `InpRiskPercent` (0.3% = $150).
  - The room taper, daily profit cap, daily soft stop, max open risk and trailing buffer need a new guard that tracks a
    **trailing** floor. The existing Calyx guards use a static floor.
  - Running the 20 SETs without that guard has none of these protections. In the as-is test, unguarded and
    Calyx-guarded portfolios breached this firm in 50–100% of 3-year paths.
- **Not installed, nothing changed:** no terminal, account or AutoTrading was touched.
- **Confirm the firm's exact rules:**
  - balance or equity trailing;
  - whether it locks at the start balance;
  - whether withdrawals re-base it;
  - the consistency definition.
