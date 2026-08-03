from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import logging
import math
from pathlib import Path
import time

import joblib
import MetaTrader5 as mt5

from .config import Config, ROOT
from .core import discover_gold_symbol, infer_weekly_timing, model_validated, momentum_signal, risk_sized_volume
from .state import StateStore


LOG = logging.getLogger("weekend_direction.live")


class Gateway:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.info = None
        self.symbol = ""

    def __enter__(self) -> "Gateway":
        if not mt5.initialize():
            raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
        self.info = discover_gold_symbol(mt5.symbols_get() or ())
        self.symbol = str(self.info.name)
        mt5.symbol_select(self.symbol, True)
        return self

    def __exit__(self, *_: object) -> None:
        mt5.shutdown()

    def account(self):
        account = mt5.account_info()
        if account is None:
            raise RuntimeError(f"MT5 account unavailable: {mt5.last_error()}")
        return account

    def positions(self):
        return [x for x in (mt5.positions_get(symbol=self.symbol) or ()) if int(x.magic) == self.config.magic]

    def daily_stats(self, now: datetime) -> tuple[float, int]:
        start = now.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        deals = [
            deal for deal in (mt5.history_deals_get(start, now) or ())
            if int(getattr(deal, "magic", -1)) == self.config.magic
        ]
        realized = sum(
            float(getattr(deal, "profit", 0.0))
            + float(getattr(deal, "commission", 0.0))
            + float(getattr(deal, "swap", 0.0))
            + float(getattr(deal, "fee", 0.0))
            for deal in deals
            if int(getattr(deal, "entry", -1)) in {mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_OUT_BY}
        )
        opened = {
            int(getattr(deal, "order", 0))
            for deal in deals
            if int(getattr(deal, "entry", -1)) == mt5.DEAL_ENTRY_IN
        }
        return realized, len(opened)

    def timing_and_rates(self):
        now = datetime.now(timezone.utc)
        rates = mt5.copy_rates_range(self.symbol, mt5.TIMEFRAME_M1, now - timedelta(weeks=self.config.history_weeks), now)
        if rates is None or len(rates) < 50_000:
            raise RuntimeError("Broker M1 history is incomplete")
        timing = infer_weekly_timing([int(x["time"]) for x in rates])
        return timing, rates

    def volume(self, side: str, entry: float, stop: float) -> float | None:
        if self.config.sizing_mode == "fixed_lot":
            raw = self.config.fixed_lot
        else:
            account = self.account()
            order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL
            loss = mt5.order_calc_profit(order_type, self.symbol, 1.0, entry, stop)
            if loss is None:
                raise RuntimeError(f"order_calc_profit failed: {mt5.last_error()}")
            raw = risk_sized_volume(float(account.equity) * self.config.risk_pct / 100, abs(float(loss)), float(self.info.volume_min), float(self.info.volume_max), float(self.info.volume_step))
            if raw is None:
                return None
        step = float(self.info.volume_step)
        return round(max(float(self.info.volume_min), math.floor(float(raw) / step + 1e-12) * step), 8)

    def market(self, side: str, stop: float, target: float, volume: float) -> int | None:
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            raise RuntimeError("No executable tick")
        entry = float(tick.ask if side == "BUY" else tick.bid)
        base = {
            "action": mt5.TRADE_ACTION_DEAL, "symbol": self.symbol, "volume": volume,
            "type": mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL,
            "price": round(entry, int(self.info.digits)), "sl": round(stop, int(self.info.digits)), "tp": round(target, int(self.info.digits)),
            "deviation": max(1, int(round(self.config.max_slippage_usd / float(self.info.point)))), "magic": self.config.magic,
            "comment": "WeekendDir PROV momentum"[:31], "type_time": mt5.ORDER_TIME_GTC,
        }
        for fill in dict.fromkeys([int(self.info.filling_mode), mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN]):
            request = {**base, "type_filling": fill}
            check = mt5.order_check(request)
            LOG.info("order_check request=%s response=%s", request, check)
            if check is None or int(check.retcode) not in {0, mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED}:
                continue
            if not self.config.execution_enabled:
                LOG.warning("PAPER market signal: %s", request)
                return None
            result = mt5.order_send(request)
            LOG.info("order_send request=%s response=%s", request, result)
            if result is None or int(result.retcode) not in {mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED}:
                raise RuntimeError(f"order_send failed: {result}")
            return int(result.order or result.deal)
        raise RuntimeError("No broker-supported filling mode passed order_check")

    def close_position(self, position) -> None:
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            return
        is_buy = int(position.type) == mt5.POSITION_TYPE_BUY
        base = {
            "action": mt5.TRADE_ACTION_DEAL, "symbol": self.symbol, "position": int(position.ticket), "volume": float(position.volume),
            "type": mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY, "price": float(tick.bid if is_buy else tick.ask),
            "deviation": max(1, int(round(self.config.max_slippage_usd / float(self.info.point)))), "magic": self.config.magic,
            "comment": "WeekendDir reopen exit"[:31], "type_time": mt5.ORDER_TIME_GTC,
        }
        if not self.config.execution_enabled:
            LOG.warning("PAPER reopen close: %s", base)
            return
        for fill in dict.fromkeys([int(self.info.filling_mode), mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK]):
            request = {**base, "type_filling": fill}
            check = mt5.order_check(request)
            LOG.info("close order_check request=%s response=%s", request, check)
            if check is None or int(check.retcode) not in {0, mt5.TRADE_RETCODE_DONE}:
                continue
            result = mt5.order_send(request)
            LOG.info("close order_send request=%s response=%s", request, result)
            if result is not None and int(result.retcode) == mt5.TRADE_RETCODE_DONE:
                return
        raise RuntimeError("Could not close owned weekend position")


def _friday_returns(rates, close_minute_of_week: int, before_utc: datetime) -> tuple[list[float], float | None]:
    rows = [x for x in rates if int(x["time"]) < int(before_utc.timestamp())]
    by_week: dict[str, list] = {}
    for row in rows:
        stamp = datetime.fromtimestamp(int(row["time"]), timezone.utc)
        by_week.setdefault(stamp.strftime("%G-W%V"), []).append(row)
    prior: list[float] = []
    current: float | None = None
    current_week = before_utc.strftime("%G-W%V")
    for week, values in sorted(by_week.items()):
        values.sort(key=lambda x: int(x["time"]))
        end = values[-1]
        end_time = datetime.fromtimestamp(int(end["time"]), timezone.utc)
        if abs((end_time.weekday() * 1440 + end_time.hour * 60 + end_time.minute) - close_minute_of_week) > 10:
            continue
        cutoff = int(end["time"]) - 24 * 3600
        start_candidates = [x for x in values if int(x["time"]) <= cutoff]
        if not start_candidates:
            continue
        start = start_candidates[-1]
        value = float(end["close"]) / float(start["close"]) - 1.0
        if week == current_week:
            current = value
        else:
            prior.append(value)
    return prior, current


def run_once(config: Config, now: datetime | None = None) -> str:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    artifact = joblib.load(config.model_path)
    validated = model_validated(config.model_metadata_path, artifact)
    if not validated and not config.allow_provisional:
        return "NO_TRADE: selected weekend model is rejected (validated=false)"
    store = StateStore(ROOT / "state" / "weekend-direction.json")
    state = store.load()
    with Gateway(config) as gateway:
        account = gateway.account()
        demo_mode = int(getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0))
        is_demo = "demo" in str(account.server).lower() or int(getattr(account, "trade_mode", -1)) == demo_mode
        if not validated and config.allow_provisional and not is_demo:
            return "NO_TRADE: provisional momentum mode is demo-only"
        timing, rates = gateway.timing_and_rates()
        current_minute = now.weekday() * 1440 + now.hour * 60 + now.minute
        positions = gateway.positions()
        # Reopening is inferred from actual M1 gaps. The first executable tick closes owned exposure.
        if positions and abs(current_minute - timing.reopen_minute_of_week) <= 10:
            for position in positions:
                gateway.close_position(position)
            return "REOPEN: owned weekend position close submitted"
        delta = timing.close_minute_of_week - current_minute
        if delta != config.lead_minutes:
            return f"WAIT: inferred close in {delta} minute(s); {timing.observations} historical gaps"
        week_id = now.strftime("%G-W%V")
        if week_id in state.processed_weeks or positions:
            return f"NO_TRADE: weekend {week_id} already processed or owned position exists"
        prior, current = _friday_returns(rates, timing.close_minute_of_week, now)
        if current is None:
            # Current 24h momentum is calculated strictly from bars completed before now.
            completed = [x for x in rates if int(x["time"]) < int(now.replace(second=0, microsecond=0).timestamp())]
            before = [x for x in completed if int(x["time"]) <= int(now.timestamp()) - 24 * 3600]
            if not completed or not before:
                return "NO_TRADE: completed 24-hour history is incomplete"
            current = float(completed[-1]["close"]) / float(before[-1]["close"]) - 1.0
        signal = momentum_signal(current_return=current, prior_returns=prior, quantile=config.momentum_quantile, close_utc=now + timedelta(minutes=config.lead_minutes))
        if signal is None:
            state.processed_weeks[week_id] = {"status": "no_trade", "reason": "momentum below prior-only threshold"}
            store.save(state)
            return "NO_TRADE: Friday momentum below rolling 70th percentile"
        tick = mt5.symbol_info_tick(gateway.symbol)
        spread = float(tick.ask) - float(tick.bid)
        if spread > config.max_spread_usd:
            return f"NO_TRADE: spread {spread:.2f} exceeds {config.max_spread_usd:.2f}"
        if account.margin > 0 and float(account.margin_level) < config.min_margin_level_pct:
            return "NO_TRADE: insufficient margin level"
        daily_pnl, daily_trades = gateway.daily_stats(now)
        if daily_pnl <= -float(account.balance) * config.max_daily_loss_pct / 100.0:
            return "NO_TRADE: owned WeekendDirection daily-loss limit reached"
        if daily_trades >= config.max_daily_trades:
            return "NO_TRADE: owned WeekendDirection daily-trade limit reached"
        entry = float(tick.ask if signal.side == "BUY" else tick.bid)
        stop = entry - config.stop_usd if signal.side == "BUY" else entry + config.stop_usd
        target = entry + config.stop_usd * config.reward_risk if signal.side == "BUY" else entry - config.stop_usd * config.reward_risk
        volume = gateway.volume(signal.side, entry, stop)
        if volume is None:
            return "NO_TRADE: broker minimum lot exceeds risk cap"
        order_type = mt5.ORDER_TYPE_BUY if signal.side == "BUY" else mt5.ORDER_TYPE_SELL
        planned_loss = mt5.order_calc_profit(order_type, gateway.symbol, volume, entry, stop)
        if planned_loss is None:
            return f"NO_TRADE: risk calculation failed {mt5.last_error()}"
        if abs(float(planned_loss)) > float(account.equity) * config.max_open_risk_pct / 100.0 + 1e-9:
            return "NO_TRADE: planned risk exceeds MAX_OPEN_RISK_PCT"
        required_margin = mt5.order_calc_margin(order_type, gateway.symbol, volume, entry)
        if required_margin is None or float(required_margin) > float(account.margin_free):
            return "NO_TRADE: insufficient free margin"
        ticket = gateway.market(signal.side, stop, target, volume)
        state.processed_weeks[week_id] = {"status": "live" if ticket else "paper", "side": signal.side, "return_24h": signal.return_24h, "threshold": signal.threshold, "ticket": ticket, "entry": entry, "stop": stop, "target": target, "volume": volume}
        store.save(state)
        return f"{'LIVE' if ticket else 'PAPER'} {signal.side} {volume} {gateway.symbol} | 24h={signal.return_24h:.3%} threshold={signal.threshold:.3%}"


def run_live(config: Config) -> None:
    LOG.info("WeekendDirection started | execution_enabled=%s provisional=%s", config.execution_enabled, config.allow_provisional)
    while True:
        try:
            LOG.info(run_once(config))
        except Exception:
            LOG.exception("Worker cycle failed safely")
        time.sleep(config.poll_seconds)


def configure_logging() -> None:
    (ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)sZ | %(levelname)-7s | %(name)s | %(message)s", handlers=[logging.StreamHandler(), logging.FileHandler(ROOT / "logs" / "weekend-direction.log", encoding="utf-8")])
