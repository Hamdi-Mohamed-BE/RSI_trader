"""Isolated native tester orchestration; no live terminal, no order API, no promotion."""
from pathlib import Path
import os, sys, json, importlib.util, hashlib, gzip, re, subprocess, time
os.environ["EA_STORE_DISABLE_MT5"]="1"
ROOT=Path(__file__).resolve().parent
PACKAGE=ROOT.parent
OLD=PACKAGE/"No Wick Candle Raw 2026-09-25"
spec=importlib.util.spec_from_file_location("retained_no_wick_runner",OLD/"run_nw.py")
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
CONFIG=json.loads((ROOT/"run-config.json").read_text())
private_login=base.CONFIG["login"]
base.ROOT=ROOT;base.OUT=ROOT/"native";base.STATUS=base.OUT/"status.json"
base.CONFIG=CONFIG|{"login":private_login}
base.TESTER=PACKAGE/CONFIG["isolated_tester"]
base.REPORT_DIR=base.TESTER/"reports"/"calyx-no-wick"
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def tick_notes(journal):
    """Same line matches as the prior regex, without quadratic rescans of each line."""
    keys=('real ticks begin','real ticks absent','ticks discarded','tick generation')
    return sorted({line for line in journal.splitlines() if any(k in line.lower() for k in keys)})[:30]
def checked_fail(msg):
    safe=str(msg).replace(str(private_login),"[ACCOUNT]")
    base.status(state="FAILED",error=safe,event="FAILED: "+safe)
    raise RuntimeError(safe)
base.fail=checked_fail

def preflight():
    assert str(base.TESTER).endswith("_Backtests\\MT5-DMC-20260811")
    assert not base.isolated_running(),"Isolated tester is already in use."
    assert not base.port_3000_busy(),"Port 3000 belongs to another process; do not interrupt it."
    profile=base.TESTER/"MQL5"/"Profiles"/"Charts"/CONFIG["profile"]
    assert profile.is_dir() and not list(profile.glob("*.chr")),"Research profile must exist and be empty."
    common=base.text(base.TESTER/"Config"/"common.ini")
    found=re.search(r"(?im)^Login\s*=\s*(\d+)",common)
    assert found and int(found.group(1))==int(private_login),"Isolated tester account has changed; inspect before running."
    del common
    history=base.TESTER/"bases"/CONFIG["server"]/"history"
    assert all((history/s).is_dir() for s,_ in CONFIG["matrix"]),"Requested symbol not present in isolated broker history."
    processes=subprocess.check_output(["powershell","-NoProfile","-Command",
        "Get-CimInstance Win32_Process -Filter \"Name = 'terminal64.exe'\" | Select-Object ProcessId,ExecutablePath | ConvertTo-Json -Compress"],text=True).strip()
    preflight_path=ROOT/("preflight-resume.json" if (ROOT/"preflight.json").exists() else "preflight.json")
    preflight_path.write_text(json.dumps({"utc":base.now(),"tester_path":str(base.TESTER),"server":CONFIG["server"],
        "account_match":True,"account_id_published":False,"empty_profile":True,"normal_terminal_not_touched":True,
        "running_terminals_before":json.loads(processes) if processes else [],
        "symbols":sorted({s for s,_ in CONFIG["matrix"]}),"config_sha256":digest(ROOT/"run-config.json"),
        "rules_sha256":digest(ROOT/"RULES.md")},indent=2))
    base.OUT.mkdir(parents=True,exist_ok=True)

def run_case(symbol,variant,period):
    base.CONFIG["period"]="M5" if variant.endswith("5") and not variant.endswith("15") else "M15"
    result=base.run_case(symbol,variant,period)
    folder=base.OUT/result["case"]
    report=base.REPORT_DIR/(result["case"]+".htm")
    trades=json.loads(gzip.decompress((folder/"trades.json.gz").read_bytes()))
    report_text=base._read_report(report)
    result["metrics"]["max_relative_equity_dd_pct"]=base._number(base._metric(report_text,"Equity Drawdown Relative"))
    result["metrics"]["max_relative_balance_dd_pct"]=base._number(base._metric(report_text,"Balance Drawdown Relative"))
    expected=base.variant_inputs(variant)
    actual=base._report_inputs(report)
    assert all(k in actual and base._same_setting(v,actual[k]) for k,v in expected.items()),"Exact input verification failed"
    assert len(trades)==result["metrics"]["trades"],"Trade count reconciliation failed"
    assert abs(sum(t["net_profit"] for t in trades)-result["metrics"]["net_profit"])<=max(.05,len(trades)*.011),"Net cash flow mismatch"
    journal=gzip.decompress((folder/"journal.txt.gz").read_bytes()).decode()
    assert not result["journal_flags"]["init_failed"] and not result["journal_flags"]["critical"],"Fatal tester diagnostic"
    assert "NW_SPEC " in journal and "NW_STATS " in journal,"EA lifecycle evidence missing"
    accepted=len(re.findall("NW_SIGNAL ",journal))
    signals=re.findall(r"NW_SIGNAL time=(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}) signal=(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}) side=(-?\d+) entry=([\d.]+) sl=([\d.]+) tp=([\d.]+) pivot=([\d.]+) volume=([\d.]+)",journal)
    from datetime import datetime
    signal_seconds=int(expected["InpSignalTimeframe"])*60
    for placed_at,bar_at,direction,entry,sl,tp,pivot,volume in signals:
        a=datetime.strptime(placed_at,"%Y.%m.%d %H:%M:%S");b=datetime.strptime(bar_at,"%Y.%m.%d %H:%M:%S")
        assert (a-b).total_seconds()>=signal_seconds,"Entry used an unclosed signal candle"
        d=int(direction);entry=float(entry);sl=float(sl);tp=float(tp)
        assert d*(entry-sl)>0 and d*(tp-entry)>0,"Invalid stop/target direction"
        assert abs(abs(tp-entry)-abs(entry-sl))<=max(1e-8,abs(entry-sl)*1e-7),"Not 1:1 at placement"
    result["audit"]={"exact_inputs":True,"ledger_reconciled":True,"signals_logged":accepted,"causal_and_1R_checks":len(signals),
        "spec_lines":sorted(set(re.findall(r"NW_SPEC [^\r\n]+",journal))),
        "stats_lines":sorted(set(re.findall(r"NW_STATS [^\r\n]+",journal))),
        "tick_notes":tick_notes(journal),
        "commission":round(sum(t["commission"] for t in trades),2),"swap":round(sum(t["swap"] for t in trades),2),
        "source_sha256":digest(ROOT/CONFIG["source"]),"ex5_sha256":digest((ROOT/CONFIG["source"]).with_suffix(".ex5")),
        "trades_sha256":digest(folder/"trades.json.gz")}
    (folder/"run.json").write_text(json.dumps(result,indent=2))
    return result

def main():
    args=sys.argv[1:] or ["all"]
    preflight()
    if "compile" in args or "all" in args:
        build=base.compile_ea()
        assert re.search(r"0 warnings?",build["compile_tail"]),build["compile_tail"]
        deps=[OLD/"EA"/"AAA_Final_Common.mqh",OLD/"EA"/"DynamicTrailingSessionFilter.mqh",PACKAGE/"_Shared"/"CalyxAdaptivePortfolio.mqh"]
        build["dependencies"]={str(p.relative_to(PACKAGE)):digest(p) for p in deps}
        build["terminal_build"]=subprocess.check_output(["powershell","-NoProfile","-Command",f"(Get-Item -LiteralPath '{base.TESTER / 'terminal64.exe'}').VersionInfo.FileVersion"],text=True).strip()
        (base.OUT/"build.json").write_text(json.dumps(build,indent=2))
    base.install_experts()
    if "smoke" in args or "all" in args:run_case("EURUSD","S15","smoke")
    if "main" in args or "all" in args:
        for symbol,variant in CONFIG["matrix"]:
            for period in CONFIG["main_periods"]:run_case(symbol,variant,period)
    if "control" in args or "all" in args:
        for symbol,variant in CONFIG["matrix"]:
            for period in CONFIG["control_periods"]:run_case(symbol,variant.replace("S","C"),period)
    base.summary()
    base.status(state="ALL DONE",event="ALL REQUESTED STAGES DONE")
if __name__=="__main__":main()
