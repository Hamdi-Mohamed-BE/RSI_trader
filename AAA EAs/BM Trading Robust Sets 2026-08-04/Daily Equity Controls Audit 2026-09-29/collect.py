"""Read-only public FTMO specs and connected MT5 historical prices. No trading calls."""
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import Request,urlopen
import json, numpy as np, MetaTrader5 as mt
ROOT=Path(__file__).resolve().parent
SYMBOLS=['XAUUSD','USTEC','USDJPY','BTCUSD','ETHUSD','XAGUSD','EURUSD']

def main():
    raw=urlopen(Request('https://ftmo.com/wp-json/ftmo/symbols',headers={'User-Agent':'Mozilla/5.0'}),timeout=30).read()
    allspec=json.loads(raw)['data']['symbols']
    target=[s for s in allspec if s['code'] in ['XAU/USD','US100.cash','USD/JPY','BTCUSD','ETHUSD','XAG/USD','EUR/USD']]
    (ROOT/'FTMO_SPECS.json').write_text(json.dumps(target,indent=2),encoding='utf-8')
    print('FTMO',json.dumps([{k:s.get(k) for k in ['code','contractSize','leverageSwing','commission','commissionType']} for s in target]),flush=True)
    assert mt.initialize(path=r'C:\Program Files\MetaTrader 5\terminal64.exe')
    info=mt.account_info(); assert info.server.startswith('Exness-'),info.server
    specs={}; audit=[]
    for sym in SYMBOLS:
        s=mt.symbol_info(sym);assert s is not None,sym
        specs[sym]={k:getattr(s,k) for k in ['point','trade_contract_size','volume_min','volume_step','volume_max','trade_calc_mode','currency_profit','margin_initial','margin_maintenance','swap_mode']}
        quote=mt.symbol_info_tick(sym);margin=mt.order_calc_margin(mt.ORDER_TYPE_BUY,sym,1.,quote.ask)
        specs[sym]['margin_one_lot_current']=margin
        specs[sym]['margin_quote']=quote.ask
        local=ROOT/f'{sym}-M1.npz'
        rows=np.load(local)['rates'] if local.exists() else mt.copy_rates_range(sym,mt.TIMEFRAME_M1,datetime(2025,8,25,tzinfo=timezone.utc),datetime(2026,9,29,tzinfo=timezone.utc))
        if rows is None or len(rows)==0:
            audit.append(dict(symbol=sym,error=str(mt.last_error())));print(audit[-1],flush=True);continue
        np.savez_compressed(ROOT/f'{sym}-M1.npz',rates=rows)
        audit.append(dict(symbol=sym,bars=len(rows),first=int(rows['time'][0]),last=int(rows['time'][-1])))
        print(audit[-1],flush=True)
    (ROOT/'SOURCE_SPECS.json').write_text(json.dumps(dict(server=info.server,leverage=info.leverage,symbols=specs,rates=audit),indent=2),encoding='utf-8')
    mt.shutdown() # disconnect this Python client only; does not close the terminal

if __name__=='__main__':main()
