from us100_bot.models import SymbolSpec
from us100_bot.normalization import PriceNormalizer


def test_strategy_pip_conversion():
    spec = SymbolSpec(
        "UT100", "US Tech 100 Index", "Cash Indices", 2, 0.01, 0.01,
        0.01, 1.0, 0.01, 50, 0.01, 0, 0, 170, 4, 3, True,
    )
    norm = PriceNormalizer(spec, 1.0)
    assert norm.pips_to_broker_points(1) == 100
    assert norm.pips_to_ticks(1) == 100
    assert norm.risk_per_lot(50) == 50
    assert norm.money_for_move(0.5, 100) == 50


def test_volume_rounding_never_exceeds_request():
    spec = SymbolSpec(
        "UT100", "", "", 2, 0.01, 0.01, 0.01, 1.0,
        0.01, 50, 0.01, 0, 0, 1, 4, 3, True,
    )
    norm = PriceNormalizer(spec)
    assert norm.round_volume(0.126) == 0.12

