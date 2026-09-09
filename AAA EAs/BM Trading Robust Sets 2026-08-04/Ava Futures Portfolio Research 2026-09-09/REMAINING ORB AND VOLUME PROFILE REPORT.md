# Ava remaining ORB and volume-profile review

Generated 2026-09-09 from isolated Ava MT5 Every Tick tests. The active Ava demo profile was not changed during this review.

## Results

| Strategy | Mode | Ava history | Return | PF | Win rate | Max DD | Sharpe | Recovery | Trades | PF 1.40 rule |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| LTA Volume Profile | Standard | 2024-02-28–2026-09-08 | +88.75% | 1.37 | 28.57% | 18.44% | 3.02 | 2.82 | 329 | Fail |
| LTA Volume Profile | Safe | 2024-02-28–2026-09-08 | +79.25% | 1.43 | 31.72% | 18.41% | 3.85 | 2.11 | 186 | Pass |
| ORB Volume Profile | Standard | 2024-02-28–2026-09-08 | -8.43% | 0.78 | 42.37% | 18.55% | -3.44 | -0.41 | 59 | Fail |
| ORB Volume Profile | Volume Confirmed | 2024-02-28–2026-09-08 | -8.87% | 0.64 | 40.00% | 15.21% | -5.00 | -0.54 | 30 | Fail |
| US100 Selective ORB V3 | Standard | 2023-09-09–2026-09-08 | +9.63% | 1.35 | 52.78% | 11.27% | 4.50 | 0.76 | 36 | Fail |

## Decision

- Only **LTA Volume Profile Safe** passes the requested PF 1.40 threshold.
- LTA Safe is the only candidate for a later Ava portfolio addition. Its PF margin is narrow and Gold history quality is 68%, so it should remain demo-only.
- Do not add ORB Volume Profile Standard, Volume Confirmed, or US100 Selective ORB V3 to Ava.
- Keep the already active ORB selections: XAU London/NY Overlap M30, US100 H1 ORB 13UTC, and US100 New York M30.

## Test context

- Gold tests used continuous `GCEc1` history; the corresponding live micro contract is `MGCZ26`.
- Nasdaq used continuous `ENQc1` history; the corresponding live micro contract is `MNQZ26`.
- Results use Ava-only EA builds fixed to one broker-minimum contract and a scaled tester deposit for micro-contract economics.
- Gold history quality is 68%; Nasdaq history quality is 98%.
