"""DMC video-levels study runner (2026-09-25). Stages: compile | parity | main | ablation | summary.

Modelled on Nasdaq 5M DI Promotion 2026-09-25/run_native_parity.py. Account, server, dates, model and
delay come from run-config.json. Metrics use the EA Store's own report parser (app.mt5_evidence_jobs).

Safety: launches ONLY the isolated portable research terminal (_Backtests/MT5-DMC-20260811) with
/portable, the empty research profile, [Experts] Enabled=0 and AllowLiveTrading=0. Never touches the
normal MT5 terminal, places orders, publishes website data or runs installers. One test at a time;
finished cases are skipped so the run can resume. Journals and reports are stored gzip-compressed.
Run with EA_STORE_DISABLE_MT5=1.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

assert os.getenv("EA_STORE_DISABLE_MT5") == "1", "Set EA_STORE_DISABLE_MT5=1"
ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
sys.path.insert(0, str(PACKAGE.parent / "EA store"))
from app.mt5_evidence_jobs import _metric, _native_metrics, _native_trades, _number, _percent_in_parentheses, _read_report, _report_inputs, _same_setting  # noqa: E402

CONFIG = json.loads((ROOT / "run-config.json").read_text(encoding="utf-8"))
TESTER = PACKAGE / CONFIG["isolated_tester"]
OUT = ROOT / "native"
STATUS = OUT / "status.json"
REPORT_DIR = TESTER / "reports" / "calyx-dmc-video-levels"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def text(p: Path) -> str:
    raw = p.read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16")
    return raw.decode("utf-8-sig", errors="replace")


def status(**kw) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cur = json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else {"events": []}
    cur.update({k: v for k, v in kw.items() if k != "event"})
    if "event" in kw:
        cur["events"].append({"utc": now(), "event": kw["event"]})
        print(kw["event"], flush=True)
    cur["updated_utc"] = now()
    STATUS.write_text(json.dumps(cur, indent=1), encoding="utf-8")


def fail(msg: str) -> None:
    status(state="FAILED", error=msg, event="FAILED: " + msg)
    sys.exit(1)


def isolated_running() -> bool:
    cmd = "Get-CimInstance Win32_Process -Filter \"Name = 'terminal64.exe'\" | Select-Object -ExpandProperty ExecutablePath"
    out = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True).stdout
    return str(TESTER).lower() in out.lower()


def log_files() -> list[Path]:
    return (list((TESTER / "logs").glob("*.log")) + list((TESTER / "Tester" / "logs").glob("*.log"))
            + list((TESTER / "Tester").glob("Agent-*/logs/*.log")))


def compile_all() -> dict:
    build = {}
    for key, ea in CONFIG["eas"].items():
        src = ROOT / ea["source"]
        ex5, log = src.with_suffix(".ex5"), src.with_name(src.stem + ".compile.log")
        began = time.time()
        cmd = f'"{TESTER / "MetaEditor64.exe"}" /portable /compile:"{src}" /log:"{log}"'
        status(event="COMPILE " + src.name)
        subprocess.run(cmd, creationflags=subprocess.CREATE_NO_WINDOW, timeout=240)
        body = text(log) if log.exists() else ""
        if not re.search(r"\b0 errors?\b", body):
            fail("Compile errors:\n" + body[-4000:])
        if not ex5.exists() or ex5.stat().st_mtime < began - 2:
            fail(f"EX5 was not freshly written: {ex5}")
        build[key] = dict(source_sha256=sha(src), engine_sha256=sha(ROOT / "EA" / "AAA_Final_Strategy_Engine.mqh"),
                          ex5_sha256=sha(ex5), production_ex5_sha256=sha(PACKAGE / ea["production_ex5"]),
                          compile_tail=body[-300:])
        status(event=f"COMPILE OK {src.name} {build[key]['ex5_sha256'][:12]}")
    (OUT / "build.json").write_text(json.dumps(build, indent=1), encoding="utf-8")
    return build


def install_experts() -> None:
    dest = TESTER / "MQL5" / "Experts" / CONFIG["expert_dir"]
    dest.mkdir(parents=True, exist_ok=True)
    for ea in CONFIG["eas"].values():
        shutil.copy2(PACKAGE / ea["production_ex5"], dest / ea["production_expert_file"])
        shutil.copy2((ROOT / ea["source"]).with_suffix(".ex5"), dest / ea["research_expert_file"])


def set_text(cfg_key: str, symbol: str, variant: str) -> str:
    cfg = CONFIG["configs"][cfg_key]
    values: dict[str, str] = {}
    for line in text(PACKAGE / cfg["set"]).splitlines():
        line = line.strip()
        if line and not line.startswith(";") and "=" in line:
            k, v = line.split("=", 1)
            values[k.strip()] = v.strip()
    if symbol != cfg["native_symbol"] and values.get("InpDmCStopMode", "0") == "0":
        values.update(CONFIG["portable_overrides"])
    values.update(CONFIG["variants"][variant]["overrides"])
    return "\n".join(f"{k}={v}" for k, v in values.items()) + "\n"


def summarize(report: Path) -> dict:
    t = _read_report(report)
    m = _native_metrics(report)
    m["balance_dd_pct"] = round(_percent_in_parentheses(_metric(t, "Balance Drawdown Maximal")), 2)
    m["expected_payoff"] = round(_number(_metric(t, "Expected Payoff")), 2)
    return m


def run_case(cfg_key: str, symbol: str, variant: str, period: str, production: bool = False) -> dict:
    ea = CONFIG["eas"][CONFIG["configs"][cfg_key]["ea"]]
    expert_file = ea["production_expert_file"] if production else ea["research_expert_file"]
    tag = "PROD" if production else variant
    case = f"dmcv-{cfg_key}-{symbol}-{tag}-{period}"
    out = OUT / case
    done = out / "run.json"
    if done.exists():
        meta = json.loads(done.read_text(encoding="utf-8"))
        if meta.get("ok"):
            return meta
    start, end = CONFIG["periods"][period], CONFIG["end_date"]
    out.mkdir(parents=True, exist_ok=True)
    body = set_text(cfg_key, symbol, variant)
    set_name = f"{case}.set"
    (out / set_name).write_text(body, encoding="utf-8")
    (TESTER / "MQL5" / "Profiles" / "Tester" / set_name).write_text(body, encoding="utf-8")
    ini = out / "tester.ini"
    ini.write_text(f"""[Common]
Login={CONFIG['login']}
Server={CONFIG['server']}
[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert={CONFIG['expert_dir']}\\{Path(expert_file).stem}
ExpertParameters={set_name}
Symbol={symbol}
Period={CONFIG['period']}
Deposit={CONFIG['deposit']}
Currency={CONFIG['currency']}
Leverage={CONFIG['leverage']}
Model={CONFIG['model']}
ExecutionMode={CONFIG['execution_delay_ms']}
Optimization=0
FromDate={start}
ToDate={end}
ForwardMode=0
Report=reports\\calyx-dmc-video-levels\\{case}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
""", encoding="utf-8-sig")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = REPORT_DIR / f"{case}.htm"
    if isolated_running():
        fail("Isolated research terminal is already running; refusing to start a second tester.")
    offsets = {p: p.stat().st_size for p in log_files()}
    began = time.time()
    cmd = f'"{TESTER / "terminal64.exe"}" /portable /profile:"{CONFIG["profile"]}" /config:"{ini}"'
    status(state="running", case=case, event=f"START {case} {start}..{end}")
    proc = subprocess.Popen(cmd, cwd=TESTER, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        proc.wait(timeout=CONFIG["timeout_seconds"])
    except subprocess.TimeoutExpired:
        proc.terminate()  # only the isolated process this runner started
        proc.wait(timeout=30)
        fail(f"Timeout after {CONFIG['timeout_seconds']}s for {case}")
    journal = ""
    for f in log_files():
        if f.stat().st_mtime < began - 2:
            continue
        with f.open("rb") as h:
            h.seek(offsets.get(f, 0))
            journal += f"\n===== {f.relative_to(TESTER)} =====\n" + h.read().decode("utf-16-le", errors="replace")
    (out / "journal.txt.gz").write_bytes(gzip.compress(journal.encode("utf-8"), 9, mtime=0))
    if not report.exists() or report.stat().st_mtime < began - 2:
        fail(f"No fresh report for {case} (exit code {proc.returncode}). Journal tail:\n{journal[-3000:]}")
    rbody = text(report)
    expected = {k: v for k, v in (l.split("=", 1) for l in body.splitlines() if "=" in l)}
    actual = _report_inputs(report)
    mismatched = [k for k in expected if k in actual and not _same_setting(expected[k], actual[k])]
    checks = {
        "expert_in_report": Path(expert_file).stem in rbody,
        "symbol_in_report": symbol in rbody,
        "period_in_report": start in rbody and end in rbody,
        "inputs_applied": not mismatched and len(set(expected) & set(actual)) >= 0.8 * len(expected),
    }
    flags = {k: len(re.findall(p, journal, re.I)) for k, p in {
        "init_failed": r"initialization failed|INIT_FAILED|init\S* failed",
        "no_history": r"no history|history not found|not enough history|waiting for history",
        "rejected": r"rejected|failed.*(buy|sell)|invalid (stops|volume|price)",
        "size_below_min": r"size below broker minimum",
        "critical": r"critical|access violation",
    }.items()}
    trades = _native_trades(report, case)
    for f in REPORT_DIR.glob(case + "*"):
        if f.is_file() and f.stat().st_mtime >= began - 2:
            if f.suffix.lower() in (".htm", ".html"):
                (out / (f.name + ".gz")).write_bytes(gzip.compress(f.read_bytes(), 9, mtime=0))
            else:
                shutil.copy2(f, out / f.name)
    (out / "trades.json").write_text(json.dumps(trades, indent=0), encoding="utf-8")
    meta = dict(case=case, config=cfg_key, symbol=symbol, variant=tag, period=period, start=start,
                end_exclusive=end, expert=expert_file, exit_code=proc.returncode,
                elapsed_seconds=round(time.time() - began, 1), report_sha256=sha(report),
                report_checks=checks, input_mismatches=mismatched[:10], journal_flags=flags,
                real_tick_lines=sorted(set(re.findall(r"real ticks begin from[^\r\n]*", journal))),
                set_sha256=hashlib.sha256(body.encode()).hexdigest(), metrics=summarize(report))
    meta["ok"] = all(checks.values())
    done.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    if not meta["ok"]:
        fail(f"Report does not match requested run {case}: {checks} {mismatched[:5]}")
    m = meta["metrics"]
    status(event=f"DONE {case} {meta['elapsed_seconds']}s | {m['return_pct']}% PF {m['profit_factor']} "
                 f"n={m['trades']} DD {m['max_drawdown_pct']}% | flags {flags}")
    return meta


def trade_key(t: dict) -> tuple:
    return (str(t.get("open_time")), str(t.get("side") or t.get("type")), str(t.get("close_time")),
            round(float(t.get("open_price") or 0), 2), round(float(t.get("close_price") or 0), 2))


def parity() -> None:
    rows = []
    for cfg_key, cfg in CONFIG["configs"].items():
        sym = cfg["native_symbol"]
        prod = run_case(cfg_key, sym, "BASE", "1y", production=True)
        new = run_case(cfg_key, sym, "BASE", "1y")
        a = json.loads((OUT / prod["case"] / "trades.json").read_text(encoding="utf-8"))
        b = json.loads((OUT / new["case"] / "trades.json").read_text(encoding="utf-8"))
        same = [trade_key(x) for x in a] == [trade_key(x) for x in b]
        rows.append(dict(config=cfg_key, symbol=sym, production_trades=len(a), research_trades=len(b),
                         identical_entries_exits=same, production_net=prod["metrics"]["net_profit"],
                         research_net=new["metrics"]["net_profit"]))
        status(event=f"PARITY {cfg_key} {sym}: {len(a)} vs {len(b)} trades, identical={same}")
    (OUT / "PARITY.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    if not all(r["identical_entries_exits"] for r in rows):
        fail("Parity failed: research build with new inputs off does not reproduce production.")


def main_grid() -> None:
    for cfg_key, cfg in CONFIG["configs"].items():
        symbols = [cfg["native_symbol"]] + [s for s in CONFIG["symbols"] if s != cfg["native_symbol"]]
        for sym in symbols:
            for period in CONFIG["periods"]:
                for variant in ("BASE", "VIDEO"):
                    run_case(cfg_key, sym, variant, period)


def ablation() -> None:
    for cfg_key, cfg in CONFIG["configs"].items():
        symbols = [cfg["native_symbol"]] + [s for s in CONFIG["symbols"] if s != cfg["native_symbol"]]
        for sym in symbols:
            for variant in ("UNTESTED", "TARGET"):
                run_case(cfg_key, sym, variant, "5y")


def untested_grid() -> None:
    """Added after the 5y ablation: UNTESTED alone on the remaining periods (selection made on 5y results)."""
    for cfg_key, cfg in CONFIG["configs"].items():
        symbols = [cfg["native_symbol"]] + [s for s in CONFIG["symbols"] if s != cfg["native_symbol"]]
        for sym in symbols:
            for period in CONFIG["periods"]:
                run_case(cfg_key, sym, "UNTESTED", period)


def summary() -> None:
    rows = []
    for f in sorted(OUT.glob("dmcv-*/run.json")):
        m = json.loads(f.read_text(encoding="utf-8"))
        if m.get("ok"):
            rows.append({k: m[k] for k in ("case", "config", "symbol", "variant", "period", "start", "end_exclusive",
                                           "journal_flags", "real_tick_lines")} | m["metrics"])
    (ROOT / "RESULTS.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"{len(rows)} runs summarised")


if __name__ == "__main__":
    stages = sys.argv[1:] or ["compile", "parity", "main", "ablation", "summary"]
    OUT.mkdir(parents=True, exist_ok=True)
    status(state="preflight", event="STAGES " + " ".join(stages))
    if isolated_running():
        fail("Isolated research terminal is already running.")
    if "compile" in stages:
        compile_all()
    install_experts()
    for stage in stages:
        {"parity": parity, "main": main_grid, "ablation": ablation, "untested": untested_grid, "summary": summary}.get(stage, lambda: None)()
    status(state="ALL DONE", event="ALL DONE " + " ".join(stages))
