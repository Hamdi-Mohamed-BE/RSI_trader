from types import SimpleNamespace

from app.telegram.filters import filter_message, looks_like_trade_signal


def test_trade_signal_with_disclaimer_is_not_filtered_before_parser():
    text = """
    SCALP IDEA
    I AM SELLING XAUUSD (GOLD)
    Entry point : 4056-4060
    Stop Loss : 4062
    TP 1 : 4055
    TP 2 : 4054
    TP 3 : 4052
    For educational purposes only. This is not financial advice.
    """
    message = SimpleNamespace(text=text, fwd_from=None, reply_to=None)

    assert looks_like_trade_signal(text) is True
    assert filter_message(message) == (False, None)


def test_plain_result_message_is_still_filtered():
    message = SimpleNamespace(text="TP all done profit 120 pips", fwd_from=None, reply_to=None)

    assert filter_message(message) == (True, "result")
