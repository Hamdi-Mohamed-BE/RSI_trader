from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import xml.etree.ElementTree as ET


SS = "{urn:schemas-microsoft-com:office:spreadsheet}"


def parse_value(text: str):
    value = text.strip()
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    try:
        return float(value) if any(c in value for c in ".eE") else int(value)
    except ValueError:
        return value


def read_rows(path: Path) -> list[dict]:
    root = ET.parse(path).getroot()
    table = root.find(f".//{SS}Table")
    if table is None:
        raise RuntimeError(f"No optimization table found in {path}")
    raw_rows: list[list] = []
    for row in table.findall(f"{SS}Row"):
        values = []
        for cell in row.findall(f"{SS}Cell"):
            data = cell.find(f"{SS}Data")
            values.append(parse_value(data.text or "") if data is not None else "")
        raw_rows.append(values)
    if not raw_rows:
        return []
    headers = [str(item) for item in raw_rows[0]]
    return [dict(zip(headers, row)) for row in raw_rows[1:]]


def robust_score(row: dict) -> float:
    profit = float(row.get("Profit", 0) or 0)
    pf = float(row.get("Profit Factor", 0) or 0)
    recovery = float(row.get("Recovery Factor", 0) or 0)
    sharpe = float(row.get("Sharpe Ratio", 0) or 0)
    dd = float(row.get("Equity DD %", 0) or 0)
    trades = float(row.get("Trades", 0) or 0)
    if profit <= 0 or pf < 1.05 or trades < 40 or dd <= 0:
        return -1_000_000 + trades
    trade_weight = min(1.5, (trades / 100.0) ** 0.5)
    return (profit / dd) * trade_weight * min(pf, 2.5) * max(0.25, min(recovery, 4.0)) * max(0.25, min(sharpe + 0.5, 3.0))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("xml", type=Path)
    parser.add_argument("--top", type=int, default=30)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    rows = read_rows(args.xml)
    for row in rows:
        row["Robust Score"] = round(robust_score(row), 6)
    ranked = sorted(rows, key=lambda row: row["Robust Score"], reverse=True)
    selected = ranked[: max(args.top, 1)]
    output = args.out or args.xml.with_name(args.xml.stem + "-ranked.json")
    output.write_text(json.dumps(selected, indent=2), encoding="utf-8")
    csv_path = output.with_suffix(".csv")
    if selected:
        with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(selected[0]))
            writer.writeheader()
            writer.writerows(selected)
    print(json.dumps(selected[:10], indent=2))
    print(f"Parsed {len(rows)} passes; saved {len(selected)} to {output} and {csv_path}")


if __name__ == "__main__":
    main()
