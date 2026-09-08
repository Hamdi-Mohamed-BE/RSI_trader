from pathlib import Path
import json

ROOT=Path(__file__).resolve().parent
checks=[]
def check(name,condition):checks.append((name,bool(condition)))

selection=json.loads((ROOT/"selection-lock.json").read_text(encoding="utf-8"));native=json.loads((ROOT/"native-results.json").read_text(encoding="utf-8"))
check("two frozen selections",set(selection)=={"USTEC","US30"})
check("risk fixed in every native input",all(float(row["inputs"]["InpRiskPercent"])==1.0 for row in native))
check("four native results",len(native)==4)
check("all native results valid",all(row["status"]=="valid" for row in native))
check("history quality at least 98%",all(float(row["history_quality_pct"])>=98 for row in native))
check("trade ledgers reconcile",all(int(row["audit"]["trades"])==int(row["trades"]) for row in native))
check("compile clean","0 errors, 0 warnings" in (ROOT/"EA"/"compile.log").read_text(encoding="utf-8"))
check("selection frozen before locked",json.loads((ROOT/"progress.json").read_text(encoding="utf-8"))["locked_first_read_after_freeze"] is True)
for name in ("all-screen-results.csv","rr-sensitivity.csv","stop-sensitivity.csv","management-sensitivity.csv","calendar-session-timeframe-sensitivity.csv","rolling-stability.csv","native-results.csv","native-monte-carlo-summary.csv","REPORT.md"):
    check(name,(ROOT/name).is_file() and (ROOT/name).stat().st_size>0)
for name in ("locked-summary.png","locked-equity-curves.png","rr-sensitivity.png","native-locked-summary.png","native-locked-equity.png","native-monte-carlo.png","rolling-stability.png"):
    check("chart "+name,(ROOT/"Charts"/name).is_file() and (ROOT/"Charts"/name).stat().st_size>1000)
text="\n".join(("PASS" if ok else "FAIL")+"  "+name for name,ok in checks)+f"\n\n{sum(ok for _,ok in checks)}/{len(checks)} checks passed.\n"
(ROOT/"VERIFICATION.txt").write_text(text,encoding="utf-8");print(text)
if not all(ok for _,ok in checks):raise SystemExit(1)
