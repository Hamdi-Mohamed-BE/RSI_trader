from rsi_divergence_bot.telegram_html_parser import is_reply_bubble, looks_like_ad, parse_all_messages, parse_latest_message

SAMPLE_HTML = """
<div class="bubbles-inner">
  <div class="bubble service is-date"><div class="bubble-content">May 22</div></div>
  <div class="bubble" data-mid="998877" data-peer-id="-1001234567890">
    <div class="bubble-content-wrapper">
      <div class="bubble-content">
        <div class="message spoilers-container">
          <span class="translatable-message">XAUUSD BUY
SL 2300
TP1 2350
TP2 2360</span>
        </div>
      </div>
    </div>
    <span class="time" title="22.05.2026, 16:58:41">16:58</span>
  </div>
  <div class="bubble" data-mid="111">
    <div class="message">Join our VIP promo - sponsored ad</div>
  </div>
</div>
"""


def test_parse_latest_message_from_bubble_html() -> None:
    parsed, diagnostics = parse_latest_message(SAMPLE_HTML, skip_ads=True)
    assert parsed is not None
    assert parsed.key == "998877"
    assert "XAUUSD BUY" in parsed.text
    assert diagnostics.bubble_count == 3


def test_parse_latest_message_without_skip_returns_last_even_if_ad() -> None:
    parsed, _ = parse_latest_message(SAMPLE_HTML, skip_ads=False)
    assert parsed is not None
    assert parsed.key == "111"


def test_parse_latest_message_skips_date_bubble() -> None:
    parsed, _ = parse_latest_message(
        '<div class="bubbles-inner"><div class="bubble is-date service">Today</div></div>'
    )
    assert parsed is None


def test_parse_latest_message_skips_trailing_ad() -> None:
    parsed, _ = parse_latest_message(SAMPLE_HTML, skip_ads=True)
    assert parsed is not None
    assert parsed.key == "998877"
    assert "XAUUSD BUY" in parsed.text


def test_looks_like_ad_variants() -> None:
    assert looks_like_ad("Check out this AD for VIP")
    assert looks_like_ad("ad MANISH DIRECT $5")
    assert looks_like_ad("Please add admin to unlock")
    assert not looks_like_ad("XAUUSD BUY SL 2300 TP1 2350")


SIGNAL_BUBBLE_HTML = """
<div class="bubble" data-mid="1001">
  <div class="message-content peer-color-2 text has-reactions has-shadow has-solid-background has-appendix has-footer">
    <div class="content-inner" dir="auto">
      <div class="text-content clearfix with-meta">XAUUSD BUY NOW<br>STOPLOSS @ 4465<br><br>TP @ 4490<br>TP @ 4500<br>TP @ 4540</div>
    </div>
  </div>
</div>
"""

REPLY_BUBBLE_HTML = """
<div class="bubble" data-mid="1002">
  <div class="message-content peer-color-2 text has-subheader has-reactions has-shadow has-solid-background has-appendix has-footer">
    <div class="content-inner with-subheader" dir="auto">
      <div class="message-subheader">
        <div class="EmbeddedMessage">
          <div class="message-text">
            <p class="embedded-text-wrapper">XAUUSD BUY NOW
STOPLOSS @ 4465

TP @ 4490
TP @ 4500
TP @ 4540</p>
          </div>
        </div>
      </div>
      <div class="text-content clearfix with-meta">BOOOOM XAUUSD Flyingg non-stop</div>
    </div>
  </div>
</div>
"""


def test_is_reply_bubble_detects_telegram_web_reply_markup() -> None:
    from bs4 import BeautifulSoup

    reply = BeautifulSoup(REPLY_BUBBLE_HTML, "html.parser").select_one(".bubble")
    signal = BeautifulSoup(SIGNAL_BUBBLE_HTML, "html.parser").select_one(".bubble")
    assert reply is not None and signal is not None
    assert is_reply_bubble(reply)
    assert not is_reply_bubble(signal)


def test_parse_all_messages_skips_replies() -> None:
    html = f'<div class="bubbles-inner">{SIGNAL_BUBBLE_HTML}{REPLY_BUBBLE_HTML}</div>'
    messages, diagnostics = parse_all_messages(html)
    assert len(messages) == 1
    assert messages[0].key == "1001"
    assert "XAUUSD BUY NOW" in messages[0].text
    assert "BOOOOM" not in messages[0].text
    assert diagnostics.reply_count == 1


def test_parse_latest_message_skips_trailing_reply() -> None:
    html = f'<div class="bubbles-inner">{SIGNAL_BUBBLE_HTML}{REPLY_BUBBLE_HTML}</div>'
    parsed, diagnostics = parse_latest_message(html, skip_ads=True)
    assert parsed is not None
    assert parsed.key == "1001"
    assert diagnostics.reply_count == 1
