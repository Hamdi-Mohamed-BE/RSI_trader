# Gold Band Wave: raw test, best trade and FTMO simulations (frozen 2026-11-10, before any result)

Owner request: test the pasted clip's "Gold Band Wave" strategy, try to find its best trade in the history, and simulate FTMO 1-Step and 2-Step at 0.5 / 0.75 / 1% risk. The clip is data, not evidence.

## Clip rules and my declared reading
- **Chart:** XAUUSD H4.
- **Trend:** buy only with price above the 200 moving average; sell only below it. Declared: SMA(200) of the close, checked on the signal bar's close.
- **The wave:** the clip does not name the indicator. Declared: John Bollinger's **BBTrend**, which matches "two Bollinger Bands, shown as a wave under the chart":
  - `(|lowerShort - lowerLong| - |upperShort - upperLong|) / middleShort x 100`;
  - short band BB(20, 2), long band BB(50, 2), close prices.
- **"The line that follows it":** declared SMA(9) of BBTrend.
- **Entry:** buy when BBTrend crosses above its signal line on a closed H4 bar (and price is above SMA200); sell is the mirror. Market entry at the next bar open.
- **Stop:** 2 x the average candle size. Declared: ATR(14) on H4 at the signal bar.
- **No target:** close a long when BBTrend crosses back below the signal line, a short on the opposite cross.
  - If the closing cross also qualifies as an entry the other way (price on that side of SMA200), the reverse trade opens on the same bar.
- **One position at a time.**
- **Risk:** the clip uses $1,500 per trade on $100k = 1.5%. Runs at 1% (our standard) and at 1.5% (the clip's sizing).

## Data
- Exness XAUUSD, native MT5 Model 4 (every tick), 150 ms, $10k (and $100k for the clip-sized run).
- Ticks before 2026 are generated, not recorded.
- Windows from `data_split.research_split('2019-01-01', '2026-11-10')`:
  - development to 2023-11-10;
  - validation to 2024-11-10;
  - OOS to 2026-11-10 (gold has been studied over these years before, so not untouched).
- Also: the clip's "five years", 2021-11-10 to 2026-11-10, and the last year.
- Buy and hold XAUUSD on the same windows (pipeline rule).

## Variants
| Key | Rule |
|---|---|
| GBW | The rules above, 1% risk, $10k |
| GBW_CLIP | The same rules at 1.5% on $100k (the clip's sizing) |
| GBW_NOTREND | Control: no SMA200 filter |
| GBW_RAND | Control: same signal times and exits, random direction |

## Raw gate
All of these must hold:
1. PF at least 1.15.
2. Positive in development, validation and OOS.
3. Positive without its 5 best days.
4. Beats both controls.
5. Three-way Monte Carlo (resample red ≤5%, randomize red ≤10%).

## Best trade
List the largest winners (R and $ at the clip's $1,500 risk). Look for one near +$12,000 (about +8R) and give its dates.

## FTMO simulations (owner asked for them regardless of the raw result)
- **Stream:** the long-history runner with intratrade marks (2021-10-06 to 2026-10-06, the window the frozen prop engines use).
- **Engines:** frozen FTMO 2-step (`prop_select.challenge`) and FTMO 1-Step (`f1_profile` guard; firm rules only with no guard), $100k, MC 2,000 paths.
- **Risk:** 0.5 / 0.75 / 1%.
- **Guard and no guard:** both, as for the other portfolios.

These are in-sample replays, not forecasts. Nothing is installed or deployed by this study.
