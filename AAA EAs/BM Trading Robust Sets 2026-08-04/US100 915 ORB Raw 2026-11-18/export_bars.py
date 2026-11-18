"""Addendum 2: export USTEC M15 + M1 bars (2022-06-01 -> 2026-11-17, server time = UTC) from the ISOLATED research terminal (_Backtests/MT5-DMC-20260811,
portable). Read-only: copy_rates_range only, no orders. The terminal is shut down afterwards. Output: bars/USTEC_M15.npz, bars/USTEC_M1.npz."""
import sys
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5
import numpy as np

H = Path(__file__).resolve().parent; TERM = H.parent / '_Backtests/MT5-DMC-20260811/terminal64.exe'
A = datetime(2022, 6, 1, tzinfo=timezone.utc); E = datetime(2026, 11, 17, tzinfo=timezone.utc)


def main():
    assert mt5.initialize(path=str(TERM), portable=True, timeout=120000), mt5.last_error()
    try:
        info = mt5.terminal_info(); print('terminal', info.path if info else None, flush=True)
        assert info and 'MT5-DMC-20260811' in info.path, 'not the isolated research terminal'
        mt5.symbol_select('USTEC', True); (H / 'bars').mkdir(exist_ok=True)
        jobs = (('M15', mt5.TIMEFRAME_M15, A), ('M1', mt5.TIMEFRAME_M1, A)) if 'long' not in sys.argv else (('M15LONG', mt5.TIMEFRAME_M15, datetime(2019, 1, 1, tzinfo=timezone.utc)),)
        for name, tf, start in jobs:
            r = mt5.copy_rates_range('USTEC', tf, start, E)
            assert r is not None and len(r), (name, mt5.last_error())
            np.savez_compressed(H / 'bars' / f'USTEC_{name}.npz', time=r['time'], open=r['open'], high=r['high'], low=r['low'], close=r['close'], spread=r['spread'])
            print(name, len(r), datetime.fromtimestamp(int(r['time'][0]), timezone.utc), '->', datetime.fromtimestamp(int(r['time'][-1]), timezone.utc), flush=True)
    finally:
        mt5.shutdown()


if __name__ == '__main__':
    main()
