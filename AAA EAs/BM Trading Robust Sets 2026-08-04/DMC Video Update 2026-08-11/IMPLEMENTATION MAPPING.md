# Video-to-EA implementation mapping

## What the EA implements

| Video concept | Mechanical definition used in `AAA Final DmC Video EA` |
|---|---|
| Higher-timeframe levels | Open and close boundaries of completed daily, weekly and monthly candle bodies |
| Untested level | No completed source-timeframe candle and no lower-timeframe candle in the current source period touched the level before the signal |
| Failed loss/gain | H1 touches or crosses a level and closes back on the original side with configurable ATR tolerance |
| Quick regain | The previous H1 close is outside the level and the newest closed H1 regains it |
| Confirmation entry | Market entry at the first tick after the confirming H1 closes |
| Retest entry | A second H1 retests the level after the rejection/regain and remains on the confirmed side |
| Direction | Long after failed loss/regain from below; short after failed gain/regain from above |
| Target | Nearest structural level in the trade direction, slightly front-run; recent swing fallback is optional |
| Stop | Nearest structural level behind the setup plus an ATR buffer; recent swing fallback is optional |
| Risk | Equity-based position sizing for a maximum planned 1% loss at the initial stop |
| Repeated tests | Maximum one entry per UTC day by default and only one open exposure per symbol/magic number |
| Martingale | Not implemented |

## Deliberately excluded from the baseline

- Blind entries: offered as an option in the video but inherently discretionary and higher-drawdown.
- DCA: optional in the video and not precisely specified; excluding it preserves the 1% risk ceiling.
- No-stop trading: rejected for an automated EA because the video also recommends a protective level behind the setup.
- Emotional-discomfort sizing: replaced with the user’s established 1% risk rule.
- A claimed 80–90% hit rate: the public video says the exact nuances are not supplied, and the tests did not reproduce this claim.
- Subjective early exit after a perceived trend shift: no deterministic numerical rule is supplied in the video, so inventing one would not be faithful.

## Important interpretation

This is a transparent mechanical interpretation of the public rules, not a claim that the presenter would personally take every generated signal. Parameters expose the unavoidable choices left undefined by the video. The old EA is preserved unchanged so the comparison remains auditable.

