"""Read-only MT5 history export; no orders, settings, login or terminal restart."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

import MetaTrader5 as mt5
import numpy as np

ROOT = Path(__file__).resolve().parent
TERMINAL = r'C:\Program Files\MetaTrader 5\terminal64.exe'


def main():
    assert mt5.initialize(path=TERMINAL), mt5.last_error()
    try:
        account = mt5.account_info()
        terminal = mt5.terminal_info()
        spec = mt5.symbol_info('USTEC')
        assert account and terminal and terminal.connected and spec, mt5.last_error()
        # Warm-up is not part of the tested return period.
        first = datetime(2025, 8, 1, tzinfo=timezone.utc)
        last = datetime(2026, 10, 13, tzinfo=timezone.utc)
        rates = mt5.copy_rates_range('USTEC', mt5.TIMEFRAME_M1, first, last)
        assert rates is not None and len(rates), mt5.last_error()
        rates = rates[(rates['time'] >= first.timestamp()) & (rates['time'] < last.timestamp())]
        assert np.all(np.diff(rates['time']) > 0)
        path = ROOT / 'USTEC-M1.npz'
        np.savez_compressed(path, rates=rates)
        metadata = {
            'retrieved_utc': datetime.now(timezone.utc).isoformat(),
            'api': 'MetaTrader5.copy_rates_range; read only',
            'terminal_path': terminal.path, 'broker': account.company,
            'server': account.server, 'account_currency': account.currency,
            'symbol': 'USTEC', 'timeframe': 'M1', 'time_basis': 'UTC',
            'requested_start': first.isoformat(), 'requested_end_exclusive': last.isoformat(),
            'rows': len(rates),
            'first': datetime.fromtimestamp(int(rates['time'][0]), timezone.utc).isoformat(),
            'last': datetime.fromtimestamp(int(rates['time'][-1]), timezone.utc).isoformat(),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'specification': {k: getattr(spec, k) for k in (
                'digits', 'point', 'trade_tick_size', 'trade_tick_value',
                'trade_contract_size', 'volume_min', 'volume_step', 'volume_max', 'path')},
        }
        (ROOT / 'DATA.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        print(json.dumps(metadata))
    finally:
        mt5.shutdown()  # Disconnects this API client, not the running terminal.


if __name__ == '__main__':
    main()
