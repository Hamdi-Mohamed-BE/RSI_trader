# Gold Trend Rider EA for MT5

`GoldTrendRiderEA.mq5` is an original MT5 implementation based only on the behavior described in the supplied Gold Rider video transcript. It is not the seller's source code and cannot reproduce undisclosed formulas, preset values, or advertised results.

## Implemented behavior

- XAUUSD M15 operation, including broker-specific gold symbol names because it trades the chart symbol.
- Non-repainting SuperTrend flips calculated from completed candles.
- MACD crossover entries from completed candles.
- Delayed re-entry when a signal was blocked and its conditions later become valid.
- ATR volatility, EMA trend, higher-timeframe EMA, Bollinger extreme, and optional spread filters.
- Fixed lot or equity-risk sizing, with broker minimum volume and a maximum lot cap.
- Fixed-point or ATR-based stop loss, plus fixed or risk/reward take profit.
- Optional break-even, trailing stop, and SuperTrend opposite-signal close.
- Trading hours and peak-equity drawdown protection.
- One managed position per symbol and magic number. No martingale and no grid.

## Install

1. Run `install_gold_ea.bat` from the project folder.
2. In MT5, right-click **Expert Advisors** in Navigator and choose **Refresh**.
3. Open your broker's gold symbol, such as `XAUUSD`, `GOLD`, or `XAUUSDm`, on M15.
4. Attach **GoldTrendRiderEA** to the chart.
5. Leave **Algo Trading** disabled until testing is complete.

The installer also places `GoldTrendRider_Conservative.set` in the MT5 tester profile folder. The source is in `mt5/Experts`, and the preset is in `mt5/Presets`.

## Test first

Use MT5 Strategy Tester with **Every tick based on real ticks**, your exact broker symbol, variable spread, and commission. Test several years, then use a separate forward period and a demo account. The included preset starts at 1% equity risk, not the transcript's marketing growth assumptions.

Point-based distances depend on the broker's symbol digits. The default stop, break-even trigger, and trailing distances use ATR multiples so the starter preset is more portable. Tune fixed-point settings only against the exact broker symbol being traded.

The drawdown guard measures from the highest account equity observed since the EA was attached. By default it closes only positions belonging to this EA and prevents new entries until the EA is restarted. `DRAWDOWN_WHOLE_ACCOUNT` is available but can close unrelated positions, so use it deliberately.

Backtest claims in a promotional video are not evidence of future profitability. Do not enable live trading until the EA has passed your own broker-specific backtest and demo forward test.

