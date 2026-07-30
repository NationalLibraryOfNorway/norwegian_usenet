import logging
import mailbox
from collections.abc import Iterator
from pathlib import Path

from usenet_no.archives.encoding import decode_bytes, detect_file_encoding
from usenet_no.mbox_utils import message_factory, write_mbox

logger = logging.getLogger(__name__)


def iter_raw_messages(mbox_file: Path) -> Iterator[bytes]:
    """Yield each message in an mbox file as its raw, undecoded bytes."""
    mbox_in = mailbox.mbox(str(mbox_file), factory=message_factory)
    # .keys() is load-bearing: mailbox.Mailbox sets __iter__ to itervalues, so
    # iterating the mailbox directly yields messages, which get_bytes rejects.
    for key in mbox_in.keys():
        yield mbox_in.get_bytes(key, from_=True)


def process_mbox_file(mbox_file: Path, outfile: Path) -> str:
    """Detect the encoding of one newsgroup's mbox, decode its messages and write them.

    Returns the encoding, which the caller reports against the source file.
    """
    encoding = detect_file_encoding(mbox_file)
    logger.debug("Reading %s as %s", mbox_file.name, encoding)
    write_mbox(
        (decode_bytes(raw, encoding) for raw in iter_raw_messages(mbox_file)),
        outfile,
    )
    return encoding
