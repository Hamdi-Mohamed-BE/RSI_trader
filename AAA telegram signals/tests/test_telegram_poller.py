from app.telegram.poller import _candidate_numeric_ids, parse_chat_reference


def test_parse_chat_reference_supports_web_and_private_links():
    assert parse_chat_reference("https://web.telegram.org/a/#-1001184623065") == -1001184623065
    assert parse_chat_reference("https://web.telegram.org/k/#-1001303328644") == -1001303328644
    assert parse_chat_reference("https://web.telegram.org/k/#-1184623065") == -1001184623065
    assert parse_chat_reference("https://web.telegram.org/k/#@alhimmer") == "alhimmer"
    assert parse_chat_reference("https://t.me/c/1184623065/42") == -1001184623065
    assert parse_chat_reference("https://t.me/alhimmer") == "alhimmer"
    assert parse_chat_reference("-1001184623065") == -1001184623065
    assert parse_chat_reference("@alhimmer") == "alhimmer"
    assert parse_chat_reference("channel_username") == "channel_username"


def test_candidate_numeric_ids_include_marked_and_raw_channel_id():
    assert _candidate_numeric_ids(-1005154968317) == {1005154968317, 5154968317}
