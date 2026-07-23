from app.services.copier_service import CopierService
from app.llm.schemas import SignalParseSchema


def test_split_signal_message_classifiers():
    header = "BUY LIMIT 4087 - 4085 Sl 4082"
    continuation = "TP 4092 4102 4112 4122 4132 4142"

    assert CopierService._looks_like_signal_header_waiting_for_tps(header) is True
    assert CopierService._looks_like_tp_continuation(continuation) is True
    assert CopierService._looks_like_tp_continuation(header) is False


def test_copier_defaults_missing_symbol_to_xauusd_for_gold_prices():
    parsed = SignalParseSchema(
        is_signal=True,
        confidence=1.0,
        message_type="signal",
        symbol_raw=None,
        side="buy",
        order_type="pending",
        pending_type="buy_limit",
        entry_price=4065.0,
        stop_loss=4055.0,
        take_profits=[4150.0],
        final_take_profit=4150.0,
        break_even_trigger_tp=4065.0,
    )

    inferred = CopierService._infer_missing_symbol_from_signal_prices("", parsed)

    assert inferred == "XAUUSD"
