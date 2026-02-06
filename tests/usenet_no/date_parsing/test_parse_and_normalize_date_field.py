from usenet_no.date_parsing import parse_and_normalize_date_field

example_date_fields = [
    "",
    " ",
    "Tue, 04 Dec 2001 21:45:43 +0100",
    "1997/03/23",
    "15. april 2000 17:13",
    "herejkre",
    None,
]

expected_outputs = [
    "unknown",
    "unknown",
    "2001-12-04",
    "1997-03-23",
    "2000-04-15",
    "unknown",
    "unknown",
]


def test_parses_and_normalizes():
    for input, expected_output in zip(example_date_fields, expected_outputs):
        assert parse_and_normalize_date_field(input) == expected_output
