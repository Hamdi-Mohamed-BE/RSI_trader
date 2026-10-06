"""Central chronological date planner. No MT5, network, trading or optimization."""
from __future__ import annotations

import argparse
import calendar
import json
from datetime import date, datetime, timezone
from pathlib import Path

POLICY = Path(__file__).with_name("pipeline-policy.json")


def as_date(value: date | str) -> date:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).date() if value.tzinfo else value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value.replace(".", "-"))


def months_before(value: date, months: int) -> date:
    ordinal = value.year * 12 + value.month - 1 - months
    year, month_zero = divmod(ordinal, 12)
    month = month_zero + 1
    return date(year, month, min(value.day, calendar.monthrange(year, month)[1]))


def research_split(history_start: date | str, end_exclusive: date | str | None = None) -> dict:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    rules = policy["data_split"]
    if rules["final_out_of_sample_years"] != 2:
        raise ValueError("The user requires a final TWO-calendar-year OOS window")
    end = as_date(end_exclusive) if end_exclusive is not None else datetime.now(timezone.utc).date()
    start = as_date(history_start)
    oos_start = months_before(end, 24)
    validation_start = months_before(oos_start, rules["validation_months_before_oos"])
    if not start < validation_start < oos_start < end:
        raise ValueError("Insufficient older history for development + pre-OOS validation; do not shorten the two-year OOS")
    return {
        "policy_version": policy["version"],
        "boundary_convention": "start-inclusive, end-exclusive; UTC dates",
        "development": {"start": start.isoformat(), "end_exclusive": validation_start.isoformat()},
        "validation": {"start": validation_start.isoformat(), "end_exclusive": oos_start.isoformat()},
        "oos": {"start": oos_start.isoformat(), "end_exclusive": end.isoformat(), "calendar_years": 2},
        "selection_must_end_before_oos": True,
        "recent_subwindows_are_diagnostic_only": True,
        "untouched_status": "not asserted; study must disclose prior inspection and selection provenance",
    }


def validate_split(manifest: dict) -> None:
    expected = research_split(manifest["development"]["start"], manifest["oos"]["end_exclusive"])
    for section in ["development", "validation", "oos"]:
        if manifest[section] != expected[section]:
            raise ValueError(f"{section} dates do not match the current chronological two-year OOS policy")
    if manifest.get("selection_must_end_before_oos") is not True:
        raise ValueError("Selection must exclude OOS")


def validate_report_window(manifest: dict, report_start: date | str, report_end_exclusive: date | str) -> None:
    validate_split(manifest)
    if as_date(report_start).isoformat() != manifest["oos"]["start"] or as_date(report_end_exclusive).isoformat() != manifest["oos"]["end_exclusive"]:
        raise ValueError("Final OOS report must cover exactly the last TWO calendar years of the frozen study")


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan and freeze the mandatory last-two-year OOS split")
    parser.add_argument("--history-start", required=True)
    parser.add_argument("--end-exclusive", help="Default: today UTC (through yesterday); freeze once per study")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    split = research_split(args.history_start, args.end_exclusive)
    validate_split(split)
    body = json.dumps(split, indent=2) + "\n"
    if args.output:
        if args.output.exists():
            if json.loads(args.output.read_text(encoding="utf-8")) != split:
                parser.error("Existing frozen date split differs; create a new study revision, do not overwrite")
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(body, encoding="utf-8")
    print(body)


if __name__ == "__main__":
    main()
