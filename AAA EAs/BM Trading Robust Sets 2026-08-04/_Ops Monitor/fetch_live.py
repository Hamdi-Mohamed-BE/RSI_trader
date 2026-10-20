"""Read-only snapshot of the NORMAL MT5 terminal's account history (never Ava, never the isolated tester).

Safety: refuses unless C:\\Program Files\\MetaTrader 5\\terminal64.exe is ALREADY running (the MT5 Python API would
otherwise launch it). Only account_info / history_deals_get / positions_get are called: no orders, no settings.
The login is stored masked; deals stay in the git-ignored output/live folder.

uv run python ".../_Ops Monitor/fetch_live.py" --since 2026-09-01
"""
import argparse
import json
import subprocess
from datetime import datetime, timezone

from common import NORMAL_TERMINAL, OUT, now_utc  # calls MetaTrader5 directly and read-only

FIELDS = ('ticket', 'order', 'time', 'time_msc', 'type', 'entry', 'magic', 'position_id', 'reason', 'volume', 'price',
          'commission', 'swap', 'profit', 'fee', 'symbol', 'comment')


def normal_terminal_running() -> bool:
    out = subprocess.run(['powershell', '-NoProfile', '-Command',
                          "Get-Process terminal64 -ErrorAction SilentlyContinue | ForEach-Object { $_.Path }"],
                         capture_output=True, text=True, timeout=60).stdout
    return any(line.strip().lower() == str(NORMAL_TERMINAL).lower() for line in out.splitlines())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--since', required=True, help='YYYY-MM-DD (UTC)')
    args = ap.parse_args()
    if not normal_terminal_running():
        raise SystemExit('Normal MT5 is not running; refusing to start it. Open MT5 yourself and rerun.')
    import MetaTrader5 as mt5
    if not mt5.initialize(path=str(NORMAL_TERMINAL), timeout=60_000):
        raise SystemExit(f'MT5 attach failed: {mt5.last_error()}')
    try:
        acc = mt5.account_info(); term = mt5.terminal_info()
        if acc is None or term is None:
            raise SystemExit('No account info; is the terminal logged in?')
        since = datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc)
        deals = [{f: getattr(d, f) for f in FIELDS} for d in (mt5.history_deals_get(since, now_utc()) or [])]
        positions = [dict(ticket=p.ticket, magic=p.magic, symbol=p.symbol, type=p.type, volume=p.volume, price_open=p.price_open,
                          sl=p.sl, tp=p.tp, time=p.time, profit=p.profit, swap=p.swap, comment=p.comment) for p in (mt5.positions_get() or [])]
        snap = dict(fetched_utc=now_utc().isoformat(), since=args.since, terminal=str(NORMAL_TERMINAL),
                    account=dict(login_masked=f'****{str(acc.login)[-4:]}', server=acc.server, company=acc.company, currency=acc.currency,
                                 trade_mode=int(acc.trade_mode), margin_mode=int(acc.margin_mode), balance=acc.balance, equity=acc.equity,
                                 leverage=acc.leverage),
                    terminal_state=dict(connected=bool(term.connected), trade_allowed=bool(term.trade_allowed)),
                    deals=deals, open_positions=positions)
    finally:
        mt5.shutdown()
    folder = OUT / 'live'; folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"snapshot-{now_utc():%Y%m%dT%H%M}.json"
    path.write_text(json.dumps(snap, indent=0, default=str), encoding='utf-8')
    (folder / 'latest.json').write_text(json.dumps(snap, indent=0, default=str), encoding='utf-8')
    a = snap['account']
    print(f"{a['server']} {a['login_masked']} {a['currency']} trade_mode={a['trade_mode']} (0=demo) balance={a['balance']:.2f} equity={a['equity']:.2f} "
          f"| AutoTrading allowed={snap['terminal_state']['trade_allowed']} | {len(deals)} deals since {args.since}, {len(positions)} open positions -> {path.name}")


if __name__ == '__main__':
    main()
