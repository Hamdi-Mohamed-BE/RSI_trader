from __future__ import annotations

import csv
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OPT_ROOT = ROOT / "Optimization Results"
SETS_ROOT = ROOT / "Sets"
BASE_SET = SETS_ROOT / "OPTIMIZE - Top Down FVG Liquidity - M15 - 1pct.set"
SYMBOLS = ("XAUUSD", "USTEC", "BTCUSD", "ETHUSD")
NS = "{urn:schemas-microsoft-com:office:spreadsheet}"


def read_rows(path: Path) -> list[dict[str, str]]:
    tree = ET.parse(path)
    rows = tree.findall(f".//{NS}Row")
    values: list[list[str]] = []
    for row in rows:
        current: list[str] = []
        for cell in row.findall(f"{NS}Cell"):
            data = cell.find(f"{NS}Data")
            current.append("" if data is None or data.text is None else data.text)
        values.append(current)
    if not values:
        return []
    header = values[0]
    return [dict(zip(header, row, strict=False)) for row in values[1:] if row]


def number(row: dict[str, str], key: str) -> float:
    try:
        return float(row.get(key, "nan"))
    except ValueError:
        return math.nan


def score(row: dict[str, str]) -> float:
    profit = number(row, "Profit")
    pf = number(row, "Profit Factor")
    recovery = number(row, "Recovery Factor")
    dd = number(row, "Equity DD %")
    trades = number(row, "Trades")
    if not all(math.isfinite(value) for value in (profit, pf, recovery, dd, trades)):
        return -math.inf
    if profit <= 0 or pf < 1.02 or dd <= 0 or dd > 30 or trades < 40:
        return -math.inf
    return (min(pf, 3.0) - 1.0) * math.sqrt(trades) * max(recovery, 0.1) / (1.0 + dd / 10.0)


def selected_row(rows: list[dict[str, str]]) -> dict[str, str]:
    ranked = sorted(rows, key=score, reverse=True)
    if ranked and math.isfinite(score(ranked[0])):
        return ranked[0]
    fallback = [row for row in rows if number(row, "Profit") > 0 and number(row, "Trades") >= 15]
    if not fallback:
        raise RuntimeError("Optimization produced no positive candidate with at least 15 trades")
    return max(fallback, key=lambda row: (number(row, "Profit Factor"), -number(row, "Equity DD %")))


def write_set(symbol: str, row: dict[str, str]) -> Path:
    optimised = {
        "InpBiasMode",
        "InpSweepLookbackBars",
        "InpDisplacementBodyATR",
        "InpRetestExpiryBars",
        "InpRewardRisk",
        "InpBreakEvenAtR",
    }
    output: list[str] = []
    for raw in BASE_SET.read_text(encoding="utf-8-sig").splitlines():
        if "=" not in raw:
            output.append(raw)
            continue
        name, values = raw.split("=", 1)
        parts = values.split("||")
        if name in optimised:
            chosen = row[name]
            if name in {"InpBiasMode", "InpSweepLookbackBars", "InpRetestExpiryBars"}:
                chosen = str(int(float(chosen)))
            parts[0] = chosen
            if len(parts) >= 5:
                parts[4] = "N"
        output.append(name + "=" + "||".join(parts))
    path = SETS_ROOT / f"SELECTED - {symbol} M15 - Top Down FVG Liquidity - 1pct.set"
    path.write_text("\n".join(output) + "\n", encoding="utf-8-sig")
    return path


def main() -> None:
    summary: list[dict[str, object]] = []
    for symbol in SYMBOLS:
        rows = read_rows(OPT_ROOT / f"{symbol.lower()}.xml")
        chosen = selected_row(rows)
        set_path = write_set(symbol, chosen)
        chosen_score = score(chosen)
        summary.append(
            {
                "symbol": symbol,
                "passes": len(rows),
                "training_period": "2021-01-01 to 2024-12-31",
                "profit": number(chosen, "Profit"),
                "profit_factor": number(chosen, "Profit Factor"),
                "equity_dd_pct": number(chosen, "Equity DD %"),
                "trades": int(number(chosen, "Trades")),
                "recovery_factor": number(chosen, "Recovery Factor"),
                "score": chosen_score if math.isfinite(chosen_score) else None,
                "parameters": {
                    key: chosen[key]
                    for key in (
                        "InpBiasMode",
                        "InpSweepLookbackBars",
                        "InpDisplacementBodyATR",
                        "InpRetestExpiryBars",
                        "InpRewardRisk",
                        "InpBreakEvenAtR",
                    )
                },
                "set_path": str(set_path),
            }
        )
    (ROOT / "optimization-selection.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with (ROOT / "optimization-selection.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["symbol", "passes", "profit", "profit_factor", "equity_dd_pct", "trades", "recovery_factor", "score", "set_path"])
        writer.writeheader()
        for row in summary:
            writer.writerow({key: row[key] for key in writer.fieldnames})
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
