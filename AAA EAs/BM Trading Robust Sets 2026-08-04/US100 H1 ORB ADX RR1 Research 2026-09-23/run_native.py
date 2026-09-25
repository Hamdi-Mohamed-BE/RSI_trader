"""Native MT5 Strategy Tester study: US100 H1 ORB 13UTC ADX/DMI filters + 5/15/30-min 1R ranges.

Run-specific runner (2026-09-23), adapted from
  Nasdaq 5M DI Filter Research 2026-09-23/run_native_compare.py
which in turn follows the retained runners
  News Pulse Event Parameters Research 2026-09-19/run_native.py
  Gold Overnight Value Area Pipeline 2026-09-19/native.py
  Gold Overnight Value Area EA/verify_and_publish.py
Account, server, symbol, dates, delay, model and every case come from run-config.json.
Archived evidence and the production EA/SET are never modified.

Safety: launches ONLY the isolated portable research terminal (_Backtests/MT5-DMC-20260811)
with /portable, the empty research profile, [Experts] Enabled=0 and AllowLiveTrading=0.
It never closes, restarts or configures the normal MT5 terminal, never places orders,
publishes website data or runs portfolio installers. Tests run strictly one at a time.
Standard library only.

Usage: python run_native.py            # all cases
       python run_native.py H1-RR6     # only cases whose name starts with this prefix
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
REPORT_DIR = "calyx-us100-orb-adx"


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


def compile_research() -> dict:
    src = ROOT / CONFIG["research_source"]
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


def read_set(base: Path) -> dict:
    cfg = {}
    for line in text(base).splitlines():
        line = line.strip()
        if not line or line.startswith(";") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        cfg[k.strip()] = v
    return cfg


def set_body(cfg: dict) -> str:
    return "\n".join(f"{k}={v}" for k, v in cfg.items()) + "\n"


def cases() -> list[dict]:
    base = read_set(PACKAGE / CONFIG["base_set"])
    base.update(CONFIG["tester_overrides"])
    out = [dict(name="H1-RR6-production", variant="H1-RR6", filter="none", production=True,
                period=CONFIG["variants"]["H1-RR6"]["period"], inputs=dict(base))]
    for vkey, v in CONFIG["variants"].items():
        for fkey, f in CONFIG["filters"].items():
            inputs = dict(base)
            inputs.update(v["overrides"])
            inputs.update(CONFIG["common_research_overrides"])
            inputs.update(f["overrides"])
            out.append(dict(name=f"{vkey}-{fkey}", variant=vkey, filter=fkey, production=False,
                            period=v["period"], inputs=inputs))
    return out


def run_case(c: dict) -> dict:
    start, end = c.get("start", CONFIG["start_date"]), c.get("end", CONFIG["end_date"])
    case = f"us100orb-{c['name']}-{c.get('window', '1y')}-m{CONFIG['model']}-d{CONFIG['execution_delay_ms']}"
    out = OUT / case
    out.mkdir(parents=True, exist_ok=True)
    set_name = f"us100orb-{c['name']}.set"
    body_text = set_body(c["inputs"])
    (out / set_name).write_text(body_text, encoding="utf-8")
    (TESTER / "MQL5" / "Profiles" / "Tester" / set_name).write_text(body_text, encoding="utf-8")
    expert_file = CONFIG["production_expert_file"] if c["production"] else CONFIG["research_expert_file"]
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
Period={c['period']}
Deposit={CONFIG['deposit']}
Currency={CONFIG['currency']}
Leverage={CONFIG['leverage']}
Model={CONFIG['model']}
ExecutionMode={CONFIG['execution_delay_ms']}
Optimization=0
FromDate={start}
ToDate={end}
ForwardMode=0
Report=reports\\{REPORT_DIR}\\{case}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
""", encoding="utf-8-sig")
    (TESTER / "reports" / REPORT_DIR).mkdir(parents=True, exist_ok=True)
    report = TESTER / "reports" / REPORT_DIR / f"{case}.htm"
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
        fail(f"No fresh report for {case} (exit code {proc.returncode}). Journal tail:\n{journal[-3000:]}")
    for f in report.parent.glob(case + "*"):
        if f.is_file() and f.stat().st_mtime >= began - 2:
            shutil.copy2(f, out / f.name)
    body = text(report)
    inputs = c["inputs"]
    checks = {
        "expert_in_report": Path(expert_file).stem in body,
        "symbol_in_report": CONFIG["symbol"] in body,
        "period_in_report": start in body and end in body,
        "range_minutes_match": f"InpOpeningRangeMinutes={inputs['InpOpeningRangeMinutes']}" in body,
        "reward_risk_match": re.search(rf"InpRewardRisk={float(inputs['InpRewardRisk']):g}(\.0+)?\b", body) is not None,
    }
    if not c["production"]:
        checks["adx_mode_match"] = f"InpAdxFilterMode={inputs['InpAdxFilterMode']}" in body
    flags = {k: len(re.findall(p, journal, re.I)) for k, p in {
        "init_failed": r"initialization failed|INIT_FAILED|init\S* failed",
        "no_history": r"no history|history not found|not enough history|waiting for history",
        "rejected": r"rejected|entry failed|invalid (stops|volume|price)",
        "market_closed": r"market closed",
        "critical": r"critical|access violation",
    }.items()}
    ticks = re.findall(r"real ticks begin from[^\r\n]*", journal)
    meta = dict(case=case, name=c["name"], variant=c["variant"], filter=c["filter"], production=c["production"],
                chart_period=c["period"], start=start, end_exclusive=end, command=cmd,
                exit_code=proc.returncode, elapsed_seconds=round(time.time() - began, 1),
                report=str(out / report.name), report_checks=checks, journal_flags=flags,
                real_tick_lines=sorted(set(ticks)), set_sha256=hashlib.sha256(body_text.encode()).hexdigest())
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
    build = compile_research()
    dest = TESTER / "MQL5" / "Experts" / CONFIG["expert_dir"]
    dest.mkdir(parents=True, exist_ok=True)
    prod_ex5 = PACKAGE / CONFIG["production_ex5"]
    research_ex5 = (ROOT / CONFIG["research_source"]).with_suffix(".ex5")
    shutil.copy2(prod_ex5, dest / CONFIG["production_expert_file"])
    shutil.copy2(research_ex5, dest / CONFIG["research_expert_file"])
    base_set = PACKAGE / CONFIG["base_set"]
    build.update(production_ex5=str(prod_ex5), production_ex5_sha256=sha(prod_ex5),
                 base_set=str(base_set), base_set_sha256=sha(base_set))
    (OUT / "build.json").write_text(json.dumps(build, indent=2), encoding="utf-8")
    only = sys.argv[1:]
    if only == ["validation"]:
        v = CONFIG["validation"]
        todo = [dict(c, start=v["start_date"], end=v["end_date"], window="val4y") for c in cases() if c["name"] in v["cases"]]
    else:
        todo = [c for c in cases() if not only or any(c["name"].startswith(p) for p in only)]
    status(event=f"{len(todo)} cases queued")
    results = []
    for c in todo:
        results.append(run_case(c))
        (OUT / ("runs-validation.json" if only == ["validation"] else "runs.json")).write_text(json.dumps(results, indent=2), encoding="utf-8")
    status(state="ALL DONE", event="ALL DONE")


if __name__ == "__main__":
    main()
