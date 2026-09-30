# Nasdaq 5M — current claude_eas vs QUANT_LAB-style management

USTEC, isolated MT5 tester (Exness-MT5Trial16), $10,000, 1% risk, M5, Model 4 (real ticks from 2026-01), 150 ms delay. Windows end 2026-09-25 (includes the video week). Same entry rule in every variant; only stop/target/trail/holding differ.

| Variant | CURRENT: Current claude_eas version (production DI EX5 + installed SET): 4 ATR stop, 2.5R target, flat 15:55 NY | QL: QUANT_LAB-style: 0.60% stop, no target, stop trails EMA(200) M5 from +0.5R, held overnight/weekend | QL_ATR: QUANT_LAB-style with our existing ATR trail (6 ATR from +1R) instead of the MA trail | WIDE: Only the wider 0.60% stop (2.5R target and 15:55 NY close kept) |

## 6m (2026.03.25 → 2026.09.25)

| Variant | Trades | Return | PF | Win | Max DD | Avg W/L streak (max) | Avg hold h (max) | Held >8h | Swap | Best trade (× median loss) |
|---|---:|---:|---:|---:|---:|---|---|---:|---:|---:|
| CURRENT | 92 | +17.47% | 1.30 | 42.4% | 10.49% | 1.6/2.2 (3/10) | 4.1 (59) | 2% | -56 | 2.6× |
| QL | 83 | +22.95% | 1.65 | 50.6% | 8.04% | 1.8/1.8 (5/3) | 13.3 (91) | 39% | -166 | 5.3× |
| QL_ATR | 89 | +18.97% | 1.37 | 48.3% | 6.56% | 1.8/1.9 (6/6) | 13.8 (96) | 36% | -157 | 5.2× |
| WIDE | 92 | +24.92% | 1.53 | 50.0% | 6.17% | 1.9/2.0 (6/4) | 5.3 (61) | 3% | -28 | 2.7× |

## 1y (2025.09.25 → 2026.09.25)

| Variant | Trades | Return | PF | Win | Max DD | Avg W/L streak (max) | Avg hold h (max) | Held >8h | Swap | Best trade (× median loss) |
|---|---:|---:|---:|---:|---:|---|---|---:|---:|---:|
| CURRENT | 190 | +50.60% | 1.38 | 43.7% | 10.90% | 1.9/2.5 (11/10) | 5.0 (73) | 5% | -156 | 2.7× |
| QL | 172 | +37.96% | 1.49 | 48.8% | 8.76% | 2.0/2.1 (8/7) | 12.9 (146) | 40% | -334 | 7.4× |
| QL_ATR | 179 | +55.45% | 1.48 | 51.4% | 10.06% | 2.1/2.0 (9/6) | 14.4 (96) | 40% | -385 | 5.5× |
| WIDE | 190 | +41.22% | 1.40 | 50.0% | 10.81% | 2.1/2.1 (11/11) | 7.0 (78) | 7% | -108 | 2.9× |

## 3y (2023.09.25 → 2026.09.25)

| Variant | Trades | Return | PF | Win | Max DD | Avg W/L streak (max) | Avg hold h (max) | Held >8h | Swap | Best trade (× median loss) |
|---|---:|---:|---:|---:|---:|---|---|---:|---:|---:|
| CURRENT | 576 | +133.59% | 1.29 | 42.2% | 10.88% | 1.8/2.5 (11/12) | 4.5 (80) | 4% | -409 | 4.3× |
| QL | 527 | +83.03% | 1.32 | 45.9% | 17.30% | 1.8/2.2 (12/11) | 14.4 (146) | 42% | -1205 | 11.5× |
| QL_ATR | 536 | +162.16% | 1.40 | 47.8% | 10.06% | 2.0/2.2 (9/9) | 14.9 (104) | 44% | -1560 | 21.4× |
| WIDE | 575 | +76.88% | 1.25 | 47.1% | 19.38% | 1.8/2.1 (11/11) | 6.9 (80) | 6% | -295 | 4.4× |

## 5y (2021.09.25 → 2026.09.25)

| Variant | Trades | Return | PF | Win | Max DD | Avg W/L streak (max) | Avg hold h (max) | Held >8h | Swap | Best trade (× median loss) |
|---|---:|---:|---:|---:|---:|---|---|---:|---:|---:|
| CURRENT | 968 | +180.24% | 1.22 | 40.7% | 10.88% | 1.7/2.5 (11/12) | 4.4 (81) | 4% | -532 | 5.6× |
| QL | 907 | +81.43% | 1.18 | 43.3% | 28.79% | 1.8/2.4 (12/11) | 12.2 (146) | 36% | -1844 | 11.4× |
| QL_ATR | 923 | +212.72% | 1.29 | 44.2% | 24.07% | 1.9/2.4 (9/9) | 12.1 (104) | 37% | -2548 | 23.2× |
| WIDE | 969 | +104.73% | 1.18 | 44.0% | 24.55% | 1.8/2.3 (11/14) | 5.8 (81) | 5% | -428 | 4.7× |

## Parity

```
{
 "production_trades": 190,
 "research_trades": 190,
 "identical_entries_exits": true,
 "production_net": 5059.88,
 "research_net": 5059.88
}
```
