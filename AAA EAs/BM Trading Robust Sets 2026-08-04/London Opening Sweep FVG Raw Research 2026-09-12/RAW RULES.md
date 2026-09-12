# XAU London Opening Sweep and FVG — frozen raw rules

User source: pasted video transcript, plus explicit corrections to compare M1, M5 and M15 entry timeframes and put the stop beyond the FVG. No claimed predictive certainty is assumed.

1. Instrument: XAUUSD CFD. London time follows GMT/BST, not a fixed UTC offset. Mark the completed 08:00–09:00 H1 candle's high and low.
2. After 09:00, wait for the first completed H1 candle with its entire body inside the opening range and its wick outside exactly one end. A downside sweep gives long bias; upside gives short bias. Sweeps of both ends are ambiguous and do not qualify.
3. From confirmation onward, use the selected lower timeframe (M1, M5, M15). The first three-candle FVG is defined by candle three's low above candle one's high for buys, or candle three's high below candle one's low for sells. The middle candle must close in the trade direction. All three bars must start after sweep confirmation and be fully closed and consecutive. No retroactive entry into a gap before it exists.
4. Place a buy limit at the bullish gap's upper edge, or a sell limit at the bearish gap's lower edge. Stop is ONE instrument tick beyond the far edge of the FVG. This implements the user's corrected stop placement; it does not use the sweep wick as the stop.
5. Target the opposite boundary of the opening H1 range. RR is variable, determined by the opening range and gap width. No fixed RR filter, trailing stop, breakeven or volume/trend/news filter.
6. Assumptions needed because the transcript omits lifecycle details: first qualifying sweep and first subsequent gap only; at most one filled trade per London date; abandon the setup if its sweep extreme breaks again or its target is reached before entry. Cancel pending orders and flatten at 17:00 London, retrying if the broker initially rejects a close. Actual delayed exits and costs remain in the report.
7. USD 10,000 initial balance; requested 1% equity risk. As previously requested for the system, lot sizes round UP to the broker step and use at least minimum lot, so actual risk can exceed 1%. Insufficient margin, non-tradable prices and minimum stop-distance constraints can prevent execution; these are logged, not turned into invented fills.
8. The comparisons vary only the entry timeframe. The H1 sweep confirmation and all other rules are the same. These are raw research candidates, not an optimized or deployed EA.

The source explicitly refuses to run outside MT5 Strategy Tester. Standard website comparison dates end on 2026-09-05 (exclusive).

Execution environment: isolated Exness-MT5Trial16 XAUUSD tester, leverage 1:2000. The journal confirms fixed 1 ms execution delay (not random delay). All recorded commission and swap are retained; fills use the tester's bid/ask quotes. Pending-order acceptance and activation are separate: an order can be accepted but later rejected for insufficient margin, which is counted from the native journal. This is a raw comparison, not a live-execution stress test.

Reproduce with `python run_raw.py` followed by `python build_results.py`. The default requests MT5's real-tick mode (configuration Model=4). The percentage of actual real ticks must be read from each native report: MT5 may fill missing history with generated ticks. Model 0 is a separate generated-tick comparison, never labelled real ticks.
