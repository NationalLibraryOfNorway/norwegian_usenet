import mailbox

from usenet_no.filter_internet_archive_by_date import filter_mbox_by_date
from usenet_no.mbox_utils import message_factory, write_mbox


def _make_mbox(path, messages):
    """Write a list of (date, body) tuples as an mbox file."""
    texts = []
    for date, body in messages:
        texts.append(
            f"From sender@example.com\n"
            f"From: sender@example.com\n"
            f"Date: {date}\n"
            f"Subject: Test\n\n"
            f"{body}\n"
        )
    write_mbox(texts, path)


def _count_messages(path):
    return len(mailbox.mbox(str(path), factory=message_factory))


def test_keeps_messages_within_date_range(tmp_path):
    src = tmp_path / "src.mbox"
    _make_mbox(
        src,
        [
            ("Mon, 01 Jan 1996 12:00:00 +0000", "inside range"),
            ("Mon, 01 Jan 2005 12:00:00 +0000", "outside range"),
        ],
    )
    out = tmp_path / "out.mbox"
    kept, total = filter_mbox_by_date(src, out, "1990-01-01", "2000-12-31")
    assert total == 2
    assert kept == 1


def test_keeps_messages_with_unknown_date(tmp_path):
    src = tmp_path / "src.mbox"
    _make_mbox(
        src,
        [
            ("not a real date", "unparseable"),
            ("Mon, 01 Jan 2005 12:00:00 +0000", "outside range"),
        ],
    )
    out = tmp_path / "out.mbox"
    kept, total = filter_mbox_by_date(src, out, "1990-01-01", "2000-12-31")
    assert kept == 1


def test_skips_if_output_exists(tmp_path):
    src = tmp_path / "src.mbox"
    _make_mbox(src, [("Mon, 01 Jan 1996 12:00:00 +0000", "msg")])
    out = tmp_path / "out.mbox"

    filter_mbox_by_date(src, out, "1990-01-01", "2000-12-31")
    assert _count_messages(out) == 1

    _make_mbox(
        src,
        [
            ("Mon, 01 Jan 1996 12:00:00 +0000", "msg"),
            ("Mon, 01 Jan 1996 12:00:00 +0000", "msg2"),
        ],
    )
    filter_mbox_by_date(src, out, "1990-01-01", "2000-12-31")
    assert _count_messages(out) == 1


def test_overwrite_refilters_existing_output(tmp_path):
    src = tmp_path / "src.mbox"
    _make_mbox(src, [("Mon, 01 Jan 1996 12:00:00 +0000", "msg")])
    out = tmp_path / "out.mbox"

    filter_mbox_by_date(src, out, "1990-01-01", "2000-12-31")
    assert _count_messages(out) == 1

    _make_mbox(
        src,
        [
            ("Mon, 01 Jan 1996 12:00:00 +0000", "msg"),
            ("Mon, 01 Jan 1996 12:00:00 +0000", "msg2"),
        ],
    )
    filter_mbox_by_date(src, out, "1990-01-01", "2000-12-31", overwrite=True)
    assert _count_messages(out) == 2


def test_output_is_normalized_mbox(tmp_path):
    src = tmp_path / "src.mbox"
    _make_mbox(src, [("Mon, 01 Jan 1996 12:00:00 +0000", "hello")])
    out = tmp_path / "out.mbox"

    filter_mbox_by_date(src, out, "1990-01-01", "2000-12-31")

    content = out.read_bytes()
    assert b"\n\n\n" not in content
    assert content.startswith(b"From ")
