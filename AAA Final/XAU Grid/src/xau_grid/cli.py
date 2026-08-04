from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

from .config import ROOT, load_config
from .engine import prepare_features, run_backtest
from .mt5_data import account_snapshot, connected, discover_xau, load_history, symbol_spec
from .reporting import write_markdown
from .research import optimize, save_result


def _history(days: int, refresh: bool):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    with connected():
        symbol = discover_xau(load_config().canonical_symbol)
        spec = symbol_spec(symbol)
        account = account_snapshot()
        cache = ROOT / "data" / f"{symbol.replace('.', '_')}_M5_{days}d.csv"
        data = load_history(symbol, start, end, cache, refresh=refresh)
    return symbol, spec, account, data


def _print_account(symbol: str, account: dict[str, object]) -> None:
    print(
        f"Account {account['login']} | {account['server']} | balance ${account['balance']:,.2f} | "
        f"equity ${account['equity']:,.2f} | leverage 1:{account['leverage']} | XAU alias {symbol}"
    )


def command_account(_: argparse.Namespace) -> int:
    with connected():
        symbol = discover_xau(load_config().canonical_symbol)
        _print_account(symbol, account_snapshot())
        print(symbol_spec(symbol))
    return 0


def command_backtest(args: argparse.Namespace) -> int:
    live = load_config()
    symbol, spec, account, data = _history(args.days, args.refresh)
    _print_account(symbol, account)
    result = run_backtest(data, live.strategy, spec, args.balance)
    output = ROOT / "reports" / "backtest"
    save_result(result, output, "selected")
    write_markdown(output / "REPORT.md", "XAU Safe Grid Backtest", result)
    print(json.dumps(result.summary(), indent=2, allow_nan=True))
    return 0


def command_optimize(args: argparse.Namespace) -> int:
    live = load_config()
    symbol, spec, account, data = _history(args.days, args.refresh)
    _print_account(symbol, account)
    selection, table = optimize(
        data, live.strategy, spec, args.balance, args.validation_days, args.holdout_days, args.top
    )
    output = ROOT / "reports" / "optimization"
    output.mkdir(parents=True, exist_ok=True)
    table.to_csv(output / "candidates.csv", index=False)
    save_result(selection.train, output, "train")
    save_result(selection.validation, output, "validation")
    save_result(selection.holdout, output, "holdout")
    write_markdown(output / "TRAIN.md", "XAU Grid Training Result", selection.train)
    holdout_score = (
        selection.holdout.return_pct
        - 2.5 * selection.holdout.max_drawdown_pct
        + 2.5 * min(selection.holdout.profit_factor, 5.0)
    )
    passed = (
        selection.score > -10_000
        and selection.holdout.trades >= 4
        and selection.holdout.profit_factor >= 1.10
        and selection.holdout.max_drawdown_pct <= 8.0
        and selection.holdout.return_pct > 0
    )
    note = "Validation gate: PASSED." if passed else "Validation gate: FAILED. Do not describe this set as safe."
    write_markdown(output / "VALIDATION.md", "XAU Grid Unseen Validation", selection.validation, note)
    write_markdown(output / "HOLDOUT.md", "XAU Grid Final Chronological Holdout", selection.holdout, note)
    payload = {
        "validation_gate_passed": passed,
        "score": selection.score,
        "holdout_score": holdout_score,
        "config": selection.config.to_dict(),
        "train": selection.train.summary(),
        "validation": selection.validation.summary(),
        "holdout": selection.holdout.summary(),
    }
    (output / "selected.json").write_text(json.dumps(payload, indent=2, allow_nan=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, allow_nan=True))
    return 0 if passed else 2


def command_live(_: argparse.Namespace) -> int:
    from .live import run_live

    run_live(load_config())
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="xau-grid", description="Risk-capped XAUUSD adaptive grid")
    commands = root.add_subparsers(dest="command", required=True)
    account = commands.add_parser("account", help="Show connected MT5 account and discovered symbol")
    account.set_defaults(func=command_account)
    for name, function, default_days in (("backtest", command_backtest, 365), ("optimize", command_optimize, 550)):
        item = commands.add_parser(name)
        item.add_argument("--days", type=int, default=default_days)
        item.add_argument("--balance", type=float, default=10_000.0)
        item.add_argument("--refresh", action="store_true")
        if name == "optimize":
            item.add_argument("--validation-days", type=int, default=120)
            item.add_argument("--holdout-days", type=int, default=90)
            item.add_argument("--top", type=int, default=32)
        item.set_defaults(func=function)
    live = commands.add_parser("live", help="Run the live monitor/executor")
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


if __name__ == "__main__":
    raise SystemExit(main())
