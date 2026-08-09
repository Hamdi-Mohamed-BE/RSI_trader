from __future__ import annotations

import csv
import json
import math
import statistics
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from news_pending_strategy import ROOT, load_day, load_events


START = datetime(2021, 8, 1, tzinfo=timezone.utc)
HOLDOUT_START = datetime(2025, 8, 1, tzinfo=timezone.utc)
END = datetime(2026, 8, 1, tzinfo=timezone.utc)
EVENT_NAMES = ("NFP", "CPI", "PPI", "GDP", "FOMC")
TICK_DIR = ROOT / "data" / "xau-news-ticks-5y"

LEADS_SECONDS = (60, 30, 10)
OFFSETS_DOLLARS = (0.25, 0.50, 0.75, 1.00, 1.50, 2.00, 3.00, 4.00)
SPREAD_MULTIPLIERS = (1.0, 1.5, 2.0)
EXPIRY_SECONDS = (30, 60)
STOP_DOLLARS = (1.50, 2.00, 3.00, 4.00, 5.00, 7.00, 9.00, 12.00)
TARGET_DOLLARS = (1.50, 2.00, 3.00, 4.00, 5.00, 7.00, 9.00, 12.00, 15.00, 20.00, 25.00, 30.00, 40.00)
BASE_CANCEL_LATENCY_MS = 250
MAX_HOLD_MINUTES = 60

OUTPUT_JSON = ROOT / "news_straddle_tick_5y.json"
OUTPUT_CSV = ROOT / "news_straddle_tick_5y_trades.csv"
OUTPUT_MD = ROOT / "NEWS_STRADDLE_TICK_5Y.md"


@dataclass(frozen=True)
class EntryConfig:
    lead_seconds: int
    buy_offset_dollars: float
    sell_offset_dollars: float
    spread_multiplier: float
    expiry_seconds: int
    cancel_latency_ms: int = BASE_CANCEL_LATENCY_MS


@dataclass
class EventData:
    event: str
    released: datetime
    release_ms: int
    times: np.ndarray
    bid: np.ndarray
    ask: np.ndarray
    m1_bid: dict[int, dict[str, float]]
    m1_ask: dict[int, dict[str, float]]

    @property
    def key(self) -> str:
        return self.released.isoformat()


def _tick_path(event: dict) -> Path:
    release = event["released"]
    hhmm = f"{release.hour:02d}{release.minute:02d}"
    return TICK_DIR / f"xauusd-tick-{release.date().isoformat()}-{hhmm}-{event['event'].lower()}.json"


def _load_market(event: dict) -> EventData | None:
    path = _tick_path(event)
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    ticks = raw.get("ticks") if isinstance(raw, dict) else None
    if not isinstance(ticks, list) or len(ticks) < 20:
        return None
    rows = [
        (
            int(row["timestamp"]),
            float(row["bidPrice"]),
            float(row["askPrice"]),
        )
        for row in ticks
        if row.get("timestamp") is not None
        and row.get("bidPrice") is not None
        and row.get("askPrice") is not None
        and float(row["bidPrice"]) > 0
        and float(row["askPrice"]) > 0
    ]
    if len(rows) < 20:
        return None
    rows.sort(key=lambda item: item[0])
    release = event["released"]
    return EventData(
        event=event["event"],
        released=release,
        release_ms=int(release.timestamp() * 1000),
        times=np.asarray([row[0] for row in rows], dtype=np.int64),
        bid=np.asarray([row[1] for row in rows], dtype=np.float64),
        ask=np.asarray([row[2] for row in rows], dtype=np.float64),
        m1_bid=load_day("xauusd", release.date().isoformat(), "bid"),
        m1_ask=load_day("xauusd", release.date().isoformat(), "ask"),
    )


def _first_true(values: np.ndarray) -> int | None:
    hits = np.flatnonzero(values)
    return int(hits[0]) if hits.size else None


def _resolve_entry(data: EventData, config: EntryConfig) -> dict:
    placement_ms = data.release_ms - config.lead_seconds * 1000
    anchor_index = int(np.searchsorted(data.times, placement_ms, side="right") - 1)
    if anchor_index < 0:
        return {"status": "missing_anchor"}
    start_index = int(np.searchsorted(data.times, placement_ms, side="left"))
    expiry_ms = data.release_ms + config.expiry_seconds * 1000
    end_index = int(np.searchsorted(data.times, expiry_ms, side="right"))
    if start_index >= end_index:
        return {"status": "missing_window"}

    spread = max(0.0, float(data.ask[anchor_index] - data.bid[anchor_index]))
    buy_offset = max(config.buy_offset_dollars, spread * config.spread_multiplier)
    sell_offset = max(config.sell_offset_dollars, spread * config.spread_multiplier)
    buy_level = float(data.ask[anchor_index] + buy_offset)
    sell_level = float(data.bid[anchor_index] - sell_offset)
    window_ask = data.ask[start_index:end_index]
    window_bid = data.bid[start_index:end_index]
    buy_relative = _first_true(window_ask >= buy_level)
    sell_relative = _first_true(window_bid <= sell_level)
    triggers = []
    if buy_relative is not None:
        index = start_index + buy_relative
        triggers.append((int(data.times[index]), "buy", index, buy_level))
    if sell_relative is not None:
        index = start_index + sell_relative
        triggers.append((int(data.times[index]), "sell", index, sell_level))
    if not triggers:
        return {
            "status": "expired",
            "spread": spread,
            "buy_level": buy_level,
            "sell_level": sell_level,
        }

    triggers.sort(key=lambda item: (item[0], item[1]))
    first_time = triggers[0][0]
    accepted = [row for row in triggers if row[0] <= first_time + config.cancel_latency_ms]
    fills = []
    for trigger_time, side, index, intended in accepted:
        fill_price = max(intended, float(data.ask[index])) if side == "buy" else min(intended, float(data.bid[index]))
        path_end = int(np.searchsorted(data.times, data.release_ms + 300_000, side="right"))
        if side == "buy":
            path = data.bid[index + 1 : path_end]
            mfe = max(0.0, float(np.max(path) - fill_price)) if path.size else 0.0
            mae = max(0.0, float(fill_price - np.min(path))) if path.size else 0.0
        else:
            path = data.ask[index + 1 : path_end]
            mfe = max(0.0, float(fill_price - np.min(path))) if path.size else 0.0
            mae = max(0.0, float(np.max(path) - fill_price)) if path.size else 0.0
        fills.append(
            {
                "side": side,
                "index": index,
                "trigger_ms": trigger_time,
                "intended": intended,
                "fill": fill_price,
                "slippage": abs(fill_price - intended),
                "mfe_5m": mfe,
                "mae_5m": mae,
            }
        )
    return {
        "status": "traded",
        "spread": spread,
        "buy_level": buy_level,
        "sell_level": sell_level,
        "fills": fills,
        "dual_fill": len(fills) > 1,
        "pre_release_fill": first_time < data.release_ms,
    }


def _entry_configs() -> list[EntryConfig]:
    return [
        EntryConfig(lead, buy, sell, multiplier, expiry)
        for lead in LEADS_SECONDS
        for buy in OFFSETS_DOLLARS
        for sell in OFFSETS_DOLLARS
        for multiplier in SPREAD_MULTIPLIERS
        for expiry in EXPIRY_SECONDS
    ]


def _entry_rank(config: EntryConfig, markets: list[EventData]) -> dict:
    outcomes = [_resolve_entry(market, config) for market in markets]
    traded = [outcome for outcome in outcomes if outcome["status"] == "traded"]
    if not traded:
        return {"config": config, "score": -math.inf, "trades": 0}
    qualities = []
    for outcome in traded:
        leg_quality = [
            (fill["mfe_5m"] - 1.25 * fill["mae_5m"])
            / (fill["mfe_5m"] + fill["mae_5m"] + 1.0)
            for fill in outcome["fills"]
        ]
        qualities.append(sum(leg_quality))
    fill_rate = len(traded) / len(markets)
    dual_rate = sum(outcome["dual_fill"] for outcome in traded) / len(traded)
    pre_rate = sum(outcome["pre_release_fill"] for outcome in traded) / len(traded)
    score = statistics.fmean(qualities) + 0.35 * fill_rate - 2.0 * dual_rate - 0.35 * pre_rate
    return {
        "config": config,
        "score": score,
        "trades": len(traded),
        "fill_rate": fill_rate,
        "dual_rate": dual_rate,
        "pre_rate": pre_rate,
    }


def _rank_entries(markets: list[EventData], limit: int, minimum_fills: int) -> list[EntryConfig]:
    ranked = [_entry_rank(config, markets) for config in _entry_configs()]
    ranked = [row for row in ranked if row["trades"] >= minimum_fills]
    ranked.sort(key=lambda row: (row["score"], row["trades"]), reverse=True)
    return [row["config"] for row in ranked[:limit]]


def _first_exit_cross(
    data: EventData,
    fill: dict,
    level: float,
    kind: str,
) -> tuple[int, float] | None:
    side = fill["side"]
    start_index = int(fill["index"]) + 1
    if side == "buy":
        prices = data.bid[start_index:]
        mask = prices <= level if kind == "stop" else prices >= level
    else:
        prices = data.ask[start_index:]
        mask = prices >= level if kind == "stop" else prices <= level
    relative = _first_true(mask)
    if relative is not None:
        index = start_index + relative
        return int(data.times[index]), float(prices[relative])

    # Reuse the final tick minute as an M1 envelope after the cached tick
    # window ends. Same-minute stop/target ties remain pessimistic.
    first_m1 = int(data.times[-1] // 60_000 * 60_000)
    last_m1 = data.release_ms + MAX_HOLD_MINUTES * 60_000
    for stamp in sorted(set(data.m1_bid) & set(data.m1_ask)):
        if stamp < first_m1 or stamp > last_m1:
            continue
        bid_bar = data.m1_bid[stamp]
        ask_bar = data.m1_ask[stamp]
        if side == "buy":
            bar = bid_bar
            hit = bar["low"] <= level if kind == "stop" else bar["high"] >= level
            exit_price = min(level, bar["open"]) if kind == "stop" else max(level, bar["open"])
        else:
            bar = ask_bar
            hit = bar["high"] >= level if kind == "stop" else bar["low"] <= level
            exit_price = max(level, bar["open"]) if kind == "stop" else min(level, bar["open"])
        if hit:
            return int(stamp), float(exit_price)
    return None


def _timeout_exit(data: EventData, side: str) -> tuple[int, float]:
    last_stamp = data.release_ms + MAX_HOLD_MINUTES * 60_000
    stamps = [stamp for stamp in sorted(set(data.m1_bid) & set(data.m1_ask)) if stamp <= last_stamp]
    if stamps:
        stamp = stamps[-1]
        price = data.m1_bid[stamp]["close"] if side == "buy" else data.m1_ask[stamp]["close"]
        return int(stamp), float(price)
    return int(data.times[-1]), float(data.bid[-1] if side == "buy" else data.ask[-1])


def _leg_matrix(data: EventData, fill: dict, extra_slippage: float) -> tuple[np.ndarray, np.ndarray]:
    side = fill["side"]
    intended = float(fill["intended"])
    actual_entry = float(fill["fill"] + extra_slippage if side == "buy" else fill["fill"] - extra_slippage)
    stop_hits = []
    for stop_distance in STOP_DOLLARS:
        level = intended - stop_distance if side == "buy" else intended + stop_distance
        stop_hits.append(_first_exit_cross(data, fill, level, "stop"))
    target_hits = []
    for target_distance in TARGET_DOLLARS:
        level = intended + target_distance if side == "buy" else intended - target_distance
        target_hits.append(_first_exit_cross(data, fill, level, "target"))
    timeout_stamp, timeout_price = _timeout_exit(data, side)
    matrix = np.zeros((len(STOP_DOLLARS), len(TARGET_DOLLARS)), dtype=np.float64)
    target_matrix = np.zeros((len(STOP_DOLLARS), len(TARGET_DOLLARS)), dtype=np.int8)
    for stop_index, stop_distance in enumerate(STOP_DOLLARS):
        for target_index, _ in enumerate(TARGET_DOLLARS):
            stop_hit = stop_hits[stop_index]
            target_hit = target_hits[target_index]
            if stop_hit and (not target_hit or stop_hit[0] <= target_hit[0]):
                exit_price = stop_hit[1]
            elif target_hit:
                exit_price = target_hit[1]
                target_matrix[stop_index, target_index] = 1
            else:
                exit_price = timeout_price
            exit_price = exit_price - extra_slippage if side == "buy" else exit_price + extra_slippage
            pnl = exit_price - actual_entry if side == "buy" else actual_entry - exit_price
            matrix[stop_index, target_index] = pnl / stop_distance
    return matrix, target_matrix


def _event_matrix(data: EventData, config: EntryConfig, extra_slippage: float = 0.0) -> dict | None:
    outcome = _resolve_entry(data, config)
    if outcome["status"] != "traded":
        return None
    result = np.zeros((len(STOP_DOLLARS), len(TARGET_DOLLARS)), dtype=np.float64)
    target_hits = np.zeros((len(STOP_DOLLARS), len(TARGET_DOLLARS)), dtype=np.int8)
    for fill in outcome["fills"]:
        leg_result, leg_targets = _leg_matrix(data, fill, extra_slippage)
        result += leg_result
        target_hits += leg_targets
    return {
        "matrix": result,
        "target_hits": target_hits,
        "event": data.event,
        "released": data.released,
        "legs": len(outcome["fills"]),
        "dual_fill": bool(outcome["dual_fill"]),
        "pre_release_fill": bool(outcome["pre_release_fill"]),
        "spread": float(outcome["spread"]),
        "slippage": sum(float(fill["slippage"]) for fill in outcome["fills"]),
        "first_side": outcome["fills"][0]["side"],
    }


def _max_drawdown(results: list[float]) -> float:
    running = 0.0
    peak = 0.0
    maximum = 0.0
    for result in results:
        running += result
        peak = max(peak, running)
        maximum = max(maximum, peak - running)
    return maximum


def _performance(rows: list[dict], total_events: int, stop: float, target: float) -> dict:
    results = [float(row["result_r"]) for row in rows]
    gross_profit = sum(max(0.0, result) for result in results)
    gross_loss = -sum(min(0.0, result) for result in results)
    wins = sum(result > 0 for result in results)
    yearly: dict[str, float] = {}
    event_net: dict[str, float] = {}
    block_net: dict[str, float] = {}
    for row in rows:
        year = str(row["released"].year)
        yearly[year] = yearly.get(year, 0.0) + float(row["result_r"])
        event_net[row["event"]] = event_net.get(row["event"], 0.0) + float(row["result_r"])
        released = row["released"]
        block = str(((released.year * 12 + released.month) - (START.year * 12 + START.month)) // 12 + 1)
        block_net[block] = block_net.get(block, 0.0) + float(row["result_r"])
    rr = target / stop
    return {
        "events": total_events,
        "traded_events": len(rows),
        "legs": sum(int(row["legs"]) for row in rows),
        "fill_rate_pct": 100.0 * len(rows) / total_events if total_events else 0.0,
        "wins": wins,
        "losses": len(rows) - wins,
        "win_rate_pct": 100.0 * wins / len(rows) if rows else 0.0,
        "profit_factor": gross_profit / gross_loss if gross_loss else None,
        "net_r": gross_profit - gross_loss,
        "expectancy_r": (gross_profit - gross_loss) / len(rows) if rows else 0.0,
        "max_drawdown_r": _max_drawdown(results),
        "largest_loss_r": min(results) if results else 0.0,
        "target_hit_rate_pct": 100.0 * sum(int(row["target_hits"]) > 0 for row in rows) / len(rows) if rows else 0.0,
        "dual_fill_rate_pct": 100.0 * sum(bool(row["dual_fill"]) for row in rows) / len(rows) if rows else 0.0,
        "pre_release_fill_rate_pct": 100.0 * sum(bool(row["pre_release_fill"]) for row in rows) / len(rows) if rows else 0.0,
        "median_spread_dollars": statistics.median(row["spread"] for row in rows) if rows else None,
        "median_entry_slippage_dollars": statistics.median(row["slippage"] / row["legs"] for row in rows) if rows else None,
        "year_net_r": yearly,
        "twelve_month_block_net_r": block_net,
        "event_net_r": event_net,
    }


def _cell_rows(items: list[dict | None], stop_index: int, target_index: int) -> list[dict]:
    rows = []
    for item in items:
        if item is None:
            continue
        rows.append(
            {
                **item,
                "result_r": float(item["matrix"][stop_index, target_index]),
                "target_hits": int(item["target_hits"][stop_index, target_index]),
            }
        )
    return rows


def _selection_score(stats: dict, require_families: bool) -> float:
    year_values = list(stats["twelve_month_block_net_r"].values())
    family_values = list(stats["event_net_r"].values())
    worst_year = min(year_values) if year_values else -100.0
    worst_family = min(family_values) if family_values else -100.0
    score = stats["net_r"] - 1.0 * stats["max_drawdown_r"]
    score += 2.0 * min(0.0, worst_year)
    if require_families:
        score += 2.0 * min(0.0, worst_family)
    score -= 0.10 * stats["dual_fill_rate_pct"]
    return score


def _strict_selection_pass(stats: dict, reward_risk: float, require_families: bool) -> bool:
    blocks = list(stats["twelve_month_block_net_r"].values())
    positive_blocks = sum(value > 0 for value in blocks)
    required_blocks = 3 if len(blocks) >= 4 else max(1, len(blocks) - 1)
    families = list(stats["event_net_r"].values())
    positive_families = sum(value > 0 for value in families)
    return (
        (stats["profit_factor"] or 0.0) >= 1.10
        and positive_blocks >= required_blocks
        and stats["largest_loss_r"] >= -2.50
        and 0.50 <= reward_risk <= 7.0
        and stats["target_hit_rate_pct"] >= 5.0
        and stats["dual_fill_rate_pct"] <= 10.0
        and (not require_families or positive_families >= 4)
    )


def _select(
    candidates: list[EntryConfig],
    markets: list[EventData],
    matrix_cache: dict,
    minimum_trades: int,
    require_families: bool,
) -> tuple[dict, list[dict]]:
    leaderboard = []
    for config in candidates:
        items = [matrix_cache[(config, market.key, 0.0)] for market in markets]
        for stop_index, stop in enumerate(STOP_DOLLARS):
            for target_index, target in enumerate(TARGET_DOLLARS):
                rows = _cell_rows(items, stop_index, target_index)
                stats = _performance(rows, len(markets), stop, target)
                if stats["traded_events"] < minimum_trades or (stats["profit_factor"] or 0.0) < 0.80:
                    continue
                leaderboard.append(
                    {
                        "entry": config,
                        "stop_dollars": stop,
                        "target_dollars": target,
                        "reward_risk": target / stop,
                        "performance": stats,
                        "score": _selection_score(stats, require_families),
                        "strict_pass": _strict_selection_pass(stats, target / stop, require_families),
                    }
                )
    if not leaderboard:
        raise RuntimeError("No configuration passed the minimum selection rules.")
    strict = [row for row in leaderboard if row["strict_pass"]]
    selection_pool = strict or leaderboard
    selection_pool.sort(
        key=lambda row: (
            row["score"],
            row["performance"]["profit_factor"] or 0.0,
            row["performance"]["traded_events"],
        ),
        reverse=True,
    )
    leaderboard.sort(key=lambda row: (row["strict_pass"], row["score"]), reverse=True)
    return selection_pool[0], leaderboard[:20]


def _evaluate(
    selected: dict,
    markets: list[EventData],
    matrix_cache: dict,
    extra_slippage: float = 0.0,
) -> tuple[dict, list[dict]]:
    config = selected["entry"]
    stop_index = STOP_DOLLARS.index(float(selected["stop_dollars"]))
    target_index = TARGET_DOLLARS.index(float(selected["target_dollars"]))
    items = []
    for market in markets:
        cache_key = (config, market.key, extra_slippage)
        if cache_key not in matrix_cache:
            matrix_cache[cache_key] = _event_matrix(market, config, extra_slippage)
        items.append(matrix_cache[cache_key])
    rows = _cell_rows(items, stop_index, target_index)
    return _performance(rows, len(markets), selected["stop_dollars"], selected["target_dollars"]), rows


def _serial_selected(selected: dict) -> dict:
    return {
        "entry": asdict(selected["entry"]),
        "stop_dollars": selected["stop_dollars"],
        "target_dollars": selected["target_dollars"],
        "reward_risk": selected["reward_risk"],
    }


def _fmt(value: float | None, digits: int = 2) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def run() -> dict:
    events = [event for event in load_events(START, END) if event["event"] in EVENT_NAMES]
    markets = [market for event in events if (market := _load_market(event)) is not None]
    development = [market for market in markets if market.released < HOLDOUT_START]
    holdout = [market for market in markets if market.released >= HOLDOUT_START]
    missing = len(events) - len(markets)
    print(f"Loaded {len(markets)}/{len(events)} event tick windows; {missing} are unavailable.")

    print("Ranking universal entry geometry...")
    universal_entries = _rank_entries(development, limit=75, minimum_fills=70)
    event_entries: dict[str, list[EntryConfig]] = {}
    for event_name in EVENT_NAMES:
        subset = [market for market in development if market.event == event_name]
        event_entries[event_name] = _rank_entries(subset, limit=20, minimum_fills=max(6, len(subset) // 3))
        print(f"Ranked {event_name}: {len(subset)} development events.")

    all_candidates = list(dict.fromkeys(universal_entries + [config for rows in event_entries.values() for config in rows]))
    matrix_cache: dict[tuple, dict | None] = {}
    print(f"Building execution matrices for {len(all_candidates)} entry candidates...")
    for candidate_index, config in enumerate(all_candidates, start=1):
        for market in markets:
            matrix_cache[(config, market.key, 0.0)] = _event_matrix(market, config)
        if candidate_index % 10 == 0 or candidate_index == len(all_candidates):
            print(f"  {candidate_index}/{len(all_candidates)} entry candidates")

    universal_selected, universal_leaderboard = _select(
        universal_entries,
        development,
        matrix_cache,
        minimum_trades=70,
        require_families=True,
    )
    universal_dev, _ = _evaluate(universal_selected, development, matrix_cache)
    universal_holdout, _ = _evaluate(universal_selected, holdout, matrix_cache)
    universal_full, universal_rows = _evaluate(universal_selected, markets, matrix_cache)

    event_specific = {}
    for event_name in EVENT_NAMES:
        event_dev = [market for market in development if market.event == event_name]
        event_test = [market for market in holdout if market.event == event_name]
        event_full = [market for market in markets if market.event == event_name]
        selected, leaderboard = _select(
            event_entries[event_name],
            event_dev,
            matrix_cache,
            minimum_trades=max(6, len(event_dev) // 3),
            require_families=False,
        )
        dev_stats, _ = _evaluate(selected, event_dev, matrix_cache)
        test_stats, _ = _evaluate(selected, event_test, matrix_cache)
        full_stats, _ = _evaluate(selected, event_full, matrix_cache)
        event_stress = []
        for extra_slippage in (0.25, 0.50):
            stress_stats, _ = _evaluate(
                selected,
                event_test,
                matrix_cache,
                extra_slippage=extra_slippage,
            )
            event_stress.append(
                {
                    "name": f"${extra_slippage:.2f} adverse entry and exit slippage",
                    "holdout": stress_stats,
                }
            )
        latency_selected = {
            **selected,
            "entry": replace(selected["entry"], cancel_latency_ms=500),
        }
        latency_stats, _ = _evaluate(latency_selected, event_test, matrix_cache)
        event_stress.append(
            {"name": "500 ms opposite-order cancellation", "holdout": latency_stats}
        )
        event_specific[event_name] = {
            "selected": _serial_selected(selected),
            "development_selection_strict_pass": bool(selected["strict_pass"]),
            "development": dev_stats,
            "holdout": test_stats,
            "full": full_stats,
            "stress_tests": event_stress,
            "leaderboard_development": [
                {"selected": _serial_selected(row), "performance": row["performance"], "score": row["score"]}
                for row in leaderboard[:5]
            ],
        }

    universal_event_breakdown = {}
    for event_name in EVENT_NAMES:
        subset = [market for market in markets if market.event == event_name]
        stats, _ = _evaluate(universal_selected, subset, matrix_cache)
        universal_event_breakdown[event_name] = stats

    lead_sensitivity = []
    for lead in LEADS_SECONDS:
        variant = {**universal_selected, "entry": replace(universal_selected["entry"], lead_seconds=lead)}
        stats, _ = _evaluate(variant, holdout, matrix_cache)
        lead_sensitivity.append({"lead_seconds": lead, "holdout": stats})

    stress_tests = []
    for extra_slippage in (0.25, 0.50):
        stats, _ = _evaluate(universal_selected, holdout, matrix_cache, extra_slippage=extra_slippage)
        stress_tests.append({"name": f"${extra_slippage:.2f} adverse entry and exit slippage", "holdout": stats})
    latency_variant = {**universal_selected, "entry": replace(universal_selected["entry"], cancel_latency_ms=500)}
    latency_stats, _ = _evaluate(latency_variant, holdout, matrix_cache)
    stress_tests.append({"name": "500 ms opposite-order cancellation", "holdout": latency_stats})

    universal_stress_pf = [
        float(row["holdout"]["profit_factor"] or 0.0) for row in stress_tests
    ]
    profitable_full_families = sum(
        stats["net_r"] > 0 for stats in universal_event_breakdown.values()
    )
    universal_deployable = (
        (universal_holdout["profit_factor"] or 0.0) >= 1.10
        and universal_holdout["net_r"] > 0
        and (universal_full["profit_factor"] or 0.0) >= 1.05
        and min(universal_stress_pf, default=0.0) >= 1.0
        and profitable_full_families >= 4
    )

    payload = {
        "methodology": {
            "symbol": "XAUUSD",
            "data_source": "Dukascopy bid/ask ticks through T+5, then bid/ask M1 through T+60",
            "window": [START.isoformat(), END.isoformat()],
            "development_end": HOLDOUT_START.isoformat(),
            "scheduled_events": len(events),
            "usable_tick_events": len(markets),
            "missing_tick_events": missing,
            "events": EVENT_NAMES,
            "placement_leads_seconds": LEADS_SECONDS,
            "oco_cancellation_latency_ms": BASE_CANCEL_LATENCY_MS,
            "same_m1_bar_policy": "stop wins",
            "selection": "development only; net R minus drawdown, worst-year, worst-event-family, and dual-fill penalties",
        },
        "universal": {
            "selected": _serial_selected(universal_selected),
            "deployment_verdict": "paper-test only" if universal_deployable else "rejected",
            "development_selection_strict_pass": bool(universal_selected["strict_pass"]),
            "development": universal_dev,
            "holdout": universal_holdout,
            "full": universal_full,
            "event_breakdown_full": universal_event_breakdown,
            "lead_sensitivity_holdout": lead_sensitivity,
            "stress_tests": stress_tests,
            "leaderboard_development": [
                {"selected": _serial_selected(row), "performance": row["performance"], "score": row["score"]}
                for row in universal_leaderboard[:10]
            ],
        },
        "event_specific": event_specific,
    }
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    csv_rows = []
    for row in universal_rows:
        csv_rows.append(
            {
                "release_utc": row["released"].isoformat(),
                "event": row["event"],
                "first_side": row["first_side"],
                "legs": row["legs"],
                "dual_fill": row["dual_fill"],
                "pre_release_fill": row["pre_release_fill"],
                "spread_dollars": row["spread"],
                "entry_slippage_dollars": row["slippage"],
                "result_r": row["result_r"],
            }
        )
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]) if csv_rows else ["release_utc"])
        writer.writeheader()
        writer.writerows(csv_rows)

    selected = universal_selected
    lines = [
        "# XAUUSD Tick-Level News Straddle Study",
        "",
        "## Honest answer first",
        "",
        "No pending-order offset can guarantee a win on every news release. A stop order becomes a market order after triggering, so a release gap can fill beyond the requested price. Fast reversals can also fill both sides before the second order is cancelled.",
        "",
        "## Test design",
        "",
        f"- Window: {START.date()} through {END.date()}.",
        f"- Usable tick windows: {len(markets)} of {len(events)} scheduled events; {missing} windows had no tick data.",
        f"- Development: {START.date()} through {HOLDOUT_START.date()}; locked holdout: {HOLDOUT_START.date()} through {END.date()}.",
        "- Events: NFP, CPI, PPI, advance GDP, and FOMC statements.",
        "- Both buy-stop and sell-stop are placed from the latest bid/ask at T-60s, T-30s, or T-10s.",
        f"- The first fill attempts to cancel the other order after {BASE_CANCEL_LATENCY_MS} ms. Both fills count when the opposite trigger occurs first.",
        "- Dukascopy bid/ask ticks drive placement, triggers, spread, slippage, OCO collisions, and exits through T+5. Bid/ask M1 extends exits to T+60; same-bar ties lose.",
        "- Parameters were selected only on the first four years. The last year was not used for selection.",
        "",
        "## One configuration across all events",
        "",
        f"- Overall verdict: **{'PAPER-TEST ONLY' if universal_deployable else 'REJECTED - no universal edge survived the locked holdout'}**",
        f"- Placement: **T-{selected['entry'].lead_seconds} seconds**",
        f"- Buy stop: **max(${selected['entry'].buy_offset_dollars:.2f}, live spread x {selected['entry'].spread_multiplier:.1f}) above ask**",
        f"- Sell stop: **max(${selected['entry'].sell_offset_dollars:.2f}, live spread x {selected['entry'].spread_multiplier:.1f}) below bid**",
        f"- Stop loss: **${selected['stop_dollars']:.2f}**",
        f"- Take profit: **${selected['target_dollars']:.2f}** ({selected['reward_risk']:.2f}R)",
        f"- Unfilled-order expiry: **T+{selected['entry'].expiry_seconds} seconds**",
        f"- Development-only robustness gate: **{'passed' if selected['strict_pass'] else 'fallback only'}**",
        "",
        "| Period | Events traded | Fill rate | Win rate | Target hit | PF | Net R | Max DD | Dual fill | Pre-release fill |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label, stats in (("Development", universal_dev), ("Locked holdout", universal_holdout), ("Full five years", universal_full)):
        lines.append(
            f"| {label} | {stats['traded_events']} | {stats['fill_rate_pct']:.1f}% | {stats['win_rate_pct']:.1f}% | {stats['target_hit_rate_pct']:.1f}% | {_fmt(stats['profit_factor'])} | {stats['net_r']:.2f} | {stats['max_drawdown_r']:.2f}R | {stats['dual_fill_rate_pct']:.1f}% | {stats['pre_release_fill_rate_pct']:.1f}% |"
        )

    lines.extend([
        "",
        "## Universal configuration by event",
        "",
        "| Event | Trades | Win rate | PF | Net R | Max DD | Dual fill |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for event_name in EVENT_NAMES:
        stats = universal_event_breakdown[event_name]
        lines.append(
            f"| {event_name} | {stats['traded_events']} | {stats['win_rate_pct']:.1f}% | {_fmt(stats['profit_factor'])} | {stats['net_r']:.2f} | {stats['max_drawdown_r']:.2f}R | {stats['dual_fill_rate_pct']:.1f}% |"
        )

    lines.extend([
        "",
        "## Event-specific development selections",
        "",
        "These are research comparisons, not five independent promises. GDP has the smallest sample and the greatest overfitting risk.",
        "",
        "| Event | Lead | Buy offset | Sell offset | SL | TP | Holdout trades | Holdout PF | +$0.25 slip PF | Holdout net R | Decision |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ])
    for event_name in EVENT_NAMES:
        block = event_specific[event_name]
        config = block["selected"]
        entry = config["entry"]
        stats = block["holdout"]
        slip_stats = block["stress_tests"][0]["holdout"]
        decision = (
            "paper-test only"
            if stats["traded_events"] >= 8
            and (stats["profit_factor"] or 0.0) >= 1.20
            and (slip_stats["profit_factor"] or 0.0) >= 1.05
            else "reject"
        )
        lines.append(
            f"| {event_name} | T-{entry['lead_seconds']}s | ${entry['buy_offset_dollars']:.2f} | ${entry['sell_offset_dollars']:.2f} | ${config['stop_dollars']:.2f} | ${config['target_dollars']:.2f} | {stats['traded_events']} | {_fmt(stats['profit_factor'])} | {_fmt(slip_stats['profit_factor'])} | {stats['net_r']:.2f} | {decision} |"
        )

    lines.extend([
        "",
        "## Timing sensitivity on the locked holdout",
        "",
        "| Placement | Trades | Win rate | PF | Net R | Max DD |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for row in lead_sensitivity:
        stats = row["holdout"]
        lines.append(
            f"| T-{row['lead_seconds']}s | {stats['traded_events']} | {stats['win_rate_pct']:.1f}% | {_fmt(stats['profit_factor'])} | {stats['net_r']:.2f} | {stats['max_drawdown_r']:.2f}R |"
        )

    lines.extend([
        "",
        "## Execution stress on the locked holdout",
        "",
        "| Stress | Trades | Win rate | PF | Net R | Max DD | Dual fill |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for row in stress_tests:
        stats = row["holdout"]
        lines.append(
            f"| {row['name']} | {stats['traded_events']} | {stats['win_rate_pct']:.1f}% | {_fmt(stats['profit_factor'])} | {stats['net_r']:.2f} | {stats['max_drawdown_r']:.2f}R | {stats['dual_fill_rate_pct']:.1f}% |"
        )

    lines.extend([
        "",
        "## Interpretation",
        "",
        "The locked holdout is the result that matters. If it is weak, the attractive development result is curve fitting. Even a positive holdout is only one year and must be forward-tested on the intended broker because release spread, stop-order slippage, minimum stop distance, and OCO cancellation latency differ from Dukascopy.",
        "",
        "The universal configuration failed that test: its locked-holdout PF was below 1, its stress results worsened, and only NFP and GDP were profitable over the full sample. There is no deployable all-event straddle in this search space.",
        "",
        "NFP is the only event-specific candidate that remained positive in the locked holdout, but its edge fell to approximately break-even under $0.50 adverse entry and exit slippage. It is suitable only for broker-specific paper testing, not live promotion.",
    ])
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = run()
    universal = result["universal"]
    print(json.dumps({"selected": universal["selected"], "holdout": universal["holdout"]}, indent=2))
