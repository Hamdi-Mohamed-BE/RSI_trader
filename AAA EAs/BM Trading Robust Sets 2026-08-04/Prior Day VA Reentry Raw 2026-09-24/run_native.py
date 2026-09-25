"""Native MT5 Strategy Tester raw test: previous-day value area re-entry ("80% rule") on XAUUSD.

Run-specific runner (2026-09-24), adapted from
  UK100 Trend Extreme Reversal Raw 2026-09-24/run_native.py (same safety design as the
  2026-09-23 US100 ORB ADX and Nasdaq 5M DI Filter runners).
Account, server, symbol, dates, delay, model and every case come from run-config.json.
Archived evidence and production EAs/SETs are never modified.

Safety: launches ONLY the isolated portable research terminal (_Backtests/MT5-DMC-20260811)
with /portable, the empty research profile, [Experts] Enabled=0 and AllowLiveTrading=0.
It never closes, restarts or configures the normal MT5 terminal, never places orders,
publishes website data or runs portfolio installers. Tests run strictly one at a time.
Standard library only.

Usage: python run_native.py            # all cases
       python run_native.py M30        # only cases whose name starts with this prefix
"""
from __future__ import annotations
import hashlib, json, re, shutil, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
CONFIG = json.loads((ROOT / "run-config.json").read_text(encoding="utf-8"))
TESTER = PACKAGE / CONFIG["isolated_tester"]
OUT = ROOT / "native"
STATUS = OUT / "status.json"
REPORT_DIR = "calyx-pdva"


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
    STATUS.write_text(json.dumps(cur, indent=2), encoding="utf-8")


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
    ex5 = src.with_suffix(".ex5")
    log = src.with_name(src.stem + ".compile.log")
    began = time.time()
    cmd = f'"{TESTER / "MetaEditor64.exe"}" /portable /compile:"{src}" /log:"{log}"'
    status(event="COMPILE " + cmd)
    subprocess.run(cmd, creationflags=subprocess.CREATE_NO_WINDOW, timeout=180)
    if not log.exists():
        fail(f"No compile log produced by: {cmd}")
    body = text(log)
    shutil.copy2(log, OUT / "compile.log")
    if not re.search(r"\b0 errors?, 0 warnings?\b", body):
        fail("Compile did not finish with 0 errors, 0 warnings:\n" + body[-4000:])
    if not ex5.exists() or ex5.stat().st_mtime < began - 2:
        fail(f"EX5 was not freshly written: {ex5}")
    result = dict(command=cmd, log_tail=body[-600:], source_sha256=sha(src), ex5_sha256=sha(ex5),
                  ex5_mtime_utc=datetime.fromtimestamp(ex5.stat().st_mtime, timezone.utc).isoformat())
    status(event="COMPILE OK " + result["ex5_sha256"][:12])
    return result


def cases() -> list[dict]:
    out = []
    for name, v in CONFIG["variants"].items():
        inputs = dict(CONFIG["inputs"], **v["inputs"], InpCase=f"pdva-{name}")
        out.append(dict(name=name, period=v["period"], inputs=inputs))
    return out


def run_case(c: dict) -> dict:
    start, end = CONFIG["start_date"], CONFIG["end_date"]
    case = f"pdva-{c['name']}-5y-m{CONFIG['model']}-d{CONFIG['execution_delay_ms']}"
    out = OUT / case
    out.mkdir(parents=True, exist_ok=True)
    set_name = f"pdva-{c['name']}.set"
    body_text = "\n".join(f"{k}={v}" for k, v in c["inputs"].items()) + "\n"
    (out / set_name).write_text(body_text, encoding="utf-8")
    (TESTER / "MQL5" / "Profiles" / "Tester" / set_name).write_text(body_text, encoding="utf-8")
    expert = CONFIG["expert_dir"] + "\\" + Path(CONFIG["expert_file"]).stem
    ini = out / "tester.ini"
    lines = [
        "[Common]", f"Login={CONFIG['login']}", f"Server={CONFIG['server']}",
        "[Experts]", "Enabled=0", "AllowLiveTrading=0", "AllowDllImport=0",
        "[Tester]", f"Expert={expert}", f"ExpertParameters={set_name}", f"Symbol={CONFIG['symbol']}",
        f"Period={c['period']}", f"Deposit={CONFIG['deposit']}", f"Currency={CONFIG['currency']}",
        f"Leverage={CONFIG['leverage']}", f"Model={CONFIG['model']}", f"ExecutionMode={CONFIG['execution_delay_ms']}",
        "Optimization=0", f"FromDate={start}", f"ToDate={end}", "ForwardMode=0",
        "Report=reports\\" + REPORT_DIR + "\\" + case + ".htm", "ReplaceReport=1", "ShutdownTerminal=1",
        "UseLocal=1", "UseRemote=0", "UseCloud=0", "Visual=0",
    ]
    ini.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    (TESTER / "reports" / REPORT_DIR).mkdir(parents=True, exist_ok=True)
    report = TESTER / "reports" / REPORT_DIR / f"{case}.htm"
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
    (out / "journal.txt").write_text(journal, encoding="utf-8")
    if not report.exists() or report.stat().st_mtime < began - 2:
        fail(f"No fresh report for {case} (exit code {proc.returncode}). Journal tail:\n{journal[-3000:]}")
    for f in report.parent.glob(case + "*"):
        if f.is_file() and f.stat().st_mtime >= began - 2:
            shutil.copy2(f, out / f.name)
    body = text(report)
    i = c["inputs"]
    checks = {
        "expert_in_report": Path(CONFIG["expert_file"]).stem in body,
        "symbol_in_report": CONFIG["symbol"] in body,
        "period_in_report": start in body and end in body,
        "inputs_match": all(f"{k}={i[k]}" in body for k in ("InpSignalTimeframe", "InpMaxDailyADX", "InpMinBodyFraction")),
    }
    flags = {k: len(re.findall(p, journal, re.I)) for k, p in {
        "init_failed": r"initialization failed|INIT_FAILED|init\S* failed",
        "no_history": r"no history|history not found|not enough history|waiting for history",
        "rejected": r"PDVA_REJECT|invalid (stops|volume|price)",
        "market_closed": r"market closed",
        "critical": r"critical|access violation",
    }.items()}
    meta = dict(case=case, name=c["name"],
                start=start, end_exclusive=end, command=cmd, exit_code=proc.returncode,
                elapsed_seconds=round(time.time() - began, 1), report=str(out / report.name), report_checks=checks,
                journal_flags=flags, real_tick_lines=sorted(set(re.findall(r"real ticks begin from[^\r\n]*", journal))),
                ea_summary=re.findall(r"PDVA_SUMMARY\|[^\r\n]*", journal)[-1:],
                ea_spec=re.findall(r"PDVA_SPEC\|[^\r\n]*", journal)[-1:],
                set_sha256=hashlib.sha256(body_text.encode()).hexdigest())
    (out / "run.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    if not all(checks.values()):
        fail(f"Report does not match requested run {case}: {checks}")
    status(event=f"DONE {case} in {meta['elapsed_seconds']}s flags={flags}")
    return meta


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    status(state="preflight", started_utc=now(), event="PREFLIGHT")
    for p in ("terminal64.exe", "MetaEditor64.exe"):
        if not (TESTER / p).exists():
            fail(f"Missing {TESTER / p}")
    if isolated_running():
        fail("Isolated research terminal is already running.")
    build = compile_ea()
    dest = TESTER / "MQL5" / "Experts" / CONFIG["expert_dir"]
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2((ROOT / CONFIG["source"]).with_suffix(".ex5"), dest / CONFIG["expert_file"])
    (OUT / "build.json").write_text(json.dumps(build, indent=2), encoding="utf-8")
    only = sys.argv[1:]
    todo = [c for c in cases() if not only or any(c["name"].startswith(p) for p in only)]
    status(event=f"{len(todo)} cases queued")
    results = []
    for c in todo:
        results.append(run_case(c))
        (OUT / "runs.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    status(state="ALL DONE", event="ALL DONE")


if __name__ == "__main__":
    main()
