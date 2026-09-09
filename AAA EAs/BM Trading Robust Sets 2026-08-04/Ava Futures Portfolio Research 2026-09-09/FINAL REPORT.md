# Calyx Ava Futures Top 10 — Final Report

Generated 2026-09-09.

## Outcome

- A separate Codex MCP entry named `ava-mt5-mcp` was added for `C:\Program Files\Ava Trade MT5 Terminal\terminal64.exe`. The original CFD MT5 MCP configuration was not changed.
- Ava demo account `100057610` on `Ava-Demo 1-MT5` is connected, trade-enabled, and uses netting mode.
- The `Calyx-Ava-Futures-Top10` profile is installed and running with 10 charts.
- The terminal log confirms all ten experts loaded successfully on their intended timeframes, including the three H4 strategies.
- Every Ava-only EA build uses exactly one broker-minimum contract. It does not force a 1% risk target.
- An Ava-only per-contract ownership guard prevents multiple Calyx EAs from merging or managing one another's net position.
- News Pulse XAU and News Pulse XAG are mandatory members of the profile.
- XAU RSI VWAP was rejected after its futures result turned negative. US100 ORB New York M30 replaced it.

## Installed portfolio and comparison

| EA | Ava history | Ava return | Ava PF | Ava win rate | Ava DD | Ava trades | CFD 3y return | CFD PF | CFD win rate | CFD DD | CFD trades |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| News Pulse XAG | 2024-02-28–2026-09-08 | +90.95% | 32.91 | 73.68% | 1.67% | 19 | +221.19% | 13.41 | 63.16% | 2.52% | 38 |
| News Pulse XAU | 2024-02-28–2026-09-08 | +14.46% | 4.53 | 45.00% | 2.50% | 20 | +55.54% | 9.03 | 64.71% | 1.79% | 34 |
| XAU Trend Progression | 2024-02-28–2026-09-08 | +122.87% | 2.50 | 52.83% | 11.12% | 53 | +72.47% | 2.72 | 62.22% | 5.92% | 90 |
| DMC Fresh Reaction XAU | 2024-02-28–2026-09-08 | +29.25% | 1.39 | 42.86% | 21.84% | 42 | +36.18% | 2.49 | 60.00% | 4.08% | 55 |
| Safe EMA3 | 2024-02-28–2026-09-08 | +97.54% | 1.29 | 59.09% | 39.18% | 66 | +33.56% | 2.30 | 64.94% | 3.95% | 77 |
| XAU ORB London/NY Overlap M30 | 2024-02-28–2026-09-08 | +4.95% | 2.96 | 59.09% | 1.60% | 22 | +28.10% | 2.51 | 56.96% | 3.88% | 79 |
| XAU Elliott Wave 1-2-3 | 2024-02-28–2026-09-08 | +17.35% | 1.15 | 34.00% | 27.52% | 50 | +69.85% | 2.47 | 45.71% | 6.83% | 70 |
| US100 H1 ORB 13UTC | 2023-09-09–2026-09-08 | +88.41% | 1.50 | 53.07% | 14.87% | 179 | +106.20% | 1.94 | 54.14% | 6.81% | 181 |
| Safe XAU Weakness | 2024-02-28–2026-09-08 | +120.65% | 1.61 | 43.33% | 15.23% | 150 | +134.07% | 1.95 | 44.00% | 6.81% | 175 |
| US100 ORB New York M30 | 2023-09-09–2026-09-08 | +51.60% | 2.60 | 48.84% | 5.51% | 43 | +36.94% | 2.15 | 50.79% | 4.77% | 63 |

## Data limits and interpretation

- Nasdaq futures history is the requested full three years and reported 98% MT5 history quality.
- Ava supplies Gold and Silver continuous history only from 2024-02-28. Those comparisons cover about 2.5 years, with reported history quality of 68% for Gold and 65% for Silver. They are provisional demo evidence, not a three-year validation.
- Continuous contracts `GCEc1`, `SIEc1`, and `ENQc1` were used only for historical analysis. The live demo profile uses tradable micro contracts `MGCZ26`, `SILZ26`, and `MNQZ26`.
- Percentage results emulate one micro contract on the USD 10,000 demo balance by scaling the full-contract tester deposit according to the full-to-micro contract multiplier.
- One minimum contract can exceed 1% planned risk. This is intentional under the user's minimum-contract instruction.
- Because the account is netting, a signal is skipped while another Calyx EA owns the same dated contract. This is the safe alternative to allowing one EA to merge with or close another EA's position. A separate account or separately tradable contract is required if every same-symbol signal must execute concurrently.
- The Gold/Silver sample sizes—especially the two News Pulse rows—are small. Demo-forward observation is required before any real-capital decision.

## Rejected futures candidates

| Candidate | Ava return | PF | Win rate | DD | Trades | Decision |
|---|---:|---:|---:|---:|---:|---|
| XAU RSI VWAP | -25.71% | 0.81 | 67.95% | 48.73% | 78 | Rejected: negative expectancy despite high win rate |
| DMC Fresh Reaction US100 | -1.17% | 0.00 | 0.00% | 2.00% | 1 | Rejected: no usable futures sample |
| XAU ORB New York M30 | -0.26% | 0.95 | 41.67% | 11.05% | 12 | Rejected |
| ORB Volume Profile High Win 0.75R | +0.65% | 1.02 | 71.19% | 14.98% | 59 | Rejected: high win rate without useful expectancy |
| US100 Selective ORB V3 | -1.32% | 0.00 | 0.00% | about 1.32% | 1 | Rejected: one losing trade only |

## Operations

- Reusable installer: `INSTALL AVA FUTURES TOP 10 - MINIMUM CONTRACT.bat`.
- Installation record: `LAST AVA FUTURES INSTALL.txt`.
- Current December contracts expire in December 2026. The symbols must be rolled and this profile reinstalled before expiry.
- The normal CFD portfolio, its risk selection, and its MT5 MCP server remain separate and unchanged by the Ava-only deployment.
