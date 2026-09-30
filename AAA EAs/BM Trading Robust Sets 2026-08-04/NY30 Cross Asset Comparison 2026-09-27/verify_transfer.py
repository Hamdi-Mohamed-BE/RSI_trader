"""Additional verification not dependent on the performance report."""
from pathlib import Path
import hashlib,json,sys,gzip,re
from datetime import datetime
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent;GOLD=BASE/"Gold NY30 Value Area VWAP Raw 2026-09-27"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def main():
 source=GOLD/"GoldNY30.mq5";binary=source.with_suffix(".ex5")
 build=load(GOLD/"BUILD.json")
 assert sha(source)==build["source_sha256"] and sha(binary)==build["binary_sha256"]
 configs=[load(BASE/(a+" NY30 Value Area VWAP Raw 2026-09-27")/"run-config.json") for a in ("Gold","US100","US500")]
 for cfg in configs[1:]:
  for key in ("deposit","risk_percent","lot_rounding","delay_ms","variants","periods","fixed","reversal","continuation","control","arbitration","gate","schedule"):
   assert cfg[key]==configs[0][key],key
 assert [c["symbol"] for c in configs]==["XAUUSD","USTEC","US500"]
 evidence={}
 for asset,symbol in (("US100","USTEC"),("US500","US500")):
  root=BASE/(asset+" NY30 Value Area VWAP Raw 2026-09-27")
  frozen=load(root/"BUILD.json")
  assert sha(root/"run-config.json")==frozen["config_sha256"]
  assert sha(root/"RULES.md")==frozen["rules_sha256"]
  cases=list((root/"native").glob("*/run.json"))
  for p in cases:
   m=load(p);assert m["ok"]
   assert m["tag"].startswith(symbol+"-")
   assert m["delay_ms"]==150
   assert m["source_sha256"]==sha(source) and m["binary_sha256"]==sha(binary)
   begin=datetime.strptime(m["start"],"%Y.%m.%d");end=datetime.strptime(m["end"],"%Y.%m.%d")
   for trade in load(p.parent/"trades.json"):
    assert trade["symbol"]==symbol
    assert begin<=datetime.fromisoformat(trade["open_time"])<=datetime.fromisoformat(trade["close_time"])<end
   a=p.parent/"AUDIT.json"
   if a.exists():
    ar=load(a);assert ar["ok"] and ar["bars_with_real_volume"]==0
   journal=gzip.decompress((p.parent/"journal.txt.gz").read_bytes()).decode()
   assert "NY30_SPEC|"+symbol+"|" in journal
  evidence[asset]={"native_cases":len(cases),"audited":sum((p.parent/"AUDIT.json").exists() for p in cases)}
 deps={str(p):sha(p) for p in (source,binary,GOLD/"audit.py",GOLD/"final_check.py",GOLD/"test_stats.py",BASE/"PIPELINE.md",ROOT/"run_transfer.py",ROOT/"make_report.py")}
 out=dict(ok=True,settings_parity=True,source_binary_parity=True,evidence=evidence,dependency_hashes=deps)
 (ROOT/"PARITY_CHECK.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
 print(json.dumps({k:v for k,v in out.items() if k!="dependency_hashes"},indent=2))
if __name__=="__main__":main()
