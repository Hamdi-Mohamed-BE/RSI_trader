# ICT + SNR research hypothesis

This experiment converts discretionary ICT and support/resistance language into closed-bar, non-repainting rules. It is isolated from every active BAT and deployment script.

## Objective model

1. Build fresh support/resistance candidates from the previous UTC day high/low, completed Asian range high/low, previous week high/low, and the newest confirmed H1 swing high/low.
2. Give a level more weight when independent levels overlap inside an ATR-normalized zone and when recent closed candles have already rejected the area.
3. During a configured London/New York window, require price to sweep beyond a qualified level and close back through it.
4. Record the pre-sweep internal swing. In the next few bars, require an ATR-sized displacement candle to close through that swing (market-structure shift) and leave a three-candle fair-value gap.
5. Enter only after a later closed candle retraces to the configured part of the FVG and closes back in the intended direction.
6. Put the stop beyond the raid extreme plus an ATR buffer. Use a fixed R target so targets remain reproducible across instruments. Break-even and ATR trailing are optional research variables.
7. Risk 1% of current equity, allow at most one position per symbol, limit daily entries, filter excessive spread, and optionally flatten after the session.

## Anti-lookahead rules

- All swing levels require right-side confirmation.
- Signals use only completed candles.
- A displacement/FVG candle cannot also be its own retracement entry.
- Parameters are selected on an earlier training window and then frozen for the latest complete one-year test.
- Final results use MT5 Every Tick with random execution delay on the isolated Exness tester.

## Interpretation guardrail

ICT terminology is a descriptive framework, not established causal proof of institutional activity. This test evaluates only the explicit mechanical rules above. A profitable result would support this implementation on this broker history; it would not validate every discretionary ICT claim.
