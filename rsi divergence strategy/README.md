# RSI Divergence Strategy Bot

This is a clean Python RSI-divergence strategy/backtester using MT5 candles.

Default backtest:

```bat
run_backtest.bat
```

The default batch file runs the optimized top-5 portfolio:

```text
AUDUSD, XAUUSD, GBPCHF, AUDCAD, XAGUSD
```

Manual command:

```powershell
& "C:\Users\hama101\Desktop\geek\ai trader\rsi-divergence-mt5-bot\.venv\Scripts\python.exe" .\rsi_divergence_bot.py --backtest --days 60 --balance 300 --risk 4
```

Rules implemented:

- RSI 14 pivot divergence.
- Bullish setup: price lower/equal low, RSI higher low.
- Bearish setup: price higher/equal high, RSI lower high.
- Confirmation modes from your master prompt: EMA reclaim/reject, trend guard, RSI extreme, or raw/off.
- Stop loss based on divergence pivot plus ATR buffer.
- Three-leg trade idea: TP1, TP2, TP3.
- Risk is applied per trade idea, default 4%.
- Position sizing modes:
  - `RISK_PERCENT`: dynamic lot from account balance percentage.
  - `FIXED_LOT`: use the exact configured lot.
  - `USD_RISK_CAP`: dynamic lot tries to keep risk under a fixed USD cap minus a small offset.
- TP1 moves remaining legs to break even.
- TP2 moves final leg stop to TP1.
- Weekend candles are naturally ignored if the broker has no data.

Reports are saved under:

```text
reports\YYYYMMDD-HHMMSS\
```

Optimizer:

```bat
run_optimize.bat
```

The optimizer saves the selected settings to:

```text
optimized_configs.json
```

Yearly backtest:

```bat
run_backtest_year.bat
```

Demo live bot:

```bat
run_live_demo.bat
```

Paper scanner:

```bat
run_live_paper.bat
```

Live behavior:

- Uses `optimized_configs.json`, currently `AUDUSD, XAUUSD, GBPCHF, AUDCAD, XAGUSD`.
- Requires a demo/trial account by default.
- Scans every `RSI_SCAN_INTERVAL_SECONDS`.
- Only places fresh RSI divergence signals.
- Skips duplicate signals after restart using `runtime/live_state.json`.
- One idea opens 3 legs: TP1, TP2, TP3.
- Skips same-symbol same-side exposure by default.
- Blocks entries if price has drifted too far from the tested entry.
- `run_live_demo.bat` enables live demo orders only for that window.

Sizing examples:

```powershell
# Risk 4% of balance, dynamic lot
.\run_backtest.bat

# Use fixed 0.01 lot
& "C:\Users\hama101\Desktop\geek\ai trader\rsi-divergence-mt5-bot\.venv\Scripts\python.exe" .\rsi_divergence_bot.py --backtest --risk-mode FIXED_LOT --fixed-lot 0.01

# Cap risk around $12, but target $11.50 to leave a broker rounding offset
& "C:\Users\hama101\Desktop\geek\ai trader\rsi-divergence-mt5-bot\.venv\Scripts\python.exe" .\rsi_divergence_bot.py --backtest --risk-mode USD_RISK_CAP --risk-usd-cap 12 --risk-usd-offset 0.50
```
