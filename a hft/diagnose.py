"""Quick MT5 health check — run: python diagnose.py"""

import MetaTrader5 as mt5

import config as cfg
from mt5_client import entry_block_reason, initialize, lot_size, shutdown, spread_points
from risk import calc_sl_tp, format_sl_tp
from strategy import get_scalp_signal, warm_up


def main() -> None:
    print("=== HFT Scalper diagnose ===", flush=True)
    symbols = initialize()
    warm_up(symbols, 3)

    for symbol in symbols:
        sig = get_scalp_signal(symbol)
        block = entry_block_reason(symbol)
        print(f"\n{symbol}:", flush=True)
        print(f"  Signal: {sig.side.value} score={sig.score} ({sig.reason})", flush=True)
        print(f"  Spread: {spread_points(symbol):.0f} pts | lot={lot_size(symbol)}", flush=True)
        print(f"  Entry block: {block or 'none — ready'}", flush=True)

        tick = mt5.symbol_info_tick(symbol)
        if tick:
            from mt5_client import _filling_mode, effective_deviation

            entry = tick.ask
            sl, tp, tp_usd, sl_usd = calc_sl_tp(symbol, "BUY", entry, lot_size(symbol))
            print(f"  SL/TP plan: {format_sl_tp(symbol, 'BUY', entry, lot_size(symbol))}", flush=True)

            req = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot_size(symbol),
                "type": mt5.ORDER_TYPE_BUY,
                "price": entry,
                "deviation": effective_deviation(symbol),
                "magic": cfg.MAGIC_NUMBER,
                "comment": "diag",
                "type_filling": _filling_mode(symbol),
            }
            if cfg.PLACE_BROKER_SLTP and sl and tp:
                req["sl"] = sl
                req["tp"] = tp
            chk = mt5.order_check(req)
            if chk:
                print(f"  order_check: retcode={chk.retcode} {chk.comment}", flush=True)
            else:
                print(f"  order_check failed: {mt5.last_error()}", flush=True)

    shutdown()
    print("\n=== done ===", flush=True)


if __name__ == "__main__":
    main()
