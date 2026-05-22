from __future__ import annotations

import logging
from datetime import datetime, timezone

from .config import AppConfig, SymbolConfig
from .decision import evaluate_trade_signal, resolve_trade_filters
from .mt5_client import MT5Client
from .state import StateStore
from .strategy import Signal
from .symbols import market_key

Outcome = str  # placed | skipped | duplicate | failed
ORDER_COMMENT = "RSI auto bot"


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
            "SIGNAL %s key=%s %s entry %.5f sl %.5f tps %s risk_usd %.2f spread_atr %.2f profile=%s dry_run=%s session=%s",
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
        )
        if self.config.bot.dry_run:
            self.state.mark_seen(signal.setup_id)
            self.logger.info("PAPER %s would place %s legs", signal.symbol, len(signal.tps))
            return "paper"

        tickets: list[int] = []
        for index, tp in enumerate(signal.tps, start=1):
            result = self.client.send_market(
                signal.symbol,
                signal.side,
                signal.lot_per_leg,
                signal.sl,
                tp,
                self.config.bot.magic,
                ORDER_COMMENT,
            )
            retcode = getattr(result, "retcode", None)
            order = int(getattr(result, "order", 0) or getattr(result, "deal", 0) or 0)
            done_code = getattr(self.client, "TRADE_DONE", 10009)
            if retcode == done_code and order:
                tickets.append(order)
                self.logger.info("PLACED %s ticket=%s tp=%s", signal.symbol, order, round(tp, 5))
            else:
                self.logger.warning("ORDER FAILED %s tp=%s ret=%s result=%s", signal.symbol, tp, retcode, result)

        if tickets:
            self.state.add_setup(
                {
                    "setup_id": signal.setup_id,
                    "symbol": signal.symbol,
                    "market_key": signal.market_key,
                    "side": signal.side,
                    "tickets": tickets,
                    "tps": signal.tps,
                    "sl": signal.sl,
                    "moved_to_tp": 0,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            return "placed"

        self.logger.warning("SETUP FAILED %s no orders filled for %s", signal.symbol, signal.setup_id)
        return "failed"

    def _symbol_cfg(self, symbol: str) -> SymbolConfig | None:
        for item in self.config.symbols:
            if item.symbol == symbol:
                return item
        return None

    def _has_market_position(self, target_key: str) -> bool:
        return target_key in self._position_market_keys()

    def _position_market_keys(self) -> set[str]:
        positions = self.client.positions() or []
        return {market_key(str(pos.get("symbol") if isinstance(pos, dict) else pos.symbol)) for pos in positions}

    def _active_setup_count(self) -> int:
        positions = self.client.positions() or []
        open_tickets = {int(pos.get("ticket") if isinstance(pos, dict) else pos.ticket) for pos in positions}
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
            ticket = int(pos.get("ticket") if isinstance(pos, dict) else pos.ticket)
            magic = int(pos.get("magic") if isinstance(pos, dict) else pos.magic)
            symbol = str(pos.get("symbol") if isinstance(pos, dict) else pos.symbol)
            if magic != self.config.bot.magic:
                continue
            if ticket not in tracked_tickets:
                orphan_symbols.add(symbol)

        return len(setup_keys) + len(orphan_symbols)

    def manage_tp_protection(self, enabled: bool | None = None) -> None:
        if enabled is None:
            enabled = self.config.bot.strategy == "signal_with_tp_protection"
        if not enabled:
            return

        state = self.state.read()
        setups = state.get("setups", [])
        next_setups: list[dict] = []
        all_positions = self.client.positions() or []
        open_by_ticket = {int(pos.get("ticket") if isinstance(pos, dict) else pos.ticket): pos for pos in all_positions}

        for setup in setups:
            tickets = [int(ticket) for ticket in setup.get("tickets", [])]
            open_tickets = [ticket for ticket in tickets if ticket in open_by_ticket]
            if not open_tickets:
                self.logger.info("SETUP DONE %s %s", setup.get("symbol"), setup.get("setup_id"))
                continue

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
                        tp = float(pos.get("tp") if isinstance(pos, dict) else pos.tp)
                        result = self.client.update_position_sl(ticket, symbol, new_sl, tp)
                        self.logger.info("SL UPDATE ticket=%s ret=%s", ticket, getattr(result, "retcode", None))
                setup["moved_to_tp"] = target_index

            next_setups.append(setup)

        self.state.update_setups(next_setups)

    def apply_breakeven(self, setup: dict) -> dict:
        tickets = [int(ticket) for ticket in setup.get("tickets", [])]
        if not tickets:
            return {"status": "skipped", "reason": "setup has no tickets", "setup_id": setup.get("setup_id")}

        symbol = str(setup.get("symbol") or "")
        if not symbol:
            return {"status": "skipped", "reason": "setup has no symbol", "setup_id": setup.get("setup_id")}

        all_positions = self.client.positions() or []
        open_by_ticket = {
            int(pos.get("ticket") if isinstance(pos, dict) else pos.ticket): pos for pos in all_positions
        }
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
                float(pos.get("price_open") if isinstance(pos, dict) else pos.price_open)
                for ticket in open_tickets
                for pos in [open_by_ticket[ticket]]
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
            tp = float(pos.get("tp") if isinstance(pos, dict) else pos.tp)
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
