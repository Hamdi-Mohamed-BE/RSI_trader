from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
BASE_PATH = ROOT / "analyze_prop_portfolio.py"
PATHS = 100_000
DAYS = 84
BLOCK = 20
SEED = 20260817


def load_base():
    spec = importlib.util.spec_from_file_location("prop_base", BASE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(BASE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bootstrap(daily: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    blocks = math.ceil(DAYS / BLOCK)
    starts = rng.integers(0, len(daily) - BLOCK + 1, size=(PATHS, blocks))
    indices = (starts[:, :, None] + np.arange(BLOCK)[None, None, :]).reshape(PATHS, -1)[:, :DAYS]
    return daily[indices]


def simulate(daily: np.ndarray, phase1_target: float, stressed: bool, seed_offset: int) -> dict:
    rng = np.random.default_rng(SEED + seed_offset)
    returns = bootstrap(daily, rng)
    if stressed:
        returns = np.where(returns >= 0.0, returns * 0.90, returns * 1.10)

    # 0=phase 1, 1=phase 2, 2=funded, 3=first reward, -1=failed.
    stage = np.zeros(PATHS, dtype=np.int8)
    balance = np.ones(PATHS, dtype=float)
    trade_days = np.zeros(PATHS, dtype=np.int16)
    funded_days = np.zeros(PATHS, dtype=np.int16)
    for day in range(DAYS):
        live = (stage >= 0) & (stage < 3)
        today = returns[:, day]
        balance[live] *= 1.0 + today[live]
        trade_days[live & (np.abs(today) > 1e-12)] += 1
        funded_days[stage == 2] += 1

        failed = live & ((today <= -0.05) | (balance <= 0.90))
        stage[failed] = -1

        p1 = (stage == 0) & (balance >= 1.0 + phase1_target) & (trade_days >= 3)
        stage[p1] = 1
        balance[p1] = 1.0
        trade_days[p1] = 0

        p2 = (stage == 1) & (balance >= 1.05) & (trade_days >= 3)
        stage[p2] = 2
        balance[p2] = 1.0
        funded_days[p2] = 0

        paid = (stage == 2) & (funded_days >= 10) & (balance >= 1.02)
        stage[paid] = 3

    return {
        "phase1_or_better_pct": float(np.mean(stage >= 1) * 100.0),
        "funded_or_better_pct": float(np.mean(stage >= 2) * 100.0),
        "first_reward_pct": float(np.mean(stage == 3) * 100.0),
        "failed_pct": float(np.mean(stage == -1) * 100.0),
        "still_in_progress_pct": float(np.mean((stage == 0) | (stage == 1) | (stage == 2)) * 100.0),
    }


def main() -> None:
    base = load_base()
    parser = base.load_parser()
    manifest = json.loads((base.SOURCE / "manifest.json").read_text(encoding="utf-8-sig"))
    cases = {case["id"]: case for case in manifest if case["id"] in base.SELECTED_IDS}
    rows = {key: parser.parse_report(Path(case["report"]), case) for key, case in cases.items()}

    output = {
        "method": "100,000 20-day block-bootstrap paths over 84 trading days; sequential phase 1, phase 2, then +2% funded reward after ten funded trading days; static -10% and daily -5% failure rules; realized deal stream only",
        "four_months": {},
    }
    seed_offset = 0
    for risk in (0.35, 0.50, 0.75, 1.00):
        name = f"risk_{risk:.2f}pct"
        _, _, daily = base.scenario_metrics(
            name,
            {"02-orb-volume-profile": risk, "07-aaa-final-ema3": risk},
            rows,
        )
        output["four_months"][name] = {}
        for firm, target in (("FTMO_2Step_10pct", 0.10), ("The5ers_Classic_8pct", 0.08)):
            seed_offset += 10
            output["four_months"][name][firm] = {
                "nominal": simulate(daily, target, False, seed_offset),
                "execution_stress": simulate(daily, target, True, seed_offset + 1),
            }

    (ROOT / "four-month-results.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
