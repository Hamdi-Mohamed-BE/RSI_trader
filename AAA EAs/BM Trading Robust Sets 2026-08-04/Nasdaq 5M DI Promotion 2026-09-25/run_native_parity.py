"""Promotion parity for the production Nasdaq 5M DI build (copied from Nasdaq 5M DI Filter Research 2026-09-23/run_native_compare.py; the EX5 is NOT recompiled).

Run-specific runner (2026-09-23). Modelled on the retained runners
  News Pulse Event Parameters Research 2026-09-19/run_native.py
  Gold Overnight Value Area Pipeline 2026-09-19/native.py
  Gold Overnight Value Area EA/verify_and_publish.py
Account, server, symbol, dates, delay and model come from run-config.json, not from
hard-coded historical values. Archived evidence is never modified.

Safety: launches ONLY the isolated portable research terminal (_Backtests/MT5-DMC-20260811)
with /portable, the empty research profile, [Experts] Enabled=0 and AllowLiveTrading=0.
It never closes, restarts or configures the normal MT5 terminal, never places orders,
publishes website data or runs portfolio installers. Tests run strictly one at a time.
Standard library only.
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


def compile_new() -> dict:
    src = ROOT / CONFIG["new_source"]
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
    if "0 errors, 0 warnings" not in body and not re.search(r"\b0 errors?\b", body):
        fail("Compile errors:\n" + body[-4000:])
    if not ex5.exists() or ex5.stat().st_mtime < began - 2:
        fail(f"EX5 was not freshly written: {ex5}")
    result = dict(command=cmd, log_tail=body[-600:], source_sha256=sha(src), ex5_sha256=sha(ex5),
                  ex5_mtime_utc=datetime.fromtimestamp(ex5.stat().st_mtime, timezone.utc).isoformat())
    status(event="COMPILE OK " + result["ex5_sha256"][:12])
    return result


def set_text(base: Path, overrides: dict) -> str:
    cfg = {}
    for line in text(base).splitlines():
        line = line.strip()
        if not line or line.startswith(";") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        cfg[k.strip()] = v
    cfg.update({k: str(v) for k, v in overrides.items()})
    return "\n".join(f"{k}={v}" for k, v in cfg.items()) + "\n"


def run_case(version: str, period: str, expert_file: str, set_name: str, set_body: str) -> dict:
    start, end = CONFIG["periods"][period], CONFIG["end_date"]
    case = f"n5p-{version}-{period}-m{CONFIG['model']}-d{CONFIG['execution_delay_ms']}"
    out = OUT / case
    out.mkdir(parents=True, exist_ok=True)
    (out / set_name).write_text(set_body, encoding="utf-8")
    (TESTER / "MQL5" / "Profiles" / "Tester" / set_name).write_text(set_body, encoding="utf-8")
    expert = CONFIG["expert_dir"] + "\\" + Path(expert_file).stem
    ini = out / "tester.ini"
    ini.write_text(f"""[Common]
Login={CONFIG['login']}
Server={CONFIG['server']}
[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert={expert}
ExpertParameters={set_name}
Symbol={CONFIG['symbol']}
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
Report=reports\\calyx-n5-di-promotion\\{case}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
""", encoding="utf-8-sig")
    (TESTER / "reports" / "calyx-n5-di-promotion").mkdir(parents=True, exist_ok=True)
    report = TESTER / "reports" / "calyx-n5-di-promotion" / f"{case}.htm"
    if isolated_running():
        fail("Isolated research terminal is already running; refusing to start a second tester.")
    offsets = {p: p.stat().st_size for p in log_files()}
    began = time.time()
    cmd = f'"{TESTER / "terminal64.exe"}" /portable /profile:"{CONFIG["profile"]}" /config:"{ini}"'
    status(state="running", case=case, event=f"START {case} {start}..{end} :: {cmd}")
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
        tail = journal[-3000:]
        fail(f"No fresh report for {case} (exit code {proc.returncode}). Journal tail:\n{tail}")
    for f in report.parent.glob(case + "*"):
        if f.is_file() and f.stat().st_mtime >= began - 2:
            shutil.copy2(f, out / f.name)
    body = text(report)
    checks = {
        "expert_in_report": Path(expert_file).stem in body,
        "symbol_in_report": CONFIG["symbol"] in body,
        "period_in_report": start in body and end in body,
        "di_flag_matches": ("InpRequireDIAgreement=true" in body) == (version == "di"),
    }
    flags = {k: len(re.findall(p, journal, re.I)) for k, p in {
        "init_failed": r"initialization failed|INIT_FAILED|init\S* failed",
        "no_history": r"no history|history not found|not enough history|waiting for history",
        "rejected": r"rejected|failed.*(buy|sell)|invalid (stops|volume|price)",
        "critical": r"critical|access violation",
    }.items()}
    ticks = re.findall(r"real ticks begin from[^\r\n]*", journal)
    meta = dict(case=case, version=version, period=period, start=start, end_exclusive=end, command=cmd,
                exit_code=proc.returncode, elapsed_seconds=round(time.time() - began, 1), report=str(out / report.name),
                report_checks=checks, journal_flags=flags, real_tick_lines=sorted(set(ticks)),
                set_sha256=hashlib.sha256(set_body.encode()).hexdigest())
    (out / "run.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    if not all(checks.values()):
        fail(f"Report does not match requested run {case}: {checks}")
    status(event=f"DONE {case} in {meta['elapsed_seconds']}s flags={flags}")
    return meta


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    status(state="preflight", started_utc=now(), event="PREFLIGHT")
    if isolated_running():
        fail("Isolated research terminal is already running.")
    dest = TESTER / "MQL5" / "Experts" / CONFIG["expert_dir"]
    dest.mkdir(parents=True, exist_ok=True)
    cur_ex5, new_ex5 = PACKAGE / CONFIG["current_ex5"], PACKAGE / CONFIG["new_ex5"]
    shutil.copy2(cur_ex5, dest / CONFIG["current_expert_file"])
    shutil.copy2(new_ex5, dest / CONFIG["new_expert_file"])
    base_set, di_set = PACKAGE / CONFIG["current_set"], PACKAGE / CONFIG["di_set"]
    ov = CONFIG["tester_overrides"]
    build = dict(current_ex5_sha256=sha(cur_ex5), new_ex5_sha256=sha(new_ex5),
                 base_set_sha256=sha(base_set), di_set_sha256=sha(di_set))
    (OUT / "build.json").write_text(json.dumps(build, indent=2), encoding="utf-8")
    results = [
        run_case("current", "1y", CONFIG["current_expert_file"], "n5p-current.set", set_text(base_set, ov)),
        run_case("newoff", "1y", CONFIG["new_expert_file"], "n5p-newoff.set", set_text(base_set, ov)),
        run_case("di", "1y", CONFIG["new_expert_file"], "n5p-di.set", set_text(di_set, ov)),
    ]
    (OUT / "runs.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    status(state="ALL DONE", event="ALL DONE")


if __name__ == "__main__":
    main()
