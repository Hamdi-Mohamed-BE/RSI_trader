from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
SYMBOLS = ("XAUUSD", "XAGUSD", "BTCUSD", "US30", "USTEC", "GBPJPY")
checks: list[tuple[bool, str]] = []


def check(condition: bool, label: str) -> None:
    checks.append((bool(condition), label))


native = json.loads((ROOT / "native-results.json").read_text(encoding="utf-8"))
locks = json.loads((ROOT / "selection-lock.json").read_text(encoding="utf-8"))
check(set(locks) == set(SYMBOLS), "selection lock contains all six required assets")
check(len(native) == 12, "six locked plus six three-year native results")
check(all(row["model"] == 0 for row in native), "every authoritative native result uses Every Tick model")
check(all(row["history_quality_pct"] >= 98 for row in native), "native history quality is at least 98%")
check(all(row["inputs"]["InpRiskPercent"] == 1.0 for row in native), "all native tests use fixed 1% risk")
check(all(row["inputs"]["InpTesterOnly"] is True for row in native), "all research sets remain tester-only")
check(all(row["config"] == locks[row["symbol"]]["config"] for row in native), "native configurations match the frozen lock")
check({row["stage"] for row in native} == {"locked", "full"}, "native horizons are locked and full")
check(all("(2025.09.01 - 2026.09.01)" in row["period"] for row in native if row["stage"] == "locked"), "locked date boundary is exact")
check(all("(2023.09.01 - 2026.09.01)" in row["period"] for row in native if row["stage"] == "full"), "three-year date boundary is exact")

for row in native:
    case_dir = ROOT / "Native" / row["case"]
    trades = json.loads((case_dir / "trades.json").read_text(encoding="utf-8"))
    check(len(trades) == row["trades"], f"{row['case']} trade ledger count reconciles")
    check(abs(sum(t["net"] for t in trades) - row["net_profit"]) <= .06, f"{row['case']} trade ledger P/L reconciles")
    expected = hashlib.sha256(((ROOT / "EA" / "Calyx Volatility Compression Expansion EA.mq5").read_text(encoding="utf-8") +
                               json.dumps(row["inputs"], sort_keys=True) +
                               ("2025.09.01" if row["stage"] == "locked" else "2023.09.01") + "2026.09.01" + "0").encode()).hexdigest()
    check(row["fingerprint"] == expected, f"{row['case']} artifact fingerprint matches")

compile_log = (ROOT / "EA" / "Calyx Volatility Compression Expansion EA.compile.log").read_text(encoding="utf-16")
check("0 errors, 0 warnings" in compile_log, "EA compiles with 0 errors and 0 warnings")
check((ROOT / "REPORT.md").exists(), "report exists")
check((ROOT / "native-monte-carlo-summary.csv").exists(), "native Monte Carlo summary exists")
for chart in ("native-locked-equity-curves.png", "native-locked-comparison.png", "native-monte-carlo.png"):
    check((ROOT / "Charts" / chart).exists(), f"chart exists: {chart}")

installers = list(PACKAGE.rglob("*.bat")) + list(PACKAGE.rglob("*.ps1"))
production_hits = []
for path in installers:
    if ROOT in path.parents:
        continue
    try:
        if re.search(r"Calyx Volatility Compression Expansion", path.read_text(encoding="utf-8", errors="ignore"), re.I):
            production_hits.append(str(path))
    except OSError:
        pass
check(not production_hits, "research EA is absent from production BAT/PowerShell installers")

passed = sum(ok for ok, _ in checks)
lines = [f"VERIFICATION: {passed}/{len(checks)} checks passed", ""]
lines += [("PASS " if ok else "FAIL ") + label for ok, label in checks]
if production_hits:
    lines += ["", "Unexpected production references:", *production_hits]
(ROOT / "VERIFICATION.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
if passed != len(checks):
    raise SystemExit(1)
