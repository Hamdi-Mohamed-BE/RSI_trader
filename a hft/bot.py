"""
Multi-crypto MT5 scalper (fun / demo project).

Run:  python bot.py
Edit: config.py for all tunables.
"""

from __future__ import annotations

import signal
import sys
import time

import config as cfg
import mt5_client as mt5c
from risk import tp_sl_usd
from session import fetch_closed_profit
from strategy import Side, get_scalp_signal, warm_up


class HFTScalper:
    def __init__(self) -> None:
        self.session_pnl = 0.0
        self.trades_closed = 0
        self.last_entry_time: dict[str, float] = {}
        self.tracked_tickets: set[int] = set()
        self.running = True
        self.symbols: list[str] = []

    def stop(self, *_args) -> None:
        self.running = False
        mt5c.log("Stopping…")

    def _should_close(self, position) -> tuple[bool, str]:
        if not cfg.USE_SOFTWARE_SLTP_BACKUP:
            return False, ""
        if position.sl > 0 and position.tp > 0:
            return False, ""  # broker handles it

        profit = position.profit + position.swap
        tp_usd, sl_usd = tp_sl_usd(position.symbol)
        if profit >= tp_usd:
            return True, f"TP +${profit:.2f}"
        if profit <= -sl_usd:
            return True, f"SL ${profit:.2f}"
        if cfg.MAX_POSITION_AGE_SECONDS > 0:
            age = time.time() - position.time
            if age >= cfg.MAX_POSITION_AGE_SECONDS:
                return True, f"timeout {age:.0f}s pnl=${profit:.2f}"
        return False, ""

    def _track_broker_closes(self) -> None:
        current = {p.ticket for p in mt5c.bot_positions(self.symbols)}
        closed = self.tracked_tickets - current
        for ticket in closed:
            profit = fetch_closed_profit(ticket)
            if profit is not None:
                self.session_pnl += profit
                self.trades_closed += 1
                mt5c.log(f"  broker closed ticket={ticket} pnl=${profit:.2f} | session=${self.session_pnl:.2f}")
        self.tracked_tickets = current

    def manage_open_positions(self) -> None:
        self._track_broker_closes()

        for pos in mt5c.bot_positions(self.symbols):
            self.tracked_tickets.add(pos.ticket)
            should_close, reason = self._should_close(pos)
            if not should_close:
                continue
            profit_before = pos.profit + pos.swap
            if mt5c.close_position(pos):
                self.session_pnl += profit_before
                self.trades_closed += 1
                self.tracked_tickets.discard(pos.ticket)
                mt5c.log(f"  {pos.symbol} {reason} | session=${self.session_pnl:.2f}")

    def _cooldown_ok(self, symbol: str) -> bool:
        last = self.last_entry_time.get(symbol, 0.0)
        return time.time() - last >= cfg.MIN_SECONDS_BETWEEN_ENTRIES

    def try_open(self) -> None:
        candidates: list[tuple[int, str, object]] = []
        for symbol in self.symbols:
            if not self._cooldown_ok(symbol):
                continue
            if mt5c.entry_block_reason(symbol) is not None:
                continue
            sig = get_scalp_signal(symbol)
            if sig.side != Side.FLAT:
                candidates.append((sig.score, symbol, sig))

        if not candidates:
            if not hasattr(self, "_last_flat_log") or time.time() - self._last_flat_log >= 30:
                mt5c.log("scanning — no setup on any symbol yet")
                self._last_flat_log = time.time()
            return

        candidates.sort(key=lambda x: x[0], reverse=True)
        _, symbol, sig = candidates[0]

        if mt5c.open_market(symbol, sig.side.value):
            self.last_entry_time[symbol] = time.time()
            mt5c.log(f"  {symbol} {sig.side.value} score={sig.score} ({sig.reason})")

    def session_done(self) -> bool:
        if self.session_pnl >= cfg.SESSION_TARGET_PROFIT_USD:
            mt5c.log(f"SESSION TARGET HIT +${self.session_pnl:.2f}")
            return True
        if self.session_pnl <= -cfg.SESSION_MAX_LOSS_USD:
            mt5c.log(f"SESSION MAX LOSS ${self.session_pnl:.2f} — stopping")
            return True
        return False

    def status_line(self) -> None:
        positions = mt5c.bot_positions(self.symbols)
        open_count = len(positions)
        floating = sum(p.profit + p.swap for p in positions)
        by_symbol = ", ".join(
            f"{s}:{sum(1 for p in positions if p.symbol == s)}"
            for s in self.symbols
        )
        mt5c.log(
            f"open={open_count} [{by_symbol}] closed={self.trades_closed} "
            f"realized=${self.session_pnl:.2f} floating=${floating:.2f} "
            f"target=${cfg.SESSION_TARGET_PROFIT_USD:.0f}"
        )

    def run(self) -> None:
        self.symbols = mt5c.initialize()
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        mt5c.log(
            f"Scalper started | {len(self.symbols)} cryptos lot={cfg.LOT_SIZE} "
            f"default TP=${cfg.TAKE_PROFIT_USD} SL=${cfg.STOP_LOSS_USD} "
            f"broker SL/TP={'ON' if cfg.PLACE_BROKER_SLTP else 'OFF'} "
            f"→ session goal ${cfg.SESSION_TARGET_PROFIT_USD}"
        )
        mt5c.log("Tip: enable Algo Trading in MT5 toolbar (green play button)")

        warm_up(self.symbols)
        for _ in range(max(cfg.TICK_MOMENTUM_COUNT, 3)):
            time.sleep(0.2)
            warm_up(self.symbols, samples=1)

        last_status = time.time()
        try:
            while self.running:
                self.manage_open_positions()
                if self.session_done():
                    break
                self.try_open()
                if time.time() - last_status >= cfg.STATUS_EVERY_SECONDS:
                    self.status_line()
                    last_status = time.time()
                time.sleep(cfg.LOOP_SLEEP_SECONDS)
        finally:
            self.status_line()
            mt5c.shutdown()
            mt5c.log("Done.")


def main() -> int:
    try:
        HFTScalper().run()
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f"Fatal: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
