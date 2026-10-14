"""Read-only US500 history through the supported MT5 Python API."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import MetaTrader5 as mt5
import numpy as np

ROOT=Path(__file__).resolve().parent


def main():
    assert mt5.initialize(path=r'C:\Program Files\MetaTrader 5\terminal64.exe'),mt5.last_error()
    try:
        account,term,spec=mt5.account_info(),mt5.terminal_info(),mt5.symbol_info('US500')
        assert account and term and term.connected and spec and spec.visible
        start=datetime(2019,12,16,tzinfo=timezone.utc)
        end=datetime(2024,1,2,tzinfo=timezone.utc)
        bars=mt5.copy_rates_range('US500',mt5.TIMEFRAME_M1,start,end)
        assert bars is not None and len(bars),mt5.last_error()
        bars=bars[(bars['time']>=start.timestamp())&(bars['time']<end.timestamp())]
        assert np.all(np.diff(bars['time'])>0)
        path=ROOT/'US500-M1.npz';np.savez_compressed(path,rates=bars)
        iso=lambda t:datetime.fromtimestamp(int(t),timezone.utc).isoformat()
        meta=dict(symbol='US500',instrument='S&P 500 CFD, not ES futures',server=account.server,
                  broker=account.company,currency=account.currency,api='MetaTrader5.copy_rates_range; read-only',
                  requested_start=start.isoformat(),requested_end_exclusive=end.isoformat(),
                  retrieved_utc=datetime.now(timezone.utc).isoformat(),rows=len(bars),
                  first=iso(bars['time'][0]),last=iso(bars['time'][-1]),
                  source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  specification={k:getattr(spec,k) for k in ['point','digits','trade_tick_size',
                    'trade_tick_value','trade_contract_size','volume_min','volume_step','volume_max','path']})
        years=np.array([datetime.fromtimestamp(int(t),timezone.utc).year for t in bars['time']])
        meta['yearly_bars']={str(y):int((years==y).sum()) for y in range(2020,2024)}
        (ROOT/'DATA.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
        # Small direct API spot checks; do not write personal account identifiers.
        spots={}
        for stamp in ['2020-01-02T15:10:00+00:00','2022-01-06T15:10:00+00:00','2023-07-06T14:10:00+00:00']:
            dt=datetime.fromisoformat(stamp)
            rows=mt5.copy_rates_range('US500',mt5.TIMEFRAME_M1,dt,dt.replace(minute=15))
            spots[stamp]=[{k:iso(row[k]) if k=='time' else row[k].item() for k in rows.dtype.names}
                          for row in rows] if rows is not None else None
        (ROOT/'API-SPOT-CHECKS.json').write_text(json.dumps(spots,indent=2),encoding='utf-8')
        print(json.dumps(meta,indent=2))
    finally:mt5.shutdown()


if __name__=='__main__':main()
