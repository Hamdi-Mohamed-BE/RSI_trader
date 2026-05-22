from rsi_divergence_bot.telegram_html_parser import looks_like_ad, parse_all_messages, parse_latest_message

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
