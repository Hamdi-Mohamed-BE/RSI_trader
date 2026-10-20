"""Isolated research tester infrastructure. Importing this module performs no I/O.

No MetaTrader5 Python API is imported. Only this repository's fixed portable
tester may be launched, under an exclusive lease, after explicit invocation.
Account-bound INI headers are read privately at runtime and never serialized
into public receipts. This module does not install or change production EAs.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
TESTER = BASE / "_Backtests" / "MT5-DMC-20260811"
EDITOR = TESTER / "MetaEditor64.exe"
TERMINAL = TESTER / "terminal64.exe"
EMPTY_PROFILE = TESTER / "MQL5/Profiles/Charts/Calyx Research Empty"
LOCK = BASE / "LTA VWAP Developing POC Comparison 2026-10-05/tester.lock"
PRIVATE_TEMPLATE = BASE / "FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini"
EXPERT_FOLDER = "AAA Research\\BTCWeekendPipeline20261017"
COMMON_FOLDER = "BTCWeekendPipeline20261017"
PORT = 3010
RATE_DTYPE = np.dtype([( "time", "<i8"), ("open", "<f8"), ("high", "<f8"),
                       ("low", "<f8"), ("close", "<f8"), ("tick_volume", "<i8"), ("spread", "<i4")])
PREFIX_DTYPE = np.dtype(RATE_DTYPE.descr + [("complete", "<i4")])
TF_SECONDS = {"M1": 60, "M5": 300, "H1": 3600, "D1": 86400}


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def text(path):
    data = Path(path).read_bytes()
    return data.decode("utf-16") if data[:2] in (b"\xff\xfe", b"\xfe\xff") else data.decode("utf-8-sig", errors="replace")


def clean(value):
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [clean(v) for v in value]
    return value


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(value), indent=2, allow_nan=False, default=str) + "\n", encoding="utf-8")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def epoch(value):
    return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp())


def date_input(value):
    return datetime.fromisoformat(value).strftime("%Y.%m.%d %H:%M:%S")


def valid_tag(tag):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", tag) or ".." in tag:
        raise ValueError("Use a unique simple research tag, without path components")
    return tag


def _startup():
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    return {"creationflags": subprocess.CREATE_NO_WINDOW, "startupinfo": startup}


@contextmanager
def tester_lease():
    import msvcrt
    with LOCK.open("a+b") as handle:
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            yield handle
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def ensure_free():
    """Read-only checks; never stop an existing process or clear another lock."""
    if TESTER.resolve() != (BASE / "_Backtests/MT5-DMC-20260811").resolve():
        raise RuntimeError("Unexpected tester path")
    for path in (EDITOR, TERMINAL):
        if not path.is_file():
            raise RuntimeError("Missing isolated tester executable: " + str(path))
    if not EMPTY_PROFILE.is_dir() or list(EMPTY_PROFILE.glob("*.chr")):
        raise RuntimeError("The isolated research profile must contain zero charts")
    script = "Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('terminal64.exe','terminal.exe','metaeditor64.exe')} | Select-Object ExecutablePath,ProcessId | ConvertTo-Json -Compress"
    result = subprocess.run(["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script], capture_output=True, text=True, check=True, timeout=30, **_startup())
    records = json.loads(result.stdout) if result.stdout.strip() else []
    if isinstance(records, dict):
        records = [records]
    root = str(TESTER.resolve()).lower() + os.sep
    if any(str(row.get("ExecutablePath") or "").lower().startswith(root) for row in records):
        raise RuntimeError("Isolated terminal/editor is occupied; no process was stopped")
    ports = subprocess.run(["netstat.exe", "-ano", "-p", "TCP"], capture_output=True, text=True, check=True, timeout=30, **_startup()).stdout
    if any(re.search(r":(?:3000|3010)\s", line) and "LISTENING" in line.upper() for line in ports.splitlines()):
        raise RuntimeError("Research tester port3000/3010 is occupied; no process was stopped")
    return {"isolated_terminal_running": False, "research_ports_clear": True, "empty_profile_charts": 0}


def _private_header():
    """Only runtime-generated tester.ini receives these private values."""
    body = text(PRIVATE_TEMPLATE).split("[Experts]", 1)[0]
    login = re.search(r"(?im)^Login\s*=\s*([1-9]\d*)\s*$", body)
    server = re.search(r"(?im)^Server\s*=\s*([^\r\n]+)", body)
    if not login or not server or server.group(1).strip().lower() != "exness-mt5trial16":
        raise RuntimeError("Missing authorized isolated Trial16 private configuration")
    return "[Common]\nLogin=" + login.group(1) + "\nServer=Exness-MT5Trial16\n"


def _logs():
    return list((TESTER / "logs").glob("*.log")) + list((TESTER / "Tester/logs").glob("*.log")) + list((TESTER / "Tester").glob("Agent-*/logs/*.log"))


def _report_helpers():
    os.environ["EA_STORE_DISABLE_MT5"] = "1"
    path = BASE / "FTMO Exit Management Research 2026-09-27/run.py"
    spec = importlib.util.spec_from_file_location("btc_weekend_report_parsers", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _compile_locked(name):
    if name not in ("Export", "BtcWeekend"):
        raise ValueError("Only the two tester-only study EAs may be compiled")
    ensure_free()
    source = ROOT / "EA" / (name + ".mq5")
    if not source.is_file():
        raise FileNotFoundError(source)
    binary = source.with_suffix(".ex5")
    builds = read(ROOT / "BUILD.json") if (ROOT / "BUILD.json").exists() else {}
    old = builds.get(name)
    if old and old["source_sha256"] == sha(source) and binary.exists() and old["binary_sha256"] == sha(binary):
        return old
    log = ROOT / "native" / "build" / (name + ".compile.log")
    log.parent.mkdir(parents=True, exist_ok=True)
    began = time.time()
    compiler = subprocess.run(f'"{EDITOR}" /portable /compile:"{source}" /log:"{log}"', cwd=TESTER, timeout=180, check=False, **_startup())
    body = text(log) if log.exists() else ""
    if compiler.returncode not in (0, 1) or not re.search(r"0 errors, 0 warnings", body, re.I) or not binary.exists() or binary.stat().st_mtime < began - 2:
        raise RuntimeError("Research compiler did not produce a fresh zero-warning binary; inspect private compile log")
    result = {"source_sha256": sha(source), "binary_sha256": sha(binary), "compiler": str(EDITOR), "compiled_utc": datetime.now(timezone.utc).isoformat(), "status": "0 errors, 0 warnings"}
    builds[name] = result
    save(ROOT / "BUILD.json", builds)
    return result


def compile_ea(name):
    with tester_lease():
        return _compile_locked(name)


def _input_equal(wanted, actual):
    a, b = str(wanted).strip(), str(actual).strip()
    if a.lower() == b.lower():
        return True
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M", "%Y.%m.%d"):
        try:
            d = datetime.strptime(a, fmt)
        except ValueError:
            continue
        # This terminal build serializes datetime inputs as Unix seconds in
        # native HTM; compare the exact UTC integer, not a loose string match.
        if re.fullmatch(r"\d+", b) and int(d.replace(tzinfo=timezone.utc).timestamp()) == int(b):
            return True
        for other in ("%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M", "%Y.%m.%d"):
            try:
                if d == datetime.strptime(b, other):
                    return True
            except ValueError:
                pass
    try:
        return math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-10)
    except ValueError:
        return {"true": "1", "false": "0"}.get(a.lower(), a) == {"true": "1", "false": "0"}.get(b.lower(), b)


def archive_case_build(tag, require_both=False):
    """Archive exact hash-matching provenance, never substitute a newer build.

    This can backfill an already completed case without any terminal/API call.
    An unavailable old source is explicitly missing even if semantics match.
    """
    out = ROOT / "native" / valid_tag(tag)
    manifest = read(out / "manifest.json")
    name = manifest["ea"]
    if name not in ("Export", "BtcWeekend"):
        raise RuntimeError("Unexpected case EA")
    receipt = {"tag": tag, "source": None, "binary": None, "missing": []}
    locations = {
        "source": ("source_sha256", "Source.mq5", [ROOT / "EA" / (name + ".mq5")]),
        "binary": ("binary_sha256", "Tester.ex5", [ROOT / "EA" / (name + ".ex5"), TESTER / "MQL5/Experts" / Path(EXPERT_FOLDER.replace("\\", "/")) / (name + ".ex5")]),
    }
    for kind, (hash_key, filename, candidates) in locations.items():
        target = out / filename
        expected = manifest["build"][hash_key]
        if target.exists():
            if sha(target) != expected:
                raise RuntimeError("An existing immutable build archive has the wrong hash")
        else:
            source = next((p for p in candidates if p.is_file() and sha(p) == expected), None)
            if source is not None:
                shutil.copy2(source, target)
        if target.exists() and sha(target) == expected:
            receipt[kind] = {"path": str(target.relative_to(ROOT)), "sha256": expected, "bytes": target.stat().st_size}
        else:
            receipt["missing"].append(kind)
    receipt["status"] = "COMPLETE_EXACT_BUILD_ARCHIVE" if not receipt["missing"] else "PARTIAL_ARCHIVE_OLD_BUILD_UNAVAILABLE"
    receipt["no_substitution"] = True
    receipt["no_terminal_launch_or_account_api"] = True
    if require_both and receipt["missing"]:
        raise RuntimeError("Current native build could not be archived exactly before launch")
    save(out / "build-archive.json", receipt)
    return receipt


def _execute_locked(name, tag, start, end, inputs, model, delay_ms=150, timeout=3600):
    valid_tag(tag)
    if model not in (1, 4) or delay_ms < 0:
        raise ValueError("Only Model1/Model4 and nonnegative execution delay are supported")
    if epoch(end) <= epoch(start):
        raise ValueError("Empty requested native interval")
    build = _compile_locked(name)
    ensure_free()
    out = ROOT / "native" / tag
    out.mkdir(parents=True, exist_ok=True)
    if (out / "manifest.json").exists():
        raise RuntimeError("Use a new tag; native manifests are never overwritten or silently reused")
    manifest = {"tag": tag, "ea": name, "symbol": "BTCUSD", "server": "Exness-MT5Trial16", "start": start, "end_exclusive": end,
                "model": model, "execution_delay_ms": delay_ms, "deposit_usd": 10000, "leverage": 15, "inputs": inputs,
                "build": build, "tester": str(TESTER), "agent_port": PORT, "empty_profile": str(EMPTY_PROFILE), "no_live_account_api": True}
    save(out / "manifest.json", manifest)
    archive_case_build(tag, require_both=True)
    dest = TESTER / "MQL5/Experts" / Path(EXPERT_FOLDER.replace("\\", "/"))
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "EA" / (name + ".ex5"), dest / (name + ".ex5"))
    setname = "btc-weekend-" + tag + ".set"
    settings = "\n".join(str(k) + "=" + str(v) for k, v in inputs.items()) + "\n"
    (out / "Parameters.set").write_text(settings, encoding="utf-8")
    (TESTER / "MQL5/Profiles/Tester" / setname).write_text(settings, encoding="utf-8")
    report_relative = "reports\\btc-weekend-pipeline-20261017\\" + tag + ".htm"
    report = TESTER / Path(report_relative.replace("\\", "/"))
    report.parent.mkdir(parents=True, exist_ok=True)
    ini = out / "tester.ini"
    ini.write_text(_private_header() + f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Port={PORT}
Expert={EXPERT_FOLDER}\\{name}
ExpertParameters={setname}
Symbol=BTCUSD
Period=M1
Deposit=10000
Currency=USD
Leverage=1:15
Model={model}
ExecutionMode={delay_ms}
Optimization=0
FromDate={start.replace('-', '.')}
ToDate={end.replace('-', '.')}
ForwardMode=0
Report={report_relative}
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''', encoding="utf-8-sig")
    offsets = {path: path.stat().st_size for path in _logs()}
    began = time.time()
    process = subprocess.Popen(f'"{TERMINAL}" /portable /profile:"Calyx Research Empty" /config:"{ini}"', cwd=TESTER, **_startup())
    save(out / "owned-process.json", {"pid": process.pid, "executable": str(TERMINAL), "started_epoch": began})
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.terminate()
        process.wait(timeout=30)
        raise RuntimeError("Only this owned isolated research child was terminated after timeout")
    journal = ""
    for path in _logs():
        if path.stat().st_mtime < began - 2:
            continue
        with path.open("rb") as stream:
            stream.seek(offsets.get(path, 0))
            journal += stream.read().decode("utf-16-le", errors="replace") + "\n"
    (out / "journal.txt.gz").write_bytes(gzip.compress(journal.encode(), compresslevel=3, mtime=0))
    if process.returncode != 0 or not report.exists() or report.stat().st_mtime < began - 2:
        raise RuntimeError("Missing fresh native report or owned tester failed")
    fatal = r"initialization failed|not enough history|access violation|array out of range|zero divide|margin call|stop out"
    if name != "Export":
        fatal += r"|start time changed"
    if re.search(fatal, journal, re.I):
        raise RuntimeError("Native history/runtime/margin failure; inspect private journal")
    helpers = _report_helpers()
    actual = helpers._report_inputs(report)
    mismatches = [key for key, value in inputs.items() if key not in actual or not _input_equal(value, actual[key])]
    if mismatches:
        raise RuntimeError("Native input mismatch: " + ", ".join(mismatches))
    report_text = helpers._read_report(report)
    if start.replace("-", ".") not in report_text or end.replace("-", ".") not in report_text:
        raise RuntimeError("Wrong native report date range")
    (out / "report.htm.gz").write_bytes(gzip.compress(report.read_bytes(), compresslevel=3, mtime=0))
    result = {"manifest": manifest, "seconds": time.time() - began, "report_sha256": sha(report),
              "tick_notes": sorted(set(line.strip() for line in journal.splitlines() if re.search(r"real ticks begin|real ticks absent|ticks discarded|generated ticks", line, re.I))),
              "tester_start_shift_notes": sorted(set(line.strip() for line in journal.splitlines() if re.search(r"start time changed", line, re.I))),
              "native_warnings": {key: len(re.findall(pattern, journal, re.I)) for key, pattern in {"invalid_stops": "invalid stops", "invalid_volume": "invalid volume", "market_closed": "market closed", "not_enough_money": "not enough money"}.items()}}
    return out, began, journal, result


def _common(tag):
    return Path(os.environ["APPDATA"]) / "MetaQuotes/Terminal/Common/Files" / COMMON_FOLDER / valid_tag(tag)


def _recover_export_receipt(tag, inputs, start, end):
    """Collect only a completed owned NO-ORDER export; never salvage a trading run."""
    ensure_free()
    out = ROOT / "native" / valid_tag(tag)
    manifest = read(out / "manifest.json")
    owner = read(out / "owned-process.json")
    began = float(owner["started_epoch"])
    if manifest["ea"] != "Export" or manifest["tag"] != tag or manifest["symbol"] != "BTCUSD" or manifest["server"] != "Exness-MT5Trial16":
        raise RuntimeError("Not an owned source-only BTC export")
    if owner["executable"] != str(TERMINAL) or manifest["tester"] != str(TESTER) or manifest["inputs"] != inputs or manifest["start"] != start or manifest["end_exclusive"] != end:
        raise RuntimeError("Export ownership/input provenance mismatch")
    if manifest["build"]["source_sha256"] != sha(ROOT / "EA/Export.mq5") or manifest["build"]["binary_sha256"] != sha(ROOT / "EA/Export.ex5"):
        raise RuntimeError("Export source/binary changed after owned launch")
    journal_path = out / "journal.txt.gz"
    report = TESTER / "reports/btc-weekend-pipeline-20261017" / (tag + ".htm")
    if not journal_path.exists() or not report.exists() or report.stat().st_mtime < began - 2:
        raise RuntimeError("No fresh owned report/journal to recover")
    journal = gzip.decompress(journal_path.read_bytes()).decode("utf-8")
    if "BW_EXPORT_COMPLETE" not in journal or "BW_EXPORT_INCOMPLETE" in journal or re.search(r"initialization failed|access violation|array out of range|zero divide", journal, re.I):
        raise RuntimeError("Export never completed successfully")
    helpers = _report_helpers()
    actual = helpers._report_inputs(report)
    if any(key not in actual or not _input_equal(value, actual[key]) for key, value in inputs.items()):
        raise RuntimeError("Recovered export has wrong report inputs")
    body = helpers._read_report(report)
    if start.replace("-", ".") not in body or end.replace("-", ".") not in body:
        raise RuntimeError("Recovered export has wrong requested report dates")
    (out / "report.htm.gz").write_bytes(gzip.compress(report.read_bytes(), compresslevel=3, mtime=0))
    native = {"manifest": manifest, "report_sha256": sha(report), "owned_started_epoch": began,
              "recovered_completed_export_without_relaunch": True,
              "tester_start_shift_notes": sorted(set(line.strip() for line in journal.splitlines() if re.search(r"start time changed", line, re.I))),
              "tick_notes": sorted(set(line.strip() for line in journal.splitlines() if re.search(r"real ticks begin|real ticks absent|ticks discarded|generated ticks", line, re.I))),
              "scope": "Source capture only: CopyRates requested endpoints are independently verified below. A shifted tester simulation is NOT a valid trading backtest; BtcWeekend rejects such shifts."}
    return out, began, journal, native


def export_data(tag="data-2018-20261017", start=None, end=None, _recover=False):
    plan = read(ROOT / "PLAN.json")
    start = start or plan["data"]["requested_start"]
    end = end or plan["data"]["end_exclusive"]
    inputs = {"InpExportFrom": date_input(start), "InpExportTo": date_input(end), "InpTag": valid_tag(tag)}
    with tester_lease():
        out, began, journal, native = _recover_export_receipt(tag, inputs, start, end) if _recover else _execute_locked("Export", tag, start, end, inputs, model=1)
        if "BW_EXPORT_COMPLETE" not in journal or "BW_EXPORT_INCOMPLETE" in journal:
            raise RuntimeError("Exporter did not complete all four timeframes")
        common = _common(tag)
        for filename in ("export-status.csv", "specification.csv"):
            path = common / filename
            if not path.exists() or path.stat().st_mtime < began - 2:
                raise RuntimeError("Missing fresh exporter receipt: " + filename)
            shutil.copy2(path, out / filename)
        statuses = list(csv.DictReader((out / "export-status.csv").open(encoding="utf-8-sig")))
        if {x["timeframe"] for x in statuses} != set(TF_SECONDS):
            raise RuntimeError("Missing exporter timeframe")
        specification = next(csv.DictReader((out / "specification.csv").open(encoding="utf-8-sig")))
        if specification["symbol"] != "BTCUSD" or float(specification["point"]) <= 0 or float(specification["contract_size"]) <= 0:
            raise RuntimeError("Wrong or invalid native BTC specification")
        data_dir = ROOT / "data"
        data_dir.mkdir(exist_ok=True)
        coverage = []
        complete = True
        for label, step in TF_SECONDS.items():
            source = common / ("BTCUSD-" + label + ".bin")
            if not source.exists() or source.stat().st_mtime < began - 2 or source.stat().st_size % RATE_DTYPE.itemsize:
                raise RuntimeError("Missing, stale, or malformed packed rate export: " + label)
            array = np.fromfile(source, dtype=RATE_DTYPE)
            status = next(x for x in statuses if x["timeframe"] == label)
            if not len(array) or len(array) != int(status["rows"]) or not np.all(np.diff(array["time"]) > 0):
                raise RuntimeError("Bad export count/order: " + label)
            if not np.all(np.isfinite(array["open"])) or not np.all(array["open"] > 0):
                raise RuntimeError("Invalid native prices: " + label)
            if np.any(array["time"] < epoch(start)) or np.any(array["time"] >= epoch(end)):
                raise RuntimeError("Exporter leaked outside its explicit interval")
            path = data_dir / ("BTCUSD-" + label + ".npz")
            np.savez_compressed(path, rates=array)
            first, last = int(array["time"][0]), int(array["time"][-1])
            start_ok, end_ok = first <= epoch(start) + step, last >= epoch(end) - step
            complete = complete and start_ok and end_ok and int(status["failed_chunks"]) == 0
            record = {"symbol": "BTCUSD", "timeframe": label, "timeframe_seconds": step, "rows": len(array),
                      "first_epoch": first, "last_epoch": last, "first_utc": datetime.fromtimestamp(first, timezone.utc).isoformat(),
                      "last_bar_open_utc": datetime.fromtimestamp(last, timezone.utc).isoformat(), "start_covered": start_ok, "end_covered": end_ok,
                      "gaps": int(np.sum(np.diff(array["time"]) > step)), "maximum_gap_seconds": int(np.max(np.diff(array["time"]))) if len(array) > 1 else None,
                      "nonpositive_spread_bars": int(np.sum(array["spread"] <= 0)), "spread_points_median": float(np.median(array["spread"])),
                      "packed_record_bytes": RATE_DTYPE.itemsize, "source_binary_sha256": sha(source), "path": str(path.relative_to(ROOT)), "sha256": sha(path)}
            coverage.append(record)
            with source.open("rb") as src, gzip.GzipFile(filename=str(out / (source.name + ".gz")), mode="wb", compresslevel=3, mtime=0) as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)
            del array
        result = {"status": "EXPORT_COMPLETE" if complete else "EXPORT_COVERAGE_FAILED", "requested_start": start, "end_exclusive": end,
                  "server": "Exness-MT5Trial16", "specification": specification, "coverage": coverage, "native": native,
                  "schema": [[name, str(RATE_DTYPE[name])] for name in RATE_DTYPE.names], "no_spread_imputation": True, "no_live_account_api": True}
        save(ROOT / "DATA.json", result)
        save(out / "results.json", result)
        if not complete:
            raise RuntimeError("Actual export does not cover all requested endpoints; DATA.json records gaps. Do not shift anchor silently.")
        return result


def recover_export(tag="data-2018-20261017"):
    """No terminal launch: verify/recover an already completed source-only export."""
    return export_data(tag, _recover=True)


CANDIDATE_DEFAULTS = {"timeframe_minutes": 5, "entry_mode": 0, "stop_mode": 0,
    "stop_value": 0, "target_rr": 0, "management_mode": 0, "management_value": 0,
    "filter_mode": 0, "filter_value": 0, "entry_minute_ny": 1020, "exit_minute_ny": 1020}
CANDIDATE_INPUTS = {"timeframe_minutes": "InpTimeframeMinutes", "entry_mode": "InpEntryMode",
    "stop_mode": "InpStopMode", "stop_value": "InpStopValue", "target_rr": "InpTargetRR",
    "management_mode": "InpManagementMode", "management_value": "InpManagementValue",
    "filter_mode": "InpFilterMode", "filter_value": "InpFilterValue",
    "entry_minute_ny": "InpEntryMinuteNY", "exit_minute_ny": "InpExitMinuteNY"}


def candidate_inputs(candidate, tag, start, end, sizing_mode=0, risk_percent=1):
    """Pure input mapping; candidate identity never changes the registered fields."""
    unknown = set(candidate) - set(CANDIDATE_DEFAULTS) - {"id", "label", "stage", "parent_id"}
    if unknown:
        raise ValueError("Unknown native candidate fields: " + ", ".join(sorted(unknown)))
    p = CANDIDATE_DEFAULTS | {k: v for k, v in candidate.items() if k in CANDIDATE_DEFAULTS}
    if p["timeframe_minutes"] not in (1, 3, 5, 15, 30, 60, 240, 1440):
        raise ValueError("Unregistered feature timeframe")
    for key, high in (("entry_mode", 2), ("stop_mode", 3), ("management_mode", 5), ("filter_mode", 7)):
        if p[key] != int(p[key]) or not 0 <= p[key] <= high:
            raise ValueError("Invalid " + key)
    for key in ("entry_minute_ny", "exit_minute_ny"):
        if p[key] != int(p[key]) or not 0 <= p[key] < 1440:
            raise ValueError("Invalid wall-clock minute")
    if p["stop_mode"] == 0 and (p["target_rr"] or p["management_mode"] or sizing_mode):
        raise ValueError("A no-stop strategy cannot be labelled stop-risk-sized or R-managed")
    if sizing_mode not in (0, 1) or not 0 < risk_percent <= 100:
        raise ValueError("Invalid sizing overlay")
    inputs = {"InpFrom": date_input(start), "InpTo": date_input(end),
              "InpHistoryFrom": "2018.01.01 00:00:00", "InpTag": valid_tag(tag)}
    inputs.update({CANDIDATE_INPUTS[k]: v for k, v in p.items()})
    inputs.update({"InpSizingMode": sizing_mode, "InpRiskPercent": risk_percent, "InpNotionalMultiple": 1})
    return p, inputs


def needs_features(p):
    return bool(p["entry_mode"] or p["stop_mode"] in (1, 3) or p["management_mode"] or p["filter_mode"] in range(1, 7))


def _resample_prefix(source, minutes):
    """Same frozen construction as search.py; source already ends before start."""
    if not len(source):
        return np.empty(0, dtype=RATE_DTYPE)
    groups = source["time"] // (minutes * 60)
    starts = np.r_[0, np.flatnonzero(np.diff(groups)) + 1]
    ends = np.r_[starts[1:], len(source)]
    result = np.zeros(len(starts), dtype=RATE_DTYPE)
    result["time"] = groups[starts] * minutes * 60
    result["open"] = source["open"][starts]
    result["high"] = np.maximum.reduceat(source["high"], starts)
    result["low"] = np.minimum.reduceat(source["low"], starts)
    result["close"] = source["close"][ends - 1]
    result["tick_volume"] = np.add.reduceat(source["tick_volume"], starts)
    result["spread"] = source["spread"][ends - 1]
    return result


def prepare_feature_prefix(candidate, tag, start):
    """No MT5 calls: hash-verified same-broker closed history, no future bytes.

    CopyRates may refuse 2018 history in a tester whose interval starts years
    later. The frozen exported prefix supplies indicator STATE only. All price
    decisions/fills inside the case still come from the native tester.
    """
    if not needs_features(candidate):
        return {"InpWarmFile": "", "InpWarmRows": 0, "InpWarmSHA256": ""}, {"needed": False, "reason": "Clock/no-feature hypothesis does not use any historical indicator"}
    if (ROOT / "native" / valid_tag(tag) / "manifest.json").exists():
        raise RuntimeError("Cannot change the prefix of an existing immutable native case")
    data = read(ROOT / "DATA.json")
    start_epoch = epoch(start)
    requested_from = epoch(data["requested_start"])
    used = []

    def load(label):
        record = next(x for x in data["coverage"] if x["timeframe"] == label)
        path = ROOT / record["path"]
        if record["sha256"] != sha(path):
            raise RuntimeError("Frozen exported prefix source hash changed: " + label)
        with np.load(path, allow_pickle=False) as saved:
            values = saved["rates"]
            # Truncate BEFORE any resampling or high/low aggregation.
            values = values[values["time"] < start_epoch].copy()
        used.append({"timeframe": label, "path": record["path"], "sha256": record["sha256"], "rows_before_case_start": len(values)})
        return values

    minute = int(candidate["timeframe_minutes"])
    native_labels = {1: "M1", 5: "M5", 60: "H1", 1440: "D1"}
    fine = load("M1")
    if minute == 1:
        bars = fine
        construction = "native exported M1"
    elif minute in native_labels:
        bars = load(native_labels[minute])
        construction = "native exported " + native_labels[minute]
    else:
        source = fine if minute < 5 else load("M5")
        bars = _resample_prefix(source, minute)
        construction = "UTC-aligned resampling of " + ("M1" if minute < 5 else "M5") + ", same OHLC/last-spread construction as search.py"
    bars = bars[(bars["time"] >= requested_from) & (bars["time"] + minute * 60 <= start_epoch)]
    counts = np.searchsorted(fine["time"], bars["time"] + minute * 60) - np.searchsorted(fine["time"], bars["time"])
    packed = np.zeros(len(bars), dtype=PREFIX_DTYPE)
    for name in RATE_DTYPE.names:
        packed[name] = bars[name]
    packed["complete"] = (counts == minute).astype(np.int32)
    common = _common(tag)
    common.mkdir(parents=True, exist_ok=True)
    path = common / "feature-prefix.bin"
    packed.tofile(path)
    receipt = {"needed": True, "sha256": sha(path), "rows": len(packed), "record_bytes": PREFIX_DTYPE.itemsize,
               "first_bar_open_epoch": int(bars["time"][0]) if len(bars) else None,
               "last_bar_open_epoch": int(bars["time"][-1]) if len(bars) else None,
               "last_bar_end_epoch": int(bars["time"][-1]) + minute * 60 if len(bars) else None,
               "all_bars_end_at_or_before_case_start": bool(np.all(bars["time"] + minute * 60 <= start_epoch)),
               "case_start_epoch": start_epoch, "incomplete_constituent_bars": int(np.sum(packed["complete"] == 0)),
               "construction": construction, "validity": "Each record carries exact M1 constituent count equality; native ring additionally requires temporal adjacency and 14-bar/EMA/ADX lookbacks.",
               "sources": used, "source_DATA_sha256": sha(ROOT / "DATA.json"),
               "scope": "Frozen same-broker historical indicator warm-up only; never prices/fills from outside the native case; no rows ending after case start are staged."}
    out = ROOT / "native" / tag
    out.mkdir(parents=True, exist_ok=True)
    save(out / "feature-prefix.json", receipt)
    with path.open("rb") as src, gzip.GzipFile(filename=str(out / "feature-prefix.bin.gz"), mode="wb", compresslevel=3, mtime=0) as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)
    return {"InpWarmFile": "feature-prefix.bin", "InpWarmRows": len(packed), "InpWarmSHA256": receipt["sha256"]}, receipt


def _csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _utc(at):
    return datetime.fromtimestamp(float(at), timezone.utc).isoformat()


def ny_weekend_schedule(friday, entry_minute=1020, exit_minute=1020):
    """Independent wall-clock oracle for native schedule audit, including DST."""
    from datetime import timedelta
    date = datetime.fromisoformat(friday).date()
    if date.weekday() != 4 or not 0 <= entry_minute < 1440 or not 0 <= exit_minute < 1440:
        raise ValueError("Expected a Friday and valid NY clock minutes")
    zone = ZoneInfo("America/New_York")
    local = datetime(date.year, date.month, date.day, tzinfo=zone)
    entry = local + timedelta(minutes=entry_minute)
    exit_at = local + timedelta(days=2, minutes=exit_minute)
    return int(entry.timestamp()), int(exit_at.timestamp())


def _dd(values, initial=10000):
    peak = float(initial)
    cash = pct = 0.0
    for value in values:
        peak = max(peak, float(value))
        cash = max(cash, peak - float(value))
        pct = max(pct, (peak - float(value)) / peak * 100 if peak > 0 else 0)
    return {"cash": cash, "pct": pct}


def _equity_audit(path):
    """Streaming reduction: a multi-year M1 file must not consume RAM as dicts."""
    peak = 10000.0
    cash = pct = 0.0
    first = last = None
    count = 0
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            value = float(row["equity"])
            if not math.isfinite(value) or value <= 0:
                raise RuntimeError("Invalid native equity audit")
            at = int(row["epoch"])
            if last is not None and at < last:
                raise RuntimeError("Native equity audit reversed time")
            first = at if first is None else first
            last = at
            peak = max(peak, value)
            cash = max(cash, peak - value)
            pct = max(pct, (peak - value) / peak * 100)
            count += 1
    if not count:
        raise RuntimeError("Empty native equity audit")
    return {"cash": cash, "pct": pct, "snapshots": count, "first_snapshot_epoch": first, "last_snapshot_epoch": last,
            "scope": "First tick per M1 plus entry/scheduled-exit/final snapshots, not every native tick"}


def _positions_from_deals(deals, orders, decisions):
    """Native position-ID grouping; includes opening costs and fee, no FIFO guesses."""
    groups = {}
    for deal in deals:
        if deal["symbol"] == "BTCUSD" and int(deal["type"]) in (0, 1) and int(deal["magic"]) == 86701701:
            groups.setdefault(deal["position_id"], []).append(deal)
    result = []
    for pid, rows in groups.items():
        entries = [d for d in rows if int(d["entry"]) == 0]
        exits = [d for d in rows if int(d["entry"]) in (1, 3)]
        if any(int(d["entry"]) == 2 for d in rows):
            raise RuntimeError("Unexpected native position reversal in a long-only weekly case")
        incoming = sum(float(d["volume"]) for d in entries)
        outgoing = sum(float(d["volume"]) for d in exits)
        if not entries or any(int(d["type"]) != 0 for d in entries):
            raise RuntimeError("Unexpected missing/non-long native entry")
        rows.sort(key=lambda d: (int(d["time_msc"]), int(d["ticket"])))
        entry = min(entries, key=lambda d: int(d["time_msc"]))
        order = next((x for x in orders if x["ticket"] == entry["order"]), None)
        if order is None:
            raise RuntimeError("Missing initial native order geometry")
        open_price = sum(float(d["price"]) * float(d["volume"]) for d in entries) / incoming
        close_price = sum(float(d["price"]) * float(d["volume"]) for d in exits) / outgoing if outgoing else None
        last = max(exits, key=lambda d: int(d["time_msc"])) if exits else None
        cost = {k: sum(float(d[k]) for d in rows) for k in ("profit", "commission", "swap", "fee")}
        actual_sl = float(order["sl"])
        fill = next((d for d in decisions if d["reason"] == "entry_filled" and abs(int(d["entry_epoch"]) - int(entry["epoch"])) <= 1), None)
        comments = [d["comment"] for d in exits]
        forced = any(re.search(r"end of test|test end", comment, re.I) for comment in comments)
        exit_label = "open" if not exits else "test-end" if forced else "SL" if int(last["reason"]) == 4 else "TP" if int(last["reason"]) == 5 else "scheduled/EA" if int(last["reason"]) == 3 else "other-native"
        row = {"position_id": pid, "side": "long", "volume": incoming,
               "open_epoch": int(entry["epoch"]), "open_time_msc": int(entry["time_msc"]), "open_time": _utc(entry["epoch"]),
               "close_epoch": int(last["epoch"]) if last else None, "close_time_msc": int(last["time_msc"]) if last else None,
               "close_time": _utc(last["epoch"]) if last else None, "open_price": open_price, "close_price": close_price,
               "initial_sl": actual_sl, "initial_tp": float(order["tp"]), "initial_r_points": open_price - actual_sl if actual_sl > 0 else None,
               "gross_profit": cost["profit"], "commission": cost["commission"], "swap": cost["swap"], "fee": cost["fee"],
               "net_profit": sum(cost.values()), "exit_reason": exit_label, "exit_comments": comments,
               "exit_fills": len(exits), "entry_fills": len(entries), "end_of_test_liquidation": forced,
               "closed": abs(incoming - outgoing) < 1e-8, "remaining_volume": incoming - outgoing,
               "scheduled_exit_epoch": int(fill["scheduled_exit_epoch"]) if fill else None,
               "native_entry_decision": fill}
        result.append(row)
    return sorted(result, key=lambda x: (x["close_time_msc"] or 10**20, x["open_time_msc"]))


def run_case(tag, candidate, start, end, model=4, delay_ms=150, sizing_mode=0, risk_percent=1, timeout=7200):
    """Explicit isolated invocation; root owns launch authorization and all sequencing.

    Default one-times-equity notional is DOWN-rounded. A mode1 protective-stop
    overlay is separately identified and remains bounded by one-times notional.
    """
    p, inputs = candidate_inputs(candidate, tag, start, end, sizing_mode, risk_percent)
    with tester_lease():
        warm_inputs, prefix = prepare_feature_prefix(p, tag, start)
        inputs.update(warm_inputs)
        out, began, journal, native = _execute_locked("BtcWeekend", tag, start, end, inputs, model, delay_ms, timeout)
        if "BW_NATIVE_COMPLETE" not in journal or re.search(r"BW_FATAL|BW_NATIVE_AUDIT_ERROR", journal):
            raise RuntimeError("Missing native completion or failed feature/audit export")
        if prefix["needed"]:
            if sha(_common(tag) / "feature-prefix.bin") != prefix["sha256"] or "BW_PREFIX_COMPLETE" not in journal or prefix["sha256"] not in journal:
                raise RuntimeError("Native historical prefix did not complete or changed during execution")
            receipts = re.findall(r"BW_PREFIX_COMPLETE rows=(\d+) last_end=(\d+) cutoff=(\d+) sha=([a-fA-F0-9]{64})", journal)
            expected = (str(prefix["rows"]), str(prefix["last_bar_end_epoch"] or 0), str(epoch(start)), prefix["sha256"])
            if not receipts or any(tuple(row) != expected for row in receipts):
                raise RuntimeError("Native prefix row count/end/cutoff/hash receipt mismatch")
            prefix["content_unchanged_after_native_execution"] = True
            prefix["native_rows_end_cutoff_hash_receipt_matches"] = True
        tables = {}
        artifacts = {}
        for name in ("deals", "orders", "decisions", "equity-m1", "stats"):
            source = _common(tag) / (name + ".csv")
            if not source.exists() or source.stat().st_mtime < began - 2:
                raise RuntimeError("Missing fresh native audit: " + name)
            tables[name] = _equity_audit(source) if name == "equity-m1" else _csv(source)
            compressed = out / (name + ".csv.gz")
            with source.open("rb") as src, gzip.GzipFile(filename=str(compressed), mode="wb", compresslevel=3, mtime=0) as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)
            artifacts[name] = {"path": str(compressed.relative_to(ROOT)), "sha256": sha(compressed), "uncompressed_sha256": sha(source), "uncompressed_bytes": source.stat().st_size, "gzip_level": 3}
        helpers = _report_helpers()
        report = TESTER / "reports/btc-weekend-pipeline-20261017" / (tag + ".htm")
        report_metrics = helpers._native_metrics(report)
        positions = _positions_from_deals(tables["deals"], tables["orders"], tables["decisions"])
        closed = [x for x in positions if x["closed"]]
        cash_deals = sorted([d for d in tables["deals"] if d["symbol"] == "BTCUSD" and int(d["type"]) in (0, 1)], key=lambda d: (int(d["time_msc"]), int(d["ticket"])))
        cash_net = sum(sum(float(d[k]) for k in ("profit", "commission", "swap", "fee")) for d in cash_deals)
        if abs(cash_net - report_metrics["net_profit"]) > .011:
            raise RuntimeError("Native cash/report total failed reconciliation")
        if len(closed) != report_metrics["trades"]:
            raise RuntimeError("Whole-position count differs from native report")
        win_cash = sum(max(0, x["net_profit"]) for x in closed)
        loss_cash = -sum(min(0, x["net_profit"]) for x in closed)
        balance = 10000.0
        cash_curve = []
        for d in cash_deals:
            balance += sum(float(d[k]) for k in ("profit", "commission", "swap", "fee"))
            cash_curve.append({"epoch": int(d["epoch"]), "time_msc": int(d["time_msc"]), "balance": balance})
        closed_balance = 10000.0
        closed_curve = []
        for x in closed:
            closed_balance += x["net_profit"]
            closed_curve.append(closed_balance)
        wins = [int(x["net_profit"] > 0) for x in closed]
        streak_w = streak_l = max_w = max_l = 0
        for x in closed:
            streak_w = streak_w + 1 if x["net_profit"] > 0 else 0
            streak_l = streak_l + 1 if x["net_profit"] < 0 else 0
            max_w, max_l = max(max_w, streak_w), max(max_l, streak_l)
        stats = tables["stats"][0]
        request_rows = [d for d in tables["decisions"] if d["reason"] == "entry_request"]
        for request in request_rows:
            at = int(request["epoch"])
            local_day = datetime.fromtimestamp(at, ZoneInfo("America/New_York")).date().isoformat()
            expected_entry, expected_exit = ny_weekend_schedule(local_day, p["entry_minute_ny"], p["exit_minute_ny"])
            if not expected_entry <= at < expected_entry + 60 or int(request["scheduled_exit_epoch"]) != expected_exit:
                raise RuntimeError("Native NY/DST entry/exit schedule failed independent wall-clock audit")
            if expected_exit >= epoch(end):
                raise RuntimeError("Native entered an administratively incomplete weekend")
        final_quote = int(stats["last_quote_epoch"])
        metrics = {"trades": len(closed), "wins": sum(wins), "losses": sum(x["net_profit"] < 0 for x in closed),
                   "win_rate_pct": 100 * sum(wins) / len(wins) if wins else None,
                   "profit_factor": win_cash / loss_cash if loss_cash else None,
                   "no_loss_trades": bool(closed and not loss_cash), "net_profit": cash_net,
                   "return_pct": cash_net / 10000 * 100, "initial_balance": 10000, "final_balance": 10000 + cash_net,
                   "max_win_streak": max_w, "max_loss_streak": max_l,
                   "closed_position_dd": _dd(closed_curve), "actual_cash_posting_dd": _dd([x["balance"] for x in cash_curve]),
                   "sampled_m1_equity_dd": tables["equity-m1"],
                   "native_report": report_metrics}
        result = {"tag": tag, "candidate": p, "start": start, "end_exclusive": end, "metrics": metrics,
                  "trades": positions, "native": native, "feature_prefix": prefix, "statistics": stats, "audit_artifacts": artifacts,
                  "entry_requests": request_rows,
                  "decision_counts": {reason: sum(d["reason"] == reason for d in tables["decisions"]) for reason in sorted({d["reason"] for d in tables["decisions"]})},
                  "last_quote_utc": _utc(final_quote), "requested_end_covered_to_within_5min": final_quote >= epoch(end) - 300,
                  "sizing": {"mode": "one-times-current-equity-notional" if sizing_mode == 0 else "separate-protective-stop-risk-overlay", "risk_percent_if_overlay": risk_percent if sizing_mode else None, "notional_cap": 1, "lot_rounding": "down; skip if below minimum"},
                  "cash_curve": cash_curve,
                  "verification": {"cash_report_reconciles": True, "native_position_count_reconciles": True, "cash_minus_native_report": cash_net - report_metrics["net_profit"], "explicit_input_report_parity": True, "ny_dst_entry_exit_schedule_matches_zoneinfo": True, "incomplete_weekends_not_entered": True},
                  "limitations": ["MT5 server timestamps are treated as UTC under the frozen Trial16 basis; NY dates are DST-adjusted separately.", "Model4 can use generated fallback where real tick history is unavailable; inspect native tick notes and history quality.", "M1 equity is the first observed tick per minute plus entry/exit snapshots, not an intraminute complete equity path.", "Filter7 uses the previous completed M5 bar's recorded spread divided by that bar's close; actual entry tick spread is separately logged as execution evidence.", "SL/TP are request-anchored and native execution-delay fills may alter realised initial R.", "No-live-account API or production deployment occurred."]}
        save(out / "results.json", result)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    exp = sub.add_parser("export")
    exp.add_argument("--tag", default="data-2018-20261017")
    exp.add_argument("--start")
    exp.add_argument("--end")
    recover = sub.add_parser("recover-export")
    recover.add_argument("--tag", default="data-2018-20261017")
    comp = sub.add_parser("compile")
    comp.add_argument("name", choices=["Export", "BtcWeekend"])
    case = sub.add_parser("run")
    case.add_argument("--tag", required=True)
    case.add_argument("--candidate", help="JSON file containing one flat registered candidate")
    case.add_argument("--start", required=True)
    case.add_argument("--end", required=True)
    case.add_argument("--model", type=int, choices=[1, 4], default=4)
    case.add_argument("--sizing-mode", type=int, choices=[0, 1], default=0)
    case.add_argument("--risk-percent", type=float, default=1)
    args = parser.parse_args()
    if args.action in ("export", "recover-export"):
        result = recover_export(args.tag) if args.action == "recover-export" else export_data(args.tag, args.start, args.end)
        print(json.dumps({"status": result["status"], "coverage": result["coverage"]}, indent=2))
    elif args.action == "compile":
        print(json.dumps(compile_ea(args.name), indent=2))
    else:
        result = run_case(args.tag, read(args.candidate) if args.candidate else {}, args.start, args.end, args.model, sizing_mode=args.sizing_mode, risk_percent=args.risk_percent)
        print(json.dumps({"tag": result["tag"], "metrics": result["metrics"], "verification": result["verification"]}, indent=2))


if __name__ == "__main__":
    main()
