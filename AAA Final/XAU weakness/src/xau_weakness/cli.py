from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

from .config import ROOT, load_config
from .engine import run_backtest
from .mt5_data import account_snapshot, connected, discover_xau, load_history, symbol_spec
from .research import optimize


def _history(days: int, refresh: bool):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    config = load_config()
    with connected():
        symbol = discover_xau(config.canonical_symbol)
        spec = symbol_spec(symbol)
        account = account_snapshot()
        data = load_history(symbol, start, end, ROOT / "data" / f"{symbol}_M15_{days}d.csv", refresh)
    print(
        f"Account {account['login']} | {account['server']} | balance {account['balance']:,.2f} {account['currency']} | "
        f"equity {account['equity']:,.2f} | leverage 1:{account['leverage']} | XAU alias {symbol}"
    )
    return symbol, spec, data


def _save_result(folder: Path, name: str, result) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}_summary.json").write_text(json.dumps(result.summary(), indent=2, allow_nan=True), encoding="utf-8")
    import pandas as pd
    pd.DataFrame([item.to_dict() for item in result.records]).to_csv(folder / f"{name}_trades.csv", index=False)
    result.equity.to_csv(folder / f"{name}_equity.csv")


def command_backtest(args) -> int:
    config = load_config()
    _, spec, data = _history(args.days, args.refresh)
    result = run_backtest(data, config.strategy, spec, args.balance)
    _save_result(ROOT / "reports" / "backtest", "selected", result)
    print(json.dumps(result.summary(), indent=2, allow_nan=True))
    return 0


def command_optimize(args) -> int:
    config = load_config()
    _, spec, data = _history(args.days, args.refresh)
    selection, candidates = optimize(data, config.strategy, spec, args.balance)
    folder = ROOT / "reports" / "optimization"
    folder.mkdir(parents=True, exist_ok=True)
    candidates.to_csv(folder / "candidates.csv", index=False)
    for name in ("train", "validation", "holdout"):
        _save_result(folder, name, getattr(selection, name))
    payload = {
        "validation_gate_passed": selection.gate_passed,
        "config": selection.config.to_dict(),
        "train": selection.train.summary(), "validation": selection.validation.summary(),
        "holdout": selection.holdout.summary(),
    }
    (folder / "selected.json").write_text(json.dumps(payload, indent=2, allow_nan=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, allow_nan=True))
    return 0 if selection.gate_passed else 2


def command_account(_args) -> int:
    with connected():
        symbol = discover_xau(load_config().canonical_symbol)
        print(account_snapshot())
        print(symbol_spec(symbol))
    return 0


def command_live(args) -> int:
    from .live import run_live
    run_live(load_config(), once=args.once)
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="xau-weakness")
    commands = root.add_subparsers(dest="command", required=True)
    account = commands.add_parser("account")
    account.set_defaults(func=command_account)
    for name, function, days in (("backtest", command_backtest, 365), ("optimize", command_optimize, 365)):
        item = commands.add_parser(name)
        item.add_argument("--days", type=int, default=days)
        item.add_argument("--balance", type=float, default=10_000.0)
        item.add_argument("--refresh", action="store_true")
        item.set_defaults(func=function)
    live = commands.add_parser("live")
    live.add_argument("--once", action="store_true")
    live.set_defaults(func=command_live)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        print("Stopped by user.")
        return 130
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
