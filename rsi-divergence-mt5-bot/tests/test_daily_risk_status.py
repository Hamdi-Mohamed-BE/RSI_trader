import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from rsi_divergence_bot.config import RiskConfig
from rsi_divergence_bot.daily_risk import compute_daily_risk_status, resolve_day_start_equity


class DailyRiskStatusTests(unittest.TestCase):
    def test_new_day_snapshots_current_equity(self) -> None:
        client = MagicMock()
        client.account_snapshot.return_value = {
            "equity": 3398.5,
            "balance": 3781.46,
            "floating_pnl": -382.96,
        }
        state = MagicMock()
        state.read.return_value = {"daily_risk": {"date": "2026-05-26", "start_equity": 1000.0}}
        risk_cfg = RiskConfig(use_daily_loss_guard=True, max_daily_loss_pct=15.0)

        with unittest.mock.patch(
            "rsi_divergence_bot.daily_risk.datetime",
            wraps=datetime,
        ) as dt_mock:
            dt_mock.now.return_value = datetime(2026, 5, 27, 12, 0, tzinfo=timezone.utc)
            status = compute_daily_risk_status(client, state, risk_cfg)

        self.assertEqual(status["start_equity"], 3398.5)
        self.assertEqual(status["loss"], 0.0)
        self.assertFalse(status["halted"])

    def test_same_day_uses_stored_start_equity_and_mt5_equity(self) -> None:
        client = MagicMock()
        client.account_snapshot.return_value = {
            "equity": 3000.0,
            "balance": 3100.0,
            "floating_pnl": -100.0,
        }
        state = MagicMock()
        state.read.return_value = {
            "daily_risk": {
                "date": "2026-05-27",
                "start_equity": 3398.5,
                "created_at": "2026-05-27T00:05:00+00:00",
            }
        }
        risk_cfg = RiskConfig(use_daily_loss_guard=True, max_daily_loss_pct=15.0)

        with unittest.mock.patch(
            "rsi_divergence_bot.daily_risk.datetime",
            wraps=datetime,
        ) as dt_mock:
            dt_mock.now.return_value = datetime(2026, 5, 27, 12, 0, tzinfo=timezone.utc)
            status = compute_daily_risk_status(client, state, risk_cfg)

        self.assertEqual(status["start_equity"], 3398.5)
        self.assertEqual(status["loss"], 398.5)
        self.assertEqual(status["loss_limit"], round(3398.5 * 0.15, 2))
        self.assertFalse(status["halted"])

    def test_midday_restart_reconstructs_from_closed_deals(self) -> None:
        client = MagicMock()
        client.net_pnl_since.return_value = -150.0
        client.balance_adjustments_since.return_value = 0.0
        now = datetime(2026, 5, 27, 12, 0, tzinfo=timezone.utc)
        start = resolve_day_start_equity(
            client,
            MagicMock(),
            RiskConfig(use_daily_loss_guard=True, max_daily_loss_pct=15.0),
            equity=3000.0,
            now=now,
            stored={"date": "2026-05-27"},
        )
        self.assertEqual(start, 3150.0)

    def test_compute_daily_risk_disabled(self) -> None:
        client = MagicMock()
        client.account_snapshot.return_value = {"equity": 1000.0, "balance": 1000.0, "floating_pnl": 0.0}
        state = MagicMock()
        state.read.return_value = {
            "daily_risk": {
                "enabled": True,
                "halted": True,
                "loss": 1662.17,
                "loss_limit": 398.95,
            }
        }
        risk_cfg = RiskConfig(use_daily_loss_guard=False, max_daily_loss_pct=15.0)
        status = compute_daily_risk_status(client, state, risk_cfg)
        self.assertFalse(status["enabled"])
        self.assertFalse(status["halted"])
        self.assertEqual(status["loss"], 0.0)
        state.update_daily_risk.assert_called_once()
        client.net_pnl_since.assert_not_called()


if __name__ == "__main__":
    unittest.main()
