import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from rsi_divergence_bot.config import RiskConfig
from rsi_divergence_bot.daily_risk import compute_daily_risk_status, resolve_day_start_equity


class DailyRiskStatusTests(unittest.TestCase):
    def _mock_client(
        self,
        *,
        equity: float,
        balance: float | None = None,
        floating: float = 0.0,
        login: int = 1001,
        server: str = "Broker-Demo",
        net_pnl: float = 0.0,
        balance_adj: float = 0.0,
        peak: float | None = None,
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
        client.net_pnl_since.return_value = net_pnl
        client.balance_adjustments_since.return_value = balance_adj
        client.intraday_balance_peak_since.return_value = peak if peak is not None else balance
        return client

    def test_new_day_snapshots_current_equity(self) -> None:
        client = self._mock_client(
            equity=3398.5,
            balance=3781.46,
            floating=-382.96,
            net_pnl=0.0,
            peak=3781.46,
        )
        state = MagicMock()
        state.read.return_value = {
            "daily_risk": {
                "date": "2026-05-26",
                "account_key": "1001@Broker-Demo",
                "start_equity": 1000.0,
            }
        }
        risk_cfg = RiskConfig(use_daily_loss_guard=True, max_daily_loss_pct=15.0)

        with unittest.mock.patch(
            "rsi_divergence_bot.daily_risk.datetime",
            wraps=datetime,
        ) as dt_mock:
            dt_mock.now.return_value = datetime(2026, 5, 27, 12, 0, tzinfo=timezone.utc)
            status = compute_daily_risk_status(client, state, risk_cfg)

        # equity + floating = start when no closed P/L today (open loss only)
        self.assertEqual(status["start_equity"], 3781.46)
        self.assertEqual(status["daily_pnl"], -382.96)
        self.assertEqual(status["loss"], 382.96)
        self.assertFalse(status["halted"])
        self.assertEqual(status["data_source"], "mt5")

    def test_same_day_keeps_locked_start_and_running_peak(self) -> None:
        client = self._mock_client(
            equity=300.0,
            balance=300.0,
            floating=0.0,
            net_pnl=-50.0,
            balance_adj=0.0,
        )
        state = MagicMock()
        state.read.return_value = {
            "daily_risk": {
                "date": "2026-05-27",
                "account_key": "1001@Broker-Demo",
                "start_equity": 350.0,
                "peak_equity": 350.0,
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

        self.assertEqual(status["start_equity"], 350.0)
        self.assertEqual(status["peak_equity"], 350.0)
        self.assertEqual(status["daily_pnl"], -50.0)
        self.assertEqual(status["loss"], 50.0)
        self.assertEqual(status["loss_limit"], round(350.0 * 0.15, 2))
        self.assertFalse(status["halted"])
        client.intraday_balance_peak_since.assert_not_called()

    def test_account_switch_resets_context(self) -> None:
        client = self._mock_client(
            equity=300.0,
            login=2002,
            server="Broker-Live",
            net_pnl=0.0,
            peak=300.0,
        )
        state = MagicMock()
        state.read.return_value = {
            "daily_risk": {
                "date": "2026-05-27",
                "account_key": "1001@Broker-Demo",
                "start_equity": 3011.39,
                "peak_equity": 3011.39,
                "halted": True,
                "halt_reason": "loss",
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

    def test_peak_equity_sets_loss_limit(self) -> None:
        client = self._mock_client(
            equity=1530.0,
            net_pnl=-270.0,
            floating=0.0,
        )
        state = MagicMock()
        state.read.return_value = {
            "daily_risk": {
                "date": "2026-05-27",
                "account_key": "1001@Broker-Demo",
                "start_equity": 1800.0,
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
        client = self._mock_client(equity=1150.0, net_pnl=150.0, floating=0.0, peak=1150.0)
        state = MagicMock()
        state.read.return_value = {
            "daily_risk": {
                "date": "2026-05-27",
                "account_key": "1001@Broker-Demo",
                "start_equity": 1000.0,
                "created_at": "2026-05-27T00:05:00+00:00",
            }
        }
        client.net_pnl_since.return_value = 150.0
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
        start = resolve_day_start_equity(client, equity=3000.0, now=now, floating_pnl=-25.0)
        self.assertEqual(start, 3175.0)

    def test_gave_back_intraday_gain_shows_drawdown_not_day_pnl(self) -> None:
        client = self._mock_client(equity=301.84, balance=301.84, floating=0.0, net_pnl=0.0)
        state = MagicMock()
        state.read.return_value = {
            "daily_risk": {
                "date": "2026-05-31",
                "account_key": "1001@Broker-Demo",
                "start_equity": 301.84,
                "peak_equity": 303.68,
            }
        }
        risk_cfg = RiskConfig(use_daily_loss_guard=True, max_daily_loss_pct=20.0)

        with unittest.mock.patch(
            "rsi_divergence_bot.daily_risk.datetime",
            wraps=datetime,
        ) as dt_mock:
            dt_mock.now.return_value = datetime(2026, 5, 31, 7, 55, tzinfo=timezone.utc)
            status = compute_daily_risk_status(client, state, risk_cfg)

        self.assertEqual(status["start_equity"], 301.84)
        self.assertEqual(status["peak_equity"], 303.68)
        self.assertEqual(status["daily_pnl"], 0.0)
        self.assertEqual(status["loss"], 1.84)

    def test_open_floating_profit_does_not_raise_peak(self) -> None:
        client = self._mock_client(
            equity=301.84,
            balance=300.0,
            floating=1.84,
            net_pnl=0.0,
        )
        state = MagicMock()
        state.read.return_value = {
            "daily_risk": {
                "date": "2026-05-31",
                "account_key": "1001@Broker-Demo",
                "start_equity": 300.0,
                "peak_equity": 300.0,
            }
        }
        risk_cfg = RiskConfig(use_daily_loss_guard=True, max_daily_loss_pct=20.0)

        with unittest.mock.patch(
            "rsi_divergence_bot.daily_risk.datetime",
            wraps=datetime,
        ) as dt_mock:
            dt_mock.now.return_value = datetime(2026, 5, 31, 7, 55, tzinfo=timezone.utc)
            status = compute_daily_risk_status(client, state, risk_cfg)

        self.assertEqual(status["closed_balance"], 300.0)
        self.assertEqual(status["peak_equity"], 300.0)
        self.assertEqual(status["daily_pnl"], 1.84)
        self.assertEqual(status["loss"], 0.0)

    def test_peak_rises_after_closed_profit(self) -> None:
        client = self._mock_client(
            equity=303.68,
            balance=303.68,
            floating=0.0,
            net_pnl=3.68,
        )
        state = MagicMock()
        state.read.return_value = {
            "daily_risk": {
                "date": "2026-05-31",
                "account_key": "1001@Broker-Demo",
                "start_equity": 300.0,
                "peak_equity": 300.0,
            }
        }
        risk_cfg = RiskConfig(use_daily_loss_guard=True, max_daily_loss_pct=20.0)

        with unittest.mock.patch(
            "rsi_divergence_bot.daily_risk.datetime",
            wraps=datetime,
        ) as dt_mock:
            dt_mock.now.return_value = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
            status = compute_daily_risk_status(client, state, risk_cfg)

        self.assertEqual(status["peak_equity"], 303.68)
        self.assertEqual(status["loss"], 0.0)

    def test_compute_daily_risk_disabled(self) -> None:
        client = self._mock_client(equity=1000.0)
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
