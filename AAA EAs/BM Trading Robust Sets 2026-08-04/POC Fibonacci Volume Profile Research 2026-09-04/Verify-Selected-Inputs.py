from __future__ import annotations

import json
import math
import re
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent
SYMBOLS = ("xauusd", "xagusd", "btcusd", "us30", "ustec", "gbpjpy")


def values_from_set(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if "=" in line and not line.lstrip().startswith(";"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def values_from_report(path: Path) -> dict[str, str]:
    raw = path.read_bytes()
    text = raw.decode("utf-16")
    soup = BeautifulSoup(text, "html.parser")
    values: dict[str, str] = {}
    for bold in soup.find_all("b"):
        item = " ".join(bold.get_text(" ", strip=True).split())
        if re.fullmatch(r"Inp[A-Za-z0-9_]+=.*", item):
            key, value = item.split("=", 1)
            values[key] = value
    return values


def equivalent(expected: str, actual: str) -> bool:
    if expected.lower() in {"true", "false"} or actual.lower() in {"true", "false"}:
        return expected.lower() == actual.lower()
    try:
        return math.isclose(float(expected), float(actual), rel_tol=0.0, abs_tol=1e-9)
    except ValueError:
        return expected == actual


def main() -> None:
    cases = []
    for phase in ("locked", "full"):
        for symbol in SYMBOLS:
            set_path = ROOT / "Sets" / f"POCFib-{symbol}--optimized--{phase}.set"
            report_path = ROOT / "Backtest Reports" / phase / f"{symbol}--optimized--{phase}.htm"
            expected = values_from_set(set_path)
            actual = values_from_report(report_path)
            mismatches = {
                key: {"expected": value, "actual": actual.get(key)}
                for key, value in expected.items()
                if key not in actual or not equivalent(value, actual[key])
            }
            cases.append(
                {
                    "symbol": symbol.upper(),
                    "phase": phase,
                    "checked_inputs": len(expected),
                    "mismatches": mismatches,
                    "passed": not mismatches,
                }
            )
    payload = {
        "policy": "Every saved optimized set input must match the native MT5 report input.",
        "cases": cases,
        "all_passed": all(case["passed"] for case in cases),
        "total_checked_values": sum(case["checked_inputs"] for case in cases),
    }
    (ROOT / "SETTINGS VERIFICATION.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
