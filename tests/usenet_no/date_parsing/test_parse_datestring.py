from datetime import datetime

from usenet_no.date_parsing import parse_datestring

example_dates = [
    "Tue, 04 Dec 2001 21:45:43 +0100",
    "1997/03/23",
    "Mon, 23 Sep 2002 13:24:43 +0200",
    "Mon, 23 Sep 2002 11:32:04 -0400",
    "Sun, 25 Feb 2007 03:52:41 -0800",
    "15. april 2000 17:13",
]

expected_datetimes = [
    datetime(2001, 12, 4),
    datetime(1997, 3, 23),
    datetime(2002, 9, 23),
    datetime(2002, 9, 23),
    datetime(2007, 2, 25),
    datetime(2000, 4, 15),
]


def test_extracts_dates():
    for date_string, expected_datetime in zip(example_dates, expected_datetimes):
        assert parse_datestring(date_string) == expected_datetime


def test_empty_string():
    assert parse_datestring("") is None
    assert parse_datestring(" ") is None


def test_returns_none_when_non_date_input():
    for nonsense in ("ejrre", "2024-53-87", "908ds908s34"):
        assert parse_datestring(nonsense) is None
