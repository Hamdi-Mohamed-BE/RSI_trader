from pathlib import Path
from dataclasses import replace
from types import SimpleNamespace

import pandas as pd

from rsi_divergence_bot.backtest import _build_daily_performance
from rsi_divergence_bot.config import AppConfig
from rsi_divergence_bot.decision import evaluate_trade_signal
from rsi_divergence_bot.state import StateStore
from rsi_divergence_bot.strategy import Signal
from rsi_divergence_bot.trade_execution import simulate_split_trade
from rsi_divergence_bot.trade_geometry import invalid_market_geometry
from rsi_divergence_bot.trader import TradeExecutor


class _Client:
    TRADE_DONE = 10009

    def __init__(self, *, bid=104.9, ask=105.0):
        self.sent = 0
        self._bid = bid
        self._ask = ask

    def tick(self, _symbol):
        return {"bid": self._bid, "ask": self._ask}

    def spread_price(self, _symbol):
        return 0.1

    def money_for_distance(self, _symbol, volume, price_distance):
        return volume * price_distance

    def normalize_volume(self, _symbol, volume):
        return volume

    def positions(self):
        return []

    def send_market(self, *_args, **_kwargs):
        self.sent += 1


def _config(tmp_path: Path) -> AppConfig:
    return AppConfig.model_validate(
        {
            "bot": {"dry_run": False, "state_file": str(tmp_path / "state.json"), "trade_decision_profile": "backtest"},
            "symbols": [{"symbol": "EURUSD", "name": "Euro / US Dollar", "lot_per_leg": 0.01}],
        }
    )


def _signal(side: str, entry: float, sl: float, tps: list[float]) -> Signal:
    return Signal(
        setup_id="abc",
        symbol="EURUSD",
        market_key="EURUSD",
        name="Euro / US Dollar",
        side=side,
        time="2026-05-24T00:00:00+00:00",
        entry=entry,
        sl=sl,
        tps=tps,
        lot_per_leg=0.01,
        risk_distance=abs(entry - sl),
        session="test",
        reason="test",
    )


def test_geometry_rejects_wrong_side_take_profit():
    assert invalid_market_geometry("buy", 105.0, 104.0, [104.5]) is not None
    assert invalid_market_geometry("sell", 104.9, 106.0, [105.5]) is not None
    assert invalid_market_geometry("buy", 105.0, 104.0, [106.0]) is None
    assert invalid_market_geometry("sell", 104.9, 106.0, [103.0]) is None


def test_decision_rejects_inverted_signal(tmp_path):
    config = _config(tmp_path)
    decision = evaluate_trade_signal(_Client(), config, _signal("buy", 100.0, 99.0, [98.0]), config.symbols[0])

    assert decision.allowed is False
    assert decision.code == "geometry"


def test_executor_does_not_send_stale_tp(tmp_path):
    config = _config(tmp_path)
    client = _Client()
    executor = TradeExecutor(config, client, StateStore(config.bot.state_file), logger=type("L", (), {"warning": lambda *a, **k: None})())

    result = executor.place_market_setup(
        setup_id="manual",
        symbol="EURUSD",
        market_key="EURUSD",
        side="buy",
        sl=104.0,
        tps=[104.5],
        lot_per_leg=0.01,
    )

    assert result["status"] == "skipped"
    assert client.sent == 0


def test_executor_rejects_adverse_live_entry_drift(tmp_path):
    config = _config(tmp_path)
    client = _Client(bid=100.7, ask=100.8)
    executor = TradeExecutor(config, client, StateStore(config.bot.state_file), logger=type("L", (), {"warning": lambda *a, **k: None})())

    result = executor.place_market_setup(
        setup_id="drift",
        symbol="EURUSD",
        market_key="EURUSD",
        side="buy",
        sl=99.0,
        tps=[101.5],
        lot_per_leg=0.01,
        entry_price=100.0,
    )

    assert result["status"] == "skipped"
    assert "drift" in result["reason"]
    assert client.sent == 0


def test_split_backtest_reports_each_tp_leg():
    client = _Client()
    signal = _signal("buy", 100.0, 90.0, [110.0, 120.0, 130.0])
    signal = replace(signal, lot_per_leg=2.0)
    rows = [
        SimpleNamespace(time=pd.Timestamp("2026-05-24T12:00:00Z"), high=111.0, low=99.0, close=105.0),
        SimpleNamespace(time=pd.Timestamp("2026-05-24T12:05:00Z"), high=121.0, low=105.0, close=115.0),
        SimpleNamespace(time=pd.Timestamp("2026-05-24T12:10:00Z"), high=131.0, low=115.0, close=125.0),
    ]

    result = simulate_split_trade(client, signal, rows, tp_protection=False)

    assert result["pnl"] == 120.0
    assert [leg["leg"] for leg in result["legs"]] == [1, 2, 3]
    assert [leg["tp"] for leg in result["legs"]] == [110.0, 120.0, 130.0]
    assert [leg["pnl"] for leg in result["legs"]] == [20.0, 40.0, 60.0]


def test_daily_performance_counts_position_legs():
    daily = _build_daily_performance(
        [
            {
                "symbol": "BTCUSD",
                "side": "buy",
                "entry_time": "2026-05-24T12:00:00+00:00",
                "exit_time": "2026-05-24T12:05:00+00:00",
                "exit_kind": "tp1",
                "pnl": 10.0,
                "sort_time": 1779624300,
                "leg": 1,
                "legs": 3,
                "entry": 100.0,
                "sl": 90.0,
                "tp": 110.0,
                "lot": 1.0,
                "exit_price": 110.0,
            },
            {
                "symbol": "BTCUSD",
                "side": "buy",
                "entry_time": "2026-05-24T12:00:00+00:00",
                "exit_time": "2026-05-24T12:10:00+00:00",
                "exit_kind": "tp2",
                "pnl": 20.0,
                "sort_time": 1779624600,
                "leg": 2,
                "legs": 3,
                "entry": 100.0,
                "sl": 90.0,
                "tp": 120.0,
                "lot": 1.0,
                "exit_price": 120.0,
            },
        ],
        1000.0,
    )

    assert daily[0]["trades"] == 2
    assert daily[0]["wins"] == 2
    assert daily[0]["trade_rows"][0]["leg"] == 1
    assert daily[0]["trade_rows"][0]["entry"] == 100.0
    assert daily[0]["trade_rows"][0]["sl"] == 90.0
    assert daily[0]["trade_rows"][0]["tp"] == 110.0
