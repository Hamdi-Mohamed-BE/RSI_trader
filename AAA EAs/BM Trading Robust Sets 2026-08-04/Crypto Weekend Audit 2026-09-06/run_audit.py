from __future__ import annotations

import csv
import importlib.util
import json
import shutil
import subprocess
import time
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
TESTER = PACKAGE / "_Backtests" / "MT5-DMC-20260811"
METAEDITOR = TESTER / "MetaEditor64.exe"
TERMINAL = TESTER / "terminal64.exe"
PARSER_PATH = PACKAGE / "US100 Momentum Continuation Research 2026-08-31" / "Analyze-Reports.py"
spec = importlib.util.spec_from_file_location("mt5_report_parser", PARSER_PATH)
parser = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(parser)

CASES = (
    {
        "strategy": "BTC Top-Down FVG", "slug": "btc-topdown", "symbol": "BTCUSD", "period": "M15",
        "source": PACKAGE / "Top Down FVG Liquidity Research 2026-08-27" / "EA" / "Top Down FVG Liquidity EA.mq5",
        "set": PACKAGE / "Selected Portfolio Settings 2026-09-01" / "02 BTC Top Down FVG Liquidity - CURRENT - ALL DAY.set",
    },
    {
        "strategy": "ETH Top-Down FVG", "slug": "eth-topdown", "symbol": "ETHUSD", "period": "M15",
        "source": PACKAGE / "Top Down FVG Liquidity Research 2026-08-27" / "EA" / "Top Down FVG Liquidity EA.mq5",
        "set": PACKAGE / "Selected Portfolio Settings 2026-09-01" / "03 ETH Top Down FVG Liquidity - DYNAMIC 50-20 - ALL DAY.set",
    },
    {
        "strategy": "BTC POC Fibonacci", "slug": "btc-pocfib", "symbol": "BTCUSD", "period": "M15",
        "source": PACKAGE / "POC Fibonacci Volume Profile Research 2026-09-04" / "EA" / "POC Fibonacci Volume Profile EA.mq5",
        "set": PACKAGE / "POC Fibonacci Volume Profile Research 2026-09-04" / "Sets" / "POCFib-btcusd--optimized--locked.set",
    },
)
WINDOWS = {
    "locked": ("2025.09.01", "2026.09.01"),
    "three-year": ("2023.09.01", "2026.09.01"),
}


def upsert(text: str, key: str, value: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith(key + "="):
            suffix = line.split("||", 1)[1] if "||" in line else ""
            lines[index] = f"{key}={value}" + ("||" + suffix if suffix else "")
            break
    else:
        lines.append(f"{key}={value}")
    return "\r\n".join(lines) + "\r\n"


def compile_ea(source: Path) -> None:
    log = ROOT / "Compile" / (source.stem + ".log")
    log.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        f'"{METAEDITOR}" /portable /compile:"{source}" /log:"{log}"',
        timeout=120, creationflags=subprocess.CREATE_NO_WINDOW,
    )
    text = log.read_text(encoding="utf-16") if log.exists() else ""
    if "0 errors, 0 warnings" not in text or not source.with_suffix(".ex5").exists():
        raise RuntimeError(f"Compile failure for {source}:\n{text[-5000:]}")
    print("COMPILE", source.name, "0 errors, 0 warnings", flush=True)


def prepare() -> tuple[Path, Path, Path]:
    for source in {case["source"] for case in CASES}:
        compile_ea(source)
    expert_dir = TESTER / "MQL5" / "Experts" / "AAA Research" / "Crypto Weekend Audit 20260906"
    set_dir = TESTER / "MQL5" / "Profiles" / "Tester"
    config_dir = TESTER / "backtest-configs" / "crypto-weekend-audit-20260906"
    report_dir = TESTER / "reports" / "crypto-weekend-audit-20260906"
    for path in (expert_dir, set_dir, config_dir, report_dir, ROOT / "Reports", ROOT / "Sets"):
        path.mkdir(parents=True, exist_ok=True)
    config_source = Path(r"C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\config")
    isolated = TESTER / "Config"; isolated.mkdir(exist_ok=True)
    for name in ("accounts.dat", "servers.dat", "common.ini"):
        if (config_source / name).exists():
            shutil.copy2(config_source / name, isolated / name)
    copied = set()
    for case in CASES:
        source = case["source"]
        if source not in copied:
            shutil.copy2(source.with_suffix(".ex5"), expert_dir / source.with_suffix(".ex5").name)
            copied.add(source)
    return expert_dir, set_dir, config_dir


def run_case(case: dict, stage: str, weekdays: bool, set_dir: Path, config_dir: Path, timeout: int = 1200) -> dict:
    mode = "weekdays" if weekdays else "all-days"
    case_id = f"{case['slug']}--{stage}--{mode}"
    output_dir = ROOT / "Reports"
    result_path = output_dir / (case_id + ".json")
    if result_path.exists():
        return json.loads(result_path.read_text(encoding="utf-8"))
    set_name = case_id + ".set"
    set_text = upsert(case["set"].read_text(encoding="utf-8-sig"), "InpWeekdaysOnly", str(weekdays).lower())
    (ROOT / "Sets" / set_name).write_text(set_text, encoding="utf-8")
    (set_dir / set_name).write_text(set_text, encoding="utf-8")
    expert_name = case["source"].stem
    start, end = WINDOWS[stage]
    report_rel = f"reports\\crypto-weekend-audit-20260906\\{case_id}.htm"
    tester_report = TESTER / "reports" / "crypto-weekend-audit-20260906" / (case_id + ".htm")
    ini = config_dir / (case_id + ".ini")
    ini.write_text(f"""[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=AAA Research\\Crypto Weekend Audit 20260906\\{expert_name}
ExpertParameters={set_name}
Symbol={case['symbol']}
Period={case['period']}
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=0
ExecutionMode=1
Optimization=0
FromDate={start}
ToDate={end}
ForwardMode=0
Report={report_rel}
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
""", encoding="utf-8-sig")
    print("START", case_id, flush=True); began = time.monotonic()
    subprocess.run(f'"{TERMINAL}" /portable /profile:"Calyx Research Empty" /config:"{ini}"', timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW)
    if not tester_report.exists():
        raise RuntimeError("MT5 produced no report for " + case_id)
    for report in tester_report.parent.glob(case_id + "*"):
        shutil.copy2(report, output_dir / report.name)
    result = parser.parse_report(output_dir / (case_id + ".htm"))
    result.update(strategy=case["strategy"], symbol=case["symbol"], stage=stage, weekdays_only=weekdays,
                  from_date=start, to_date=end, model=0, elapsed_seconds=round(time.monotonic() - began, 2))
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("DONE", case_id, {k: result[k] for k in ("return_pct", "profit_factor", "win_rate", "equity_dd_pct", "trades")}, flush=True)
    return result


def keep_weekdays(all_days: dict, weekdays: dict) -> bool:
    return (
        weekdays["trades"] >= 15
        and weekdays["return_pct"] > all_days["return_pct"]
        and weekdays["profit_factor"] > all_days["profit_factor"]
        and weekdays["equity_dd_pct"] <= all_days["equity_dd_pct"]
    )


def report(rows: list[dict]) -> None:
    keyed = {(r["strategy"], r["stage"], r["weekdays_only"]): r for r in rows}
    decisions = {}
    for case in CASES:
        strategy = case["strategy"]
        locked_pass = keep_weekdays(keyed[strategy, "locked", False], keyed[strategy, "locked", True])
        full_pass = keep_weekdays(keyed[strategy, "three-year", False], keyed[strategy, "three-year", True])
        decisions[strategy] = {"disable_weekends": locked_pass and full_pass, "locked_pass": locked_pass, "three_year_pass": full_pass}
    (ROOT / "decisions.json").write_text(json.dumps(decisions, indent=2), encoding="utf-8")
    flat = [{k: v for k, v in row.items() if k != "series"} for row in rows]
    with (ROOT / "results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=flat[0].keys(), extrasaction="ignore"); writer.writeheader(); writer.writerows(flat)
    (ROOT / "results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")

    plt.style.use("dark_background")
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.8), constrained_layout=True); fig.patch.set_facecolor("#06110f")
    for ax, case in zip(axes, CASES):
        strategy = case["strategy"]
        for weekdays, color, label in ((False, "#74b9ff", "All days"), (True, "#55efc4", "Mon–Fri")):
            row = keyed[strategy, "three-year", weekdays]
            frame = pd.DataFrame(row["series"]); frame["date"] = pd.to_datetime(frame["date"], format="mixed")
            ax.plot(frame.date, frame.balance, color=color, lw=1.7, label=label)
        ax.set_title(strategy, loc="left", weight="bold"); ax.set_facecolor("#081916"); ax.grid(color="#28433e", alpha=.35)
        ax.tick_params(axis="x", rotation=25); ax.legend()
    fig.suptitle("Crypto weekend filter — exact three-year native MT5 comparison", fontsize=18, color="#88f7cf", weight="bold")
    fig.savefig(ROOT / "weekend-filter-comparison.png", dpi=160, facecolor=fig.get_facecolor()); plt.close(fig)

    lines = ["# Crypto Weekend Audit — 2026-09-06", "", "Native MT5 Every Tick comparison at the exact selected 1% risk presets.", "",
             "| EA | Horizon | Mode | Return | PF | Win rate | DD | Trades |", "|---|---|---|---:|---:|---:|---:|---:|"]
    for case in CASES:
        for stage in WINDOWS:
            for weekdays in (False, True):
                row = keyed[case["strategy"], stage, weekdays]
                lines.append(f"| {case['strategy']} | {stage} | {'Mon–Fri' if weekdays else 'All days'} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | {row['win_rate']:.2f}% | {row['equity_dd_pct']:.2f}% | {row['trades']} |")
    lines += ["", "## Mechanical decision", ""]
    for strategy, decision in decisions.items():
        text = "DISABLE WEEKENDS" if decision["disable_weekends"] else "KEEP WEEKENDS"
        lines.append(f"- **{strategy}: {text}.** Required return and PF to rise and DD to fall in both horizons with at least 15 remaining trades.")
    (ROOT / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    _, set_dir, config_dir = prepare(); rows = []
    for case in CASES:
        for stage in WINDOWS:
            for weekdays in (False, True):
                rows.append(run_case(case, stage, weekdays, set_dir, config_dir))
    report(rows)
    print("AUDIT COMPLETE", ROOT / "REPORT.md", flush=True)


if __name__ == "__main__":
    main()
