"""Read-only M1 export of the Exness symbols from the ISOLATED research terminal (server clock = UTC), for clock checks and 5-minute marks.
Writes exness/<SYM>_m1.npy (t, o, h, l, c, v, spread). The terminal is closed again by its verified path."""
import subprocess, time
from datetime import datetime, timezone
from pathlib import Path
import MetaTrader5 as mt5, numpy as np
H = Path(__file__).resolve().parent; T = H.parent / '_Backtests/MT5-DMC-20260811/terminal64.exe'; OUT = H / 'bars'; OUT.mkdir(exist_ok=True)
assert mt5.initialize(path=str(T), portable=True, timeout=90000), mt5.last_error()
try:
    for s in ('USTEC', 'US500', 'DE30'):
        mt5.symbol_select(s, True); r = None
        for _ in range(20):
            r = mt5.copy_rates_range(s, mt5.TIMEFRAME_M1, datetime(2019, 7, 1, tzinfo=timezone.utc), datetime(2026, 11, 21, tzinfo=timezone.utc))
            if r is not None and len(r) > 1000: break
            time.sleep(3)
        np.save(OUT / f'{s}_m1.npy', np.stack([r['time'].astype(float), r['open'], r['high'], r['low'], r['close'], r['tick_volume'].astype(float), r['spread'].astype(float)], 1))
        print(s, len(r), datetime.fromtimestamp(int(r['time'][0]), timezone.utc), datetime.fromtimestamp(int(r['time'][-1]), timezone.utc), flush=True)
finally:
    mt5.shutdown()
    time.sleep(3)
    ps = f"Get-Process terminal64 -ErrorAction SilentlyContinue | Where-Object {{ $_.Path -eq '{T}' }} | Stop-Process"
    subprocess.run(['powershell', '-NoProfile', '-Command', ps.replace('/', chr(92))])
