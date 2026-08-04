from __future__ import annotations

from pathlib import Path

from .engine import BacktestResult


def _metric_rows(result: BacktestResult) -> list[tuple[str, str]]:
    pf = "∞" if result.profit_factor == float("inf") else f"{result.profit_factor:.2f}"
    return [
        ("Period", f"{result.start:%Y-%m-%d} to {result.end:%Y-%m-%d}"),
        ("Trades", str(result.trades)),
        ("Wins / losses", f"{result.wins} / {result.losses}"),
        ("Win rate", f"{result.win_rate:.2f}%"),
        ("Profit factor", pf),
        ("Net profit", f"${result.net_profit:,.2f}"),
        ("Ending balance", f"${result.ending_balance:,.2f}"),
        ("Return", f"{result.return_pct:+.2f}%"),
        ("Max equity DD", f"{result.max_drawdown_pct:.2f}%"),
        ("Realized DD", f"{result.realized_drawdown_pct:.2f}%"),
        ("Max exposure at stop", f"{result.exposure_pct_max:.2f}%"),
        ("Max consecutive losses", str(result.max_consecutive_losses)),
    ]


def write_markdown(path: Path, title: str, result: BacktestResult, note: str = "") -> None:
    lines = [f"# {title}", "", "| Metric | Result |", "|---|---:|"]
    lines.extend(f"| {name} | {value} |" for name, value in _metric_rows(result))
    if note:
        lines.extend(["", note])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
