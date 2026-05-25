from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rsi_divergence_bot.config import AppConfig, BotRuntimeConfig, RiskConfig, SymbolConfig, load_config, save_config
from rsi_divergence_bot.config_snapshots import (
    apply_config_snapshot,
    apply_snapshot,
    delete_snapshot,
    list_snapshots,
    load_snapshot,
    save_snapshot,
    slugify_snapshot_name,
)


def _config(**overrides) -> AppConfig:
    bot = BotRuntimeConfig(strategy="signal_no_tp_protection", dry_run=True, max_concurrent_setups=5)
    bot = bot.model_copy(update=overrides.pop("bot", {}))
    risk = RiskConfig(max_setup_risk_usd=120.0)
    risk = risk.model_copy(update=overrides.pop("risk", {}))
    return AppConfig(
        bot=bot,
        risk=risk,
        symbols=[
            SymbolConfig(symbol="EURUSD", name="Euro", lot_per_leg=0.2, enabled=True),
            SymbolConfig(symbol="GBPUSD", name="Cable", lot_per_leg=0.1, enabled=False),
        ],
        **overrides,
    )


class ConfigSnapshotTests(unittest.TestCase):
    def test_slugify_snapshot_name(self) -> None:
        self.assertEqual(slugify_snapshot_name("Conservative May"), "conservative-may")

    def test_save_list_load_apply_delete_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "config.yaml"
            base = _config()
            save_config(config_path, base)

            save_snapshot(config_path, name="Conservative May", config=base, note="Low risk")
            entries = list_snapshots(config_path)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["name"], "Conservative May")
            self.assertEqual(entries[0]["summary"]["strategy"], "signal_no_tp_protection")

            changed = _config()
            changed.bot.strategy = "signal_with_tp_protection"  # type: ignore[assignment]
            changed.symbols[0].lot_per_leg = 0.5
            save_config(config_path, changed)

            target = load_config(config_path)
            apply_snapshot(config_path, slug="conservative-may", target=target, persist=True)

            self.assertEqual(target.bot.strategy, "signal_no_tp_protection")
            self.assertEqual(target.symbols[0].lot_per_leg, 0.2)
            reloaded = load_config(config_path)
            self.assertEqual(reloaded.bot.strategy, "signal_no_tp_protection")

            snapshot = load_snapshot(config_path, "conservative-may")
            self.assertEqual(snapshot.symbols[1].enabled, False)

            delete_snapshot(config_path, "conservative-may")
            self.assertEqual(list_snapshots(config_path), [])

    def test_apply_config_snapshot_mutates_target(self) -> None:
        target = _config()
        source = _config()
        source.risk.max_setup_risk_usd = 50.0
        source.symbols[0].lot_per_leg = 0.33
        apply_config_snapshot(target, source)
        self.assertEqual(target.risk.max_setup_risk_usd, 50.0)
        self.assertEqual(target.symbols[0].lot_per_leg, 0.33)


if __name__ == "__main__":
    unittest.main()
