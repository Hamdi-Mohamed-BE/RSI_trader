from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from crypto_lab.domain.polymarket.arbitrage import (
    ComplementBuyMergeDetector,
    ComplementSplitSellDetector,
    NegRiskBasketBuyDetector,
    OpportunityKind,
    ScanConfig,
)
from crypto_lab.domain.polymarket.fees import FeeSchedule
from crypto_lab.domain.polymarket.orderbook import PriceLevel
from tests.polymarket_factories import NOW, book, event, market

D = Decimal
CRYPTO_FEES = FeeSchedule(rate=D("0.07"))
SMALL = ScanConfig(share_sizes=(D(10), D(100)), min_net_edge_usdc=D("0.01"), min_edge_pct=D(0))


class TestOrderBook:
    def test_build_sorts_and_drops_invalid_levels(self) -> None:
        b = book(
            "t", asks=[("0.60", "5"), ("0.55", "5"), ("1.00", "9")], bids=[("0.40", "5"), ("0.45", "0"), ("0.50", "3")]
        )
        assert b.best_ask == D("0.55") and b.best_bid == D("0.50")
        assert [lv.price for lv in b.asks] == [D("0.55"), D("0.60")]
        assert all(lv.size > 0 for lv in b.bids)

    def test_buy_walks_levels_and_reports_vwap(self) -> None:
        fill = book("t", asks=[("0.50", "10"), ("0.60", "10")]).buy(D(15))
        assert fill is not None
        assert fill.notional == D("8.00")  # 10*0.50 + 5*0.60
        assert fill.average_price == D("8.00") / D(15)
        assert fill.worst_price == D("0.60") and fill.levels_used == 2

    def test_insufficient_depth_returns_none(self) -> None:
        assert book("t", asks=[("0.5", "3")]).buy(D(5)) is None

    def test_non_positive_size_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            book("t", asks=[("0.5", "3")]).buy(D(0))


class TestFees:
    def test_documented_example_100_crypto_shares_at_50_cents_costs_1_75(self) -> None:
        assert CRYPTO_FEES.taker_fee_at(D(100), D("0.5")) == D("1.75000")

    def test_fee_is_rounded_to_five_decimals(self) -> None:
        assert CRYPTO_FEES.taker_fee_at(D(1), D("0.333")) == D("0.01555")

    def test_walked_fill_is_charged_per_level(self) -> None:
        fill = book("t", asks=[("0.50", "10"), ("0.90", "10")]).buy(D(20))
        assert fill is not None
        expected = CRYPTO_FEES.taker_fee_at(D(10), D("0.50")) + CRYPTO_FEES.taker_fee_at(D(10), D("0.90"))
        assert CRYPTO_FEES.taker_fee(fill) == expected

    def test_makers_pay_nothing_when_taker_only(self) -> None:
        assert CRYPTO_FEES.maker_fee(D(100), D("0.5")) == 0


class TestComplementBuyMerge:
    def test_detects_pair_below_one_dollar_after_fees(self) -> None:
        m = market("c1")
        books = {"c1-yes": book("c1-yes", asks=[("0.45", "500")]), "c1-no": book("c1-no", asks=[("0.50", "500")])}
        [opp] = ComplementBuyMergeDetector().detect(event(m), books, SMALL, NOW)
        assert opp.kind is OpportunityKind.COMPLEMENT_BUY_MERGE
        assert opp.shares == D(100)  # the larger size has the larger absolute edge
        assert opp.capital == D("95.00") and opp.payout == D(100) and opp.net_edge == D("5.00")
        assert opp.holds_to_resolution is False and opp.days_locked() == 0

    def test_fees_can_remove_the_edge(self) -> None:
        m = market("c1", fees=CRYPTO_FEES)
        # 0.49 + 0.50 = 0.99 per pair, but ~0.035 fees per pair make it unprofitable.
        books = {"c1-yes": book("c1-yes", asks=[("0.49", "500")]), "c1-no": book("c1-no", asks=[("0.50", "500")])}
        assert ComplementBuyMergeDetector().detect(event(m), books, SMALL, NOW) == []

    def test_thin_book_limits_size(self) -> None:
        m = market("c1")
        books = {"c1-yes": book("c1-yes", asks=[("0.40", "20")]), "c1-no": book("c1-no", asks=[("0.40", "500")])}
        [opp] = ComplementBuyMergeDetector().detect(event(m), books, SMALL, NOW)
        assert opp.shares == D(10)

    def test_missing_book_is_skipped(self) -> None:
        books = {"c1-yes": book("c1-yes", asks=[("0.10", "500")])}
        assert ComplementBuyMergeDetector().detect(event(market("c1")), books, SMALL, NOW) == []


class TestComplementSplitSell:
    def test_detects_bids_summing_above_one_dollar(self) -> None:
        m = market("c1")
        books = {"c1-yes": book("c1-yes", bids=[("0.55", "500")]), "c1-no": book("c1-no", bids=[("0.50", "500")])}
        [opp] = ComplementSplitSellDetector().detect(event(m), books, SMALL, NOW)
        assert opp.capital == D(100) and opp.payout == D("105.00") and opp.net_edge == D("5.00")


class TestNegRiskBasket:
    def _setup(self, prices: tuple[str, ...]) -> tuple[list, dict]:  # type: ignore[type-arg]
        markets = [market(f"m{i}", neg_risk=True, title=f"Outcome {i}") for i in range(len(prices))]
        books = {f"m{i}-yes": book(f"m{i}-yes", asks=[(p, "500")]) for i, p in enumerate(prices)}
        return markets, books

    def test_detects_complete_basket_below_one_dollar(self) -> None:
        markets, books = self._setup(("0.30", "0.30", "0.30"))
        [opp] = NegRiskBasketBuyDetector().detect(event(*markets, neg_risk=True), books, SMALL, NOW)
        assert opp.net_edge == D("10.00") and opp.holds_to_resolution is True
        assert opp.days_locked() == D(str((opp.resolves_at - NOW).total_seconds() / 86400))  # type: ignore[operator]
        assert opp.annualised_pct() is not None

    def test_augmented_event_is_never_treated_as_complete(self) -> None:
        markets, books = self._setup(("0.30", "0.30", "0.30"))
        assert (
            NegRiskBasketBuyDetector().detect(event(*markets, neg_risk=True, augmented=True), books, SMALL, NOW) == []
        )

    def test_non_neg_risk_event_is_ignored(self) -> None:
        markets, books = self._setup(("0.30", "0.30", "0.30"))
        assert NegRiskBasketBuyDetector().detect(event(*markets), books, SMALL, NOW) == []

    def test_missing_outcome_book_breaks_the_guarantee(self) -> None:
        markets, books = self._setup(("0.30", "0.30", "0.30"))
        del books["m2-yes"]
        assert NegRiskBasketBuyDetector().detect(event(*markets, neg_risk=True), books, SMALL, NOW) == []


def test_min_order_size_filters_small_sizes() -> None:
    m = market("c1", min_size="50")
    books = {"c1-yes": book("c1-yes", asks=[("0.45", "500")]), "c1-no": book("c1-no", asks=[("0.50", "500")])}
    [opp] = ComplementBuyMergeDetector().detect(event(m), books, replace(SMALL, share_sizes=(D(10), D(60))), NOW)
    assert opp.shares == D(60)


def test_opportunity_fingerprint_is_stable_across_sizes() -> None:
    m = market("c1")
    books = {"c1-yes": book("c1-yes", asks=[("0.45", "500")]), "c1-no": book("c1-no", asks=[("0.50", "500")])}
    a = ComplementBuyMergeDetector().detect(event(m), books, SMALL, NOW)[0]
    b = ComplementBuyMergeDetector().detect(event(m), books, SMALL, NOW + timedelta(seconds=5))[0]
    assert a.fingerprint == b.fingerprint == "complement_buy_merge:c1"


def test_price_level_is_a_value_object() -> None:
    assert PriceLevel(D("0.5"), D(1)) == PriceLevel(D("0.50"), D("1.0"))
