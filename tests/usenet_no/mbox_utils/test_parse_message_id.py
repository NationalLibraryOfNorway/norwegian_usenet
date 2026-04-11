from usenet_no.mbox_utils import parse_message_id, parse_references


class TestParseMessageId:
    def test_extracts_angle_bracket_id(self):
        assert parse_message_id("<abc123@example.com>") == "<abc123@example.com>"

    def test_lowercases_result(self):
        assert parse_message_id("<ABC@Example.COM>") == "<abc@example.com>"

    def test_strips_ia_trailing_junk(self):
        assert (
            parse_message_id("<3334F293.5A03@eller.no>#1/1")
            == "<3334f293.5a03@eller.no>"
        )

    def test_returns_none_for_none(self):
        assert parse_message_id(None) is None

    def test_returns_none_for_empty_string(self):
        assert parse_message_id("") is None

    def test_returns_none_when_no_angle_brackets(self):
        assert parse_message_id("no-brackets-here") is None


class TestParseReferences:
    def test_single_reference(self):
        assert parse_references("<abc@example.com>") == ["<abc@example.com>"]

    def test_multiple_references(self):
        raw = "<a@x.com> <b@x.com> <c@x.com>"
        assert parse_references(raw) == ["<a@x.com>", "<b@x.com>", "<c@x.com>"]

    def test_lowercases_results(self):
        assert parse_references("<ABC@Example.COM>") == ["<abc@example.com>"]

    def test_returns_empty_list_for_none(self):
        assert parse_references(None) == []

    def test_returns_empty_list_for_empty_string(self):
        assert parse_references("") == []

    def test_real_world_references_header(self):
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
