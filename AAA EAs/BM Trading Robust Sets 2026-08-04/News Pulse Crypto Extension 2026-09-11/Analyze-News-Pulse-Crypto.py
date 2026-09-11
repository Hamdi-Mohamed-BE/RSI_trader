from __future__ import annotations

import argparse
import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LEGACY_ANALYZER = ROOT.parent / "News Pulse Direction Research 2026-09-05" / "Analyze-News-Pulse-Multi.py"
ASSETS = ("btcusd", "ethusd")


def load_legacy():
    spec = importlib.util.spec_from_file_location("news_pulse_legacy_analyzer", LEGACY_ANALYZER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {LEGACY_ANALYZER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_rows(stage: str) -> list[dict]:
    legacy = load_legacy()
    manifest_path = ROOT / "Backtest Reports" / stage / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if isinstance(manifest, dict):
        manifest = [manifest]
    return [legacy.parse_report(Path(meta["report"]), meta) for meta in manifest]


def save_rows(stage: str, rows: list[dict]) -> None:
    (ROOT / f"{stage.upper()} RESULTS.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    flat = [{key: value for key, value in row.items() if key not in {"series", "trade_returns"}} for row in rows]
    with (ROOT / f"{stage.upper()} RESULTS.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat[0]))
        writer.writeheader()
        writer.writerows(flat)


def select(stage: str, rows: list[dict]) -> None:
    picks = []
    for asset in ASSETS:
        candidates = [row for row in rows if row["asset"] == asset]
        best = max(candidates, key=lambda row: row["selection_score"])
        picks.append({
            "asset": asset,
            "symbol": best["symbol"],
            "direction": best["direction"],
            "geometry": best["geometry"],
            "entry_offset": best["entry_offset"],
            "stop_distance": best["stop_distance"],
            "trail_distance": best["trail_distance"],
            "management": best["management"],
            "placement_lead_seconds": best["placement_lead_seconds"],
            "close_seconds": best["close_seconds"],
            "dynamic": best["dynamic"],
            "development_return_pct": best["return_pct"],
            "development_profit_factor": best["profit_factor"],
            "development_drawdown_pct": best["max_drawdown_pct"],
            "development_trades": best["trades"],
            "selection_score": best["selection_score"],
        })
    name = "CALIBRATION SELECTION.json" if stage == "Calibration" else "DEVELOPMENT SELECTION.json"
    (ROOT / name).write_text(json.dumps(picks, indent=2), encoding="utf-8")


def finalize() -> None:
    required = {stage: ROOT / f"{stage.upper()} RESULTS.json" for stage in ("Calibration", "Management", "Locked", "Full", "Stress")}
    if not all(path.exists() for path in required.values()):
        return
    legacy = load_legacy()
    stages = {stage: json.loads(path.read_text(encoding="utf-8")) for stage, path in required.items()}
    monte_carlo = {row["asset"]: legacy.monte_carlo(row) for row in stages["Full"]}
    audit = {
        "test_design": {
            "development": "2025-09-01 to 2026-05-31",
            "locked": "2026-06-01 to 2026-09-01",
            "full": "2025-09-01 to 2026-09-01",
            "model": "MT5 Every Tick with Exness broker costs",
            "stress": "MT5 random execution delay",
            "risk_per_enabled_side_pct": 0.75,
            "maximum_two_sided_event_risk_pct": 1.5,
        },
        "selection": json.loads((ROOT / "DEVELOPMENT SELECTION.json").read_text(encoding="utf-8")),
        "stages": stages,
        "monte_carlo": monte_carlo,
    }
    (ROOT / "FINAL AUDIT.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")

    lines = [
        "# News Pulse crypto extension — review only",
        "",
        "These candidates use the same one-year NFP/CPI/FOMC event schedule and hard 0.75% risk per enabled stop as the deployed News Pulse family. They are not added to the portfolio.",
        "",
        "| Market | Direction | Entry / stop | Lead / forced exit | Development return / PF / trades | Locked return / PF / trades | Full return | PF | Win rate | Max DD | Trades | Random-delay return / PF | MC P5 return | MC P95 DD |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for asset in ASSETS:
        dev = next(row for row in stages["Management"] if row["asset"] == asset and row["case_id"] == next(item for item in audit["selection"] if item["asset"] == asset)["asset"] + "__" + next(item for item in audit["selection"] if item["asset"] == asset)["direction"] + "__" + next(item for item in audit["selection"] if item["asset"] == asset)["geometry"] + "__" + next(item for item in audit["selection"] if item["asset"] == asset)["management"])
        locked = next(row for row in stages["Locked"] if row["asset"] == asset)
        full = next(row for row in stages["Full"] if row["asset"] == asset)
        stress = next(row for row in stages["Stress"] if row["asset"] == asset)
        mc = monte_carlo[asset]
        lines.append(
            f"| {full['symbol']} | {full['direction']} | {full['entry_offset']:g} / {full['stop_distance']:g} | {full['placement_lead_seconds']}s / {full['close_seconds']}s | "
            f"{dev['return_pct']:+.2f}% / {dev['profit_factor']:.2f} / {dev['trades']} | "
            f"{locked['return_pct']:+.2f}% / {locked['profit_factor']:.2f} / {locked['trades']} | "
            f"{full['return_pct']:+.2f}% | {full['profit_factor']:.2f} | {full['win_rate_pct']:.2f}% | {full['max_drawdown_pct']:.2f}% | {full['trades']} | "
            f"{stress['return_pct']:+.2f}% / {stress['profit_factor']:.2f} | {mc['return_p5_pct']:+.2f}% | {mc['max_dd_p95_pct']:.2f}% |"
        )
    lines.extend([
        "",
        "Selection was made only on the development period. The locked quarter, full-year replay, random-delay run and Monte Carlo results were not used to choose parameters.",
    ])
    (ROOT / "FINAL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=("Calibration", "Management", "Locked", "Full", "Stress", "Verified"))
    args = parser.parse_args()
    rows = load_rows(args.stage)
    save_rows(args.stage, rows)
    if args.stage in {"Calibration", "Management"}:
        select(args.stage, rows)
    finalize()


if __name__ == "__main__":
    main()
