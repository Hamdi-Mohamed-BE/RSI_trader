from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


RESEARCH_ROOT = Path(__file__).resolve().parent
PACKAGE_ROOT = RESEARCH_ROOT.parent
PIPELINE_ROOT = PACKAGE_ROOT.parent / "Calyx Research Pipeline"
TESTER_ROOT = PACKAGE_ROOT / "_Backtests" / "MT5-DMC-20260811"
TERMINAL = TESTER_ROOT / "terminal64.exe"
METAEDITOR = TESTER_ROOT / "MetaEditor64.exe"
SOURCE_ROOT = PACKAGE_ROOT / "AAA Final EAs" / "AAA Final News Pulse EA"
BASE_EXPERT = SOURCE_ROOT / "AAA Final News Pulse EA.ex5"
EXPERT_FOLDER = Path("AAA Research") / "News Pulse FXMacroData 20260910"
EXPERT_ROOT = TESTER_ROOT / "MQL5" / "Experts" / EXPERT_FOLDER
SET_ROOT = TESTER_ROOT / "MQL5" / "Profiles" / "Tester"
CONFIG_ROOT = TESTER_ROOT / "backtest-configs" / "news-pulse-fxmacrodata-20260910"
REPORT_ROOT = TESTER_ROOT / "reports" / "news-pulse-fxmacrodata-20260910"
OUTPUT_ROOT = RESEARCH_ROOT / "Schedule Replay Reports"
CALENDAR_INCLUDE = SOURCE_ROOT / "NewsPulseTesterCalendar.mqh"
CALENDAR_MANIFEST = RESEARCH_ROOT / "generated-calendar-manifest.json"
CALENDAR_RAW = RESEARCH_ROOT / "generated-calendar-mcp-raw.json"
TEST_START = "2026-06-12"
TEST_END = "2026-09-10"

CASES = (
    (
        "xauusd",
        "XAUUSD",
        PACKAGE_ROOT / "Selected Portfolio Settings 2026-09-01" / "12A News Pulse XAU Two Sided - HARD 1.5 TOTAL.set",
    ),
    (
        "xagusd",
        "XAGUSD",
        PACKAGE_ROOT / "Selected Portfolio Settings 2026-09-01" / "12B News Pulse XAG Two Sided - HARD 1.5 TOTAL.set",
    ),
    (
        "eurusd",
        "EURUSD",
        PACKAGE_ROOT / "Selected Portfolio Settings 2026-09-01" / "12C News Pulse EURUSD Two Sided - HARD 1.5 TOTAL.set",
    ),
)


def stop_isolated_terminal() -> None:
    environment = os.environ.copy()
    environment["CALYX_TESTER_TO_STOP"] = str(TERMINAL.resolve())
    command = (
        "$target=$env:CALYX_TESTER_TO_STOP; "
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -match '^terminal(64)?\\.exe$' -and $_.ExecutablePath -ieq $target } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
    )
    subprocess.run(
        ["powershell.exe", "-NoLogo", "-NoProfile", "-Command", command],
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def prepare_experts() -> None:
    EXPERT_ROOT.mkdir(parents=True, exist_ok=True)
    for dependency in (
        "AAA_Final_Common.mqh",
        "SafeRegimeFilter.mqh",
        "DynamicTrailingSessionFilter.mqh",
        "NewsPulseTesterCalendar.mqh",
    ):
        shutil.copy2(SOURCE_ROOT / dependency, EXPERT_ROOT / dependency)
    shutil.copy2(BASE_EXPERT, EXPERT_ROOT / "News Pulse Baseline.ex5")

    research_source = EXPERT_ROOT / "News Pulse FXMacroData.mq5"
    shutil.copy2(SOURCE_ROOT / "AAA Final News Pulse EA.mq5", research_source)
    compile_log = RESEARCH_ROOT / "compile-fxmacrodata-calendar.log"
    command = f'"{METAEDITOR}" /portable /compile:"{research_source}" /log:"{compile_log}"'
    subprocess.run(command, timeout=120, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    log = compile_log.read_text(encoding="utf-16", errors="ignore") if compile_log.exists() else ""
    # MetaEditor commonly returns process code 1 even when compilation succeeds;
    # its compiler summary and produced EX5 are the reliable success checks.
    if "0 errors" not in log.lower():
        raise RuntimeError(f"Research EA compilation failed. See {compile_log}")
    if not (EXPERT_ROOT / "News Pulse FXMacroData.ex5").is_file():
        raise RuntimeError("MetaEditor reported success but did not create the research EX5.")


def write_config(case_id: str, symbol: str, expert: str, set_name: str) -> tuple[Path, Path]:
    report_name = f"{case_id}--{expert.lower().replace(' ', '-')}"
    report_path = REPORT_ROOT / f"{report_name}.htm"
    relative_report = Path("reports") / "news-pulse-fxmacrodata-20260910" / f"{report_name}.htm"
    config_path = CONFIG_ROOT / f"{report_name}.ini"
    config = (
        "[Common]\r\n"
        "Login=472334559\r\n"
        "Server=Exness-MT5Trial16\r\n\r\n"
        "[Tester]\r\n"
        f"Expert={EXPERT_FOLDER}\\{expert}\r\n"
        f"ExpertParameters={set_name}\r\n"
        f"Symbol={symbol}\r\n"
        "Period=M1\r\n"
        "Login=472334559\r\n"
        "Deposit=10000\r\n"
        "Currency=USD\r\n"
        "Leverage=1:2000\r\n"
        "Model=0\r\n"
        "ExecutionMode=1\r\n"
        "Optimization=0\r\n"
        f"FromDate={TEST_START.replace('-', '.')}\r\n"
        f"ToDate={TEST_END.replace('-', '.')}\r\n"
        "ForwardMode=0\r\n"
        f"Report={relative_report}\r\n"
        "ReplaceReport=1\r\n"
        "ShutdownTerminal=1\r\n"
        "UseCloud=0\r\n"
        "Visual=0\r\n"
    )
    config_path.write_text(config, encoding="utf-16")
    return config_path, report_path


def run_test(config_path: Path, report_path: Path) -> None:
    report_path.unlink(missing_ok=True)
    stop_isolated_terminal()
    process = subprocess.Popen(
        [str(TERMINAL), "/portable", f"/config:{config_path.relative_to(TESTER_ROOT)}"],
        cwd=TESTER_ROOT,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        process.wait(timeout=1200)
    except subprocess.TimeoutExpired:
        process.kill()
        raise RuntimeError(f"MT5 timed out for {config_path.name}")
    if process.returncode not in (0, None):
        raise RuntimeError(f"MT5 exited with code {process.returncode} for {config_path.name}")
    if not report_path.is_file():
        raise RuntimeError(f"MT5 did not create {report_path}")


def input_value(report_path: Path, name: str) -> str | None:
    raw = report_path.read_bytes()
    text = raw.decode("utf-16", errors="ignore") if raw[:200].count(b"\x00") > 20 else raw.decode("utf-8", errors="ignore")
    match = re.search(rf"{re.escape(name)}=([^<\r\n]+)", text)
    return match.group(1).strip() if match else None


def on_tester_result(report_path: Path) -> float | None:
    raw = report_path.read_bytes()
    text = raw.decode("utf-16", errors="ignore") if raw[:200].count(b"\x00") > 20 else raw.decode("utf-8", errors="ignore")
    match = re.search(r"OnTester result:</td>\s*<td[^>]*><b>([-+0-9.,]+)</b>", text, re.IGNORECASE)
    if not match:
        return None
    return float(match.group(1).replace(",", ""))


def write_calendar_set(source: Path, destination: Path) -> None:
    text = source.read_text(encoding="utf-8-sig").rstrip() + "\n"
    fields = {
        "InpTesterFromDateUTC": TEST_START.replace("-", ""),
        "InpTesterToDateUTC": TEST_END.replace("-", ""),
    }
    for name, value in fields.items():
        pattern = re.compile(rf"^{re.escape(name)}=.*$", re.MULTILINE)
        replacement = f"{name}={value}"
        text = pattern.sub(replacement, text) if pattern.search(text) else text + replacement + "\n"
    destination.write_text(text, encoding="utf-8")


def main() -> int:
    if str(PIPELINE_ROOT) not in sys.path:
        sys.path.insert(0, str(PIPELINE_ROOT))
    from calyx_pipeline import parse_mt5_report
    from news_pulse_calendar import generate_calendar

    for path in (TERMINAL, METAEDITOR, BASE_EXPERT, *(row[2] for row in CASES)):
        if not path.is_file():
            raise FileNotFoundError(path)
    for path in (SET_ROOT, CONFIG_ROOT, REPORT_ROOT, OUTPUT_ROOT):
        path.mkdir(parents=True, exist_ok=True)
    manifest = generate_calendar(TEST_START, TEST_END, CALENDAR_INCLUDE, CALENDAR_MANIFEST, CALENDAR_RAW)
    prepare_experts()

    results = []
    for case_id, symbol, source_set in CASES:
        baseline_set_name = f"News Pulse Baseline {case_id}.set"
        calendar_set_name = f"News Pulse FXMacroData {case_id}.set"
        shutil.copy2(source_set, SET_ROOT / baseline_set_name)
        write_calendar_set(source_set, SET_ROOT / calendar_set_name)
        case_rows = []
        for variant, expert in (("baseline", "News Pulse Baseline"), ("fxmacrodata_schedule", "News Pulse FXMacroData")):
            print(f"Running {symbol} {variant}", flush=True)
            set_name = baseline_set_name if variant == "baseline" else calendar_set_name
            config_path, report_path = write_config(case_id, symbol, expert, set_name)
            run_test(config_path, report_path)
            if input_value(report_path, "InpRiskPercent") != "0.75":
                raise RuntimeError(f"{report_path.name} did not use the locked 0.75% per-stop risk")
            tester_result = on_tester_result(report_path)
            if variant == "fxmacrodata_schedule":
                if input_value(report_path, "InpTesterFromDateUTC") != TEST_START.replace("-", ""):
                    raise RuntimeError(f"{report_path.name} did not declare the requested calendar start")
                if input_value(report_path, "InpTesterToDateUTC") != TEST_END.replace("-", ""):
                    raise RuntimeError(f"{report_path.name} did not declare the requested calendar end")
                if tester_result != float(manifest["event_count"]):
                    raise RuntimeError(
                        f"{report_path.name} processed {tester_result} events; manifest requires {manifest['event_count']}"
                    )
            metadata, outcomes = parse_mt5_report(report_path)
            copied = OUTPUT_ROOT / f"{case_id}--{variant}.htm"
            shutil.copy2(report_path, copied)
            row = {
                "variant": variant,
                "report": str(copied),
                "metrics": metadata,
                "parsed_closed_trades": len(outcomes),
                "parsed_net_profit": round(sum(outcome.pnl for outcome in outcomes), 2),
                "on_tester_processed_events": tester_result,
            }
            case_rows.append(row)
        baseline, updated = case_rows
        results.append(
            {
                "asset": case_id,
                "symbol": symbol,
                "period": f"{TEST_START} to {TEST_END}",
                "baseline": baseline,
                "fxmacrodata_schedule": updated,
                "delta": {
                    "trades": updated["metrics"]["reported_trades"] - baseline["metrics"]["reported_trades"],
                    "net_profit": round(updated["metrics"]["reported_net_profit"] - baseline["metrics"]["reported_net_profit"], 2),
                    "return_pct": round(
                        100
                        * (updated["metrics"]["reported_net_profit"] - baseline["metrics"]["reported_net_profit"])
                        / baseline["metrics"]["initial_balance"],
                        2,
                    ),
                },
            }
        )

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Research-only Exness generated-tick replay",
        "change": "Replaced the research tester's manual date assumptions with the complete FXMacroData-generated UTC calendar for the requested window.",
        "calendar_manifest": str(CALENDAR_MANIFEST),
        "calendar_sha256": manifest["calendar_sha256"],
        "expected_events": manifest["event_count"],
        "production_source_changed": True,
        "deployed_ex5_changed": False,
        "results": results,
    }
    (RESEARCH_ROOT / "schedule-replay-results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
