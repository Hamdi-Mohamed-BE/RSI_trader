import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from rsi_divergence_bot.config import RiskConfig
from rsi_divergence_bot.daily_risk import compute_daily_risk_status, loss_from_day_start


class DailyRiskStatusTests(unittest.TestCase):
    def _mock_client(
        self,
        *,
        equity: float,
        balance: float | None = None,
        floating: float = 0.0,
        login: int = 1001,
        server: str = "Broker-Demo",
        balance_adj: float = 0.0,
    ) -> MagicMock:
        client = MagicMock()
        balance = balance if balance is not None else equity
        client.account_snapshot.return_value = {
            "login": login,
            "server": server,
            "equity": equity,
            "balance": balance,
            "floating_pnl": floating,
        }
        client.balance_adjustments_since.return_value = balance_adj
        return client

    def test_loss_from_day_start(self) -> None:
        self.assertEqual(loss_from_day_start(300.0, 240.0), 60.0)
        self.assertEqual(loss_from_day_start(300.0, 320.0), 0.0)

    def test_new_day_locks_start_equity(self) -> None:
        client = self._mock_client(equity=300.0)
        state = MagicMock()
        state.read.return_value = {"daily_risk": {"date": "2026-05-26", "account_key": "1001@Broker-Demo"}}
        risk_cfg = RiskConfig(use_daily_loss_guard=True, max_daily_loss_pct=20.0)

        with unittest.mock.patch(
            "rsi_divergence_bot.daily_risk.datetime",
            wraps=datetime,
        ) as dt_mock:
            dt_mock.now.return_value = datetime(2026, 5, 27, 8, 0, tzinfo=timezone.utc)
            status = compute_daily_risk_status(client, state, risk_cfg)

        self.assertEqual(status["start_equity"], 300.0)
        self.assertEqual(status["daily_pnl"], 0.0)
        self.assertEqual(status["loss"], 0.0)
        self.assertEqual(status["loss_limit"], 60.0)
        self.assertEqual(status["loss_floor_equity"], 240.0)

    def test_loss_halt_at_twenty_percent_of_start(self) -> None:
        client = self._mock_client(equity=240.0)
        state = MagicMock()
        state.read.return_value = {
            "daily_risk": {
                "date": "2026-05-27",
                "account_key": "1001@Broker-Demo",
                "start_equity": 300.0,
            }
        }
        risk_cfg = RiskConfig(use_daily_loss_guard=True, max_daily_loss_pct=20.0)

        with unittest.mock.patch(
            "rsi_divergence_bot.daily_risk.datetime",
            wraps=datetime,
        ) as dt_mock:
            dt_mock.now.return_value = datetime(2026, 5, 27, 14, 0, tzinfo=timezone.utc)
            status = compute_daily_risk_status(client, state, risk_cfg)

        self.assertEqual(status["start_equity"], 300.0)
        self.assertEqual(status["daily_pnl"], -60.0)
        self.assertEqual(status["loss"], 60.0)
        self.assertEqual(status["loss_limit"], 60.0)
        self.assertTrue(status["loss_halted"])

    def test_win_halt_when_profit_reaches_usd_target(self) -> None:
        client = self._mock_client(equity=500.0)
        state = MagicMock()
        state.read.return_value = {
            "daily_risk": {
                "date": "2026-05-27",
                "account_key": "1001@Broker-Demo",
                "start_equity": 300.0,
            }
        }
        risk_cfg = RiskConfig(
            use_daily_loss_guard=False,
            use_daily_win_guard=True,
            daily_win_target_mode="usd",
            max_daily_win_usd=200.0,
        )

        with unittest.mock.patch(
            "rsi_divergence_bot.daily_risk.datetime",
            wraps=datetime,
        ) as dt_mock:
            dt_mock.now.return_value = datetime(2026, 5, 27, 16, 0, tzinfo=timezone.utc)
            status = compute_daily_risk_status(client, state, risk_cfg)

        self.assertEqual(status["gain"], 200.0)
        self.assertEqual(status["win_goal_equity"], 500.0)
        self.assertTrue(status["win_halted"])
        self.assertEqual(status["halt_reason"], "win")

    def test_same_day_keeps_locked_start(self) -> None:
        client = self._mock_client(equity=280.0)
        state = MagicMock()
        state.read.return_value = {
            "daily_risk": {
                "date": "2026-05-27",
                "account_key": "1001@Broker-Demo",
                "start_equity": 300.0,
            }
        }
        risk_cfg = RiskConfig(use_daily_loss_guard=True, max_daily_loss_pct=20.0)

        with unittest.mock.patch(
            "rsi_divergence_bot.daily_risk.datetime",
            wraps=datetime,
        ) as dt_mock:
            dt_mock.now.return_value = datetime(2026, 5, 27, 12, 0, tzinfo=timezone.utc)
            status = compute_daily_risk_status(client, state, risk_cfg)

        self.assertEqual(status["start_equity"], 300.0)
        self.assertEqual(status["daily_pnl"], -20.0)
        self.assertEqual(status["loss"], 20.0)
        self.assertFalse(status["halted"])

    def test_deposit_does_not_count_as_loss(self) -> None:
        client = self._mock_client(equity=600.0, balance_adj=300.0)
        state = MagicMock()
        state.read.return_value = {
            "daily_risk": {
                "date": "2026-05-27",
                "account_key": "1001@Broker-Demo",
                "start_equity": 300.0,
            }
        }
        risk_cfg = RiskConfig(use_daily_loss_guard=True, max_daily_loss_pct=20.0)

        with unittest.mock.patch(
            "rsi_divergence_bot.daily_risk.datetime",
            wraps=datetime,
        ) as dt_mock:
            dt_mock.now.return_value = datetime(2026, 5, 27, 12, 0, tzinfo=timezone.utc)
            status = compute_daily_risk_status(client, state, risk_cfg)

        self.assertEqual(status["daily_pnl"], 0.0)
        self.assertEqual(status["loss"], 0.0)

    def test_account_switch_resets_start(self) -> None:
        client = self._mock_client(equity=300.0, login=2002, server="Broker-Live")
        state = MagicMock()
        state.read.return_value = {
            "daily_risk": {
                "date": "2026-05-27",
                "account_key": "1001@Broker-Demo",
                "start_equity": 3011.39,
                "halted": True,
            }
        }
        risk_cfg = RiskConfig(use_daily_loss_guard=True, max_daily_loss_pct=15.0)

        with unittest.mock.patch(
            "rsi_divergence_bot.daily_risk.datetime",
            wraps=datetime,
        ) as dt_mock:
            dt_mock.now.return_value = datetime(2026, 5, 27, 12, 0, tzinfo=timezone.utc)
            status = compute_daily_risk_status(client, state, risk_cfg)

        self.assertEqual(status["account_key"], "2002@Broker-Live")
        self.assertEqual(status["start_equity"], 300.0)
        self.assertFalse(status["halted"])

    def test_compute_daily_risk_disabled(self) -> None:
        client = self._mock_client(equity=1000.0)
        state = MagicMock()
        state.read.return_value = {"daily_risk": {"enabled": True, "halted": True}}
        risk_cfg = RiskConfig(use_daily_loss_guard=False, use_daily_win_guard=False)
        status = compute_daily_risk_status(client, state, risk_cfg)
        self.assertFalse(status["enabled"])
        self.assertFalse(status["halted"])
        self.assertEqual(status["loss"], 0.0)
        client.balance_adjustments_since.assert_not_called()


if __name__ == "__main__":
    unittest.main()
