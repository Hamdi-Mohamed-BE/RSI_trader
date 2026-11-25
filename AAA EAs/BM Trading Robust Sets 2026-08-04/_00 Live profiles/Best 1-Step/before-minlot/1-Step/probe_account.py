"""Read-only snapshot for the already-running terminal chosen by the user."""
import argparse
import json
import time

import MetaTrader5 as mt5


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--terminal', required=True)
    args = parser.parse_args()
    if not mt5.initialize(path=args.terminal, timeout=15000):
        raise RuntimeError('Cannot attach to selected terminal: '+str(mt5.last_error()))
    try:
        a, t = mt5.account_info(), mt5.terminal_info()
        positions, orders, symbols = mt5.positions_get(), mt5.orders_get(), mt5.symbols_get()
        if any(v is None for v in (a, t, positions, orders, symbols)):
            raise RuntimeError('Incomplete account/exposure/symbol snapshot')
        print(json.dumps(dict(
            ok=True, snapshot_utc=int(time.time()),
            account={k: getattr(a, k) for k in ('login', 'server', 'company', 'currency', 'balance', 'equity',
                       'leverage', 'margin_mode', 'trade_allowed', 'trade_expert')},
            terminal={k: getattr(t, k) for k in ('path', 'data_path', 'connected', 'trade_allowed')},
            positions=len(positions), orders=len(orders),
            symbols=[{k: getattr(s, k) for k in ('name', 'path', 'visible', 'trade_mode', 'volume_min',
                      'volume_max', 'volume_step', 'trade_contract_size')} for s in symbols],
        )))
    finally:
        mt5.shutdown()


if __name__ == '__main__':
    main()
