from usenet_no.mbox_utils import parse_message_id


def test_extracts_angle_bracket_id():
    assert parse_message_id("<abc123@example.com>") == "<abc123@example.com>"


def test_lowercases_result():
    assert parse_message_id("<ABC@Example.COM>") == "<abc@example.com>"


def test_strips_ia_trailing_junk():
    assert (
        parse_message_id("<3334F293.5A03@eller.no>#1/1") == "<3334f293.5a03@eller.no>"
    )


def test_returns_none_for_none():
    assert parse_message_id(None) is None


def test_returns_none_for_empty_string():
    assert parse_message_id("") is None


def test_returns_none_when_no_angle_brackets():
    assert parse_message_id("no-brackets-here") is None
