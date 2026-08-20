"""StrictMbox begins a message only at an envelope line matching its pattern.

The IA source files hold 3497 body lines starting with "From " that mailbox.mbox
reads as messages of their own. Those lines carry no Google Groups id, so the
envelope pattern passes over them.
"""

import mailbox

from usenet_no.mbox_utils import message_factory, open_mbox, open_source_mbox

IA_SOURCE = (
    "From 6051272061054231474\n"
    "X-Google-Thread: 10d1ce,7560fa0a1b3f7c5d\n"
    "From: ola@uio.no\n"
    "Subject: nick\n"
    "\n"
    "Frank Geronimo?\n"
    "\n"
    "From now on I'm thinking only of me.\n"
    "\n"
    "From -3831648075992104022\n"
    "X-Google-Thread: 10d1ce,7560fa0a1b3f7c5d\n"
    "From: kari@uio.no\n"
    "Subject: nick\n"
    "\n"
    "Hei\n"
)

WRITTEN = (
    "From MAILER-DAEMON\n"
    "From: ola@uio.no\n"
    "Subject: nick\n"
    "\n"
    ">From now on I'm thinking only of me.\n"
    "\n"
    "From 6051272061054231474\n"
    "From: kari@uio.no\n"
    "Subject: nick\n"
    "\n"
    "Hei\n"
)


def _write(tmp_path, name, text):
    mbox_file = tmp_path / name
    mbox_file.write_bytes(text.encode("utf-8"))
    return mbox_file


def test_a_body_line_starting_with_from_does_not_start_a_message(tmp_path):
    mbox_file = _write(tmp_path, "no.source.mbox", IA_SOURCE)

    assert len(open_source_mbox(mbox_file)) == 2


def test_mailbox_mbox_would_have_split_that_file(tmp_path):
    """What the reader is for: the stdlib finds a third message in the same bytes."""
    mbox_file = _write(tmp_path, "no.source.mbox", IA_SOURCE)

    assert len(mailbox.mbox(str(mbox_file), factory=message_factory)) == 3


def test_the_skipped_line_stays_in_the_body(tmp_path):
    mbox_file = _write(tmp_path, "no.source.mbox", IA_SOURCE)
    mbox = open_source_mbox(mbox_file)

    assert b"From now on I'm thinking only of me." in mbox.get_bytes(0)


def test_counts_the_lines_it_passed_over(tmp_path):
    mbox_file = _write(tmp_path, "no.source.mbox", IA_SOURCE)
    mbox = open_source_mbox(mbox_file)
    len(mbox)

    assert mbox.rejected_envelope_count == 1


def test_reports_bytes_ahead_of_the_first_message(tmp_path):
    """Bytes before the first envelope line belong to no message, and are dropped."""
    mbox_file = _write(tmp_path, "no.leading.mbox", "stray text\n\n" + IA_SOURCE)
    mbox = open_source_mbox(mbox_file)

    assert len(mbox) == 2
    assert mbox.bytes_before_first_message == len("stray text\n\n")


def test_matches_mailbox_mbox_when_no_body_line_starts_with_from(tmp_path):
    """Pins the _generate_toc override, which copies a private method."""
    text = "".join(
        f"From {index}\nFrom: ola@uio.no\nSubject: {index}\n\nBody {index}\n\n"
        for index in range(5)
    )
    mbox_file = _write(tmp_path, "no.plain.mbox", text)

    strict = open_source_mbox(mbox_file)
    stock = mailbox.mbox(str(mbox_file), factory=message_factory)

    assert len(strict) == len(stock) == 5
    assert [strict.get_bytes(key) for key in strict.keys()] == [
        stock.get_bytes(key) for key in stock.keys()
    ]


def test_open_mbox_accepts_the_placeholder_envelope(tmp_path):
    mbox_file = _write(tmp_path, "no.written.mbox", WRITTEN)

    assert len(open_mbox(mbox_file)) == 2


def test_open_mbox_passes_over_an_escaped_body_line(tmp_path):
    mbox_file = _write(tmp_path, "no.written.mbox", WRITTEN)
    mbox = open_mbox(mbox_file)

    assert b">From now on I'm thinking only of me." in mbox.get_bytes(0)


def test_open_source_mbox_rejects_the_placeholder_envelope(tmp_path):
    """The IA source has no placeholder envelopes, so its rule does not accept one."""
    mbox_file = _write(tmp_path, "no.written.mbox", WRITTEN)

    assert len(open_source_mbox(mbox_file)) == 1


def test_a_body_line_that_carries_an_id_does_start_a_message(tmp_path):
    """The limit of the rule. No IA source line takes this form outside an envelope."""
    text = (
        "From 6051272061054231474\n"
        "X-Google-Thread: 10d1ce\n"
        "From: ola@uio.no\n"
        "\n"
        "From 42\n"
    )
    mbox_file = _write(tmp_path, "no.source.mbox", text)

    assert len(open_source_mbox(mbox_file)) == 2
