from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from typing import Iterable

import numpy as np
import pandas as pd

from .config import Config
from .models import Skip, Trade
from .normalization import PriceNormalizer
from .risk import position_volume
from .sessions import NY, is_trading_day


def _window(day: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    clock = day["ny_time"]
    return day[(clock >= start) & (clock < end)]


def prepare_m1(raw: pd.DataFrame, norm: PriceNormalizer) -> pd.DataFrame:
    df = raw.copy()
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df["ny_dt"] = df["time"].dt.tz_convert(NY)
    df["ny_date"] = df["ny_dt"].dt.date
    df["ny_time"] = df["ny_dt"].dt.strftime("%H:%M")
    df["spread_price"] = df["spread"].astype(float) * norm.spec.point
    return df


def _aggregate(candles: pd.DataFrame) -> dict[str, float] | None:
    if candles.empty:
        return None
    return {
        "open": float(candles.iloc[0]["open"]),
        "high": float(candles["high"].max()),
        "low": float(candles["low"].min()),
        "close": float(candles.iloc[-1]["close"]),
    }


def _exit_trade(
    trade: Trade,
    row: pd.Series,
    price: float,
    reason: str,
    norm: PriceNormalizer,
    commission_per_lot: float,
) -> Trade:
    trade.exit_time = row["time"].to_pydatetime()
    trade.exit = norm.round_price(price)
    gross = norm.money_for_move(trade.volume, trade.entry - trade.exit)
    commission = commission_per_lot * trade.volume
    trade.pnl = gross - commission
    trade.exit_reason = reason
    return trade


def simulate_short(
    day: pd.DataFrame,
    start_pos: int,
    entry: float,
    stop: float,
    target: float | None,
    volume: float,
    risk_cash: float,
    strategy: str,
    norm: PriceNormalizer,
    cfg: Config,
    force_exit_clock: str,
    trail_method: str = "",
    trail_buffer: float = 0.0,
    break_even_r: float = 0.0,
) -> Trade:
    row0 = day.iloc[start_pos]
    trade = Trade(
        strategy=strategy,
        side="SELL",
        entry_time=row0["time"].to_pydatetime(),
        entry=norm.round_price(entry),
        stop=norm.round_price(stop),
        target=None if target is None else norm.round_price(target),
        volume=volume,
        risk_cash=risk_cash,
        spread_cost=float(row0["spread_price"]) / norm.spec.tick_size * norm.spec.tick_value * volume,
        slippage_cost=cfg.slippage_pips * norm.risk_per_lot(1) * volume,
    )
    initial_risk = stop - entry
    highs: list[float] = []
    last_boundary = None
    end = day[day["ny_time"] <= force_exit_clock]
    end_pos = int(end.index[-1]) if not end.empty else int(day.index[-1])
    # day has its original index; iterate using iloc positions.
    for pos in range(start_pos, len(day)):
        row = day.iloc[pos]
        if row["ny_time"] > force_exit_clock:
            break
        ask_high = float(row["high"] + row["spread_price"])
        ask_low = float(row["low"] + row["spread_price"])
        ask_close = float(row["close"] + row["spread_price"])
        trade.mae = max(trade.mae, max(0.0, ask_high - trade.entry))
        trade.mfe = max(trade.mfe, max(0.0, trade.entry - ask_low))

        # Update trailing only at the start of a new quarter hour, based on closed data.
        minute = row["ny_dt"].minute
        boundary = row["ny_dt"].floor("15min")
        if trail_method and minute % 15 == 0 and boundary != last_boundary:
            closed = day[
                (day["ny_dt"] >= boundary - pd.Timedelta(minutes=30))
                & (day["ny_dt"] < boundary)
            ]
            recent = closed[closed["ny_dt"] >= boundary - pd.Timedelta(minutes=15)]
            previous_two = closed
            candidate = None
            if trail_method == "previous_m15" and not recent.empty:
                candidate = float((recent["high"] + recent["spread_price"]).max()) + trail_buffer
            elif trail_method == "previous_two_m15" and not previous_two.empty:
                candidate = float(
                    (previous_two["high"] + previous_two["spread_price"]).max()
                ) + trail_buffer
            elif trail_method == "atr" and not previous_two.empty:
                tr = float((previous_two["high"] - previous_two["low"]).mean())
                candidate = ask_close + 1.5 * tr + trail_buffer
            if candidate is not None and ask_close < candidate < trade.stop:
                trade.stop = norm.round_price(candidate)
            last_boundary = boundary

        if break_even_r > 0 and trade.mfe >= initial_risk * break_even_r:
            be = trade.entry
            if ask_close < be < trade.stop:
                trade.stop = norm.round_price(be)

        # Pessimistic same-minute ordering: stop before target.
        if ask_high >= trade.stop:
            return _exit_trade(
                trade,
                row,
                trade.stop + cfg.slippage_pips * cfg.pip_size,
                "stop",
                norm,
                cfg.commission_per_lot,
            )
        if trade.target is not None and ask_low <= trade.target:
            return _exit_trade(
                trade,
                row,
                trade.target + cfg.slippage_pips * cfg.pip_size,
                "target",
                norm,
                cfg.commission_per_lot,
            )
    row = day.iloc[-1] if day.empty else day[day["ny_time"] <= force_exit_clock].iloc[-1]
    return _exit_trade(
        trade,
        row,
        float(row["close"] + row["spread_price"] + cfg.slippage_pips * cfg.pip_size),
        "time_exit",
        norm,
        cfg.commission_per_lot,
    )


class Backtest:
    def __init__(self, cfg: Config, norm: PriceNormalizer):
        self.cfg = cfg
        self.norm = norm

    def run(
        self,
        raw: pd.DataFrame,
        strategies: Iterable[str] = ("A_FIXED", "A_RUNNER", "B1", "B2"),
    ) -> tuple[list[Trade], list[Skip]]:
        wanted = set(strategies)
        data = prepare_m1(raw, self.norm)
        trades: list[Trade] = []
        skips: list[Skip] = []
        equity = self.cfg.starting_balance
        for ny_day, day in data.groupby("ny_date", sort=True):
            day = day.reset_index(drop=True)
            valid, reason = is_trading_day(ny_day)
            if not valid:
                for s in wanted:
                    skips.append(Skip(str(ny_day), s, reason))
                continue
            if self.cfg.friday_filter and ny_day.weekday() == 4:
                for s in wanted:
                    skips.append(Skip(str(ny_day), s, "Friday filter"))
                continue
            day_trades: list[Trade] = []
            if self.cfg.strategy_a_enabled and {"A_FIXED", "A_RUNNER"} & wanted:
                new, new_skips = self._strategy_a(day, equity, wanted)
                day_trades.extend(new)
                skips.extend(new_skips)
            if self.cfg.strategy_b_enabled and {"B1", "B2"} & wanted:
                new, new_skips = self._strategy_b(day, equity, wanted)
                day_trades.extend(new)
                skips.extend(new_skips)
            day_trades.sort(key=lambda t: t.entry_time)
            # Account compounding is chronological at realized exits.
            for trade in sorted(day_trades, key=lambda t: t.exit_time or t.entry_time):
                equity += trade.pnl
            trades.extend(day_trades)
        return sorted(trades, key=lambda t: t.entry_time), skips

    def _spread_ok(self, row: pd.Series) -> bool:
        return float(row["spread_price"]) / self.cfg.pip_size <= self.cfg.max_spread_pips

    def _strategy_a(
        self, day: pd.DataFrame, equity: float, wanted: set[str]
    ) -> tuple[list[Trade], list[Skip]]:
        date_text = str(day.iloc[0]["ny_date"])
        at_open = day[day["ny_time"] >= self.cfg.ny_open.strftime("%H:%M")]
        at_open = at_open[at_open["ny_time"] <= "09:35"]
        if at_open.empty:
            return [], [Skip(date_text, "A", "no valid 09:30 tick")]
        pos = int(at_open.index[0])
        row = day.iloc[pos]
        if not self._spread_ok(row):
            return [], [Skip(date_text, "A", "spread filter")]
        entry = float(row["open"]) - self.cfg.slippage_pips * self.cfg.pip_size
        stop = entry + self.norm.pips_to_price(self.cfg.a_stop_pips)
        volume, risk = position_volume(
            self.cfg, self.norm, equity, self.cfg.a_stop_pips, risk_fraction=0.5
        )
        result: list[Trade] = []
        if "A_FIXED" in wanted:
            target = entry - self.norm.pips_to_price(self.cfg.a_target_pips)
            result.append(
                simulate_short(
                    day,
                    pos,
                    entry,
                    stop,
                    target,
                    volume,
                    risk,
                    "A_FIXED",
                    self.norm,
                    self.cfg,
                    self.cfg.a_force_exit.strftime("%H:%M"),
                )
            )
        if "A_RUNNER" in wanted:
            result.append(
                simulate_short(
                    day,
                    pos,
                    entry,
                    stop,
                    None,
                    volume,
                    risk,
                    "A_RUNNER",
                    self.norm,
                    self.cfg,
                    self.cfg.a_force_exit.strftime("%H:%M"),
                    trail_method=self.cfg.a_runner_method,
                    trail_buffer=self.norm.pips_to_price(self.cfg.a_trail_buffer_pips),
                    break_even_r=self.cfg.a_break_even_r,
                )
            )
        return result, []

    def _strategy_b(
        self, day: pd.DataFrame, equity: float, wanted: set[str]
    ) -> tuple[list[Trade], list[Skip]]:
        date_text = str(day.iloc[0]["ny_date"])
        second = _window(
            day,
            self.cfg.second_start.strftime("%H:%M"),
            self.cfg.second_end.strftime("%H:%M"),
        )
        candle = _aggregate(second)
        if candle is None or len(second) < 10:
            return [], [Skip(date_text, "B", "missing second M15 candle")]
        body_pips = abs(candle["close"] - candle["open"]) / self.cfg.pip_size
        if body_pips < self.cfg.doji_body_pips:
            return [], [Skip(date_text, "B", "doji/body filter")]
        after = day[day["ny_time"] >= self.cfg.second_end.strftime("%H:%M")]
        if after.empty:
            return [], [Skip(date_text, "B", "no 10:00 tick")]
        pos = int(after.index[0])
        row = day.iloc[pos]
        if not self._spread_ok(row):
            return [], [Skip(date_text, "B", "spread filter")]
        if candle["close"] > candle["open"]:
            if not self.cfg.b1_enabled:
                return [], [Skip(date_text, "B1", "disabled")]
            if "B1" not in wanted:
                return [], []
            return self._b1(day, pos, candle, equity)
        if not self.cfg.b2_enabled:
            return [], [Skip(date_text, "B2", "disabled")]
        if "B2" not in wanted:
            return [], []
        return self._b2(day, pos, candle, equity)

    def _b1(
        self, day: pd.DataFrame, pos: int, candle: dict[str, float], equity: float
    ) -> tuple[list[Trade], list[Skip]]:
        date_text = str(day.iloc[0]["ny_date"])
        ref = self.cfg.b1_stop_reference
        if ref == "second_candle_high":
            high = candle["high"]
        elif ref == "reference_candle_high":
            c = _aggregate(_window(day, "09:15", "09:30"))
            high = c["high"] if c else np.nan
        elif ref == "latest_london_m15":
            c = _aggregate(_window(day, "09:30", "09:45"))
            high = c["high"] if c else np.nan
        else:
            london = _window(
                day, self.cfg.london_start.strftime("%H:%M"), self.cfg.second_end.strftime("%H:%M")
            )
            high = float(london["high"].max()) if not london.empty else np.nan
        entry = float(day.iloc[pos]["open"]) - self.cfg.slippage_pips * self.cfg.pip_size
        stop = high + self.norm.pips_to_price(self.cfg.b1_stop_buffer_pips)
        stop_pips = (stop - entry) / self.cfg.pip_size
        if not np.isfinite(stop_pips) or not (
            self.cfg.min_stop_pips <= stop_pips <= self.cfg.max_stop_pips
        ):
            return [], [Skip(date_text, "B1", f"invalid stop {stop_pips:.1f} pips")]
        volume, risk = position_volume(self.cfg, self.norm, equity, stop_pips)
        target = entry - (stop - entry) * self.cfg.b1_rr
        return [
            simulate_short(
                day,
                pos,
                entry,
                stop,
                target,
                volume,
                risk,
                "B1",
                self.norm,
                self.cfg,
                self.cfg.a_force_exit.strftime("%H:%M"),
            )
        ], []

    def _b2(
        self, day: pd.DataFrame, pos: int, candle: dict[str, float], equity: float
    ) -> tuple[list[Trade], list[Skip]]:
        date_text = str(day.iloc[0]["ny_date"])
        mode = self.cfg.b2_pullback_mode
        if mode == "candle_midpoint":
            pending = (candle["high"] + candle["low"]) / 2
        elif mode == "reference_midpoint":
            c = _aggregate(_window(day, "09:15", "09:30"))
            pending = (c["high"] + c["low"]) / 2 if c else np.nan
        elif mode == "candle_50pct":
            pending = candle["low"] + 0.5 * (candle["high"] - candle["low"])
        else:
            pending = candle["close"] + self.norm.pips_to_price(self.cfg.b2_entry_pips)
        stop = pending + self.norm.pips_to_price(self.cfg.b2_stop_pips)
        target = pending - self.norm.pips_to_price(self.cfg.b2_stop_pips * self.cfg.b2_rr)
        expiry = self.cfg.b2_expiry.strftime("%H:%M")
        future = day.iloc[pos:]
        future = future[future["ny_time"] <= expiry]
        for idx, row in future.iterrows():
            if float(row["high"]) >= stop:
                return [], [Skip(date_text, "B2", "structure invalidated before fill")]
            if float(row["high"]) >= pending:
                volume, risk = position_volume(
                    self.cfg, self.norm, equity, self.cfg.b2_stop_pips
                )
                trade = simulate_short(
                    day,
                    int(idx),
                    pending - self.cfg.slippage_pips * self.cfg.pip_size,
                    stop,
                    target,
                    volume,
                    risk,
                    "B2",
                    self.norm,
                    self.cfg,
                    self.cfg.a_force_exit.strftime("%H:%M"),
                )
                trade.metadata["pending_minutes"] = (
                    trade.entry_time - day.iloc[pos]["time"].to_pydatetime()
                ).total_seconds() / 60
                return [trade], []
        return [], [Skip(date_text, "B2", "pending order expired")]


def evolve(cfg: Config, **changes: object) -> Config:
    return replace(cfg, **changes)
