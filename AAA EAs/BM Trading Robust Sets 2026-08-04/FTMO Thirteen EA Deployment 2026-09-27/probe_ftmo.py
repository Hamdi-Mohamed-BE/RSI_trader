"""Read-only queries of an ALREADY RUNNING terminal. Called by guarded launcher."""
import argparse, json
import MetaTrader5 as mt5
def main():
    parser=argparse.ArgumentParser();parser.add_argument("--terminal",required=True)
    args=parser.parse_args()
    if not mt5.initialize(path=args.terminal,timeout=15000):
        raise RuntimeError("Cannot attach to selected MT5: "+str(mt5.last_error()))
    try:
        a,t=mt5.account_info(),mt5.terminal_info()
        pos,orders,syms=mt5.positions_get(),mt5.orders_get(),mt5.symbols_get()
        if any(x is None for x in (a,t,pos,orders,syms)):
            raise RuntimeError("Incomplete account/exposure/symbol snapshot")
        # Exclude account holder names and credentials from artifacts/output.
        account={k:getattr(a,k) for k in ("login","server","company","currency","balance","equity",
                                        "leverage","margin_mode","trade_allowed","trade_expert")}
        terminal={k:getattr(t,k) for k in ("path","data_path","connected","trade_allowed")}
        symbols=[{k:getattr(s,k) for k in ("name","path","visible","trade_mode","volume_min",
                                         "volume_max","volume_step","trade_contract_size")} for s in syms]
        print(json.dumps(dict(ok=True,account=account,terminal=terminal,
                              positions=len(pos),orders=len(orders),symbols=symbols)))
    finally:mt5.shutdown()
if __name__=="__main__":main()
