import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from crypto_lab.domain.performance import ClosedTrade, performance_table
from crypto_lab.domain.polymarket.fees import NO_FEES
from crypto_lab.domain.polymarket.wallets import (
    ClosedPosition,
    WalletStyle,
    WalletTrade,
    compute_wallet_stats,
    wilson_lower_bound,
)
from crypto_lab.infrastructure.polymarket import mappers

D = Decimal


def _raw_market(**overrides: object) -> dict[str, object]:
    raw: dict[str, object] = {
        "conditionId": "0xabc",
        "question": "Will it rain?",
        "slug": "rain",
        "active": True,
        "closed": False,
        "enableOrderBook": True,
        "acceptingOrders": True,
        "clobTokenIds": json.dumps(["111", "222"]),
        "outcomes": json.dumps(["Yes", "No"]),
        "negRisk": False,
        "feesEnabled": True,
        "feeSchedule": {"exponent": 1, "rate": 0.05, "takerOnly": True, "rebateRate": 0.15},
        "orderPriceMinTickSize": 0.01,
        "orderMinSize": 5,
        "endDate": "2026-10-01T12:00:00Z",
        "volume24hr": 1234.5,
        "liquidityNum": 999,
    }
    raw.update(overrides)
    return raw


class TestMappers:
    def test_market_decodes_json_string_fields_and_fee_schedule(self) -> None:
        m = mappers.market_from_gamma(_raw_market(), "ev1")
        assert m is not None
        assert [t.token_id for t in m.tokens] == ["111", "222"] and m.yes.outcome == "Yes"
        assert m.fees.rate == D("0.05") and m.fees.taker_only is True
        assert m.end_date == datetime(2026, 10, 1, 12, tzinfo=UTC)

    def test_fees_disabled_means_no_fees(self) -> None:
        m = mappers.market_from_gamma(_raw_market(feesEnabled=False), "ev1")
        assert m is not None and m.fees == NO_FEES

    @pytest.mark.parametrize(
        ("fee_type", "rate"), [("crypto_fees_v2", "0.07"), ("politics_fees", "0.04"), ("mystery_fees", "0.07")]
    )
    def test_missing_schedule_falls_back_by_fee_type(self, fee_type: str, rate: str) -> None:
        m = mappers.market_from_gamma(_raw_market(feeSchedule=None, feeType=fee_type), "ev1")
        assert m is not None and m.fees.rate == D(rate)

    def test_non_binary_market_is_skipped(self) -> None:
        assert mappers.market_from_gamma(_raw_market(clobTokenIds=json.dumps(["1"])), "ev") is None

    def test_event_keeps_only_tradeable_markets(self) -> None:
        raw = {
            "id": "9",
            "slug": "e",
            "title": "E",
            "negRisk": True,
            "negRiskAugmented": False,
            "volume24hr": 10,
            "markets": [_raw_market(), _raw_market(conditionId="0xdef", closed=True)],
            "tags": [{"label": "Politics"}],
        }
        e = mappers.event_from_gamma(raw)
        assert e is not None and len(e.markets) == 1 and e.neg_risk and e.tags == ("Politics",)

    def test_book_mapping_normalises_order(self) -> None:
        raw = {
            "asset_id": "111",
            "timestamp": "1790686702472",
            "tick_size": "0.01",
            "min_order_size": "5",
            "bids": [{"price": "0.01", "size": "10"}, {"price": "0.40", "size": "3"}],
            "asks": [{"price": "0.99", "size": "10"}, {"price": "0.42", "size": "4"}],
        }
        b = mappers.book_from_clob(raw)
        assert b is not None and b.best_bid == D("0.40") and b.best_ask == D("0.42")
        assert b.timestamp_ms == 1790686702472

    def test_wallet_trade_parses_epoch_seconds(self) -> None:
        t = mappers.wallet_trade(
            {
                "proxyWallet": "0xAB",
                "asset": "1",
                "conditionId": "c",
                "side": "BUY",
                "size": 8,
                "price": 0.96,
                "timestamp": 1790686698,
                "outcomeIndex": 1,
            }
        )
        assert t is not None and t.wallet == "0xab" and t.at.tzinfo is UTC and t.usdc == D("7.68")


def _closed(pnl: str) -> ClosedPosition:
    return ClosedPosition("0xw", "a", "c", D("0.5"), D(10), D(pnl), D(1), "Yes", "t", "s", "e", None)


def _trade(cid: str, idx: int, price: str, hours: int = 0) -> WalletTrade:
    return WalletTrade(
        "0xw",
        "tx",
        f"a{idx}",
        cid,
        "BUY",
        D(10),
        D(price),
        "Yes",
        idx,
        "t",
        "s",
        "e",
        datetime(2026, 9, 1, tzinfo=UTC) + timedelta(hours=hours),
    )


class TestWalletStats:
    def test_wilson_bound_is_below_raw_rate_and_handles_zero(self) -> None:
        lb = wilson_lower_bound(9, 10)
        assert lb is not None and 0.55 < lb < 0.9
        assert wilson_lower_bound(0, 0) is None

    def test_stats_counts_wins_pf_and_hedged_style(self) -> None:
        stats = compute_wallet_stats(
            [_closed("10"), _closed("5"), _closed("-5")],
            [_trade("c1", 0, "0.4"), _trade("c1", 1, "0.5", 1), _trade("c2", 0, "0.5", 30)],
        )
        assert (stats.wins, stats.losses) == (2, 1)
        assert stats.profit_factor == 3.0 and stats.realized_pnl == D(10)
        assert stats.both_sides_ratio == 0.5 and stats.style is WalletStyle.HEDGED
        assert stats.active_days == 2

    def test_empty_wallet_has_unknown_style(self) -> None:
        stats = compute_wallet_stats([], [])
        assert stats.win_rate is None and stats.style is WalletStyle.UNKNOWN


class TestPerformanceTable:
    def test_standard_metrics_on_a_known_sequence(self) -> None:
        start = datetime(2026, 9, 1, tzinfo=UTC)
        trades = [
            ClosedTrade(start + timedelta(days=d), D(p))
            for d, p in [(0, "10"), (1, "10"), (2, "-5"), (3, "10"), (4, "-10"), (4, "-5")]
        ]
        t = performance_table(trades, D(1000))
        assert t.trades == 6 and t.net_pnl == D(10) and t.return_pct == pytest.approx(1.0)
        assert t.profit_factor == pytest.approx(1.5)
        assert t.win_rate == pytest.approx(0.5)
        assert t.avg_win_streak == pytest.approx(1.5) and t.avg_loss_streak == pytest.approx(1.5)
        assert t.consistency == pytest.approx(3 / 5)
        assert t.max_balance_dd_pct == pytest.approx(15 / 1025 * 100)
        assert t.trades_per_day == pytest.approx(6 / 4)
        assert t.max_equity_dd_pct is None  # missing data stays missing
        assert t.sharpe is not None

    def test_empty_ledger(self) -> None:
        t = performance_table([], D(1000))
        assert t.trades == 0 and t.trades_per_day is None and t.win_rate is None and t.balance_curve == ()
