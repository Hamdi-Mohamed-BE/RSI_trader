from app.services.copier_service import CopierService


def test_split_leg_targets_uses_all_tps_when_limit_is_zero():
    assert CopierService._split_leg_targets([101, 102, 103], 0) == [101.0, 102.0, 103.0]


def test_split_leg_targets_respects_max_count():
    assert CopierService._split_leg_targets([101, 102, 103, 104], 2) == [101.0, 102.0]


def test_break_even_trigger_uses_requested_tp_level():
    assert CopierService._break_even_trigger_from_level([101, 102, 103], 2) == 102.0


def test_break_even_trigger_clamps_past_last_tp():
    assert CopierService._break_even_trigger_from_level([101, 102, 103], 10) == 103.0


def test_split_legs_divides_fixed_lot():
    fixed_lot, risk_pct, risk_usd = CopierService._risk_inputs_for_leg(
        "fixed_lot", 1.0, 4.0, 200.0, 4
    )
    assert fixed_lot == 0.25
    assert risk_pct == 4.0
    assert risk_usd == 200.0


def test_split_legs_divides_usd_risk_cap():
    fixed_lot, risk_pct, risk_usd = CopierService._risk_inputs_for_leg(
        "risk_usd_cap", 1.0, 4.0, 200.0, 4
    )
    assert fixed_lot == 1.0
    assert risk_pct == 4.0
    assert risk_usd == 50.0


def test_split_legs_divides_percent_risk():
    fixed_lot, risk_pct, risk_usd = CopierService._risk_inputs_for_leg(
        "risk_percent", 1.0, 4.0, 200.0, 4
    )
    assert fixed_lot == 1.0
    assert risk_pct == 1.0
    assert risk_usd == 200.0
