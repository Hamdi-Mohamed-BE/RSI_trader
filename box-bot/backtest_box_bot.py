from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5


TIMEFRAMES = {
    "M5": mt5.TIMEFRAME_M5,
    "H4": mt5.TIMEFRAME_H4,
}


@dataclass
class CandidateTrade:
    symbol: str
    broker_symbol: str
    setup: str
    side: str
    signal_time: int
    entry_time: int
    exit_time: int
    entry: float
    sl: float
    tp: float
    lot: float
    pnl: float
    result: str
    rr: float
    margin: float
    reason: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def mt5_as_dict(value: Any) -> dict[str, Any]:
    return value._asdict() if hasattr(value, "_asdict") else dict(value or {})


def rates_to_dicts(rates) -> list[dict[str, float]]:
    if rates is None:
        return []
    return [
        {key: (int(value) if key == "time" else float(value)) for key, value in zip(rates.dtype.names, row)}
        for row in rates
    ]


def atr(candles: list[dict[str, float]], period: int = 14) -> float | None:
    if len(candles) <= period:
        return None
    ranges: list[float] = []
    for index in range(1, len(candles)):
        high = candles[index]["high"]
        low = candles[index]["low"]
        prev_close = candles[index - 1]["close"]
        ranges.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    if len(ranges) < period:
        return None
    value = sum(ranges[:period]) / period
    for true_range in ranges[period:]:
        value = (value * (period - 1) + true_range) / period
    return value


def iso_time(timestamp: int) -> str:
    return datetime.fromtimestamp(int(timestamp), timezone.utc).isoformat().replace("+00:00", "Z")


def round_to_digits(value: float, digits: int) -> float:
    return round(float(value), int(digits))


class BoxBacktester:
    def __init__(self, root: Path, config: dict[str, Any], start_balance: float) -> None:
        self.root = root
        self.config = config
        self.start_balance = float(start_balance)

    def connect(self) -> None:
        mt5_path = self.config.get("mt5_path")
        ok = mt5.initialize(path=mt5_path) if mt5_path else mt5.initialize()
        if not ok:
            raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

    def shutdown(self) -> None:
        mt5.shutdown()

    def symbol_config(self, logical: str, entry: Any) -> tuple[list[str], float]:
        if isinstance(entry, dict):
            aliases = list(entry.get("aliases", [logical]))
            lot = float(entry.get("lot", 0.01))
        else:
            aliases = list(entry if isinstance(entry, list) else [logical])
            lot = 0.01
        return aliases, lot

    def resolve_symbol(self, logical: str, aliases: list[str]) -> str | None:
        names = [symbol.name for symbol in (mt5.symbols_get() or [])]
        upper_to_name = {name.upper(): name for name in names}
        for alias in aliases:
            found = upper_to_name.get(alias.upper())
            if found:
                mt5.symbol_select(found, True)
                return found
        candidates = [name for name in names if name.upper().startswith(logical.upper())]
        candidates.sort(key=lambda name: (0 if "VIP" in name.upper() else 1, len(name), name))
        if candidates:
            mt5.symbol_select(candidates[0], True)
            return candidates[0]
        return None

    def copy_rates(self, symbol: str, timeframe_name: str, start: datetime, end: datetime) -> list[dict[str, float]]:
        timeframe = TIMEFRAMES[timeframe_name]
        direct = rates_to_dicts(mt5.copy_rates_range(symbol, timeframe, start, end))
        if direct:
            return direct

        # Some terminals return an empty range result when the requested start is
        # older than the local chart window, while copy_rates_from can still page
        # backward. Stitch chunks and then filter to the requested period.
        chunk_end = end
        seen: dict[int, dict[str, float]] = {}
        for _ in range(20):
            chunk = rates_to_dicts(mt5.copy_rates_from(symbol, timeframe, chunk_end, 50000))
            if not chunk:
                break
            for candle in chunk:
                timestamp = int(candle["time"])
                if int(start.timestamp()) <= timestamp <= int(end.timestamp()):
                    seen[timestamp] = candle
            first_time = int(chunk[0]["time"])
            if first_time <= int(start.timestamp()):
                break
            next_end = datetime.fromtimestamp(first_time, timezone.utc) - timedelta(minutes=5)
            if next_end >= chunk_end:
                break
            chunk_end = next_end
        return [seen[key] for key in sorted(seen)]

    def spread_price(self, symbol: str, candle: dict[str, float]) -> float:
        info = mt5.symbol_info(symbol)
        if not info:
            return 0.0
        spread_points = float(candle.get("spread", 0.0) or 0.0)
        if spread_points <= 0:
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                return abs(float(tick.ask) - float(tick.bid))
            return 0.0
        return spread_points * float(info.point or 0.0)

    def calc_profit(self, symbol: str, side: str, lot: float, entry: float, exit_price: float) -> float:
        order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL
        value = mt5.order_calc_profit(order_type, symbol, lot, entry, exit_price)
        return float(value) if value is not None else 0.0

    def calc_margin(self, symbol: str, side: str, lot: float, entry: float) -> float:
        order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL
        value = mt5.order_calc_margin(order_type, symbol, lot, entry)
        return float(value) if value is not None else 0.0

    def normalize_lot(self, symbol: str, requested: float) -> float | None:
        info = mt5.symbol_info(symbol)
        if not info:
            return None
        step = float(info.volume_step or 0.01)
        min_lot = float(info.volume_min or step)
        max_lot = float(info.volume_max or requested)
        lot = math.floor(float(requested) / step) * step
        lot = round(lot, 8)
        if lot < min_lot:
            return None
        return min(max(lot, min_lot), max_lot)

    def h4_box_for_time(
        self,
        h4: list[dict[str, float]],
        h4_index: int,
        m5_time: int,
    ) -> tuple[dict[str, float] | None, int]:
        while h4_index + 1 < len(h4) and int(h4[h4_index + 1]["time"]) + 4 * 3600 <= m5_time:
            h4_index += 1
        if h4_index < 0 or int(h4[h4_index]["time"]) + 4 * 3600 > m5_time:
            return None, h4_index
        return h4[h4_index], h4_index

    def detect_exit(
        self,
        m5: list[dict[str, float]],
        start_index: int,
        side: str,
        sl: float,
        tp: float,
    ) -> tuple[int, float, str]:
        for index in range(start_index, len(m5)):
            candle = m5[index]
            high = float(candle["high"])
            low = float(candle["low"])
            if side == "BUY":
                hit_sl = low <= sl
                hit_tp = high >= tp
                if hit_sl:
                    return int(candle["time"]), sl, "SL"
                if hit_tp:
                    return int(candle["time"]), tp, "TP"
            else:
                hit_sl = high >= sl
                hit_tp = low <= tp
                if hit_sl:
                    return int(candle["time"]), sl, "SL"
                if hit_tp:
                    return int(candle["time"]), tp, "TP"
        last = m5[-1]
        return int(last["time"]), float(last["close"]), "EOD"

    def make_entry_price(self, symbol: str, side: str, next_bar: dict[str, float]) -> float:
        spread = self.spread_price(symbol, next_bar)
        mid_open = float(next_bar["open"])
        return mid_open + spread / 2.0 if side == "BUY" else mid_open - spread / 2.0

    def generate_symbol_trades(
        self,
        logical: str,
        entry: Any,
        start: datetime,
        end: datetime,
    ) -> tuple[list[CandidateTrade], dict[str, Any]]:
        aliases, requested_lot = self.symbol_config(logical, entry)
        broker_symbol = self.resolve_symbol(logical, aliases)
        if not broker_symbol:
            return [], {"symbol": logical, "status": "symbol_not_found", "aliases": aliases}
        lot = self.normalize_lot(broker_symbol, requested_lot)
        if lot is None:
            return [], {"symbol": logical, "broker_symbol": broker_symbol, "status": "lot_invalid", "lot": requested_lot}

        warmup_start = start - timedelta(days=10)
        m5 = self.copy_rates(broker_symbol, "M5", warmup_start, end)
        h4 = self.copy_rates(broker_symbol, "H4", warmup_start - timedelta(days=20), end)
        if len(m5) < 200 or len(h4) < 20:
            return [], {
                "symbol": logical,
                "broker_symbol": broker_symbol,
                "status": "insufficient_history",
                "m5_bars": len(m5),
                "h4_bars": len(h4),
            }

        info = mt5.symbol_info(broker_symbol)
        if not info:
            return [], {"symbol": logical, "broker_symbol": broker_symbol, "status": "symbol_info_missing"}
        digits = int(info.digits)

        strategy = self.config.get("strategy", {})
        atr_period = int(strategy.get("atr_period", 14))
        final_rr = float(strategy.get("final_rr", 3.0))
        min_final_rr = float(strategy.get("min_final_rr", 2.9))
        edge_zone_pct = float(strategy.get("edge_zone_pct", 0.15))
        max_spread_atr_ratio = float(strategy.get("max_spread_atr_ratio", 0.35))
        stop_buffer_atr = float(strategy.get("stop_buffer_atr", 0.1))
        stop_buffer_spread_mult = float(strategy.get("stop_buffer_spread_mult", 2.0))
        breakout_close_buffer_atr = float(strategy.get("breakout_close_buffer_atr", 0.1))
        breakout_retest_tolerance_atr = float(strategy.get("breakout_retest_tolerance_atr", 0.2))
        max_breakout_stop_atr = float(strategy.get("max_breakout_stop_atr", 1.6))
        require_rejection = bool(strategy.get("require_rejection_candle", True))

        trades: list[CandidateTrade] = []
        breakout_by_box: dict[int, str] = {}
        last_exit_index = 0
        h4_index = -1
        skipped: dict[str, int] = {}

        for index in range(atr_period + 50, len(m5) - 1):
            candle = m5[index]
            signal_time = int(candle["time"])
            if signal_time < int(start.timestamp()) or index < last_exit_index:
                continue
            box, h4_index = self.h4_box_for_time(h4, h4_index, signal_time)
            if not box:
                continue
            box_time = int(box["time"])
            box_high = float(box["high"])
            box_low = float(box["low"])
            box_range = box_high - box_low
            if box_range <= float(info.point or 0.0):
                skipped["invalid_box"] = skipped.get("invalid_box", 0) + 1
                continue

            lookback = m5[max(0, index - atr_period - 60) : index + 1]
            atr_value = atr(lookback, atr_period)
            if not atr_value or atr_value <= 0:
                skipped["invalid_atr"] = skipped.get("invalid_atr", 0) + 1
                continue
            spread = self.spread_price(broker_symbol, candle)
            if spread / atr_value > max_spread_atr_ratio:
                skipped["spread"] = skipped.get("spread", 0) + 1
                continue
            buffer = max(
                atr_value * stop_buffer_atr,
                spread * stop_buffer_spread_mult,
                float(info.point or 0.0) * max(float(info.trade_stops_level or 0.0), 1.0),
            )

            breakout_buffer = max(atr_value * breakout_close_buffer_atr, buffer)
            active_breakout = breakout_by_box.get(box_time)
            close = float(candle["close"])
            if not active_breakout:
                if close > box_high + breakout_buffer:
                    breakout_by_box[box_time] = "UP"
                    skipped["breakout_set_up"] = skipped.get("breakout_set_up", 0) + 1
                    continue
                if close < box_low - breakout_buffer:
                    breakout_by_box[box_time] = "DOWN"
                    skipped["breakout_set_down"] = skipped.get("breakout_set_down", 0) + 1
                    continue

            plan = self.plan_breakout_trade(
                logical,
                broker_symbol,
                lot,
                m5,
                index,
                box_time,
                box_high,
                box_low,
                atr_value,
                buffer,
                breakout_by_box.get(box_time),
                breakout_retest_tolerance_atr,
                max_breakout_stop_atr,
                digits,
            )
            if plan is None:
                plan = self.plan_range_trade(
                    logical,
                    broker_symbol,
                    lot,
                    m5,
                    index,
                    box_time,
                    box_high,
                    box_low,
                    box_range,
                    buffer,
                    edge_zone_pct,
                    final_rr,
                    min_final_rr,
                    require_rejection,
                    digits,
                )
            if plan is None:
                continue
            trades.append(plan)
            exit_index = next((i for i, item in enumerate(m5) if int(item["time"]) == plan.exit_time), index + 1)
            last_exit_index = max(last_exit_index, exit_index + 1)

        return trades, {
            "symbol": logical,
            "broker_symbol": broker_symbol,
            "status": "ok",
            "m5_bars": len(m5),
            "h4_bars": len(h4),
            "lot": lot,
            "skipped": skipped,
        }

    def plan_range_trade(
        self,
        logical: str,
        broker_symbol: str,
        lot: float,
        m5: list[dict[str, float]],
        index: int,
        box_time: int,
        box_high: float,
        box_low: float,
        box_range: float,
        buffer: float,
        edge_zone_pct: float,
        final_rr: float,
        min_final_rr: float,
        require_rejection: bool,
        digits: int,
    ) -> CandidateTrade | None:
        candle = m5[index]
        next_bar = m5[index + 1]
        edge_zone = box_range * edge_zone_pct
        side: str | None = None
        reason = ""
        if float(candle["high"]) >= box_high - edge_zone and float(candle["close"]) <= box_high - buffer:
            if not require_rejection or float(candle["close"]) < float(candle["open"]):
                side = "SELL"
                reason = "range_rejection_from_h4_high"
        if float(candle["low"]) <= box_low + edge_zone and float(candle["close"]) >= box_low + buffer:
            if not require_rejection or float(candle["close"]) > float(candle["open"]):
                side = "BUY"
                reason = "range_rejection_from_h4_low"
        if not side:
            return None

        entry = self.make_entry_price(broker_symbol, side, next_bar)
        target = box_high if side == "BUY" else box_low
        reward = target - entry if side == "BUY" else entry - target
        if reward <= 0:
            return None
        risk = reward / final_rr
        if side == "BUY":
            sl = entry - risk
            if sl > box_low - buffer:
                return None
            tp = target
        else:
            sl = entry + risk
            if sl < box_high + buffer:
                return None
            tp = target
        rr = reward / abs(entry - sl)
        if rr < min_final_rr:
            return None
        return self.finish_trade(logical, broker_symbol, "range", side, box_time, m5, index, entry, sl, tp, lot, rr, reason, digits)

    def plan_breakout_trade(
        self,
        logical: str,
        broker_symbol: str,
        lot: float,
        m5: list[dict[str, float]],
        index: int,
        box_time: int,
        box_high: float,
        box_low: float,
        atr_value: float,
        buffer: float,
        direction: str | None,
        tolerance_atr: float,
        max_stop_atr: float,
        digits: int,
    ) -> CandidateTrade | None:
        if direction not in {"UP", "DOWN"}:
            return None
        candle = m5[index]
        next_bar = m5[index + 1]
        tolerance = max(atr_value * tolerance_atr, buffer)
        if direction == "UP":
            touched_edge = float(candle["low"]) <= box_high + tolerance
            rejected = float(candle["close"]) > box_high and float(candle["close"]) > float(candle["open"])
            if not (touched_edge and rejected):
                return None
            side = "BUY"
            entry = self.make_entry_price(broker_symbol, side, next_bar)
            sl = min(box_high, float(candle["low"])) - buffer
            reason = "breakout_up_retest_buy"
        else:
            touched_edge = float(candle["high"]) >= box_low - tolerance
            rejected = float(candle["close"]) < box_low and float(candle["close"]) < float(candle["open"])
            if not (touched_edge and rejected):
                return None
            side = "SELL"
            entry = self.make_entry_price(broker_symbol, side, next_bar)
            sl = max(box_low, float(candle["high"])) + buffer
            reason = "breakout_down_retest_sell"
        risk = abs(entry - sl)
        if risk <= 0 or risk > atr_value * max_stop_atr:
            return None
        tp = entry + risk * 3.0 if side == "BUY" else entry - risk * 3.0
        return self.finish_trade(logical, broker_symbol, "breakout_retest", side, box_time, m5, index, entry, sl, tp, lot, 3.0, reason, digits)

    def finish_trade(
        self,
        logical: str,
        broker_symbol: str,
        setup: str,
        side: str,
        box_time: int,
        m5: list[dict[str, float]],
        signal_index: int,
        entry: float,
        sl: float,
        tp: float,
        lot: float,
        rr: float,
        reason: str,
        digits: int,
    ) -> CandidateTrade:
        entry = round_to_digits(entry, digits)
        sl = round_to_digits(sl, digits)
        tp = round_to_digits(tp, digits)
        exit_time, exit_price, result = self.detect_exit(m5, signal_index + 1, side, sl, tp)
        pnl = self.calc_profit(broker_symbol, side, lot, entry, exit_price)
        margin = self.calc_margin(broker_symbol, side, lot, entry)
        return CandidateTrade(
            symbol=logical,
            broker_symbol=broker_symbol,
            setup=setup,
            side=side,
            signal_time=int(m5[signal_index]["time"]),
            entry_time=int(m5[signal_index + 1]["time"]),
            exit_time=exit_time,
            entry=entry,
            sl=sl,
            tp=tp,
            lot=lot,
            pnl=round(float(pnl), 2),
            result=result,
            rr=round(rr, 2),
            margin=round(float(margin), 2),
            reason=reason,
        )

    def summarize_trades(self, trades: list[CandidateTrade], start_balance: float) -> dict[str, Any]:
        balance = float(start_balance)
        peak = balance
        max_drawdown = 0.0
        wins = 0
        losses = 0
        accepted: list[CandidateTrade] = []
        skipped_margin = 0
        for trade in sorted(trades, key=lambda item: (item.entry_time, item.symbol)):
            if balance <= 0:
                break
            if trade.margin > balance:
                skipped_margin += 1
                continue
            balance += trade.pnl
            accepted.append(trade)
            peak = max(peak, balance)
            max_drawdown = max(max_drawdown, peak - balance)
            if trade.pnl > 0:
                wins += 1
            elif trade.pnl < 0:
                losses += 1
        gross_profit = sum(trade.pnl for trade in accepted if trade.pnl > 0)
        gross_loss = abs(sum(trade.pnl for trade in accepted if trade.pnl < 0))
        return {
            "trades": len(accepted),
            "wins": wins,
            "losses": losses,
            "win_rate_pct": round((wins / len(accepted) * 100.0), 2) if accepted else 0.0,
            "start_balance": round(start_balance, 2),
            "end_balance": round(balance, 2),
            "net_pnl": round(balance - start_balance, 2),
            "return_pct": round(((balance - start_balance) / start_balance * 100.0), 2) if start_balance else 0.0,
            "max_drawdown_cash": round(max_drawdown, 2),
            "max_drawdown_pct": round((max_drawdown / peak * 100.0), 2) if peak else 0.0,
            "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else None,
            "skipped_margin": skipped_margin,
        }

    def summarize_portfolio(self, trades_by_symbol: dict[str, list[CandidateTrade]]) -> dict[str, Any]:
        balance = self.start_balance
        peak = balance
        max_drawdown = 0.0
        accepted: list[CandidateTrade] = []
        skipped_overlap = 0
        skipped_margin = 0
        busy_until = 0
        all_trades = sorted(
            [trade for trades in trades_by_symbol.values() for trade in trades],
            key=lambda item: (item.entry_time, item.symbol),
        )
        for trade in all_trades:
            if balance <= 0:
                break
            if trade.entry_time < busy_until:
                skipped_overlap += 1
                continue
            if trade.margin > balance:
                skipped_margin += 1
                continue
            balance += trade.pnl
            accepted.append(trade)
            busy_until = trade.exit_time
            peak = max(peak, balance)
            max_drawdown = max(max_drawdown, peak - balance)
        wins = sum(1 for trade in accepted if trade.pnl > 0)
        losses = sum(1 for trade in accepted if trade.pnl < 0)
        gross_profit = sum(trade.pnl for trade in accepted if trade.pnl > 0)
        gross_loss = abs(sum(trade.pnl for trade in accepted if trade.pnl < 0))
        return {
            "mode": "combined_one_trade_at_a_time",
            "trades": len(accepted),
            "wins": wins,
            "losses": losses,
            "win_rate_pct": round((wins / len(accepted) * 100.0), 2) if accepted else 0.0,
            "start_balance": round(self.start_balance, 2),
            "end_balance": round(balance, 2),
            "net_pnl": round(balance - self.start_balance, 2),
            "return_pct": round(((balance - self.start_balance) / self.start_balance * 100.0), 2) if self.start_balance else 0.0,
            "max_drawdown_cash": round(max_drawdown, 2),
            "max_drawdown_pct": round((max_drawdown / peak * 100.0), 2) if peak else 0.0,
            "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else None,
            "skipped_overlap": skipped_overlap,
            "skipped_margin": skipped_margin,
            "accepted_trades": [asdict(trade) | {"signal_time_iso": iso_time(trade.signal_time), "entry_time_iso": iso_time(trade.entry_time), "exit_time_iso": iso_time(trade.exit_time)} for trade in accepted],
        }

    def run(self, start: datetime, end: datetime) -> dict[str, Any]:
        diagnostics: list[dict[str, Any]] = []
        trades_by_symbol: dict[str, list[CandidateTrade]] = {}
        symbol_summaries: dict[str, Any] = {}
        for logical, entry in self.config.get("symbols", {}).items():
            trades, diagnostic = self.generate_symbol_trades(logical, entry, start, end)
            diagnostics.append(diagnostic)
            trades_by_symbol[logical] = trades
            symbol_summaries[logical] = self.summarize_trades(trades, self.start_balance)
        portfolio = self.summarize_portfolio(trades_by_symbol)
        return {
            "generated_at": utc_now().isoformat().replace("+00:00", "Z"),
            "period": {"start": start.isoformat().replace("+00:00", "Z"), "end": end.isoformat().replace("+00:00", "Z")},
            "assumptions": {
                "starting_balance": self.start_balance,
                "entry": "next M5 open after signal, adjusted by bar spread when available",
                "exit": "M5 OHLC, SL wins if SL and TP are both touched in one candle",
                "costs": "gross MT5 order_calc_profit values; commission and swap not included",
                "portfolio_mode": "combined account accepts one open trade at a time to avoid overestimating small-account margin capacity",
            },
            "diagnostics": diagnostics,
            "symbols": symbol_summaries,
            "portfolio": portfolio,
            "trades_by_symbol": {
                symbol: [
                    asdict(trade)
                    | {
                        "signal_time_iso": iso_time(trade.signal_time),
                        "entry_time_iso": iso_time(trade.entry_time),
                        "exit_time_iso": iso_time(trade.exit_time),
                    }
                    for trade in trades
                ]
                for symbol, trades in trades_by_symbol.items()
            },
        }


def write_reports(root: Path, result: dict[str, Any]) -> tuple[Path, Path]:
    report_dir = root / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = report_dir / f"backtest_{stamp}.json"
    csv_path = report_dir / f"backtest_trades_{stamp}.csv"
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    rows: list[dict[str, Any]] = []
    for trades in result["trades_by_symbol"].values():
        rows.extend(trades)
    rows.sort(key=lambda item: (item["entry_time"], item["symbol"]))
    fields = [
        "symbol",
        "broker_symbol",
        "setup",
        "side",
        "signal_time_iso",
        "entry_time_iso",
        "exit_time_iso",
        "entry",
        "sl",
        "tp",
        "lot",
        "pnl",
        "result",
        "rr",
        "margin",
        "reason",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return json_path, csv_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Backtest the H4 box bot on MT5 history.")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--start-balance", type=float, default=300.0)
    parser.add_argument("--years", type=float, default=1.0)
    parser.add_argument("--start", default=None, help="UTC date, e.g. 2025-06-17")
    parser.add_argument("--end", default=None, help="UTC date, e.g. 2026-06-17")
    parser.add_argument("--summary-only", action="store_true", help="Print compact summary while still saving full reports.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = root / config_path
    config = load_json(config_path)

    end = datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc) if args.end else utc_now()
    start = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc) if args.start else end - timedelta(days=365 * args.years)

    tester = BoxBacktester(root, config, args.start_balance)
    tester.connect()
    try:
        result = tester.run(start, end)
    finally:
        tester.shutdown()
    json_path, csv_path = write_reports(root, result)
    result["report_files"] = {"json": str(json_path), "csv": str(csv_path)}
    if args.summary_only:
        compact = dict(result)
        compact.pop("trades_by_symbol", None)
        compact["portfolio"] = dict(compact["portfolio"])
        compact["portfolio"].pop("accepted_trades", None)
        print(json.dumps(compact, indent=2))
    else:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
