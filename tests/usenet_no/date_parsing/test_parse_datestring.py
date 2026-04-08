from datetime import datetime

from usenet_no.date_parsing import parse_datestring

example_dates = [
    "Tue, 04 Dec 2001 21:45:43 +0100",
    "1997/03/23",
    "Mon, 23 Sep 2002 13:24:43 +0200",
    "Mon, 23 Sep 2002 11:32:04 -0400",
    "Sun, 25 Feb 2007 03:52:41 -0800",
    "15. april 2000 17:13",
    "10 Nov 1997",
    "5 Oct 95 23:37: 7 GMT",
    "Sat, 14 Sep 1996 22:06:06 +3500",
    "Fri, 4 Oct 1996 18:25:48 +2900",
    "02 Oct 1996 15:51:37 -9100",
]

expected_datetimes = [
    datetime(2001, 12, 4),
    datetime(1997, 3, 23),
    datetime(2002, 9, 23),
    datetime(2002, 9, 23),
    datetime(2007, 2, 25),
    datetime(2000, 4, 15),
    datetime(1997, 11, 10),
    datetime(1995, 10, 5),
    datetime(1996, 9, 14),
    datetime(1996, 10, 4),
    datetime(1996, 10, 2),
]


def test_extracts_dates():
    for date_string, expected_datetime in zip(example_dates, expected_datetimes):
        assert parse_datestring(date_string) == expected_datetime


def test_empty_string():
    assert parse_datestring("") is None
    assert parse_datestring(" ") is None


def test_returns_none_when_non_date_input():
    for nonsense in (
        "ejrre",
        "2024-53-87",
        "908ds908s34",
        "DEC 15",
        "Jun 21",
        "19 jun",
    ):
        assert parse_datestring(nonsense) is None
