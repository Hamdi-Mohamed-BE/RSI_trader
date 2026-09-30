"""Read-only-to-production qualification using the original native MT5 harness/parser.

python run_qualification.py parity|screen|confirm|controls|report
Only research evidence and the isolated portable tester are written.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import time

os.environ["EA_STORE_DISABLE_MT5"] = "1"
ROOT = Path(__file__).resolve().parent
RAW = ROOT.parent / "3 Way Volume Profile Raw 2026-09-26"
CFG = json.loads((ROOT / "run-config.json").read_text())
spec = importlib.util.spec_from_file_location("raw_harness", RAW / "run_3wvp.py")
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
BINDING = dict(h.CONFIG)
h.ROOT = ROOT
h.OUT = ROOT / "native"
h.STATUS = h.OUT / "status.json"
h.CONFIG = BINDING | {k: CFG[k] for k in ("source", "expert_dir", "expert_file")}
h.REPORT_DIR = h.TESTER / "reports" / "calyx-3wvp-qualification"
h.OUT.mkdir(exist_ok=True)


def dump(path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def dependencies():
    paths = [ROOT / "run-config.json", ROOT / "PLAN.md", ROOT / CFG["source"],
             RAW / "run-config.json", RAW / "run_3wvp.py"]
    paths += list((RAW / "EA").glob("*.mq*"))
    paths += list((ROOT.parent / "_Shared").glob("*.mqh"))
    return {str(p.relative_to(ROOT.parent)): h.sha(p) for p in paths}


def build():
    if h.isolated_running():
        raise RuntimeError("Isolated terminal already running; no compile/install permitted.")
    result = h.compile_ea()
    if not re.search(r"0 errors?, 0 warnings?", result["compile_tail"]):
        raise RuntimeError("Build is not warning-free: " + result["compile_tail"])
    result["dependencies"] = dependencies()
    dump(h.OUT / "build.json", result)
    h.install_experts()
    return result


def verified_build():
    info = json.loads((h.OUT / "build.json").read_text())
    if info["dependencies"] != dependencies():
        raise RuntimeError("Frozen source/config/dependency changed: preserve evidence and create a new experiment.")
    if info["ex5_sha256"] != h.sha((ROOT / CFG["source"]).with_suffix(".ex5")):
        raise RuntimeError("Compiled binary hash changed")
    return info


def inputs(c, control_seed=None):
    return BINDING["common_inputs"] | {
        "InpSetups": c["setups"], "InpNoSignalControl": "false" if control_seed is None else "true",
        "InpControlSeed": control_seed or 101, "InpControlProbability": c["control_probability"],
        "InpControlStopATR": 2.0,
    }


def run(c, period, model, control_seed=None):
    build_info = verified_build()
    params = inputs(c, control_seed)
    identity = dict(symbol=c["symbol"], variant=c["variant"], start=CFG["periods"][period],
                    end=CFG["end_date"], period=period, model=model, inputs=params,
                    source_sha256=build_info["ex5_sha256"])
    fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    control = "raw" if control_seed is None else f"control{control_seed}"
    case = f"qual-{c['symbol']}-{c['variant']}-{period}-m{model}-{control}"
    out = h.OUT / case
    out.mkdir(exist_ok=True)
    result_path = out / "run.json"
    if result_path.exists():
        old = json.loads(result_path.read_text())
        if old.get("fingerprint") != fingerprint:
            raise RuntimeError("Refusing to overwrite a different run: " + case)
        if old.get("ok"):
            return old
    h.wait_for_port_3000()
    if h.isolated_running():
        raise RuntimeError("Isolated terminal busy; no second instance")
    # The selected research chart profile must remain empty.
    profile = h.TESTER / "MQL5" / "Profiles" / "Charts" / BINDING["profile"]
    if not profile.is_dir() or list(profile.glob("*.chr")):
        raise RuntimeError("Expected empty research profile is missing or has charts")
    set_name = case + ".set"
    body = "".join(f"{k}={v}\n" for k, v in params.items())
    (out / set_name).write_text(body, encoding="utf-8")
    (h.TESTER / "MQL5" / "Profiles" / "Tester" / set_name).write_text(body, encoding="utf-8")
    ini = out / "tester.ini"
    expert = CFG["expert_dir"] + "\\" + Path(CFG["expert_file"]).stem
    sections = {
        "Common": {"Login": BINDING["login"], "Server": BINDING["server"]},
        "Experts": {"Enabled": 0, "AllowLiveTrading": 0, "AllowDllImport": 0},
        "Tester": {"Expert": expert, "ExpertParameters": set_name, "Symbol": c["symbol"],
                   "Period": "M15", "Deposit": 10000, "Currency": "USD", "Leverage": BINDING["leverage"],
                   "Model": model, "ExecutionMode": 150, "Optimization": 0,
                   "FromDate": identity["start"], "ToDate": identity["end"], "ForwardMode": 0,
                   "Report": "reports\\calyx-3wvp-qualification\\" + case + ".htm",
                   "ReplaceReport": 1, "ShutdownTerminal": 1, "UseLocal": 1, "UseRemote": 0,
                   "UseCloud": 0, "Visual": 0},
    }
    ini.write_text("\n".join("[" + s + "]\n" + "\n".join(f"{k}={v}" for k, v in values.items())
                             for s, values in sections.items()), encoding="utf-8-sig")
    h.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = h.REPORT_DIR / (case + ".htm")
    offsets = {p: p.stat().st_size for p in h.log_files()}
    began = time.time()
    h.status(state="running", case=case, event="START " + case)
    command = f'"{h.TESTER / "terminal64.exe"}" /portable /profile:"{BINDING["profile"]}" /config:"{ini}"'
    proc = subprocess.Popen(command, cwd=h.TESTER, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        proc.wait(timeout=BINDING["timeout_seconds"])
    except subprocess.TimeoutExpired:
        proc.terminate()  # only the process owned by this run
        proc.wait(timeout=30)
        raise RuntimeError("Owned isolated test timed out: " + case)
    journal = ""
    for f in h.log_files():
        if f.stat().st_mtime < began - 2:
            continue
        with f.open("rb") as stream:
            stream.seek(offsets.get(f, 0))
            journal += "\n[" + str(f.relative_to(h.TESTER)) + "]\n" + stream.read().decode("utf-16-le", errors="replace")
    (out / "journal.txt.gz").write_bytes(gzip.compress(journal.encode(), mtime=0))
    if not report.exists() or report.stat().st_mtime < began - 2:
        raise RuntimeError("No fresh report: " + case + "\n" + journal[-2000:])
    actual = h._report_inputs(report)
    mismatches = [k for k, v in params.items() if k not in actual or not h._same_setting(str(v), actual[k])]
    rb = h.text(report)
    checks = {"inputs_exact": not mismatches, "expert": Path(CFG["expert_file"]).stem in rb,
              "symbol": c["symbol"] in rb, "dates": identity["start"] in rb and identity["end"] in rb,
              "process_exit": proc.returncode == 0}
    flags = {k: re.findall(pattern, journal, re.I) for k, pattern in {
        "critical": r"[^\r\n]*(?:initialization failed|critical|access violation)[^\r\n]*",
        "history": r"[^\r\n]*(?:no history|history not found|not enough history|start time changed)[^\r\n]*",
        "orders": r"[^\r\n]*(?:failed.*(?:buy|sell)|invalid (?:stops|volume|price)|not enough money)[^\r\n]*",
        "coverage": r"[^\r\n]*(?:real ticks begin from|history data begins from|history synchronized from|ticks synchronized from)[^\r\n]*",
    }.items()}
    trades = h._native_trades(report, case)
    for f in h.REPORT_DIR.glob(case + "*"):
        if f.is_file() and f.stat().st_mtime >= began - 2:
            if f.suffix.lower() in (".htm", ".html"):
                (out / (f.name + ".gz")).write_bytes(gzip.compress(f.read_bytes(), mtime=0))
            else:
                shutil.copy2(f, out / f.name)
    (out / "trades.json.gz").write_bytes(gzip.compress(json.dumps(trades).encode(), mtime=0))
    result = identity | dict(case=case, control_seed=control_seed, fingerprint=fingerprint,
                            ok=all(checks.values()) and not flags["critical"], checks=checks,
                            mismatches=mismatches, journal=flags, metrics=h.summarize(report),
                            elapsed_seconds=round(time.time() - began, 1), report_sha256=h.sha(report))
    dump(result_path, result)
    if not result["ok"]:
        raise RuntimeError(f"Evidence verification failed: {case} {checks} {mismatches}")
    m = result["metrics"]
    h.status(event=f"DONE {case}: return {m['return_pct']}%, PF {m['profit_factor']}, trades {m['trades']}, equity DD {m['max_drawdown_pct']}%")
    return result


def qualifies(result):
    m = result["metrics"]
    return (result["ok"] and not result["journal"]["history"] and m["return_pct"] > 0
            and m["profit_factor"] >= CFG["raw_gate"]["minimum_pf"] and m["trades"] >= 30)


def rows():
    return [json.loads(p.read_text()) for p in sorted(h.OUT.glob("qual-*/run.json"))]


def report():
    data = rows()
    dump(ROOT / "RESULTS.json", data)
    lines = ["# 3 Way Volume Profile: qualification results", "",
             "Native MT5; M15, $10,000, target risk 1% (lots round up), 2R, 150 ms configured delay.", "",
             "Model 1 is an OHLC screen; Model 4 can mix real and generated ticks. See journals for coverage.", "",
             "| Asset / setup | Window | Model | Type | Return | PF | Trades | Win | Equity DD | Absolute gate |",
             "|---|---|---|---|---:|---:|---:|---:|---:|---|"]
    for r in data:
        m = r["metrics"]
        lines.append(f"| {r['symbol']} {r['variant']} | {r['period']} | {r['model']} | "
                     f"{r['control_seed'] or 'raw'} | {m['return_pct']:+.2f}% | {m['profit_factor']:.2f} | "
                     f"{m['trades']} | {m['win_rate_pct']:.2f}% | {m['max_drawdown_pct']:.2f}% | "
                     f"{'PASS' if qualifies(r) else 'FAIL'} |")
    lines += ["", "Absolute gate: return > 0, PF >= 1.15, >= 30 trades, no detected history-start shift. Both 3y AND 5y required; a control comparison is also required before qualification.",
              "", "Optimization has NOT started. No production files or settings changed."]
    (ROOT / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["parity", "screen", "confirm", "controls", "report"])
    a = parser.parse_args()
    lock = ROOT / ".qualification.lock"
    if a.stage == "report":
        report()
        return
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    try:
        if a.stage == "parity":
            if (h.OUT / "build.json").exists():
                verified_build()
            else:
                build()
            r = run(CFG["candidates"][1], "1y", 4)
            old = json.loads((RAW / "native" / "3wvp-XAUUSD-BRK-1y" / "run.json").read_text())
            prior_trades = json.loads(gzip.decompress((RAW / "native" / "3wvp-XAUUSD-BRK-1y" / "trades.json.gz").read_bytes()))
            current_trades = json.loads(gzip.decompress((h.OUT / r["case"] / "trades.json.gz").read_bytes()))
            # Parser IDs/labels describe the report, not trading behavior.
            ignored = {"id", "ea", "ea_id", "label", "strategy", "ea_name", "mode_id", "source"}
            clean = lambda trades: [{k: v for k, v in t.items() if k not in ignored} for t in trades]
            parity = dict(metrics_equal=old["metrics"] == r["metrics"],
                          trades_equal=clean(prior_trades) == clean(current_trades),
                          prior_count=len(prior_trades), current_count=len(current_trades))
            dump(ROOT / "parity.json", parity)
            if not all(parity[k] for k in ("metrics_equal", "trades_equal")):
                raise RuntimeError("Parity failed; investigate before long runs: " + str(parity))
        else:
            parity = json.loads((ROOT / "parity.json").read_text())
            if not parity["metrics_equal"] or not parity["trades_equal"]:
                raise RuntimeError("Parity not established")
            verified_build()
            h.install_experts()
            if a.stage in ("screen", "confirm"):
                for c in CFG["candidates"]:
                    for p in ("3y", "5y"):
                        run(c, p, 1 if a.stage == "screen" else 4)
                        report()
            else:
                for c in CFG["candidates"]:
                    baseline = [r for r in rows() if r["symbol"] == c["symbol"] and r["variant"] == c["variant"]
                                and r["model"] == 4 and r["control_seed"] is None and r["period"] in ("3y", "5y")]
                    if len(baseline) == 2 and all(qualifies(r) for r in baseline):
                        for p in ("3y", "5y"):
                            for seed in CFG["control_seeds"]:
                                run(c, p, 4, seed)
                                report()
        report()
        h.status(state="complete", event="STAGE COMPLETE " + a.stage)
    except BaseException as error:
        h.status(state="failed", event=str(error))
        raise
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
