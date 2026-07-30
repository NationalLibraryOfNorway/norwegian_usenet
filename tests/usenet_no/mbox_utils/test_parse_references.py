from usenet_no.mbox_utils import parse_references


def test_single_reference():
    assert parse_references("<abc@example.com>") == ["<abc@example.com>"]


def test_multiple_references():
    raw = "<a@x.com> <b@x.com> <c@x.com>"
    assert parse_references(raw) == ["<a@x.com>", "<b@x.com>", "<c@x.com>"]


def test_lowercases_results():
    assert parse_references("<ABC@Example.COM>") == ["<abc@example.com>"]


def test_returns_empty_list_for_none():
    assert parse_references(None) == []


def test_returns_empty_list_for_empty_string():
    assert parse_references("") == []


def test_real_world_references_header():
    raw = (
        "<01bc818b$a1e7ede0$a8d9ccc3@vbs-mm3riksnett> "
        "<33B1787D.2425@tvedestrand.mail.telia.com> "
        "<33B22529.4E9F@jusit.uoi.no>"
    )
    result = parse_references(raw)
    assert result == [
        "<01bc818b$a1e7ede0$a8d9ccc3@vbs-mm3riksnett>",
        "<33b1787d.2425@tvedestrand.mail.telia.com>",
        "<33b22529.4e9f@jusit.uoi.no>",
    ]
