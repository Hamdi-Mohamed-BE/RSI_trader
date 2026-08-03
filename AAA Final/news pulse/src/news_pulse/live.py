from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import logging
from pathlib import Path
import time

from .config import Config, ROOT
from .core import entry_buffer, oco_comment
from .mt5_gateway import MT5Gateway
from .prediction import PredictionService
from .state import StateStore, signal_hash


LOG = logging.getLogger("news_pulse.live")


def _calendar_key(row: dict) -> tuple[str, datetime]:
    release = row["release"].replace(second=0, microsecond=0)
    return str(row["event"]).upper(), release


def _live_events(config: Config) -> list[dict]:
    """Load the current broker-week calendar without coupling execution to it."""
    provider_path = config.ai_news_root / "calendar_provider.py"
    if not provider_path.exists():
        raise RuntimeError(f"Live calendar provider is missing: {provider_path}")
    spec = importlib.util.spec_from_file_location("news_pulse_calendar_provider", provider_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load the live calendar provider")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.upcoming_us_events(days=config.live_calendar_days)
    if result.get("status") != "ok":
        raise RuntimeError(str(result.get("message") or "Live calendar provider is unavailable"))
    rows: list[dict] = []
    for item in result.get("events", []):
        name = str(item.get("event") or "").upper()
        if name not in config.events:
            continue
        release_text = item.get("release_time") or item.get("release_utc")
        if not release_text:
            continue
        release = datetime.fromisoformat(str(release_text).replace("Z", "+00:00"))
        if release.tzinfo is None:
            release = release.replace(tzinfo=timezone.utc)
        release = release.astimezone(timezone.utc)
        rows.append({
            **item,
            "event": name,
            "release": release,
            "release_utc": release.isoformat(),
            "calendar_provider": result.get("provider"),
        })
    return rows


def _events(config: Config) -> list[dict]:
    rows: list[dict] = []
    with config.calendar_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            name = str(row["event"]).upper()
            if name not in config.events:
                continue
            release = datetime.fromisoformat(str(row["release_utc"]).replace("Z", "+00:00")).astimezone(timezone.utc)
            rows.append({**row, "event": name, "release": release})
    merged = {_calendar_key(row): row for row in rows}
    if config.live_calendar_enabled:
        try:
            for row in _live_events(config):
                merged[_calendar_key(row)] = row
        except Exception as error:
            # Fail closed: stale/static data may still be inspected, but no event is
            # invented and therefore no order can be placed from a missing schedule.
            LOG.warning("Live calendar refresh failed; static calendar only: %s", error)
    return sorted(merged.values(), key=lambda item: item["release"])


def _event_id(row: dict) -> str:
    return f"{row['release'].isoformat()}:{row['event']}"


def _passes_guards(config: Config, gateway: MT5Gateway, now: datetime) -> None:
    account = gateway.account()
    tick = gateway.tick()
    spread = float(tick.ask) - float(tick.bid)
    if spread > config.max_spread_usd:
        raise RuntimeError(f"Spread {spread:.2f} exceeds maximum {config.max_spread_usd:.2f}")
    if account.margin > 0 and float(account.margin_level) < config.min_margin_level_pct:
        raise RuntimeError("Account margin level is below the configured minimum")
    daily_pnl, daily_trades = gateway.daily_stats(now)
    if daily_pnl <= -float(account.balance) * config.max_daily_loss_pct / 100.0:
        raise RuntimeError("Owned NewsPulse daily-loss limit is reached")
    if daily_trades >= config.max_daily_trades:
        raise RuntimeError("Owned NewsPulse daily-trade limit is reached")
    if gateway.owned_positions() or gateway.owned_orders():
        raise RuntimeError("An owned NewsPulse order/position already exists")


def _place(row: dict, config: Config, gateway: MT5Gateway, prediction: dict, frozen: object, now: datetime) -> dict:
    _passes_guards(config, gateway, now)
    tick = gateway.tick()
    point = float(gateway.info.point)
    broker_min = max(float(gateway.info.trade_stops_level), float(gateway.info.trade_freeze_level)) * point
    spread = float(tick.ask) - float(tick.bid)
    buffer = entry_buffer(broker_min=broker_min, configured_min=config.min_buffer_pips * config.pip_size, spread=spread, spread_multiplier=config.spread_multiplier, atr=float(frozen.atr), atr_multiplier=config.atr_multiplier)
    stop_distance = config.breakout_sl_pips * config.pip_size
    direction = str(prediction.get("gold_impact", "UNKNOWN")).upper()
    sides = ["buy", "sell"] if config.mode == "oco" else (["buy"] if direction == "POSITIVE" else ["sell"] if direction == "NEGATIVE" else [])
    if not sides:
        raise RuntimeError(f"Prediction direction is not actionable: {direction}")
    expiry = row["release"] + timedelta(minutes=config.pending_expiry_minutes)
    tickets: list[int] = []
    plans: list[dict] = []
    for side in sides:
        entry = float(frozen.high) + buffer if side == "buy" else float(frozen.low) - buffer
        stop = entry - stop_distance if side == "buy" else entry + stop_distance
        target = entry + stop_distance * config.reward_risk if side == "buy" else entry - stop_distance * config.reward_risk
        volume = gateway.volume_for(side, entry, stop)
        if volume is None:
            raise RuntimeError("Broker minimum lot would exceed configured risk")
        account = gateway.account()
        proposed_risk = gateway.cash_risk(side, volume, entry, stop)
        if proposed_risk > float(account.equity) * config.max_open_risk_pct / 100.0 + 1e-9:
            raise RuntimeError("Planned NewsPulse exposure exceeds MAX_OPEN_RISK_PCT")
        receipt = gateway.send_pending(side=side, entry=entry, stop=stop, target=target, volume=volume, expiration=expiry, comment=oco_comment(f"{row['event']} {side.upper()}"))
        plans.append({"side": side, "entry": entry, "stop": stop, "target": target, "volume": volume})
        if receipt:
            tickets.append(receipt.ticket)
    return {"tickets": tickets, "plans": plans, "buffer": buffer, "expiry": expiry.isoformat(), "frozen": frozen.__dict__}


def run_once(config: Config, now: datetime | None = None) -> str:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    state_store = StateStore(ROOT / "state" / "news-pulse.json")
    state = state_store.load()
    all_events = _events(config)
    active_rows = [row for row in all_events if _event_id(row) in state.active]
    future = active_rows or [
        row for row in all_events
        if row["release"] > now - timedelta(minutes=config.max_hold_minutes)
        and _event_id(row) not in state.processed
    ]
    if not future:
        return "NO_TRADE: calendar has no current or future supported event"
    row = future[0]
    event_id = _event_id(row)
    seconds = (row["release"] - now).total_seconds()
    if event_id in state.processed:
        return f"NO_TRADE: {event_id} already processed"
    if row["event"] not in config.allowed_events:
        if seconds <= 15 * 60:
            state.processed[event_id] = {"status": "filtered", "reason": "development-selected event filter"}
            state_store.save(state)
        return f"NO_TRADE: {row['event']} excluded by validated event-family filter"
    with MT5Gateway(config) as gateway:
        active = state.active.setdefault(event_id, {})
        positions = gateway.owned_positions()
        orders = gateway.owned_orders()
        if seconds <= 0 and "release_values" not in active:
            active["release_values"] = {
                "actual": row.get("actual"),
                "forecast": row.get("forecast"),
                "previous": row.get("previous"),
                "revised": row.get("revised"),
                "captured_utc": now.isoformat(),
            }
            state_store.save(state)
        if seconds < -config.pending_expiry_minutes * 60 and orders:
            for order in orders:
                gateway.cancel_order(int(order.ticket))
            active["pending_cancelled_utc"] = now.isoformat()
            state_store.save(state)
            orders = []
        if seconds <= -config.max_hold_minutes * 60 and positions:
            for position in positions:
                gateway.close_position(position, "NewsPulse max hold")
            active["max_hold_close_utc"] = now.isoformat()
            state_store.save(state)
            positions = []
        if 29 * 60 <= seconds <= 30.5 * 60 and "frozen" not in active:
            frozen = gateway.frozen_range(row["release"])
            active["frozen"] = frozen.__dict__
            state_store.save(state)
        if 29 * 60 <= seconds <= 30.5 * 60 and "early_prediction" not in active:
            service = PredictionService(config.ai_news_root, ROOT / "state" / "predictions")
            active["early_prediction"] = service.predict(row["event"], row["release"], "early", row.get("forecast"), row.get("previous"))
            state_store.save(state)
            return f"EARLY prediction saved for {event_id}"
        if 14 * 60 <= seconds <= 15.5 * 60 and "final_prediction" not in active:
            if "frozen" not in active or "early_prediction" not in active:
                raise RuntimeError("T-30 range/prediction is missing; stale late-start execution rejected")
            service = PredictionService(config.ai_news_root, ROOT / "state" / "predictions")
            final = service.predict(row["event"], row["release"], "final", row.get("forecast"), row.get("previous"))
            active["final_prediction"] = final
            confidence = float(final.get("confidence_pct", 0.0)) / 100.0
            if confidence < config.confidence_threshold:
                state.processed[event_id] = {"status": "no_trade", "reason": "confidence", "confidence": confidence}
                state.active.pop(event_id, None)
                state_store.save(state)
                return f"NO_TRADE: confidence {confidence:.2f} below {config.confidence_threshold:.2f}"
            frozen = type("Frozen", (), active["frozen"])()
            plan = _place(row, config, gateway, final, frozen, now)
            active["signal_hash"] = signal_hash(event_id, final.get("gold_impact"), plan["frozen"]["high"], plan["frozen"]["low"], config.mode, config.reward_risk)
            active["order_plan"] = plan
            state_store.save(state)
            return f"{'LIVE' if config.execution_enabled else 'PAPER'} orders prepared for {event_id}: {plan['plans']}"
        # OCO ownership management: first position cancels the opposite owned order.
        if positions and orders:
            for order in orders:
                gateway.cancel_order(int(order.ticket))
            active["filled_position_tickets"] = [int(x.ticket) for x in positions]
            active["filled_side"] = "buy" if int(positions[0].type) == 0 else "sell"
            active["oco_cancelled"] = True
            state_store.save(state)
        # The validated configuration permits exactly one retracement re-entry,
        # and only after the breakout position has closed at a loss.
        if (
            config.allow_reentry
            and not positions
            and not orders
            and active.get("filled_position_tickets")
            and not active.get("reentry_placed")
            and seconds > -config.max_hold_minutes * 60
        ):
            deals = gateway.recent_owned_deals(row["release"] - timedelta(minutes=15), now)
            exits = [deal for deal in deals if int(getattr(deal, "entry", -1)) in {1, 3}]
            if exits and sum(float(getattr(deal, "profit", 0.0)) for deal in exits) < 0:
                frozen_data = active["frozen"]
                side = str(active.get("filled_side", ""))
                low, high = float(frozen_data["low"]), float(frozen_data["high"])
                fib = config.buy_reentry_fib if side == "buy" else config.sell_reentry_fib
                entry = low + (high - low) * fib
                stop_distance = config.reentry_sl_pips * config.pip_size
                stop = entry - stop_distance if side == "buy" else entry + stop_distance
                target = entry + stop_distance * 5.0 if side == "buy" else entry - stop_distance * 5.0
                tick = gateway.tick()
                valid_side = (side == "buy" and entry < float(tick.ask)) or (side == "sell" and entry > float(tick.bid))
                if valid_side:
                    volume = gateway.volume_for(side, entry, stop)
                    if volume is not None:
                        receipt = gateway.send_pending(
                            side=side, entry=entry, stop=stop, target=target, volume=volume,
                            expiration=row["release"] + timedelta(minutes=config.max_hold_minutes),
                            comment=oco_comment(f"{row['event']} REENTRY"), order_kind="limit",
                        )
                        active["reentry_placed"] = {"ticket": receipt.ticket if receipt else None, "side": side, "entry": entry, "stop": stop, "target": target, "volume": volume}
                        state_store.save(state)
        if seconds < -config.max_hold_minutes * 60:
            state.processed[event_id] = {"status": "expired", **active}
            state.active.pop(event_id, None)
            state_store.save(state)
    return f"WAIT: next {event_id} in {seconds / 60:.1f} minutes"


def run_live(config: Config) -> None:
    LOG.info("NewsPulse started | execution_enabled=%s", config.execution_enabled)
    while True:
        try:
            LOG.info(run_once(config))
        except Exception:
            LOG.exception("Worker cycle failed safely")
        time.sleep(config.poll_seconds)


def configure_logging() -> None:
    (ROOT / "logs").mkdir(exist_ok=True)
    handlers = [logging.StreamHandler(), logging.FileHandler(ROOT / "logs" / "news-pulse.log", encoding="utf-8")]
    logging.basicConfig(level=logging.INFO, format="%(asctime)sZ | %(levelname)-7s | %(name)s | %(message)s", handlers=handlers)
