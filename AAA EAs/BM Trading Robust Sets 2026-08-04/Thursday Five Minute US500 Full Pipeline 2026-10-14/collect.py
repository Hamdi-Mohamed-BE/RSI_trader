"""Read-only MT5 export, physically separate development and final holdout files."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json
import MetaTrader5 as mt5
import numpy as np
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    protocol=json.loads((ROOT/'PROTOCOL.json').read_text())
    assert not (ROOT/'DATA.json').exists(), 'Existing source export is immutable'
    assert mt5.initialize(path=r'C:\Program Files\MetaTrader 5\terminal64.exe'),mt5.last_error()
    try:
        account,term,spec=mt5.account_info(),mt5.terminal_info(),mt5.symbol_info('US500')
        assert account and term and term.connected and spec and spec.visible
        start=datetime(2019,12,16,tzinfo=timezone.utc);cut=datetime(2024,10,14,tzinfo=timezone.utc);end=datetime(2026,10,14,tzinfo=timezone.utc)
        rates=mt5.copy_rates_range('US500',mt5.TIMEFRAME_M1,start,end)
        assert rates is not None and len(rates),mt5.last_error()
        rates=rates[(rates['time']>=start.timestamp())&(rates['time']<end.timestamp())]
        assert np.all(np.diff(rates['time'])>0)
        iso=lambda x:datetime.fromtimestamp(int(x),timezone.utc).isoformat()
        files={}
        for name,sel in [('IS',rates['time']<cut.timestamp()),('OOS',rates['time']>=cut.timestamp())]:
            rows=rates[sel];p=ROOT/('US500-'+name+'.npz');np.savez_compressed(p,rates=rows)
            files[name]=dict(filename=p.name,rows=len(rows),first=iso(rows['time'][0]),last=iso(rows['time'][-1]),sha256=sha(p))
        meta=dict(symbol='US500',instrument='S&P 500 CFD, not ES futures',api='MetaTrader5.copy_rates_range read-only',
                  server=account.server,broker=account.company,currency=account.currency,
                  retrieved_utc=datetime.now(timezone.utc).isoformat(),protocol_sha256=sha(ROOT/'PROTOCOL.json'),files=files,
                  specification={k:getattr(spec,k) for k in ['point','digits','trade_tick_size','trade_tick_value','trade_contract_size','volume_min','volume_step','volume_max','path']})
        (ROOT/'DATA.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
        spots={}
        for stamp in ['2020-01-02T15:10:00+00:00','2023-07-06T14:10:00+00:00','2024-11-07T15:10:00+00:00','2025-07-03T14:10:00+00:00','2026-10-08T14:10:00+00:00']:
            dt=datetime.fromisoformat(stamp);a=mt5.copy_rates_range('US500',mt5.TIMEFRAME_M1,dt,dt.replace(minute=15))
            spots[stamp]=[{k:iso(x[k]) if k=='time' else x[k].item() for k in a.dtype.names} for x in a] if a is not None else None
        (ROOT/'API-SPOT-CHECKS.json').write_text(json.dumps(spots,indent=2),encoding='utf-8')
        print(json.dumps(meta,indent=2),flush=True)
    finally:mt5.shutdown()
if __name__=='__main__':main()
