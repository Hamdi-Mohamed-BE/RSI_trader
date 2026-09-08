"""Read-only M15 history acquisition from the isolated Exness demo research terminal."""
from pathlib import Path
from datetime import datetime, timezone
import json, subprocess, time
import MetaTrader5 as mt5
import numpy as np

ROOT = Path(__file__).resolve().parent
TESTER = ROOT.parent / '_Backtests' / 'MT5-DMC-20260811'
SYMBOLS = ('XAUUSD','XAGUSD','BTCUSD','ETHUSD','USTEC','US30','EURUSD','GBPJPY')
START = datetime(2022, 1, 1, tzinfo=timezone.utc)
END = datetime(2026, 9, 1, tzinfo=timezone.utc)

def main():
    data = ROOT / 'Data'; data.mkdir(parents=True, exist_ok=True)
    config = ROOT / 'data-reader.ini'
    config.write_text('[Common]\nLogin=472334559\nServer=Exness-MT5Trial16\n[Experts]\nEnabled=0\n[Charts]\nMaxBars=10000000\n', encoding='utf-8-sig')
    proc = subprocess.Popen(f'"{TESTER / "terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{config}"', creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        time.sleep(10)
        if proc.poll() is not None:
            raise RuntimeError('The isolated research terminal exited before IPC was available')
        if not mt5.initialize(str(TESTER / 'terminal64.exe'), portable=True, timeout=120000):
            raise RuntimeError(str(mt5.last_error()))
        terminal = mt5.terminal_info(); account = mt5.account_info()
        if not terminal or str(TESTER).lower() != terminal.path.lower():
            raise RuntimeError('Unexpected MT5 terminal; refusing to read from a live installation')
        if not account or account.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
            raise RuntimeError('Historical acquisition is restricted to the demo research terminal')
        meta = {'server': account.server, 'currency': account.currency, 'acquired_utc': datetime.now(timezone.utc).isoformat(), 'symbols': {}}
        for symbol in SYMBOLS:
            if not mt5.symbol_select(symbol, True):
                raise RuntimeError(f'{symbol} is unavailable: {mt5.last_error()}')
            info = mt5.symbol_info(symbol)._asdict()
            keys = ('name','digits','point','trade_contract_size','trade_tick_size','trade_tick_value','volume_min','volume_step','volume_max','swap_mode','swap_long','swap_short','swap_rollover3days','trade_calc_mode','trade_stops_level','currency_profit','currency_margin')
            path = data / f'{symbol}-M15.npz'
            parts = []
            # Quarterly requests are more reliable than asking the terminal for the entire range at once.
            for year in range(START.year, END.year + 1):
                for month in (1,4,7,10):
                    begin = datetime(year, month, 1, tzinfo=timezone.utc)
                    finish = datetime(year + (month == 10), 1 if month == 10 else month + 3, 1, tzinfo=timezone.utc)
                    if finish <= START or begin >= END: continue
                    begin=max(begin,START); finish=min(finish,END)
                    chunk = None
                    for _ in range(8):
                        chunk = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M15, begin, finish)
                        if chunk is not None and len(chunk): break
                        time.sleep(2)
                    if chunk is None or not len(chunk):
                        raise RuntimeError(f'{symbol}: no M15 data for {begin.date()}..{finish.date()} ({mt5.last_error()})')
                    parts.append(chunk); print(symbol, begin.date(), finish.date(), len(chunk), flush=True)
            rates=np.concatenate(parts)
            _,ix=np.unique(rates['time'],return_index=True); rates=rates[np.sort(ix)]
            rates=rates[(rates['time']>=START.timestamp())&(rates['time']<END.timestamp())]
            np.savez_compressed(path,rates=rates)
            meta['symbols'][symbol]={k:info.get(k) for k in keys}
            meta['symbols'][symbol].update(bars=int(len(rates)),first_utc=datetime.fromtimestamp(int(rates['time'][0]),timezone.utc).isoformat(),last_utc=datetime.fromtimestamp(int(rates['time'][-1]),timezone.utc).isoformat(),zero_spread_bars=int((rates['spread']==0).sum()))
            (data/'metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
            print('SAVED',symbol,len(rates),flush=True)
    finally:
        mt5.shutdown()
        if proc.poll() is None:
            proc.terminate()
            try: proc.wait(timeout=30)
            except subprocess.TimeoutExpired: proc.kill()

if __name__ == '__main__': main()
