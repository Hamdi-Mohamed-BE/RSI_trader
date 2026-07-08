from app.telegram.poller import parse_chat_reference


def test_parse_chat_reference_supports_web_and_private_links():
    assert parse_chat_reference("https://web.telegram.org/a/#-1001184623065") == -1001184623065
    assert parse_chat_reference("https://web.telegram.org/k/#-1001303328644") == -1001303328644
    assert parse_chat_reference("https://t.me/c/1184623065/42") == -1001184623065
    assert parse_chat_reference("-1001184623065") == -1001184623065
    assert parse_chat_reference("channel_username") == "channel_username"
