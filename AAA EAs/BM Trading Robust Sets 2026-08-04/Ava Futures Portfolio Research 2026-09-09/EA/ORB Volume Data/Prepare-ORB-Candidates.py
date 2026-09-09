from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


def set_value(text: str, name: str, value) -> str:
    if isinstance(value, bool):
        rendered = "true" if value else "false"
    else:
        rendered = str(value)
    pattern = re.compile(rf"(?m)^{re.escape(name)}=[^|\r\n]*(?=\|\|)")
    if not pattern.search(text):
        raise KeyError(f"{name} is missing from the template")
    return pattern.sub(f"{name}={rendered}", text, count=1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("ranked", type=Path)
    parser.add_argument("template", type=Path)
    parser.add_argument("tester_set_dir", type=Path)
    parser.add_argument("config_dir", type=Path)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--top", type=int, default=8)
    parser.add_argument("--zone", type=int, default=0)
    parser.add_argument("--hour", type=int, default=9)
    parser.add_argument("--minute", type=int, default=30)
    parser.add_argument("--opening-range", type=int)
    parser.add_argument("--from-date", default="2025.01.01")
    parser.add_argument("--to-date", default="2025.08.06")
    args = parser.parse_args()

    rows = json.loads(args.ranked.read_text(encoding="utf-8"))[: args.top]
    base = args.template.read_text(encoding="utf-8-sig")
    args.tester_set_dir.mkdir(parents=True, exist_ok=True)
    args.config_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for index, row in enumerate(rows, start=1):
        candidate = base
        for name, value in row.items():
            if name.startswith("Inp"):
                candidate = set_value(candidate, name, value)
        candidate = set_value(candidate, "InpSessionZone", args.zone)
        candidate = set_value(candidate, "InpSessionHour", args.hour)
        candidate = set_value(candidate, "InpSessionMinute", args.minute)
        if args.opening_range is not None:
            candidate = set_value(candidate, "InpOpeningRangeMinutes", args.opening_range)
        candidate = set_value(candidate, "InpMagic", 86080700 + index)
        set_name = f"ORB {args.slug.upper()} Candidate {index:02d}.set"
        set_path = args.tester_set_dir / set_name
        set_path.write_text(candidate, encoding="utf-8", newline="")

        case_slug = f"select-{args.slug}-{index:02d}"
        config = f"""[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=BM Trading\\ORB Volume Data EA\\ORB Volume Data EA
ExpertParameters={set_name}
Symbol={args.symbol}
Period=M5
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=1
ExecutionMode=1
Optimization=0
FromDate={args.from_date}
ToDate={args.to_date}
ForwardMode=0
Report=reports\\orb-volume-data\\{case_slug}.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"""
        config_path = args.config_dir / f"{case_slug}.ini"
        config_path.write_text(config, encoding="utf-8-sig", newline="")
        manifest.append({"case": case_slug, "set": set_name, "config": str(config_path), "train": row})

    manifest_path = args.config_dir / f"select-{args.slug}-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Prepared {len(manifest)} candidates: {manifest_path}")


if __name__ == "__main__":
    main()
