from __future__ import annotations

import csv
import importlib.util
import json
import math
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
PARSER_PATH = PACKAGE / "BAT Portfolio Backtest 2026-08-09" / "Build-BAT-Portfolio-Report.py"
BASELINE_ROOT = ROOT / "Backtest Reports" / "Baseline"
SCREEN_ROOT = ROOT / "Backtest Reports" / "Training Screen"
FINAL_ROOT = ROOT / "Backtest Reports" / "Final Validation" / "BTC Four SMA b07"

spec = importlib.util.spec_from_file_location("existing_report_parser", PARSER_PATH)
parser = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(parser)


def parse(path: Path, label: str = "") -> dict:
    case = {
        "id": path.stem,
        "label": label or path.stem,
        "symbol": "",
        "period": "",
        "chart": "",
        "set_source": "",
    }
    return parser.parse_report(path, case)


def cagr(final: float, initial: float, years: float) -> float:
    if initial <= 0 or final <= 0 or years <= 0:
        return -100.0
    return ((final / initial) ** (1.0 / years) - 1.0) * 100.0


def row(path: Path, label: str, symbol: str, timeframe: str, years: float, phase: str) -> dict:
    data = parse(path, label)
    return {
        "phase": phase,
        "case": path.stem,
        "label": label,
        "symbol": symbol,
        "timeframe": timeframe,
        "initial": data["initial"],
        "final": data["final"],
        "net": data["net"],
        "return_pct": data["return_pct"],
        "cagr_pct": cagr(data["final"], data["initial"], years),
        "equity_dd_pct": data["equity_dd_pct"],
        "balance_dd_pct": data["balance_dd_pct"],
        "profit_factor": data["profit_factor"],
        "win_rate_pct": data["win_rate_pct"],
        "trades": data["trades"],
        "history_quality": data["history_quality"],
        "report": str(path),
    }


baseline_cases = {
    "xau-pullback": ("XAU Pullback Window", "XAUUSD", "M5"),
    "keltner-eurusd": ("FX Keltner Breakout", "EURUSD", "D1"),
    "keltner-gbpusd": ("FX Keltner Breakout", "GBPUSD", "D1"),
    "keltner-usdcad": ("FX Keltner Breakout", "USDCAD", "D1"),
    "keltner-nzdusd": ("FX Keltner Breakout", "NZDUSD", "D1"),
    "ustec-alt22": ("US100 Alt22 Donchian", "USTEC", "D1"),
    "us500-alt31": ("US500 Alt31 Donchian", "US500", "D1"),
    "btc-four-sma": ("BTC Four-SMA", "BTCUSD", "M5"),
    "us30-supply-demand": ("US30 Supply/Demand ATR", "US30", "H1"),
}

screen_group = {
    "x": ("XAU Pullback Window", "XAUUSD", "M5"),
    "eurusd": ("FX Keltner Breakout", "EURUSD", "D1"),
    "gbpusd": ("FX Keltner Breakout", "GBPUSD", "D1"),
    "usdcad": ("FX Keltner Breakout", "USDCAD", "D1"),
    "nzdusd": ("FX Keltner Breakout", "NZDUSD", "D1"),
    "ustec": ("US100 Alt22 Donchian", "USTEC", "D1"),
    "us500": ("US500 Alt31 Donchian", "US500", "D1"),
    "b": ("BTC Four-SMA", "BTCUSD", "M5"),
    "u": ("US30 Supply/Demand ATR", "US30", "H1"),
}


def screen_key(stem: str) -> str:
    for prefix in ("eurusd", "gbpusd", "usdcad", "nzdusd", "ustec", "us500"):
        if stem.startswith(prefix + "-"):
            return prefix
    if stem.startswith("x"):
        return "x"
    if stem.startswith("b"):
        return "b"
    if stem.startswith("u"):
        return "u"
    raise KeyError(stem)


def main() -> None:
    full_years = (date(2026, 8, 6) - date(2023, 8, 10)).days / 365.2425
    train_years = (date(2025, 8, 6) - date(2023, 8, 10)).days / 365.2425
    baseline = []
    for stem, (label, symbol, timeframe) in baseline_cases.items():
        baseline.append(row(BASELINE_ROOT / f"{stem}.htm", label, symbol, timeframe, full_years, "baseline-full"))

    manifest = json.loads((SCREEN_ROOT / "manifest.json").read_text(encoding="utf-8-sig"))
    manifest_labels = {item["Slug"]: item["Label"] for item in manifest}
    screens = []
    for path in sorted(SCREEN_ROOT.glob("*.htm")):
        key = screen_key(path.stem)
        strategy, symbol, timeframe = screen_group[key]
        label = manifest_labels.get(path.stem, path.stem)
        item = row(path, label, symbol, timeframe, train_years, "training-screen")
        item["strategy"] = strategy
        screens.append(item)

    best = []
    for key, (strategy, symbol, timeframe) in screen_group.items():
        candidates = [item for item in screens if item["strategy"] == strategy and item["symbol"] == symbol]
        best.append(max(candidates, key=lambda item: item["return_pct"]))

    final = [
        row(FINAL_ROOT / "btc-b07-oos-1y.htm", "BTC b07 untouched OOS", "BTCUSD", "M5", 1.0, "oos-validation"),
        row(FINAL_ROOT / "btc-b07-full-3y.htm", "BTC b07 full period", "BTCUSD", "M5", full_years, "full-validation"),
    ]

    fields = [
        "phase", "case", "label", "symbol", "timeframe", "initial", "final", "net", "return_pct",
        "cagr_pct", "equity_dd_pct", "balance_dd_pct", "profit_factor", "win_rate_pct", "trades",
        "history_quality", "report",
    ]
    with (ROOT / "ALL 104 TRAINING RESULTS.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(screens)
    with (ROOT / "BASELINE AND FINAL RESULTS.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(baseline + final)

    def table(items: list[dict], use_strategy: bool = False) -> list[str]:
        lines = [
            "| Strategy / case | Symbol / TF | Return | CAGR | PF | Win rate | Max equity DD | Trades |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
        for item in items:
            name = item.get("strategy", item["label"]) if use_strategy else item["label"]
            if use_strategy:
                name += f" (`{item['case']}`)"
            lines.append(
                f"| {name} | {item['symbol']} {item['timeframe']} | {item['return_pct']:+.2f}% | "
                f"{item['cagr_pct']:+.2f}% | {item['profit_factor']:.2f} | {item['win_rate_pct']:.2f}% | "
                f"{item['equity_dd_pct']:.2f}% | {item['trades']} |"
            )
        return lines

    lines = [
        "# Online research EAs — Exness backtest and 15% annual-return gate",
        "",
        "## Verdict",
        "",
        "**Accepted EAs: none.** Six dedicated EA entry points were created and compiled with zero errors/warnings, covering nine symbol tests. "
        "The only parameter set that exceeded 15% CAGR in the two-year training window was BTC `b07`; it then lost "
        "20.60% in the untouched final year, so it was rejected as unstable/overfit. Nothing was added to the active BAT.",
        "",
        "## Test protocol",
        "",
        "- Broker/symbol history: Exness demo, synchronized locally.",
        "- Account: USD 10,000, leverage 1:2000.",
        "- Risk: 1% per initial trade. Published Donchian pyramids can add units, so campaign exposure can exceed 1%.",
        "- Baseline/full period: 2023-08-10 through 2026-08-06.",
        "- Training screen: 2023-08-10 through 2025-08-06; 104 bounded variants.",
        "- Untouched validation: 2025-08-07 through 2026-08-06.",
        "- Final model: MT5 Every Tick generated from synchronized Exness M1 bars. Reported history quality is 98–100%. "
        "Exness did not provide the required historical real-tick archive for XAU, indices, or BTC, so no report is labeled real-tick.",
        "- Acceptance gate: at least 15% training CAGR and at least +15% return in the untouched final year; profitable PF required.",
        "",
        "## Published/default baseline — full three years",
        "",
        *table(baseline),
        "",
        "## Best training variant for each strategy/symbol",
        "",
        *table(best, use_strategy=True),
        "",
        "## BTC training winner — validation failure",
        "",
        *table(final),
        "",
        "The full-period BTC result (+16.61% total, about +5.26% CAGR) is not a pass: its final year was sharply negative, "
        "PF was only 1.04 over the full period, and max equity drawdown reached 28.41%.",
        "",
        "## Implementation scope",
        "",
        "- `Research FX Keltner Breakout EA`: direct implementation of the published daily Keltner/ATR/exit-MA rules; tested on EURUSD, GBPUSD, USDCAD, NZDUSD.",
        "- `Research US100 Alt22 Donchian EA` and `Research US500 Alt31 Donchian EA`: dedicated entry points sharing the tested Donchian/pyramid/trailing core.",
        "- `Research BTC Four SMA EA`: implements the paper's four-SMA crossover and trailing factor rules; the paper does not publish one transferable universal parameter vector.",
        "- `Research XAU Pullback Window EA`: reproduces the public state-machine logic and exposes ambiguous thresholds as inputs.",
        "- `Research US30 Supply Demand ATR EA`: labeled as a core reconstruction because the paper does not specify its passive filters sufficiently for an exact clone.",
        "",
        "## Files",
        "",
        "- `ALL 104 TRAINING RESULTS.csv`: every screened variant.",
        "- `BASELINE AND FINAL RESULTS.csv`: default baselines plus final BTC validation.",
        "- `Backtest Reports`: native MT5 HTML reports and equity charts.",
        "- `EA Packages`: per-EA source, EX5, sets, reports, and charts.",
    ]
    # BOM keeps em dashes and percentage ranges readable in Windows PowerShell/Notepad too.
    (ROOT / "RESEARCH RESULTS - 15PCT GATE.md").write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


if __name__ == "__main__":
    main()
