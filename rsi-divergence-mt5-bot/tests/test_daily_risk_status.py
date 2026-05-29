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

    def test_peak_equity_sets_loss_limit(self) -> None:
        client = MagicMock()
        client.account_snapshot.return_value = {
            "equity": 1530.0,
            "balance": 1530.0,
            "floating_pnl": 0.0,
        }
        state = MagicMock()
        state.read.return_value = {
            "daily_risk": {
                "date": "2026-05-27",
                "start_equity": 1000.0,
                "peak_equity": 1800.0,
                "created_at": "2026-05-27T00:05:00+00:00",
            }
        }
        risk_cfg = RiskConfig(use_daily_loss_guard=True, max_daily_loss_pct=15.0)

        with unittest.mock.patch(
            "rsi_divergence_bot.daily_risk.datetime",
            wraps=datetime,
        ) as dt_mock:
            dt_mock.now.return_value = datetime(2026, 5, 27, 15, 0, tzinfo=timezone.utc)
            status = compute_daily_risk_status(client, state, risk_cfg)

        self.assertEqual(status["peak_equity"], 1800.0)
        self.assertEqual(status["loss"], 270.0)
        self.assertEqual(status["loss_limit"], 270.0)
        self.assertTrue(status["halted"])

    def test_daily_win_guard_halts_from_start_of_day_gain(self) -> None:
        client = MagicMock()
        client.account_snapshot.return_value = {
            "equity": 1150.0,
            "balance": 1150.0,
            "floating_pnl": 0.0,
        }
        state = MagicMock()
        state.read.return_value = {
            "daily_risk": {
                "date": "2026-05-27",
                "start_equity": 1000.0,
                "created_at": "2026-05-27T00:05:00+00:00",
            }
        }
        risk_cfg = RiskConfig(
            use_daily_loss_guard=False,
            use_daily_win_guard=True,
            daily_win_target_mode="percent",
            max_daily_win_pct=10.0,
        )

        with unittest.mock.patch(
            "rsi_divergence_bot.daily_risk.datetime",
            wraps=datetime,
        ) as dt_mock:
            dt_mock.now.return_value = datetime(2026, 5, 27, 16, 0, tzinfo=timezone.utc)
            status = compute_daily_risk_status(client, state, risk_cfg)

        self.assertEqual(status["gain"], 150.0)
        self.assertEqual(status["win_target"], 100.0)
        self.assertTrue(status["win_halted"])
        self.assertEqual(status["halt_reason"], "win")
        self.assertTrue(status["halted"])

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
        risk_cfg = RiskConfig(use_daily_loss_guard=False, use_daily_win_guard=False, max_daily_loss_pct=15.0)
        status = compute_daily_risk_status(client, state, risk_cfg)
        self.assertFalse(status["enabled"])
        self.assertFalse(status["halted"])
        self.assertEqual(status["loss"], 0.0)
        state.update_daily_risk.assert_called_once()
        client.net_pnl_since.assert_not_called()


if __name__ == "__main__":
    unittest.main()
