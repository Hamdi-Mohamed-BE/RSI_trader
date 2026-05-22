from __future__ import annotations

import logging
from datetime import datetime, timezone

from .config import AppConfig, SymbolConfig
from .decision import evaluate_trade_signal, resolve_trade_filters
from .mt5_client import MT5Client
from .state import StateStore
from .strategy import Signal
from .strategy_modes import is_partial_strategy, tp_protection_enabled
from .symbols import market_key

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
        position_keys = self._position_market_keys() if filters.existing_position else None
        decision = evaluate_trade_signal(
            self.client,
            self.config,
            signal,
            symbol_cfg,
            seen=False,
            filters=filters,
            market_position_keys=position_keys,
            active_setup_count=self._active_setup_count() if filters.max_setups else None,
        )
        if not decision.allowed:
            self.logger.info("SKIP %s %s", signal.symbol, decision.reason)
            if decision.code == "duplicate":
                return "duplicate"
            if decision.code != "max_setups":
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
            "partial" if is_partial_strategy(self.config.bot.strategy) else "split",
        )
        if self.config.bot.dry_run:
            self.state.mark_seen(signal.setup_id)
            if is_partial_strategy(self.config.bot.strategy):
                total = self.client.normalize_volume(signal.symbol, signal.lot_per_leg * len(signal.tps))
                self.logger.info("PAPER %s would place 1 partial position vol=%s", signal.symbol, total)
            else:
                self.logger.info("PAPER %s would place %s legs", signal.symbol, len(signal.tps))
            return "paper"

        if is_partial_strategy(self.config.bot.strategy):
            return self._place_partial_signal(signal)

        return self._place_split_signal(signal)

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
    ) -> dict:
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
        )
        if result.get("status") == "placed":
            self.state.mark_seen(signal.setup_id)
            return "placed"
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
        )
        if result.get("status") == "placed":
            self.state.mark_seen(signal.setup_id)
            return "placed"
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
        tickets: list[int] = []
        for index, tp in enumerate(tps, start=1):
            result = self.client.send_market(
                symbol,
                side,
                lot_per_leg,
                sl,
                tp,
                self.config.bot.magic,
                f"{comment} TP{index}"[:31],
            )
            retcode = getattr(result, "retcode", None)
            order = int(getattr(result, "order", 0) or getattr(result, "deal", 0) or 0)
            if retcode == self.client.TRADE_DONE and order:
                tickets.append(order)
                self.logger.info("PLACED %s ticket=%s tp=%s", symbol, order, round(tp, 5))
            else:
                self.logger.warning("ORDER FAILED %s tp=%s ret=%s result=%s", symbol, tp, retcode, result)

        if not tickets:
            self.logger.warning("SETUP FAILED %s no orders filled for %s", symbol, setup_id)
            return {"status": "failed", "tickets": tickets}

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
        return {"status": "placed", "tickets": tickets}

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

        total_volume = self.client.normalize_volume(symbol, lot_per_leg * len(tps))
        final_tp = float(tps[-1])
        result = self.client.send_market(
            symbol,
            side,
            total_volume,
            sl,
            final_tp,
            self.config.bot.magic,
            f"{comment} partial"[:31],
        )
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

    def _symbol_cfg(self, symbol: str) -> SymbolConfig | None:
        for item in self.config.symbols:
            if item.symbol == symbol:
                return item
        return None

    def _position_market_keys(self) -> set[str]:
        positions = self.client.positions() or []
        return {market_key(str(_field(pos, "symbol", ""))) for pos in positions}

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
            if execution_mode == "partial":
                kept = self._manage_partial_setup(setup, open_by_ticket, enabled)
                if kept is not None:
                    next_setups.append(kept)
                continue

            kept = self._manage_split_setup(setup, open_by_ticket, enabled)
            if kept is not None:
                next_setups.append(kept)

        self.state.update_setups(next_setups)

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
            new_sl = tps[target_index - 1]
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
