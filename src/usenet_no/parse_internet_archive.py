import logging
import mailbox
from pathlib import Path
from typing import Iterator

import cchardet as chardet

from usenet_no.mbox_utils import message_factory, write_mbox

logger = logging.getLogger(__name__)


def detect_encoding(mbox_file: Path) -> str:
    """Return the encoding to read a raw IA mbox file with."""
    try:
        [_ for _ in mailbox.mbox(mbox_file)]
        logger.debug("Detected UTF-8 encoding for %s", mbox_file.name)
        return "utf-8"
    except UnicodeDecodeError:
        encoding = chardet.detect(mbox_file.read_bytes()).get("encoding")
        logger.debug("Re-encoding %s from %s to UTF-8", mbox_file.name, encoding)
        return encoding


def iter_raw_messages(mbox_file: Path) -> Iterator[bytes]:
    """Yield each message in an mbox file as its raw, undecoded bytes."""
    mbox_in = mailbox.mbox(str(mbox_file), factory=message_factory)
    for key in mbox_in.keys():
        yield mbox_in.get_bytes(key)


def decode_message_text(raw: bytes, encoding: str, error_handler: str) -> str:
    """Decode one raw message's bytes to text (headers and body together)."""
    return raw.decode(encoding, errors=error_handler)


def process_mbox_file(
    mbox_file: Path, outfile: Path, error_handler: str
) -> tuple[str, str]:
    """Detect encoding, decode each message and write the mbox. Returns (stem, encoding)."""
    encoding = detect_encoding(mbox_file)
    write_mbox(
        (
            decode_message_text(raw, encoding, error_handler)
            for raw in iter_raw_messages(mbox_file)
        ),
        outfile,
    )
    return mbox_file.stem, encoding
