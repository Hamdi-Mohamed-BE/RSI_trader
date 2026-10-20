"""Supplement the MCP symbol schema with read-only broker profit/margin APIs.

No order_check/order_send/login/terminal restart. Never export identity, balances,
names, passwords or terminal paths. The user requested the connected demo specs.
"""
from pathlib import Path
import json
import time
import MetaTrader5 as mt5

ROOT = Path(__file__).resolve().parent


def main():
    assert mt5.initialize(path=r'C:\Program Files\MetaTrader 5\terminal64.exe', timeout=15000), mt5.last_error()
    try:
        account, terminal = mt5.account_info(), mt5.terminal_info()
        assert account and terminal and terminal.connected
        assert account.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO
        assert account.currency == 'USD' and account.margin_mode == 2
        result = dict(fetched_utc_epoch=int(time.time()), broker=account.company,
                      server=account.server, currency=account.currency, demo=True,
                      leverage=account.leverage, hedging=True, symbols={})
        for symbol in ('USTEC', 'XAUUSD', 'USDJPY'):
            info, tick = mt5.symbol_info(symbol), mt5.symbol_info_tick(symbol)
            assert info and tick and tick.ask > 0 and tick.bid > 0
            row = {k: getattr(info, k) for k in (
                'name', 'digits', 'point', 'trade_contract_size', 'trade_calc_mode',
                'trade_tick_size', 'trade_tick_value', 'trade_tick_value_profit', 'trade_tick_value_loss',
                'volume_min', 'volume_step', 'volume_max', 'currency_base', 'currency_profit', 'currency_margin',
                'margin_initial', 'margin_maintenance', 'trade_exemode', 'filling_mode',
                'trade_stops_level', 'swap_mode', 'swap_long', 'swap_short', 'swap_rollover3days')}
            row.update(bid=tick.bid, ask=tick.ask, quote_epoch=tick.time, quote_spread=tick.ask-tick.bid)
            row['buy_margin_one_lot'] = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, symbol, 1., tick.ask)
            row['sell_margin_one_lot'] = mt5.order_calc_margin(mt5.ORDER_TYPE_SELL, symbol, 1., tick.bid)
            assert row['buy_margin_one_lot'] is not None and row['sell_margin_one_lot'] is not None, mt5.last_error()
            row['buy_one_price_unit_loss_one_lot'] = mt5.order_calc_profit(mt5.ORDER_TYPE_BUY, symbol, 1., tick.ask, tick.ask-1.)
            row['sell_one_price_unit_loss_one_lot'] = mt5.order_calc_profit(mt5.ORDER_TYPE_SELL, symbol, 1., tick.bid, tick.bid+1.)
            result['symbols'][symbol] = row
        (ROOT/'BROKER.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n', encoding='utf-8')
        print(json.dumps(result, indent=2, allow_nan=False))
    finally:
        mt5.shutdown()


if __name__ == '__main__':
    main()
