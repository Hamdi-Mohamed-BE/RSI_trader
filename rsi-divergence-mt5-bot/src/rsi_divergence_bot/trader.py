from __future__ import annotations

import logging
from datetime import datetime, timezone

from .config import AppConfig, SymbolConfig
from .daily_risk import resolve_daily_loss_reference_equity
from .decision import evaluate_trade_signal, resolve_trade_filters, skip_should_mark_seen
from .mt5_client import MT5Client
from .state import StateStore
from .strategy import Signal
from .strategy_modes import (
    closes_opposite_before_entry,
    is_full_position_strategy,
    is_partial_strategy,
    is_single_leg_strategy,
    tp_protection_enabled,
)
from .symbols import market_key
from .trade_geometry import invalid_market_geometry
from .trade_execution import normalized_full_volume, normalized_partial_volumes, normalized_split_lot

Outcome = str  # placed | skipped | duplicate | failed | paper
ORDER_COMMENT = "RSI auto bot"


def _field(obj, name: str, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


class TradeExecutor:
    def __init__(self, config: AppConfig, client: MT5Client, state: StateStore, logger: logging.Logger):
        self.config = config
        self.client = client
        self.state = state
        self.logger = logger

    def place_signal(self, signal: Signal) -> Outcome:
        symbol_cfg = self._symbol_cfg(signal.symbol)
        if symbol_cfg is None:
            self.logger.warning("SKIP %s unknown symbol config", signal.symbol)
            self.state.mark_seen(signal.setup_id)
            return "skipped"

        seen = self.state.is_seen(signal.setup_id)
        if seen:
            decision = evaluate_trade_signal(self.client, self.config, signal, symbol_cfg, seen=True)
            self.logger.info("SKIP %s %s", signal.symbol, decision.reason)
            return "duplicate"

        filters = resolve_trade_filters(self.config)
        if closes_opposite_before_entry(self.config.bot.strategy):
            self._close_opposite_positions(signal.symbol, signal.side)
            if self._has_bot_position_on_side(signal.symbol, signal.side):
                self.logger.info("SKIP %s single-leg pyramiding=0 same-side position open", signal.symbol)
                return "skipped"
            position_keys = None
        else:
            position_keys = self._position_market_keys() if filters.existing_position else None
        daily_loss_reference = resolve_daily_loss_reference_equity(self.client, self.state, self.config.risk)
        decision = evaluate_trade_signal(
            self.client,
            self.config,
            signal,
            symbol_cfg,
            seen=False,
            filters=filters,
            market_position_keys=position_keys,
            active_setup_count=self._active_setup_count() if filters.max_setups else None,
            day_start_balance=daily_loss_reference,
        )
        if not decision.allowed:
            self.logger.info("SKIP %s %s", signal.symbol, decision.reason)
            if decision.code == "duplicate":
                return "duplicate"
            if skip_should_mark_seen(decision.code):
                self.state.mark_seen(signal.setup_id)
            return "skipped"

        self.logger.info(
            "SIGNAL %s key=%s %s entry %.5f sl %.5f tps %s risk_usd %.2f spread_atr %.2f profile=%s dry_run=%s session=%s mode=%s",
            signal.symbol,
            signal.market_key,
            signal.side.upper(),
            signal.entry,
            signal.sl,
            [round(tp, 5) for tp in signal.tps],
            decision.risk_usd,
            decision.spread_atr,
            self.config.bot.trade_decision_profile,
            self.config.bot.dry_run,
            signal.session,
            (
                "partial"
                if is_partial_strategy(self.config.bot.strategy)
                else "full"
                if is_full_position_strategy(self.config.bot.strategy)
                else "single"
                if is_single_leg_strategy(self.config.bot.strategy)
                else "split"
            ),
        )
        if self.config.bot.dry_run:
            self.state.mark_seen(signal.setup_id)
            if is_partial_strategy(self.config.bot.strategy):
                total, _per_slice = normalized_partial_volumes(
                    self.client, signal.symbol, signal.lot_per_leg, len(signal.tps)
                )
                self.logger.info("PAPER %s would place 1 partial position vol=%s", signal.symbol, total)
            elif is_full_position_strategy(self.config.bot.strategy):
                total = normalized_full_volume(self.client, signal.symbol, signal.lot_per_leg)
                self.logger.info("PAPER %s would place 1 full position vol=%s", signal.symbol, total)
            elif is_single_leg_strategy(self.config.bot.strategy):
                lot = normalized_split_lot(self.client, signal.symbol, signal.lot_per_leg)
                self.logger.info("PAPER %s would place single-leg vol=%s", signal.symbol, lot)
            else:
                self.logger.info("PAPER %s would place %s legs", signal.symbol, len(signal.tps))
            return "paper"

        if is_partial_strategy(self.config.bot.strategy):
            return self._place_partial_signal(signal)

        if is_full_position_strategy(self.config.bot.strategy):
            return self._place_full_signal(signal)

        if is_single_leg_strategy(self.config.bot.strategy):
            return self._place_single_signal(signal)

        return self._place_split_signal(signal)

    def place_test_trade(
        self,
        symbol: str = "XAUUSD",
        side: str = "buy",
        volume: float = 0.01,
        *,
        comment: str = "RSI test trade",
    ) -> dict:
        side = side.lower()
        if side not in {"buy", "sell"}:
            return {"status": "failed", "reason": f"unsupported side: {side}"}

        tick = self.client.tick(symbol)
        if tick is None:
            return {"status": "failed", "reason": f"no live tick for {symbol}", "symbol": symbol}

        entry = float(_field(tick, "ask") if side == "buy" else _field(tick, "bid"))
        norm_volume = self.client.normalize_volume(symbol, volume)
        payload = {
            "symbol": symbol,
            "side": side,
            "volume": norm_volume,
            "entry_price": entry,
        }

        if self.config.bot.dry_run:
            self.logger.warning(
                "TEST TRADE PAPER %s %s vol=%s entry=%.5f dry_run=true",
                symbol,
                side.upper(),
                norm_volume,
                entry,
            )
            return {"status": "paper", **payload}

        try:
            result = self.client.send_market_bare(
                symbol,
                side,
                norm_volume,
                self.config.bot.magic,
                comment[:31],
            )
        except Exception as exc:  # noqa: BLE001
            self.logger.warning("TEST TRADE REJECTED %s %s reason=%s", symbol, side.upper(), exc)
            return {"status": "failed", "reason": str(exc), **payload}

        retcode = getattr(result, "retcode", None)
        ticket = int(getattr(result, "order", 0) or getattr(result, "deal", 0) or 0)
        if retcode == self.client.TRADE_DONE and ticket:
            self.logger.warning(
                "TEST TRADE PLACED %s %s ticket=%s vol=%s entry=%.5f",
                symbol,
                side.upper(),
                ticket,
                norm_volume,
                entry,
            )
            return {"status": "placed", "ticket": ticket, "retcode": retcode, **payload}

        comment_text = getattr(result, "comment", None)
        reason = f"retcode={retcode} comment={comment_text}"
        self.logger.warning("TEST TRADE FAILED %s %s %s result=%s", symbol, side.upper(), reason, result)
        return {"status": "failed", "reason": reason, "retcode": retcode, "ticket": ticket, **payload}

    def place_market_setup(
        self,
        *,
        setup_id: str,
        symbol: str,
        market_key: str,
        side: str,
        sl: float,
        tps: list[float],
        lot_per_leg: float,
        entry_price: float | None = None,
        extra_setup: dict | None = None,
        comment: str = ORDER_COMMENT,
        execution_mode: str = "auto",
    ) -> dict:
        if execution_mode == "split":
            return self._place_split_market(
                setup_id=setup_id,
                symbol=symbol,
                market_key=market_key,
                side=side,
                sl=sl,
                tps=tps,
                lot_per_leg=lot_per_leg,
                entry_price=entry_price,
                extra_setup=extra_setup,
                comment=comment,
            )
        if is_partial_strategy(self.config.bot.strategy):
            return self._place_partial_market(
                setup_id=setup_id,
                symbol=symbol,
                market_key=market_key,
                side=side,
                sl=sl,
                tps=tps,
                lot_per_leg=lot_per_leg,
                entry_price=entry_price,
                extra_setup=extra_setup,
                comment=comment,
            )
        if is_full_position_strategy(self.config.bot.strategy):
            return self._place_full_market(
                setup_id=setup_id,
                symbol=symbol,
                market_key=market_key,
                side=side,
                sl=sl,
                tps=tps,
                lot_per_leg=lot_per_leg,
                entry_price=entry_price,
                extra_setup=extra_setup,
                comment=comment,
            )
        if is_single_leg_strategy(self.config.bot.strategy):
            return self._place_single_market(
                setup_id=setup_id,
                symbol=symbol,
                market_key=market_key,
                side=side,
                sl=sl,
                tps=tps,
                lot_per_leg=lot_per_leg,
                entry_price=entry_price,
                extra_setup=extra_setup,
                comment=comment,
            )
        return self._place_split_market(
            setup_id=setup_id,
            symbol=symbol,
            market_key=market_key,
            side=side,
            sl=sl,
            tps=tps,
            lot_per_leg=lot_per_leg,
            entry_price=entry_price,
            extra_setup=extra_setup,
            comment=comment,
        )

    def _place_split_signal(self, signal: Signal) -> Outcome:
        result = self._place_split_market(
            setup_id=signal.setup_id,
            symbol=signal.symbol,
            market_key=signal.market_key,
            side=signal.side,
            sl=signal.sl,
            tps=signal.tps,
            lot_per_leg=signal.lot_per_leg,
            entry_price=signal.entry,
        )
        if result.get("status") == "placed":
            self.state.mark_seen(signal.setup_id)
            return "placed"
        if result.get("status") == "skipped":
            self.state.mark_seen(signal.setup_id)
            return "skipped"
        if result.get("status") == "failed":
            return "failed"
        return "skipped"

    def _place_partial_signal(self, signal: Signal) -> Outcome:
        result = self._place_partial_market(
            setup_id=signal.setup_id,
            symbol=signal.symbol,
            market_key=signal.market_key,
            side=signal.side,
            sl=signal.sl,
            tps=signal.tps,
            lot_per_leg=signal.lot_per_leg,
            entry_price=signal.entry,
        )
        if result.get("status") == "placed":
            self.state.mark_seen(signal.setup_id)
            return "placed"
        if result.get("status") == "skipped":
            self.state.mark_seen(signal.setup_id)
            return "skipped"
        if result.get("status") == "failed":
            return "failed"
        return "skipped"

    def _place_split_market(
        self,
        *,
        setup_id: str,
        symbol: str,
        market_key: str,
        side: str,
        sl: float,
        tps: list[float],
        lot_per_leg: float,
        entry_price: float | None = None,
        extra_setup: dict | None = None,
        comment: str = ORDER_COMMENT,
    ) -> dict:
        signal_entry = entry_price
        valid, reason, live_entry = self._validate_market_setup(symbol, side, sl, tps, signal_entry)
        if not valid:
            self.logger.warning("SETUP REJECTED %s %s", symbol, reason)
            return {"status": "skipped", "reason": reason, "entry_price": live_entry}
        if entry_price is None:
            entry_price = live_entry

        tickets: list[int] = []
        last_failure: str | None = None
        for index, tp in enumerate(tps, start=1):
            try:
                result = self.client.send_market(
                    symbol,
                    side,
                    lot_per_leg,
                    sl,
                    tp,
                    self.config.bot.magic,
                    f"{comment} TP{index}"[:31],
                )
            except ValueError as exc:
                last_failure = str(exc)
                self.logger.warning("ORDER REJECTED %s tp=%s reason=%s", symbol, tp, exc)
                continue
            retcode = getattr(result, "retcode", None)
            order = int(getattr(result, "order", 0) or getattr(result, "deal", 0) or 0)
            if retcode == self.client.TRADE_DONE and order:
                tickets.append(order)
                self.logger.info("PLACED %s ticket=%s tp=%s", symbol, order, round(tp, 5))
            else:
                comment_text = getattr(result, "comment", None)
                last_failure = f"retcode={retcode} comment={comment_text}"
                self.logger.warning("ORDER FAILED %s tp=%s ret=%s result=%s", symbol, tp, retcode, result)

        if not tickets:
            self.logger.warning("SETUP FAILED %s no orders filled for %s", symbol, setup_id)
            return {
                "status": "failed",
                "tickets": tickets,
                "ticket": 0,
                "reason": last_failure or "no orders filled",
                "entry_price": live_entry,
            }

        setup = {
            "setup_id": setup_id,
            "symbol": symbol,
            "market_key": market_key,
            "side": side,
            "execution_mode": "split",
            "tickets": tickets,
            "tps": tps,
            "sl": sl,
            "moved_to_tp": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if entry_price is not None:
            setup["entry_price"] = entry_price
        if extra_setup:
            setup.update(extra_setup)
        self.state.add_setup(setup)
        return {
            "status": "placed",
            "tickets": tickets,
            "ticket": tickets[0],
            "entry_price": entry_price,
            "legs": len(tickets),
        }

    def _place_partial_market(
        self,
        *,
        setup_id: str,
        symbol: str,
        market_key: str,
        side: str,
        sl: float,
        tps: list[float],
        lot_per_leg: float,
        entry_price: float | None = None,
        extra_setup: dict | None = None,
        comment: str = ORDER_COMMENT,
    ) -> dict:
        if not tps:
            return {"status": "failed", "reason": "missing take profits"}
        signal_entry = entry_price
        valid, reason, live_entry = self._validate_market_setup(symbol, side, sl, tps, signal_entry)
        if not valid:
            self.logger.warning("PARTIAL SETUP REJECTED %s %s", symbol, reason)
            return {"status": "skipped", "reason": reason, "entry_price": live_entry}
        if entry_price is None:
            entry_price = live_entry

        total_volume, _per_slice = normalized_partial_volumes(self.client, symbol, lot_per_leg, len(tps))
        final_tp = float(tps[-1])
        try:
            result = self.client.send_market(
                symbol,
                side,
                total_volume,
                sl,
                final_tp,
                self.config.bot.magic,
                f"{comment} partial"[:31],
            )
        except ValueError as exc:
            self.logger.warning("PARTIAL ORDER REJECTED %s reason=%s", symbol, exc)
            return {"status": "skipped", "reason": str(exc)}
        retcode = getattr(result, "retcode", None)
        ticket = int(getattr(result, "order", 0) or getattr(result, "deal", 0) or 0)
        if retcode != self.client.TRADE_DONE or not ticket:
            self.logger.warning("PARTIAL ORDER FAILED %s ret=%s result=%s", symbol, retcode, result)
            return {"status": "failed", "ticket": ticket}

        self.logger.info(
            "PARTIAL PLACED %s ticket=%s vol=%s sl=%.5f final_tp=%.5f",
            symbol,
            ticket,
            total_volume,
            sl,
            final_tp,
        )
        setup = {
            "setup_id": setup_id,
            "symbol": symbol,
            "market_key": market_key,
            "side": side,
            "execution_mode": "partial",
            "tickets": [ticket],
            "tps": [float(tp) for tp in tps],
            "sl": sl,
            "initial_volume": total_volume,
            "partial_closed_tp": 0,
            "moved_to_tp": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if entry_price is not None:
            setup["entry_price"] = entry_price
        if extra_setup:
            setup.update(extra_setup)
        self.state.add_setup(setup)
        return {"status": "placed", "ticket": ticket, "volume": total_volume}

    def _place_full_signal(self, signal: Signal) -> Outcome:
        result = self._place_full_market(
            setup_id=signal.setup_id,
            symbol=signal.symbol,
            market_key=signal.market_key,
            side=signal.side,
            sl=signal.sl,
            tps=signal.tps,
            lot_per_leg=signal.lot_per_leg,
            entry_price=signal.entry,
        )
        if result.get("status") == "placed":
            self.state.mark_seen(signal.setup_id)
            return "placed"
        if result.get("status") == "skipped":
            self.state.mark_seen(signal.setup_id)
            return "skipped"
        if result.get("status") == "failed":
            return "failed"
        return "skipped"

    def _place_full_market(
        self,
        *,
        setup_id: str,
        symbol: str,
        market_key: str,
        side: str,
        sl: float,
        tps: list[float],
        lot_per_leg: float,
        entry_price: float | None = None,
        extra_setup: dict | None = None,
        comment: str = ORDER_COMMENT,
    ) -> dict:
        if not tps:
            return {"status": "failed", "reason": "missing take profits"}
        signal_entry = entry_price
        valid, reason, live_entry = self._validate_market_setup(symbol, side, sl, tps, signal_entry)
        if not valid:
            self.logger.warning("FULL SETUP REJECTED %s %s", symbol, reason)
            return {"status": "skipped", "reason": reason, "entry_price": live_entry}
        if entry_price is None:
            entry_price = live_entry

        total_volume = normalized_full_volume(self.client, symbol, lot_per_leg)
        final_tp = float(tps[-1])
        try:
            result = self.client.send_market(
                symbol,
                side,
                total_volume,
                sl,
                final_tp,
                self.config.bot.magic,
                f"{comment} full"[:31],
            )
        except ValueError as exc:
            self.logger.warning("FULL ORDER REJECTED %s reason=%s", symbol, exc)
            return {"status": "skipped", "reason": str(exc)}
        retcode = getattr(result, "retcode", None)
        ticket = int(getattr(result, "order", 0) or getattr(result, "deal", 0) or 0)
        if retcode != self.client.TRADE_DONE or not ticket:
            self.logger.warning("FULL ORDER FAILED %s ret=%s result=%s", symbol, retcode, result)
            return {"status": "failed", "ticket": ticket}

        self.logger.info(
            "FULL PLACED %s ticket=%s vol=%s sl=%.5f final_tp=%.5f",
            symbol,
            ticket,
            total_volume,
            sl,
            final_tp,
        )
        setup = {
            "setup_id": setup_id,
            "symbol": symbol,
            "market_key": market_key,
            "side": side,
            "execution_mode": "full",
            "tickets": [ticket],
            "tps": [float(tp) for tp in tps],
            "sl": sl,
            "initial_volume": total_volume,
            "moved_to_tp": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if entry_price is not None:
            setup["entry_price"] = entry_price
        if extra_setup:
            setup.update(extra_setup)
        self.state.add_setup(setup)
        return {"status": "placed", "ticket": ticket, "volume": total_volume}

    def _place_single_signal(self, signal: Signal) -> Outcome:
        result = self._place_single_market(
            setup_id=signal.setup_id,
            symbol=signal.symbol,
            market_key=signal.market_key,
            side=signal.side,
            sl=signal.sl,
            tps=signal.tps,
            lot_per_leg=signal.lot_per_leg,
            entry_price=signal.entry,
        )
        if result.get("status") == "placed":
            self.state.mark_seen(signal.setup_id)
            return "placed"
        if result.get("status") == "skipped":
            self.state.mark_seen(signal.setup_id)
            return "skipped"
        if result.get("status") == "failed":
            return "failed"
        return "skipped"

    def _place_single_market(
        self,
        *,
        setup_id: str,
        symbol: str,
        market_key: str,
        side: str,
        sl: float,
        tps: list[float],
        lot_per_leg: float,
        entry_price: float | None = None,
        extra_setup: dict | None = None,
        comment: str = ORDER_COMMENT,
    ) -> dict:
        if not tps:
            return {"status": "failed", "reason": "missing take profit"}
        signal_entry = entry_price
        valid, reason, live_entry = self._validate_market_setup(symbol, side, sl, tps, signal_entry)
        if not valid:
            self.logger.warning("SINGLE-LEG SETUP REJECTED %s %s", symbol, reason)
            return {"status": "skipped", "reason": reason, "entry_price": live_entry}
        if entry_price is None:
            entry_price = live_entry

        lot = normalized_split_lot(self.client, symbol, lot_per_leg)
        tp = float(tps[0])
        try:
            result = self.client.send_market(
                symbol,
                side,
                lot,
                sl,
                tp,
                self.config.bot.magic,
                f"{comment} SDzone"[:31],
            )
        except ValueError as exc:
            self.logger.warning("SINGLE-LEG ORDER REJECTED %s reason=%s", symbol, exc)
            return {"status": "skipped", "reason": str(exc)}
        retcode = getattr(result, "retcode", None)
        ticket = int(getattr(result, "order", 0) or getattr(result, "deal", 0) or 0)
        if retcode != self.client.TRADE_DONE or not ticket:
            self.logger.warning("SINGLE-LEG ORDER FAILED %s ret=%s result=%s", symbol, retcode, result)
            return {"status": "failed", "ticket": ticket}

        self.logger.info(
            "SINGLE-LEG PLACED %s ticket=%s vol=%s sl=%.5f tp=%.5f",
            symbol,
            ticket,
            lot,
            sl,
            tp,
        )
        setup = {
            "setup_id": setup_id,
            "symbol": symbol,
            "market_key": market_key,
            "side": side,
            "execution_mode": "single",
            "tickets": [ticket],
            "tps": [tp],
            "sl": sl,
            "moved_to_tp": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if entry_price is not None:
            setup["entry_price"] = entry_price
        if extra_setup:
            setup.update(extra_setup)
        self.state.add_setup(setup)
        return {"status": "placed", "ticket": ticket, "volume": lot}

    def _validate_market_setup(
        self,
        symbol: str,
        side: str,
        sl: float,
        tps: list[float],
        signal_entry: float | None = None,
    ) -> tuple[bool, str, float | None]:
        side = side.lower()
        tick = self.client.tick(symbol)
        if tick is None:
            return False, f"no live tick for {symbol}", None
        entry = float(_field(tick, "ask") if side == "buy" else _field(tick, "bid"))
        if signal_entry is not None and self.config.risk.max_live_entry_drift_risk is not None:
            reference = float(signal_entry)
            risk_distance = abs(reference - float(sl))
            max_drift = risk_distance * float(self.config.risk.max_live_entry_drift_risk)
            adverse_drift = entry - reference if side == "buy" else reference - entry
            if risk_distance > 0 and adverse_drift > max_drift:
                return (
                    False,
                    (
                        f"live entry drift too high for {side.upper()}: "
                        f"signal={reference:.5f} live={entry:.5f} max={max_drift:.5f}"
                    ),
                    entry,
                )
        reason = invalid_market_geometry(side, entry, float(sl), [float(tp) for tp in tps], label="live price")
        if reason:
            return False, reason, entry
        return True, "", entry

    def _symbol_cfg(self, symbol: str) -> SymbolConfig | None:
        for item in self.config.symbols:
            if item.symbol == symbol:
                return item
        return None

    def _position_market_keys(self) -> set[str]:
        positions = self.client.positions() or []
        return {market_key(str(_field(pos, "symbol", ""))) for pos in positions}

    def _bot_positions(self, symbol: str) -> list:
        positions = self.client.positions() or []
        return [
            pos
            for pos in positions
            if str(_field(pos, "symbol", "")) == symbol
            and int(_field(pos, "magic", 0) or 0) == self.config.bot.magic
        ]

    def _position_is_buy(self, pos) -> bool:
        return int(_field(pos, "type", 0) or 0) == 0

    def _sl_locks_profit(self, pos, new_sl: float) -> bool:
        open_price = float(_field(pos, "price_open", 0.0) or 0.0)
        if open_price <= 0:
            return False
        if self._position_is_buy(pos):
            return new_sl > open_price
        return new_sl < open_price

    def _has_bot_position_on_side(self, symbol: str, side: str) -> bool:
        for pos in self._bot_positions(symbol):
            is_buy = self._position_is_buy(pos)
            if side == "buy" and is_buy:
                return True
            if side == "sell" and not is_buy:
                return True
        return False

    def _close_opposite_positions(self, symbol: str, side_to_open: str) -> None:
        if self.config.bot.dry_run:
            return
        for pos in self._bot_positions(symbol):
            is_buy = self._position_is_buy(pos)
            close = (side_to_open == "buy" and not is_buy) or (side_to_open == "sell" and is_buy)
            if not close:
                continue
            ticket = int(_field(pos, "ticket"))
            result = self.client.close_position(ticket, symbol)
            self.logger.info(
                "SINGLE-LEG CLOSE opposite %s ticket=%s ret=%s",
                symbol,
                ticket,
                getattr(result, "retcode", None),
            )

    def _active_setup_count(self) -> int:
        positions = self.client.positions() or []
        open_tickets = {int(_field(pos, "ticket")) for pos in positions}
        setup_keys: set[str] = set()

        state = self.state.read()
        tracked_tickets: set[int] = set()
        for setup in state.get("setups", []):
            tickets = [int(ticket) for ticket in setup.get("tickets", [])]
            tracked_tickets.update(tickets)
            if any(ticket in open_tickets for ticket in tickets):
                setup_keys.add(str(setup.get("setup_id")))

        orphan_symbols: set[str] = set()
        for pos in positions:
            ticket = int(_field(pos, "ticket"))
            magic = int(_field(pos, "magic", 0) or 0)
            symbol = str(_field(pos, "symbol", ""))
            if magic != self.config.bot.magic:
                continue
            if ticket not in tracked_tickets:
                orphan_symbols.add(symbol)

        return len(setup_keys) + len(orphan_symbols)

    def manage_tp_protection(self, enabled: bool | None = None) -> None:
        if enabled is None:
            enabled = tp_protection_enabled(self.config.bot.strategy)
        state = self.state.read()
        setups = state.get("setups", [])
        next_setups: list[dict] = []
        all_positions = self.client.positions() or []
        open_by_ticket = {int(_field(pos, "ticket")): pos for pos in all_positions}

        for setup in setups:
            execution_mode = str(setup.get("execution_mode") or "split")
            if execution_mode == "single":
                kept = self._manage_single_setup(setup, open_by_ticket)
                if kept is not None:
                    next_setups.append(kept)
                continue
            if execution_mode == "partial":
                kept = self._manage_partial_setup(setup, open_by_ticket, enabled)
                if kept is not None:
                    next_setups.append(kept)
                continue
            if execution_mode == "full":
                kept = self._manage_full_setup(setup, open_by_ticket, enabled)
                if kept is not None:
                    next_setups.append(kept)
                continue

            kept = self._manage_split_setup(setup, open_by_ticket, enabled)
            if kept is not None:
                next_setups.append(kept)

        self.state.update_setups(next_setups)

    def _manage_single_setup(self, setup: dict, open_by_ticket: dict) -> dict | None:
        tickets = [int(ticket) for ticket in setup.get("tickets", [])]
        open_tickets = [ticket for ticket in tickets if ticket in open_by_ticket]
        if not open_tickets:
            self.logger.info("SINGLE-LEG SETUP DONE %s %s", setup.get("symbol"), setup.get("setup_id"))
            return None
        return setup

    def _manage_full_setup(self, setup: dict, open_by_ticket: dict, tp_protect: bool) -> dict | None:
        tickets = [int(ticket) for ticket in setup.get("tickets", [])]
        if not tickets:
            return None
        ticket = tickets[0]
        if ticket not in open_by_ticket:
            self.logger.info("FULL SETUP DONE %s %s", setup.get("symbol"), setup.get("setup_id"))
            return None

        if not tp_protect:
            return setup

        symbol = str(setup.get("symbol"))
        side = str(setup.get("side"))
        tps = [float(tp) for tp in setup.get("tps", [])]
        if len(tps) < 2:
            return setup

        moved_to_tp = int(setup.get("moved_to_tp", 0))
        tick = self.client.tick(symbol)
        if tick is None:
            return setup

        bid = float(_field(tick, "bid", 0.0) or 0.0)
        ask = float(_field(tick, "ask", 0.0) or 0.0)
        mark = ask if side == "buy" else bid

        while moved_to_tp < len(tps) - 1:
            tp_level = tps[moved_to_tp]
            hit = mark >= tp_level if side == "buy" else mark <= tp_level
            if not hit:
                break

            moved_to_tp += 1
            setup["moved_to_tp"] = moved_to_tp
            if not self.config.bot.dry_run:
                pos = open_by_ticket.get(ticket)
                if pos is None:
                    break
                new_sl = self.client.normalize_price(symbol, tp_level)
                if not self._sl_locks_profit(pos, new_sl):
                    self.logger.warning(
                        "FULL TP PROTECT SKIP ticket=%s %s new SL %.5f would not lock profit from open %.5f",
                        ticket,
                        symbol,
                        new_sl,
                        float(_field(pos, "price_open", 0.0) or 0.0),
                    )
                    break
                final_tp = float(_field(pos, "tp"))
                self.client.update_position_sl(ticket, symbol, new_sl, final_tp)
                setup["sl"] = new_sl
                self.logger.info("FULL TP PROTECT %s SL -> %.5f after TP%s", symbol, new_sl, moved_to_tp)

        return setup

    def _manage_split_setup(self, setup: dict, open_by_ticket: dict, tp_protect: bool) -> dict | None:
        tickets = [int(ticket) for ticket in setup.get("tickets", [])]
        open_tickets = [ticket for ticket in tickets if ticket in open_by_ticket]
        if not open_tickets:
            self.logger.info("SETUP DONE %s %s", setup.get("symbol"), setup.get("setup_id"))
            return None

        if not tp_protect:
            return setup

        moved_to_tp = int(setup.get("moved_to_tp", 0))
        tps = [float(tp) for tp in setup.get("tps", [])]
        symbol = str(setup.get("symbol"))
        setup["market_key"] = setup.get("market_key") or market_key(symbol)

        target_index = moved_to_tp
        if len(tickets) >= 1 and tickets[0] not in open_by_ticket:
            target_index = max(target_index, 1)
        if len(tickets) >= 2 and tickets[1] not in open_by_ticket:
            target_index = max(target_index, 2)

        if target_index > moved_to_tp and target_index <= len(tps):
            new_sl = self.client.normalize_price(symbol, tps[target_index - 1])
            self.logger.info(
                "TP PROTECT %s setup=%s move remaining SL to TP%s %.5f",
                symbol,
                setup.get("setup_id"),
                target_index,
                new_sl,
            )
            if not self.config.bot.dry_run:
                for ticket in open_tickets:
                    pos = open_by_ticket[ticket]
                    if not self._sl_locks_profit(pos, new_sl):
                        self.logger.warning(
                            "TP PROTECT SKIP ticket=%s %s new SL %.5f would not lock profit from open %.5f",
                            ticket,
                            symbol,
                            new_sl,
                            float(_field(pos, "price_open", 0.0) or 0.0),
                        )
                        continue
                    tp = float(_field(pos, "tp"))
                    result = self.client.update_position_sl(ticket, symbol, new_sl, tp)
                    self.logger.info("SL UPDATE ticket=%s ret=%s", ticket, getattr(result, "retcode", None))
            setup["moved_to_tp"] = target_index

        return setup

    def _manage_partial_setup(self, setup: dict, open_by_ticket: dict, tp_protect: bool) -> dict | None:
        tickets = [int(ticket) for ticket in setup.get("tickets", [])]
        if not tickets:
            return None
        ticket = tickets[0]
        if ticket not in open_by_ticket:
            self.logger.info("PARTIAL SETUP DONE %s %s", setup.get("symbol"), setup.get("setup_id"))
            return None

        symbol = str(setup.get("symbol"))
        side = str(setup.get("side"))
        tps = [float(tp) for tp in setup.get("tps", [])]
        if not tps:
            return setup

        pos = open_by_ticket[ticket]
        current_volume = float(_field(pos, "volume", 0.0) or 0.0)
        initial_volume = float(setup.get("initial_volume") or current_volume)
        partial_closed_tp = int(setup.get("partial_closed_tp", 0))
        per_slice = self.client.normalize_volume(symbol, initial_volume / len(tps))

        tick = self.client.tick(symbol)
        if tick is None:
            return setup

        bid = float(_field(tick, "bid", 0.0) or 0.0)
        ask = float(_field(tick, "ask", 0.0) or 0.0)
        mark = ask if side == "buy" else bid

        while partial_closed_tp < len(tps) - 1:
            tp_level = tps[partial_closed_tp]
            hit = mark >= tp_level if side == "buy" else mark <= tp_level
            if not hit:
                break

            close_volume = per_slice
            if partial_closed_tp == len(tps) - 2:
                close_volume = self.client.normalize_volume(symbol, current_volume - per_slice)
            close_volume = min(close_volume, current_volume)
            if close_volume <= 0:
                break

            self.logger.info(
                "PARTIAL TP%s %s setup=%s close %.4f lots at %.5f",
                partial_closed_tp + 1,
                symbol,
                setup.get("setup_id"),
                close_volume,
                tp_level,
            )
            if not self.config.bot.dry_run:
                result = self.client.close_position_partial(ticket, symbol, close_volume)
                self.logger.info("PARTIAL CLOSE ticket=%s ret=%s", ticket, getattr(result, "retcode", None))

            partial_closed_tp += 1
            setup["partial_closed_tp"] = partial_closed_tp
            current_volume = max(0.0, current_volume - close_volume)

            if tp_protect and not self.config.bot.dry_run:
                pos = open_by_ticket.get(ticket)
                if pos is not None:
                    new_sl = self.client.normalize_price(symbol, tp_level)
                    if not self._sl_locks_profit(pos, new_sl):
                        self.logger.warning(
                            "PARTIAL TP PROTECT SKIP ticket=%s %s new SL %.5f would not lock profit from open %.5f",
                            ticket,
                            symbol,
                            new_sl,
                            float(_field(pos, "price_open", 0.0) or 0.0),
                        )
                        continue
                    final_tp = float(_field(pos, "tp"))
                    self.client.update_position_sl(ticket, symbol, new_sl, final_tp)
                    setup["moved_to_tp"] = partial_closed_tp
                    setup["sl"] = new_sl
                    self.logger.info("PARTIAL TP PROTECT %s SL -> %.5f", symbol, new_sl)

        return setup

    def apply_breakeven(self, setup: dict) -> dict:
        tickets = [int(ticket) for ticket in setup.get("tickets", [])]
        if not tickets:
            return {"status": "skipped", "reason": "setup has no tickets", "setup_id": setup.get("setup_id")}

        symbol = str(setup.get("symbol") or "")
        if not symbol:
            return {"status": "skipped", "reason": "setup has no symbol", "setup_id": setup.get("setup_id")}

        all_positions = self.client.positions() or []
        open_by_ticket = {int(_field(pos, "ticket")): pos for pos in all_positions}
        open_tickets = [ticket for ticket in tickets if ticket in open_by_ticket]
        if not open_tickets:
            return {
                "status": "skipped",
                "reason": "no open positions for setup",
                "setup_id": setup.get("setup_id"),
                "symbol": symbol,
            }

        entry = float(setup.get("entry_price") or 0.0)
        if entry <= 0:
            entry = sum(
                float(_field(open_by_ticket[ticket], "price_open"))
                for ticket in open_tickets
            ) / len(open_tickets)

        new_sl = self.client.normalize_price(symbol, entry)
        self.logger.warning(
            "BREAKEVEN %s setup=%s move SL to entry %.5f tickets=%s dry_run=%s",
            symbol,
            setup.get("setup_id"),
            new_sl,
            open_tickets,
            self.config.bot.dry_run,
        )
        if self.config.bot.dry_run:
            return {
                "status": "paper",
                "reason": "breakeven SL move",
                "setup_id": setup.get("setup_id"),
                "symbol": symbol,
                "entry_price": new_sl,
                "tickets": open_tickets,
            }

        updated: list[dict] = []
        for ticket in open_tickets:
            pos = open_by_ticket[ticket]
            tp = float(_field(pos, "tp"))
            result = self.client.update_position_sl(ticket, symbol, new_sl, tp)
            updated.append(
                {
                    "ticket": ticket,
                    "retcode": getattr(result, "retcode", None),
                    "result": str(result),
                }
            )

        if setup.get("setup_id"):
            self.state.update_setup(
                str(setup["setup_id"]),
                {"breakeven_applied": True, "sl": new_sl},
            )

        return {
            "status": "breakeven",
            "reason": "stop loss moved to entry",
            "setup_id": setup.get("setup_id"),
            "symbol": symbol,
            "entry_price": new_sl,
            "tickets": updated,
        }

    def apply_sl_update(self, setup: dict, new_sl: float, *, reason: str = "stop loss updated") -> dict:
        tickets = [int(ticket) for ticket in setup.get("tickets", [])]
        if not tickets:
            return {"status": "skipped", "reason": "setup has no tickets", "setup_id": setup.get("setup_id")}

        symbol = str(setup.get("symbol") or "")
        if not symbol:
            return {"status": "skipped", "reason": "setup has no symbol", "setup_id": setup.get("setup_id")}

        side = str(setup.get("side") or "")
        tps = [float(tp) for tp in setup.get("tps", [])]
        entry = float(setup.get("entry_price") or 0.0)
        if entry <= 0:
            all_positions = self.client.positions() or []
            open_by_ticket = {int(_field(pos, "ticket")): pos for pos in all_positions}
            open_tickets = [ticket for ticket in tickets if ticket in open_by_ticket]
            if open_tickets:
                entry = sum(
                    float(_field(open_by_ticket[ticket], "price_open"))
                    for ticket in open_tickets
                ) / len(open_tickets)

        normalized_sl = self.client.normalize_price(symbol, float(new_sl))
        geometry_reason = invalid_market_geometry(side, entry, normalized_sl, tps, label="entry")
        if geometry_reason:
            return {
                "status": "skipped",
                "reason": geometry_reason,
                "setup_id": setup.get("setup_id"),
                "symbol": symbol,
            }

        all_positions = self.client.positions() or []
        open_by_ticket = {int(_field(pos, "ticket")): pos for pos in all_positions}
        open_tickets = [ticket for ticket in tickets if ticket in open_by_ticket]
        if not open_tickets:
            return {
                "status": "skipped",
                "reason": "no open positions for setup",
                "setup_id": setup.get("setup_id"),
                "symbol": symbol,
            }

        self.logger.warning(
            "SL UPDATE %s setup=%s move SL to %.5f tickets=%s dry_run=%s reason=%s",
            symbol,
            setup.get("setup_id"),
            normalized_sl,
            open_tickets,
            self.config.bot.dry_run,
            reason,
        )
        if self.config.bot.dry_run:
            return {
                "status": "paper",
                "reason": reason,
                "setup_id": setup.get("setup_id"),
                "symbol": symbol,
                "sl": normalized_sl,
                "tickets": open_tickets,
            }

        updated: list[dict] = []
        for ticket in open_tickets:
            pos = open_by_ticket[ticket]
            tp = float(_field(pos, "tp"))
            result = self.client.update_position_sl(ticket, symbol, normalized_sl, tp)
            updated.append(
                {
                    "ticket": ticket,
                    "retcode": getattr(result, "retcode", None),
                    "result": str(result),
                }
            )

        if setup.get("setup_id"):
            self.state.update_setup(
                str(setup["setup_id"]),
                {"sl": normalized_sl, "sl_synthetic": False, "sl_updated_from_telegram": True},
            )

        return {
            "status": "updated",
            "reason": reason,
            "setup_id": setup.get("setup_id"),
            "symbol": symbol,
            "sl": normalized_sl,
            "tickets": updated,
        }
