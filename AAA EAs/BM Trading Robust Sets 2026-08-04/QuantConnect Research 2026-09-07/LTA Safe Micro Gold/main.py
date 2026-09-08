from AlgorithmImports import *
from collections import deque
from datetime import timedelta
import math


class LtaSafeMicroGold(QCAlgorithm):
    """QuantConnect port of the current locked LTA Safe XAU configuration.

    Signal data comes from the continuous Micro Gold future. Orders are sent to
    the mapped front contract. The strategy intentionally preserves the MT5
    rules instead of adding new optimisation conditions during the migration.
    """

    RISK_FRACTION = 0.01
    REWARD_RISK = 3.0
    PROFILE_BINS = 64
    VALUE_AREA = 0.70
    KEY_BUFFER_ATR = 0.24
    SL_BUFFER_ATR = 0.12
    MITIGATION_BARS = 5
    ZONE_LOOKBACK = 220
    BASE_BARS = 3
    ZONE_BREAK_LOOKBACK = 18
    BASE_MAX_RANGE_ATR = 1.20
    EXPANSION_MIN_BODY_ATR = 0.75
    EXPANSION_MIN_RANGE_ATR = 1.15
    EXPANSION_VOLUME_MULT = 1.05
    ZONE_EXPIRY_BARS = 160
    MIN_WICK_RATIO = 0.25
    MIN_CONFIRM_VOLUME_MULT = 1.0
    MARKOV_WINDOW = 40
    MARKOV_THRESHOLD = 0.05
    MARKOV_SIGNAL_GATE = 0.05
    MARKOV_MIN_LABELS = 252
    MAX_CONSECUTIVE_LOSSES = 2

    def initialize(self):
        self.set_start_date(2025, 9, 7)
        self.set_end_date(2026, 9, 6)
        self.set_cash(100000)
        self.set_time_zone(TimeZones.UTC)

        self.future = self.add_future(
            Futures.Metals.MICRO_GOLD,
            Resolution.MINUTE,
            extended_market_hours=True,
            data_mapping_mode=DataMappingMode.OPEN_INTEREST,
            data_normalization_mode=DataNormalizationMode.BACKWARDS_PANAMA_CANAL,
            contract_depth_offset=0,
        )
        self.future.set_filter(0, 180)
        self.signal_symbol = self.future.symbol

        self.m15 = deque(maxlen=15 * 24 * 4)
        self.h1 = deque(maxlen=300)
        self.h4 = deque(maxlen=260)
        self.daily_rows = []
        self.daily_cache_date = None

        # Register the higher-timeframe consolidators first so their newly
        # completed bars are available when the M15 signal handler runs at a
        # shared boundary.
        self.consolidate(self.signal_symbol, timedelta(hours=4), self._on_h4)
        self.consolidate(self.signal_symbol, timedelta(hours=1), self._on_h1)
        self.consolidate(self.signal_symbol, timedelta(minutes=15), self._on_m15)

        # MT5 starts with broker history already loaded. Seed the equivalent
        # M15/H1/H4 state before permitting QuantConnect orders, including the
        # full 220-bar H4 supply/demand-zone lookback.
        self.set_warm_up(timedelta(days=70), Resolution.MINUTE)

        self.entry_order_id = None
        self.stop_ticket = None
        self.target_ticket = None
        self.pending_signal = None
        self.last_trade_bar = None
        self.loss_date = None
        self.consecutive_losses = 0
        self.set_benchmark(lambda _: 0)

    def _on_h1(self, bar):
        self.h1.append(bar)

    def _on_h4(self, bar):
        self.h4.append(bar)

    def _on_m15(self, bar):
        self.m15.append(bar)
        self._reset_daily_loss_gate()

        if self.is_warming_up:
            return

        self._refresh_daily_rows()

        if len(self.m15) < 25 or len(self.h1) < 55 or len(self.h4) < 40:
            return
        if self.portfolio.invested or self.entry_order_id is not None:
            return
        if self.consecutive_losses >= self.MAX_CONSECUTIVE_LOSSES:
            return
        if self.last_trade_bar == bar.end_time:
            return

        macro = self._trend(self.daily_rows)
        structure = self._trend(list(self.h1))
        if macro == 0:
            macro = structure

        for direction in (1, -1):
            # Locked EA is momentum-only and uses automatic macro bias.
            if macro and direction != macro:
                continue
            if structure and direction != structure:
                continue
            if not self._safe_markov_allows(direction):
                continue

            candidate = self._candidate(direction)
            if candidate is None:
                continue

            stop, model = self._em1(direction, candidate)
            if stop is None:
                stop, model = self._em4(direction, candidate)
            if stop is None:
                continue

            entry = bar.close
            atr = self._atr(list(self.m15), 14)
            if atr <= 0:
                continue
            buffer_value = atr * self.SL_BUFFER_ATR
            if candidate["is_zone"]:
                stop = min(stop, candidate["low"] - buffer_value) if direction > 0 else max(stop, candidate["high"] + buffer_value)
            if direction > 0 and stop >= entry:
                stop = entry - atr
            if direction < 0 and stop <= entry:
                stop = entry + atr

            risk_distance = abs(entry - stop)
            if risk_distance <= 0:
                continue
            self._enter(direction, risk_distance, model, candidate["name"], bar.end_time)
            return

    def _enter(self, direction, risk_distance, model, level_name, bar_time):
        contract = self.future.mapped
        if contract is None or contract not in self.securities:
            return
        security = self.securities[contract]
        multiplier = float(security.symbol_properties.contract_multiplier)
        if multiplier <= 0:
            return
        risk_budget = float(self.portfolio.total_portfolio_value) * self.RISK_FRACTION
        quantity = int(math.floor(risk_budget / (risk_distance * multiplier)))
        if quantity < 1:
            self.debug(f"Risk-safe skip: one MGC contract exceeds 1% risk at {risk_distance:.2f} points")
            return

        self.pending_signal = {
            "direction": direction,
            "risk_distance": risk_distance,
            "tag": f"Safe LTA {model} {level_name} MOM",
        }
        # Submit asynchronously so the order id is registered before LEAN emits
        # the fill event that creates the protective OCO stop and target.
        ticket = self.market_order(
            contract,
            direction * quantity,
            asynchronous=True,
            tag=self.pending_signal["tag"],
        )
        self.entry_order_id = ticket.order_id
        self.last_trade_bar = bar_time

    def on_order_event(self, event):
        if event.status != OrderStatus.FILLED:
            return

        # Handle protective exits first. During backtests, LEAN can emit the
        # market fill before market_order returns its ticket to the caller, so
        # pending_signal is the authoritative entry marker here.
        if self.stop_ticket and event.order_id == self.stop_ticket.order_id:
            if self.target_ticket:
                self.target_ticket.cancel("OCO sibling filled")
            self._finish_trade(False)
            return
        if self.target_ticket and event.order_id == self.target_ticket.order_id:
            if self.stop_ticket:
                self.stop_ticket.cancel("OCO sibling filled")
            self._finish_trade(True)
            return

        if self.pending_signal is not None and self.stop_ticket is None and self.target_ticket is None:
            signal = self.pending_signal
            direction = signal["direction"]
            distance = signal["risk_distance"]
            quantity = abs(event.fill_quantity)
            entry = event.fill_price
            stop = entry - direction * distance
            target = entry + direction * distance * self.REWARD_RISK
            exit_quantity = -direction * quantity
            self.stop_ticket = self.stop_market_order(event.symbol, exit_quantity, stop, tag="Safe LTA -1R")
            self.target_ticket = self.limit_order(event.symbol, exit_quantity, target, tag="Safe LTA +3R")
            self.entry_order_id = None
            return

    def _finish_trade(self, won):
        self.consecutive_losses = 0 if won else self.consecutive_losses + 1
        self.stop_ticket = None
        self.target_ticket = None
        self.pending_signal = None

    def on_symbol_changed_events(self, events):
        event = events.get(self.signal_symbol)
        if event is None or not self.portfolio[event.old_symbol].invested:
            return
        rollover_was_profitable = self.portfolio[event.old_symbol].unrealized_profit >= 0
        self.transactions.cancel_open_orders(event.old_symbol, "Contract rollover")
        self.liquidate(event.old_symbol, "Contract rollover")
        # This port closes instead of carrying an intraday LTA trade across a
        # futures rollover. Do not automatically classify every rollover as a
        # strategy loss for the daily loss gate.
        self._finish_trade(rollover_was_profitable)

    def _reset_daily_loss_gate(self):
        today = self.time.date()
        if self.loss_date != today:
            self.loss_date = today
            self.consecutive_losses = 0

    def _refresh_daily_rows(self):
        today = self.time.date()
        if self.daily_cache_date == today:
            return
        self.daily_cache_date = today
        history = self.history(self.signal_symbol, 2700, Resolution.DAILY)
        rows = []
        if history is not None and not history.empty:
            frame = history.reset_index()
            for _, row in frame.iterrows():
                rows.append({
                    "time": row.get("time", row.get("index")),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]),
                })
        self.daily_rows = rows

    def _safe_markov_allows(self, direction):
        closes = [row["close"] for row in self.daily_rows]
        if len(closes) <= self.MARKOV_WINDOW + self.MARKOV_MIN_LABELS:
            return False
        states = []
        for index in range(self.MARKOV_WINDOW, len(closes)):
            value = closes[index] / closes[index - self.MARKOV_WINDOW] - 1.0
            states.append(2 if value > self.MARKOV_THRESHOLD else 0 if value < -self.MARKOV_THRESHOLD else 1)
        if len(states) <= self.MARKOV_MIN_LABELS:
            return False
        counts = [[0.0] * 3 for _ in range(3)]
        # Exclude the transition into the newest completed D1 state.
        for previous, current in zip(states[:-2], states[1:-1]):
            counts[previous][current] += 1.0
        state = states[-1]
        total = sum(counts[state])
        if total <= 0:
            return False
        signal = (counts[state][2] - counts[state][0]) / total
        return signal > self.MARKOV_SIGNAL_GATE if direction > 0 else signal < -self.MARKOV_SIGNAL_GATE

    def _candidate(self, direction):
        atr = self._atr(list(self.m15), 14)
        if atr <= 0:
            return None
        buffer_value = atr * self.KEY_BUFFER_ATR

        zone = self._recent_zone(direction)
        if zone and self._zone_mitigated(direction, zone, buffer_value):
            return zone

        for name, bars in (("PW", self._previous_week_bars()), ("PD", self._previous_day_bars())):
            profile = self._profile(bars)
            if profile is None:
                continue
            candidate = self._profile_candidate(direction, name, profile, buffer_value)
            if candidate:
                return candidate
        return None

    def _profile(self, bars):
        if len(bars) < 8:
            return None
        high = max(bar.high for bar in bars)
        low = min(bar.low for bar in bars)
        total_volume = sum(float(bar.volume) for bar in bars)
        if high <= low or total_volume <= 0:
            return None
        step = (high - low) / self.PROFILE_BINS
        volumes = [0.0] * self.PROFILE_BINS
        for bar in bars:
            first = max(0, min(self.PROFILE_BINS - 1, int(math.floor((bar.low - low) / step))))
            last = max(0, min(self.PROFILE_BINS - 1, int(math.floor((bar.high - low) / step))))
            if last < first:
                first, last = last, first
            allocation = float(bar.volume) / max(1, last - first + 1)
            for index in range(first, last + 1):
                volumes[index] += allocation
        poc_index = max(range(self.PROFILE_BINS), key=lambda index: volumes[index])
        left = right = poc_index
        cumulative = volumes[poc_index]
        target = total_volume * self.VALUE_AREA
        while cumulative < target and (left > 0 or right < self.PROFILE_BINS - 1):
            left_volume = volumes[left - 1] if left > 0 else -1
            right_volume = volumes[right + 1] if right < self.PROFILE_BINS - 1 else -1
            if right_volume > left_volume:
                right += 1
                cumulative += volumes[right]
            else:
                left -= 1
                cumulative += volumes[left]
        return {
            "poc": low + (poc_index + 0.5) * step,
            "vah": low + (right + 1.0) * step,
            "val": low + left * step,
        }

    def _profile_candidate(self, direction, prefix, profile, buffer_value):
        latest_close = self.m15[-1].close
        best = None
        for suffix in ("poc", "vah", "val"):
            price = profile[suffix]
            if not self._level_mitigated(direction, price, buffer_value):
                continue
            if direction > 0 and latest_close < price - buffer_value:
                continue
            if direction < 0 and latest_close > price + buffer_value:
                continue
            distance = abs(latest_close - price)
            if best is None or distance < best[0]:
                best = (distance, {
                    "name": f"{prefix}-{suffix.upper()}",
                    "price": price,
                    "low": price - buffer_value,
                    "high": price + buffer_value,
                    "is_zone": False,
                })
        return best[1] if best else None

    def _recent_zone(self, direction):
        bars = list(self.h4)
        if len(bars) < self.BASE_BARS + self.ZONE_BREAK_LOOKBACK + 10:
            return None
        atr = self._atr(bars, 14)
        if atr <= 0:
            return None
        average_volume = sum(float(bar.volume) for bar in bars[-20:]) / min(20, len(bars))
        newest = len(bars) - 1
        oldest = max(self.BASE_BARS + self.ZONE_BREAK_LOOKBACK, newest - self.ZONE_EXPIRY_BARS)
        for index in range(newest, oldest - 1, -1):
            expansion = bars[index]
            body = abs(expansion.close - expansion.open)
            candle_range = expansion.high - expansion.low
            bullish = expansion.close > expansion.open and body >= atr * self.EXPANSION_MIN_BODY_ATR and candle_range >= atr * self.EXPANSION_MIN_RANGE_ATR and expansion.volume >= average_volume * self.EXPANSION_VOLUME_MULT
            bearish = expansion.close < expansion.open and body >= atr * self.EXPANSION_MIN_BODY_ATR and candle_range >= atr * self.EXPANSION_MIN_RANGE_ATR and expansion.volume >= average_volume * self.EXPANSION_VOLUME_MULT
            if (direction > 0 and not bullish) or (direction < 0 and not bearish):
                continue
            base = bars[index - self.BASE_BARS:index]
            prior_start = index - self.BASE_BARS - self.ZONE_BREAK_LOOKBACK
            prior = bars[prior_start:index - self.BASE_BARS]
            if len(base) < self.BASE_BARS or len(prior) < self.ZONE_BREAK_LOOKBACK:
                continue
            zone_high = max(bar.high for bar in base)
            zone_low = min(bar.low for bar in base)
            if zone_high - zone_low > atr * self.BASE_MAX_RANGE_ATR:
                continue
            breaks = expansion.close > max(bar.high for bar in prior) or expansion.high > max(bar.high for bar in prior) if direction > 0 else expansion.close < min(bar.low for bar in prior) or expansion.low < min(bar.low for bar in prior)
            if not breaks:
                continue
            return {
                "name": "Demand(H4)" if direction > 0 else "Supply(H4)",
                "price": (zone_low + zone_high) / 2,
                "low": zone_low,
                "high": zone_high,
                "is_zone": True,
            }
        return None

    def _level_mitigated(self, direction, price, buffer_value):
        for bar in list(self.m15)[-self.MITIGATION_BARS:]:
            if bar.low <= price + buffer_value and bar.high >= price - buffer_value:
                if direction > 0 and bar.close >= price - buffer_value:
                    return True
                if direction < 0 and bar.close <= price + buffer_value:
                    return True
        return False

    def _zone_mitigated(self, direction, zone, buffer_value):
        for bar in list(self.m15)[-self.MITIGATION_BARS:]:
            touched = bar.low <= zone["high"] + buffer_value and bar.high >= zone["low"] - buffer_value
            if touched and ((direction > 0 and bar.close > zone["low"]) or (direction < 0 and bar.close < zone["high"])):
                return True
        return False

    @staticmethod
    def _touches(bar, candidate):
        return bar.low <= candidate["high"] and bar.high >= candidate["low"]

    def _volume_confirmed(self):
        bars = list(self.m15)
        if len(bars) < 22:
            return True
        average = sum(float(bar.volume) for bar in bars[-21:-1]) / 20.0
        return average <= 0 or bars[-1].volume >= average * self.MIN_CONFIRM_VOLUME_MULT

    def _em1(self, direction, candidate):
        bars = list(self.m15)
        if len(bars) < 25 or not self._volume_confirmed():
            return None, None
        a, b = bars[-1], bars[-2]
        if not (self._touches(a, candidate) or self._touches(b, candidate)):
            return None, None
        range_a = max(a.high - a.low, 1e-9)
        range_b = max(b.high - b.low, 1e-9)
        atr = self._atr(bars, 14)
        if direction > 0:
            wick = min(a.open, a.close) - a.low >= range_a * self.MIN_WICK_RATIO or min(b.open, b.close) - b.low >= range_b * self.MIN_WICK_RATIO
            flip = a.close > a.open and a.close > b.close
            return (min(a.low, b.low) - atr * self.SL_BUFFER_ATR, "EM1-DoubleWick") if wick and flip else (None, None)
        wick = a.high - max(a.open, a.close) >= range_a * self.MIN_WICK_RATIO or b.high - max(b.open, b.close) >= range_b * self.MIN_WICK_RATIO
        flip = a.close < a.open and a.close < b.close
        return (max(a.high, b.high) + atr * self.SL_BUFFER_ATR, "EM1-DoubleWick") if wick and flip else (None, None)

    def _em4(self, direction, candidate):
        bars = list(self.m15)
        if len(bars) < 25 or not self._volume_confirmed():
            return None, None
        first, second, third = bars[-3], bars[-2], bars[-1]
        if not (self._touches(first, candidate) or self._touches(second, candidate)):
            return None, None
        atr = self._atr(bars, 14)
        if direction > 0:
            flip = second.close < second.open or second.low < first.low
            confirm = third.close > third.open and third.close > max(first.high, second.high)
            return (min(first.low, second.low, third.low) - atr * self.SL_BUFFER_ATR, "EM4-Continuation") if flip and confirm else (None, None)
        flip = second.close > second.open or second.high > first.high
        confirm = third.close < third.open and third.close < min(first.low, second.low)
        return (max(first.high, second.high, third.high) + atr * self.SL_BUFFER_ATR, "EM4-Continuation") if flip and confirm else (None, None)

    def _previous_day_bars(self):
        bars = list(self.m15)
        dates = sorted({bar.end_time.date() for bar in bars if bar.end_time.date() < self.time.date()})
        return [bar for bar in bars if bar.end_time.date() == dates[-1]] if dates else []

    def _previous_week_bars(self):
        bars = list(self.m15)
        current = self.time.date().isocalendar()[:2]
        weeks = sorted({bar.end_time.date().isocalendar()[:2] for bar in bars if bar.end_time.date().isocalendar()[:2] < current})
        return [bar for bar in bars if bar.end_time.date().isocalendar()[:2] == weeks[-1]] if weeks else []

    @staticmethod
    def _atr(bars, period):
        if len(bars) < period + 1:
            return 0.0
        selected = bars[-(period + 1):]
        values = []
        for index in range(1, len(selected)):
            current, previous = selected[index], selected[index - 1]
            values.append(max(current.high - current.low, abs(current.high - previous.close), abs(current.low - previous.close)))
        return sum(values[-period:]) / period

    @staticmethod
    def _trend(rows):
        if len(rows) < 55:
            return 0
        closes = [row["close"] if isinstance(row, dict) else row.close for row in rows]
        highs = [row["high"] if isinstance(row, dict) else row.high for row in rows]
        lows = [row["low"] if isinstance(row, dict) else row.low for row in rows]
        fast = sum(closes[-20:]) / 20
        slow = sum(closes[-50:]) / 50
        recent_high, prior_high = max(highs[-10:]), max(highs[-30:-10])
        recent_low, prior_low = min(lows[-10:]), min(lows[-30:-10])
        if closes[-1] > fast > slow and recent_high >= prior_high:
            return 1
        if closes[-1] < fast < slow and recent_low <= prior_low:
            return -1
        return 1 if fast > slow else -1 if fast < slow else 0
