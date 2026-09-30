"""Nasdaq 5M index-transfer runner (2026-09-25). Stages: main | summary (production EX5 only, no compile).

Copied from Order Block 30m Raw 2026-09-25/run_ob30.py. Account, server, dates, model and
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
REPORT_DIR = TESTER / "reports" / "calyx-n5-index-transfer"


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


def compile_ea() -> dict:
    src = ROOT / CONFIG["source"]
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
    build = dict(source_sha256=sha(src), ex5_sha256=sha(ex5), compile_tail=body[-300:])
    (OUT / "build.json").write_text(json.dumps(build, indent=1), encoding="utf-8")
    status(event=f"COMPILE OK {build['ex5_sha256'][:12]}")
    return build


def install_experts() -> None:
    dest = TESTER / "MQL5" / "Experts" / CONFIG["expert_dir"]
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PACKAGE / CONFIG["production_ex5"], dest / CONFIG["production_expert_file"])


def base_set_values() -> dict:
    values = {}
    for line in text(PACKAGE / CONFIG["base_set"]).splitlines():
        line = line.strip()
        if line and not line.startswith(";") and "=" in line:
            k, v = line.split("=", 1)
            values[k.strip()] = v.strip()
    return values


def variant_inputs(variant: str) -> dict:
    spec = CONFIG["variants"].get(variant, {"inputs": {}})   # PARITY = base SET on the research EX5
    return {**base_set_values(), **spec["inputs"]}


def set_text(variant: str) -> str:
    return "\n".join(f"{k}={v}" for k, v in variant_inputs(variant).items()) + "\n"


def summarize(report: Path) -> dict:
    t = _read_report(report)
    m = _native_metrics(report)
    m["balance_dd_pct"] = round(_percent_in_parentheses(_metric(t, "Balance Drawdown Maximal")), 2)
    m["expected_payoff"] = round(_number(_metric(t, "Expected Payoff")), 2)
    return m


def port_3000_busy() -> bool:
    """MT5's first local tester agent uses 127.0.0.1:3000; another listener there causes 'tester agent authorization error'."""
    out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True).stdout
    return any(":3000 " in line and "LISTENING" in line for line in out.splitlines())


def wait_for_port_3000() -> None:
    waited = 0
    while port_3000_busy():
        if waited % 300 == 0:
            status(event=f"WAIT port 3000 is held by another program (waited {waited}s); not touching it")
        time.sleep(20)
        waited += 20
        if waited > 6 * 3600:
            fail("Port 3000 stayed busy for 6 hours.")


def run_case(symbol: str, variant: str, period: str) -> dict:
    production = CONFIG["variants"].get(variant, {}).get("production", False)
    expert_file = CONFIG["production_expert_file"] if production else CONFIG["expert_file"]
    tag = variant
    case = f"n5idx-{symbol}-{variant}-{period}"
    out = OUT / case
    done = out / "run.json"
    if done.exists():
        meta = json.loads(done.read_text(encoding="utf-8"))
        if meta.get("ok"):
            return meta
    start, end = CONFIG["periods"][period], CONFIG["end_date"]
    out.mkdir(parents=True, exist_ok=True)
    body = set_text(variant)
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
Report=reports\\calyx-n5-index-transfer\\{case}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
""", encoding="utf-8-sig")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = REPORT_DIR / f"{case}.htm"
    wait_for_port_3000()
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
    (out / "trades.json.gz").write_bytes(gzip.compress(json.dumps(trades).encode("utf-8"), 9, mtime=0))
    meta = dict(case=case, symbol=symbol, variant=tag, period=period, start=start,
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


def main_grid() -> None:
    for sym in CONFIG["symbols"]:
        for period in CONFIG["periods"]:
            for variant in CONFIG["variants"]:
                run_case(sym, variant, period)


def parity() -> None:
    a = run_case("USTEC", "CURRENT", CONFIG["parity"]["period"])
    b = run_case("USTEC", "PARITY", CONFIG["parity"]["period"])
    load = lambda m: json.loads(gzip.decompress((OUT / m["case"] / "trades.json.gz").read_bytes()).decode("utf-8"))
    key = lambda t: (t["open_time"], t["side"], t["close_time"], round(t["open_price"], 2), round(t["close_price"], 2))
    ta, tb = load(a), load(b)
    same = [key(t) for t in ta] == [key(t) for t in tb]
    res = dict(production_trades=len(ta), research_trades=len(tb), identical_entries_exits=same,
               production_net=a["metrics"]["net_profit"], research_net=b["metrics"]["net_profit"])
    (OUT / "PARITY.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    status(event=f"PARITY {len(ta)} vs {len(tb)} identical={same}")
    if not same:
        fail("Parity failed: research EX5 with new options off does not reproduce production.")


def summary() -> None:
    rows = []
    for f in sorted(OUT.glob("n5idx-*/run.json")):
        m = json.loads(f.read_text(encoding="utf-8"))
        if m.get("ok"):
            rows.append({k: m[k] for k in ("case", "symbol", "variant", "period", "start", "end_exclusive",
                                           "journal_flags", "real_tick_lines")} | m["metrics"])
    (ROOT / "RESULTS.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"{len(rows)} runs summarised")


if __name__ == "__main__":
    stages = sys.argv[1:] or ["main", "summary"]
    OUT.mkdir(parents=True, exist_ok=True)
    status(state="preflight", event="STAGES " + " ".join(stages))
    if isolated_running():
        fail("Isolated research terminal is already running.")
    if "compile" in stages:
        compile_ea()
    install_experts()
    for stage in stages:
        {"parity": parity, "main": main_grid, "summary": summary}.get(stage, lambda: None)()
    status(state="ALL DONE", event="ALL DONE " + " ".join(stages))
