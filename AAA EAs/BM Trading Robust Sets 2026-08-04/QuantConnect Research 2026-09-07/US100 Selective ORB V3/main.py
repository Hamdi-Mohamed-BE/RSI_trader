from AlgorithmImports import *
from collections import defaultdict, deque
from datetime import datetime, time, timedelta
from statistics import median
import math


class Us100SelectiveOrbV3(QCAlgorithm):
    """QuantConnect port of the locked Calyx US100 Selective ORB V3 preset."""

    RISK_FRACTION = 0.01
    OPENING_RANGE_MINUTES = 30
    BASELINE_DAYS = 20
    MIN_OPENING_RELATIVE_VOLUME = 0.60
    MIN_RANGE_DAILY_ATR = 0.05
    MAX_RANGE_DAILY_ATR = 0.35
    MIN_BREAKOUT_RELATIVE_VOLUME = 0.90
    MIN_BREAKOUT_BODY = 0.75
    BREAKOUT_BUFFER_DAILY_ATR = 0.015
    MAX_RETEST_BARS = 3
    RETEST_TOLERANCE_RANGE = 0.25
    MAX_PRE_RETEST_EXCURSION_RANGE = 0.60
    STOP_BUFFER_RANGE = 0.05
    MAX_STOP_DAILY_ATR = 0.80
    REWARD_RISK = 2.0
    BREAK_EVEN_AT_R = 1.0
    MAX_SPREAD_RANGE_FRACTION = 0.10

    def initialize(self):
        self.set_start_date(2020, 1, 1)
        self.set_end_date(2026, 9, 6)
        self.set_cash(100000)
        self.set_time_zone(TimeZones.NEW_YORK)
        self.set_brokerage_model(BrokerageName.INTERACTIVE_BROKERS_BROKERAGE, AccountType.MARGIN)

        # MNQ is used instead of a CFD so the volume gates use centralized CME
        # traded volume. Signals use the continuous series; orders use its
        # currently mapped, tradable front contract.
        self.future = self.add_future(
            Futures.Indices.MICRO_NASDAQ_100_E_MINI,
            Resolution.MINUTE,
            extended_market_hours=True,
            data_mapping_mode=DataMappingMode.OPEN_INTEREST,
            data_normalization_mode=DataNormalizationMode.BACKWARDS_PANAMA_CANAL,
            contract_depth_offset=0,
        )
        self.future.set_filter(0, 180)
        self.signal_symbol = self.future.symbol

        self.true_ranges = deque(maxlen=80)
        self.opening_volumes = deque(maxlen=80)
        self.clock_volumes = defaultdict(lambda: deque(maxlen=80))
        self.previous_rth_close = None

        self.session_date = None
        self.rth_high = None
        self.rth_low = None
        self.rth_close = None
        self.range_high = None
        self.range_low = None
        self.range_volume = 0.0
        self.range_width = 0.0
        self.daily_atr = 0.0
        self.range_ready = False
        self.range_attempted = False
        self.traded_today = False
        self.breakout_direction = 0
        self.breakout_age = 0
        self.session_vwap_numerator = 0.0
        self.session_vwap_volume = 0.0

        self.m5_key = None
        self.m5_minutes = []
        self.entry_order_id = None
        self.stop_ticket = None
        self.target_ticket = None
        self.pending_entry = None
        self.entry_price = None
        self.initial_risk = None
        self.position_direction = 0
        self.current_stop = None

        self.diag = defaultdict(int)

        self.set_warm_up(timedelta(days=45), Resolution.MINUTE)
        self.set_benchmark(lambda _: 0)

    def on_data(self, data):
        bar = data.bars.get(self.signal_symbol)
        if bar is None:
            return

        bar_start = bar.time
        current_date = bar_start.date()
        if self.session_date != current_date:
            self._start_session(current_date)

        self._roll_m5(bar)
        clock = bar_start.time()

        if time(9, 30) <= clock < time(16, 0):
            self.rth_high = bar.high if self.rth_high is None else max(self.rth_high, bar.high)
            self.rth_low = bar.low if self.rth_low is None else min(self.rth_low, bar.low)
            self.rth_close = bar.close

        if time(9, 30) <= clock < time(15, 55):
            volume = float(bar.volume)
            typical = (bar.high + bar.low + bar.close) / 3.0
            self.session_vwap_numerator += typical * volume
            self.session_vwap_volume += volume

        if time(9, 30) <= clock < time(10, 0):
            self.range_high = bar.high if self.range_high is None else max(self.range_high, bar.high)
            self.range_low = bar.low if self.range_low is None else min(self.range_low, bar.low)
            self.range_volume += float(bar.volume)

        if clock >= time(10, 0) and not self.range_attempted:
            self.range_attempted = True
            self._finalize_opening_range()

        if clock >= time(15, 55):
            self._flatten_end_of_day()

    def _start_session(self, current_date):
        if self.session_date is not None:
            self._finalize_prior_session()
        self.session_date = current_date
        self.rth_high = self.rth_low = self.rth_close = None
        self.range_high = self.range_low = None
        self.range_volume = 0.0
        self.range_width = 0.0
        self.daily_atr = 0.0
        self.range_ready = False
        self.range_attempted = False
        self.traded_today = False
        self.breakout_direction = 0
        self.breakout_age = 0
        self.session_vwap_numerator = 0.0
        self.session_vwap_volume = 0.0

    def _finalize_prior_session(self):
        if self.rth_high is None or self.rth_low is None or self.rth_close is None:
            return
        if self.previous_rth_close is not None:
            true_range = max(
                self.rth_high - self.rth_low,
                abs(self.rth_high - self.previous_rth_close),
                abs(self.rth_low - self.previous_rth_close),
            )
            if true_range > 0:
                self.true_ranges.append(true_range)
        self.previous_rth_close = self.rth_close

    def _finalize_opening_range(self):
        self.diag["range_attempts"] += 1
        if self.range_high is None or self.range_low is None or self.range_volume <= 0:
            self.diag["range_missing"] += 1
            return
        if len(self.true_ranges) < self.BASELINE_DAYS or len(self.opening_volumes) < self.BASELINE_DAYS:
            self.diag["range_warmup"] += 1
            self.opening_volumes.append(self.range_volume)
            return
        self.daily_atr = median(list(self.true_ranges)[-self.BASELINE_DAYS:])
        baseline_volume = median(list(self.opening_volumes)[-self.BASELINE_DAYS:])
        self.opening_volumes.append(self.range_volume)
        if self.daily_atr <= 0 or baseline_volume <= 0:
            self.diag["range_bad_baseline"] += 1
            return
        self.range_width = self.range_high - self.range_low
        relative_volume = self.range_volume / baseline_volume
        normalized_range = self.range_width / self.daily_atr
        self.range_ready = (
            self.range_width > 0
            and relative_volume >= self.MIN_OPENING_RELATIVE_VOLUME
            and self.MIN_RANGE_DAILY_ATR <= normalized_range <= self.MAX_RANGE_DAILY_ATR
        )
        self.diag["range_ready" if self.range_ready else "range_rejected"] += 1

    def _roll_m5(self, minute_bar):
        key = minute_bar.time.replace(minute=(minute_bar.time.minute // 5) * 5, second=0, microsecond=0)
        if self.m5_key is None:
            self.m5_key = key
        if key != self.m5_key:
            completed = self._combine_minutes(self.m5_key, self.m5_minutes)
            self.m5_key = key
            self.m5_minutes = []
            if completed is not None:
                self._on_m5(completed)
        self.m5_minutes.append(minute_bar)

    @staticmethod
    def _combine_minutes(start, bars):
        if not bars:
            return None
        return {
            "start": start,
            "end": start + timedelta(minutes=5),
            "open": bars[0].open,
            "high": max(bar.high for bar in bars),
            "low": min(bar.low for bar in bars),
            "close": bars[-1].close,
            "volume": sum(float(bar.volume) for bar in bars),
        }

    def _on_m5(self, bar):
        clock_key = (bar["start"].hour, bar["start"].minute)
        history = self.clock_volumes[clock_key]

        if self.is_warming_up:
            history.append(bar["volume"])
            return

        if self.portfolio.invested:
            self._manage_break_even(bar)

        eligible = (
            self.range_ready
            and not self.traded_today
            and not self.portfolio.invested
            and self.entry_order_id is None
            and bar["start"].weekday() < 5
            and time(10, 0) <= bar["start"].time() < time(11, 30)
            and len(history) >= self.BASELINE_DAYS
        )
        if eligible:
            self.diag["eligible_m5"] += 1
            self._evaluate_signal(bar, median(list(history)[-self.BASELINE_DAYS:]))

        history.append(bar["volume"])

    def _evaluate_signal(self, bar, volume_baseline):
        if self.breakout_direction != 0:
            self.diag["retest_bars"] += 1
            self.breakout_age += 1
            direction = self.breakout_direction
            excursion = bar["high"] - self.range_high if direction > 0 else self.range_low - bar["low"]
            if self.breakout_age > self.MAX_RETEST_BARS or excursion > self.MAX_PRE_RETEST_EXCURSION_RANGE * self.range_width:
                self.breakout_direction = 0
                return
            tolerance = self.RETEST_TOLERANCE_RANGE * self.range_width
            accepted = (
                bar["low"] <= self.range_high + tolerance
                and bar["close"] >= self.range_high
                and bar["close"] > bar["open"]
            ) if direction > 0 else (
                bar["high"] >= self.range_low - tolerance
                and bar["close"] <= self.range_low
                and bar["close"] < bar["open"]
            )
            if accepted and self._time_direction_allowed(direction, bar["end"].time()):
                self.diag["retest_accepted"] += 1
                self.breakout_direction = 0
                self._enter(direction, bar["close"])
            return

        candle_range = bar["high"] - bar["low"]
        if candle_range <= 0:
            return
        if abs(bar["close"] - bar["open"]) / candle_range < self.MIN_BREAKOUT_BODY:
            self.diag["body_rejected"] += 1
            return
        if volume_baseline <= 0 or bar["volume"] / volume_baseline < self.MIN_BREAKOUT_RELATIVE_VOLUME:
            self.diag["volume_rejected"] += 1
            return

        buffer_value = self.BREAKOUT_BUFFER_DAILY_ATR * self.daily_atr
        direction = 0
        if bar["close"] > self.range_high + buffer_value and bar["close"] > bar["open"]:
            direction = 1
        elif bar["close"] < self.range_low - buffer_value and bar["close"] < bar["open"]:
            direction = -1
        if direction == 0 or not self._time_direction_allowed(direction, bar["end"].time()):
            self.diag["price_or_direction_rejected"] += 1
            return

        if self.session_vwap_volume <= 0:
            self.diag["vwap_missing"] += 1
            return
        vwap = self.session_vwap_numerator / self.session_vwap_volume
        if (direction > 0 and bar["close"] <= vwap) or (direction < 0 and bar["close"] >= vwap):
            self.diag["vwap_rejected"] += 1
            return
        self.diag["breakouts"] += 1
        self.breakout_direction = direction
        self.breakout_age = 0

    @staticmethod
    def _time_direction_allowed(direction, current_time):
        minutes = current_time.hour * 60 + current_time.minute
        if minutes < 10 * 60 + 30:
            return True
        if minutes < 11 * 60:
            return direction > 0
        return direction < 0

    def _spread_acceptable(self, security):
        if self.range_width <= 0:
            return False
        bid, ask = float(security.bid_price), float(security.ask_price)
        return bid <= 0 or ask <= bid or (ask - bid) / self.range_width <= self.MAX_SPREAD_RANGE_FRACTION

    def _enter(self, direction, signal_price):
        self.diag["entry_attempts"] += 1
        contract = self.future.mapped
        if contract is None or contract not in self.securities:
            self.diag["contract_missing"] += 1
            return
        security = self.securities[contract]
        if not self._spread_acceptable(security):
            self.diag["spread_rejected"] += 1
            return
        entry = float(security.ask_price if direction > 0 else security.bid_price)
        if entry <= 0:
            entry = float(security.price)
        # The continuous signal series is backwards-adjusted while the mapped
        # order contract is raw. Transfer the distance, never the absolute
        # continuous-series stop price, across the roll adjustment.
        signal_stop = self.range_low - self.STOP_BUFFER_RANGE * self.range_width if direction > 0 else self.range_high + self.STOP_BUFFER_RANGE * self.range_width
        risk_distance = signal_price - signal_stop if direction > 0 else signal_stop - signal_price
        if risk_distance <= 0 or risk_distance > self.MAX_STOP_DAILY_ATR * self.daily_atr:
            self.diag["stop_rejected"] += 1
            return
        multiplier = float(security.symbol_properties.contract_multiplier)
        risk_budget = float(self.portfolio.total_portfolio_value) * self.RISK_FRACTION
        quantity = int(math.floor(risk_budget / (risk_distance * multiplier)))
        if quantity < 1:
            self.diag["size_rejected"] += 1
            self.debug(f"Risk-safe skip: one MNQ contract exceeds 1% risk at {risk_distance:.2f} points")
            return

        self.pending_entry = {"direction": direction, "risk": risk_distance}
        ticket = self.market_order(contract, direction * quantity, asynchronous=True, tag="US100 Selective ORB V3")
        self.entry_order_id = ticket.order_id
        self.traded_today = True
        self.diag["orders_submitted"] += 1

    def on_end_of_algorithm(self):
        summary = ", ".join(f"{key}={self.diag[key]}" for key in sorted(self.diag))
        self.debug(f"ORB_DIAGNOSTICS {summary}")

    def on_order_event(self, event):
        if event.status != OrderStatus.FILLED:
            return
        if self.stop_ticket and event.order_id == self.stop_ticket.order_id:
            if self.target_ticket:
                self.target_ticket.cancel("OCO sibling filled")
            self._clear_position_state()
            return
        if self.target_ticket and event.order_id == self.target_ticket.order_id:
            if self.stop_ticket:
                self.stop_ticket.cancel("OCO sibling filled")
            self._clear_position_state()
            return
        if self.pending_entry is not None and self.stop_ticket is None and self.target_ticket is None:
            direction = self.pending_entry["direction"]
            risk_distance = self.pending_entry["risk"]
            quantity = abs(event.fill_quantity)
            self.entry_price = event.fill_price
            self.initial_risk = risk_distance
            self.position_direction = direction
            stop = self.entry_price - direction * risk_distance
            target = self.entry_price + direction * risk_distance * self.REWARD_RISK
            self.current_stop = stop
            exit_quantity = -direction * quantity
            self.stop_ticket = self.stop_market_order(event.symbol, exit_quantity, stop, tag="ORB -1R")
            self.target_ticket = self.limit_order(event.symbol, exit_quantity, target, tag="ORB +2R")
            self.entry_order_id = None

    def _manage_break_even(self, bar):
        if not self.stop_ticket or self.entry_price is None or self.initial_risk is None:
            return
        favorable = bar["high"] - self.entry_price if self.position_direction > 0 else self.entry_price - bar["low"]
        if favorable < self.BREAK_EVEN_AT_R * self.initial_risk:
            return
        if self.current_stop is not None and (
            (self.position_direction > 0 and self.current_stop >= self.entry_price)
            or (self.position_direction < 0 and self.current_stop <= self.entry_price)
        ):
            return
        fields = UpdateOrderFields()
        fields.stop_price = self.entry_price
        fields.tag = "ORB break-even"
        response = self.stop_ticket.update(fields)
        if response.is_success:
            self.current_stop = self.entry_price

    def _flatten_end_of_day(self):
        if not self.portfolio.invested:
            return
        contract = self.future.mapped
        if contract is None:
            return
        self.transactions.cancel_open_orders(contract, "15:55 New York flat")
        self.liquidate(contract, "15:55 New York flat")
        self._clear_position_state()

    def on_symbol_changed_events(self, events):
        event = events.get(self.signal_symbol)
        if event is None or not self.portfolio[event.old_symbol].invested:
            return
        self.transactions.cancel_open_orders(event.old_symbol, "Contract rollover")
        self.liquidate(event.old_symbol, "Contract rollover")
        self._clear_position_state()

    def _clear_position_state(self):
        self.stop_ticket = None
        self.target_ticket = None
        self.pending_entry = None
        self.entry_order_id = None
        self.entry_price = None
        self.initial_risk = None
        self.position_direction = 0
        self.current_stop = None
