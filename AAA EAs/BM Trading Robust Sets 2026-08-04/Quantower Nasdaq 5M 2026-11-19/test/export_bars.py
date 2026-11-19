"""Export USTEC M5 bars 2026-06-01 -> now from the ISOLATED research terminal (read-only copy_rates_range; terminal shut down after). -> data/USTEC_M5.csv
Server time of this terminal = UTC (checked 2026-11-19: last bar 17:38 at 17:37 UTC)."""
import csv, time
from datetime import datetime, timezone
from pathlib import Path
import MetaTrader5 as mt5
H = Path(__file__).resolve().parents[1]; TERM = H.parent / '_Backtests/MT5-DMC-20260811/terminal64.exe'
assert mt5.initialize(path=str(TERM), portable=True, timeout=120000), mt5.last_error()
try:
    assert 'MT5-DMC-20260811' in mt5.terminal_info().path
    mt5.symbol_select('USTEC', True); r = None
    for _ in range(10):
        r = mt5.copy_rates_range('USTEC', mt5.TIMEFRAME_M5, datetime(2026, 6, 1, tzinfo=timezone.utc), datetime.now(timezone.utc))
        if r is not None and len(r) > 1000: break
        time.sleep(2)
    with open(H / 'data/USTEC_M5.csv', 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['time_utc', 'open', 'high', 'low', 'close'])
        for x in r: w.writerow([datetime.fromtimestamp(int(x['time']), timezone.utc).strftime('%Y-%m-%d %H:%M'), repr(float(x['open'])), repr(float(x['high'])), repr(float(x['low'])), repr(float(x['close']))])
    print('bars', len(r), datetime.fromtimestamp(int(r['time'][0]), timezone.utc), '->', datetime.fromtimestamp(int(r['time'][-1]), timezone.utc))
finally:
    mt5.shutdown()
