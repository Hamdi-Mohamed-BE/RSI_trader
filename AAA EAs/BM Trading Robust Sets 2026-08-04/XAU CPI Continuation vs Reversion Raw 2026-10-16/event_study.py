"""Frozen CPI event-price study, not a trade or executable-return backtest.

Only local, already-exported historical prices are read. Each release uses one
identified Exness Gold archive; no other broker feed is blended into a synthetic
event window. The initial one-minute jump is excluded from continuation moves.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

import numpy as np

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
ARCHIVE = BASE / "New Ideas 01 Price Event Clock Raw 2026-10-13"
HORIZONS = (5, 15, 30)
PRICE_FIELDS = ("open", "high", "low", "close")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def iso(epoch: int) -> str:
    return datetime.fromtimestamp(int(epoch), timezone.utc).isoformat()


def epoch(date: str) -> int:
    return int(datetime.fromisoformat(date).replace(tzinfo=timezone.utc).timestamp())


def load_source(path: Path, label: str) -> dict:
    assert path.suffix == ".npz", "This Gold study accepts its verified local NPZ price archive only"
    with np.load(path, allow_pickle=False) as saved:
        rates = saved["rates"]
        times = np.asarray(rates["time"], dtype=np.int64)
        prices = np.column_stack([rates[k] for k in PRICE_FIELDS]).astype(float)
    assert len(times) and np.all(np.isfinite(prices)), f"Invalid historical prices: {path}"
    order = np.argsort(times, kind="stable")
    times, prices = times[order], prices[order]
    duplicate = np.flatnonzero(np.diff(times) == 0)
    assert all(np.array_equal(prices[i], prices[i + 1]) for i in duplicate), f"Conflicting duplicate candles: {path}"
    keep = np.r_[True, np.diff(times) != 0]
    times, prices = times[keep], prices[keep]
    assert np.all(np.diff(times) > 0) and np.all(times % 60 == 0)
    assert np.all(prices[:, 1] >= prices[:, [0, 2, 3]].max(axis=1))
    assert np.all(prices[:, 2] <= prices[:, [0, 1, 3]].min(axis=1))
    metadata = dict(label=label, path=str(path), sha256=sha(path), rows=len(times),
                    first_utc=iso(times[0]), last_utc=iso(times[-1]),
                    duplicate_identical_rows_removed=len(duplicate), time_basis="UTC")
    return dict(times=times, prices=prices, metadata=metadata)


def window(source: dict, wanted: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    times = source["times"]
    positions = np.searchsorted(times, wanted)
    valid = positions < len(times)
    valid[valid] &= times[positions[valid]] == wanted[valid]
    values = np.full((len(wanted), 4), np.nan)
    values[valid] = source["prices"][positions[valid]]
    return valid, values


def overlap(a: dict, b: dict, wanted: np.ndarray) -> dict:
    av, ap = window(a, wanted)
    bv, bp = window(b, wanted)
    both = av & bv
    differences = np.abs(ap[both] - bp[both])
    return dict(source_a=a["metadata"]["label"], source_b=b["metadata"]["label"],
                requested_rows=len(wanted), overlap_rows=int(both.sum()),
                exactly_equal_ohlc_rows=int(np.all(differences == 0, axis=1).sum()),
                equal_within_one_tick_rows=int(np.all(differences <= .00100001, axis=1).sum()),
                maximum_absolute_ohlc_difference=float(differences.max()) if len(differences) else None,
                overlap_start_utc=iso(wanted[both][0]) if both.any() else None,
                overlap_end_utc=iso(wanted[both][-1]) if both.any() else None,
                action="Comparison only; neither archive is overwritten or blended")


def choose_source(event_epoch: int, sources: dict) -> tuple[dict | None, str, list[dict]]:
    source = sources.get("Gold-recent")
    if source is None:
        return None, "Missing verified recent Exness XAUUSD archive", []
    if event_epoch < int(source["times"][0]) or event_epoch > int(source["times"][-1]):
        return source, "Scheduled CPI outside independent Gold archive coverage; no older/different-broker prices are substituted", []
    wanted = event_epoch + np.arange(-15, 30, dtype=np.int64) * 60
    complete = bool(window(source, wanted)[0].all())
    return source, ("Single verified recent Exness XAUUSD archive; " +
                    ("complete event window" if complete else
                     "incomplete event window retained as missing, no interpolation")), []


def describe_event(event: dict, sources: dict) -> dict:
    t = int(event["epoch"])
    source, choice, comparisons = choose_source(t, sources)
    row = dict(event_epoch=t, release_utc=iso(t), release_ny=event.get("release_ny"),
               month=iso(t)[:7], official_source=event.get("source"), source_choice=choice,
               source_refs=[source["metadata"]] if source is not None else [],
               overlap_comparisons=comparisons, fair=None, atr=None, first_close=None,
               first_open=None, first_high=None, first_low=None, first_impulse_points=None,
               spike=0, common_eligible=False, common_ineligibility_reason=None, horizons={})
    if source is None:
        row.update(status="missing_prices", common_ineligibility_reason="No local source")
        return row
    wanted = t + np.arange(-15, 30, dtype=np.int64) * 60
    valid, bars = window(source, wanted)
    row["exact_candles_available"] = int(valid.sum())
    row["expected_candles"] = len(wanted)
    row["missing_candle_utc"] = [iso(x) for x in wanted[~valid]]
    # Fifteen pre-release bars supply fourteen strictly pre-release true ranges.
    row["pre_release_15_candles_complete"] = bool(valid[:15].all())
    row["fixed_first_release_candle_available"] = bool(valid[15])
    if valid[14]:
        row["fair"] = float(bars[14, 3])
    if valid[:15].all():
        prior_close = bars[:14, 3]
        tr = np.maximum.reduce([bars[1:15, 1] - bars[1:15, 2],
                                np.abs(bars[1:15, 1] - prior_close),
                                np.abs(bars[1:15, 2] - prior_close)])
        row["atr"] = float(tr.mean())
    if valid[15]:
        row.update(first_open=float(bars[15, 0]), first_high=float(bars[15, 1]),
                   first_low=float(bars[15, 2]), first_close=float(bars[15, 3]))
    if row["fair"] is None or row["first_close"] is None:
        row.update(status="missing_anchor_or_first_candle",
                   common_ineligibility_reason="Exact pre-release close or fixed first release candle missing")
    else:
        move = row["first_close"] - row["fair"]
        row["first_impulse_points"] = move
        row["spike"] = int(np.sign(move))
        row["status"] = "observed" if move else "zero_initial_impulse"
        if not move:
            row["common_ineligibility_reason"] = "Zero close-to-anchor initial impulse"
        elif row["atr"] is None or row["atr"] <= 0:
            row["common_ineligibility_reason"] = "Complete positive pre-release ATR unavailable"
        else:
            candle_range = row["first_high"] - row["first_low"]
            extreme_distance = (row["first_high"] - row["first_close"] if move > 0
                                else row["first_close"] - row["first_low"])
            row["initial_impulse_atr"] = abs(move) / row["atr"]
            row["directional_outer_quarter_close"] = bool(candle_range > 0 and extreme_distance <= .25 * candle_range + 1e-10)
            row["common_eligible"] = bool(abs(move) + 1e-10 >= row["atr"] and row["directional_outer_quarter_close"])
            row["common_ineligibility_reason"] = (None if row["common_eligible"] else
                                                   "Fixed initial candle did not meet both >=1 ATR displacement and directional outer-quarter close")
    for horizon in HORIZONS:
        # +5 means completed release+4m candle, i.e. the price at five minutes
        # after the release. Requiring every post-release minute prevents gaps.
        complete = bool(valid[15:15 + horizon].all())
        endpoint = float(bars[15 + horizon - 1, 3]) if complete else None
        eligible = bool(complete and row["spike"] and row["first_close"] is not None)
        signed = row["spike"] * (endpoint - row["first_close"]) if eligible else None
        row["horizons"][str(horizon)] = dict(
            minutes_after_release=horizon, endpoint_bar_utc=iso(t + (horizon - 1) * 60),
            observation_time_utc=iso(t + horizon * 60), contiguous_post_release_candles=complete,
            endpoint_close=endpoint, nonzero_impulse_sample_eligible=eligible,
            raw_increment_points=(endpoint - row["first_close"]) if eligible else None,
            signed_continuation_increment_points=signed,
            continuation=signed > 0 if eligible else None,
            reversion=signed < 0 if eligible else None,
            flat=signed == 0 if eligible else None,
            note="Increment begins at fixed first M1 close: initial news jump is excluded")
    return row


def wilson(successes: int, n: int) -> list[float] | None:
    if not n:
        return None
    z = 1.959963984540054
    p = successes / n
    center = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [float(100 * (center - half)), float(100 * (center + half))]


def summarize(rows: list[dict], start: str, end: str) -> dict:
    selected = [r for r in rows if epoch(start) <= r["event_epoch"] < epoch(end)]
    result = dict(requested_start=start, requested_end_exclusive=end, scheduled_cpi_releases=len(selected),
                  observed_initial_impulse_events=sum(r["spike"] != 0 for r in selected),
                  common_impulse_eligible_events=sum(r["common_eligible"] for r in selected),
                  scheduled_events_without_exact_anchor_or_first_candle=sum(r["fair"] is None or r["first_close"] is None for r in selected),
                  first_scheduled_utc=selected[0]["release_utc"] if selected else None,
                  last_scheduled_utc=selected[-1]["release_utc"] if selected else None, cohorts={})
    for cohort in ("all_nonzero_first_minute_impulses", "significant_common_impulse"):
        result["cohorts"][cohort] = {}
        for horizon in HORIZONS:
            observations = [r for r in selected if r["horizons"].get(str(horizon), {}).get("nonzero_impulse_sample_eligible")
                            and (cohort == "all_nonzero_first_minute_impulses" or r["common_eligible"])]
            values = np.asarray([r["horizons"][str(horizon)]["signed_continuation_increment_points"] for r in observations], dtype=float)
            n = len(values)
            continuation = int((values > 0).sum())
            result["cohorts"][cohort][str(horizon)] = dict(
                observations=n, continuation_events=continuation, reversion_events=int((values < 0).sum()),
                flat_events=int((values == 0).sum()),
                continuation_pct=float(100 * continuation / n) if n else None,
                continuation_wilson_95_pct=wilson(continuation, n),
                mean_signed_increment_points=float(values.mean()) if n else None,
                median_signed_increment_points=float(np.median(values)) if n else None,
                first_observed_release_utc=observations[0]["release_utc"] if n else None,
                last_observed_release_utc=observations[-1]["release_utc"] if n else None,
                unit="Gold price change in USD per troy ounce, not MT5 points, account returns or executed P&L")
    return result


def main() -> dict:
    config_path, calendar_path = ROOT / "config.json", ROOT / "calendar.json"
    assert calendar_path.exists(), "Run the study's calendar preparation first; no dates are inferred"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    calendar = json.loads(calendar_path.read_text(encoding="utf-8"))
    events = sorted([e for e in calendar["events"] if e["kind"] == "CPI"
                     and epoch(config["start"]) <= int(e["epoch"]) < epoch(config["end_exclusive"])], key=lambda e: e["epoch"])
    assert events and len({e["epoch"] for e in events}) == len(events)
    archive_metadata = json.loads((ARCHIVE / "DATA.json").read_text(encoding="utf-8"))
    assert config["symbol"] == "XAUUSD"
    record = archive_metadata["files"]["XAUUSD"]
    path = ARCHIVE / "XAUUSD-M1.npz"
    assert path.exists(), f"Missing verified Gold archive: {path}"
    gold = load_source(path, "Gold-recent")
    assert gold["metadata"]["sha256"] == record["sha256"], f"Archive hash changed: {path}"
    assert gold["metadata"]["rows"] == record["rows"]
    assert gold["metadata"]["first_utc"] == record["first"] and gold["metadata"]["last_utc"] == record["last"]
    gold["metadata"].update(server=archive_metadata["server"], broker=archive_metadata["broker"],
                            retrieved_utc=archive_metadata["retrieved_utc"], specification=record["specification"],
                            source_metadata_path=str(ARCHIVE / "DATA.json"), source_metadata_sha256=sha(ARCHIVE / "DATA.json"))
    sources = {"Gold-recent": gold}
    rows = [describe_event(e, sources) for e in events]
    summaries = dict(all_history=summarize(rows, config["start"], config["end_exclusive"]),
                     retrospective_last_two_years=summarize(rows, config["oos_start"], config["end_exclusive"]),
                     last_year=summarize(rows, "2025-10-16", config["end_exclusive"]),
                     last_three_months=summarize(rows, "2026-07-16", config["end_exclusive"]))
    summaries["yearly"] = {str(y): summarize(rows, f"{y}-01-01", min(f"{y+1}-01-01", config["end_exclusive"]))
                           for y in sorted({datetime.fromtimestamp(e["epoch"], timezone.utc).year for e in events})}
    result = dict(study="CPI post-initial-reaction Gold descriptive event study", generated_utc=datetime.now(timezone.utc).isoformat(),
                  config_sha256=sha(config_path), calendar_sha256=sha(calendar_path), source_sha256=sha(Path(__file__)),
                  parameters_optimized=0, sources=[s["metadata"] for s in sources.values()],
                  independent_archive_coverage=dict(first_utc=gold["metadata"]["first_utc"], last_utc=gold["metadata"]["last_utc"]),
                  descriptive_horizon_scope="5/15/30 minutes AFTER release, not the EA holding period. Approved native holding limits are read separately from config.json.",
                  approved_native_holding_limits_minutes_from_fill=dict(
                      continuation=config["continuation"]["maximum_hold_minutes_from_fill"],
                      reversion=config["reversion"]["maximum_hold_minutes_from_fill"],
                      anchor_diagnostic=config["reversion"]["maximum_hold_minutes_from_fill"]),
                  feed_comparison_scope="Independent OHLC is Exness-MT5Trial15 Pro. Native isolated replay uses Exness-MT5Trial16; separate server/feed data can differ. This is not exact native-tick-fill verification.",
                  source_policy="One verified recent Exness Trial15 XAUUSD NPZ archive only. Requested older/newer CPI events outside that archive remain missing. No MEXAtlantic feed, broker substitution, inferred quotes or interpolation.",
                  definitions=dict(fair="Exact M1 bid close immediately before release", first_close="Fixed first release-aligned M1 bid close",
                                   atr="Mean 14 pre-release M1 true ranges from 15 consecutive pre-release candles",
                                   signed_increment="sign(first_close - fair) * (horizon_close - first_close)",
                                   horizons="Completed M1 bar at release+(horizon-1) minutes; initial jump excluded",
                                   common_impulse="abs(first_close-fair)>=pre-release ATR and close in directional outer25% of fixed first-minute range"),
                  limitations=["Descriptive M1 bid-price increments, not executable trading returns, not a 70% win-rate claim.",
                               "No spread, slippage, fees, stops, targets or trade entry logic are applied here; native strategy results are separate.",
                               "The last-two-year evaluation is retrospective, not untouched data.",
                               "Missing newest CPI price windows remain missing; scheduled events and observed events are reported separately.",
                               "Direction is inferred only from the fixed first-minute price reaction, not from actual-minus-consensus surprises.",
                               "The independent export covers only 2025-08-01 through 2026-10-13 00:02 UTC, not the full requested 2020–2026 or two-year window.",
                               "Exness-MT5Trial15 independent OHLC versus Exness-MT5Trial16 native replay is a separate-server/feed comparison, not native fill or exact feature verification.",
                               "Descriptive +5/+15/+30 minute moves do not change or simulate the approved native holding limits recorded from config.json."],
                  summaries=summaries, events=rows, live_changes=False)
    (ROOT / "EVENT-STUDY.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(dict(scheduled=len(rows), sources=len(sources), newest_scheduled=rows[-1]["release_utc"],
                          observed_nonzero=sum(r["spike"] != 0 for r in rows),
                          missing_initial=sum(r["fair"] is None or r["first_close"] is None for r in rows),
                          output=str(ROOT / "EVENT-STUDY.json")), indent=2), flush=True)
    return result


if __name__ == "__main__":
    main()

