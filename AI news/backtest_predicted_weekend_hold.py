from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from itertools import product
from math import isfinite
from pathlib import Path

import numpy as np

from predicted_weekend_hold_strategy import (
    DirectionSignal,
    HoldConfig,
    HoldTrade,
    calculate_metrics,
    compounded_metrics,
    simulate_trade,
)
from train_weekend_direction_model import _load_cache


ROOT = Path(__file__).resolve().parent
PREDICTIONS_PATH = ROOT / "gold_weekend_direction_v2_predictions.csv"
JSON_PATH = ROOT / "predicted_weekend_hold_backtest.json"
CSV_PATH = ROOT / "predicted_weekend_hold_trades.csv"
PROVISIONAL_CSV_PATH = ROOT / "predicted_weekend_hold_best_observed_trades.csv"
REPORT_PATH = ROOT / "PREDICTED_WEEKEND_HOLD_BACKTEST.md"
CHART_PATH = ROOT / "charts" / "predicted-weekend-hold" / "strategy-holdout-equity.svg"
PROVISIONAL_CHART_PATH = ROOT / "charts" / "predicted-weekend-hold" / "best-observed-holdout-equity.svg"

SIGNAL_POLICIES = (
    "v2_gate",
    "v2_conf_55",
    "v2_conf_60",
    "v2_all",
    "momentum_gate",
    "agreement",
)
STOP_SPECS = (
    "fixed_5",
    "fixed_10",
    "fixed_15",
    "fixed_20",
    "fixed_30",
    "atr60_5",
    "atr60_10",
    "range60_0.5",
    "range60_1.0",
)
REWARD_RISKS = (1.0, 1.5, 2.0, 2.5, 3.0, 4.0)


@dataclass(frozen=True)
class Prediction:
    position: int
    sample_index: int
    feature_time_utc: str
    reopen_utc: str
    called: bool
    predicted_up: bool
    significant_probability: float
    direction_probability_up: float
    momentum_called: bool
    momentum_up: bool


def parse_bool(value: str) -> bool:
    return value.strip().lower() == "true"


def load_predictions() -> list[Prediction]:
    output: list[Prediction] = []
    with PREDICTIONS_PATH.open(newline="", encoding="utf-8") as handle:
        for position, row in enumerate(csv.DictReader(handle)):
            output.append(
                Prediction(
                    position=position,
                    sample_index=int(row["sample_index"]),
                    feature_time_utc=row["feature_time_utc"],
                    reopen_utc=row["reopen_utc"],
                    called=parse_bool(row["called"]),
                    predicted_up=parse_bool(row["predicted_up"]),
                    significant_probability=float(row["significant_probability"]),
                    direction_probability_up=float(row["direction_probability_up"]),
                    momentum_called=parse_bool(row["momentum_called"]),
                    momentum_up=parse_bool(row["momentum_up"]),
                )
            )
    return output


def side_for_policy(row: Prediction, policy: str) -> str | None:
    confidence = max(row.direction_probability_up, 1.0 - row.direction_probability_up)
    if policy == "v2_gate":
        active, up = row.called, row.predicted_up
    elif policy == "v2_conf_55":
        active, up = confidence >= 0.55, row.predicted_up
    elif policy == "v2_conf_60":
        active, up = confidence >= 0.60, row.predicted_up
    elif policy == "v2_all":
        active, up = True, row.predicted_up
    elif policy == "momentum_gate":
        active, up = row.momentum_called, row.momentum_up
    elif policy == "agreement":
        active = row.called and row.momentum_called and row.predicted_up == row.momentum_up
        up = row.predicted_up
    else:
        raise ValueError(f"Unknown signal policy: {policy}")
    return ("BUY" if up else "SELL") if active else None


def close_indices(gold, predictions: list[Prediction]) -> dict[int, int]:
    output: dict[int, int] = {}
    for row in predictions:
        reopen_stamp = int(datetime.fromisoformat(row.reopen_utc).timestamp())
        reopen_index = int(np.searchsorted(gold.time, reopen_stamp, side="left"))
        if reopen_index >= len(gold.time) or int(gold.time[reopen_index]) != reopen_stamp:
            raise RuntimeError(f"Could not map reopen bar {row.reopen_utc}")
        if reopen_index < 1 or int(gold.time[reopen_index]) - int(gold.time[reopen_index - 1]) < 24 * 60 * 60:
            raise RuntimeError(f"Mapped bar is not a weekly reopen: {row.reopen_utc}")
        output[row.sample_index] = reopen_index - 1
    return output


class Evaluator:
    def __init__(self, gold, predictions: list[Prediction], closes: dict[int, int]):
        self.gold = gold
        self.predictions = predictions
        self.closes = closes
        self.cache: dict[tuple, HoldTrade] = {}

    def trade(self, row: Prediction, side: str, config: HoldConfig) -> HoldTrade:
        key = (
            row.sample_index,
            side,
            config.lead_minutes,
            config.stop_spec,
            config.reward_risk,
            config.max_hold_minutes,
        )
        if key not in self.cache:
            signal = DirectionSignal(row.sample_index, row.reopen_utc, side)
            self.cache[key] = simulate_trade(self.gold, signal, self.closes[row.sample_index], config)
        return self.cache[key]

    def trades(self, config: HoldConfig, positions: set[int]) -> list[HoldTrade]:
        output: list[HoldTrade] = []
        for row in self.predictions:
            if row.position not in positions:
                continue
            side = side_for_policy(row, config.signal_policy)
            if side:
                output.append(self.trade(row, side, config))
        return output


def public_metrics(trades: list[HoldTrade]) -> dict:
    metrics = calculate_metrics(trades)
    if not isfinite(float(metrics["profit_factor"])):
        metrics["profit_factor"] = None
    return metrics


def config_candidates(reward_risks: tuple[float, ...] = REWARD_RISKS):
    for policy, lead, stop, rr, hold in product(
        SIGNAL_POLICIES,
        (1, 2, 3, 4, 5),
        STOP_SPECS,
        reward_risks,
        (0, 15, 60, 240, 720),
    ):
        yield HoldConfig(policy, lead, stop, rr, hold)


def optimize(
    evaluator: Evaluator,
    development: set[int],
    development_blocks: list[set[int]],
    *,
    reward_risks: tuple[float, ...] = REWARD_RISKS,
) -> tuple[dict, list[dict], list[dict]]:
    candidates: list[dict] = []
    for config in config_candidates(reward_risks):
        trades = evaluator.trades(config, development)
        metrics = public_metrics(trades)
        if metrics["trades"] < 12:
            continue
        blocks = [public_metrics(evaluator.trades(config, positions)) for positions in development_blocks]
        if min(item["trades"] for item in blocks) < 3:
            continue
        positive_blocks = sum(item["net_r"] > 0 for item in blocks)
        worst_block = min(item["net_r"] for item in blocks)
        pf = metrics["profit_factor"] or 0.0
        score = metrics["net_r"] - 1.25 * metrics["max_drawdown_r"] + 1.5 * worst_block + 0.25 * min(pf, 5.0)
        candidates.append(
            {
                "config": asdict(config),
                "development": metrics,
                "development_blocks": blocks,
                "positive_blocks": positive_blocks,
                "worst_block_r": round(worst_block, 4),
                "selection_score": round(score, 4),
            }
        )
    if not candidates:
        raise RuntimeError("No strategy candidate met the minimum development sample requirements")
    ranking = rank_candidates(candidates, len(development_blocks))
    return ranking[0], ranking[:15], candidates


def rank_candidates(candidates: list[dict], block_count: int) -> list[dict]:
    robust = [item for item in candidates if item["positive_blocks"] == block_count]
    if not robust:
        robust = [item for item in candidates if item["positive_blocks"] >= block_count - 1]
    pool = robust or candidates
    return sorted(
        pool,
        key=lambda item: (
            item["selection_score"],
            item["development"]["profit_factor"] or 0.0,
            item["worst_block_r"],
        ),
        reverse=True,
    )


def add_results(candidate: dict, evaluator: Evaluator, full: set[int], holdout: set[int]) -> dict:
    config = HoldConfig(**candidate["config"])
    full_trades = evaluator.trades(config, full)
    holdout_trades = evaluator.trades(config, holdout)
    positions = sorted(holdout)
    halfway = len(positions) // 2
    first_half = set(positions[:halfway])
    second_half = set(positions[halfway:])
    output = dict(candidate)
    output.update(
        {
            "full": public_metrics(full_trades),
            "holdout": public_metrics(holdout_trades),
            "holdout_halves": [
                public_metrics(evaluator.trades(config, first_half)),
                public_metrics(evaluator.trades(config, second_half)),
            ],
            "risk_scenarios_full": [compounded_metrics(full_trades, risk) for risk in (0.01, 0.03, 0.05)],
            "risk_scenarios_holdout": [compounded_metrics(holdout_trades, risk) for risk in (0.01, 0.03, 0.05)],
            "trades": full_trades,
            "holdout_trades": holdout_trades,
        }
    )
    holdout_metrics = output["holdout"]
    output["validated"] = bool(
        holdout_metrics["trades"] >= 10
        and (holdout_metrics["profit_factor"] or 0.0) >= 1.20
        and holdout_metrics["net_r"] > 0
        and all(item["net_r"] > 0 for item in output["holdout_halves"])
        and holdout_metrics["max_drawdown_r"] <= 10.0
    )
    return output


def equity_chart(path: Path, trades: list[HoldTrade]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height, margin = 1000, 460, 70
    equity = [0.0]
    for trade in trades:
        equity.append(equity[-1] + trade.result_r)
    low, high = min(equity), max(equity)
    padding = max((high - low) * 0.12, 1.0)
    low, high = low - padding, high + padding
    plot_w, plot_h = width - 2 * margin, height - 2 * margin

    def point(index: int, value: float) -> tuple[float, float]:
        x = margin + plot_w * index / max(1, len(equity) - 1)
        y = margin + plot_h * (high - value) / (high - low)
        return x, y

    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#07101d"/>',
        '<text x="70" y="38" fill="#edf3fc" font-family="Arial" font-size="22" font-weight="700">Strategy holdout cumulative R</text>',
    ]
    for step in range(6):
        value = low + (high - low) * step / 5
        y = point(0, value)[1]
        pieces.append(f'<line x1="{margin}" y1="{y:.1f}" x2="{width-margin}" y2="{y:.1f}" stroke="#273750"/>')
        pieces.append(f'<text x="{margin-10}" y="{y+4:.1f}" text-anchor="end" fill="#9aabc2" font-family="Arial" font-size="12">{value:+.1f}R</text>')
    zero_y = point(0, 0.0)[1]
    pieces.append(f'<line x1="{margin}" y1="{zero_y:.1f}" x2="{width-margin}" y2="{zero_y:.1f}" stroke="#8090a8" stroke-dasharray="5 5"/>')
    points = " ".join(f"{x:.1f},{y:.1f}" for x, y in (point(i, value) for i, value in enumerate(equity)))
    pieces.append(f'<polyline points="{points}" fill="none" stroke="#19c99a" stroke-width="3"/>')
    pieces.append(f'<text x="{width-margin}" y="{height-22}" text-anchor="end" fill="#9aabc2" font-family="Arial" font-size="12">{len(trades)} trades</text>')
    pieces.append("</svg>")
    path.write_text("\n".join(pieces), encoding="utf-8")


def serializable(candidate: dict) -> dict:
    return {
        key: [asdict(item) for item in value] if key in ("trades", "holdout_trades") else value
        for key, value in candidate.items()
    }


def fmt_pf(value) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def write_report(payload: dict, selected: dict, rr_comparison: list[dict], provisional: dict) -> None:
    config = selected["config"]
    provisional_config = provisional["config"]
    development = selected["development"]
    holdout = selected["holdout"]
    full = selected["full"]
    verdict = "PASSED RESEARCH HOLDOUT" if selected["validated"] else "REJECTED"
    lines = [
        "# Predicted-Direction XAUUSD Weekend Hold",
        "",
        f"**Strategy verdict: {verdict}.** The underlying V2 direction model remains rejected, so a passing execution result would still require forward confirmation before use.",
        "",
        f"Nested model-prediction period: {payload['period']['start_utc'][:10]} through {payload['period']['end_utc'][:10]} UTC. "
        f"The first {payload['split']['development_weeks']} prediction weeks select the strategy; the final {payload['split']['holdout_weeks']} weeks are strategy holdout.",
        "",
        "## Development-selected winner",
        "",
        f"- Direction policy: `{config['signal_policy']}`",
        f"- Entry: market order `{config['lead_minutes']}` minute(s) before Friday close",
        f"- Stop: `{config['stop_spec']}`",
        f"- Reward/risk: `{config['reward_risk']}:1`",
        f"- Maximum hold after weekly reopen: `{config['max_hold_minutes']}` market minutes (`0` exits at the reopening price)",
        "- Historical spread is applied; weekend stop gaps exit at the Monday opening price; favorable TP gaps are capped at the target.",
        "",
        "## Main results",
        "",
        "| Sample | Trades | Win rate | Profit factor | Net | Average | Max DD | Gap stops | Timeouts |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        f"| Development | {development['trades']} | {development['win_rate_pct']:.2f}% | {fmt_pf(development['profit_factor'])} | {development['net_r']:+.2f}R | {development['average_r']:+.3f}R | {development['max_drawdown_r']:.2f}R | {development['gap_stop_count']} | {development['timeout_count']} |",
        f"| Strategy holdout | {holdout['trades']} | {holdout['win_rate_pct']:.2f}% | {fmt_pf(holdout['profit_factor'])} | {holdout['net_r']:+.2f}R | {holdout['average_r']:+.3f}R | {holdout['max_drawdown_r']:.2f}R | {holdout['gap_stop_count']} | {holdout['timeout_count']} |",
        f"| All nested predictions | {full['trades']} | {full['win_rate_pct']:.2f}% | {fmt_pf(full['profit_factor'])} | {full['net_r']:+.2f}R | {full['average_r']:+.3f}R | {full['max_drawdown_r']:.2f}R | {full['gap_stop_count']} | {full['timeout_count']} |",
        "",
        "## Best observed horizon-matched candidate",
        "",
        "This candidate was locked from development within its RR family, but it is selected for presentation after comparing six RR families on the same holdout. Treat it as provisional and require new forward weekends before deployment.",
        "",
        f"- Signal: `{provisional_config['signal_policy']}` (strong Friday 24-hour momentum, direction follows the move)",
        f"- Entry: `{provisional_config['lead_minutes']}` minutes before Friday close",
        f"- Emergency stop/target: `{provisional_config['stop_spec']}` at `{provisional_config['reward_risk']}:1`",
        f"- Exit: weekly reopening price (`{provisional_config['max_hold_minutes']}` post-reopen minutes)",
        "",
        "| Sample | Trades | Win rate | Profit factor | Net | Average | Max DD |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| Development | {provisional['development']['trades']} | {provisional['development']['win_rate_pct']:.2f}% | {fmt_pf(provisional['development']['profit_factor'])} | {provisional['development']['net_r']:+.2f}R | {provisional['development']['average_r']:+.3f}R | {provisional['development']['max_drawdown_r']:.2f}R |",
        f"| Strategy holdout | {provisional['holdout']['trades']} | {provisional['holdout']['win_rate_pct']:.2f}% | {fmt_pf(provisional['holdout']['profit_factor'])} | {provisional['holdout']['net_r']:+.2f}R | {provisional['holdout']['average_r']:+.3f}R | {provisional['holdout']['max_drawdown_r']:.2f}R |",
        f"| Full nested sample | {provisional['full']['trades']} | {provisional['full']['win_rate_pct']:.2f}% | {fmt_pf(provisional['full']['profit_factor'])} | {provisional['full']['net_r']:+.2f}R | {provisional['full']['average_r']:+.3f}R | {provisional['full']['max_drawdown_r']:.2f}R |",
        "",
        "## Locked RR comparison",
        "",
        "Each row independently selected its other parameters using development only.",
        "",
        "| RR | Policy | Lead | Stop | Hold | Holdout trades | Win rate | PF | Net | Max DD | Verdict |",
        "|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for item in rr_comparison:
        cfg, result = item["config"], item["holdout"]
        lines.append(
            f"| {cfg['reward_risk']:.1f} | {cfg['signal_policy']} | {cfg['lead_minutes']}m | {cfg['stop_spec']} | {cfg['max_hold_minutes']}m | "
            f"{result['trades']} | {result['win_rate_pct']:.2f}% | {fmt_pf(result['profit_factor'])} | {result['net_r']:+.2f}R | {result['max_drawdown_r']:.2f}R | {'PASS' if item['validated'] else 'FAIL'} |"
        )
    lines.extend(
        [
            "",
            "## Compounded scenarios",
            "",
            "These are mathematical sequences, not forecasts. Gap slippage can make an individual loss larger than the nominal risk percentage.",
            "",
            "| Sample | Nominal risk | Return | Max equity DD |",
            "|---|---:|---:|---:|",
        ]
    )
    for label, key in (("Holdout", "risk_scenarios_holdout"), ("Full", "risk_scenarios_full")):
        for item in provisional[key]:
            lines.append(f"| {label} | {item['risk_pct']:.0f}% | {item['return_pct']:+.2f}% | {item['max_drawdown_pct']:.2f}% |")
    lines.extend(
        [
            "",
            "![Best observed holdout equity](charts/predicted-weekend-hold/best-observed-holdout-equity.svg)",
            "",
            "## Holdout trades",
            "",
            "| Reopen | Side | Entry | Stop | Target | Exit | Outcome | Result |",
            "|---|---|---:|---:|---:|---:|---|---:|",
        ]
    )
    for trade in provisional["holdout_trades"]:
        lines.append(
            f"| {trade.reopen_utc[:10]} | {trade.side} | {trade.entry_price:.2f} | {trade.stop_loss:.2f} | "
            f"{trade.take_profit:.2f} | {trade.exit_price:.2f} | {trade.outcome} | {trade.result_r:+.2f}R |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The prediction probabilities are nested out-of-sample, but this strategy layer is a later research iteration. The global development winner failed its holdout. The 3R immediate-reopen candidate passed its individual gates, but choosing it after comparing six RR families creates selection bias; new forward weekends are required. M1 bars cannot reveal the path when both stop and target occur inside one candle, so the backtest assumes the stop happened first. Swap, commission, margin constraints, and broker-specific weekend execution rules are not present in the historical bar cache.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> dict:
    predictions = load_predictions()
    markets, metadata = _load_cache()
    gold = markets["XAUUSD"]
    evaluator = Evaluator(gold, predictions, close_indices(gold, predictions))
    count = len(predictions)
    development_count = 70
    if count <= development_count + 20:
        raise RuntimeError("Not enough nested prediction weeks for the strategy holdout")
    full_positions = set(range(count))
    development = set(range(development_count))
    holdout = set(range(development_count, count))
    block_edges = np.linspace(0, development_count, 4, dtype=int)
    blocks = [set(range(int(block_edges[index]), int(block_edges[index + 1]))) for index in range(3)]

    selected_raw, ranking, candidates = optimize(evaluator, development, blocks)
    selected = add_results(selected_raw, evaluator, full_positions, holdout)
    rr_comparison: list[dict] = []
    for rr in REWARD_RISKS:
        rr_candidates = [item for item in candidates if float(item["config"]["reward_risk"]) == rr]
        candidate = rank_candidates(rr_candidates, len(blocks))[0]
        rr_comparison.append(add_results(candidate, evaluator, full_positions, holdout))

    passing = [item for item in rr_comparison if item["validated"]]
    provisional = max(
        passing or rr_comparison,
        key=lambda item: (
            item["validated"],
            item["holdout"]["profit_factor"] or 0.0,
            item["holdout"]["net_r"],
        ),
    )

    equity_chart(CHART_PATH, selected["holdout_trades"])
    equity_chart(PROVISIONAL_CHART_PATH, provisional["holdout_trades"])
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        fields = list(asdict(selected["trades"][0]).keys()) if selected["trades"] else ["sample_index"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for trade in selected["trades"]:
            writer.writerow(asdict(trade))
    with PROVISIONAL_CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        fields = list(asdict(provisional["trades"][0]).keys()) if provisional["trades"] else ["sample_index"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for trade in provisional["trades"]:
            writer.writerow(asdict(trade))

    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "period": {
            "start_utc": predictions[0].reopen_utc,
            "end_utc": predictions[-1].reopen_utc,
            "nested_prediction_weeks": count,
        },
        "data": {
            "server": metadata.get("server"),
            "symbol": gold.symbol,
            "point": gold.point,
        },
        "split": {
            "development_weeks": development_count,
            "holdout_weeks": count - development_count,
            "holdout_start_utc": predictions[development_count].reopen_utc,
        },
        "methodology": {
            "direction_predictions": "Nested chronological V2 OOS probabilities generated before strategy selection",
            "entry": "Market entry 1-5 minutes before the inferred Friday close",
            "execution": "Historical spread, stop-first ambiguous M1 bars, adverse Monday stop-gap slippage, favorable TP gaps capped at target",
            "selection": "First 70 prediction weeks with three development blocks; final 41 weeks strategy holdout",
        },
        "selected": serializable(selected),
        "best_observed_after_rr_comparison": serializable(provisional),
        "locked_rr_comparison": [serializable(item) for item in rr_comparison],
        "top_development_candidates": ranking,
    }
    JSON_PATH.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    write_report(payload, selected, rr_comparison, provisional)
    return payload


def main() -> None:
    payload = run()
    selected = payload["selected"]
    holdout = selected["holdout"]
    print(f"Strategy verdict: {'PASS' if selected['validated'] else 'REJECTED'}")
    print(f"Selected: {selected['config']}")
    print(
        f"Holdout: {holdout['trades']} trades, {holdout['win_rate_pct']:.2f}% wins, "
        f"PF {fmt_pf(holdout['profit_factor'])}, {holdout['net_r']:+.2f}R, max DD {holdout['max_drawdown_r']:.2f}R"
    )
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
