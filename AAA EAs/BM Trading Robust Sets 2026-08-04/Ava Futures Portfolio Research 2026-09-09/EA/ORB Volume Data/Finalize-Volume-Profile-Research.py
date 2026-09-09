from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
BT = PACKAGE / "_Backtests" / "MT5-Isolated-20260805"
TESTER = BT / "MQL5" / "Profiles" / "Tester"
SOURCE_REPORTS = BT / "reports" / "orb-volume-profile"
REPORTS = ROOT / "Volume Profile Reports"
SETTINGS = ROOT / "Volume Profile Settings"
REJECTED = SETTINGS / "Research Rejected"

BASES = {
    "xau": ("XAUUSD", "VALIDATED - XAUUSD M5 - 1pct.set", True, "validated baseline"),
    "btc": ("BTCUSD", "REJECTED FINAL - BTCUSD M5 - 1pct.set", False, "research only - unprofitable final year"),
    "us30": ("US30", "VALIDATED MODEST - US30 M5 - 1pct.set", True, "modest baseline"),
    "ustec": ("USTEC", "REJECTED FINAL - USTEC M5 - 1pct.set", False, "research only - unprofitable final year"),
    "us500": ("US500", "REJECTED FINAL - US500 M5 - 1pct.set", False, "research only - unprofitable final year"),
}


def load_prepare_module():
    path = ROOT / "Prepare-Volume-Profile-Research.py"
    spec = importlib.util.spec_from_file_location("prepare_vp", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def load_results(name: str) -> list[dict]:
    return json.loads((ROOT / f"volume-profile-{name}-results.json").read_text(encoding="utf-8"))


def by_key(rows: list[dict]) -> dict[tuple[str, str], dict]:
    return {(row["market"], row["variant"]): row for row in rows}


def fmt(row: dict) -> str:
    return (f"{row['return_pct']:+.2f}% / {row['equity_dd_pct']:.2f}% / "
            f"{row['profit_factor']:.2f} / {row['trades']}")


def main() -> None:
    prepare = load_prepare_module()
    REPORTS.mkdir(parents=True, exist_ok=True)
    SETTINGS.mkdir(parents=True, exist_ok=True)
    REJECTED.mkdir(parents=True, exist_ok=True)

    for key, (symbol, source_name, enabled, label) in BASES.items():
        original = (ROOT / "Best Settings" / source_name).read_text(encoding="utf-8-sig")
        visual = prepare.inject_profile_inputs(original, (False, False, False, 1.0))
        visual = visual.replace("InpShowProfileLevels=false||", "InpShowProfileLevels=true||")
        if not enabled:
            visual = visual.replace("InpEnableTrading=true||", "InpEnableTrading=false||")
        (SETTINGS / f"VISUAL PROFILE - {symbol} M5 - {label}.set").write_text(visual, encoding="utf-8-sig")

    rejected_candidates = {
        "XAUUSD": "va",
        "BTCUSD": "lvn100",
        "USTEC": "va",
    }
    for symbol, variant in rejected_candidates.items():
        source = TESTER / f"ORBVP {symbol} {variant}.set"
        shutil.copy2(source, REJECTED / f"FAILED FINAL - {symbol} {variant}.set")

    for source in SOURCE_REPORTS.glob("*.htm"):
        shutil.copy2(source, REPORTS / source.name)
        graph = source.with_suffix(".png")
        if graph.exists():
            shutil.copy2(graph, REPORTS / graph.name)

    dev = by_key(load_results("dev"))
    selection = by_key(load_results("selection"))
    final = by_key(load_results("final"))
    chosen = {
        "xau": "va",
        "btc": "lvn100",
        "us30": "control",
        "ustec": "va",
        "us500": "control",
    }

    lines = [
        "# ORB tick-activity volume-profile research",
        "",
        "## Honest conclusion",
        "",
        "The volume profile is useful as context and as an on-chart explanation, but the tested filters did not earn automatic live activation. XAUUSD's value-area filter reduced the final-year return too much. BTCUSD and USTEC filters reduced their losses but remained unprofitable. US30 and US500 were better left unchanged.",
        "",
        "The recommended live behavior is therefore: show the profile, but leave all three profile filters disabled. The original XAUUSD baseline remains validated and the original US30 baseline remains a modest pass. BTCUSD, USTEC, and US500 remain research-only with trading disabled in the supplied visual presets.",
        "",
        "## What the chart means",
        "",
        "- POC (orange): the price bin with the most Exness quote-tick activity from 08:00 New York through the end of the opening range.",
        "- VAH / VAL (blue): the upper and lower edges of the contiguous bins around POC containing 70% of that activity.",
        "- OR-high / OR-low node ratio: activity in the price bin touching that opening-range boundary divided by average activity per bin. Below 1.00 is relatively thin; above 1.00 is relatively heavy.",
        "- A value-area breakout closes beyond both the opening range and the relevant value-area edge. A POC bias asks that POC sit on the opposite half of the range. The LVN filter accepts only a boundary ratio at or below 1.00.",
        "",
        "This is a broker tick-activity profile, not centralized exchange traded volume. It counts quote ticks by midpoint price because Exness CFD history does not provide a single consolidated CME/NYSE volume feed.",
        "",
        "## Locked comparison",
        "",
        "All figures use USD 10,000 initial balance, 1% equity risk per trade, MT5 Every Tick, random execution delay, and the New York 09:30 opening range. Cells show return / max equity DD / PF / trades.",
        "US30's 2024 PF of 107.67 comes from only nine trades and must not be treated as a stable estimate.",
        "",
        "| Market | Candidate chosen before final | 2024 development | Jan-Aug 2025 selection | Last-year candidate | Last-year control | Decision |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    labels = {"xau": "XAUUSD", "btc": "BTCUSD", "us30": "US30", "ustec": "USTEC", "us500": "US500"}
    decisions = {
        "xau": "Reject filter; retain control",
        "btc": "Reject market; filter still loses",
        "us30": "Retain modest control",
        "ustec": "Reject market; filter still loses",
        "us500": "Reject market; retain research control",
    }
    for market in ["xau", "btc", "us30", "ustec", "us500"]:
        variant = chosen[market]
        lines.append(
            f"| {labels[market]} | {variant} | {fmt(dev[(market, variant)])} | "
            f"{fmt(selection[(market, variant)])} | {fmt(final[(market, variant)])} | "
            f"{fmt(final[(market, 'control')])} | {decisions[market]} |"
        )

    lines += [
        "",
        "## No-lookahead safeguards",
        "",
        "- Profile window ends at the opening-range close; later ticks are never included.",
        "- New York daylight-saving conversion is automatic.",
        "- The profile inputs were selected on 2024 development plus Jan-Aug 2025 selection data before the final-year comparison.",
        "- The final-year result was not used to retune thresholds after it ran.",
        "",
        "## Files",
        "",
        "- `Volume Profile Settings`: safe visual presets. Trading remains enabled only for XAUUSD and US30.",
        "- `Volume Profile Settings/Research Rejected`: tested filters that failed the final-year acceptance test.",
        "- `Volume Profile Reports`: native MT5 reports and equity graphs for audit.",
    ]
    (ROOT / "VOLUME PROFILE REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Volume-profile presets and report finalized.")


if __name__ == "__main__":
    main()
