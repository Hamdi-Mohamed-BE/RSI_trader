# 3 Way Volume Profile — raw test report (2026-09-26)

Source: Pips Beyond Borders volume-profile video (transcript supplied by the user): Way 1 POC bounce, Way 2 value-area
reversal, Way 3 value-area breakout, and the three combined. Raw rules and our fill-in choices are in `run-config.json`
(fixed before testing). Standard raw-test format: M15, 8 assets, last year (2025-09-26 → 2026-09-26), full metric table,
balance graph (`balance_curves.png`), survivor list. Research only; nothing deployed. Full tables: `RESULTS.md` / `RESULTS.csv`.

## Setup
EA `EA/3 Way Volume Profile Research EA.mq5` (0 errors / 0 warnings); isolated tester, Exness-MT5Trial16, $10,000, 1% risk,
Model 4 (real ticks from 2026-01; bars-generated before), 150 ms delay; 32 native runs, all valid; 18 "[Market closed]"
journal lines only. Smoke test confirmed all three setups fire and Monday uses Friday's profile.

## Survivors for the optimization stage (return > 0, PF ≥ 1.15, ≥ 30 trades, consistency ≥ 50%, equity DD ≤ 20%)

| Asset / way | Trades (/mo, /day) | Return | PF | Win | Consistency | Sharpe | Max bal DD / eq DD |
|---|---|---|---|---|---|---|---|
| BTCUSD — VA reversal | 208 (17.3, 0.80) | +50.5% | 1.29 | 41% | 62% | 1.87 | 10.3% / 11.2% |
| USDJPY — 3 Way combined | 164 (13.7, 0.63) | +39.7% | 1.29 | 41% | 62% | 1.74 | 15.1% / 16.6% |
| BTCUSD — VA breakout | 144 (12.0, 0.55) | +22.2% | 1.20 | 39% | 62% | 1.16 | 12.4% / 13.5% |
| XAUUSD — VA breakout | 78 (6.5, 0.30) | +19.8% | 1.30 | 41% | 54% | 1.20 | 12.9% / 13.4% |

Near misses (worth a look but not promoted): USDJPY breakout (+17.6%, PF 1.28, consistency 46%), XAU combined (+27.9%,
PF 1.16, equity DD 23.6%), BTC combined (+34.3%, PF 1.14), USTEC POC bounce (+6.8%, PF 1.22, 46 trades).

## Findings
1. No single way works everywhere. POC bounce is rare (2–5 trades/month) and weak; the value-area reversal works on BTC
   but loses badly on GBPJPY/XAG/USTEC; the breakout is the most consistent way (positive on XAU, BTC, USDJPY, GBPJPY).
2. The combined system is not automatically better: it only survives on USDJPY; elsewhere a losing way drags it down.
3. US100 fails every way except a small POC-bounce near miss.
4. This is one year of mostly bars-generated history (real ticks only from 2026-01) with ~13 calendar months: survivors
   are candidates, not proof. The optimization stage (PIPELINE.md) uses the full history with a dev/validation/holdout
   split and Monte Carlo before anything could be promoted.
