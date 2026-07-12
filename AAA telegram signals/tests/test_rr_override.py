from app.services.copier_service import CopierService


def test_rr_override_builds_buy_ladder_with_fractional_target():
    assert CopierService._build_rr_take_profit_ladder(
        side="buy",
        entry_price=100.0,
        stop_loss=90.0,
        target_rr=1.5,
        symbol_info={"digits": 2},
    ) == [110.0, 115.0]


def test_rr_override_builds_sell_ladder_to_three_r():
    assert CopierService._build_rr_take_profit_ladder(
        side="sell",
        entry_price=100.0,
        stop_loss=110.0,
        target_rr=3.0,
        symbol_info={"digits": 2},
    ) == [90.0, 80.0, 70.0]
