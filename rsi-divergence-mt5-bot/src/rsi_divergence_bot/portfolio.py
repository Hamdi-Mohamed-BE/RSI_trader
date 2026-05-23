from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OpenSetup:
    setup_id: str
    market_key: str
    exit_unix: int


@dataclass
class BacktestPortfolio:
    """In-memory portfolio state mirroring live StateStore + open MT5 positions."""

    seen_setup_ids: set[str] = field(default_factory=set)
    open_setups: list[OpenSetup] = field(default_factory=list)

    def settle_through(self, as_of_unix: int) -> None:
        self.open_setups = [setup for setup in self.open_setups if setup.exit_unix > as_of_unix]

    def is_seen(self, setup_id: str) -> bool:
        return setup_id in self.seen_setup_ids

    def mark_seen(self, setup_id: str) -> None:
        self.seen_setup_ids.add(setup_id)

    def open_market_keys(self) -> set[str]:
        return {setup.market_key for setup in self.open_setups}

    def active_setup_count(self) -> int:
        return len(self.open_setups)

    def close_market_setups(self, market_key: str) -> None:
        self.open_setups = [setup for setup in self.open_setups if setup.market_key != market_key]

    def register_open(self, setup_id: str, market_key: str, exit_unix: int) -> None:
        self.open_setups.append(OpenSetup(setup_id=setup_id, market_key=market_key, exit_unix=exit_unix))
