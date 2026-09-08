"""Read-only historical data acquisition from the isolated MT5 research terminal."""
from pathlib import Path
from datetime import datetime, timezone
import json, time, subprocess
import MetaTrader5 as mt5
import numpy as np

ROOT=Path(__file__).resolve().parent
TESTER=ROOT.parent/'_Backtests'/'MT5-DMC-20260811'

def main():
    data=ROOT/'Data';data.mkdir(exist_ok=True)
    config=ROOT/'data-reader.ini'
    config.write_text('[Common]\nLogin=472334559\nServer=Exness-MT5Trial16\n[Experts]\nEnabled=0\n[Charts]\nMaxBars=10000000\n',encoding='utf-8-sig')
    process=subprocess.Popen(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{config}"',creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        # Allow the configured process to register IPC; initialize must not race
        # it and accidentally start a second terminal with an inherited profile.
        time.sleep(10)
        if process.poll() is not None:raise RuntimeError('Configured research terminal did not remain running; do not auto-launch a replacement')
        if not mt5.initialize(str(TESTER/'terminal64.exe'),portable=True,timeout=120000):
            raise RuntimeError(mt5.last_error())
        info=mt5.terminal_info()
        if str(TESTER).lower()!=info.path.lower(): raise RuntimeError('Unexpected terminal')
        account=mt5.account_info()
        if not account or account.trade_mode!=mt5.ACCOUNT_TRADE_MODE_DEMO: raise RuntimeError('Research terminal must be demo')
        meta={'server':account.server,'currency':account.currency,'acquired_utc':datetime.now(timezone.utc).isoformat(),'symbols':{}}
        for sym in ('BTCUSD','ETHUSD','XAUUSD','XAGUSD'):
            if not mt5.symbol_select(sym,True): raise RuntimeError(sym+' unavailable')
            spec=mt5.symbol_info(sym)._asdict()
            fields=['name','digits','point','trade_contract_size','trade_tick_size','trade_tick_value','volume_min','volume_step','volume_max','swap_mode','swap_long','swap_short','swap_rollover3days','trade_calc_mode','trade_stops_level','currency_profit','currency_margin']
            meta['symbols'][sym]={k:spec[k] for k in fields}
            path=data/(sym+'-M5.npz')
            if path.exists():
                a=np.load(path)['rates']
            else:
                parts=[]
                for year in range(2023,2027):
                    for month in range(1,13):
                        start=datetime(year,month,1,tzinfo=timezone.utc)
                        end=datetime(year+int(month==12),month%12+1,1,tzinfo=timezone.utc)
                        if start<datetime(2023,6,1,tzinfo=timezone.utc) or start>=datetime(2026,9,1,tzinfo=timezone.utc): continue
                        chunk=None
                        for attempt in range(6):
                            chunk=mt5.copy_rates_range(sym,mt5.TIMEFRAME_M5,start,end)
                            if chunk is not None and len(chunk): break
                            time.sleep(2)
                        if chunk is None or not len(chunk): raise RuntimeError(f'{sym} missing {start}: {mt5.last_error()}')
                        parts.append(chunk)
                        print(sym,start.date(),len(chunk),flush=True)
                a=np.concatenate(parts);a=a[np.unique(a['time'],return_index=True)[1]]
                a=a[a['time']<datetime(2026,9,1,tzinfo=timezone.utc).timestamp()]
                np.savez_compressed(path,rates=a)
            meta['symbols'][sym].update(bars=len(a),first_utc=datetime.fromtimestamp(int(a['time'][0]),timezone.utc).isoformat(),last_utc=datetime.fromtimestamp(int(a['time'][-1]),timezone.utc).isoformat(),zero_spread_bars=int((a['spread']==0).sum()))
            (data/'metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
            print('SAVED',sym,meta['symbols'][sym],flush=True)
    finally:
        mt5.shutdown()
        # Only this exact isolated process was started by this reader.
        process.terminate()
        process.wait(timeout=30)

if __name__=='__main__': main()
