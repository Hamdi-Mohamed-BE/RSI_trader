from yt_stream_copy.interpreter import ContextInterpreter, interpret


def test_confirmed_gold_entry():
    signal = interpret("I am buying gold now. Entry 4320.5, stop loss 4310, target 4341.5", "Lorenzo")
    assert signal is not None
    assert signal["status"] == "confirmed_entry"
    assert signal["symbol"] == "XAUUSD"
    assert signal["side"] == "buy"
    assert signal["entry"] == 4320.5
    assert signal["stop_loss"] == 4310
    assert signal["take_profit"] == 4341.5
    assert signal["mt5_comment"] == "Stream Lorenzo"


def test_hypothetical_is_not_confirmed():
    signal = interpret("I might buy Nasdaq if price comes lower", "Lorenzo")
    assert signal is not None
    assert signal["status"] == "watching"


def test_non_trade_is_ignored():
    assert interpret("Good morning everyone", "Lorenzo") is None


def test_fragmented_stream_entry_is_confirmed_with_context():
    detector = ContextInterpreter("Lorenzo Corrado")
    detector.feed("The dollar was pushing but gold did not break down")
    signal = detector.feed("I am going to try to buy here my friends")
    assert signal is not None
    assert signal["status"] == "confirmed_entry"
    assert signal["symbol"] == "XAUUSD"
    assert signal["side"] == "buy"


def test_press_buy_uses_recent_symbol():
    detector = ContextInterpreter("Lorenzo")
    detector.feed("Gold is holding the daily demand zone")
    signal = detector.feed("press buy thank you very much")
    assert signal is not None
    assert signal["status"] == "confirmed_entry"
    assert signal["symbol"] == "XAUUSD"


def test_candle_close_is_not_exit_but_position_close_is():
    detector = ContextInterpreter("Lorenzo")
    detector.feed("I am buying gold")
    assert detector.feed("we closed above the sellers and above VWAP") is None
    signal = detector.feed("I closed the position")
    assert signal is not None
    assert signal["status"] == "exit_reported"


def test_stop_and_target_can_arrive_after_entry():
    detector = ContextInterpreter("Lorenzo")
    detector.feed("I am buying gold")
    update = detector.feed("my stop loss is at 4402 and target 4449")
    assert update is not None
    assert update["status"] == "level_update"
    assert update["stop_loss"] == 4402
    assert update["take_profit"] == 4449
