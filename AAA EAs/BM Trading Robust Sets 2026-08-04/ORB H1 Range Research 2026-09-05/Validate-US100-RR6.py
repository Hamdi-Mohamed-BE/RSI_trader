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
base["InpRewardRisk"] = 6.0
locked = module.run_case("ustec", "overlap-1300", "locked-rr-extension", "rr6", base, 401, module.LOCKED)
full = module.run_case("ustec", "overlap-1300", "full-rr-extension", "rr6", base, 402, module.FULL)
outcomes = module.ORB.ANALYZER.trade_outcomes(locked["deals"])
mc = module.ORB.ANALYZER.monte_carlo(outcomes, locked["initial_balance"], 10_000)
payload = {
    "config": base,
    "locked": module.clean(locked),
    "full": module.clean(full),
    "monte_carlo": mc,
}
(ROOT / "US100 RR6 VALIDATION.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
set_name = "USTEC - overlap-1300 - H1 opening range - RR6 - 1pct.set"
(module.ORB.SETS / set_name).write_text(module.ORB.set_text(base, 962000402), encoding="utf-8")
print(json.dumps({
    "locked": {key: locked[key] for key in ("return_pct", "profit_factor", "win_rate_pct", "max_drawdown_pct", "trades", "sharpe", "recovery_factor")},
    "full": {key: full[key] for key in ("return_pct", "profit_factor", "win_rate_pct", "max_drawdown_pct", "trades", "sharpe", "recovery_factor")},
    "monte_carlo": mc,
    "set": str(module.ORB.SETS / set_name),
}, indent=2))
