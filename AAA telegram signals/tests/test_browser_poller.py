from app.telegram.browser_poller import BrowserTelegramPoller, normalize_telegram_web_url


def test_normalize_telegram_web_url_keeps_existing_web_link():
    link = "https://web.telegram.org/k/#-1184623065"

    assert normalize_telegram_web_url(link) == link


def test_normalize_telegram_web_url_maps_private_channel_id():
    assert normalize_telegram_web_url("-1001184623065") == "https://web.telegram.org/k/#-1184623065"


def test_browser_message_extraction_from_basic_html():
    html = """
    <div class="message" data-message-id="101">
      XAUUSD BUY NOW<br>SL @ 2400<br>TP @ 2410
    </div>
    <div class="message" data-message-id="102">profit secured</div>
    """

    messages = BrowserTelegramPoller._extract_messages(html)

    assert len(messages) == 2
    assert messages[0].id == 101
    assert "XAUUSD BUY NOW" in messages[0].text
