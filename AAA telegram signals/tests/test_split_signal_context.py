from app.services.copier_service import CopierService


def test_split_signal_message_classifiers():
    header = "BUY LIMIT 4087 - 4085 Sl 4082"
    continuation = "TP 4092 4102 4112 4122 4132 4142"

    assert CopierService._looks_like_signal_header_waiting_for_tps(header) is True
    assert CopierService._looks_like_tp_continuation(continuation) is True
    assert CopierService._looks_like_tp_continuation(header) is False
