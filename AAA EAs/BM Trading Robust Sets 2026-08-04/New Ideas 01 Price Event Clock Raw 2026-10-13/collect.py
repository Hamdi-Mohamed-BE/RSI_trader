"""Read-only data collection through the supported MT5 Python API."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import MetaTrader5 as mt5
import numpy as np

ROOT = Path(__file__).resolve().parent


def main():
    assert mt5.initialize(path=r'C:\Program Files\MetaTrader 5\terminal64.exe'), mt5.last_error()
    try:
        acct, term = mt5.account_info(), mt5.terminal_info()
        assert acct and term and term.connected
        start = datetime(2025,8,1,tzinfo=timezone.utc)
        end = datetime(2026,10,13,0,2,tzinfo=timezone.utc)
        meta = dict(api='Read-only MetaTrader5.copy_rates_range', broker=acct.company,
                    server=acct.server, currency=acct.currency,
                    retrieved_utc=datetime.now(timezone.utc).isoformat(), files={})
        for symbol in ['BTCUSD','XAUUSD','USTEC']:
            spec = mt5.symbol_info(symbol)
            assert spec and spec.visible, f'{symbol} unavailable without changing market watch'
            rates = mt5.copy_rates_range(symbol,mt5.TIMEFRAME_M1,start,end)
            assert rates is not None and len(rates), mt5.last_error()
            assert np.all(np.diff(rates['time']) > 0)
            path = ROOT / f'{symbol}-M1.npz'
            np.savez_compressed(path,rates=rates)
            meta['files'][symbol] = dict(rows=len(rates), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                first=datetime.fromtimestamp(int(rates['time'][0]),timezone.utc).isoformat(),
                last=datetime.fromtimestamp(int(rates['time'][-1]),timezone.utc).isoformat(),
                specification={k:getattr(spec,k) for k in ['digits','point','trade_tick_size',
                    'trade_tick_value','trade_contract_size','volume_min','volume_step','volume_max',
                    'swap_mode','swap_long','swap_short','swap_rollover3days','path']})
            print(json.dumps({symbol:meta['files'][symbol]}),flush=True)
        (ROOT/'DATA.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    finally:
        mt5.shutdown()


if __name__ == '__main__':
    main()
