from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PIPELINE = ROOT / "Run-ORB-H1-Pipeline.py"
spec = importlib.util.spec_from_file_location("h1_orb", PIPELINE)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load H1 ORB pipeline")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.prepare()

audit = json.loads((ROOT / "FINAL AUDIT.json").read_text(encoding="utf-8"))
base = deepcopy(audit["symbols"]["ustec"]["anchors"]["overlap-1300"]["selected_config"])
rows = []
for offset, rr in enumerate((3.0, 4.0, 5.0, 6.0, 8.0, 10.0), start=1):
    config = deepcopy(base)
    config["InpRewardRisk"] = rr
    row = module.run_case("ustec", "overlap-1300", "rr-extension", f"rr{rr:g}", config, 300 + offset)
    row["selection_score"] = module.score(row)
    rows.append(row)

winner = module.choose(rows, "rr")
payload = {
    "period": "2023-09-01 to 2025-08-31",
    "purpose": "Boundary extension because 4R won the initial 0.5R–4R grid",
    "winner": module.clean(winner),
    "rows": [module.clean(row) for row in rows],
}
(ROOT / "RR EXTENSION RESULTS.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
print(json.dumps([
    {
        "rr": row["config"]["InpRewardRisk"],
        "return_pct": row["return_pct"],
        "pf": row["profit_factor"],
        "win_pct": row["win_rate_pct"],
        "dd_pct": row["max_drawdown_pct"],
        "trades": row["trades"],
        "sharpe": row["sharpe"],
        "recovery": row["recovery_factor"],
        "score": row["selection_score"],
    }
    for row in rows
], indent=2))
print(f"WINNER {winner['config']['InpRewardRisk']}R")
