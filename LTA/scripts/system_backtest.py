from __future__ import annotations

from datetime import date, timedelta
import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import REPORTS_DIR


def run_command(command: list[str], cwd: Path) -> dict[str, Any]:
    result = subprocess.run(command, cwd=str(cwd), capture_output=True, text=True)
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout_tail": "\n".join(result.stdout.splitlines()[-80:]),
        "stderr_tail": "\n".join(result.stderr.splitlines()[-80:]),
    }


def latest(pattern: str, root: Path) -> str | None:
    matches = sorted(root.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    return str(matches[0]) if matches else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Precompute cached reports for the LTA dashboard.")
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--balance", type=float, default=300.0)
    parser.add_argument("--risk-pct", type=float, default=5.0)
    parser.add_argument("--skip-heavy", action="store_true", help="Only run the BPR backtest.")
    args = parser.parse_args()

    end_day = date.fromisoformat(args.end) if args.end else date.today()
    start_day = date.fromisoformat(args.start) if args.start else end_day - timedelta(days=max(1, args.days))
    py = str(ROOT / ".venv" / "Scripts" / "python.exe")
    if not Path(py).exists():
        py = sys.executable

    out_dir = REPORTS_DIR / "system_cache"
    out_dir.mkdir(parents=True, exist_ok=True)
    runs: dict[str, Any] = {}

    runs["bpr"] = run_command(
        [
            py,
            "scripts\\bpr_backtest.py",
            "--start",
            start_day.isoformat(),
            "--end",
            end_day.isoformat(),
            "--balance",
            str(args.balance),
            "--risk-pct",
            str(args.risk_pct),
        ],
        ROOT,
    )

    if not args.skip_heavy:
        runs["lta_orb"] = run_command(
            [
                py,
                "scripts\\dynamic_exit_backtest.py",
                "--start",
                start_day.isoformat(),
                "--end",
                end_day.isoformat(),
                "--balance",
                str(args.balance),
                "--risk-pct",
                str(args.risk_pct),
            ],
            ROOT,
        )
        runs["20pip"] = run_command(
            [
                py,
                "scripts\\orb_challenge_backtest.py",
                "--start",
                start_day.isoformat(),
                "--end",
                end_day.isoformat(),
            ],
            ROOT,
        )
        sniper_root = ROOT.parent / "sniper entry"
        if sniper_root.exists():
            runs["sniper"] = run_command(
                [
                    py,
                    "sniper_backtest.py",
                    "--start",
                    start_day.isoformat(),
                    "--end",
                    end_day.isoformat(),
                    "--balance",
                    str(args.balance),
                    "--risk-pct",
                    str(args.risk_pct),
                ],
                sniper_root,
            )

    report = {
        "created_at": date.today().isoformat(),
        "window_start": start_day.isoformat(),
        "window_end": end_day.isoformat(),
        "starting_balance": args.balance,
        "risk_pct": args.risk_pct,
        "runs": runs,
        "latest": {
            "bpr": latest("bpr_backtest/*/bpr_backtest_report.json", REPORTS_DIR),
            "lta_orb": latest("dynamic_exit_backtest/*/dynamic_exit_backtest_report.json", REPORTS_DIR),
            "20pip": latest("20pip_challenge_backtest/*/orb_challenge_backtest_report.json", REPORTS_DIR),
            "sniper": latest("reports/sniper_backtest/*/sniper_backtest_report.json", ROOT.parent / "sniper entry")
            if (ROOT.parent / "sniper entry").exists()
            else None,
        },
    }
    report_path = out_dir / f"system_backtest_{start_day}_{end_day}.json"
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"report": str(report_path), "latest": report["latest"]}, indent=2))


if __name__ == "__main__":
    main()
