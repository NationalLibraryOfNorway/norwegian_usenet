import mailbox

from usenet_no.filter_archive_by_date import filter_mbox_by_date
from usenet_no.mbox_utils import message_factory

SPAN = ("1990-01-01", "2000-12-31")


def _count_messages(path):
    return len(mailbox.mbox(str(path), factory=message_factory))


def test_keeps_messages_within_date_range(mbox_data, tmp_path):
    source = mbox_data / "ia/no.inside.and.outside.span.mbox"
    out = tmp_path / "out.mbox"

    kept, total = filter_mbox_by_date(source, out, *SPAN)

    assert total == 2
    assert kept == 1


def test_excludes_messages_with_unknown_date(mbox_data, tmp_path):
    source = mbox_data / "ia/no.unknown.and.outside.span.mbox"
    out = tmp_path / "out.mbox"

    kept, total = filter_mbox_by_date(source, out, *SPAN)

    assert total == 2
    assert kept == 0


def test_skips_if_output_exists(mbox_data, tmp_path):
    out = tmp_path / "out.mbox"

    filter_mbox_by_date(mbox_data / "ia/no.one.dated.message.mbox", out, *SPAN)
    assert _count_messages(out) == 1

    # A larger source must not reach an output file that is already there
    filter_mbox_by_date(mbox_data / "ia/no.two.dated.messages.mbox", out, *SPAN)
    assert _count_messages(out) == 1


def test_overwrite_refilters_existing_output(mbox_data, tmp_path):
    out = tmp_path / "out.mbox"

    filter_mbox_by_date(mbox_data / "ia/no.one.dated.message.mbox", out, *SPAN)
    assert _count_messages(out) == 1

    filter_mbox_by_date(
        mbox_data / "ia/no.two.dated.messages.mbox", out, *SPAN, overwrite=True
    )
    assert _count_messages(out) == 2


def test_output_is_normalized_mbox(mbox_data, tmp_path):
    source = mbox_data / "ia/no.one.dated.message.mbox"
    out = tmp_path / "out.mbox"

    filter_mbox_by_date(source, out, *SPAN)

    content = out.read_bytes()
    assert b"\n\n\n" not in content
    assert content.startswith(b"From ")
