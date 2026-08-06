import logging
from collections.abc import Iterator
from pathlib import Path

from usenet_no.archives.encoding import decode_bytes, detect_file_encoding
from usenet_no.mbox_utils import (
    RawMessage,
    open_source_mbox,
    split_envelope,
    write_mbox,
)

logger = logging.getLogger(__name__)

# Every archived article carries one of these. A message that carries neither did
# not come through the Google Groups archive the source files were scraped from.
_GOOGLE_HEADERS = (b"X-Google", b"Xref: archiver")

# How far into a message to look for them, past the envelope line.
_HEADER_SEARCH_BYTES = 4096


def iter_raw_messages(mbox_file: Path) -> Iterator[bytes]:
    """Yield each message in an mbox file as its raw, undecoded bytes."""
    mbox_in = open_source_mbox(mbox_file)
    # .keys() is load-bearing: mailbox.Mailbox sets __iter__ to itervalues, so
    # iterating the mailbox directly yields messages, which get_bytes rejects.
    for key in mbox_in.keys():
        yield mbox_in.get_bytes(key, from_=True)


def count_messages_without_google_headers(mbox_file: Path) -> int:
    """The number of messages carrying no X-Google or Google Xref header.

    Checked against the envelope rule that split the file, which was derived
    separately, so a message counted here means one of the two is wrong.
    """
    return sum(
        1
        for raw in iter_raw_messages(mbox_file)
        if not any(header in raw[:_HEADER_SEARCH_BYTES] for header in _GOOGLE_HEADERS)
    )


def process_mbox_file(mbox_file: Path, outfile: Path) -> str:
    """Detect the encoding of one newsgroup's mbox, decode its messages and write them.

    The source is an mbox file, so every message starts with its own envelope
    line. Its text is not unescaped: the source's own ">From " lines are content
    as far as this step can tell.

    Returns the encoding, which the caller reports against the source file.
    """
    encoding = detect_file_encoding(mbox_file)
    logger.debug("Reading %s as %s", mbox_file.name, encoding)
    mbox_in = open_source_mbox(mbox_file)
    message_count = len(mbox_in)
    write_mbox(
        (
            RawMessage(*split_envelope(decode_bytes(raw, encoding)))
            for raw in iter_raw_messages(mbox_file)
        ),
        outfile,
    )
    logger.info(
        "%s: %d messages, %d body lines starting with 'From ', %d bytes before the first message",
        mbox_file.name,
        message_count,
        mbox_in.rejected_envelope_count,
        mbox_in.bytes_before_first_message,
    )
    if mbox_in.bytes_before_first_message:
        logger.warning(
            "%s starts with %d bytes that belong to no message",
            mbox_file.name,
            mbox_in.bytes_before_first_message,
        )
    return encoding
