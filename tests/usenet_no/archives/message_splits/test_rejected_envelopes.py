"""The "From " lines of an IA source file that the envelope rule passes over."""

from usenet_no.archives.message_splits import rejected_envelopes
from usenet_no.mbox_utils import IA_SOURCE_ENVELOPE

TWO_MESSAGES = (
    "From 6214288843448422964\n"
    "X-Google-Language: NORWEGIAN\n"
    "From: ola@uio.no\n"
    "Subject: first\n"
    "\n"
    "From now on I write in Norwegian.\n"
    "\n"
    "From -3831648075992104022\n"
    "X-Google-Language: NORWEGIAN\n"
    "From: kari@uio.no\n"
    "Subject: second\n"
    "\n"
    "Blåbær\n"
    "From what I hear, they are ripe.\n"
)


def read(mbox_file):
    return [
        (envelope.source_file, envelope.line_number, envelope.starts_a_message)
        for envelope in rejected_envelopes(mbox_file, IA_SOURCE_ENVELOPE)
    ]


def write(tmp_path, name, text):
    mbox_file = tmp_path / name
    mbox_file.write_bytes(text.encode("utf-8"))
    return mbox_file


def test_reports_the_body_lines_and_not_the_envelope_lines(tmp_path):
    mbox_file = write(tmp_path, "no.two.mbox", TWO_MESSAGES)

    assert read(mbox_file) == [
        ("no.two.mbox", 6, False),
        ("no.two.mbox", 14, False),
    ]


def test_a_from_line_a_header_block_follows_starts_a_message(tmp_path):
    """What the report is for: such a line would be a message the envelope rule lost."""
    mbox_file = write(
        tmp_path,
        "no.envelope.mbox",
        "From 1\nX-Google-Language: NORWEGIAN\n\nhei\n\n"
        "From someone@uio.no Tue Mar 3 1998\n"
        "X-Google-Language: NORWEGIAN\n"
        "Subject: second\n"
        "\n"
        "hade\n",
    )

    assert read(mbox_file) == [("no.envelope.mbox", 6, True)]


def test_reads_the_lines_up_to_the_first_blank_one(tmp_path):
    """A body line with the next message further down it carries no header block."""
    mbox_file = write(
        tmp_path,
        "no.paragraph.mbox",
        "From 1\nX-Google-Language: NORWEGIAN\n\n"
        "From what I hear\nthey are ripe\n"
        "\n"
        "X-Google-Language: NORWEGIAN\n",
    )

    assert read(mbox_file) == [("no.paragraph.mbox", 4, False)]


def test_reports_a_from_line_at_the_end_of_the_file(tmp_path):
    mbox_file = write(
        tmp_path,
        "no.last.mbox",
        "From 1\nX-Google-Language: NORWEGIAN\n\nFrom now on\n",
    )

    assert read(mbox_file) == [("no.last.mbox", 4, False)]


def test_reports_two_from_lines_in_a_row(tmp_path):
    mbox_file = write(
        tmp_path,
        "no.run.mbox",
        "From 1\nX-Google-Language: NORWEGIAN\n\nFrom Ola\nFrom Kari\n",
    )

    assert read(mbox_file) == [("no.run.mbox", 4, False), ("no.run.mbox", 5, False)]


def test_an_escaped_from_line_is_not_one(tmp_path):
    """The IA sources escape none of theirs, but a written mbox file does."""
    mbox_file = write(
        tmp_path,
        "no.escaped.mbox",
        "From 1\nX-Google-Language: NORWEGIAN\n\n>From now on\n",
    )

    assert read(mbox_file) == []


def test_reports_nothing_for_a_file_whose_from_lines_are_all_envelopes(tmp_path):
    mbox_file = write(
        tmp_path,
        "no.plain.mbox",
        "From 1\nX-Google-Language: NORWEGIAN\n\nhei\n\nFrom -2\nSubject: hade\n\nhade\n",
    )

    assert read(mbox_file) == []
