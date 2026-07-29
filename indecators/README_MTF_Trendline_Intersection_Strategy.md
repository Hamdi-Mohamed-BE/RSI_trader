# MTF Trendline Intersection Strategy [Codex]

Files:

- `MTF_Trendline_Intersection_Strategy_v6.pine` - TradingView Pine Script v6 indicator.
- `README_MTF_Trendline_Intersection_Strategy.md` - this guide.

## What It Does

This indicator performs a top-down trendline analysis using up to four configurable timeframes, defaulting to Weekly, Daily, 12H, and 4H so lines appear on normal 4H chart history.

It:

- Detects ascending trendlines from confirmed pivot lows that form higher lows.
- Detects descending trendlines from confirmed pivot highs that form lower highs.
- Filters trendlines using an ATR-normalised slope approximation.
- Projects trendlines to the right.
- Prioritises retained trendlines by projected distance from the current price.
- Draws optional current-price probe lines from the latest confirmed pivot to live price.
- Calculates intersections between ascending and descending trendlines.
- Marks useful intersections near current price with horizontal levels.
- Uses different colours and line styles per timeframe.
- Removes stale, broken, far-away, duplicate, and lower-timeframe overlapping lines.
- Keeps higher-timeframe lines when lower-timeframe lines conflict or overlap.
- Highlights candidate long and short setups with entry, stop-loss, and 1:2 reward:risk targets by default.
- Includes alert conditions for long, short, and any setup.

## Important Limitation: The 45 Degree Line

TradingView chart angles are visual, not mathematical constants. A line that looks like 45 degrees changes when you zoom, compress the chart, switch symbols, change price scale, or change timeframe.

Because Pine Script cannot read screen pixels or chart zoom, this script approximates the idea of a 45-degree trendline using:

- Price movement measured in ATR.
- Time movement measured in higher-timeframe bars.
- A target slope of ATR per bar.

The `Require 45 degree ATR slope filter` input is off by default so you can see the trendline map first. When enabled, the default `45 degree target slope, ATR per HTF bar` is `0.35`. Adjust this value and `Slope tolerance` to make trendline selection stricter or looser.

## Installation

1. Open TradingView.
2. Open Pine Editor.
3. Create a new indicator.
4. Paste the full contents of `MTF_Trendline_Intersection_Strategy_v6.pine`.
5. Save and add it to your chart.

Recommended chart timeframe: 4H or lower. The script can be used on other timeframes, but its default top-down structure is designed to analyse down to 4H.

## Main Inputs

- `Show TF 1-4`: Enable or disable each analysis timeframe.
- `TF 1-4`: Choose the top-down timeframes. Defaults are 1W, 1D, 12H, and 4H.
- `Pivot left/right bars`: Controls how strong pivots must be. Higher values produce fewer, stronger lines.
- `Require 45 degree ATR slope filter`: Turn this on when you want stricter 45-degree-style line selection.
- `45 degree target slope, ATR per HTF bar`: The desired normalised trendline slope when the filter is enabled.
- `Slope tolerance`: How far a detected line can deviate from the target slope.
- `Minimum pivot separation, ATR`: Prevents tiny pivot differences from creating weak trendlines.
- `Max lines per timeframe/side`: Caps clutter separately for up and down lines.
- `Prefer lines closest to current price`: When the script has too many lines for one timeframe/side, it removes the farthest projected line instead of simply removing the oldest.
- `Draw latest pivot to current price lines`: Draws live probe lines from the most recent confirmed pivot low/high to the current price. These are designed to keep the chart focused on nearby active structure.
- `Delete broken trendlines`: Removes support lines broken by close below, and resistance lines broken by close above.
- `Remove lines far from price`: Optional cleanup for projected lines too far from current price. It is off by default so you can confirm lines are being detected.
- `Far-away distance, ATR`: Distance used by the far-away cleanup when enabled.
- `Duplicate/overlap threshold`: Defines when a lower-timeframe line is too close to a higher-timeframe line.
- `Keep crosses near price, ATR`: Only keeps intersections near current price.
- `Reward:risk target`: Default is 2.0 for a 1:2 setup.

## Signal Rules

Long candidate:

- A retained intersection/cross level is below or near price.
- Price trades into that level.
- The candle closes back above the level.
- The candle closes bullish.
- Entry is the signal close.
- Stop-loss is below the level by the configured ATR buffer.
- Take-profit is calculated from the selected reward:risk value.

Short candidate:

- A retained intersection/cross level is above or near price.
- Price trades into that level.
- The candle closes back below the level.
- The candle closes bearish.
- Entry is the signal close.
- Stop-loss is above the level by the configured ATR buffer.
- Take-profit is calculated from the selected reward:risk value.

## Non-Repainting Notes

The script uses confirmed pivots with `ta.pivothigh()` and `ta.pivotlow()`. A pivot only becomes available after the configured right-side confirmation bars have closed.

Higher-timeframe data is requested with lookahead disabled, so future higher-timeframe values are not intentionally pulled into the past. Signals are still delayed by pivot confirmation, which is normal and expected.

## Practical Use

Use this as a mapping and alert tool, not a fully automated trading system. The strongest areas are usually where:

- Higher-timeframe lines remain active.
- Opposite trendlines intersect close to current price.
- Price reacts cleanly at a retained horizontal cross level.
- The stop distance is reasonable relative to recent volatility.
- The setup aligns with your own session, liquidity, and market-structure rules.

## Current-Price Focus

The script now uses current price in two ways:

- Stored pivot-to-pivot trendlines are ranked by how close their projected value is to the current price. With `Prefer lines closest to current price` enabled, the farthest line is removed first when the script reaches the per-timeframe line cap.
- Current-price probe lines connect the latest confirmed pivot low/high on each enabled timeframe to the current chart price. These update as price moves, so they are useful for visual context but should be treated as live guide lines rather than fixed confirmed trendlines.

## Validation Notes

Pine Script can only be fully compiled inside TradingView. The script has been written with Pine v6 syntax and conservative object limits, but final validation should be done by pasting it into the TradingView Pine Editor and using its compiler messages.

If TradingView reports a syntax issue, check that the script begins with `//@version=6` and that your Pine Editor is using the current TradingView Pine version.
