# Full Ava ORB comparison against CFD

Generated 2026-09-09. This consolidates every ORB currently exposed in the Calyx website catalog. No active Ava chart was changed during this comparison.

## Common performance comparison

| ORB | Market | Test dates | CFD return | Ava return | CFD PF | Ava PF | CFD win rate | Ava win rate | CFD DD | Ava DD | CFD trades | Ava trades | Ava decision |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| US100 ORB New York M30 | Nasdaq | 2023-09-09–2026-09-08 | +36.94% | +51.60% | 2.15 | **2.60** | 50.79% | 48.84% | 4.77% | 5.51% | 63 | 43 | Keep |
| US100 H1 ORB 13UTC | Nasdaq | 2023-09-09–2026-09-08 | +106.20% | +88.41% | 1.94 | **1.50** | 54.14% | 53.07% | 6.81% | 14.87% | 181 | 179 | Keep |
| US100 Selective ORB V3 | Nasdaq | 2023-09-09–2026-09-08 | +6.11% | +9.63% | 2.17 | 1.35 | 55.00% | 52.78% | 3.66% | 11.27% | 20 | 36 | Reject below PF 1.40 |
| XAU ORB London/NY Overlap M30 | Gold | 2024-02-28–2026-09-08 | +28.10% | +4.95% | 2.51 | **2.96** | 56.96% | 59.09% | 3.88% | 1.60% | 79 | 22 | Keep, provisional |
| XAU ORB New York M30 | Gold | 2024-02-28–2026-09-08 | +13.41% | -0.26% | 2.36 | 0.95 | 49.02% | 41.67% | 3.43% | 11.05% | 51 | 12 | Reject |
| ORB Volume Profile High Win 0.75R | Gold | 2024-02-28–2026-09-08 | +23.35% | +0.65% | 1.48 | 1.02 | 70.18% | 71.19% | 5.32% | 14.98% | 171 | 59 | Reject |
| ORB Volume Profile Standard | Gold | 2024-02-28–2026-09-08 | +49.48% | -8.43% | 1.69 | 0.78 | 46.78% | 42.37% | 5.85% | 18.55% | 171 | 59 | Reject |
| ORB Volume Profile Volume Confirmed | Gold | 2024-02-28–2026-09-08 | +25.92% | -8.87% | 2.01 | 0.64 | 45.59% | 40.00% | 5.64% | 15.21% | 68 | 30 | Reject |

## Ava risk-adjusted metrics

| ORB | Ava Sharpe | Ava recovery | History quality |
|---|---:|---:|---:|
| US100 ORB New York M30 | 17.25 | 6.06 | 98% |
| US100 H1 ORB 13UTC | 6.79 | 3.70 | 98% |
| US100 Selective ORB V3 | 4.50 | 0.76 | 98% |
| XAU ORB London/NY Overlap M30 | 31.40 | 3.06 | 68% |
| XAU ORB New York M30 | -0.12 | -0.02 | 68% |
| ORB Volume Profile High Win 0.75R | 0.76 | 0.04 | 68% |
| ORB Volume Profile Standard | -3.44 | -0.41 | 68% |
| ORB Volume Profile Volume Confirmed | -5.00 | -0.54 | 68% |

## Finding

The Nasdaq claim is supported by these tests: all three Nasdaq ORBs were profitable on Ava, and two passed the PF 1.40 admission rule. The Gold ORBs did not transfer as consistently; only the London/New York overlap configuration passed.

The retained Ava ORB set is therefore:

1. US100 ORB New York M30.
2. US100 H1 ORB 13UTC.
3. XAU ORB London/NY Overlap M30, kept as provisional because Gold history quality is only 68% and the sample is 22 trades.

These three already exist in the active Ava profile. No new ORB should be added from the rejected rows.

## Test interpretation

- Nasdaq tests use `ENQc1` continuous history and 98% MT5 history quality. Live installation maps to the micro contract `MNQZ26`.
- Gold tests use `GCEc1` continuous history and 68% MT5 history quality. Live installation maps to `MGCZ26`.
- Ava-only EA builds use one broker-minimum contract. The full-contract tester deposit is scaled so the percentages represent the economics of one micro contract on the USD 10,000 Ava demo account.
- Sharpe values from the MT5 reports are included as reported, but they should not be compared blindly across strategies with very different trade counts.
