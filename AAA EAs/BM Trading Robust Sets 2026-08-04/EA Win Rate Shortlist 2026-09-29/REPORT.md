# EA win-rate and profit-factor review

29 September 2026 — results only; no EA, SET, installation, website, MT5 session or trading account changed.

## Decision

For your preference, the **most interesting high-win research variants are ORB Volume Profile 0.75R and US100 H1 ORB 1R + ADX**. They need current-build / out-of-sample checks before promotion. **EMA3's newer audited default and Nasdaq Overnight are the more practical existing-version shortlist.** Gold Overnight wins more often but its longer record is weak. This is a research shortlist, not an instruction to trade or a forecast of streaks.

- ORB Volume Profile 0.75R: 70.59% wins, PF 1.63, 51 yearly trades, max 7 wins / 2 losses; three-year 70.18%, PF 1.48, 171 trades, max 11 / 3. Retained old version, not a current catalogue default.
- US100 H1 ORB 1R + ADX25: 68.75%, PF 2.03, 48 trades, max 5 / 3. ADX20: 68.42%, PF 2.03, 57 trades, max 5 / 3. The extra 0.33 percentage point is not meaningful evidence that ADX25 is better than ADX20; both were searched on the same year.
- EMA3: newer default audit 65.12%, PF 1.73, 43 trades, max 7 / 3. Old Safe mode is numerically better at 70.27%, PF 2.71, 37 trades, max 9 / 4, but has no freshly verified current Safe configuration.
- Nasdaq Overnight: newer audit 60.81%, PF 1.63, 74 trades, max 10 / 4.
- Gold Overnight raw: newer 73.50%, PF 1.52, 200 trades, max 11 / 3; raw three-year PF 1.15 and five-year PF 1.04 weaken the case for relying on it.

## What was compared

34 current catalogue EAs; 45 saved Standard/Safe/Dynamic variants; 90 one-/three-year ledgers, plus 14 newer native audit ledgers and named related research. Catalogue membership is not proof that every EA is currently running on an MT5 chart. This is **not** an exhaustive search of all abandoned research folders or a new optimization/backtest.

Use PF ≥ 1.20 as the screen. Among cached modes passing it, prefer highest **net** win rate; ties prefer shorter losing streak and then PF. Replace stale default-mode figures with newer dated native tests when available, even if worse. Different Safe/research modes remain distinct and are explicitly labelled. Three-year results include the latest year: not independent validation. Test end dates differ between late August and late September 2026.

Wins and streaks are recalculated from closed trades after recorded commission/swap. Zero-net trades reset both streaks and remain in the win-rate denominator. PF* is the lower of the reported PF and net-ledger PF, a conservative screen; this preserves the familiar tester figure while not concealing a cost-adjusted failure. Full original and recalculated values are retained in INVENTORY.json. Some reported MT5 win rates count trades that are not net winners after costs: e.g. latest USDJPY 49.63% becomes 43.70% net. None of these figures includes a newly imposed extra-slippage stress.

Streaks are **historical maxima**, not forecasts or guaranteed loss limits. Risk/lot rounding differs among standalone tests, usually nominal 1%; these are not the 0.5% FTMO daily-stop portfolio results, pass probabilities, or payout projections. “Safe” is a saved mode name, not a safety guarantee.

Evidence labels: **N** newer native audit inputs; **M** cached expert and SET exactly match current catalogue fingerprints; **S** older saved mode without current-build proof; **R** related unpromoted/retained research. A different hash means not byte-identical, not necessarily changed strategy logic. Most older cache binaries differ from the current files. Generic 98–100% history quality does not prove 100% historical real ticks; newer yearly audits report about 73% real ticks and generated fallback before January 2026.

## All 34 catalogue EAs

The named mode is a candidate to review, not an automatic deployment recommendation. Read the separate research alternatives below for ORB and Slow Trend.

| EA / version | Win rate, net | PF* | Trades | Max wins / losses | Evidence / comment |
|---|---:|---:|---:|---:|---|
| Gold Overnight Value Area — Audited inputs, Sep 27 | 73.50% | 1.52 | 200 | 11 / 3 | N; Pass. High win rate but raw 3y PF 1.15 and 5y PF 1.04. Latest native audit has invalid-stop/market-closed messages. Not a robust FTMO selection. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/FTMO Fourteen EA Study 2026-09-27/native/gold-overnight-value-area/run.json>) |
| LTA Volume Profile — Safe | 32.63% | 1.42 | 236 | 5 / 10 | S; Pass. Saved historical mode; current-code reproduction required. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/EA store/data/evidence-cache/v1/products/lta-volume-profile/safe/1y.json>) |
| BTC Top Down FVG Liquidity — Standard | 50.00% | 1.92 | 26 | 3 / 2 | S; Pass. Saved historical mode; current-code reproduction required. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/EA store/data/evidence-cache/v1/products/btc-top-down-fvg-liquidity/standard/1y.json>) |
| BTC POC Fibonacci — Standard | 26.92% | 1.40 | 26 | 3 / 9 | S; Pass. Saved historical mode; current-code reproduction required. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/EA store/data/evidence-cache/v1/products/btc-poc-fibonacci/standard/1y.json>) |
| ETH Top Down FVG Liquidity — Standard | 42.31% | 1.65 | 26 | 3 / 4 | S; Pass. Saved historical mode; current-code reproduction required. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/EA store/data/evidence-cache/v1/products/eth-top-down-fvg-liquidity/standard/1y.json>) |
| ORB Volume Profile — Standard | 45.10% | 1.91 | 51 | 7 / 6 | S; Pass. Saved historical mode; current-code reproduction required. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/EA store/data/evidence-cache/v1/products/orb-volume-profile/standard/1y.json>) |
| ORB Volume Profile Volume Confirmed — Standard | 47.83% | 2.88 | 23 | 3 / 3 | S; Pass. Saved historical mode; current-code reproduction required. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/EA store/data/evidence-cache/v1/products/orb-volume-profile-volume-confirmed/standard/1y.json>) |
| XAU ORB New York M30 — Standard | 45.45% | 3.04 | 11 | 2 / 3 | S; Pass. Saved historical mode; current-code reproduction required. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/EA store/data/evidence-cache/v1/products/xau-orb-new-york-m30/standard/1y.json>) |
| XAU ORB London NY Overlap M30 — Audited inputs, Sep 27 | 40.00% | 1.90 | 25 | 3 / 5 | N; Pass. Newer native study; standalone 1% nominal sizing, not the daily-governed FTMO portfolio. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/FTMO Fourteen EA Study 2026-09-27/native/xau-orb-london-ny-overlap-m30/run.json>) |
| US100 ORB New York M30 — Standard | 48.15% | 1.68 | 27 | 4 / 4 | S; Pass. Saved historical mode; current-code reproduction required. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/EA store/data/evidence-cache/v1/products/us100-orb-new-york-m30/standard/1y.json>) |
| US100 H1 ORB 13UTC — Audited inputs, Sep 27 | 51.35% | 1.64 | 74 | 7 / 4 | N; Pass. Newer native study; standalone 1% nominal sizing, not the daily-governed FTMO portfolio. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/FTMO Fourteen EA Study 2026-09-27/native/us100-h1-orb-13utc/run.json>) |
| US100 Selective ORB V3 — Standard | 80.00% | 1.60 | 5 | 2 / 1 | S; Pass. 80% is only four wins from five trades. Not enough evidence to nominate as best. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/EA store/data/evidence-cache/v1/products/us100-selective-orb-v3/standard/1y.json>) |
| Asia Breakout — Standard | 45.83% | 1.72 | 72 | 5 / 6 | S; Pass. Saved historical mode; current-code reproduction required. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/EA store/data/evidence-cache/v1/products/asia-breakout/standard/1y.json>) |
| DMC Current XAU — Audited inputs, Sep 27 | 41.88% | 1.24 | 117 | 5 / 7 | N; Pass. Newer native study; standalone 1% nominal sizing, not the daily-governed FTMO portfolio. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/FTMO Fourteen EA Study 2026-09-27/native/dmc-current-xau/run.json>) |
| DMC Fresh Reaction XAU — Standard | 46.67% | 1.90 | 15 | 2 / 3 | S; Pass. Saved historical mode; current-code reproduction required. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/EA store/data/evidence-cache/v1/products/dmc-fresh-reaction-xau/standard/1y.json>) |
| DMC Fresh Reaction US100 — Audited inputs, Sep 27 | 54.55% | 1.08 | 11 | 2 / 2 | N; Below 1.20. Newer PF 1.08 fails. Old 66.67% / PF1.88 / 12 trades should not be presented as current proof. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/FTMO Fourteen EA Study 2026-09-27/native/dmc-fresh-reaction-us100/run.json>) |
| EMA3 — Safe | 70.27% | 2.71 | 37 | 9 / 4 | S; Pass. Old Safe mode: no distinct current Safe SET exposed by catalogue. Newer default audit: 65.12% / PF 1.73 / 43 trades / W7-L3; does not revalidate this Safe mode. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/EA store/data/evidence-cache/v1/products/ema3/safe/1y.json>) |
| XAU Weakness — Safe | 42.35% | 1.97 | 85 | 5 / 5 | S; Pass. Saved historical mode; current-code reproduction required. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/EA store/data/evidence-cache/v1/products/xau-weakness/safe/1y.json>) |
| Nasdaq Overnight — Audited inputs, Sep 27 | 60.81% | 1.63 | 74 | 10 / 4 | N; Pass. Newer native study; standalone 1% nominal sizing, not the daily-governed FTMO portfolio. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/FTMO Fourteen EA Study 2026-09-27/native/nasdaq-overnight/run.json>) |
| Nasdaq 5M Candle Momentum — DI + wide stop + ATR6 trail | 51.40% | 1.48 | 179 | 9 / 6 | M; Pass. Fingerprint-matched current research deployment; explicitly not pipeline-approved. 9-win/6-loss streaks are past observations only. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/EA store/data/evidence-cache/v1/products/nasdaq-5m-candle-momentum/dynamic/1y.json>) |
| Sell Nasdaq 15min — Safe | 46.15% | 1.32 | 52 | 4 / 4 | S; Pass. Safe wins tie-break for shorter loss streak: 4 vs Dynamic 6. Dynamic has same 46.15% win rate, PF 1.44, W4/L6, DD7.81%. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/EA store/data/evidence-cache/v1/products/sell-nasdaq-15min/safe/1y.json>) |
| USDJPY London Open Momentum — Audited inputs, Sep 27 | 43.70% | 1.32 | 135 | 8 / 13 | N; Pass. Newer native study; standalone 1% nominal sizing, not the daily-governed FTMO portfolio. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/FTMO Fourteen EA Study 2026-09-27/native/usdjpy-london-open-momentum/run.json>) |
| XAU Squeeze Momentum Standard — Safe | 64.29% | 3.27 | 14 | 6 / 2 | S; Pass. Only 14 yearly trades. Newer Standard audit: 38.89% / PF 1.27 / 18 trades / W4-L6; Safe mode not freshly retested. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/EA store/data/evidence-cache/v1/products/xau-squeeze-momentum-standard/safe/1y.json>) |
| News Pulse XAU — Audited inputs, Sep 27 | 66.67% | 11.47 | 39 | 8 / 4 | N; Pass. Experimental news execution; exceptional tester PF is not live-fill evidence. Keep outside preferred shortlist pending execution validation. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/FTMO Fourteen EA Study 2026-09-27/native/news-pulse-xau/run.json>) |
| Gold News V9 Direction | — | — | — | — | No 1y trade ledger in catalogue evidence. |
| News Pulse XAG — Standard | 50.00% | 12.41 | 34 | 3 / 5 | S; Pass. Experimental news execution; exceptional tester PF is not live-fill evidence. Keep outside preferred shortlist pending execution validation. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/EA store/data/evidence-cache/v1/products/news-pulse-xag/standard/1y.json>) |
| News Pulse BTC — Standard | 65.38% | 11.52 | 52 | 9 / 3 | S; Pass. Experimental news execution; exceptional tester PF is not live-fill evidence. Keep outside preferred shortlist pending execution validation. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/EA store/data/evidence-cache/v1/products/news-pulse-btc/standard/1y.json>) |
| News Pulse EURUSD — Standard | 56.52% | 12.94 | 46 | 5 / 4 | S; Pass. Experimental news execution; exceptional tester PF is not live-fill evidence. Keep outside preferred shortlist pending execution validation. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/EA store/data/evidence-cache/v1/products/news-pulse-eurusd/standard/1y.json>) |
| XAU RSI VWAP — Audited inputs, Sep 27 | 70.83% | 1.18 | 48 | 7 / 3 | N; Below 1.20. Newer PF 1.18 is borderline below 1.20; old cache PF1.38 is not a substitute for this result. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/FTMO Fourteen EA Study 2026-09-27/native/xau-rsi-vwap/run.json>) |
| XAU Trend Progression — Audited inputs, Sep 27 | 54.55% | 2.51 | 22 | 5 / 3 | N; Pass. Newer native study; standalone 1% nominal sizing, not the daily-governed FTMO portfolio. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/FTMO Fourteen EA Study 2026-09-27/native/xau-trend-progression/run.json>) |
| XAU Elliott Wave 1-2-3 — Standard | 54.17% | 3.15 | 24 | 6 / 4 | S; Pass. Saved historical mode; current-code reproduction required. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/EA store/data/evidence-cache/v1/products/xau-elliott-wave-1-2-3/standard/1y.json>) |
| XAU Slow Trend — Latest baseline, Sep29 | 17.95% | 0.94 | 39 | 2 / 14 | N; Below 1.20. Fails PF gate. ADX research reaches 22.22% / PF1.31 but 15 losses in a row and a losing recent six months; unsuitable for high-win preference. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/XAU Slow Trend Filter Review 2026-09-29/SUMMARY.json>) |
| XAU Regime Switch — Standard | 30.56% | 2.09 | 36 | 3 / 9 | S; Pass. Saved historical mode; current-code reproduction required. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/EA store/data/evidence-cache/v1/products/xau-regime-switch/standard/1y.json>) |
| US100 Month End Flow — Audited inputs, Sep 27 | 47.06% | 1.53 | 34 | 3 / 3 | N; Pass. Newer native study; standalone 1% nominal sizing, not the daily-governed FTMO portfolio. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/FTMO Fourteen EA Study 2026-09-27/native/us100-month-end-flow/run.json>) |

## Related versions that directly address your preference

| EA / version | Win rate, net | PF* | Trades | Max wins / losses | Evidence / comment |
|---|---:|---:|---:|---:|---|
| ORB Volume Profile — Retained 0.75R high-win | 70.59% | 1.63 | 51 | 7 / 2 | R; Pass. Not in current catalogue. 3y: 70.18%, reported PF1.48, 171 trades, W11/L3. Old binary requires revalidation. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/EA store/data/evidence-cache/v1/products/orb-volume-profile-high-win-0-75r/standard/1y.json>) |
| US100 H1 ORB 13UTC — H1-RR1-adx25 | 68.75% | 2.03 | 48 | 5 / 3 | R; Pass. Selected from 25 configurations on the same year; no untouched validation. ADX25 has slightly higher WR; ADX20 has 57 vs48 trades with similar PF. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/US100 H1 ORB ADX RR1 Research 2026-09-23/NATIVE_RESULTS.json>) |
| US100 H1 ORB 13UTC — H1-RR1-adx20 | 68.42% | 2.03 | 57 | 5 / 3 | R; Pass. Selected from 25 configurations on the same year; no untouched validation. ADX25 has slightly higher WR; ADX20 has 57 vs48 trades with similar PF. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/US100 H1 ORB ADX RR1 Research 2026-09-23/NATIVE_RESULTS.json>) |
| XAU Slow Trend — ADX20 + DI + rising ADX | 22.22% | 1.31 | 45 | 3 / 15 | R; Pass. 22.22% wins and 15 consecutive losses: poor match for requested style. Latest six months PF0.47 and negative return. Not approved. [source](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/XAU Slow Trend Filter Review 2026-09-29/SUMMARY.json>) |

## Versions I would not elevate solely on their win rate

- US100 Selective ORB V3:80% is4 wins from only5 trades; its three-year record has only20 trades.
- XAU Squeeze Safe:64.29% andPF3.27 but only14 trades in a year /38 over three years. The latest Standard test is much weaker and does not validate Safe.
- XAU RSI VWAP: latestPF1.18 is close to your request but below the strict screen. No rounding up to a pass.
- DMC Fresh US100: latestPF1.08 fails despite the old cache showing1.88.
- All News Pulse: reportedPF11–14 is attractive on paper, but highly execution-sensitive. Keep separate until replay/live execution evidence supports it. GoldNewsV9 has no comparable retained1y ledger here.
- XAU Slow Trend: latest baseline loses; filtered versions are low-win and still fail the latest six months. Long losing streaks conflict with your requested style.
- LTA, BTC POC Fibonacci and XAU Regime Switch can clearPF1.2 while having low win rates and long losing streaks. They are not the best psychological fit for this request.

## Longer-record context for the selected saved modes

| EA | Saved mode | 3y net win rate | Reported PF | Trades | Max wins / losses |
|---|---|---:|---:|---:|---:|
| Gold Overnight Value Area | standard | 69.22% | 1.15 | 601 | 11 / 5 |
| LTA Volume Profile | safe | 31.35% | 1.33 | 437 | 5 / 15 |
| BTC Top Down FVG Liquidity | standard | 41.57% | 1.29 | 89 | 3 / 7 |
| BTC POC Fibonacci | standard | 33.80% | 1.52 | 71 | 3 / 9 |
| ETH Top Down FVG Liquidity | standard | 43.18% | 1.72 | 44 | 4 / 4 |
| ORB Volume Profile | standard | 45.61% | 1.69 | 171 | 7 / 6 |
| ORB Volume Profile Volume Confirmed | standard | 44.12% | 2.01 | 68 | 6 / 7 |
| XAU ORB New York M30 | standard | 47.06% | 2.36 | 51 | 3 / 5 |
| XAU ORB London NY Overlap M30 | standard | 56.96% | 2.51 | 79 | 7 / 5 |
| US100 ORB New York M30 | standard | 50.79% | 2.15 | 63 | 5 / 4 |
| US100 H1 ORB 13UTC | standard | 53.59% | 1.94 | 181 | 7 / 5 |
| US100 Selective ORB V3 | standard | 55.00% | 2.17 | 20 | 2 / 2 |
| Asia Breakout | standard | 47.33% | 1.57 | 131 | 5 / 6 |
| DMC Current XAU | standard | 40.80% | 1.27 | 250 | 6 / 9 |
| DMC Fresh Reaction XAU | standard | 60.00% | 2.49 | 55 | 6 / 3 |
| DMC Fresh Reaction US100 | standard | 65.22% | 1.99 | 46 | 8 / 2 |
| EMA3 | safe | 64.94% | 2.30 | 77 | 16 / 4 |
| XAU Weakness | safe | 43.09% | 1.88 | 181 | 5 / 9 |
| Nasdaq Overnight | standard | 55.62% | 1.29 | 178 | 10 / 7 |
| Nasdaq 5M Candle Momentum | dynamic | 47.76% | 1.40 | 536 | 9 / 9 |
| Sell Nasdaq 15min | safe | 45.91% | 1.35 | 159 | 5 / 5 |
| USDJPY London Open Momentum | standard | 47.33% | 1.44 | 412 | 6 / 13 |
| XAU Squeeze Momentum Standard | safe | 65.79% | 3.89 | 38 | 7 / 4 |
| News Pulse XAU | standard | 65.29% | 11.12 | 121 | 8 / 4 |
| News Pulse XAG | standard | 46.67% | 10.89 | 90 | 5 / 6 |
| News Pulse BTC | standard | 44.22% | 14.26 | 147 | 9 / 14 |
| News Pulse EURUSD | standard | 50.34% | 9.64 | 147 | 5 / 9 |
| XAU RSI VWAP | standard | 76.87% | 1.74 | 134 | 14 / 3 |
| XAU Trend Progression | standard | 62.22% | 2.72 | 90 | 6 / 3 |
| XAU Elliott Wave 1-2-3 | standard | 45.71% | 2.47 | 70 | 5 / 6 |
| XAU Slow Trend | standard | 24.48% | 1.78 | 143 | 3 / 10 |
| XAU Regime Switch | standard | 30.77% | 1.93 | 117 | 3 / 9 |
| US100 Month End Flow | standard | 50.00% | 1.61 | 104 | 4 / 4 |

## Checks and limits

All 90 cached ledgers matched their reported trade counts and cash totals within two cents; all saved maximum streaks matched. All 14 newer audit ledgers matched their native counts and cash. Win-rate differences after costs are documented, not ignored. Research ORB 1R ledger counts and cash were checked against its native summaries. Source paths, hashes, native flags and alternative modes are preserved in INVENTORY.json; source inputs are not altered.

Historical selection introduces hindsight and multiple-testing risk. Higher win rate can be purchased with smaller wins relative to losses; it is not automatically a better strategy. Combining several gold bots can create concentrated exposure. Further validation should compare the exact candidate builds on common dates, realistic costs, unseen/forward data and the actual FTMO portfolio rules before any live change.

General limitation: [CFTC trading-system advisory](https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/fraudadv_tradingsystem.html) explains why hypothetical system results may differ from actual trading. All numbers here are local historical evidence, not broker-certified live returns or guaranteed future outcomes.
